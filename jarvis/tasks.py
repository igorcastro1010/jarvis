"""Cadastro explícito e fila durável. Nenhuma operação Git é executada aqui."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import uuid
from .memory import SECRET


def now(): return datetime.now(timezone.utc).isoformat()


class TaskStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS projects (name TEXT PRIMARY KEY COLLATE NOCASE, aliases TEXT NOT NULL, path TEXT NOT NULL, github TEXT, allow_write INTEGER NOT NULL DEFAULT 0, allow_push INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, project TEXT NOT NULL, request TEXT NOT NULL, status TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL, result TEXT, input_tokens INTEGER, output_tokens INTEGER, cancel_requested INTEGER NOT NULL DEFAULT 0);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db: yield db
        finally: db.close()

    def register(self, name, aliases, path, github):
        if not name.strip() or len(name) > 80 or any(not a.strip() for a in aliases): raise ValueError('Nome ou alias inválido')
        path = Path(path).resolve(strict=True)
        if not path.is_dir(): raise ValueError('Diretório inválido')
        result = subprocess.run(['git', '-C', str(path), 'rev-parse', '--show-toplevel'], capture_output=True, text=True, encoding='utf8', errors='replace')
        if result.returncode or Path(result.stdout.strip()).resolve() != path: raise ValueError('Informe a raiz de um repositório Git existente.')
        if github:
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', github): raise ValueError('Repositório inválido')
            remote = subprocess.run(['git', '-C', str(path), 'remote', 'get-url', 'origin'], capture_output=True, text=True, encoding='utf8', errors='replace')
            url = remote.stdout.strip().removesuffix('.git').casefold()
            if remote.returncode or url not in (f'https://github.com/{github}'.casefold(), f'git@github.com:{github}'.casefold()):
                raise ValueError('O GitHub informado não corresponde ao origin.')
        with self.connect() as db:
            db.execute('INSERT INTO projects(name,aliases,path,github) VALUES(?,?,?,?)', (name.strip(), json.dumps(aliases, ensure_ascii=False), str(path), github))

    def resolve(self, spoken):
        with self.connect() as db: rows = db.execute('SELECT * FROM projects').fetchall()
        matches = [dict(r) for r in rows if spoken.casefold().strip() in [r['name'].casefold(), *[x.casefold() for x in json.loads(r['aliases'])]]]
        if len(matches) != 1: raise ValueError('Projeto não encontrado ou ambíguo.')
        return matches[0]

    def submit(self, project, request):
        p = self.resolve(project)
        if not request.strip() or len(request) > 3000 or SECRET.search(request): raise ValueError('Solicitação vazia, longa ou possivelmente confidencial.')
        ident = uuid.uuid4().hex[:12]; date = now()
        with self.connect() as db:
            db.execute('INSERT INTO tasks(id,project,request,status,created,updated) VALUES(?,?,?,?,?,?)', (ident, p['name'], request.strip(), 'aguardando', date, date))
        return ident

    def get(self, ident):
        with self.connect() as db: row = db.execute('SELECT * FROM tasks WHERE id=?', (ident,)).fetchone()
        if not row: raise ValueError('Tarefa não encontrada.')
        return dict(row)

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            active = db.execute("SELECT 1 FROM tasks WHERE status IN ('planejando','executando','testando') LIMIT 1").fetchone()
            if active: return None
            row = db.execute("SELECT * FROM tasks WHERE status='aguardando' ORDER BY created LIMIT 1").fetchone()
            if not row: return None
            db.execute("UPDATE tasks SET status='planejando',updated=? WHERE id=? AND status='aguardando'", (now(), row['id']))
            return dict(row)

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE tasks SET status='aguardando aprovação',updated=?,result=? WHERE status IN ('planejando','executando','testando')", (now(), 'Interrompida; revisão manual necessária antes de nova execução.'))

    def cancel(self, ident):
        with self.connect() as db:
            row = db.execute('SELECT status FROM tasks WHERE id=?', (ident,)).fetchone()
            if not row: raise ValueError('Tarefa não encontrada.')
            if row['status'] == 'aguardando': db.execute("UPDATE tasks SET status='cancelado',updated=? WHERE id=?", (now(), ident))
            elif row['status'] in ('planejando','executando','testando'): db.execute('UPDATE tasks SET cancel_requested=1,updated=? WHERE id=?', (now(), ident))
            else: raise ValueError('Tarefa não pode ser cancelada neste estado.')

    def list(self, limit=10):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,project,status,created,updated FROM tasks ORDER BY created DESC LIMIT ?', (min(limit, 50),))]

    def update(self, ident, status, result=None, usage=None):
        allowed = {'aguardando', 'planejando', 'executando', 'testando', 'aguardando aprovação', 'concluído', 'cancelado', 'erro'}
        if status not in allowed: raise ValueError('Estado inválido')
        if result and SECRET.search(result): result = 'Resultado omitido por possível dado confidencial.'
        usage = usage or {}
        with self.connect() as db:
            db.execute('UPDATE tasks SET status=?, updated=?, result=?, input_tokens=?, output_tokens=? WHERE id=?',
                       (status, now(), result[:4000] if result else None, usage.get('input_tokens'), usage.get('output_tokens'), ident))


def default_tasks():
    from .local_vault import local_root
    return TaskStore(local_root() / 'tarefas.sqlite3')
