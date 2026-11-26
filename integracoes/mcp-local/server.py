"""Restrained local tools, served via OpenJarvis's own MCP implementation."""
import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

import psutil
import reminders
import codex_queue
import codex_manual
import codex_simulation
from openjarvis.core.types import ToolResult
from openjarvis.mcp.protocol import MCPRequest
from openjarvis.mcp.server import MCPServer
from openjarvis.tools._stubs import BaseTool, ToolSpec

HERE = Path(__file__).resolve().parent
CONFIG = HERE / 'autorizados.json'
VAULT = Path.home() / 'Documents' / 'Codex' / 'Preservacao-Jarvis-20261125' / 'data' / 'Cofre Jarvis'
FORTALAKA_ROOT = Path.home() / 'OneDrive' / 'Documentos' / 'Racha Fortalaka'
FORTALAKA_NAME = 'Racha Fortalaka'
PROJECT_DOCS = {'visao geral': 'README.md', 'fluxo': 'docs/fluxo-principal.md', 'pendencias documentadas': 'docs/revisao-pos-merge.md'}
APP_PATHS = {
    'chrome': Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Google/Chrome/Application/chrome.exe',
    'visual studio code': Path(os.environ['LOCALAPPDATA']) / 'Programs/Microsoft VS Code/Code.exe',
    'bloco de notas': Path(os.environ['SystemRoot']) / 'System32/notepad.exe',
    'obsidian': Path(os.environ['LOCALAPPDATA']) / 'Programs/Obsidian/Obsidian.exe',
}
HABBLAUD_DIR = Path.home() / 'Documents/Codex/Habblaud-oficial'
REMINDER_DB = Path.home() / '.openjarvis' / 'lembretes.db'
reminder_store = None
codex_store = None
log = logging.getLogger('jarvis_local')
log.setLevel(logging.INFO)
handler = RotatingFileHandler(HERE / 'acoes.log', maxBytes=250_000, backupCount=2, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
log.addHandler(handler)


def config():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def consulted_at():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def no_links(path):
    path = Path(os.path.abspath(path))
    for p in (path, *path.parents):
        if p.exists() and (p.is_symlink() or getattr(p, 'is_junction', lambda: False)()):
            raise ValueError('Links e junções não são permitidos')
    return path


def project(name):
    projects = config().get('projetos', {})
    if not isinstance(name, str) or name.strip().casefold() not in ('racha fortalaka', 'fortalaka'):
        raise ValueError('Projeto não autorizado')
    configured = projects.get(FORTALAKA_NAME)
    if not configured or os.path.normcase(os.path.abspath(configured)) != os.path.normcase(os.path.abspath(FORTALAKA_ROOT)):
        raise ValueError('Cadastro do projeto não autorizado')
    root = no_links(FORTALAKA_ROOT)
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
    cmd += ['status', '--porcelain=v1', '--branch', '--untracked-files=normal', '--ignore-submodules=all'] if kind == 'status' else ['log', '-10', '--format=%h %ad %s', '--date=short', '--no-show-signature']
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0', GIT_PAGER='cat', GIT_NO_REPLACE_OBJECTS='1')
    out = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if out.returncode:
        raise ValueError('Consulta Git não concluída')
    return out.stdout[:16000] or '(sem alterações)'


def project_document(name, topic):
    root = project(name)
    if not isinstance(topic, str) or topic not in PROJECT_DOCS:
        raise ValueError('Documento não autorizado')
    path = no_links(root / PROJECT_DOCS[topic])
    if not path.is_file() or path.stat().st_size > 200_000:
        raise ValueError('Documento indisponível')
    return {'fonte': 'Documentação local do Racha Fortalaka', 'origem': PROJECT_DOCS[topic], 'consultado_em': consulted_at(), 'arquivo_modificado_em': datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec='seconds'), 'conteudo': path.read_text(encoding='utf-8', errors='replace')[:16000], 'aviso': 'Documentação local pode estar desatualizada; não é confirmação do estado em produção.'}


