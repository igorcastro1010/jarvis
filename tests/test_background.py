import tempfile
import unittest
from pathlib import Path
from jarvis.background import Settings, AssistantState, load_settings, save_settings, InstanceLock


class BackgroundTests(unittest.TestCase):
    def test_settings_roundtrip_and_invalid_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.json'
            settings = Settings(inactivity_seconds=45, threshold=0.02)
            save_settings(path, settings)
            self.assertEqual(load_settings(path), settings)
            path.write_text('{broken', encoding='utf-8')
            self.assertEqual(load_settings(path), Settings())
            with self.assertRaises(ValueError):
                save_settings(path, Settings(inactivity_seconds=0))

    def test_mute_invalidates_pending_work_and_resets_context(self):
        state = AssistantState()
        state.activate(0)
        state.controller.session.remember('oi', 'olá')
        ticket = state.ticket()
        state.mute()
        self.assertFalse(state.valid(ticket))
        self.assertEqual(state.status, 'silenciado')
        self.assertEqual(state.controller.session.history, [])
        state.unmute()
        self.assertEqual(state.status, 'aguardando')

    def test_inactivity_closes_context(self):
        state = AssistantState()
        state.activate(10)
        state.controller.session.remember('a', 'b')
        self.assertFalse(state.expire(39, 30))
        self.assertTrue(state.expire(40, 30))
        self.assertFalse(state.controller.active)
        self.assertEqual(state.status, 'aguardando')
        self.assertEqual(state.controller.session.history, [])

    def test_single_instance_lock(self):
        first = InstanceLock('Local\\JarvisTest-Unique-39124')
        second = InstanceLock('Local\\JarvisTest-Unique-39124')
        try:
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
        finally:
            first.close()
            second.close()
