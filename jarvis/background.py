"""Configuração e estado do assistente residente, sem acesso a áudio."""
import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from threading import RLock
from .voice_session import VoiceController


@dataclass(eq=True)
class Settings:
    inactivity_seconds: int = 60
    threshold: float = 0.012

    def validate(self):
        if not 10 <= self.inactivity_seconds <= 3600 or not 0.001 <= self.threshold <= 0.2:
            raise ValueError('Inatividade deve ser 10–3600 s e limiar 0,001–0,2.')


def load_settings(path: Path) -> Settings:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        result = Settings(**value)
        result.validate()
        return result
    except (OSError, ValueError, TypeError):
        return Settings()


def save_settings(path: Path, settings: Settings):
    settings.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


class AssistantState:
    def __init__(self):
        self.lock = RLock()
        self.controller = VoiceController()
        self.status = 'aguardando'
        self.generation = 0
        self.last_activity = 0.0
        self.stopped = False

    def ticket(self):
        with self.lock:
            return self.generation

    def valid(self, ticket):
        with self.lock:
            return not self.stopped and self.status != 'silenciado' and ticket == self.generation

    def mute(self):
        with self.lock:
            self.generation += 1
            self.controller.active = False
            self.controller.session.reset()
            self.status = 'silenciado'

    def unmute(self):
        with self.lock:
            self.generation += 1
            self.status = 'aguardando'

    def activate(self, now):
        with self.lock:
            self.generation += 1
            self.controller.active = True
            self.last_activity = now
            self.status = 'ouvindo'

    def expire(self, now, seconds):
        with self.lock:
            if self.controller.active and now - self.last_activity >= seconds:
                self.controller.active = False
                self.controller.session.reset()
                self.status = 'aguardando'
                self.generation += 1
                return True
            return False


class InstanceLock:
    def __init__(self, name='Local\\JarvisPersonalAssistant-v03'):
        self.name = name
        self.handle = None

    def acquire(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        self.handle = kernel.CreateMutexW(None, False, self.name)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        return ctypes.get_last_error() != 183

    def close(self):
        if self.handle:
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle(self.handle)
            self.handle = None
