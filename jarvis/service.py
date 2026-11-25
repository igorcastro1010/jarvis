"""Laço de voz independente da interface; adaptadores podem ser substituídos em testes."""
import logging
import time
from .conversation import answer
from .voice_session import Session

LOG = logging.getLogger('jarvis.service')


class VoiceService:
    def __init__(self, state, settings, capture, transcribe, speak, model, clock=time.monotonic, memory=None, on_exchange=None, shared=None, release_idle=None):
        self.state, self.settings = state, settings
        self.capture, self.transcribe, self.speak, self.model = capture, transcribe, speak, model
        self.clock = clock
        self.memory = memory
        self.on_exchange = on_exchange
        self.shared = shared
        self.release_idle = release_idle
        self.muted_since = None
        self.idle_released = False

    def manage_idle(self, now):
        with self.state.lock:
            muted = self.state.status == 'silenciado'
        if not muted:
            self.muted_since = None
            self.idle_released = False
        elif self.muted_since is None:
            self.muted_since = now
        elif not self.idle_released and now - self.muted_since >= 120 and self.release_idle:
            self.idle_released = True
            try:
                self.release_idle()
            except Exception as exc:
                LOG.warning('idle_release_failed type=%s', type(exc).__name__)

    def step(self):
        state = self.state
        with state.lock:
            if state.stopped or state.status == 'silenciado':
                return
            expired = state.expire(self.clock(), self.settings().inactivity_seconds)
            ticket = state.ticket()
            state.status = 'ouvindo' if state.controller.active else 'aguardando'
        if expired and self.shared:
            self.shared.reset()
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
                    if state.valid(ticket):
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
                session.scope = state.controller.session.scope
            if action == 'ignore':
                with state.lock:
                    if state.valid(ticket):
                        state.status = 'aguardando'
                return
            if action == 'ready':
                response = 'Estou ouvindo, senhor.'
            elif action == 'end':
                if self.shared: self.shared.reset()
                response = 'Até logo, senhor.'
            else:
                response = (self.shared.respond(message, self.model, self.memory, valid=lambda: state.valid(ticket))
                            if self.shared else answer(message, session, self.model, self.memory))
            with state.lock:
                if not state.valid(ticket):
                    return
                if action == 'answer':
                    state.controller.session.history = session.history
                    state.controller.session.scope = session.scope
                state.status = 'falando'
            if self.on_exchange:
                self.on_exchange(text, response)
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
            self.manage_idle(self.clock())
            if self.state.status == 'silenciado':
                time.sleep(0.2)
                continue
            self.step()
            if self.state.status == 'erro':
                time.sleep(3)
