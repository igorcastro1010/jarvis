"""Resumo conservador das capacidades reais e cadastros locais."""
import sqlite3
import importlib.util
import shutil
from .memory import SECRET


def capability_summary(tasks_factory=None, skills_factory=None):
    sections = ['Posso conversar por texto e, quando configurada, voz local; consultar e registrar memórias e preparar prompts. '
                'A execução automática do Codex está desativada. A voz integrada ainda precisa de teste físico.']
    try:
        from .tasks import default_tasks
        tasks = (tasks_factory or default_tasks)()
        with tasks.connect() as db:
            names = [row['name'] for row in db.execute('SELECT name FROM projects ORDER BY name LIMIT 10')]
        names = [n[:80] for n in names if not SECRET.search(n)]
        sections.append('Projetos cadastrados: ' + (', '.join(names) if names else 'nenhum.'))
    except (OSError, ValueError, sqlite3.Error):
        sections.append('Cadastro de projetos indisponível.')
    try:
        from .skills import default_manager
        skills = (skills_factory or default_manager)().list()
        active = [s['name'] for s in skills if s['enabled']]
        sections.append('Sugestões de skills ativas: ' + (', '.join(active) if active else 'nenhuma.') +
                        ' Ativação não instala nem executa skills.')
    except (OSError, ValueError, sqlite3.Error):
        sections.append('Catálogo de skills indisponível.')
    audio = 'biblioteca de áudio instalada' if importlib.util.find_spec('sounddevice') else 'biblioteca de áudio não encontrada'
    sections.append(f'Áudio: {audio}; disponibilidade de dispositivos e modelos exige verificação.')
    sections.append('Codex CLI: ' + ('detectado' if shutil.which('codex') else 'não detectado') +
                    '; execução automática desativada.')
    sections.append('Graphify: consulta de relações quando houver grafo gerado; automação Windows não está disponível.')
    return '\n'.join(sections)
