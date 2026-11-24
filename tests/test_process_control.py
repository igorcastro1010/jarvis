import subprocess
import ctypes
import sys
import unittest
from jarvis.process_control import stop_process_tree


class ProcessTests(unittest.TestCase):
    def test_already_exited_does_not_claim_tree_was_stopped(self):
        process = subprocess.Popen([sys.executable, '-c', 'pass'])
        process.wait(timeout=10)
        self.assertFalse(stop_process_tree(process))

    def test_cancel_real_process_tree(self):
        script = "import subprocess,sys,time; c=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); print(c.pid,flush=True); time.sleep(60)"
        process = subprocess.Popen([sys.executable, '-u', '-c', script], stdout=subprocess.PIPE, text=True)
        try:
            child = int(process.stdout.readline().strip())
            self.assertGreater(child, 0)
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            handle = kernel.OpenProcess(0x00100000, False, child)
            self.assertTrue(handle)
            self.assertTrue(stop_process_tree(process, timeout=10))
            self.assertIsNotNone(process.poll())
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            self.assertEqual(kernel.WaitForSingleObject(handle, 10000), 0)
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel.CloseHandle(handle)
        finally:
            if process.poll() is None: process.kill()
            process.wait(timeout=10)
            process.stdout.close()
