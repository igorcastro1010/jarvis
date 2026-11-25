"""Processo residente Windows. Não fornece ferramentas de execução ao modelo."""
import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import time

import pystray
from PIL import Image, ImageDraw
import sounddevice as sd

from .background import AssistantState, InstanceLock, Settings, load_settings, save_settings
from .conversation import ollama
from .service import VoiceService
from .voice import VOICE, listen
from .memory import default_store
from .voice_session import VOICE_VOCAB

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'data' / 'configuracao.json'
LOG = logging.getLogger('jarvis')


class AudioAdapters:
    def __init__(self, stt_model='small', output_device=None, volume=1.0):
        self.recognizer = None
        self.voice = None
        self.stt_model = stt_model
        self.output_device = output_device
        self.volume = volume

    def release(self):
        import gc
        self.recognizer = None
        self.voice = None
        gc.collect()

    def transcribe(self, audio):
        try:
            if self.recognizer is None:
                from faster_whisper import WhisperModel
                self.recognizer = WhisperModel(self.stt_model, device='cpu', compute_type='int8', cpu_threads=2,
                                               local_files_only=True)
            segments, _ = self.recognizer.transcribe(audio, language='pt', beam_size=3, vad_filter=True,
                                                     initial_prompt=VOICE_VOCAB)
            return ' '.join(s.text.strip() for s in segments).strip()
        except Exception:
            self.recognizer = None
            raise

    def speak(self, text, cancelled):
        try:
            if self.voice is None:
                from piper import PiperVoice
                self.voice = PiperVoice.load(VOICE)
            for chunk in self.voice.synthesize(text):
                if cancelled():
                    return
                sd.play(chunk.audio_float_array * self.volume, chunk.sample_rate, device=self.output_device)
                while sd.get_stream().active:
                    if cancelled():
                        sd.stop()
                        return
                    time.sleep(0.05)
        except Exception:
            sd.stop()
            self.voice = None
            raise


def image_for(status):
    colors = {'aguardando': '#436c8a', 'ouvindo': '#28a86b', 'processando': '#cb9c2f',
              'falando': '#3c8ed9', 'silenciado': '#666666', 'erro': '#bd4242'}
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), fill=colors.get(status, '#666666'))
    draw.text((24, 15), 'J', fill='white', stroke_width=1)
    return image


def configure(state, store):
    import tkinter as tk
    from tkinter import messagebox
    window = tk.Tk()
    window.title('Jarvis — Configurações')
    window.resizable(False, False)
    current = store[0]
    tk.Label(window, text='Inatividade (10–3600 segundos)').grid(row=0, column=0, padx=10, pady=8)
    inactivity = tk.Entry(window)
    inactivity.insert(0, str(current.inactivity_seconds)); inactivity.grid(row=0, column=1, padx=10)
    tk.Label(window, text='Limiar do microfone (0,001–0,2)').grid(row=1, column=0, padx=10, pady=8)
    threshold = tk.Entry(window)
    threshold.insert(0, str(current.threshold)); threshold.grid(row=1, column=1, padx=10)
    def save():
        try:
            settings = Settings(int(inactivity.get()), float(threshold.get().replace(',', '.')))
            save_settings(CONFIG, settings)
            store[0] = settings
            window.destroy()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Configuração inválida', str(exc), parent=window)
    tk.Button(window, text='Salvar', command=save).grid(row=2, columnspan=2, pady=10)
    window.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke-test', type=float, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    lock = InstanceLock()
    if not lock.acquire():
        lock.close()
        return 2
    logs = ROOT / 'logs'
    logs.mkdir(exist_ok=True)
    handler = RotatingFileHandler(logs / 'assistente.log', maxBytes=512_000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    LOG.addHandler(handler); LOG.setLevel(logging.INFO)
    state = AssistantState()
    store = [load_settings(CONFIG)]
    adapters = AudioAdapters()
    service = VoiceService(state, lambda: store[0], listen, adapters.transcribe, adapters.speak, ollama, memory=default_store(), release_idle=adapters.release)
    menu = pystray.Menu(
        pystray.MenuItem(lambda _: f'Estado: {state.status}', None, enabled=False),
        pystray.MenuItem('Ativar conversa', lambda: state.activate(time.monotonic())),
        pystray.MenuItem('Silenciar', lambda: state.mute()),
        pystray.MenuItem('Reativar microfone', lambda: state.unmute()),
        pystray.MenuItem('Configurações', lambda: configure(state, store)),
        pystray.MenuItem('Sair', lambda icon: shutdown(icon, state)))
    icon = pystray.Icon('Jarvis', image_for(state.status), 'Jarvis — aguardando', menu)
    def update():
        previous = None
        while not state.stopped:
            status = state.status
            if status != previous:
                icon.icon = image_for(status)
                icon.title = 'Jarvis — ' + status
                icon.update_menu()
                previous = status
            time.sleep(0.2)
    if args.smoke_test:
        state.mute()
        threading.Timer(args.smoke_test, lambda: shutdown(icon, state)).start()
    else:
        threading.Thread(target=service.run, daemon=True, name='audio').start()
    threading.Thread(target=update, daemon=True, name='status').start()
    try:
        icon.run()
    finally:
        with state.lock:
            state.stopped = True
            state.generation += 1
        sd.stop()
        handler.close()
        lock.close()
    return 0


def shutdown(icon, state):
    with state.lock:
        state.stopped = True
        state.generation += 1
        state.controller.session.reset()
    sd.stop()
    icon.stop()


if __name__ == '__main__':
    raise SystemExit(main())
