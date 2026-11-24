import json
import urllib.error
import urllib.request
from .core import respond, route


def main():
    print('Jarvis experimental por texto. Digite sair para encerrar.')
    while True:
        try:
            message = input('Senhor: ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message.casefold() in ('sair', 'exit'):
            break
        destination = route(message)
        if destination == 'local':
            print('Jarvis:', respond(message))
        elif destination == 'codex':
            print('Jarvis: Essa tarefa precisa do Codex; a execução automática ainda não está configurada, senhor.')
        else:
            request = urllib.request.Request('http://127.0.0.1:11434/api/generate',
                data=json.dumps({'model': 'qwen2.5:3b', 'prompt': message, 'stream': False,
                                 'keep_alive': 0}).encode(), headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    print('Jarvis:', json.load(response)['response'])
            except (OSError, ValueError, KeyError, urllib.error.URLError):
                print('Jarvis: Ollama ou o modelo local não está disponível, senhor.')


if __name__ == '__main__':
    main()
