"""Ferramentas de escopo fixo. Nunca executa comandos ditados ou gerados pelo modelo."""
from datetime import datetime
import ctypes
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
import webbrowser
from contextlib import closing

from .public_web import search_web, weather

SITES = {'youtube': 'https://www.youtube.com/', 'chatgpt': 'https://chatgpt.com/', 'github': 'https://github.com/'}
VOLUMES = {'aumentar volume': 'up', 'diminuir volume': 'down', 'silenciar volume': 'mute'}
SUGGESTIONS = ('abrir youtube', 'abrir chatgpt', 'abrir github', 'abrir chrome', 'abrir obsidian',
               'abrir vs code', 'abrir codex', 'clima em fortaleza', 'recursos do sistema',
               'aumentar volume', 'diminuir volume', 'silenciar volume', 'capturar tela')
TOOLS = {'sites': 'Destinos fixos YouTube, ChatGPT e GitHub', 'aplicativos': 'Somente aplicativos permitidos',
         'projetos': 'Somente projetos cadastrados', 'clima': 'Open-Meteo para Fortaleza',
         'pesquisa': 'Busca pública na Wikipédia', 'sistema': 'CPU, RAM e armazenamento',
         'volume': 'Confirmação necessária', 'captura': 'Confirmação necessária'}


def is_automation_request(message):
    return bool(re.match(r'^(?:abrir|abra|localizar|encontrar|pesquisar na internet|pesquise na internet|pesquisar na wikipedia|pesquise na wikipedia|qual o clima|como está o clima|clima|qual a previsão do tempo|previsão do tempo|definir cidade|configurar cidade|aumentar volume|diminuir volume|silenciar volume|capturar tela|capturar screenshot|tirar screenshot|recursos do sistema|uso do sistema|uso de cpu e memória|confirmar|cancelar ação)(?:\s|$|[?.!])', message.strip(), re.I))


def suggest_command(request, model):
    from .memory import SECRET
    if not request.strip() or len(request) > 300 or SECRET.search(request):
        raise ValueError('Pedido inválido ou confidencial')
    prompt = [{'role': 'system', 'content': 'Escolha exatamente um comando da lista ou responda desconhecido. Não execute ações. Lista: ' + ', '.join(SUGGESTIONS)},
              {'role': 'user', 'content': request}]
    suggestion = str(model(prompt)).strip().casefold()
    if suggestion not in SUGGESTIONS:
        return 'Não consegui identificar um comando permitido. Nenhuma ação foi executada.'
    return f'Sugestão: diga “{suggestion}” para solicitar. Nenhuma ação foi executada.'


