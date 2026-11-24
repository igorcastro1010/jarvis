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
