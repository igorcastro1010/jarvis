"""Confirmação experimental efêmera; não autoriza execução real."""
import json
import threading
import time
from jarvis.codex_handoff import prepare_queue_handoff


class ApprovalBroker:
    def __init__(self, dialog, *, clock=time.monotonic, ttl=120):
        if ttl <= 0: raise ValueError('Prazo inválido')
        self._dialog=dialog; self._clock=clock; self._ttl=ttl
        self._lock=threading.Lock(); self._records={}; self._epochs={}

    def request(self, queue, task_id):
        preview=prepare_queue_handoff(queue, task_id)
        with self._lock:
            self._records.pop(task_id, None)
            epoch=self._epochs.get(task_id,0)+1
            self._epochs[task_id]=epoch
        message=('Confirmar este pedido após sua revisão? Esta confirmação é experimental e NÃO permite executar o Codex.\n\n'
                 + json.dumps({key:preview[key] for key in ('id','projeto','solicitacao','impressao_digital')},ensure_ascii=True,indent=2))
        if self._dialog(message) is not True: return False
        try: current=prepare_queue_handoff(queue,task_id)
        except ValueError: return False
        if current['impressao_digital'] != preview['impressao_digital']: return False
        with self._lock:
            if self._epochs.get(task_id) != epoch: return False
            self._records[task_id]=(preview['impressao_digital'],self._clock()+self._ttl)
        return True

    def fingerprint(self, task_id):
        with self._lock:
            record=self._records.get(task_id)
            if record is None or self._clock() >= record[1]: return None
            return record[0]

    def consume(self, queue, task_id):
        with self._lock: record=self._records.pop(task_id,None)
        if record is None or self._clock() >= record[1]: return False
        try: current=prepare_queue_handoff(queue,task_id)
        except ValueError: return False
        return current['impressao_digital']==record[0]
