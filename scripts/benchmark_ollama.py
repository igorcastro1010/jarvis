"""Benchmark local com prompts fictícios. Não inicia downloads nem altera drivers."""
import json
import sys
import time
import urllib.request
import psutil

PROMPTS = [
    ('portugues', 'Explique em duas frases o que é um backup e por que ele é útil.'),
    ('comando', 'Qual comando devo dizer para pedir ao assistente que abra o YouTube? Responda em uma frase.'),
    ('contexto', 'Dados fictícios: o projeto Alfa usa uniforme azul; o projeto Beta usa verde. Qual é a cor do projeto Alfa?'),
    ('resumo', 'Resuma: A biblioteca abrirá segunda-feira às 9h. Aos domingos ficará fechada. O empréstimo dura 14 dias.'),
]


def post(path, body):
    req = urllib.request.Request('http://127.0.0.1:11434/api/' + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=240)


def rss():
    total = 0
    for process in psutil.process_iter(['name', 'memory_info']):
        try:
            if 'ollama' in (process.info['name'] or '').casefold(): total += process.info['memory_info'].rss
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return total


def run(model):
    results = []
    for kind, prompt in PROMPTS:
        data = {'model': model, 'messages': [{'role': 'system', 'content': 'Responda em português brasileiro, de forma curta e precisa.'}, {'role': 'user', 'content': prompt}],
                'stream': True, 'keep_alive': '2m', 'options': {'num_ctx': 2048, 'num_predict': 128, 'temperature': 0}}
        if model.startswith('qwen3:'): data['think'] = False
        start = time.monotonic(); first = None; answer = ''; final = {}; active = {}; memory = 0
        with post('chat', data) as response:
            for line in response:
                obj = json.loads(line)
                chunk = obj.get('message', {}).get('content', '')
                if chunk and first is None:
                    first = time.monotonic() - start
                    with urllib.request.urlopen('http://127.0.0.1:11434/api/ps', timeout=5) as ps:
                        active = next((x for x in json.load(ps)['models'] if x['name'] == model), {})
                    memory = rss()
                answer += chunk
                if obj.get('done'): final = obj
        duration = final.get('eval_duration', 0) / 1e9
        results.append({'categoria': kind, 'resposta': answer, 'ttft_s': first, 'total_s': time.monotonic()-start,
                        'carga_s': final.get('load_duration', 0)/1e9, 'tokens_s': final.get('eval_count', 0)/duration if duration else None,
                        'fim': final.get('done_reason'), 'rss_ollama_bytes': memory,
                        'vram_bytes': active.get('size_vram'), 'modelo_memoria_bytes': active.get('size')})
    with post('generate', {'model': model, 'keep_alive': 0}): pass
    return results


if __name__ == '__main__':
    for model in sys.argv[1:]:
        try: print(json.dumps({'modelo': model, 'resultados': run(model)}, ensure_ascii=False), flush=True)
        except Exception as error: print(json.dumps({'modelo': model, 'erro': str(error)}, ensure_ascii=False), flush=True)
