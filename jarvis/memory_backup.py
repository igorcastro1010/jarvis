"""Cópias locais restauradas apenas em diretório novo, sem sobrescrita."""
import argparse
from pathlib import Path, PurePosixPath
import stat
import zipfile


def backup(vault, target):
    vault, target = Path(vault).resolve(), Path(target).resolve()
    if not vault.is_dir() or vault in target.parents:
        raise ValueError('Cofre inexistente ou backup dentro do cofre')
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in vault.rglob('*'):
            if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents if p != vault): continue
            if path.suffix.lower() in ('.sqlite3', '.sqlite', '.db') or '.obsidian' in path.parts: continue
            archive.write(path, path.relative_to(vault).as_posix())


def restore(archive, destination):
    destination = Path(destination).resolve()
    if destination.exists(): raise FileExistsError('Destino já existe; nenhuma substituição realizada.')
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if len(entries) > 10000 or sum(x.file_size for x in entries) > 1_000_000_000:
            raise ValueError('Backup excede limites de segurança')
        names = set()
        for item in entries:
            name = item.filename
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or
                stat.S_ISLNK(item.external_attr >> 16) or name.casefold() in names):
                raise ValueError('Caminho inseguro no backup')
            names.add(name.casefold())
        destination.mkdir(parents=True)
        for item in entries:
            target = destination.joinpath(*PurePosixPath(item.filename).parts)
            if item.is_dir(): target.mkdir(parents=True, exist_ok=True); continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as source, target.open('xb') as output:
                while chunk := source.read(1024 * 1024): output.write(chunk)


def main():
    parser = argparse.ArgumentParser(description='Backup local do cofre Jarvis')
    parser.add_argument('acao', choices=['backup', 'restaurar'])
    parser.add_argument('origem')
    parser.add_argument('destino')
    args = parser.parse_args()
    (backup if args.acao == 'backup' else restore)(args.origem, args.destino)
    print('Operação concluída.')


if __name__ == '__main__': main()
