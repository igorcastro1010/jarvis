from .conversation import answer, ollama
from .memory import default_store
from .voice_session import Session


def main():
    print('Jarvis por texto. Digite sair para encerrar.')
    session, memory = Session(), default_store()
    while True:
        try:
            message = input('Senhor: ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message.casefold() in ('sair', 'exit'):
            break
        try:
            print('Jarvis:', answer(message, session, ollama, memory))
        except (OSError, ValueError, KeyError):
            print('Jarvis: Ollama ou o modelo local não está disponível, senhor.')


if __name__ == '__main__':
    main()
