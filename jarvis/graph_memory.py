"""Extração Graphify sob demanda para um único escopo e Ollama local."""
import argparse
import os
from pathlib import Path
import subprocess
from .memory import SECRET, default_store, scope_name


def update_graph(store, project, output_root, executable):
    scope = scope_name(project)
    source = store.notes / scope
    if not source.is_dir() or source.is_symlink(): raise ValueError('Não há memórias nesse contexto.')
    for path in source.rglob('*'):
        if path.is_symlink(): raise ValueError('Links simbólicos não são permitidos na extração.')
        if path.is_file() and path.suffix.lower() == '.md' and SECRET.search(path.read_text(encoding='utf8')):
            raise ValueError('Possível credencial encontrada. Remova-a antes de gerar o grafo.')
    output = Path(output_root) / scope
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['OLLAMA_BASE_URL'] = 'http://127.0.0.1:11434/v1'
    env['OLLAMA_HOST'] = '127.0.0.1:11434'
    env['OLLAMA_API_KEY'] = 'local'
    cmd = [str(executable), 'extract', str(source), '--backend', 'ollama', '--model', 'qwen2.5:3b',
           '--max-concurrency', '1', '--api-timeout', '120', '--no-cluster', '--out', str(output)]
    result = subprocess.run(cmd, env=env, capture_output=True, timeout=600, check=False)
    if result.returncode: raise RuntimeError('Graphify falhou; verifique instalação e Ollama local.')
    return output / 'graphify-out' / 'graph.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projeto', default=None, help='Nome exato; omita para memórias pessoais')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    executable = root / 'data/graphify-venv/Scripts/graphify.exe'
    path = update_graph(default_store(), args.projeto, root / 'data/grafos', executable)
    print('Grafo gerado em:', path)


if __name__ == '__main__': main()
