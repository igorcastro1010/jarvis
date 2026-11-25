import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

from codex_queue import TaskQueue
import server


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'queue.db'
        self.queue = TaskQueue(self.path)

    def test_persistence_deduplication_and_project_restriction(self):
        first = self.queue.create('Racha Fortalaka', 'Melhorar a página de partidas')
        again = TaskQueue(self.path).create('Racha Fortalaka', 'Melhorar a página de partidas')
        self.assertEqual(first['id'], again['id'])
        self.assertEqual(TaskQueue(self.path).get(first['id'])['estado'], 'aguardando_aprovacao')
        with self.assertRaises(ValueError): self.queue.create('Outro projeto', 'Alterar página')

    def test_never_executes_even_if_requested(self):
        item = self.queue.create('Racha Fortalaka', 'Criar teste fictício')
        with patch('subprocess.Popen', side_effect=AssertionError('processo proibido')), patch('subprocess.run', side_effect=AssertionError('processo proibido')):
            result = self.queue.request_execution(item['id'])
        self.assertFalse(result['confirmado'])
        self.assertEqual(self.queue.get(item['id'])['estado'], 'aguardando_aprovacao')

    def test_recovery_and_sensitive_input(self):
        item = self.queue.create('Racha Fortalaka', 'Testar recuperação')
        with self.queue.connect() as db:
            db.execute("UPDATE tasks SET state='executando' WHERE id=?", (item['id'],))
        self.assertEqual(TaskQueue(self.path).get(item['id'])['estado'], 'revisao_necessaria')
        with self.assertRaises(ValueError): self.queue.create('Racha Fortalaka', 'senha=valorprivado')

    def test_mcp_uses_fake_project_without_process_or_approval(self):
        fake_project = Path(self.temp.name) / 'fake-project'
        fake_project.mkdir()
        subprocess.run(['git', 'init', '-q', str(fake_project)], check=True, capture_output=True)
        with patch.object(server, 'codex_store', self.queue), patch.object(server, 'project', return_value=fake_project), patch('subprocess.Popen', side_effect=AssertionError('processo proibido')), patch('subprocess.run', side_effect=AssertionError('processo proibido')):
            item = server.run('local_codex_preparar', {'projeto': 'Racha Fortalaka', 'solicitacao': 'Melhorar tela fictícia'})
            result = server.run('local_codex_executar', {'id': item['id']})
            self.assertFalse(result['confirmado'])
            self.assertEqual(server.run('local_codex_listar', {})['tarefas'][0]['estado'], 'aguardando_aprovacao')

    def test_cancel_is_persistent_and_cannot_execute(self):
        item = self.queue.create('Racha Fortalaka', 'Ajustar tela fictícia')
        self.assertEqual(self.queue.cancel(item['id'])['estado'], 'cancelado')
        self.assertEqual(TaskQueue(self.path).get(item['id'])['estado'], 'cancelado')
        self.assertFalse(self.queue.request_execution(item['id'])['confirmado'])

    def test_lifecycle_records_events_and_rejects_invalid_transition(self):
        item = self.queue.create('Racha Fortalaka', 'Ajustar projeto fictício')
        with self.assertRaises(ValueError): self.queue.transition(item['id'], 'concluido')
        self.queue.transition(item['id'], 'aprovado')
        self.queue.transition(item['id'], 'executando')
        self.queue.transition(item['id'], 'concluido')
        self.assertEqual([e['estado'] for e in self.queue.events(item['id'])], ['aguardando_aprovacao', 'aprovado', 'executando', 'concluido'])

    def test_approval_requires_exact_unchanged_request_and_real_dialog_gate(self):
        item = self.queue.create('Racha Fortalaka', 'Melhorar interface fictícia')
        fingerprint = self.queue.approval_fingerprint(item['id'])
        with self.queue.connect() as db: db.execute('UPDATE tasks SET description=? WHERE id=?', ('Outra solicitação fictícia', item['id']))
        self.assertNotEqual(fingerprint, self.queue.approval_fingerprint(item['id']))
        with patch('subprocess.Popen', side_effect=AssertionError('processo proibido')):
            self.assertFalse(self.queue.request_approval(item['id'])['confirmado'])
        self.assertEqual(self.queue.get(item['id'])['estado'], 'aguardando_aprovacao')


if __name__ == '__main__': unittest.main()
