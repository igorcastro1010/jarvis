"""Cadastro explícito e consulta da fila local."""
import argparse
import json
from .tasks import default_tasks


def main():
    parser = argparse.ArgumentParser(description='Projetos e fila Codex do Jarvis')
    sub = parser.add_subparsers(dest='action', required=True)
    register = sub.add_parser('cadastrar')
    register.add_argument('--nome', required=True)
    register.add_argument('--diretorio', required=True)
    register.add_argument('--alias', action='append', default=[])
    register.add_argument('--github')
    submit = sub.add_parser('enfileirar')
    submit.add_argument('--projeto', required=True)
    submit.add_argument('--timeout-segundos', type=int, default=120)
    submit.add_argument('--max-entrada', type=int, default=100000)
    submit.add_argument('--max-saida', type=int, default=4000)
    submit.add_argument('pedido')
    sub.add_parser('listar')
    status = sub.add_parser('status'); status.add_argument('id')
    cancel = sub.add_parser('cancelar'); cancel.add_argument('id')
    args = parser.parse_args(); db = default_tasks()
    if args.action == 'cadastrar':
        db.register(args.nome, args.alias, args.diretorio, args.github)
        print('Projeto cadastrado com permissões de escrita e push desativadas.')
    elif args.action == 'enfileirar':
        print('Tarefa registrada:', db.submit(args.projeto, args.pedido, timeout_seconds=args.timeout_segundos,
                                               max_input_tokens=args.max_entrada, max_output_tokens=args.max_saida))
        print('Execução automática ainda não está habilitada.')
    elif args.action == 'listar': print(json.dumps(db.list(), ensure_ascii=False, indent=2))
    elif args.action == 'status':
        task = db.get(args.id)
        print(json.dumps({k: task[k] for k in ('id','project','status','created','updated','result','input_tokens','cached_input_tokens','output_tokens','elapsed_seconds')}, ensure_ascii=False, indent=2))
    elif args.action == 'cancelar': db.cancel(args.id); print('Cancelamento registrado.')


if __name__ == '__main__': main()
