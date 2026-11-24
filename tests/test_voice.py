import unittest
from jarvis.voice_session import Session, extract_wake
from jarvis.conversation import answer


class VoiceSessionTests(unittest.TestCase):
    def test_wake_is_a_word_and_removes_prefix(self):
        self.assertEqual(extract_wake('Jarvis, que horas são?'), 'que horas são?')
        self.assertIsNone(extract_wake('jarvismo'))

    def test_context_is_bounded_and_reset(self):
        s = Session(max_turns=2)
        for n in range(3):
            s.remember(str(n), str(n))
        self.assertEqual([x['content'] for x in s.history], ['1', '1', '2', '2'])
        s.reset()
        self.assertEqual(s.history, [])

    def test_end_requires_exact_command(self):
        s = Session()
        self.assertTrue(s.should_end('encerrar conversa'))
        self.assertFalse(s.should_end('como encerrar conversa com o cliente?'))

    def test_context_passes_to_local_model_and_is_not_saved_on_failure(self):
        s = Session()
        calls = []
        def model(messages):
            calls.append(messages)
            return 'Fortaleza'
        self.assertEqual(answer('Qual é a capital do Ceará?', s, model), 'Fortaleza')
        answer('E o estado?', s, model)
        self.assertEqual(calls[1][-3]['content'], 'Qual é a capital do Ceará?')
        before = list(s.history)
        def fail(_):
            raise OSError('offline')
        with self.assertRaises(OSError):
            answer('pergunta', s, fail)
        self.assertEqual(s.history, before)

    def test_codex_route_never_runs_a_command(self):
        s = Session()
        def forbidden(_):
            raise AssertionError('não deveria executar')
        self.assertIn('não está configurada', answer('corrija o código', s, forbidden))


if __name__ == '__main__':
    unittest.main()
