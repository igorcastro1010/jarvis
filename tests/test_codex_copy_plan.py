import os
import tempfile
import unittest
from pathlib import Path
from jarvis.codex_copy_plan import prepare_copy_plan

class CopyPlanTests(unittest.TestCase):
    def test_only_plan_and_real_execution_remains_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source'; copy=root/'copy'; source.mkdir(); copy.mkdir()
            (copy/'arquivo.txt').write_text('ficticio')
            plan=prepare_copy_plan(source,copy)
            self.assertFalse(plan['execucao_habilitada'])
            self.assertEqual(plan['copia'], str(copy.resolve()))
    def test_rejects_hardlink_to_external_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source'; copy=root/'copy'; source.mkdir(); copy.mkdir()
            outside=root/'falso.txt'; outside.write_text('ficticio'); os.link(outside,copy/'link.txt')
            with self.assertRaises(ValueError): prepare_copy_plan(source,copy)

    def test_adapter_plan_cannot_run(self):
        from jarvis.codex_process import CodexCLI
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source'; copy=root/'copy'; source.mkdir(); copy.mkdir()
            adapter=CodexCLI(); self.assertFalse(adapter.prepare(source,copy)['execucao_habilitada'])
            with self.assertRaises(PermissionError): adapter.run('ficticio',copy)

    def test_copy_cannot_be_original_or_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source'; source.mkdir(); nested=source/'nested'; nested.mkdir()
            for copy in (source,nested):
                with self.assertRaises(ValueError): prepare_copy_plan(source,copy)

    def test_rejects_symbolic_link_if_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'source'; copy=root/'copy'; source.mkdir(); copy.mkdir()
            target=root/'fora'; target.write_text('ficticio')
            try: (copy/'link').symlink_to(target)
            except OSError: self.skipTest('Criação de symlink não disponível')
            with self.assertRaises(ValueError): prepare_copy_plan(source,copy)
