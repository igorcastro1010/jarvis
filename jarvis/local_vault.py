"""Migração aditiva do cofre: nunca apaga nem sobrescreve o original."""
import os
from pathlib import Path
import shutil
import uuid


def local_root():
    base = os.environ.get('JARVIS_LOCAL_DIR') or str(Path(os.environ['USERPROFILE']) / 'JarvisLocal')
    path = Path(base).expanduser().resolve()
    if str(path).startswith('\\\\'):
        raise ValueError('O diretório local não pode ser uma unidade de rede.')
    for key in ('OneDrive', 'OneDriveConsumer', 'OneDriveCommercial'):
        root = os.environ.get(key)
        if root:
            sync = Path(root).resolve()
            if path == sync or sync in path.parents:
                raise ValueError('Escolha um diretório fora do OneDrive.')
    return path


def migrate_vault(source, dest):
    source, dest = Path(source).resolve(), Path(dest).resolve()
    if source == dest or source in dest.parents or dest in source.parents:
        raise ValueError('Origem e destino não podem se conter.')
    if dest.exists(): return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.parent / (dest.name + '.migracao-' + uuid.uuid4().hex[:8])
    if source.exists():
        for path in source.rglob('*'):
            if path.is_symlink(): raise ValueError('O cofre contém links; migração automática suspensa.')
        shutil.copytree(source, temp, ignore=shutil.ignore_patterns('*.sqlite3', '*.sqlite3-*', '.obsidian'))
    else:
        temp.mkdir()
    temp.rename(dest)
    return True


def get_vault():
    dest = local_root() / 'Cofre Jarvis'
    prior = Path(os.environ.get('LOCALAPPDATA', '')) / 'Jarvis' / 'Cofre Jarvis'
    source = prior if prior.is_dir() else Path(__file__).resolve().parent.parent / 'data' / 'Cofre Jarvis'
    migrate_vault(source, dest)
    return dest
