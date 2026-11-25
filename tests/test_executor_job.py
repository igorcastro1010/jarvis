import sys
import threading
import unittest
from jarvis.codex_process import run_process

class ExecutorJobTests(unittest.TestCase):
    def test_capture_stdout_stderr_and_progress(self):
        progress = []
        script = "import sys,json; print(json.dumps({'type':'progress','message':'andando'}),flush=True); print('erro ficticio',file=sys.stderr,flush=True)"
        result = run_process([sys.executable, '-u', '-c', script], '', timeout=5, progress=progress.append)
        self.assertIn('andando', result.stdout)
        self.assertIn('erro ficticio', result.stderr)
        self.assertTrue(any('andando' in event for event in progress))

    def test_timeout_after_parent_exits_with_descendants(self):
        child = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); time.sleep(60)"
        parent = "import subprocess,sys; subprocess.Popen([sys.executable,'-c',%r]); print('iniciado',flush=True)" % child
        result = run_process([sys.executable, '-u', '-c', parent], '', timeout=1)
        self.assertEqual(result.status, 'timeout')
        self.assertTrue(result.tree_terminated)

    def test_cancellation_after_parent_exit(self):
        child = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); time.sleep(60)"
        parent = "import subprocess,sys; subprocess.Popen([sys.executable,'-c',%r]); print('iniciado',flush=True)" % child
        event = threading.Event(); timer = threading.Timer(1, event.set); timer.start()
        try:
            result = run_process([sys.executable, '-u', '-c', parent], '', timeout=5, cancelled=event.is_set)
            self.assertEqual(result.status, 'cancelled')
            self.assertTrue(result.tree_terminated)
        finally: timer.cancel()

class DisabledAdapterTests(unittest.TestCase):
    def test_real_codex_stays_disabled(self):
        from jarvis.codex_process import CodexCLI
        with unittest.mock.patch('jarvis.codex_process.JobProcess.start', side_effect=AssertionError('must not launch')):
            with self.assertRaises(PermissionError): CodexCLI().run('teste', '.')
