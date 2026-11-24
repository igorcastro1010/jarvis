"""Executa um subprocesso com eventos JSONL, prazo e verificação independente.

Este módulo é um componente; ele ainda não é ligado à fila de produção.
"""
from dataclasses import dataclass
import json
import os
import queue
import subprocess
import threading
import time
from .codex_events import Budget, CodexEvents
from .process_control import stop_process_tree


@dataclass
class ProcessResult:
    status: str
    events: CodexEvents
    elapsed_seconds: float


def run_process(argv, prompt, *, verifier=None, timeout=120, cancelled=lambda: False, budget=None):
    budget = budget or Budget()
    budget.check_prompt(prompt)
    if timeout <= 0: raise ValueError('Timeout deve ser positivo')
    started = time.monotonic()
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding='utf8', errors='replace', creationflags=flags)
    lines = queue.Queue(maxsize=1024)
    def read_output():
        try:
            for line in process.stdout: lines.put(line)
        finally:
            process.stdout.close()
            lines.put(None)
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        process.stdin.write(prompt)
        process.stdin.close()
        events = CodexEvents(); ended = False; parent_exited = None
        while True:
            try:
                line = lines.get(timeout=0.1)
                if line is None: ended = True
                else:
                    try: events.feed(json.loads(line))
                    except (ValueError, TypeError): pass
            except queue.Empty: pass
            if process.poll() is not None and parent_exited is None:
                parent_exited = time.monotonic()
            if parent_exited is not None and not ended and lines.empty() and time.monotonic() - parent_exited > 0.5:
                return ProcessResult('termination_unconfirmed', events, time.monotonic()-started)
            is_cancelled = cancelled()
            if is_cancelled or time.monotonic() - started >= timeout:
                reason = 'cancelled' if is_cancelled else 'timeout'
                stopped = stop_process_tree(process)
                return ProcessResult(reason if stopped else 'termination_unconfirmed', events, time.monotonic()-started)
            if ended and process.poll() is not None and lines.empty(): break
        verified = bool(verifier and verifier())
        valid = events.success(process.returncode, verified=verified)
        if events.usage is not None and budget.exceeded(events.usage): valid = False
        return ProcessResult('verified' if valid else 'unverified', events, time.monotonic()-started)
    finally:
        if process.poll() is None:
            stop_process_tree(process)
        reader.join(timeout=0.2)
        if not reader.is_alive(): process.stdout.close()
