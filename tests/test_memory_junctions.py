import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from jarvis.memory import MemoryStore


class JunctionTests(unittest.TestCase):
    def test_project_junction_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            project = store.notes / 'projeto-alfa'
            with patch.object(Path, 'is_junction', lambda path: path == project):
                with self.assertRaises(ValueError):
                    store.remember('informação fictícia', project='alfa')
