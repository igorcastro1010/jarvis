import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import server
from codex_queue import TaskQueue

class SemiautoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name); self.sessions=root/'sessions'; (self.sessions/'2026'/'11'/'25').mkdir(parents=True)
        self.queue=TaskQueue(root/'fila.db'); self.task=self.queue.create('Racha Fortalaka','Ajustar tela fictícia')
        p=patch.object(server,'codex_store',self.queue); p.start(); self.addCleanup(p.stop)
        p=patch.object(server,'project',return_value=root/'repo'); p.start(); self.addCleanup(p.stop)
        self.sid='019b0000-0000-7000-8000-000000000001'

    def write_rollout(self, user, final='Resultado fictício', include_final=True):
        rows=[{'type':'session_meta','payload':{'id':self.sid}},
              {'type':'event_msg','payload':{'type':'item_completed','turn_id':'turno1','item':{'type':'UserMessage','content':[{'type':'text','text':user}]}}}]
        if include_final: rows.append({'type':'event_msg','payload':{'type':'item_completed','turn_id':'turno1','item':{'type':'AgentMessage','phase':'final_answer','content':[{'type':'text','text':final}]}}})
        path=self.sessions/'2026'/'11'/'25'/('rollout-2026-11-25T10-00-00-'+self.sid+'.jsonl')
        path.write_text('\n'.join(json.dumps(row) for row in rows),encoding='utf8')

    def test_prompt_copiable_is_bound_and_does_not_execute(self):
        with patch('subprocess.Popen',side_effect=AssertionError('proibido')):
            result=server.run('local_codex_prompt',{'id':self.task['id']})
        self.assertIn(self.task['solicitacao'],result['prompt'])
        self.assertIn(self.task['id'],result['prompt'])
        self.assertIn(self.queue.approval_fingerprint(self.task['id']),result['prompt'])
        self.assertEqual(self.queue.get(self.task['id'])['estado'],'aguardando_aprovacao')

    def test_reads_only_result_of_matching_user_prompt(self):
        prompt=server.run('local_codex_prompt',{'id':self.task['id']})['prompt']; self.write_rollout(prompt)
        with patch('codex_manual.SESSIONS',self.sessions):
            result=server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})
        self.assertEqual(result['resposta'],'Resultado fictício')
        self.assertEqual(result['sessao'],self.sid)
        self.assertFalse(result['verificado'])

    def test_unrelated_session_does_not_leak_and_bad_id_rejected(self):
        self.write_rollout('Outra conversa', 'conteúdo privado')
        with patch('codex_manual.SESSIONS',self.sessions):
            with self.assertRaises(ValueError): server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})
            with self.assertRaises(ValueError): server.run('local_codex_resultado',{'id':self.task['id'],'sessao':'../fora'})

    def test_incomplete_result_is_pending(self):
        prompt=server.run('local_codex_prompt',{'id':self.task['id']})['prompt']; self.write_rollout(prompt,include_final=False)
        with patch('codex_manual.SESSIONS',self.sessions): result=server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})
        self.assertEqual(result['estado'],'pendente'); self.assertIsNone(result['resposta'])

    def test_open_official_app_without_arguments(self):
        with patch('os.startfile') as start:
            result=server.run('local_abrir_aplicativo',{'aplicativo':'codex'})
        start.assert_called_once_with('shell:AppsFolder\\OpenAI.Codex_2p2nqsd0c76g0!App')
        self.assertEqual(result['aplicativo'],'codex')

    def test_agent_echo_of_marker_is_not_user_association(self):
        prompt=server.run('local_codex_prompt',{'id':self.task['id']})['prompt']
        self.write_rollout('Outra tarefa',prompt)
        with patch('codex_manual.SESSIONS',self.sessions):
            with self.assertRaises(ValueError): server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})

    def test_does_not_return_later_unrelated_turn(self):
        prompt=server.run('local_codex_prompt',{'id':self.task['id']})['prompt']; self.write_rollout(prompt,include_final=False)
        path=next(self.sessions.rglob('*.jsonl'))
        with path.open('a',encoding='utf8') as out:
            out.write('\n'+json.dumps({'type':'event_msg','payload':{'type':'item_completed','turn_id':'outro','item':{'type':'UserMessage','content':[{'text':'Outro pedido'}]}}}))
            out.write('\n'+json.dumps({'type':'event_msg','payload':{'type':'item_completed','turn_id':'outro','item':{'type':'AgentMessage','phase':'final_answer','content':[{'text':'Dado de outro turno'}]}}}))
        with patch('codex_manual.SESSIONS',self.sessions): result=server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})
        self.assertEqual(result['estado'],'pendente'); self.assertIsNone(result['resposta'])

    def test_archived_session_result_is_available(self):
        prompt=server.run('local_codex_prompt',{'id':self.task['id']})['prompt']; self.write_rollout(prompt)
        archived=Path(self.tmp.name)/'archived_sessions'; archived.mkdir()
        next(self.sessions.rglob('*.jsonl')).rename(archived/('rollout-2026-11-25T10-00-00-'+self.sid+'.jsonl'))
        with patch('codex_manual.SESSIONS',self.sessions), patch('codex_manual.ARCHIVED',archived):
            result=server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})
        self.assertEqual(result['resposta'],'Resultado fictício')

    def test_hardlinked_transcript_is_not_read(self):
        import os
        prompt=server.run('local_codex_prompt',{'id':self.task['id']})['prompt']; self.write_rollout(prompt)
        path=next(self.sessions.rglob('*.jsonl')); os.link(path,Path(self.tmp.name)/'extra-link')
        with patch('codex_manual.SESSIONS',self.sessions), patch('codex_manual.ARCHIVED',Path(self.tmp.name)/'empty'):
            with self.assertRaises(ValueError): server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})

    def test_changed_task_cannot_use_previous_session(self):
        prompt=server.run('local_codex_prompt',{'id':self.task['id']})['prompt']; self.write_rollout(prompt)
        with self.queue.connect() as db: db.execute('UPDATE tasks SET description=? WHERE id=?',('Outro pedido ficticio',self.task['id']))
        with patch('codex_manual.SESSIONS',self.sessions), patch('codex_manual.ARCHIVED',Path(self.tmp.name)/'none'):
            with self.assertRaises(ValueError): server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})

    def test_openjarvis_tool_results_expose_prompt_and_matching_answer(self):
        prompt_tool=next(t for t in server.tools if t.spec.name=='local_codex_prompt')
        first=prompt_tool.execute(id=self.task['id']); self.assertTrue(first.success)
        prompt=json.loads(first.content)['prompt']; self.write_rollout(prompt)
        result_tool=next(t for t in server.tools if t.spec.name=='local_codex_resultado')
        with patch('codex_manual.SESSIONS',self.sessions), patch('codex_manual.ARCHIVED',Path(self.tmp.name)/'none'):
            result=result_tool.execute(id=self.task['id'],sessao=self.sid)
        self.assertTrue(result.success)
        self.assertEqual(json.loads(result.content)['resposta'],'Resultado fictício')

    def test_task_changed_during_session_read_fails_closed(self):
        import codex_manual
        prompt=server.run('local_codex_prompt',{'id':self.task['id']})['prompt']; self.write_rollout(prompt)
        original=codex_manual.marker; count=[]
        def change(queue, task_id):
            count.append(1)
            if len(count)==2:
                with queue.connect() as db: db.execute('UPDATE tasks SET description=? WHERE id=?',('Pedido alterado',task_id))
            return original(queue,task_id)
        with patch('codex_manual.SESSIONS',self.sessions), patch('codex_manual.ARCHIVED',Path(self.tmp.name)/'none'), patch('codex_manual.marker',side_effect=change):
            with self.assertRaises(ValueError): server.run('local_codex_resultado',{'id':self.task['id'],'sessao':self.sid})

    def test_prompt_rejects_task_changed_between_reads(self):
        original=self.queue.get; calls=[]
        def changed(task_id):
            old=original(task_id); calls.append(1)
            if len(calls)==1:
                with self.queue.connect() as db: db.execute('UPDATE tasks SET description=? WHERE id=?',('Novo pedido ficticio',task_id))
            return old
        with patch.object(self.queue,'get',side_effect=changed):
            with self.assertRaises(ValueError): server.run('local_codex_prompt',{'id':self.task['id']})

    def test_prompt_rejects_cancelled_task_during_preparation(self):
        original=self.queue.approval_fingerprint; calls=[]
        def changed(task_id):
            value=original(task_id); calls.append(1)
            self.queue.cancel(task_id)
            return value
        with patch.object(self.queue,'approval_fingerprint',side_effect=changed):
            with self.assertRaises(ValueError): server.run('local_codex_prompt',{'id':self.task['id']})
