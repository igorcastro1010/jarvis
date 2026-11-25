"""Persistent preparation only; no executor or approval bypass exists here."""
import re
import hashlib
import json
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
            db.execute('''CREATE TABLE IF NOT EXISTS task_events
                (seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, state TEXT NOT NULL, timestamp TEXT NOT NULL)''')
            db.execute("INSERT INTO task_events(task_id,state,timestamp) SELECT id,'revisao_necessaria',? FROM tasks WHERE state='executando'", (self.now(),))
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
            db.execute('INSERT INTO task_events(task_id,state,timestamp) VALUES (?,?,?)', (row[0], row[3], now))
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

    def request_approval(self, item_id):
        self.get(item_id)
        return {'confirmado': False, 'resultado': 'Aprovação indisponível: confirmação humana física e isolamento ainda não homologados.'}

    def approval_fingerprint(self, item_id):
        task = self.get(item_id)
        payload = json.dumps([task['id'], task['projeto'], task['solicitacao']], ensure_ascii=False, separators=(',', ':'))
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def transition(self, item_id, state):
        allowed = {'aguardando_aprovacao': {'aprovado', 'cancelado'}, 'aprovado': {'executando', 'cancelado'}, 'executando': {'concluido', 'falhou', 'cancelado', 'revisao_necessaria'}}
        self.get(item_id)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT state FROM tasks WHERE id=?', (item_id,)).fetchone()[0]
            if state not in allowed.get(old, set()): raise ValueError('Transição inválida')
            now = self.now()
            db.execute('UPDATE tasks SET state=?,updated_at=? WHERE id=?', (state, now, item_id))
            db.execute('INSERT INTO task_events(task_id,state,timestamp) VALUES (?,?,?)', (item_id, state, now))
        return self.get(item_id)

    def cancel(self, item_id):
        if self.get(item_id)['estado'] != 'aguardando_aprovacao': raise ValueError('Cancelamento indisponível neste estado')
        return self.transition(item_id, 'cancelado')

    def events(self, item_id):
        self.get(item_id)
        with self.connect() as db:
            return [{'estado': state, 'data': timestamp} for state, timestamp in db.execute('SELECT state,timestamp FROM task_events WHERE task_id=? ORDER BY seq', (item_id,))]
