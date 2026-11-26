import tempfile
import unittest
from pathlib import Path
from codex_queue import TaskQueue
from codex_approval import ApprovalBroker

class ApprovalBrokerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.queue=TaskQueue(Path(self.tmp.name)/'queue.db')
        self.task=self.queue.create('Racha Fortalaka','Pedido ficticio de teste')
        self.clock=[100.0]; self.broker=ApprovalBroker(lambda _:True, clock=lambda:self.clock[0], ttl=20)

    def test_one_use_and_exact_task(self):
        self.assertTrue(self.broker.request(self.queue,self.task['id']))
        self.assertTrue(self.broker.consume(self.queue,self.task['id']))
        self.assertFalse(self.broker.consume(self.queue,self.task['id']))

    def test_expiry_refusal_and_changed_request(self):
        self.assertTrue(self.broker.request(self.queue,self.task['id']))
        self.clock[0]+=20
        self.assertFalse(self.broker.consume(self.queue,self.task['id']))
        self.assertTrue(self.broker.request(self.queue,self.task['id']))
        with self.queue.connect() as db: db.execute('UPDATE tasks SET description=? WHERE id=?', ('Mudanca ficticia',self.task['id']))
        self.assertFalse(self.broker.consume(self.queue,self.task['id']))
        denied=ApprovalBroker(lambda _:False, clock=lambda:self.clock[0])
        self.assertFalse(denied.request(self.queue,self.task['id']))
        self.assertFalse(denied.consume(self.queue,self.task['id']))

    def test_concurrent_consumption_is_one_use(self):
        from concurrent.futures import ThreadPoolExecutor
        self.assertTrue(self.broker.request(self.queue,self.task['id']))
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda _:self.broker.consume(self.queue,self.task['id']),range(2)))
        self.assertEqual(sorted(outcomes),[False,True])

    def test_later_refusal_invalidates_earlier_dialog(self):
        import threading
        entered=threading.Event(); release=threading.Event(); calls=[]
        def dialog(_):
            calls.append(1)
            if len(calls)==1:
                entered.set(); release.wait(3); return True
            return False
        broker=ApprovalBroker(dialog,clock=lambda:self.clock[0])
        first=[]; thread=threading.Thread(target=lambda:first.append(broker.request(self.queue,self.task['id'])))
        thread.start(); self.assertTrue(entered.wait(3))
        self.assertFalse(broker.request(self.queue,self.task['id']))
        release.set(); thread.join(3)
        self.assertFalse(broker.consume(self.queue,self.task['id']))
