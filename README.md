# Jarvis

Base experimental independente para um assistente pessoal local no Windows. A V0.2 teve homologação física inicial relatada pelo usuário em 24/11/2026; a voz unificada e a automação V0.8 ainda precisam de teste físico. Ferramentas operam com permissões limitadas e confirmação para ações sensíveis.

Execute `python -m jarvis` para experimentar por texto. Depois de instalar as dependências de voz, use `.venv\Scripts\python.exe -m unittest discover -s tests -v` para testar. A conversação livre requer Ollama local e o modelo `qwen2.5:3b`. O roteamento para Codex apenas informa que falta integração; não executa comandos.

Consulte [ROADMAP.md](ROADMAP.md), [BACKLOG.md](BACKLOG.md), [SECURITY.md](SECURITY.md) e [docs/auditoria.md](docs/auditoria.md). Não coloque dados pessoais ou credenciais no repositório.

Para instalar e iniciar a conversa local por voz, consulte [docs/voz.md](docs/voz.md).

Para a versão experimental em segundo plano, bandeja e inicialização opcional, consulte [docs/assistente.md](docs/assistente.md). Os modos de voz usam o mesmo bloqueio e devem ser testados em sequência.

Para a memória local experimental, comandos, privacidade, backup e Graphify, consulte [docs/memoria.md](docs/memoria.md).

O cadastro e a fila para Codex estão disponíveis, mas o executor automático ainda está bloqueado; a investigação da V0.5.3 está em [docs/codex.md](docs/codex.md).

O catálogo experimental de skills e a geração manual de prompts estão descritos em [docs/skills.md](docs/skills.md).

A interface desktop experimental e suas limitações estão em [docs/interface.md](docs/interface.md).

A identidade, o contexto compartilhado e as medições da V0.7.2 estão em [docs/conversacao.md](docs/conversacao.md).

Medições pontuais e limitações da auditoria de recursos estão em [docs/auditoria-desempenho.md](docs/auditoria-desempenho.md).

Comandos, fontes e permissões da automação experimental estão em [docs/automacao.md](docs/automacao.md).
