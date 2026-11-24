import tempfile
import unittest
from pathlib import Path
from jarvis.local_vault import migrate_vault


class LocalVaultTests(unittest.TestCase):
    def test_migration_copies_without_overwriting_or_deleting_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'origem'; source.mkdir()
            (source/'nota.md').write_text('nota', encoding='utf8')
            (source/'.jarvis-indice.sqlite3').write_text('indice', encoding='utf8')
            dest = root/'local'/'Cofre'
            self.assertTrue(migrate_vault(source, dest))
            self.assertEqual((dest/'nota.md').read_text(encoding='utf8'), 'nota')
            self.assertFalse((dest/'.jarvis-indice.sqlite3').exists())
            (source/'nota.md').write_text('alterada', encoding='utf8')
            self.assertFalse(migrate_vault(source, dest))
            self.assertEqual((dest/'nota.md').read_text(encoding='utf8'), 'nota')
            self.assertEqual((source/'nota.md').read_text(encoding='utf8'), 'alterada')

    def test_rejects_destination_inside_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'vault'; source.mkdir()
            with self.assertRaises(ValueError): migrate_vault(source, source/'child')
