import unittest
from jarvis.voice_session import Session, extract_wake


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


if __name__ == '__main__':
    unittest.main()
