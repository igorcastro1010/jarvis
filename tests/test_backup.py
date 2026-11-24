import tempfile
import unittest
import zipfile
from pathlib import Path
from jarvis.memory_backup import backup, restore


class BackupTests(unittest.TestCase):
    def test_backup_restore_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); vault = base / 'vault'; vault.mkdir()
            (vault / 'nota.md').write_text('conteúdo', encoding='utf8')
            archive = base / 'backup.zip'
            backup(vault, archive)
            restore(archive, base / 'recuperado')
            self.assertEqual((base / 'recuperado' / 'nota.md').read_text(encoding='utf8'), 'conteúdo')
            with self.assertRaises(FileExistsError): restore(archive, base / 'recuperado')

    def test_restore_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); archive = base / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z: z.writestr('../escape.md', 'x')
            with self.assertRaises(ValueError): restore(archive, base / 'restored')
            self.assertFalse((base / 'escape.md').exists())
