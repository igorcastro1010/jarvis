"""Estado temporário de conversa, sem persistência de falas."""
import re


def extract_wake(text: str) -> str | None:
    match = re.search(r'\bjarvis\b', text, flags=re.IGNORECASE)
    return text[match.end():].lstrip(' ,.!?:;-').rstrip() if match else None


class Session:
    def __init__(self, max_turns: int = 4):
        if max_turns < 1:
            raise ValueError('max_turns deve ser positivo')
        self.max_turns = max_turns
        self.history: list[dict[str, str]] = []

    def remember(self, user: str, assistant: str) -> None:
        self.history.extend([{'role': 'user', 'content': user}, {'role': 'assistant', 'content': assistant}])
        self.history = self.history[-2 * self.max_turns:]

    def reset(self) -> None:
        self.history.clear()

    def should_end(self, text: str) -> bool:
        return text.casefold().strip(' .!?') in ('encerrar conversa', 'finalizar conversa', 'até mais jarvis', 'sair')


class VoiceController:
    def __init__(self):
        self.active = False
        self.session = Session()

    def accept(self, text: str, push_to_talk: bool = False) -> tuple[str, str]:
        text = text.strip()
        if not self.active:
            wake = extract_wake(text)
            if wake is None and not push_to_talk:
                return 'ignore', ''
            self.active = True
            text = text if wake is None else wake
        if self.session.should_end(text):
            self.active = False
            self.session.reset()
            return 'end', ''
        return ('answer', text) if text else ('ready', '')
