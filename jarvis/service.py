"""Laço de voz independente da interface; adaptadores podem ser substituídos em testes."""
import logging
import time
from .conversation import answer
from .voice_session import Session

LOG = logging.getLogger('jarvis.service')


class VoiceService:
    def __init__(self, state, settings, capture, transcribe, speak, model, clock=time.monotonic):
        self.state, self.settings = state, settings
        self.capture, self.transcribe, self.speak, self.model = capture, transcribe, speak, model
        self.clock = clock

    def step(self):
        state = self.state
        with state.lock:
            if state.stopped or state.status == 'silenciado':
                return
            state.expire(self.clock(), self.settings().inactivity_seconds)
            ticket = state.ticket()
            state.status = 'ouvindo' if state.controller.active else 'aguardando'
        try:
            audio = self.capture(threshold=self.settings().threshold, wait_seconds=2,
                                 cancelled=lambda: not state.valid(ticket))
            if audio is None or not state.valid(ticket):
                return
            with state.lock:
                if not state.valid(ticket):
                    return
                state.status = 'processando'
            text = self.transcribe(audio)
            if not state.valid(ticket):
                return
            if not text.strip():
                with state.lock:
                    state.status = 'ouvindo' if state.controller.active else 'aguardando'
                return
            with state.lock:
                if not state.valid(ticket):
                    return
                action, message = state.controller.accept(text)
                if action != 'ignore':
                    state.last_activity = self.clock()
                session = Session(state.controller.session.max_turns)
                session.history = list(state.controller.session.history)
            if action == 'ignore':
                with state.lock:
                    if state.valid(ticket):
                        state.status = 'aguardando'
                return
            if action == 'ready':
                response = 'Estou ouvindo, senhor.'
            elif action == 'end':
                response = 'Até logo, senhor.'
            else:
                response = answer(message, session, self.model)
            with state.lock:
                if not state.valid(ticket):
                    return
                if action == 'answer':
                    state.controller.session.history = session.history
                state.status = 'falando'
            self.speak(response, lambda: not state.valid(ticket))
            with state.lock:
                if state.valid(ticket):
                    state.last_activity = self.clock()
                    state.status = 'ouvindo' if state.controller.active else 'aguardando'
        except Exception as exc:
            LOG.warning('voice_step_failed type=%s', type(exc).__name__)
            with state.lock:
                if state.valid(ticket):
                    state.status = 'erro'

    def run(self):
        while not self.state.stopped:
            if self.state.status == 'silenciado':
                time.sleep(0.2)
                continue
            self.step()
            if self.state.status == 'erro':
                time.sleep(3)
