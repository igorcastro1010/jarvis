import tempfile
import unittest
from pathlib import Path
from jarvis.conversation import answer
from jarvis.memory import MemoryStore
from jarvis.voice_session import Session


class ConversationMemoryTests(unittest.TestCase):
    def test_commands_and_scoped_retrieval(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(Path(tmp)); session = Session(); calls = []
            model = lambda messages: calls.append(messages) or 'Resposta'
            result = answer('projeto alpha: lembre que o uniforme é azul', session, model, store)
            self.assertIn('registr', result.casefold())
            answer('projeto beta: lembre que o uniforme é verde', session, model, store)
            answer('projeto alpha: como é o uniforme?', session, model, store)
            self.assertIn('azul', str(calls[-1]))
            self.assertNotIn('verde', str(calls[-1]))

    def test_reject_sensitive_memory_without_calling_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryStore(tmp)
            result = answer('lembre que minha senha é segredo', Session(), lambda _: 'BAD', store)
            self.assertIn('não', result.casefold())
            self.assertEqual(store.search('segredo'), [])
