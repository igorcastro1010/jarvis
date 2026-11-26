"""Correlação local; nunca cria eventos ou altera o Habblaud."""
import re


def correlate_session(task_id, events, *, simulated):
    if not isinstance(task_id,str) or not re.fullmatch(r'[0-9a-f]{32}',task_id):
        raise ValueError('Identificador de tarefa inválido')
    if simulated or not events.session_id: return None
    return {'tarefa_id':task_id, 'sessao_codex':events.session_id, 'habblaud':'nao_verificado'}
