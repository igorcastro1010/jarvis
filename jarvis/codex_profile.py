"""Geração explícita de perfil MXC; não inicia o Codex."""
import json
from pathlib import Path


def build_profile(workspace, runtime, writable=False):
    try:
        workspace, runtime = Path(workspace).resolve(strict=True), Path(runtime).resolve(strict=True)
    except OSError as exc:
        raise ValueError('Diretórios inexistentes.') from exc
    if not workspace.is_dir() or not runtime.is_dir(): raise ValueError('Diretórios inválidos.')
    if workspace == runtime or workspace in runtime.parents or runtime in workspace.parents:
        raise ValueError('O runtime não pode conter o projeto nem ficar dentro dele.')
    if workspace == Path(workspace.anchor) or runtime == Path(runtime.anchor):
        raise ValueError('Não é permitido conceder acesso à raiz do disco.')
    pairs = {':minimal': 'read', str(workspace): 'write' if writable else 'read', str(runtime): 'read'}
    return 'permissions.jarvis.filesystem={' + ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in pairs.items()) + '}'
