import unittest

from jarvis.app_server_events import AppServerEvents


class AppServerEventsTests(unittest.TestCase):
    def test_success_requires_matching_turn_and_confirmed_shutdown(self):
        events = AppServerEvents('thread-1', 'turn-1')
        events.feed({'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'thread-1', 'turnId': 'turn-1', 'tokenUsage': {'total': {'inputTokens': 1, 'cachedInputTokens': 0, 'outputTokens': 1}}}})
        events.feed({'method': 'item/completed', 'params': {'threadId': 'thread-1', 'turnId': 'turn-1', 'item': {'type': 'agentMessage', 'text': 'Pronto'}}})
        events.feed({'method': 'turn/completed', 'params': {'threadId': 'thread-1', 'turn': {'id': 'turn-2', 'status': 'completed'}}})
        self.assertFalse(events.success(0, verified=True))
        events.feed({'method': 'turn/completed', 'params': {'threadId': 'thread-1', 'turn': {'id': 'turn-1', 'status': 'completed'}}})
        self.assertFalse(events.success(None, verified=True))
        self.assertFalse(events.success(0, verified=False))
        self.assertTrue(events.success(0, verified=True))

    def test_failure_and_usage(self):
        events = AppServerEvents('thread-1', 'turn-1')
        events.feed({'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'thread-1', 'turnId': 'turn-1', 'tokenUsage': {'total': {'inputTokens': 100, 'cachedInputTokens': 70, 'outputTokens': 5}}}})
        events.feed({'method': 'item/completed', 'params': {'threadId': 'thread-1', 'turnId': 'turn-1', 'item': {'type': 'commandExecution', 'status': 'failed', 'exitCode': 1}}})
        events.feed({'method': 'item/completed', 'params': {'threadId': 'thread-1', 'turnId': 'turn-1', 'item': {'type': 'agentMessage', 'text': 'Pronto'}}})
        events.feed({'method': 'turn/completed', 'params': {'threadId': 'thread-1', 'turn': {'id': 'turn-1', 'status': 'completed'}}})
        self.assertFalse(events.success(0, verified=True))
        self.assertEqual(events.usage, {'input_tokens': 100, 'cached_input_tokens': 70, 'uncached_input_tokens': 30, 'output_tokens': 5})

    def test_interrupted_or_invalid_usage_is_never_success(self):
        events = AppServerEvents('thread-1', 'turn-1')
        events.feed({'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'thread-1', 'turnId': 'turn-1', 'tokenUsage': {'total': {'inputTokens': 1, 'cachedInputTokens': 2, 'outputTokens': 1}}}})
        events.feed({'method': 'turn/completed', 'params': {'threadId': 'thread-1', 'turn': {'id': 'turn-1', 'status': 'interrupted'}}})
        self.assertIsNone(events.usage)
        self.assertFalse(events.success(0, verified=True))
