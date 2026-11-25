"""Adaptador de fila inativo por padrão; não inicia processos por conta própria."""


def execute_next(store, runner, *, enabled=False):
    if not enabled: return None
    task = store.claim()
    if task is None: return None
    ident = task['id']
    if not store.start_claimed(ident): return ident
    try:
        outcome = runner(task, lambda: bool(store.get(ident)['cancel_requested']))
        status = {'verified': 'concluído', 'cancelled': 'cancelado', 'timeout': 'erro'}.get(outcome.status, 'aguardando aprovação')
        usage = outcome.events.usage
        if status == 'concluído' and (usage is None or
            not isinstance(usage.get('input_tokens'), int) or not isinstance(usage.get('output_tokens'), int) or
            usage['input_tokens'] > task['max_input_tokens'] or usage['output_tokens'] > task['max_output_tokens'] or
            outcome.elapsed_seconds > task['timeout_seconds']):
            status = 'aguardando aprovação'
        message = outcome.events.message
        if status == 'aguardando aprovação' and not message:
            code = getattr(outcome, 'exit_code', None)
            message = f'Execução não verificada; código de saída: {code if code is not None else "indisponível"}. Revisão necessária.'
        store.finish_running(ident, status, message, outcome.events.usage, outcome.elapsed_seconds)
    except Exception:
        store.finish_running(ident, 'aguardando aprovação', 'Falha no executor; revise antes de nova tentativa.')
    return ident
