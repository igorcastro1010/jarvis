# Segurança

A aplicação atual não possui executor de comandos nem acesso automático a arquivos, microfone ou navegador. Futuras capacidades devem usar lista explícita de permissões, confirmação específica para ações sensíveis, cancelamento de emergência e registros sem segredos. Não exponha servidores locais à rede. Nunca inicie impressão física, publique em produção ou altere credenciais automaticamente.

O roteador de texto é heurístico e não é uma fronteira de segurança. A autorização deve ser verificada na própria ferramenta, independentemente do roteamento. O conteúdo enviado ao Ollama permanece local apenas se o serviço configurado for local e não usar ferramentas externas.
