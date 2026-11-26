"""Simulação local isolada da execução real e confirmação não operacional."""
import ctypes
from pathlib import Path
import sys

root = str(Path(__file__).resolve().parents[2])
if root not in sys.path: sys.path.insert(0, root)
from jarvis.codex_handoff import prepare_queue_handoff
from jarvis.codex_process import run_process
from codex_approval import ApprovalBroker


def confirm_dialog(text):
    try:
        dialog = ctypes.windll.user32.MessageBoxTimeoutW
        dialog.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_ushort, ctypes.c_uint]
        dialog.restype = ctypes.c_int
        return dialog(None, text, 'OpenJarvis - confirmação de pedido', 0x4 | 0x20 | 0x100 | 0x40000, 0, 60000) == 6
    except (AttributeError, OSError):
        return False


_approval_broker = ApprovalBroker(lambda message: confirm_dialog(message), ttl=120)


def confirm(queue, item_id):
    preview = prepare_queue_handoff(queue, item_id)
    accepted = _approval_broker.request(queue, item_id)
    return {'confirmado': accepted, 'confirmacao_humana': accepted, 'execucao_real_autorizada': False,
            'impressao_digital': _approval_broker.fingerprint(item_id) if accepted else preview['impressao_digital'], 'homologacao_fisica': 'pendente'}

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
