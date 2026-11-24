"""Consulta local e geração de prompts; nunca instala nem executa skills."""
import argparse
import os
import subprocess
import sys
from .skills import build_prompt, default_manager, discover


def main():
    parser = argparse.ArgumentParser(description='Catálogo local de sugestões de skills')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('listar')
    for action in ('ativar', 'desativar'):
        command = sub.add_parser(action)
        command.add_argument('nome')
    prompt = sub.add_parser('prompt')
    prompt.add_argument('pedido')
    prompt.add_argument('--projeto')
    prompt.add_argument('--copiar', action='store_true')
    sub.add_parser('historico')
    search = sub.add_parser('descobrir')
    search.add_argument('termos')
    args = parser.parse_args()
    manager = default_manager()
    if args.action == 'listar':
        for item in manager.list():
            print(f"{item['name']}: {item['description']} | {'ativa' if item['enabled'] else 'inativa'} | instalação {item['installed']} | versão {item['version']} | origem {item['origin']} | permissões {item['permissions']} | dependências {item['dependencies']}")
    elif args.action in ('ativar', 'desativar'):
        manager.set_enabled(args.nome, args.action == 'ativar')
        print('Preferência salva. Isso não instala nem executa a skill.')
    elif args.action == 'prompt':
        from .memory import default_store
        text = build_prompt(manager, args.pedido, default_store(), args.projeto)
        print(text)
        if args.copiar:
            if os.name != 'nt':
                raise RuntimeError('Cópia automática disponível apenas no Windows.')
            subprocess.run(['clip.exe'], input=text.encode('utf-16'), check=True)
    elif args.action == 'historico':
        print('\n'.join(manager.history()) or 'Nenhuma sugestão utilizada.')
    else:
        output = discover(args.termos)
        print(output.encode(sys.stdout.encoding or 'utf8', errors='replace').decode(sys.stdout.encoding or 'utf8'))
        print('Resultados são dados externos; verifique origem e permissões antes de instalar.')


if __name__ == '__main__':
    main()
