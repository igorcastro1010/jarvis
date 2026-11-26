import unittest
from jarvis.codex_events import CodexEvents
from jarvis.codex_correlation import correlate_session

class CorrelationTests(unittest.TestCase):
    def test_real_event_correlates_task_and_session_without_publishing(self):
        events=CodexEvents(); events.feed({'type':'thread.started','thread_id':'019b0000-0000-7000-8000-000000000001'})
        result=correlate_session('a'*32, events, simulated=False)
        self.assertEqual(result['tarefa_id'], 'a'*32)
        self.assertEqual(result['sessao_codex'], events.session_id)
        self.assertEqual(result['habblaud'], 'nao_verificado')
    def test_simulation_or_absent_session_cannot_produce_correlation(self):
        events=CodexEvents()
        self.assertIsNone(correlate_session('a'*32,events,simulated=False))
        events.feed({'type':'thread.started','thread_id':'019b0000-0000-7000-8000-000000000001'})
        self.assertIsNone(correlate_session('a'*32,events,simulated=True))
