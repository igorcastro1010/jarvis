import subprocess
import tempfile
import unittest
from pathlib import Path
from jarvis.worktree_isolation import prepare_worktree


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, text=True)


class WorktreeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.repo = self.root/'source'; self.repo.mkdir()
        git(self.repo, 'init', '-q'); git(self.repo, 'config', 'user.name', 'Teste'); git(self.repo, 'config', 'user.email', 't@example.invalid')
        (self.repo/'nota.txt').write_text('original', encoding='utf8')
        git(self.repo, 'add', 'nota.txt'); git(self.repo, 'commit', '-qm', 'inicial')

    def tearDown(self): self.tmp.cleanup()

    def test_worktree_preserves_original_and_uses_new_branch(self):
        path = prepare_worktree(self.repo, self.root/'isolados', '012345abcdef')
        self.assertEqual(git(path, 'branch', '--show-current').stdout.strip(), 'codex/tarefa-012345abcdef')
        (path/'nota.txt').write_text('alterado', encoding='utf8')
        self.assertEqual((self.repo/'nota.txt').read_text(encoding='utf8'), 'original')

    def test_dirty_repository_and_unsafe_ids_are_rejected(self):
        (self.repo/'nota.txt').write_text('em andamento', encoding='utf8')
        with self.assertRaises(ValueError): prepare_worktree(self.repo, self.root/'isolados', '012345abcdef')
        with self.assertRaises(ValueError): prepare_worktree(self.repo, self.root/'isolados', '../fora')
