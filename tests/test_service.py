import unittest
from jarvis.background import AssistantState, Settings
from jarvis.service import VoiceService


class ServiceTests(unittest.TestCase):
    def make_service(self, captures, transcriptions, speakers=None):
        self.state = AssistantState()
        self.spoken = [] if speakers is None else speakers
        self.service = VoiceService(self.state, lambda: Settings(inactivity_seconds=10),
                                    lambda **_: next(captures),
                                    lambda _: next(transcriptions),
                                    lambda text, cancelled: self.spoken.append(text),
                                    lambda _: 'Resposta local', clock=lambda: 1)
        return self.service

    def test_wake_conversation_and_end(self):
        service = self.make_service(iter([1, 1, 1]), iter(['Jarvis', 'Qual é a capital?', 'encerrar conversa']))
        service.step(); self.assertEqual(self.state.status, 'ouvindo')
        service.step(); self.assertEqual(self.state.status, 'ouvindo')
        service.step(); self.assertEqual(self.state.status, 'aguardando')
        self.assertEqual(len(self.spoken), 3)
        self.assertEqual(self.state.controller.session.history, [])

    def test_mute_during_model_discards_result_and_context(self):
        service = self.make_service(iter([1]), iter(['Jarvis, pergunte algo']))
        def model(_):
            self.state.mute()
            return 'resultado tardio'
        service.model = model
        service.step()
        self.assertEqual(self.state.status, 'silenciado')
        self.assertEqual(self.spoken, [])
        self.assertEqual(self.state.controller.session.history, [])

    def test_failure_retries_and_recovers(self):
        calls = iter([RuntimeError('indisponível'), 1])
        def capture(**_):
            value = next(calls)
            if isinstance(value, Exception):
                raise value
            return value
        service = self.make_service(iter([]), iter(['Jarvis']))
        service.capture = capture
        service.step(); self.assertEqual(self.state.status, 'erro')
        service.step(); self.assertEqual(self.state.status, 'ouvindo')


if __name__ == '__main__':
    unittest.main()
