import unittest
from jarvis.background import AssistantState, Settings
from jarvis.service import VoiceService


class ServiceTests(unittest.TestCase):
    def test_run_limits_consecutive_failures_until_reactivated(self):
        from unittest.mock import patch
        service = self.make_service(iter([]), iter([]))
        calls = []
        def fail_step():
            calls.append(1)
            service.state.status = 'erro'
        pauses = []
        def sleep(duration):
            pauses.append(duration)
            if duration == 0.5 or len(pauses) >= 5: service.state.stopped = True
        service.step = fail_step
        with patch('jarvis.service.time.sleep', side_effect=sleep): service.run()
        self.assertEqual(len(calls), 3)
        self.assertIn(0.5, pauses)
    def test_idle_release_only_after_sustained_mute(self):
        service = self.make_service(iter([]), iter([]))
        released = []
        service.release_idle = lambda: released.append(True)
        self.state.mute()
        service.manage_idle(10); service.manage_idle(129)
        self.assertEqual(released, [])
        service.manage_idle(130); service.manage_idle(200)
        self.assertEqual(released, [True])
        self.state.unmute(); service.manage_idle(201)
        self.state.mute(); service.manage_idle(202); service.manage_idle(322)
        self.assertEqual(len(released), 2)

    def test_voice_events_are_reported_only_for_accepted_turns(self):
        events = []
        service = self.make_service(iter([1, 1]), iter(['som estranho', 'Jarvis, que horas são?']))
        service.on_exchange = lambda spoken, response: events.append((spoken, response))
        service.step(); self.assertEqual(events, [])
        service.step(); self.assertEqual(len(events), 1)
        self.assertIn('Jarvis', events[0][0])

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

    def test_model_failure_does_not_end_service(self):
        service = self.make_service(iter([1, 1]), iter(['Jarvis, diga algo', 'outra pergunta']))
        def fail(_): raise OSError('offline')
        service.model = fail
        service.step(); self.assertEqual(self.state.status, 'erro')
        service.model = lambda _: 'Agora disponível'
        service.step(); self.assertEqual(self.state.status, 'ouvindo')
        self.assertEqual(self.spoken[-1], 'Agora disponível')

    def test_speech_failure_does_not_end_service(self):
        service = self.make_service(iter([1, 1]), iter(['Jarvis', 'encerrar conversa']))
        def fail(*_): raise OSError('sem saída')
        service.speak = fail
        service.step(); self.assertEqual(self.state.status, 'erro')
        service.speak = lambda text, cancelled: self.spoken.append(text)
        service.step(); self.assertEqual(self.state.status, 'aguardando')


if __name__ == '__main__':
    unittest.main()
