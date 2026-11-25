"""Contexto temporário compartilhado sem manter o bloqueio durante a inferência."""
import threading
from .voice_session import Session
from .conversation import answer


class SharedConversation:
    def __init__(self):
        self._session = Session()
        self._lock = threading.Lock()
        self._turn = threading.Lock()
        self._generation = 0

    def reset(self):
        with self._lock:
            self._generation += 1
            self._session.reset()

    def respond(self, message, model, memory=None, *, valid=lambda: True):
        with self._turn:
            if not valid():
                return None
            with self._lock:
                ticket = self._generation
                session = Session(self._session.max_turns)
                session.history = list(self._session.history)
                session.scope = self._session.scope
            response = answer(message, session, model, memory)
            with self._lock:
                if ticket == self._generation and valid():
                    self._session = session
            return response
