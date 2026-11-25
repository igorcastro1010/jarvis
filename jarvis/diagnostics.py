"""Métricas locais sem conteúdo das conversas; valores ausentes são desconhecidos."""
import json
import logging
import threading
import time
from logging.handlers import RotatingFileHandler
from urllib.request import urlopen

_lock = threading.Lock()
_logger = logging.getLogger('jarvis.usage')


def usage_fields(result):
    def count(key):
        value = result.get(key)
        return value if type(value) is int and value >= 0 else None
    return {'entrada': count('prompt_eval_count'), 'saida': count('eval_count'),
            'cache': count('prompt_eval_cached_count'), 'duracao_ns': count('total_duration')}


def record_usage(result, model, operation='chat'):
    data = usage_fields(result)
    if data['entrada'] is None and data['saida'] is None: return
    data.update(modelo=model, operacao=operation)
    try:
        with _lock:
            if not _logger.handlers:
                from .local_vault import local_root
                folder = local_root() / 'logs'; folder.mkdir(parents=True, exist_ok=True)
                handler = RotatingFileHandler(folder / 'ollama-uso.log', maxBytes=256000, backupCount=2, encoding='utf8')
                handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
                _logger.addHandler(handler); _logger.setLevel(logging.INFO); _logger.propagate = False
            _logger.info(json.dumps(data, ensure_ascii=False))
    except (OSError, ValueError):
        pass


def collect():
    import psutil
    result = {'cpu_percent': psutil.cpu_percent(interval=0.1), 'ram_percent': psutil.virtual_memory().percent,
              'gpu_percent': None, 'vram_bytes': None, 'ollama': 'indisponível', 'latencia_ms': None}
    start = time.monotonic()
    try:
        with urlopen('http://127.0.0.1:11434/api/ps', timeout=2) as response:
            data = json.load(response)
        models = data['models']
        result['ollama'] = 'disponível'
        result['latencia_ms'] = round((time.monotonic() - start) * 1000)
        if models and all(type(item.get('size_vram')) is int for item in models):
            result['vram_bytes'] = sum(item['size_vram'] for item in models)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return result
