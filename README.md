# Jarvis

Base experimental independente para um assistente pessoal local no Windows. O modo de voz é experimental e ainda precisa de homologação com microfone e alto-falantes reais; não executa ações automaticamente.

Execute `python -m jarvis` para experimentar por texto e `python -m unittest discover -s tests -v` para testar. A conversação livre requer Ollama local e o modelo `qwen2.5:3b`; não são instalados automaticamente. O roteamento para Codex apenas informa que falta integração; não executa comandos.

Consulte [ROADMAP.md](ROADMAP.md), [BACKLOG.md](BACKLOG.md), [SECURITY.md](SECURITY.md) e [docs/auditoria.md](docs/auditoria.md). Não coloque dados pessoais ou credenciais no repositório.

Para instalar e iniciar a conversa local por voz, consulte [docs/voz.md](docs/voz.md).
