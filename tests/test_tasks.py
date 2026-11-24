import tempfile
import unittest
import subprocess
from pathlib import Path
from jarvis.tasks import TaskStore
from jarvis.conversation import answer
from jarvis.voice_session import Session
from unittest.mock import patch


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.db = TaskStore(self.base/'tarefas.sqlite3')
        (self.base/'a').mkdir(); (self.base/'b').mkdir()
        for name in ('a', 'b'):
            subprocess.run(['git', 'init', '-q', str(self.base/name)], check=True)

    def tearDown(self): self.tmp.cleanup()

    def test_project_alias_ambiguity_and_permissions(self):
        self.db.register('Alfa', ['app'], self.base/'a', None)
        self.db.register('Beta', ['app'], self.base/'b', None)
        with self.assertRaises(ValueError): self.db.resolve('app')
        self.assertEqual(self.db.resolve('alfa')['path'], str((self.base/'a').resolve()))
        self.assertFalse(self.db.resolve('alfa')['allow_write'])

    def test_queue_claims_only_one_and_survives_restart(self):
        self.db.register('Alfa', [], self.base/'a', None)
        first = self.db.submit('Alfa', 'Analise o README')
        second = self.db.submit('Alfa', 'Verifique os testes')
        self.assertEqual(self.db.claim()['id'], first)
        self.assertIsNone(self.db.claim())
        reloaded = TaskStore(self.base/'tarefas.sqlite3')
        reloaded.recover()
        self.assertEqual(reloaded.get(first)['status'], 'aguardando aprovação')
        self.assertEqual(reloaded.get(second)['status'], 'aguardando')

    def test_cancel_queued_and_reject_secret(self):
        self.db.register('Alfa', [], self.base/'a', None)
        task = self.db.submit('Alfa', 'Leia o README')
        self.db.cancel(task)
        self.assertEqual(self.db.get(task)['status'], 'cancelado')
        with self.assertRaises(ValueError): self.db.submit('Alfa', 'minha senha é 123')

    def test_conversation_enqueues_without_launching_codex(self):
        self.db.register('Alfa', [], self.base/'a', None)
        with patch('jarvis.tasks.default_tasks', return_value=self.db):
            result = answer('codex projeto Alfa: analise o README', Session(), lambda _: 'não esperado')
            self.assertIn('registrada', result)
            self.assertIn('não está disponível', result)
            self.assertEqual(self.db.list()[0]['status'], 'aguardando')
            self.assertIn('aguardando', answer('listar tarefas', Session(), lambda _: 'não esperado'))
