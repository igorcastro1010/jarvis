"""Funções determinísticas; nenhuma decisão aqui executa ações externas."""
from datetime import datetime


def route(message: str) -> str:
    text = message.casefold()
    if any(x in text for x in ('código', 'programação', 'repositório', 'corrija o projeto')):
        return 'codex'
    if any(x in text for x in ('que horas', 'olá', 'oi jarvis')):
        return 'local'
    return 'ollama'


def respond(message: str) -> str:
    if 'que horas' in message.casefold():
        return f"São {datetime.now():%H:%M}, senhor."
    return 'Olá, senhor. Como posso ajudar?'


def update_delivery(rows: list[dict], identity: str, changes: dict) -> None:
    if not identity.strip():
        raise ValueError('Identificação vazia')
    matches = [r for r in rows if identity.casefold().strip() in
               (str(r.get('placa', '')).casefold().strip(), str(r.get('motorista', '')).casefold().strip())]
    if len(matches) != 1:
        raise ValueError('Identificação ausente ou ambígua; informe a placa')
    allowed = {'motorista', 'cliente', 'cidade', 'localizacao', 'previsao', 'ultima_atualizacao', 'situacao'}
    if not set(changes) <= allowed:
        raise ValueError('Campo não permitido')
    matches[0].update(changes)
