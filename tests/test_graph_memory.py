import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from jarvis.memory import MemoryStore
from jarvis.graph_memory import update_graph


class GraphTests(unittest.TestCase):
    def test_graph_uses_only_requested_project_and_local_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = MemoryStore(root / 'vault')
            store.remember('Projeto azul', project='alpha')
            store.remember('Projeto verde', project='beta')
            class Result: returncode = 0
            with patch('jarvis.graph_memory.subprocess.run', return_value=Result()) as run:
                update_graph(store, 'alpha', root / 'graphs', root / 'graphify.exe')
            args, kwargs = run.call_args
            self.assertIn('projeto-alpha', str(args[0]))
            self.assertNotIn('projeto-beta', str(args[0]))
            self.assertEqual(kwargs['env']['OLLAMA_BASE_URL'], 'http://127.0.0.1:11434/v1')

    def test_graph_rejects_secret_in_manually_added_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); store = MemoryStore(root / 'vault')
            store.remember('Projeto azul', project='alpha')
            (store.notes / 'projeto-alpha' / 'pessoal' / 'extra.md').write_text('senha=123456', encoding='utf8')
            with self.assertRaises(ValueError): update_graph(store, 'alpha', root / 'graphs', root / 'graphify.exe')
