"""Roteamento seguro de conversa; o modelo não recebe ferramentas."""
import json
import urllib.request
from .core import respond, route

SYSTEM = ('Você é Jarvis, assistente educado e objetivo. Responda em português brasileiro, '
          'de forma concisa, tratando o usuário por senhor. Não alegue executar ações.')


def answer(message, session, model):
    destination = route(message)
    if destination == 'local':
        result = respond(message)
    elif destination == 'codex':
        result = 'Essa tarefa precisa do Codex; a execução automática ainda não está configurada, senhor.'
    else:
        messages = [{'role': 'system', 'content': SYSTEM}, *session.history,
                    {'role': 'user', 'content': message}]
        result = model(messages)
    session.remember(message, result)
    return result


def ollama(messages, model='qwen2.5:3b'):
    data = json.dumps({'model': model, 'messages': messages, 'stream': False,
                       'keep_alive': '2m', 'options': {'num_predict': 160, 'num_ctx': 2048}}).encode()
    request = urllib.request.Request('http://127.0.0.1:11434/api/chat', data=data,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.load(response)
    return result['message']['content'].strip()
