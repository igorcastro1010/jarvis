import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import reminders
import server


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'test.db'
        self.store = reminders.ReminderStore(self.db)
        self.now = datetime(2026, 11, 25, 15, 0, tzinfo=reminders.FORTALEZA)

    def test_persistence_recurrence_and_one_delivery(self):
        item = self.store.create('beber água', self.now - timedelta(days=2), 'diario', now=self.now, allow_past=True)
        delivered = []
        self.store.dispatch_due(self.now, lambda title: delivered.append(title))
        self.store.dispatch_due(self.now, lambda title: delivered.append(title))
        self.assertEqual(delivered, ['Atrasado: beber água'])
        reloaded = reminders.ReminderStore(self.db).list_active()
        self.assertEqual(len(reloaded), 1)
        self.assertGreater(datetime.fromisoformat(reloaded[0]['proximo']), self.now.astimezone(timezone.utc))

    def test_sensitive_changes_require_actual_confirmation(self):
        item = self.store.create('consulta', self.now + timedelta(hours=1), 'unico', now=self.now)
        self.assertFalse(self.store.cancel(item['id'], lambda _: False))
        self.assertEqual(len(self.store.list_active()), 1)
        self.assertTrue(self.store.cancel(item['id'], lambda _: True))
        self.assertEqual(len(self.store.list_active()), 0)

    def test_input_validation_and_timezone(self):
        with self.assertRaises(ValueError): self.store.create('x', self.now - timedelta(seconds=1), 'unico', now=self.now)
        with self.assertRaises(ValueError): self.store.create('', self.now + timedelta(hours=1), 'unico', now=self.now)
        with self.assertRaises(ValueError): self.store.create('x', self.now + timedelta(hours=1), 'mensal', now=self.now)
        with self.assertRaises(ValueError): reminders.parse_time('2026-12-16')
        self.assertEqual(reminders.parse_time('2026-12-16T09:00').utcoffset(), timedelta(hours=-3))

    def test_confirmation_rejects_stale_revision(self):
        item = self.store.create('x', self.now + timedelta(hours=1), 'unico', now=self.now)
        def mutate_then_confirm(_):
            self.store.update(item['id'], 'outro', self.now + timedelta(hours=2), 'unico', lambda _: True, now=self.now)
            return True
        with self.assertRaises(ValueError): self.store.cancel(item['id'], mutate_then_confirm)

    def test_identical_create_is_not_duplicated(self):
        first = self.store.create('reunião', self.now + timedelta(hours=1), 'unico', now=self.now)
        second = self.store.create('reunião', self.now + timedelta(hours=1), 'unico', now=self.now)
        self.assertEqual(first['id'], second['id'])
        self.assertTrue(second['ja_existia'])
        self.assertEqual(len(self.store.list_active()), 1)

    def test_notification_failure_is_recorded_and_not_duplicated(self):
        self.store.create('aviso', self.now - timedelta(minutes=5), 'unico', now=self.now, allow_past=True)
        def fail(_): raise OSError('simulado')
        self.store.dispatch_due(self.now, fail)
        self.assertEqual(self.store.recent_deliveries()[0]['status'], 'falha')
        self.assertEqual(self.store.dispatch_due(self.now, lambda _: self.fail('duplicada')), 0)

    def test_concurrent_workers_claim_once(self):
        self.store.create('teste', self.now - timedelta(minutes=2), 'unico', now=self.now, allow_past=True)
        delivered=[]
        other=reminders.ReminderStore(self.db)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda store: store.dispatch_due(self.now, delivered.append), [self.store, other]))
        self.assertEqual(sum(results),1)
        self.assertEqual(len(delivered),1)

    def test_tool_refusal_is_a_failure_and_keeps_reminder(self):
        item = self.store.create('consulta', self.now + timedelta(days=100), 'unico', now=self.now)
        tool=next(t for t in server.tools if t.spec.name=='local_lembrete_cancelar')
        with patch.object(server, 'reminder_store', self.store), patch.object(self.store, 'cancel', return_value=False):
            result=tool.execute(id=item['id'])
        self.assertFalse(result.success)
        self.assertEqual(len(self.store.list_active()),1)

    def test_create_and_list_through_mcp_tools(self):
        create=next(t for t in server.tools if t.spec.name=='local_lembrete_criar')
        listing=next(t for t in server.tools if t.spec.name=='local_lembrete_listar')
        future=(datetime.now(reminders.FORTALEZA)+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        with patch.object(server, 'reminder_store', self.store):
            made=create.execute(descricao='teste isolado',data_hora=future,recorrencia='diario')
            listed=listing.execute(periodo='futuros')
        self.assertTrue(made.success)
        self.assertTrue(listed.success)
        self.assertIn('teste isolado',listed.content)


if __name__ == '__main__': unittest.main()
