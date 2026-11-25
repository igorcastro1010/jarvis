import os
import tempfile
import time
import unittest
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
    from jarvis.desktop import Window
    from jarvis.memory import MemoryStore
    from jarvis.skills import SkillManager
    from jarvis.tasks import TaskStore
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'PySide6 não instalado')
class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.memory = MemoryStore(root / 'vault')
        self.skills = SkillManager(root / 'skills.db')
        self.tasks = TaskStore(root / 'tasks.db')
        self.window = Window(model=lambda _: 'Resposta fictícia', memory_factory=lambda: self.memory,
                             tasks_factory=lambda: self.tasks, skills_factory=lambda: self.skills, tray=False)

    def tearDown(self):
        self.window.pool.waitForDone(5000)
        self.app.processEvents()
        self.window.close()
        self.tmp.cleanup()

    def wait_jobs(self):
        deadline = time.monotonic() + 5
        while self.window.jobs and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.app.processEvents()
        self.assertFalse(self.window.jobs)

    def test_chat_routes_and_updates_real_state(self):
        self.window.message.setText('uma pergunta')
        self.window.send()
        self.assertEqual(self.window.status, 'processando')
        self.wait_jobs()
        self.assertEqual(self.window.status, 'disponível')
        self.assertIn('Resposta fictícia', self.window.chat.toPlainText())

    def test_scoped_memory_and_catalog(self):
        self.memory.remember('uniforme azul', project='alfa')
        self.memory.remember('uniforme verde', project='beta')
        self.window.memory_project.setText('alfa'); self.window.memory_query.setText('uniforme')
        self.window.search_memory(); self.wait_jobs()
        self.assertIn('azul', self.window.memory_results.toPlainText())
        self.assertNotIn('verde', self.window.memory_results.toPlainText())
        self.window.skill_name.setText('playwright'); self.window.set_skill(True); self.wait_jobs()
        self.assertTrue(self.skills.list()[0]['enabled'])

    def test_navigation_and_compact_size(self):
        self.assertEqual(self.window.stack.count(), 6)
        self.window.stack.setCurrentIndex(4)
        self.assertEqual(self.window.stack.currentIndex(), 4)
        self.window.toggle_compact()
        self.assertEqual(self.window.width(), 800)

    def test_settings_persist_and_history_does_not_store_secrets(self):
        from jarvis.background import load_settings
        root = Path(self.tmp.name)
        self.window.config_path = root / 'settings.json'
        self.window.inactivity.setText('90'); self.window.threshold.setText('0.03')
        self.window.save_voice_settings()
        self.assertEqual(load_settings(self.window.config_path).inactivity_seconds, 90)
        history = root / 'history.db'
        self.window.history_path = history
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(history)) as db, db:
            db.execute('CREATE TABLE messages (role TEXT NOT NULL, content TEXT NOT NULL)')
        self.window.remember_chat('Você', 'olá')
        self.window.remember_chat('Você', 'minha senha é 123')
        with closing(sqlite3.connect(history)) as db, db:
            self.assertEqual(db.execute('SELECT content FROM messages').fetchall(), [('olá',)])
