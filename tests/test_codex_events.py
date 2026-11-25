import unittest
from jarvis.codex_events import CodexEvents, Budget


class EventsTests(unittest.TestCase):
    def test_missing_usage_and_incomplete_command_are_not_success(self):
        events = CodexEvents()
        events.feed({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'feito'}})
        events.feed({'type': 'turn.completed'})
        self.assertFalse(events.success(0, verified=True))
        events.feed({'type': 'item.completed', 'item': {'type': 'command_execution', 'status': 'in_progress', 'exit_code': None}})
        events.feed({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 2}})
        self.assertFalse(events.success(0, verified=True))

    def test_negative_token_counts_are_rejected(self):
        events = CodexEvents()
        events.feed({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'ok'}})
        events.feed({'type': 'turn.completed', 'usage': {'input_tokens': -1, 'output_tokens': 2}})
        self.assertFalse(events.success(0, verified=True))

    def test_invalid_later_usage_invalidates_previous_usage(self):
        events = CodexEvents()
        events.feed({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'ok'}})
        events.feed({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'output_tokens': 2}})
        events.feed({'type': 'turn.completed', 'usage': {'input_tokens': -1, 'output_tokens': 2}})
        self.assertFalse(events.success(0, verified=True))

    def test_invalid_cache_count_is_not_silently_changed(self):
        events = CodexEvents()
        events.feed({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'ok'}})
        events.feed({'type': 'turn.completed', 'usage': {'input_tokens': 10, 'cached_input_tokens': 20, 'output_tokens': 2}})
        self.assertFalse(events.success(0, verified=True))
    def test_exit_zero_without_turn_completed_is_not_success(self):
        events = CodexEvents()
        events.feed({'type':'item.completed','item':{'type':'agent_message','text':'Pronto'}})
        self.assertFalse(events.success(0))

    def test_failed_command_blocks_success_and_tracks_usage(self):
        events = CodexEvents()
        events.feed({'type':'item.completed','item':{'type':'command_execution','status':'failed','exit_code':1}})
        events.feed({'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':70,'output_tokens':5}})
        self.assertFalse(events.success(0))
        self.assertEqual(events.usage, {'input_tokens':100,'cached_input_tokens':70,'uncached_input_tokens':30,'output_tokens':5})

    def test_turn_success_requires_message_and_successful_exit(self):
        events = CodexEvents()
        events.feed({'type':'item.completed','item':{'type':'agent_message','text':'OK'}})
        events.feed({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}})
        self.assertFalse(events.success(0))
        self.assertTrue(events.success(0, verified=True))
        self.assertFalse(events.success(1, verified=True))

    def test_budget_rejects_oversize_input_and_checks_usage(self):
        budget = Budget(max_prompt_chars=100, max_input_tokens=1000, max_output_tokens=100)
        with self.assertRaises(ValueError): budget.check_prompt('x'*101)
        self.assertTrue(budget.exceeded({'input_tokens':1001,'output_tokens':20}))
        self.assertFalse(budget.exceeded({'input_tokens':999,'output_tokens':20}))
