"""Persistent preparation only; no executor or approval bypass exists here."""
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


class TaskQueue:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS tasks
                (id TEXT PRIMARY KEY, project TEXT NOT NULL, description TEXT NOT NULL,
                 state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
            db.execute("UPDATE tasks SET state='revisao_necessaria', updated_at=? WHERE state='executando'", (self.now(),))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat(timespec='seconds')

    @staticmethod
    def item(row):
        return dict(zip(('id', 'projeto', 'solicitacao', 'estado', 'criado_em', 'atualizado_em'), row))

    def create(self, project, description):
        if not isinstance(project, str) or project.strip().casefold() not in ('racha fortalaka', 'fortalaka'):
            raise ValueError('Projeto não autorizado')
        if not isinstance(description, str) or not 8 <= len(description.strip()) <= 2000:
            raise ValueError('Descrição deve ter entre 8 e 2000 caracteres')
        description = description.strip()
        if re.search(r'(?i)(?:senha|password|api[_ -]?key|token)\s*[:=]|\b(?:sk-|ghp_|github_pat_)|-----BEGIN .*PRIVATE KEY-----', description):
            raise ValueError('Não inclua credenciais na solicitação')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM tasks WHERE project=? AND description=? AND state='aguardando_aprovacao'", ('Racha Fortalaka', description)).fetchone()
            if row:
                return {**self.item(row), 'ja_existia': True}
            now = self.now()
            row = (uuid.uuid4().hex, 'Racha Fortalaka', description, 'aguardando_aprovacao', now, now)
            db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?)', row)
        return {**self.item(row), 'ja_existia': False}

    def get(self, item_id):
        if not isinstance(item_id, str) or not re.fullmatch(r'[0-9a-f]{32}', item_id):
            raise ValueError('Identificador inválido')
        with self.connect() as db:
            row = db.execute('SELECT * FROM tasks WHERE id=?', (item_id,)).fetchone()
        if row is None: raise ValueError('Tarefa não encontrada')
        return self.item(row)

    def list(self):
        with self.connect() as db:
            return [self.item(row) for row in db.execute('SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50')]

    def request_execution(self, item_id):
        self.get(item_id)
        return {'confirmado': False, 'estado': 'desativado', 'resultado': 'Codex não iniciado: confirmação humana física e isolamento ainda não homologados.'}
