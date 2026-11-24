"""Interpreta notificações do App Server; não inicia nem autoriza tarefas."""


class AppServerEvents:
    def __init__(self, thread_id, turn_id):
        self.thread_id = thread_id
        self.turn_id = turn_id
        self.completed = False
        self.failed = False
        self.message = None
        self.usage = None

    def feed(self, event):
        params = event.get('params', {})
        if not isinstance(params, dict) or params.get('threadId') != self.thread_id:
            return
        method = event.get('method')
        if method == 'turn/completed':
            turn = params.get('turn', {})
            if turn.get('id') != self.turn_id:
                return
            self.completed = turn.get('status') == 'completed' and not turn.get('error')
            self.failed |= not self.completed
            return
        if params.get('turnId') != self.turn_id:
            return
        if method == 'item/completed':
            item = params.get('item', {})
            if item.get('type') == 'agentMessage':
                self.message = item.get('text')
            if item.get('type') == 'commandExecution' and (item.get('status') != 'completed' or item.get('exitCode') != 0):
                self.failed = True
        elif method == 'thread/tokenUsage/updated':
            usage = params.get('tokenUsage', {}).get('total', {})
            total, cached, output = (usage.get(k) for k in ('inputTokens', 'cachedInputTokens', 'outputTokens'))
            if all(type(x) is int and x >= 0 for x in (total, cached, output)) and cached <= total:
                self.usage = {'input_tokens': total, 'cached_input_tokens': cached,
                              'uncached_input_tokens': total - cached, 'output_tokens': output}

    def success(self, exit_code, verified=False):
        return bool(verified and exit_code == 0 and self.completed and not self.failed
                    and isinstance(self.message, str) and self.message.strip() and self.usage is not None)
