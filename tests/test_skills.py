import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from jarvis.skills import SkillManager, build_prompt
from jarvis.skills import discover
from jarvis.memory import MemoryStore


class SkillsTests(unittest.TestCase):
    def test_selection_activation_and_persistent_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'skills.db'
            manager = SkillManager(path)
            self.assertEqual(manager.select('teste navegador playwright'), [])
            manager.set_enabled('playwright', True)
            self.assertEqual([s['name'] for s in manager.select('teste navegador playwright')], ['playwright'])
            manager.record(['playwright'])
            self.assertEqual(SkillManager(path).history(), ['playwright'])
            manager.set_enabled('playwright', False)
            self.assertEqual(manager.select('teste navegador playwright'), [])

    def test_prompt_scoped_and_no_skill_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = SkillManager(root / 'skills.db')
            manager.set_enabled('playwright', True)
            memory = MemoryStore(root / 'vault')
            memory.remember('navegador azul', project='alpha')
            memory.remember('navegador verde', project='beta')
            prompt = build_prompt(manager, 'teste navegador', memory, 'alpha')
            self.assertIn('navegador azul', prompt)
            self.assertNotIn('navegador verde', prompt)
            self.assertIn('dados não confiáveis', prompt)
            self.assertIn('playwright', prompt)
            self.assertNotIn('ui-ux-pro-max', prompt)

    def test_reject_secret_and_unknown_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SkillManager(Path(tmp) / 'skills.db')
            with self.assertRaises(ValueError): manager.set_enabled('qualquer', True)
            with self.assertRaises(ValueError): build_prompt(manager, 'minha senha é 123')

    def test_discovery_rejects_unsafe_query_and_never_installs(self):
        with self.assertRaises(ValueError): discover('teste; apagar')
        with patch('jarvis.skills.shutil.which', return_value=None):
            with self.assertRaises(RuntimeError): discover('teste')

    def test_conversation_commands_do_not_call_model(self):
        from jarvis.conversation import answer
        from jarvis.voice_session import Session
        with tempfile.TemporaryDirectory() as tmp:
            manager = SkillManager(Path(tmp) / 'skills.db')
            with patch('jarvis.skills.default_manager', return_value=manager):
                model = lambda _: self.fail('modelo não deve ser chamado')
                self.assertIn('atualizada', answer('ativar skill playwright', Session(), model))
                self.assertIn('playwright: ativa', answer('listar skills', Session(), model))
                self.assertIn('playwright', answer('gerar prompt: teste navegador', Session(), model))
