import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from jarvis.tasks import TaskStore
from jarvis.queue_executor import execute_next


class QueueExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name)
        repo = path / 'repo'; repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        self.store = TaskStore(path / 'queue.db')
        self.store.register('Exemplo', [], repo, None)
        self.task = self.store.submit('Exemplo', 'analisar ficheiro')

    def tearDown(self): self.tmp.cleanup()

    def test_disabled_does_not_claim_or_run(self):
        execute_next(self.store, lambda *_: self.fail('não deve executar'))
        self.assertEqual(self.store.get(self.task)['status'], 'aguardando')

    def test_verified_result_is_persisted(self):
        events = SimpleNamespace(usage={'input_tokens':100,'cached_input_tokens':80,'output_tokens':5}, message='Concluído')
        result = SimpleNamespace(status='verified', events=events, elapsed_seconds=1)
        execute_next(self.store, lambda *_: result, enabled=True)
        self.assertEqual(self.store.get(self.task)['status'], 'concluído')
        self.assertEqual(self.store.get(self.task)['input_tokens'], 100)
        self.assertEqual(self.store.get(self.task)['cached_input_tokens'], 80)
        row = self.store.list()[0]
        self.assertEqual((row['input_tokens'], row['cached_input_tokens'], row['output_tokens']), (100, 80, 5))
        self.assertEqual(row['elapsed_seconds'], 1)

    def test_cancel_racing_success_requires_review(self):
        events = SimpleNamespace(usage=None, message='Concluído')
        def runner(task, cancelled):
            self.store.cancel(task['id'])
            self.assertTrue(cancelled())
            return SimpleNamespace(status='verified', events=events, elapsed_seconds=1)
        execute_next(self.store, runner, enabled=True)
        self.assertEqual(self.store.get(self.task)['status'], 'aguardando aprovação')

    def test_unconfirmed_process_requires_review(self):
        events = SimpleNamespace(usage=None, message=None)
        result = SimpleNamespace(status='termination_unconfirmed', events=events, elapsed_seconds=1)
        execute_next(self.store, lambda *_: result, enabled=True)
        self.assertEqual(self.store.get(self.task)['status'], 'aguardando aprovação')

    def test_restart_recovery_records_review_event(self):
        self.store.claim(); self.store.start_claimed(self.task)
        TaskStore(self.store.path).recover()
        self.assertEqual(self.store.get(self.task)['status'], 'aguardando aprovação')
        with self.store.connect() as db:
            self.assertIn('aguardando aprovação', [x['event'] for x in db.execute('SELECT event FROM task_events WHERE task_id=?', (self.task,))])

    def test_exception_requires_review_instead_of_retry(self):
        def fail(*_): raise RuntimeError('simulado')
        execute_next(self.store, fail, enabled=True)
        self.assertEqual(self.store.get(self.task)['status'], 'aguardando aprovação')

    def test_task_limits_are_persisted_and_validated(self):
        ident = self.store.submit('Exemplo', 'consulta', timeout_seconds=30, max_input_tokens=25000, max_output_tokens=500)
        task = TaskStore(self.store.path).get(ident)
        self.assertEqual((task['timeout_seconds'], task['max_input_tokens'], task['max_output_tokens']), (30, 25000, 500))
        with self.assertRaises(ValueError): self.store.submit('Exemplo', 'consulta', timeout_seconds=0)

    def test_over_budget_or_missing_usage_never_succeeds(self):
        events = SimpleNamespace(usage={'input_tokens':100001,'cached_input_tokens':0,'output_tokens':5}, message='OK')
        outcome = SimpleNamespace(status='verified', events=events, elapsed_seconds=1)
        execute_next(self.store, lambda *_: outcome, enabled=True)
        self.assertEqual(self.store.get(self.task)['status'], 'aguardando aprovação')

    def test_unknown_usage_never_succeeds(self):
        events = SimpleNamespace(usage=None, message='OK')
        outcome = SimpleNamespace(status='verified', events=events, elapsed_seconds=1)
        execute_next(self.store, lambda *_: outcome, enabled=True)
        self.assertEqual(self.store.get(self.task)['status'], 'aguardando aprovação')
