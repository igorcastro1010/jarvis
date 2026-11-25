"""Executor independente: o chamador deve fornecer apenas processos de teste.

Não ligado à fila; a execução real do Codex continua desativada.
"""
from dataclasses import dataclass
import json
import queue
import subprocess
import threading
import time
from .codex_events import Budget, CodexEvents
from .windows_job import JobProcess

@dataclass
class ProcessResult:
    status: str
    events: CodexEvents
    elapsed_seconds: float
    exit_code: int | None = None
    stdout: str = ''
    stderr: str = ''
    tree_terminated: bool = False


def run_process(argv, prompt, *, verifier=None, timeout=120, cancelled=lambda: False, budget=None, progress=None):
    budget = budget or Budget(); budget.check_prompt(prompt)
    if timeout <= 0: raise ValueError('Timeout deve ser positivo')
    started = time.monotonic()
    job = JobProcess.start(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, encoding='utf8', errors='replace')
    process = job.process
    lines = queue.Queue(); output = {'stdout': [], 'stderr': []}; events = CodexEvents()
    def read(name, stream):
        try:
            for line in stream: lines.put((name, line))
        finally:
            stream.close(); lines.put((name, None))
    def write():
        try:
            process.stdin.write(prompt); process.stdin.close()
        except (OSError, ValueError): pass
    threads = [threading.Thread(target=read, args=(name, stream), daemon=True)
               for name, stream in [('stdout', process.stdout), ('stderr', process.stderr)]]
    threads.append(threading.Thread(target=write, daemon=True))
    for thread in threads: thread.start()
    ended = set(); status = None; terminated = False
    def collect(name, line):
        if line is None: ended.add(name); return
        output[name].append(line)
        if name == 'stdout':
            try: events.feed(json.loads(line))
            except (ValueError, TypeError, AttributeError): pass
        if progress: progress(line)
    try:
        while True:
            try: collect(*lines.get(timeout=.05))
            except queue.Empty: pass
            if process.poll() is not None and job.active_processes() == 0 and len(ended) == 2 and lines.empty():
                terminated = True; break
            reason = 'cancelled' if cancelled() else 'timeout' if time.monotonic() - started >= timeout else None
            if reason:
                try: terminated = job.terminate(timeout=10)
                except (OSError, subprocess.TimeoutExpired): terminated = False
                status = reason if terminated else 'termination_unconfirmed'
                break
        for thread in threads: thread.join(timeout=.5)
        while not lines.empty(): collect(*lines.get_nowait())
        if status is None:
            verified = bool(verifier and verifier())
            valid = events.success(process.returncode, verified=verified)
            if events.usage is not None and budget.exceeded(events.usage): valid = False
            status = 'verified' if valid else 'unverified'
        return ProcessResult(status, events, time.monotonic()-started, process.poll(),
                             ''.join(output['stdout']), ''.join(output['stderr']), terminated)
    finally:
        job.close()

class CodexCLI:
    """Reserva para integração futura; nenhuma execução real está habilitada."""
    def run(self, prompt, cwd):
        raise PermissionError('Codex CLI desativado até homologação e autorização operacional')
