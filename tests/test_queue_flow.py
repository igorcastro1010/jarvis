import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from jarvis.tasks import TaskStore
from jarvis.queue_executor import execute_next
from jarvis.worktree_isolation import prepare_worktree
from jarvis.codex_process import run_process


class FixtureFlowTests(unittest.TestCase):
    def test_fictitious_task_worktree_process_and_independent_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo = root/'repo'; repo.mkdir()
            def git(*args): return subprocess.run(['git','-C',str(repo),*args], check=True, capture_output=True)
            git('init','-q'); git('config','user.name','Teste'); git('config','user.email','test@example.invalid')
            (repo/'nota.txt').write_text('antes',encoding='utf8'); git('add','nota.txt'); git('commit','-qm','inicial')
            store = TaskStore(root/'fila.db'); store.register('Teste', [], repo, None)
            ident = store.submit('Teste', 'Crie resultado fictício')
            def runner(task, cancelled):
                work = prepare_worktree(repo, root/'worktrees', task['id'])
                target = work/'resultado.txt'
                events = [{'type':'item.completed','item':{'type':'agent_message','text':'ok'}},
                          {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':20,'output_tokens':5}}]
                script = "from pathlib import Path; import json; Path("+repr(str(target))+").write_text('feito'); events="+repr(events)+"; [print(json.dumps(e),flush=True) for e in events]"
                return run_process([sys.executable,'-u','-c',script], '', cancelled=cancelled,
                                   verifier=lambda: target.is_file() and target.read_text() == 'feito', timeout=10)
            execute_next(store, runner, enabled=True)
            self.assertEqual(store.get(ident)['status'], 'concluído')
            self.assertFalse((repo/'resultado.txt').exists())
            with store.connect() as db:
                self.assertEqual([r['event'] for r in db.execute('SELECT event FROM task_events WHERE task_id=? ORDER BY id', (ident,))], ['executando','concluído'])

class SimulatedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name); repo = root/'repo'; repo.mkdir()
        subprocess.run(['git','init','-q',str(repo)],check=True)
        self.store = TaskStore(root/'queue.db'); self.store.register('Teste', [], repo, None)
        self.ident = self.store.submit('Teste', 'Pedido de teste ficticio')

    def tearDown(self): self.tmp.cleanup()

    def test_progress_error_and_result_flow(self):
        progress = []; results = []
        events = [{'type':'thread.started','thread_id':'019b0000-0000-7000-8000-000000000001'},
                  {'type':'item.completed','item':{'type':'agent_message','text':'resultado ficticio'}},
                  {'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':2}}]
        script = "import sys,json; print('erro ficticio',file=sys.stderr,flush=True); events="+repr(events)+"; [print(json.dumps(e),flush=True) for e in events]"
        def runner(task, cancelled):
            result = run_process([sys.executable,'-u','-c',script], '', cancelled=cancelled, verifier=lambda: True, timeout=10, progress=progress.append)
            results.append(result); return result
        execute_next(self.store, runner, enabled=True)
        self.assertEqual(self.store.get(self.ident)['status'], 'concluído')
        self.assertIn('erro ficticio', results[0].stderr)
        self.assertTrue(any('resultado ficticio' in line for line in progress))
        self.assertEqual(results[0].events.session_id, '019b0000-0000-7000-8000-000000000001')

    def test_cancel_from_progress_stops_process_and_updates_queue(self):
        results = []
        def progress(line):
            if 'iniciado' in line: self.store.cancel(self.ident)
        def runner(task, cancelled):
            script = "import time; print('iniciado',flush=True); time.sleep(60)"
            result = run_process([sys.executable,'-u','-c',script], '', cancelled=cancelled, timeout=10, progress=progress)
            results.append(result); return result
        execute_next(self.store, runner, enabled=True)
        self.assertEqual(results[0].status, 'cancelled')
        self.assertTrue(results[0].tree_terminated)
        self.assertEqual(self.store.get(self.ident)['status'], 'cancelado')

    def test_failed_subprocess_requires_review_and_preserves_error(self):
        results = []
        def runner(task, cancelled):
            script = "import sys; print('falha ficticia',file=sys.stderr,flush=True); sys.exit(3)"
            result = run_process([sys.executable,'-u','-c',script], '', cancelled=cancelled, timeout=10)
            results.append(result); return result
        execute_next(self.store, runner, enabled=True)
        self.assertEqual(results[0].exit_code, 3)
        self.assertIn('falha ficticia', results[0].stderr)
        self.assertEqual(self.store.get(self.ident)['status'], 'aguardando aprovação')
