"""Interface de voz local. O microfone é fechado durante a reprodução."""
import argparse
import logging
import msvcrt
from pathlib import Path
import time

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from piper import PiperVoice

from .conversation import answer, ollama
from .voice_session import VoiceController

RATE = 16000
VOICE = Path(__file__).resolve().parent.parent / 'data/models/piper/pt_BR-faber-medium.onnx'
LOG = logging.getLogger('jarvis.voice')


def listen(threshold=0.012, max_seconds=12, wait_seconds=8, cancelled=lambda: False, device=None, on_level=None):
    """Capture uma frase; descarta silêncio e fecha o dispositivo ao retornar."""
    chunks = []
    started = False
    quiet = 0
    block = RATE // 5
    with sd.InputStream(samplerate=RATE, channels=1, dtype='float32', blocksize=block, device=device) as stream:
        for _ in range((max_seconds + wait_seconds) * 5):
            if cancelled():
                return None
            data, overflow = stream.read(block)
            if cancelled():
                return None
            if overflow:
                LOG.warning('audio_input_overflow')
            mono = data[:, 0].copy()
            level = float(np.sqrt(np.mean(mono * mono)))
            if on_level: on_level(level)
            loud = level >= threshold
            if loud:
                started = True
                quiet = 0
            elif started:
                quiet += 1
            if started:
                chunks.append(mono)
                if quiet >= 5 or len(chunks) >= max_seconds * 5:
                    break
            elif _ >= wait_seconds * 5:
                break
    return np.concatenate(chunks) if chunks else None


def speak(voice, text):
    """Esc interrompe a reprodução; não há captura simultânea do microfone."""
    for chunk in voice.synthesize(text):
        sd.play(chunk.audio_float_array, chunk.sample_rate)
        while sd.get_stream().active:
            if msvcrt.kbhit() and msvcrt.getwch() == '\x1b':
                sd.stop()
                return False
            time.sleep(0.05)
    return True


def _main():
    parser = argparse.ArgumentParser(description='Jarvis: conversa local por voz')
    parser.add_argument('--push-to-talk', action='store_true', help='Enter inicia cada gravação')
    parser.add_argument('--threshold', type=float, default=0.012, help='limiar de detecção de voz')
    args = parser.parse_args()
    Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(filename='logs/voz.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    if not VOICE.exists():
        print('Modelo de voz ausente. Consulte as instruções de instalação.')
        return 1
    try:
        print('Carregando reconhecimento e voz locais...')
        stt = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4)
        voice = PiperVoice.load(VOICE)
        controller = VoiceController()
        from .memory import default_store
        memory = default_store()
        print('Microfone ativo. Diga Jarvis; Esc interrompe a fala; Ctrl+C encerra.')
        while True:
            if args.push_to_talk:
                input('Pressione Enter e fale: ')
            elif controller.active:
                print('Ouvindo...')
            else:
                print('Aguardando "Jarvis"...')
            audio = listen(threshold=args.threshold)
            if audio is None:
                continue
            start = time.perf_counter()
            segments, _ = stt.transcribe(audio, language='pt', beam_size=3, vad_filter=True,
                                         initial_prompt='Jarvis é o nome do assistente.')
            text = ' '.join(segment.text.strip() for segment in segments).strip()
            LOG.info('transcription_seconds=%.2f', time.perf_counter() - start)
            if not text:
                continue
            print('Senhor:', text)
            action, message = controller.accept(text, push_to_talk=args.push_to_talk)
            if action == 'ignore':
                continue
            if action == 'end':
                print('Conversa encerrada. Contexto apagado.')
                speak(voice, 'Até logo, senhor.')
                continue
            if action == 'ready':
                response = 'Estou ouvindo, senhor.'
            else:
                try:
                    start = time.perf_counter()
                    response = answer(message, controller.session, ollama, memory)
                    LOG.info('response_seconds=%.2f', time.perf_counter() - start)
                except (OSError, ValueError, KeyError, TimeoutError):
                    LOG.warning('local_model_unavailable')
                    response = 'Não consegui acessar o modelo local, senhor.'
            print('Jarvis:', response)
            start = time.perf_counter()
            speak(voice, response)
            LOG.info('speech_seconds=%.2f', time.perf_counter() - start)
    except (KeyboardInterrupt, EOFError):
        print('\nJarvis encerrado; contexto descartado.')
        return 0
    except Exception as exc:
        LOG.error('voice_error=%s', type(exc).__name__)
        print(f'Não foi possível iniciar ou usar o áudio: {exc}')
        return 1


def main():
    from .background import InstanceLock
    lock = InstanceLock()
    if not lock.acquire():
        lock.close()
        print('Já existe uma sessão de voz Jarvis em execução.')
        return 2
    try:
        return _main()
    finally:
        lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
