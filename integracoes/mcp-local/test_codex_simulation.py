import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import server
from codex_queue import TaskQueue

class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.queue = TaskQueue(Path(self.tmp.name)/'fila.db')
        self.item = self.queue.create('Racha Fortalaka', 'Pedido ficticio')
        self.mock = patch.object(server, 'codex_store', self.queue); self.mock.start(); self.addCleanup(self.mock.stop)

    def test_simulation_runs_fixed_process_and_never_approves(self):
        result = server.run('local_codex_simular', {'id': self.item['id']})
        self.assertTrue(result['simulado'])
        self.assertEqual(result['estado'], 'concluido')
        self.assertIsNone(result['sessao_codex'])
        self.assertTrue(result['progresso'])
        self.assertEqual(self.queue.get(self.item['id'])['estado'], 'aguardando_aprovacao')
        self.assertFalse(self.queue.request_execution(self.item['id'])['confirmado'])

    def test_human_dialog_does_not_unlock_real_execution(self):
        with patch('codex_simulation.confirm_dialog', return_value=True):
            result = server.run('local_codex_confirmar', {'id': self.item['id']})
        self.assertTrue(result['confirmacao_humana'])
        self.assertFalse(result['execucao_real_autorizada'])
        self.assertEqual(self.queue.get(self.item['id'])['estado'], 'aguardando_aprovacao')
        self.assertFalse(self.queue.request_execution(self.item['id'])['confirmado'])

    def test_changed_request_during_dialog_is_rejected(self):
        def change(_):
            with self.queue.connect() as db: db.execute('UPDATE tasks SET description=? WHERE id=?', ('Outro pedido ficticio', self.item['id']))
            return True
        with patch('codex_simulation.confirm_dialog', side_effect=change):
            result = server.run('local_codex_confirmar', {'id': self.item['id']})
        self.assertFalse(result['confirmacao_humana'])
        self.assertFalse(result['execucao_real_autorizada'])

    def test_refusal_and_inexistent_task_never_launch(self):
        with patch('codex_simulation.confirm_dialog', return_value=False):
            self.assertFalse(server.run('local_codex_confirmar', {'id': self.item['id']})['confirmacao_humana'])
        with self.assertRaises(ValueError): server.run('local_codex_simular', {'id':'0'*32})

    def test_simulation_timeout_and_failure_are_not_success(self):
        from types import SimpleNamespace
        for status in ('timeout', 'cancelled', 'termination_unconfirmed'):
            result = SimpleNamespace(status=status, exit_code=0, tree_terminated=True, stdout='', stderr='')
            with patch('codex_simulation.run_process', return_value=result):
                self.assertEqual(server.run('local_codex_simular', {'id': self.item['id']})['estado'], 'falhou')

    def test_openjarvis_tool_returns_labelled_result(self):
        import json
        tool = next(t for t in server.tools if t.spec.name == 'local_codex_simular')
        response = tool.execute(id=self.item['id'])
        self.assertTrue(response.success)
        value = json.loads(response.content)
        self.assertTrue(value['simulado'])
        self.assertIsNone(value['sessao_codex'])
        self.assertFalse(value['execucao_real_autorizada'])

    def test_openjarvis_sees_simulation_failure_as_failure(self):
        from types import SimpleNamespace
        result = SimpleNamespace(status='timeout', exit_code=0, tree_terminated=True, stdout='', stderr='prazo')
        tool = next(t for t in server.tools if t.spec.name == 'local_codex_simular')
        with patch('codex_simulation.run_process', return_value=result):
            response = tool.execute(id=self.item['id'])
        self.assertFalse(response.success)
