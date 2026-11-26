"""Simulação local isolada da execução real e confirmação não operacional."""
import ctypes
import json
from pathlib import Path
import sys

root = str(Path(__file__).resolve().parents[2])
if root not in sys.path: sys.path.insert(0, root)
from jarvis.codex_handoff import prepare_queue_handoff
from jarvis.codex_process import run_process


def confirm_dialog(text):
    try:
        dialog = ctypes.windll.user32.MessageBoxTimeoutW
        dialog.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_ushort, ctypes.c_uint]
        dialog.restype = ctypes.c_int
        return dialog(None, text, 'OpenJarvis - confirmação de pedido', 0x4 | 0x20 | 0x100 | 0x40000, 0, 60000) == 6
    except (AttributeError, OSError):
        return False


def confirm(queue, item_id):
    preview = prepare_queue_handoff(queue, item_id)
    message = ('Confirmar este pedido após sua revisão? Esta confirmação é experimental e NÃO permite executar o Codex.\n\n'
               + json.dumps({key: preview[key] for key in ('id','projeto','solicitacao','impressao_digital')}, ensure_ascii=True, indent=2))
    accepted = confirm_dialog(message)
    try:
        current = prepare_queue_handoff(queue, item_id)
        unchanged = current['impressao_digital'] == preview['impressao_digital']
    except ValueError:
        unchanged = False
    return {'confirmado': bool(accepted and unchanged), 'confirmacao_humana': bool(accepted and unchanged), 'execucao_real_autorizada': False,
            'impressao_digital': preview['impressao_digital'], 'homologacao_fisica': 'pendente'}


def simulate(queue, item_id):
    task = queue.get(item_id)
    if task['estado'] != 'aguardando_aprovacao': raise ValueError('Pedido não aguarda aprovação')
    progress = []
    script = "print('Simulação iniciada', flush=True); print('Simulação concluída', flush=True)"
    result = run_process([sys.executable, '-I', '-u', '-c', script], '', timeout=10, progress=progress.append)
    ok = result.status == 'unverified' and result.exit_code == 0 and result.tree_terminated
    return {'confirmado': ok, 'simulado': True, 'tarefa_id': task['id'], 'estado': 'concluido' if ok else 'falhou',
            'progresso': progress, 'saida': result.stdout, 'erro': result.stderr,
            'sessao_codex': None, 'execucao_real_autorizada': False}
