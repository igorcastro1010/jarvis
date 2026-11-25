import unittest
from jarvis.codex_events import CodexEvents
from jarvis.codex_handoff import confirmation_preview
from jarvis.codex_process import CodexCLI

class HandoffTests(unittest.TestCase):
    def test_confirmation_is_exact_preview_and_not_approval(self):
        task = {'id':'a'*32, 'projeto':'Ficticio', 'solicitacao':'Analisar arquivo', 'estado':'aguardando_aprovacao'}
        result = confirmation_preview(task)
        self.assertEqual(result['solicitacao'], task['solicitacao'])
        self.assertFalse(result['aprovado'])
        changed = dict(task, solicitacao='Outro pedido')
        self.assertNotEqual(result['impressao_digital'], confirmation_preview(changed)['impressao_digital'])

    def test_adapter_remains_disabled_and_never_starts_process(self):
        adapter = CodexCLI()
        with self.assertRaises(PermissionError): adapter.run('pedido ficticio', '.')

    def test_capture_real_session_id_only_from_valid_thread_started(self):
        events = CodexEvents()
        events.feed({'type':'thread.started','thread_id':'not-a-uuid'})
        self.assertIsNone(events.session_id)
        ident = '019b0000-0000-7000-8000-000000000001'
        events.feed({'type':'thread.started','thread_id':ident})
        self.assertEqual(events.session_id, ident)
        events.feed({'type':'thread.started','thread_id':'019b0000-0000-7000-8000-000000000002'})
        self.assertEqual(events.session_id, ident)

class QueueHandoffTests(unittest.TestCase):
    def test_preview_uses_actual_queue_fingerprint_without_approval(self):
        import sys, tempfile
        from pathlib import Path
        from unittest.mock import patch
        folder = str(Path(__file__).resolve().parents[1] / 'integracoes' / 'mcp-local')
        sys.path.insert(0, folder)
        try:
            from codex_queue import TaskQueue
            from jarvis.codex_handoff import prepare_queue_handoff
            with tempfile.TemporaryDirectory() as temp:
                queue = TaskQueue(Path(temp)/'fila.db')
                task = queue.create('Racha Fortalaka', 'Solicitacao ficticia')
                with patch.object(queue, 'transition', side_effect=AssertionError('transicao proibida')):
                    preview = prepare_queue_handoff(queue, task['id'])
                self.assertEqual(preview['impressao_digital'], queue.approval_fingerprint(task['id']))
                self.assertFalse(preview['aprovado'])
                self.assertEqual(queue.get(task['id'])['estado'], 'aguardando_aprovacao')
                self.assertFalse(queue.request_execution(task['id'])['confirmado'])
        finally:
            sys.path.remove(folder)
