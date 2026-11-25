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
                CREATE TABLE IF NOT EXISTS task_events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, event TEXT NOT NULL, created TEXT NOT NULL);
            ''')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(tasks)')}
            for name, kind in (('cached_input_tokens', 'INTEGER'), ('elapsed_seconds', 'REAL'),
                               ('timeout_seconds', 'INTEGER NOT NULL DEFAULT 120'),
                               ('max_input_tokens', 'INTEGER NOT NULL DEFAULT 100000'),
                               ('max_output_tokens', 'INTEGER NOT NULL DEFAULT 4000')):
                if name not in columns:
                    db.execute(f'ALTER TABLE tasks ADD COLUMN {name} {kind}')

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

    def submit(self, project, request, *, timeout_seconds=120, max_input_tokens=100000, max_output_tokens=4000):
        p = self.resolve(project)
        if not request.strip() or len(request) > 3000 or SECRET.search(request): raise ValueError('Solicitação vazia, longa ou possivelmente confidencial.')
        if not (isinstance(timeout_seconds, int) and 1 <= timeout_seconds <= 3600 and
                isinstance(max_input_tokens, int) and 1 <= max_input_tokens <= 1000000 and
                isinstance(max_output_tokens, int) and 1 <= max_output_tokens <= 100000):
            raise ValueError('Limites inválidos')
        ident = uuid.uuid4().hex[:12]; date = now()
        with self.connect() as db:
            db.execute('INSERT INTO tasks(id,project,request,status,created,updated,timeout_seconds,max_input_tokens,max_output_tokens) VALUES(?,?,?,?,?,?,?,?,?)',
                       (ident, p['name'], request.strip(), 'aguardando', date, date, timeout_seconds, max_input_tokens, max_output_tokens))
        return ident

    def get(self, ident):
        with self.connect() as db: row = db.execute('SELECT * FROM tasks WHERE id=?', (ident,)).fetchone()
        if not row: raise ValueError('Tarefa não encontrada.')
        return dict(row)

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            active = db.execute("SELECT 1 FROM tasks WHERE status IN ('planejando','executando','testando','aguardando aprovação') LIMIT 1").fetchone()
            if active: return None
            row = db.execute("SELECT * FROM tasks WHERE status='aguardando' ORDER BY created LIMIT 1").fetchone()
            if not row: return None
            db.execute("UPDATE tasks SET status='planejando',updated=? WHERE id=? AND status='aguardando'", (now(), row['id']))
            return dict(row)

    def recover(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT id FROM tasks WHERE status IN ('planejando','executando','testando')").fetchall()
            db.execute("UPDATE tasks SET status='aguardando aprovação',updated=?,result=? WHERE status IN ('planejando','executando','testando')", (now(), 'Interrompida; revisão manual necessária antes de nova execução.'))
            db.executemany('INSERT INTO task_events(task_id,event,created) VALUES(?,?,?)',
                           [(row['id'], 'aguardando aprovação', now()) for row in rows])

    def cancel(self, ident):
        with self.connect() as db:
            row = db.execute('SELECT status FROM tasks WHERE id=?', (ident,)).fetchone()
            if not row: raise ValueError('Tarefa não encontrada.')
            if row['status'] == 'aguardando': db.execute("UPDATE tasks SET status='cancelado',updated=? WHERE id=?", (now(), ident))
            elif row['status'] in ('planejando','executando','testando'): db.execute('UPDATE tasks SET cancel_requested=1,updated=? WHERE id=?', (now(), ident))
            else: raise ValueError('Tarefa não pode ser cancelada neste estado.')

    def list(self, limit=10):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,project,status,created,updated,input_tokens,cached_input_tokens,output_tokens,elapsed_seconds FROM tasks ORDER BY created DESC LIMIT ?', (min(limit, 50),))]

    def update(self, ident, status, result=None, usage=None):
        allowed = {'aguardando', 'planejando', 'executando', 'testando', 'aguardando aprovação', 'concluído', 'cancelado', 'erro'}
        if status not in allowed: raise ValueError('Estado inválido')
        if result and SECRET.search(result): result = 'Resultado omitido por possível dado confidencial.'
        usage = usage or {}
        with self.connect() as db:
            db.execute('UPDATE tasks SET status=?, updated=?, result=?, input_tokens=?, output_tokens=? WHERE id=?',
                       (status, now(), result[:4000] if result else None, usage.get('input_tokens'), usage.get('output_tokens'), ident))

    def start_claimed(self, ident):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status,cancel_requested FROM tasks WHERE id=?', (ident,)).fetchone()
            if not row or row['status'] != 'planejando': return False
            state = 'cancelado' if row['cancel_requested'] else 'executando'
            db.execute('UPDATE tasks SET status=?,updated=? WHERE id=?', (state, now(), ident))
            db.execute('INSERT INTO task_events(task_id,event,created) VALUES(?,?,?)', (ident, state, now()))
            return state == 'executando'

    def finish_running(self, ident, status, result=None, usage=None, elapsed_seconds=None):
        if status not in ('concluído', 'cancelado', 'erro', 'aguardando aprovação'):
            raise ValueError('Estado final inválido')
        if result and SECRET.search(result): result = 'Resultado omitido por possível dado confidencial.'
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status,cancel_requested FROM tasks WHERE id=?', (ident,)).fetchone()
            if not row or row['status'] != 'executando': return False
            if row['cancel_requested'] and status != 'cancelado':
                status = 'aguardando aprovação'
                result = 'Cancelamento concorrente; revisão necessária.'
            usage = usage or {}
            db.execute('UPDATE tasks SET status=?,updated=?,result=?,input_tokens=?,output_tokens=?,cached_input_tokens=?,elapsed_seconds=? WHERE id=?',
                       (status, now(), result[:4000] if result else None, usage.get('input_tokens'), usage.get('output_tokens'), usage.get('cached_input_tokens'), elapsed_seconds, ident))
            db.execute('INSERT INTO task_events(task_id,event,created) VALUES(?,?,?)', (ident, status, now()))
            return True


def default_tasks():
    from .local_vault import local_root
    return TaskStore(local_root() / 'tarefas.sqlite3')
