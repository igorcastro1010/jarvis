import sys
import threading
import unittest
from jarvis.codex_process import run_process


class CodexProcessTests(unittest.TestCase):
    def test_failure_exit_code_is_preserved_without_output(self):
        result = run_process([sys.executable, '-c', 'raise SystemExit(7)'], '', timeout=10)
        self.assertEqual(result.status, 'unverified')
        self.assertEqual(result.exit_code, 7)
    def test_structured_output_requires_independent_verification(self):
        data = [{'type':'item.completed','item':{'type':'agent_message','text':'pronto'}},
                {'type':'turn.completed','usage':{'input_tokens':20,'cached_input_tokens':5,'output_tokens':3}}]
        script = 'import json; events='+repr(data)+'; [print(json.dumps(e),flush=True) for e in events]'
        result = run_process([sys.executable, '-u', '-c', script], '', verifier=lambda: True, timeout=10)
        self.assertEqual(result.status, 'verified')
        self.assertEqual(result.events.usage['uncached_input_tokens'], 15)
        result = run_process([sys.executable, '-u', '-c', script], '', verifier=lambda: False, timeout=10)
        self.assertEqual(result.status, 'unverified')

    def test_timeout_and_cancellation(self):
        script = 'import time; time.sleep(60)'
        result = run_process([sys.executable, '-u', '-c', script], '', timeout=0.5)
        self.assertEqual(result.status, 'timeout')
        event = threading.Event(); threading.Timer(0.5, event.set).start()
        result = run_process([sys.executable, '-u', '-c', script], '', cancelled=event.is_set, timeout=10)
        self.assertEqual(result.status, 'cancelled')

    def test_parent_exit_does_not_wait_for_inherited_pipe_from_child(self):
        events = [{'type':'item.completed','item':{'type':'agent_message','text':'ok'}},
                  {'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':1}}]
        script = "import subprocess,sys,json; subprocess.Popen([sys.executable,'-c','import time; time.sleep(8)']); events="+repr(events)+"; [print(json.dumps(e),flush=True) for e in events]"
        result = run_process([sys.executable, '-u', '-c', script], '', verifier=lambda: True, timeout=1)
        self.assertEqual(result.status, 'timeout')
        self.assertTrue(result.tree_terminated)
        self.assertLess(result.elapsed_seconds, 5)
