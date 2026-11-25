import unittest
from jarvis.shared_conversation import SharedConversation
from jarvis.conversation import answer


class IntelligenceTests(unittest.TestCase):
    def test_context_shared_between_text_and_voice(self):
        calls = []
        def model(messages):
            calls.append(messages)
            return 'Entendido.'
        shared = SharedConversation()
        shared.respond('Meu animal favorito é gato.', model)
        shared.respond('Qual é ele?', model)
        self.assertIn('Meu animal favorito é gato.', str(calls[-1]))

    def test_cancellation_does_not_commit_context(self):
        shared = SharedConversation()
        called = []
        shared.respond('mensagem cancelada', lambda _: called.append(True), valid=lambda: False)
        self.assertEqual(called, [])
        calls = []
        shared.respond('outra pergunta', lambda m: calls.append(m) or 'ok')
        self.assertNotIn('mensagem cancelada', str(calls[-1]))

    def test_service_voice_then_text_shares_context(self):
        from jarvis.background import AssistantState, Settings
        from jarvis.service import VoiceService
        shared = SharedConversation(); calls = []
        model = lambda messages: calls.append(messages) or 'ok'
        service = VoiceService(AssistantState(), lambda: Settings(), lambda **_: 1,
                               lambda _: 'Jarvis, prefiro chá', lambda *_: None,
                               model, shared=shared)
        service.step()
        shared.respond('O que prefiro?', model)
        self.assertIn('prefiro chá', str(calls[-1]))

    def test_text_then_service_voice_shares_context(self):
        from jarvis.background import AssistantState, Settings
        from jarvis.service import VoiceService
        shared = SharedConversation(); calls = []
        model = lambda messages: calls.append(messages) or 'ok'
        shared.respond('Prefiro café.', model)
        service = VoiceService(AssistantState(), lambda: Settings(), lambda **_: 1,
                               lambda _: 'Jarvis, o que eu prefiro?', lambda *_: None,
                               model, shared=shared)
        service.step()
        self.assertIn('Prefiro café.', str(calls[-1]))

    def test_identity_prompt_and_capabilities_are_honest(self):
        from jarvis.voice_session import Session
        calls = []
        answer('Fale sobre astronomia', Session(), lambda m: calls.append(m) or 'ok')
        system = calls[0][0]['content']
        self.assertIn('português brasileiro', system)
        self.assertIn('não afirme', system.lower())
        self.assertIn('Codex', system)

    def test_capabilities_use_local_catalog_and_do_not_claim_execution(self):
        import tempfile
        from pathlib import Path
        from jarvis.capabilities import capability_summary
        from jarvis.tasks import TaskStore
        from jarvis.skills import SkillManager
        with tempfile.TemporaryDirectory() as tmp:
            tasks = TaskStore(Path(tmp) / 'tasks.sqlite')
            skills = SkillManager(Path(tmp) / 'skills.sqlite')
            skills.set_enabled('playwright', True)
            summary = capability_summary(lambda: tasks, lambda: skills)
            self.assertIn('playwright', summary)
            self.assertIn('desativada', summary)
            self.assertIn('não instala nem executa', summary)
