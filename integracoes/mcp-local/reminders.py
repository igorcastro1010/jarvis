"""Local reminders: fixed actions, persistent scheduling, human approval."""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import re
import sqlite3
import subprocess
import threading
import uuid
from zoneinfo import ZoneInfo

FORTALEZA = ZoneInfo('America/Fortaleza')
log = logging.getLogger('jarvis_local')
FREQUENCIES = {'unico': None, 'diario': timedelta(days=1), 'semanal': timedelta(days=7)}


def parse_time(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?', value):
        raise ValueError('Informe data e hora completas em ISO 8601')
    try: result = datetime.fromisoformat(value)
    except ValueError: raise ValueError('Informe data e hora ISO válidas') from None
    return result.replace(tzinfo=FORTALEZA) if result.tzinfo is None else result.astimezone(FORTALEZA)


def validate(title, due, frequency, now, allow_past=False):
    if not isinstance(title, str) or not title.strip() or len(title) > 300 or any(ord(c) < 32 for c in title):
        raise ValueError('Descrição inválida')
    if frequency not in FREQUENCIES: raise ValueError('Recorrência deve ser unico, diario ou semanal')
    if not isinstance(due, datetime) or due.tzinfo is None: raise ValueError('Data e fuso horário inválidos')
    if not allow_past and due <= now: raise ValueError('O horário precisa estar no futuro')
    return title.strip(), due.astimezone(timezone.utc).isoformat()


def human_confirm(message):
    """Only a real Yes in the local Windows dialog authorizes the change."""
    if not hasattr(ctypes, 'windll'): return False
    try:
        dialog = ctypes.windll.user32.MessageBoxTimeoutW
        dialog.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_ushort, ctypes.c_uint]
        dialog.restype = ctypes.c_int
        # Yes/No, question icon, No as default, topmost; timeout fails closed.
        return dialog(None, message, 'OpenJarvis — confirmar lembrete', 0x00000004 | 0x20 | 0x100 | 0x40000, 0, 60000) == 6
    except (AttributeError, OSError):
        return False


