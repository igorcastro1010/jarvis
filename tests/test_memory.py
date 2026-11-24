import tempfile
import unittest
from pathlib import Path
from jarvis.memory import MemoryStore


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = MemoryStore(self.root)

    def tearDown(self): self.tmp.cleanup()

    def test_persistence_dedup_and_project_isolation(self):
        a = self.store.remember('Usar azul no aplicativo', project='alpha', category='preferencias')
        self.assertEqual(a, self.store.remember('Usar azul no aplicativo', project='alpha', category='preferencias'))
        self.store.remember('Usar verde no aplicativo', project='beta', category='preferencias')
        fresh = MemoryStore(self.root)
        self.assertIn('azul', fresh.search('aplicativo', project='alpha')[0]['content'])
        self.assertNotIn('verde', str(fresh.search('aplicativo', project='alpha')))
        self.assertEqual(fresh.search('aplicativo'), [])

    def test_correction_and_reversible_forget(self):
        entry = self.store.remember('A reunião é terça', project='alpha')
        self.store.correct(entry, 'A reunião é quarta', project='alpha')
        self.assertIn('quarta', self.store.search('reunião', project='alpha')[0]['content'])
        with self.assertRaises(ValueError): self.store.forget(entry, project='beta')
        self.store.forget(entry, project='alpha')
        self.assertEqual(self.store.search('reunião', project='alpha'), [])
        self.assertTrue(list((self.root / 'Arquivo').rglob('*.md')))

    def test_rejects_credentials_and_path_traversal(self):
        with self.assertRaises(ValueError): self.store.remember('minha senha é 123456')
        with self.assertRaises(ValueError): self.store.remember('abc', project='../outro')
        self.assertEqual(self.store.search('senha'), [])

    def test_external_edit_updates_index(self):
        self.store.remember('O carro é vermelho')
        self.assertEqual(len(self.store.search('vermelho')), 1)
        path = next((self.root / 'Memoria Jarvis').rglob('*.md'))
        path.write_text(path.read_text(encoding='utf8').replace('vermelho', 'amarelo'), encoding='utf8')
        self.assertEqual(len(self.store.search('amarelo')), 1)
        self.assertEqual(self.store.search('vermelho'), [])
