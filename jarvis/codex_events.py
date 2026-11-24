"""Avaliação conservadora de eventos; saída do processo não é prova de sucesso."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Budget:
    max_prompt_chars: int = 4000
    max_input_tokens: int = 100000
    max_output_tokens: int = 4000

    def __post_init__(self):
        if min(self.max_prompt_chars, self.max_input_tokens, self.max_output_tokens) <= 0:
            raise ValueError('Limites devem ser positivos.')

    def check_prompt(self, prompt):
        if len(prompt) > self.max_prompt_chars:
            raise ValueError('Solicitação excede o limite de caracteres.')

    def exceeded(self, usage):
        return usage.get('input_tokens', 0) > self.max_input_tokens or usage.get('output_tokens', 0) > self.max_output_tokens


class CodexEvents:
    def __init__(self):
        self.completed = False
        self.failed = False
        self.message = None
        self.usage = None

    def feed(self, event):
        kind = event.get('type')
        if kind in ('turn.failed', 'error'): self.failed = True
        if kind == 'item.completed':
            item = event.get('item', {})
            if item.get('type') == 'command_execution' and (item.get('status') == 'failed' or item.get('exit_code') not in (None, 0)):
                self.failed = True
            if item.get('type') == 'agent_message': self.message = item.get('text', '')
        if kind == 'turn.completed':
            self.completed = True
            usage = event.get('usage') or {}
            if isinstance(usage.get('input_tokens'), int) and isinstance(usage.get('output_tokens'), int):
                total = usage['input_tokens']; cached = usage.get('cached_input_tokens', 0)
                if not isinstance(cached, int) or not 0 <= cached <= total: cached = 0
                self.usage = {'input_tokens': total, 'cached_input_tokens': cached,
                              'uncached_input_tokens': total - cached, 'output_tokens': usage['output_tokens']}

    def success(self, exit_code, verified=False):
        return bool(verified and exit_code == 0 and self.completed and not self.failed and self.message and self.message.strip())
