"""Windows Job Object para subprocessos locais, sem alterar o sandbox pai."""
import ctypes
from ctypes import wintypes as w
import os
import subprocess
import time

if os.name != 'nt':
    raise ImportError('Job Objects exigem Windows')

k = ctypes.WinDLL('kernel32', use_last_error=True)
HANDLE = w.HANDLE

def api(name, restype, *args):
    fn = getattr(k, name); fn.restype = restype; fn.argtypes = args
    return fn

create_job = api('CreateJobObjectW', HANDLE, ctypes.c_void_p, w.LPCWSTR)
set_info = api('SetInformationJobObject', w.BOOL, HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD)
query = api('QueryInformationJobObject', w.BOOL, HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p)
_assign = api('AssignProcessToJobObject', w.BOOL, HANDLE, HANDLE)
terminate_job = api('TerminateJobObject', w.BOOL, HANDLE, w.UINT)
close_handle = api('CloseHandle', w.BOOL, HANDLE)
snapshot = api('CreateToolhelp32Snapshot', HANDLE, w.DWORD, w.DWORD)
open_thread = api('OpenThread', HANDLE, w.DWORD, w.BOOL, w.DWORD)
resume = api('ResumeThread', w.DWORD, HANDLE)

class BasicLimits(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
                ('LimitFlags', w.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t), ('MaximumWorkingSetSize', ctypes.c_size_t),
                ('ActiveProcessLimit', w.DWORD), ('Affinity', ctypes.c_size_t), ('PriorityClass', w.DWORD), ('SchedulingClass', w.DWORD)]
class IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
class ExtendedLimits(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', BasicLimits), ('IoInfo', IoCounters), ('ProcessMemoryLimit', ctypes.c_size_t),
                ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]
class Accounting(ctypes.Structure):
    _fields_ = [('TotalUserTime', ctypes.c_longlong), ('TotalKernelTime', ctypes.c_longlong),
                ('ThisPeriodTotalUserTime', ctypes.c_longlong), ('ThisPeriodTotalKernelTime', ctypes.c_longlong),
                ('TotalPageFaultCount', w.DWORD), ('TotalProcesses', w.DWORD), ('ActiveProcesses', w.DWORD), ('TotalTerminatedProcesses', w.DWORD)]
class ThreadEntry(ctypes.Structure):
    _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD), ('th32ThreadID', w.DWORD), ('th32OwnerProcessID', w.DWORD),
                ('tpBasePri', w.LONG), ('tpDeltaPri', w.LONG), ('dwFlags', w.DWORD)]
thread_first = api('Thread32First', w.BOOL, HANDLE, ctypes.POINTER(ThreadEntry))
thread_next = api('Thread32Next', w.BOOL, HANDLE, ctypes.POINTER(ThreadEntry))

def failure():
    return ctypes.WinError(ctypes.get_last_error())

def resume_primary(pid):
    snap = snapshot(4, 0)
    if snap == ctypes.c_void_p(-1).value: raise failure()
    try:
        entry = ThreadEntry(); entry.dwSize = ctypes.sizeof(entry)
        ok = thread_first(snap, ctypes.byref(entry))
        while ok:
            if entry.th32OwnerProcessID == pid:
                thread = open_thread(0x0002, False, entry.th32ThreadID)
                if not thread: raise failure()
                try:
                    if resume(thread) == 0xffffffff: raise failure()
                finally: close_handle(thread)
                return
            ok = thread_next(snap, ctypes.byref(entry))
        raise OSError('Thread primária suspensa não encontrada')
    finally: close_handle(snap)

class JobProcess:
    def __init__(self, handle, process): self.handle, self.process = handle, process

    @classmethod
    def start(cls, argv, **kwargs):
        handle = create_job(None, None)
        if not handle: raise failure()
        process = None
        try:
            limits = ExtendedLimits(); limits.BasicLimitInformation.LimitFlags = 0x2000
            if not set_info(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)): raise failure()
            if 'creationflags' in kwargs: raise ValueError('creationflags não permitido')
            process = subprocess.Popen(argv, creationflags=0x00000004 | subprocess.CREATE_NO_WINDOW, **kwargs)
            if not _assign(handle, int(process._handle)): raise failure()
            resume_primary(process.pid)
            return cls(handle, process)
        except BaseException:
            try:
                if process is not None:
                    try:
                        if process.poll() is None: process.kill()
                        process.wait(timeout=10)
                    finally:
                        for stream in (process.stdin, process.stdout, process.stderr):
                            if stream: stream.close()
            finally:
                close_handle(handle)
            raise

    def active_processes(self):
        info = Accounting()
        if not query(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None): raise failure()
        return info.ActiveProcesses

    def terminate(self, timeout=10):
        if not terminate_job(self.handle, 1): raise failure()
        deadline = time.monotonic() + timeout
        while self.active_processes():
            if time.monotonic() >= deadline: return False
            time.sleep(.02)
        self.process.wait(timeout=max(.1, deadline-time.monotonic()))
        return True

    def close(self):
        if self.handle:
            close_handle(self.handle); self.handle = None
