"""Dados para futura confirmação local e adaptação Codex ainda bloqueada."""
import hashlib
import json



def confirmation_preview(task):
    """Gera resumo vinculado ao pedido; não concede nem persiste aprovação."""
    if task.get('estado') != 'aguardando_aprovacao':
        raise ValueError('Pedido não aguarda aprovação')
    values = [task['id'], task['projeto'], task['solicitacao']]
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError('Pedido inválido')
    digest = hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()
    return {'id': values[0], 'projeto': values[1], 'solicitacao': values[2],
            'impressao_digital': digest, 'aprovado': False}


def prepare_queue_handoff(queue, task_id):
    """Prepara confirmação de item existente, sem transição ou execução."""
    preview = confirmation_preview(queue.get(task_id))
    if preview['impressao_digital'] != queue.approval_fingerprint(task_id):
        raise ValueError('Pedido foi alterado durante a consulta')
    return preview