def project_pending(name):
    project(name)
    root = no_links(VAULT)
    if not root.is_dir(): raise ValueError('Cofre autorizado indisponível')
    found = []
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith('.') and not (Path(current)/d).is_symlink() and not getattr(Path(current)/d, 'is_junction', lambda: False)()]
        for filename in files:
            path = Path(current) / filename
            if filename.startswith('.') or path.suffix.lower() != '.md': continue
            try:
                no_links(path)
                if path.stat().st_size > 200_000: continue
                dedicated = 'fortalaka' in str(path.relative_to(root)).casefold()
                in_section, level = dedicated, 0
                for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
                    heading = re.match(r'^(#{1,6})\s+(.+)', line)
                    if heading and not dedicated:
                        heading_level = len(heading.group(1))
                        if 'fortalaka' in heading.group(2).casefold(): in_section, level = True, heading_level
                        elif in_section and heading_level <= level: in_section = False
                    if in_section and re.match(r'^\s*[-*]\s+\[ \]', line) and not re.search(r'(?i)(api.?key|token|password|senha|secret|credencial|private.key)', line):
                        found.append({'origem': str(path.relative_to(root)), 'arquivo_modificado_em': datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec='seconds'), 'trecho': line.strip()[:400]})
                        if len(found) >= 20: return {'fonte': 'Obsidian', 'consultado_em': consulted_at(), 'pendencias': found, 'mensagem': 'Pendências registradas no Obsidian', 'aviso': 'Arquivos Git não são tarefas do Obsidian.'}
            except (OSError, ValueError): continue
    return {'fonte': 'Obsidian', 'consultado_em': consulted_at(), 'pendencias': found, 'mensagem': 'Pendências registradas no Obsidian' if found else 'Nenhuma pendência registrada no Obsidian', 'aviso': 'Foram consideradas somente tarefas abertas em notas ou seções dedicadas ao Racha Fortalaka; arquivos Git não são tarefas do Obsidian.'}


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
        env.update(HABBLAUD_HOST='127.0.0.1', HABBLAUD_BIND='127.0.0.1', HABBLAUD_TERMINAL='0', HABBLAUD_MENSAGENS='0', HABBLAUD_UPDATE_CHECK='0', HABBLAUD_DEMO='0', HABBLAUD_CODEX_DIRS=str(Path.home()/'.codex'), HABBLAUD_CLAUDE_DIRS=str(Path.home()/'.codex'))
        subprocess.Popen([str(node), str(script)], cwd=str(HABBLAUD_DIR), env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    os.startfile(url)
    return {'resultado': 'Abertura solicitada', 'aplicativo': 'habblaud', 'servidor_ja_ativo': healthy}


def run(name, args):
    global reminder_store, codex_store
    if name.startswith('local_codex_'):
        if codex_store is None: codex_store = codex_queue.TaskQueue(Path.home() / '.openjarvis' / 'tarefas_codex.db')
        if name == 'local_codex_preparar':
            project(args.get('projeto'))
            return {'resultado': 'Tarefa preparada; Codex não iniciado e execução desativada.', **codex_store.create(args.get('projeto'), args.get('solicitacao'))}
        if name == 'local_codex_prompt': return codex_manual.prepare(codex_store, args.get('id'), project(FORTALAKA_NAME))
        if name == 'local_codex_resultado': return codex_manual.read_result(codex_store, args.get('id'), args.get('sessao'))
        if name == 'local_codex_listar': return {'tarefas': codex_store.list(), 'execucao': 'desativada'}
        if name == 'local_codex_status': return {'tarefa': codex_store.get(args.get('id')), 'eventos': codex_store.events(args.get('id')), 'execucao': 'desativada'}
        if name == 'local_codex_cancelar': return {'tarefa': codex_store.cancel(args.get('id')), 'resultado': 'Solicitação cancelada; nenhum processo Codex foi iniciado.'}
        if name == 'local_codex_simular': return codex_simulation.simulate(codex_store, args.get('id'))
        if name == 'local_codex_confirmar': return codex_simulation.confirm(codex_store, args.get('id'))
        if name == 'local_codex_executar': return codex_store.request_execution(args.get('id'))
        raise ValueError('Ferramenta desconhecida')
    if name.startswith('local_lembrete_'):
        if reminder_store is None: reminder_store = reminders.ReminderStore(REMINDER_DB)
        if name == 'local_lembrete_criar':
            item = reminder_store.create(args.get('descricao'), reminders.parse_time(args.get('data_hora')), args.get('recorrencia','unico'))
            return {'resultado':'Lembrete já existente' if item['ja_existia'] else 'Lembrete criado', **item, 'fuso':'America/Fortaleza'}
        if name == 'local_lembrete_listar':
            period = args.get('periodo','todos')
            if period not in ('hoje','futuros','todos'): raise ValueError('Período inválido')
            today = datetime.now(reminders.FORTALEZA).date()
            items = reminder_store.list_active()
            if period == 'hoje': items = [i for i in items if datetime.fromisoformat(i['horario_fortaleza']).date() == today]
            elif period == 'futuros': items = [i for i in items if datetime.fromisoformat(i['horario_fortaleza']).date() > today]
            return {'lembretes':items,'entregas_recentes':reminder_store.recent_deliveries(),'agora_fortaleza':datetime.now(reminders.FORTALEZA).isoformat(timespec='seconds'),'fuso':'America/Fortaleza'}
        if name == 'local_lembrete_cancelar':
            ok=reminder_store.cancel(args.get('id'))
            return {'resultado':'Cancelado' if ok else 'Não cancelado: confirmação humana ausente ou negada', 'confirmado':ok}
        if name == 'local_lembrete_alterar':
            item_id=args.get('id'); old=reminder_store._current(item_id)
            if not any(k in args for k in ('descricao','data_hora','recorrencia')): raise ValueError('Informe o que deseja alterar')
            title=args.get('descricao',old['title']); due=reminders.parse_time(args['data_hora']) if 'data_hora' in args else datetime.fromisoformat(old['due'])
            ok=reminder_store.update(item_id,title,due,args.get('recorrencia',old['frequency']))
            return {'resultado':'Alterado' if ok else 'Não alterado: confirmação humana ausente ou negada', 'confirmado':ok}
        raise ValueError('Ferramenta desconhecida')
    if name == 'local_metricas': return metrics()
    if name == 'local_projetos':
        project(FORTALAKA_NAME)
        return {'projetos': [FORTALAKA_NAME]}
    if name == 'local_documentacao_projeto': return project_document(args.get('projeto'), args.get('tema'))
    if name == 'local_pendencias_projeto': return project_pending(args.get('projeto'))
    if name in ('local_git_status', 'local_git_historico'):
        return {'fonte': 'Git local', 'consultado_em': consulted_at(), 'tipo': 'alterações de arquivos no Git' if name.endswith('status') else 'histórico de commits do Git', 'resultado': git_query(args.get('projeto'), 'status' if name.endswith('status') else 'log'), 'aviso': 'Dados do Git não são tarefas registradas no Obsidian. O remoto não foi atualizado nesta consulta.'}
    if name == 'local_abrir_aplicativo':
        app = args.get('aplicativo')
        if app == 'habblaud': return open_habblaud()
        if app == 'codex':
            os.startfile('shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App')
            return {'resultado': 'Abertura solicitada', 'aplicativo': 'codex'}
        if not isinstance(app, str) or app not in APP_PATHS: raise ValueError('Aplicativo não autorizado')
        target = no_links(APP_PATHS[app])
        if not target.is_file() or target.suffix.lower() != '.exe': raise ValueError('Executável inválido')
        subprocess.Popen([str(target)], close_fds=True)
        return {'resultado': 'Aplicativo iniciado', 'aplicativo': app}
    if name == 'local_tarefas_codex': return {'estado': 'desativado', 'motivo': 'Aprovação e sandbox ainda não homologados'}
    raise ValueError('Ferramenta desconhecida')


class LocalTool(BaseTool):
    def __init__(self, name, description, properties=None, required=None, timeout=30):
        self._spec = ToolSpec(name=name, description=description, parameters={'type':'object','properties':properties or {},'required':required or [],'additionalProperties':False}, timeout_seconds=timeout)
    @property
    def spec(self): return self._spec
    def execute(self, **params):
        try:
            allowed = set(self._spec.parameters['properties'])
            if set(params) - allowed: raise ValueError('Argumentos não permitidos')
            value = run(self._spec.name, params)
            success = value.get('confirmado') is not False
            log.info('%s %s', self._spec.name, 'sucesso' if success else 'não confirmado')
            return ToolResult(tool_name=self._spec.name, content=json.dumps(value, ensure_ascii=False), success=success)
        except Exception as exc:
            log.warning('%s falhou: %s', self._spec.name, type(exc).__name__)
            return ToolResult(tool_name=self._spec.name, content=str(exc), success=False)


prop = {'projeto': {'type':'string', 'description':'Nome exato de projeto autorizado'}}
tools = [LocalTool('local_metricas','Consulta CPU, memória, GPU e armazenamento.'), LocalTool('local_projetos','Lista nomes de projetos autorizados.'), LocalTool('local_documentacao_projeto','Consulta documentação local do Racha Fortalaka e retorna origem e datas.',{'projeto':{'type':'string'},'tema':{'type':'string','enum':list(PROJECT_DOCS)}},['projeto','tema']), LocalTool('local_pendencias_projeto','Única fonte de tarefas do Obsidian do Racha Fortalaka. Retorna fonte, data e mensagem; se estiver vazio use a mensagem exata. Alterações Git não são tarefas do Obsidian.',prop,['projeto']), LocalTool('local_git_status','Consulta branch e alterações de arquivos do Git local com data. Essas alterações nunca são tarefas do Obsidian.',prop,['projeto']), LocalTool('local_git_historico','Consulta até dez commits do Git local com datas; não consulta tarefas do Obsidian.',prop,['projeto']), LocalTool('local_abrir_aplicativo','Abre somente chrome, visual studio code, bloco de notas, obsidian, habblaud ou codex.',{'aplicativo':{'type':'string','enum':['chrome','visual studio code','bloco de notas','obsidian','habblaud']}},['aplicativo']), LocalTool('local_tarefas_codex','Informa estado da delegação ao Codex, atualmente desativada.')]
tools.extend([
    LocalTool('local_codex_preparar', 'Prepara solicitação para o Racha Fortalaka; NÃO executa Codex. Nunca afirme que foi aprovada ou executada.', {'projeto': {'type':'string','enum':['Racha Fortalaka']}, 'solicitacao': {'type':'string','description':'Pedido do usuário, sem credenciais'}}, ['projeto','solicitacao']),
    LocalTool('local_codex_prompt', 'Exiba o prompt integral, incluindo o marcador, para o usuário copiar e enviar manualmente ao Codex; não executa a tarefa.', {'id':{'type':'string'}}, ['id']),
    LocalTool('local_codex_resultado', 'Consulta somente leitura da sessão Codex informada, quando associada à tarefa; não confirma sucesso.', {'id':{'type':'string'},'sessao':{'type':'string'}}, ['id','sessao']),
    LocalTool('local_codex_listar', 'Lista solicitações preparadas e seus estados. A execução está desativada.'),
    LocalTool('local_codex_status', 'Consulta uma solicitação preparada pelo identificador.', {'id':{'type':'string'}}, ['id']),
    LocalTool('local_codex_cancelar', 'Cancela apenas uma solicitação ainda aguardando aprovação; nenhum processo Codex foi iniciado.', {'id':{'type':'string'}}, ['id']),
    LocalTool('local_codex_simular', 'Executa somente processo fictício fixo; não executa a tarefa nem Codex.', {'id':{'type':'string'}}, ['id']),
    LocalTool('local_codex_confirmar', 'Mostra janela local experimental; não autoriza execução real.', {'id':{'type':'string'}}, ['id'], timeout=85),
    LocalTool('local_codex_executar', 'Informa que a execução está bloqueada; nunca inicia Codex.', {'id':{'type':'string'}}, ['id']),
])
reminder_fields = {'descricao':{'type':'string','description':'Descrição breve do lembrete'},'data_hora':{'type':'string','description':'Data e hora completas em ISO 8601, no horário de Fortaleza'},'recorrencia':{'type':'string','enum':['unico','diario','semanal']}}
tools.extend([
    LocalTool('local_lembrete_criar','Cria lembrete em data futura. Para data relativa consulte local_lembrete_listar antes e use agora_fortaleza; peça confirmação ao usuário se houver dúvida.',reminder_fields,['descricao','data_hora']),
    LocalTool('local_lembrete_listar','Lista lembretes, tentativas recentes e data e hora atuais em Fortaleza.',{'periodo':{'type':'string','enum':['hoje','futuros','todos']}},[]),
    LocalTool('local_lembrete_alterar','Altera lembrete somente após confirmação humana na janela do Windows.',{'id':{'type':'string'},**reminder_fields},['id'],timeout=85),
    LocalTool('local_lembrete_cancelar','Cancela lembrete somente após confirmação humana na janela do Windows.',{'id':{'type':'string'}},['id'],timeout=85),
])
if __name__ == '__main__':
    reminder_store = reminders.start_worker(REMINDER_DB)
    server = MCPServer(tools=tools)
    for line in sys.stdin:
        try:
            obj = json.loads(line)
            if 'id' not in obj: continue
            reply = server.handle(MCPRequest.from_json(line))
            print(reply.to_json(), flush=True)
        except Exception:
            log.exception('Falha de protocolo')
