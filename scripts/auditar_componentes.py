"""Medição isolada com áudio sintético em memória; não acessa microfone."""
import json
import gc
import argparse
import time
import psutil

process = psutil.Process()


def measure(name, fn):
    before = process.memory_info().rss
    cpu_before = process.cpu_times()
    start = time.perf_counter()
    value = fn()
    duration = time.perf_counter() - start
    cpu_after = process.cpu_times()
    rss = process.memory_info().rss
    cpu = ((cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system)) / max(duration, 0.001) * 100
    print(json.dumps({'etapa': name, 'segundos': round(duration, 3), 'rss_mib': round(rss / 1048576, 1),
                      'delta_rss_mib': round((rss - before) / 1048576, 1), 'cpu_percent_um_nucleo': round(cpu, 1)}), flush=True)
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeticoes', type=int, default=3, choices=range(1, 21))
    args = parser.parse_args()
    measure('inicio', lambda: None)
    voice = measure('importacao_voz', lambda: __import__('jarvis.voice', fromlist=['VOICE']))
    import numpy as np
    from piper import PiperVoice
    engine = measure('piper_carregar', lambda: PiperVoice.load(voice.VOICE))
    chunks = measure('piper_sintetizar', lambda: list(engine.synthesize('Jarvis, que horas são?')))
    audio = np.concatenate([chunk.audio_float_array for chunk in chunks])
    source_rate = chunks[0].sample_rate
    points = np.arange(round(len(audio) * 16000 / source_rate)) * source_rate / 16000
    audio = np.interp(points, np.arange(len(audio)), audio).astype('float32')
    from jarvis.tray import AudioAdapters
    adapter = AudioAdapters()
    for iteration in range(args.repeticoes):
        result = measure(f'whisper_{iteration + 1}', lambda: adapter.transcribe(audio))
        print(json.dumps({'transcricao': result}, ensure_ascii=True), flush=True)
    def release():
        adapter.recognizer = None
        gc.collect()
    measure('whisper_liberar', release)
    result = measure('whisper_recarregar', lambda: adapter.transcribe(audio))
    print(json.dumps({'transcricao_recarregada': result}, ensure_ascii=True), flush=True)


if __name__ == '__main__': main()
