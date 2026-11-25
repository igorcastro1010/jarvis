import ctypes
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from jarvis.windows_job import JobProcess

class JobTests(unittest.TestCase):
    def test_parent_exit_children_and_grandchildren_are_terminated(self):
        grandchild = 'import time; time.sleep(60)'
        child = "import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c',%r]); print(p.pid,flush=True); time.sleep(60)" % grandchild
        parent = "import subprocess,sys; p=subprocess.Popen([sys.executable,'-u','-c',%r]); print(p.pid,flush=True)" % child
        job = JobProcess.start([sys.executable, '-u', '-c', parent], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            child_pid = int(job.process.stdout.readline())
            grandchild_pid = int(job.process.stdout.readline())
            job.process.wait(timeout=10)
            handles = []
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            try:
                for pid in (child_pid, grandchild_pid):
                    handle = kernel.OpenProcess(0x100000, False, pid)
                    self.assertTrue(handle); handles.append(handle)
                self.assertGreaterEqual(job.active_processes(), 2)
                self.assertTrue(job.terminate(timeout=10))
                for handle in handles: self.assertEqual(kernel.WaitForSingleObject(handle, 10000), 0)
            finally:
                for handle in handles: kernel.CloseHandle(handle)
        finally:
            job.close(); job.process.stdout.close(); job.process.stderr.close()

    def test_failed_assignment_never_runs_program(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'ran'
            with patch('jarvis.windows_job._assign', side_effect=OSError('injected')):
                with self.assertRaises(OSError):
                    JobProcess.start([sys.executable, '-c', "from pathlib import Path; Path(%r).touch()" % str(marker)])
            time.sleep(.2)
            self.assertFalse(marker.exists())


class NestedJobTests(unittest.TestCase):
    def test_nested_job_without_breakaway(self):
        script = "from jarvis.windows_job import JobProcess; import sys; j=JobProcess.start([sys.executable,'-c','import time; time.sleep(30)']); print('nested',flush=True); assert j.terminate(); j.close()"
        job = JobProcess.start([sys.executable, '-u', '-c', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = job.process.communicate(timeout=15)
            self.assertEqual(job.process.returncode, 0, stderr.decode())
            self.assertIn(b'nested', stdout)
            deadline = time.monotonic() + 5
            while job.active_processes() and time.monotonic() < deadline: time.sleep(.02)
            self.assertEqual(job.active_processes(), 0)
        finally:
            job.close()

    def test_close_kills_job_member(self):
        job = JobProcess.start([sys.executable, '-c', 'import time; time.sleep(60)'])
        try:
            self.assertGreaterEqual(job.active_processes(), 1)
            job.close()
            job.process.wait(timeout=10)
            self.assertIsNotNone(job.process.returncode)
        finally:
            job.close()
