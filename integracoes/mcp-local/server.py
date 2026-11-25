"""Restrained local tools, served via OpenJarvis's own MCP implementation."""
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

import psutil
from openjarvis.core.types import ToolResult
from openjarvis.mcp.protocol import MCPRequest
from openjarvis.mcp.server import MCPServer
from openjarvis.tools._stubs import BaseTool, ToolSpec

HERE = Path(__file__).resolve().parent
CONFIG = HERE / 'autorizados.json'
VAULT = Path.home() / 'Documents' / 'Codex' / 'Preservacao-Jarvis-20261125' / 'data' / 'Cofre Jarvis'
APP_PATHS = {
    'chrome': Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Google/Chrome/Application/chrome.exe',
    'visual studio code': Path(os.environ['LOCALAPPDATA']) / 'Programs/Microsoft VS Code/Code.exe',
    'bloco de notas': Path(os.environ['SystemRoot']) / 'System32/notepad.exe',
    'obsidian': Path(os.environ['LOCALAPPDATA']) / 'Programs/Obsidian/Obsidian.exe',
}
HABBLAUD_DIR = Path.home() / 'Documents/Codex/Habblaud-oficial'
log = logging.getLogger('jarvis_local')
log.setLevel(logging.INFO)
handler = RotatingFileHandler(HERE / 'acoes.log', maxBytes=250_000, backupCount=2, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
log.addHandler(handler)


def config():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def no_links(path):
    path = Path(os.path.abspath(path))
    for p in (path, *path.parents):
        if p.exists() and (p.is_symlink() or getattr(p, 'is_junction', lambda: False)()):
            raise ValueError('Links e junções não são permitidos')
    return path


def project(name):
    projects = config().get('projetos', {})
    if not isinstance(name, str) or name not in projects:
        raise ValueError('Projeto não autorizado')
    root = no_links(projects[name])
    dotgit = no_links(root / '.git')
    if not root.is_dir() or not dotgit.is_dir():
        raise ValueError('Projeto inválido ou worktree não permitido')
    for current, dirs, files in os.walk(dotgit, followlinks=False):
        for child in dirs + files:
            no_links(Path(current) / child)
    if (dotgit / 'objects' / 'info' / 'alternates').exists():
        raise ValueError('Repositório com objetos externos não permitido')
    # Include directives can make git read configuration outside the project.
    gitconfig = no_links(dotgit / 'config')
    text = gitconfig.read_text(encoding='utf-8', errors='replace') if gitconfig.exists() else ''
    if re.search(r'^\s*\[\s*include(?:if)?(?:\s|\])|^\s*worktree\s*=', text, re.I | re.M):
        raise ValueError('Configuração Git com include não permitida')
    return root


def git_query(name, kind):
    root = project(name)
    cmd = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false', '-c', 'core.attributesFile='+os.devnull, '-c', 'core.excludesFile='+os.devnull, '-c', 'core.hooksPath='+os.devnull]
    cmd += ['status', '--porcelain=v1', '--untracked-files=normal', '--ignore-submodules=all'] if kind == 'status' else ['log', '-10', '--format=%h %ad %s', '--date=short', '--no-show-signature']
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0', GIT_PAGER='cat', GIT_NO_REPLACE_OBJECTS='1')
    out = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if out.returncode:
        raise ValueError('Consulta Git não concluída')
    return out.stdout[:16000] or '(sem alterações)'


def metrics():
    ram = psutil.virtual_memory()
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            d = psutil.disk_usage(part.mountpoint)
            disks.append({'unidade': part.mountpoint, 'total_bytes': d.total, 'livre_bytes': d.free})
        except (OSError, PermissionError):
            pass
    try:
        r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', 'Get-CimInstance Win32_VideoController | Select-Object Name | ConvertTo-Json -Compress'], capture_output=True, text=True, timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        gpu = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        gpu = None
    return {'cpu_percent': psutil.cpu_percent(interval=0.2), 'ram_total_bytes': ram.total, 'ram_disponivel_bytes': ram.available, 'gpu': gpu, 'gpu_uso_percent': None, 'vram_uso_bytes': None, 'armazenamento': disks}


def search_memories(query):
    from openjarvis.security.file_policy import is_sensitive_file
    if not isinstance(query, str) or len(query.strip()) < 3 or len(query) > 100:
        raise ValueError('Informe uma consulta entre 3 e 100 caracteres')
    root = no_links(VAULT)
    if not root.is_dir(): raise ValueError('Cofre autorizado indisponível')
    words = [w.casefold() for w in re.findall(r'\w+', query) if len(w) >= 3][:8]
    if not words: raise ValueError('Consulta muito curta')
    found = []
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not (Path(current)/d).is_symlink() and not getattr(Path(current)/d, 'is_junction', lambda: False)()]
        for filename in files:
            path = Path(current) / filename
            if filename.startswith('.') or path.suffix.lower() != '.md' or is_sensitive_file(path): continue
            try:
                no_links(path)
                if path.stat().st_size > 200_000: continue
                text = path.read_text(encoding='utf-8', errors='replace')
                for line in text.splitlines():
                    low = line.casefold()
                    if all(w in low for w in words) and not re.search(r'(?i)(api.?key|token|password|senha|secret|credencial|private.key)', line):
                        found.append({'origem': str(path.relative_to(root)), 'trecho': line[:400]})
                        break
            except (OSError, ValueError): continue
            if len(found) >= 5: return {'resultados': found}
    return {'resultados': found}


