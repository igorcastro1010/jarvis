"""Memória local em Markdown; índice é derivado e não é fonte de verdade."""
import hashlib
import json
import re
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = {'pessoal', 'preferencias', 'projetos', 'decisoes', 'tarefas', 'historico'}
SECRET = re.compile(r'(?i)(senha|password|token|api[ _-]?key|chave privada|private key|bearer\s+\S+|sk-[a-z0-9_-]{12,})')
STOP = {'que', 'para', 'qual', 'uma', 'como', 'sobre', 'com', 'por', 'dos', 'das', 'não', 'uma', 'isso'}


def default_store():
    return MemoryStore(Path(__file__).resolve().parent.parent / 'data' / 'Cofre Jarvis')


def tokens(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))
    return {x for x in re.findall(r'\w+', text) if len(x) > 2 and x not in STOP}


def scope_name(project):
    if project is None or project == '': return 'pessoal'
    if not re.fullmatch(r'[\w -]{1,80}', project, flags=re.UNICODE): raise ValueError('Projeto inválido')
    return 'projeto-' + re.sub(r'\s+', '-', project.strip().casefold())


class MemoryStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.notes = self.root / 'Memoria Jarvis'
        self.notes.mkdir(parents=True, exist_ok=True)
        self.db = self.root / '.jarvis-indice.sqlite3'
        with self.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS notes (path TEXT PRIMARY KEY, stamp INTEGER, size INTEGER, scope TEXT, id TEXT, category TEXT, origin TEXT, date TEXT, content TEXT)')

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db, timeout=10)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _folder(self, project, category):
        if category not in CATEGORIES: raise ValueError('Categoria inválida')
        scope = scope_name(project)
        folder = self.notes / scope / category
        if folder.is_symlink() or folder.parent.is_symlink(): raise ValueError('Links não são permitidos')
        return folder, scope

    def _sync(self):
        with self.connect() as conn:
            prior = {r[0]: (r[1], r[2]) for r in conn.execute('SELECT path, stamp, size FROM notes')}
            seen = set()
            for path in self.notes.glob('*/*/*.md'):
                if path.is_symlink() or path.parent.is_symlink() or path.parent.parent.is_symlink(): continue
                name = str(path.relative_to(self.notes)); seen.add(name)
                stat = path.stat()
                if prior.get(name) == (stat.st_mtime_ns, stat.st_size): continue
                try:
                    raw = path.read_text(encoding='utf-8')
                    header, content = raw.split('\n---\n', 1)
                    meta = json.loads(header.removeprefix('---\n'))
                    if SECRET.search(content) or not re.fullmatch(r'[0-9a-f]{12}', meta['id']): raise ValueError()
                    if meta['scope'] != path.parent.parent.name or meta['category'] != path.parent.name: raise ValueError()
                    conn.execute('INSERT OR REPLACE INTO notes VALUES (?,?,?,?,?,?,?,?,?)',
                                 (name, stat.st_mtime_ns, stat.st_size, meta['scope'], meta['id'], meta['category'], meta['origin'], meta['date'], content.strip()))
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                    conn.execute('DELETE FROM notes WHERE path=?', (name,))
            for removed in set(prior) - seen: conn.execute('DELETE FROM notes WHERE path=?', (removed,))

    def remember(self, content, project=None, category='pessoal', origin='usuario'):
        content = content.strip()
        if not content or len(content) > 4000 or SECRET.search(content) or SECRET.search(origin):
            raise ValueError('Conteúdo vazio, longo ou possivelmente confidencial; não foi salvo.')
        folder, scope = self._folder(project, category)
        self._sync()
        with self.connect() as conn:
            for ident, text in conn.execute('SELECT id, content FROM notes WHERE scope=? AND category=?', (scope, category)):
                if text.casefold().strip() == content.casefold(): return ident
        ident = uuid.uuid4().hex[:12]
        meta = {'id': ident, 'scope': scope, 'category': category, 'origin': origin[:100],
                'date': datetime.now(timezone.utc).isoformat()}
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{ident}.md').write_text('---\n' + json.dumps(meta, ensure_ascii=False) + '\n---\n' + content + '\n', encoding='utf-8')
        return ident

    def search(self, query, project=None, limit=4):
        scope = scope_name(project); terms = tokens(query)
        if not terms: return []
        self._sync()
        with self.connect() as conn:
            rows = conn.execute('SELECT id,category,origin,date,content FROM notes WHERE scope=?', (scope,)).fetchall()
        result = []
        for ident, category, origin, date, content in rows:
            score = len(terms & tokens(content))
            if score: result.append({'id': ident, 'category': category, 'origin': origin, 'date': date, 'content': content, '_score': score})
        result.sort(key=lambda x: (-x['_score'], x['id']))
        for item in result: item.pop('_score')
        return result[:min(max(limit, 0), 10)]

    def _find(self, ident, project):
        if not re.fullmatch(r'[0-9a-f]{12}', ident): raise ValueError('ID inválido')
        scope = scope_name(project); self._sync()
        with self.connect() as conn:
            row = conn.execute('SELECT path FROM notes WHERE id=? AND scope=?', (ident, scope)).fetchone()
        if not row: raise ValueError('Memória não encontrada neste contexto')
        path = self.notes / row[0]
        if path.is_symlink() or path.parent.is_symlink() or path.parent.parent.is_symlink(): raise ValueError('Link não permitido')
        return path

    def forget(self, ident, project=None):
        path = self._find(ident, project)
        archive = self.root / 'Arquivo' / scope_name(project) / path.parent.name
        archive.mkdir(parents=True, exist_ok=True)
        path.replace(archive / f'{ident}-{uuid.uuid4().hex[:8]}.md')
        self._sync()

    def correct(self, ident, content, project=None):
        if not content.strip() or len(content) > 4000 or SECRET.search(content): raise ValueError('Conteúdo inválido ou confidencial')
        path = self._find(ident, project)
        header, _ = path.read_text(encoding='utf8').split('\n---\n', 1)
        old = path.read_text(encoding='utf8')
        archive = self.root / 'Arquivo' / scope_name(project) / path.parent.name
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f'{ident}-{uuid.uuid4().hex[:8]}.md').write_text(old, encoding='utf8')
        temp = path.with_suffix('.tmp')
        temp.write_text(header + '\n---\n' + content.strip() + '\n', encoding='utf8')
        temp.replace(path)
        self._sync()
