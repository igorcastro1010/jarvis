# Jarvis

Base experimental independente para um assistente pessoal local no Windows. O modo de voz é experimental e ainda precisa de homologação com microfone e alto-falantes reais; não executa ações automaticamente.

Execute `python -m jarvis` para experimentar por texto. Depois de instalar as dependências de voz, use `.venv\Scripts\python.exe -m unittest discover -s tests -v` para testar. A conversação livre requer Ollama local e o modelo `qwen2.5:3b`. O roteamento para Codex apenas informa que falta integração; não executa comandos.

Consulte [ROADMAP.md](ROADMAP.md), [BACKLOG.md](BACKLOG.md), [SECURITY.md](SECURITY.md) e [docs/auditoria.md](docs/auditoria.md). Não coloque dados pessoais ou credenciais no repositório.

Para instalar e iniciar a conversa local por voz, consulte [docs/voz.md](docs/voz.md).

Para a versão experimental em segundo plano, bandeja e inicialização opcional, consulte [docs/assistente.md](docs/assistente.md). Os modos de voz usam o mesmo bloqueio e devem ser testados em sequência.

Para a memória local experimental, comandos, privacidade, backup e Graphify, consulte [docs/memoria.md](docs/memoria.md).