_TOAST_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$item = [Console]::In.ReadToEnd() | ConvertFrom-Json
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$safe = [System.Security.SecurityElement]::Escape([string]$item.text)
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>Lembrete do OpenJarvis</text><text>$safe</text></binding></visual></toast>")
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Microsoft.Windows.PowerShell').Show($toast)
'''


def notify_windows(text):
    import os
    binary = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    proc = subprocess.run([str(binary), '-NoProfile', '-NonInteractive', '-Command', _TOAST_SCRIPT], input=json.dumps({'text':text}, ensure_ascii=True), text=True, capture_output=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if proc.returncode: raise RuntimeError('O Windows não aceitou a notificação')


class ReminderStore:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS reminders(id TEXT PRIMARY KEY, title TEXT NOT NULL, due TEXT NOT NULL, frequency TEXT NOT NULL, active INTEGER NOT NULL, version INTEGER NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS deliveries(reminder_id TEXT NOT NULL, due TEXT NOT NULL, attempted TEXT NOT NULL, status TEXT NOT NULL, PRIMARY KEY(reminder_id,due));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, title, due, frequency, *, now=None, allow_past=False):
        now = now or datetime.now(timezone.utc)
        title, due = validate(title, due, frequency, now, allow_past)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT id FROM reminders WHERE active=1 AND title=? AND due=? AND frequency=?', (title, due, frequency)).fetchone()
            if previous: return {'id': previous['id'], 'ja_existia': True}
            item_id = uuid.uuid4().hex
            db.execute('INSERT INTO reminders VALUES(?,?,?,?,?,?,?)', (item_id,title,due,frequency,1,1,now.astimezone(timezone.utc).isoformat()))
        return {'id':item_id, 'ja_existia':False}

    def list_active(self):
        with self.connect() as db:
            rows = db.execute('SELECT id,title,due,frequency FROM reminders WHERE active=1 ORDER BY due LIMIT 100').fetchall()
        return [{'id':r['id'], 'descricao':r['title'], 'proximo':r['due'], 'horario_fortaleza':datetime.fromisoformat(r['due']).astimezone(FORTALEZA).isoformat(), 'recorrencia':r['frequency']} for r in rows]

    def _current(self, item_id):
        if not isinstance(item_id, str) or not re.fullmatch(r'[0-9a-f]{32}', item_id): raise ValueError('Identificador inválido')
        with self.connect() as db:
            row = db.execute('SELECT * FROM reminders WHERE id=? AND active=1', (item_id,)).fetchone()
        if row is None: raise ValueError('Lembrete ativo não encontrado')
        return dict(row)

    def cancel(self, item_id, confirm=human_confirm):
        row = self._current(item_id)
        due = datetime.fromisoformat(row['due']).astimezone(FORTALEZA).strftime('%d/%m/%Y %H:%M')
        if not confirm(f'Cancelar o lembrete?\n\n{row["title"]}\n{due} (Fortaleza)\nRecorrência: {row["frequency"]}\nIdentificador: {item_id}'):
            return False
        with self.connect() as db:
            cur = db.execute('UPDATE reminders SET active=0, version=version+1 WHERE id=? AND active=1 AND version=?', (item_id,row['version']))
            if cur.rowcount != 1: raise ValueError('O lembrete mudou; solicite confirmação novamente')
        return True

    def update(self, item_id, title, due, frequency, confirm=human_confirm, *, now=None):
        now = now or datetime.now(timezone.utc)
        row = self._current(item_id)
        title, due_utc = validate(title,due,frequency,now)
        local = due.astimezone(FORTALEZA).strftime('%d/%m/%Y %H:%M')
        old_due = datetime.fromisoformat(row['due']).astimezone(FORTALEZA).strftime('%d/%m/%Y %H:%M')
        if not confirm(f'Alterar o lembrete?\n\nAtual: {row["title"]}, {old_due}, {row["frequency"]}\nNovo: {title}, {local}, {frequency}\nHorário de Fortaleza\nIdentificador: {item_id}'):
            return False
        with self.connect() as db:
            cur=db.execute('UPDATE reminders SET title=?,due=?,frequency=?,version=version+1 WHERE id=? AND active=1 AND version=?', (title,due_utc,frequency,item_id,row['version']))
            if cur.rowcount != 1: raise ValueError('O lembrete mudou; solicite confirmação novamente')
        return True

    def dispatch_due(self, now, notify=notify_windows):
        now_utc = now.astimezone(timezone.utc)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute('SELECT * FROM reminders WHERE active=1 AND due<=? ORDER BY due LIMIT 100', (now_utc.isoformat(),)).fetchall()
            claimed = []
            for row in rows:
                due = datetime.fromisoformat(row['due'])
                period = FREQUENCIES[row['frequency']]
                if period:
                    steps = int((now_utc - due) // period) + 1
                    next_due = (due + period * steps).isoformat()
                    db.execute('UPDATE reminders SET due=?,version=version+1 WHERE id=?', (next_due,row['id']))
                else:
                    db.execute('UPDATE reminders SET active=0,version=version+1 WHERE id=?', (row['id'],))
                db.execute('INSERT INTO deliveries VALUES(?,?,?,?)', (row['id'],row['due'],now_utc.isoformat(),'em_envio'))
                claimed.append(dict(row))
        for row in claimed:
            try:
                late = (now_utc - datetime.fromisoformat(row['due'])).total_seconds() > 60
                notify(('Atrasado: ' if late else '') + row['title'])
                status='enviado_ao_windows'
            except Exception:
                status='falha'
                log.warning('Falha ao enviar notificação de lembrete')
            with self.connect() as db:
                db.execute('UPDATE deliveries SET status=? WHERE reminder_id=? AND due=?', (status,row['id'],row['due']))
        return len(claimed)

    def recent_deliveries(self):
        with self.connect() as db:
            rows=db.execute('SELECT d.reminder_id,r.title,d.due,d.attempted,d.status FROM deliveries d JOIN reminders r ON r.id=d.reminder_id ORDER BY d.attempted DESC LIMIT 20').fetchall()
        return [{'id':r['reminder_id'],'descricao':r['title'],'previsto_fortaleza':datetime.fromisoformat(r['due']).astimezone(FORTALEZA).isoformat(),'tentativa_fortaleza':datetime.fromisoformat(r['attempted']).astimezone(FORTALEZA).isoformat(),'status':r['status']} for r in rows]


def start_worker(path):
    store=ReminderStore(path)
    def work():
        while True:
            try: store.dispatch_due(datetime.now(timezone.utc))
            except Exception: log.exception('Falha no processamento de lembretes')
            threading.Event().wait(5)
    threading.Thread(target=work,name='lembretes-locais',daemon=True).start()
    return store
