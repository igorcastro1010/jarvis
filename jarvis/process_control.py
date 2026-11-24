"""Cancelamento de processo iniciado pelo próprio Jarvis no Windows."""
import os
import subprocess


def stop_process_tree(process, timeout=10):
    if process.poll() is not None: return True
    if os.name != 'nt': raise OSError('Cancelamento de árvore não implementado nesta plataforma.')
    result = subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'],
                            capture_output=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0 and process.poll() is not None
