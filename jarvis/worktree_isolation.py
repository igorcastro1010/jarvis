"""Preparação explícita de worktree; não executa tarefas nem publica alterações."""
from pathlib import Path
import re
import subprocess


def prepare_worktree(repository, worktree_root, task_id):
    if not re.fullmatch(r'[0-9a-f]{12}', task_id): raise ValueError('ID inválido')
    repo = Path(repository).resolve(strict=True)
    root = Path(worktree_root).resolve()
    if root == repo or repo in root.parents or root in repo.parents:
        raise ValueError('Worktree deve estar fora do repositório.')
    if not repo.is_dir() or root == Path(root.anchor): raise ValueError('Diretório inválido')
    check = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--show-toplevel'], capture_output=True, text=True, encoding='utf8', errors='replace')
    if check.returncode or Path(check.stdout.strip()).resolve() != repo: raise ValueError('Informe a raiz de um repositório Git.')
    status = subprocess.run(['git', '-C', str(repo), 'status', '--porcelain'], capture_output=True, text=True, encoding='utf8', errors='replace', check=True)
    if status.stdout.strip(): raise ValueError('Repositório contém alterações locais; preserve-as antes de continuar.')
    root.mkdir(parents=True, exist_ok=True)
    target = root / task_id
    if target.exists() or target.is_symlink(): raise FileExistsError('Destino já existe')
    subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '-b', 'codex/tarefa-'+task_id, str(target), 'HEAD'],
                   check=True, capture_output=True, text=True, encoding='utf8', errors='replace')
    return target