def open_habblaud():
    url = 'http://127.0.0.1:4747'
    try:
        with urllib.request.urlopen(url + '/api/health', timeout=2) as response:
            healthy = response.status == 200 and isinstance(json.load(response), dict)
    except (OSError, ValueError): healthy = False
    if not healthy:
        node = no_links(Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'nodejs/node.exe')
        script = no_links(HABBLAUD_DIR / 'dist/server/index.js')
        if not node.is_file() or not script.is_file(): raise ValueError('Habblaud oficial não encontrado')
        env = os.environ.copy()
        env.update(HABBLAUD_HOST='127.0.0.1', HABBLAUD_TERMINAL='0', HABBLAUD_MENSAGENS='0', HABBLAUD_UPDATE_CHECK='0')
        subprocess.Popen([str(node), str(script)], cwd=str(HABBLAUD_DIR), env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    os.startfile(url)
    return {'resultado': 'Abertura solicitada', 'aplicativo': 'habblaud', 'servidor_ja_ativo': healthy}


def run(name, args):
    if name == 'local_metricas': return metrics()
    if name == 'local_projetos': return {'projetos': list(config().get('projetos', {}))}
    if name == 'local_memorias': return search_memories(args.get('consulta'))
    if name in ('local_git_status', 'local_git_historico'):
        return {'resultado': git_query(args.get('projeto'), 'status' if name.endswith('status') else 'log')}
    if name == 'local_abrir_aplicativo':
        app = args.get('aplicativo')
        if app == 'habblaud': return open_habblaud()
        if not isinstance(app, str) or app not in APP_PATHS: raise ValueError('Aplicativo não autorizado')
        target = no_links(APP_PATHS[app])
        if not target.is_file() or target.suffix.lower() != '.exe': raise ValueError('Executável inválido')
        subprocess.Popen([str(target)], close_fds=True)
        return {'resultado': 'Aplicativo iniciado', 'aplicativo': app}
    if name == 'local_tarefas_codex': return {'estado': 'desativado', 'motivo': 'Aprovação e sandbox ainda não homologados'}
    raise ValueError('Ferramenta desconhecida')


class LocalTool(BaseTool):
    def __init__(self, name, description, properties=None, required=None):
        self._spec = ToolSpec(name=name, description=description, parameters={'type':'object','properties':properties or {},'required':required or [],'additionalProperties':False})
    @property
    def spec(self): return self._spec
    def execute(self, **params):
        try:
            allowed = set(self._spec.parameters['properties'])
            if set(params) - allowed: raise ValueError('Argumentos não permitidos')
            value = run(self._spec.name, params)
            log.info('%s sucesso', self._spec.name)
            return ToolResult(tool_name=self._spec.name, content=json.dumps(value, ensure_ascii=False), success=True)
        except Exception as exc:
            log.warning('%s falhou: %s', self._spec.name, type(exc).__name__)
            return ToolResult(tool_name=self._spec.name, content=str(exc), success=False)


prop = {'projeto': {'type':'string', 'description':'Nome exato de projeto autorizado'}}
tools = [LocalTool('local_metricas','Consulta CPU, memória, GPU e armazenamento.'), LocalTool('local_projetos','Lista nomes de projetos autorizados.'), LocalTool('local_memorias','Pesquisa no cofre pessoal autorizado, somente leitura.',{'consulta': {'type':'string'}},['consulta']), LocalTool('local_git_status','Consulta pendências do projeto autorizado.',prop,['projeto']), LocalTool('local_git_historico','Consulta até dez commits do projeto autorizado.',prop,['projeto']), LocalTool('local_abrir_aplicativo','Abre somente chrome, visual studio code, bloco de notas, obsidian ou habblaud.',{'aplicativo':{'type':'string','enum':['chrome','visual studio code','bloco de notas','obsidian','habblaud']}},['aplicativo']), LocalTool('local_tarefas_codex','Informa estado da delegação ao Codex, atualmente desativada.')]
if __name__ == '__main__':
    server = MCPServer(tools=tools)
    for line in sys.stdin:
        try:
            obj = json.loads(line)
            if 'id' not in obj: continue
            reply = server.handle(MCPRequest.from_json(line))
            print(reply.to_json(), flush=True)
        except Exception:
            log.exception('Falha de protocolo')
