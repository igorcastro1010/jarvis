"""Validação preliminar de cópia candidata; não cria nem executa processos."""
import os
from pathlib import Path
import stat


def _no_redirect(path):
    info=path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & 0x400:
        raise ValueError('Links e pontos de reparação não são permitidos')
    return info


def prepare_copy_plan(source, copy):
    source=Path(source).absolute(); copy=Path(copy).absolute()
    for path in (source,copy):
        for parent in (path,*path.parents): _no_redirect(parent)
        if not path.is_dir(): raise ValueError('Diretório inválido')
    source=source.resolve(); copy=copy.resolve()
    if source==copy or source in copy.parents or copy in source.parents:
        raise ValueError('A cópia deve ser separada da origem')
    def fail(error): raise error
    for folder,dirs,files in os.walk(copy, followlinks=False, onerror=fail):
        for name in dirs+files:
            path=Path(folder)/name; info=_no_redirect(path)
            if name in files and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
                raise ValueError('Arquivo não regular ou com hard links')
    return {'origem':str(source),'copia':str(copy),'execucao_habilitada':False,
            'isolamento':'nao_homologado'}