class Automation:
    def __init__(self, root, clock=time.monotonic):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'automacoes.sqlite3'
        if self.path.is_symlink() or self.path.is_junction(): raise ValueError('Histórico inválido')
        self.clock = clock
        self.pending = None
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS events (created TEXT, action TEXT, status TEXT)')

    def log(self, action, status):
        with closing(sqlite3.connect(self.path, timeout=0.1)) as db, db:
            db.execute('INSERT INTO events VALUES (?, ?, ?)', (datetime.now().astimezone().isoformat(timespec='seconds'), action, status))

    def history(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            return db.execute('SELECT created,action,status FROM events ORDER BY rowid DESC LIMIT 30').fetchall()

    def reset(self):
        pending, self.pending = self.pending, None
        if pending:
            try: self.log(pending[0], 'cancelado')
            except sqlite3.Error: pass

    def _request(self, action, value, label):
        self.log(action, 'aguardando confirmação')
        self.pending = (action, value, self.clock() + 60)
        return f'Confirmar {label}? Diga confirmar ou cancelar ação em até 60 segundos.'

    def handle(self, message):
        text = message.strip().casefold().rstrip('?.!')
        if text == 'cancelar ação':
            self.reset()
            return 'Ação cancelada.'
        if text == 'confirmar':
            pending, self.pending = self.pending, None
            if not pending: return 'Não há nada aguardando confirmação.'
            if self.clock() > pending[2]:
                self.log(pending[0], 'expirado')
                return 'Não há nada aguardando confirmação.'
            action, value, _ = pending
            return self._run(action, lambda: self._volume(value) if action == 'volume' else self._screenshot())
        self.reset()
        if text in VOLUMES: return self._request('volume', VOLUMES[text], text)
        if text in ('capturar tela', 'capturar screenshot', 'tirar screenshot'):
            return self._request('captura', None, 'captura da tela')
        if text in ('definir cidade fortaleza', 'configurar cidade fortaleza'):
            return self._run('cidade', self._set_city)
        if text in ('qual o clima', 'como está o clima', 'clima', 'clima em fortaleza', 'como está o clima em fortaleza'):
            city = self.root / 'cidade.json'
            configured = False
            if city.is_file() and not city.is_symlink():
                try: configured = json.loads(city.read_text(encoding='utf8')).get('cidade') == 'Fortaleza'
                except (OSError, ValueError, AttributeError): pass
            if 'fortaleza' not in text and not configured: return 'Informe Fortaleza ou configure uma cidade padrão.'
            return self._run('clima', weather)
        if text.startswith(('clima', 'qual o clima', 'como está o clima', 'previsão do tempo', 'qual a previsão do tempo')):
            if text.endswith('em fortaleza'): return self._run('clima', weather)
            return 'Por enquanto, só posso consultar clima para Fortaleza. Informe a cidade explicitamente.'
        match = re.fullmatch(r'(?:pesquisar na internet|pesquise na internet|pesquisar na wikipedia|pesquise na wikipedia)\s+(.+)', message.strip(), re.I)
        if match:
            from .memory import SECRET
            if SECRET.search(match.group(1)): return 'Consulta possivelmente confidencial não enviada.'
            return self._run('pesquisa', lambda: search_web(match.group(1)))
        if text in ('recursos do sistema', 'uso do sistema', 'uso de cpu e memória'):
            return self._run('sistema', self._system)
        match = re.fullmatch(r'(?:abrir|abra) projeto\s+([^:]{1,80})', message.strip(), re.I)
        if match: return self._run('projeto', lambda: self._project(match.group(1)))
        match = re.fullmatch(r'(?:localizar|encontrar) (?:arquivo|pasta) (.+?) (?:no|em) projeto ([^:]{1,80})', message.strip(), re.I)
        if match: return self._run('busca local', lambda: self._find(match.group(1), match.group(2)))
        match = re.fullmatch(r'(?:abrir|abra)\s+(.+)', text)
        if match:
            name = match.group(1)
            if name in SITES: return self._run('site', lambda: self._site(name))
            if name in ('chrome', 'obsidian', 'vs code', 'vscode', 'codex'):
                return self._run('aplicativo', lambda: self._app(name))
            return 'Aplicativo ou site não permitido; informe um nome da lista.'
        return None

    def _run(self, action, function):
        try:
            self.log(action, 'iniciado')
        except sqlite3.Error:
            return 'Registro indisponível; nenhuma ação foi iniciada.'
        try:
            result = function()
        except Exception:
            try: self.log(action, 'erro')
            except sqlite3.Error: pass
            return f'{action.capitalize()} indisponível ou não pôde ser concluído.'
        try:
            self.log(action, 'concluído')
        except sqlite3.Error:
            return result + ' Não foi possível atualizar o histórico.'
        return result

    def _set_city(self):
        target = self.root / 'cidade.json'
        if target.is_symlink() or target.is_junction(): raise ValueError('Configuração inválida')
        temp = self.root / ('cidade-' + uuid.uuid4().hex + '.tmp')
        with temp.open('x', encoding='utf8') as output: json.dump({'cidade': 'Fortaleza'}, output)
        temp.replace(target)
        return 'Fortaleza definida como cidade padrão.'

    def _site(self, name):
        if not webbrowser.open(SITES[name]): raise OSError('Navegador indisponível')
        return f'Solicitei a abertura de {name} no navegador.'

    def _app(self, name):
        if name == 'codex' and os.name == 'nt':
            os.startfile('shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App')
            return 'Solicitei a abertura do Codex instalado para Windows.'
        local = Path(os.environ['LOCALAPPDATA'])
        program = Path(os.environ['PROGRAMFILES'])
        if not local.is_absolute() or not program.is_absolute(): raise ValueError('Diretórios do sistema inválidos')
        candidates = {'chrome': [program / 'Google/Chrome/Application/chrome.exe', local / 'Google/Chrome/Application/chrome.exe'],
                      'obsidian': [local / 'Programs/Obsidian/Obsidian.exe'],
                      'vs code': [local / 'Programs/Microsoft VS Code/Code.exe'],
                      'vscode': [local / 'Programs/Microsoft VS Code/Code.exe'],
                      'codex': [local / 'OpenAI/Codex/Codex.exe']}
        path = next((p for p in candidates[name] if p.is_file()), None)
        if path is None: raise OSError('Aplicativo não encontrado')
        os.startfile(str(path))
        return f'Solicitei a abertura de {name}.'

    def _project(self, name):
        from .tasks import default_tasks
        path = Path(default_tasks().resolve(name.strip())['path']).resolve(strict=True)
        if not path.is_dir() or str(path).startswith('\\\\'): raise ValueError('Projeto inválido')
        os.startfile(str(path))
        return 'Solicitei a abertura da pasta do projeto cadastrado.'

    def _find(self, query, project):
        from .tasks import default_tasks
        if not re.fullmatch(r'[\w .-]{2,80}', query, re.UNICODE) or query.startswith('.'):
            raise ValueError('Nome inválido')
        root = Path(default_tasks().resolve(project.strip())['path']).resolve(strict=True)
        if not root.is_dir() or str(root).startswith('\\\\'): raise ValueError('Diretório inválido')
        matches, seen = [], 0
        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith('.') and not re.search(r'(?i)(senha|segred|secret|token|credential|credencial|password|privad|private)', d)
                       and not (Path(current) / d).is_symlink() and not (Path(current) / d).is_junction()]
            for name in dirs + files:
                seen += 1
                if seen > 5000: break
                if name.startswith('.') or re.search(r'(?i)(senha|segred|secret|token|credential|credencial|password|privad|private|\.(pem|key|pfx|p12|kdbx)$)', name): continue
                candidate = Path(current) / name
                if not candidate.is_symlink() and not candidate.is_junction() and query.casefold() in name.casefold(): matches.append(str(candidate.relative_to(root)))
                if len(matches) >= 10: break
            if len(matches) >= 10 or seen > 5000: break
        return 'Resultados no projeto:\n' + ('\n'.join(matches) if matches else 'Nenhum encontrado.')

    def _system(self):
        import psutil
        cpu, ram = psutil.cpu_percent(interval=0.2), psutil.virtual_memory().percent
        disk = psutil.disk_usage(str(self.root.anchor or self.root)).percent
        return f'CPU: {cpu:.0f}%; RAM: {ram:.0f}%; armazenamento: {disk:.0f}%. GPU: medição indisponível.'

    def _volume(self, direction):
        if os.name != 'nt': raise OSError('Windows necessário')
        key = {'up': 0xAF, 'down': 0xAE, 'mute': 0xAD}[direction]
        ctypes.windll.user32.keybd_event(key, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key, 0, 2, 0)
        return 'Comando de volume enviado ao Windows.'

    def _screenshot(self):
        from PIL import ImageGrab
        folder = self.root / 'capturas'
        if folder.is_symlink() or folder.is_junction(): raise ValueError('Destino inválido')
        folder.mkdir(exist_ok=True)
        name = folder / ('captura-' + uuid.uuid4().hex + '.png')
        image = ImageGrab.grab(all_screens=True)
        with name.open('xb') as output: image.save(output, format='PNG')
        return f'Captura salva em {name}.'


def default_automation():
    from .local_vault import local_root
    return Automation(local_root())
