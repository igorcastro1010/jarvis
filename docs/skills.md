# Skills V0.6 — catálogo e prompts

O catálogo é uma lista local de **sugestões**, não um executor. As entradas Playwright, UI/UX Pro Max e Find Skills registram origem, descrição, dependências e permissões previstas; versões não foram verificadas. A verificação de instalação procura apenas `SKILL.md` em `%CODEX_HOME%\skills` (ou `%USERPROFILE%\.codex\skills`): encontrar arquivo não comprova origem, segurança, versão ou compatibilidade. Ativar significa permitir sugerir, não instalar, conceder permissão ou executar. Todas começam desativadas. A seleção é por palavras, não por classificação semântica.

```powershell
.venv\Scripts\python.exe -m jarvis.skills_cli listar
.venv\Scripts\python.exe -m jarvis.skills_cli ativar playwright
.venv\Scripts\python.exe -m jarvis.skills_cli descobrir "playwright"
.venv\Scripts\python.exe -m jarvis.skills_cli prompt "teste o navegador" --projeto "Exemplo" --copiar
.venv\Scripts\python.exe -m jarvis.skills_cli historico
.venv\Scripts\python.exe -m jarvis.skills_cli desativar playwright
```

A busca usa `npx --no-install skills find` por meio do Node/npm instalados, somente quando solicitada, e requer rede e CLI já presente no cache npm. Resultados são dados externos, não autorização ou instruções. A instalação de qualquer skill externa exige autorização explícita e revisão prévia; Jarvis não oferece instalação automática. A cópia usa a área de transferência Windows e é acionada apenas pela opção explícita. Reveja o prompt antes de copiar ou enviá-lo: a detecção de segredos é incompleta.

Pelo texto ou voz, diga `listar skills`, `ativar skill playwright`, `desativar skill playwright`, `buscar skills playwright`, `gerar prompt: teste o navegador` ou `projeto Exemplo: gerar prompt: teste o navegador`. Comandos por voz usam o mesmo roteador de texto; reconhecimento físico ainda não foi homologado. A lista de permissões e dependências detalhada fica na CLI.

Os prompts incluem até três sugestões ativas e três trechos de memória do escopo indicado, identificados como dados não confiáveis. A memória usa o índice incremental existente; não inclui o cofre inteiro. O histórico local registra apenas nomes e data de sugestões usadas, não pedidos ou conteúdo de memórias. Ele não demonstra que uma skill foi executada. Os dados ficam em `%USERPROFILE%\JarvisLocal\skills.sqlite3` ou em `JARVIS_LOCAL_DIR`.

Graphify não é consultado neste fluxo: falta validar recuperação segura do grafo por escopo e sua correspondência com notas válidas. As integrações Playwright e UI/UX são sugestões de catálogo, não ferramentas instaladas ou homologadas. Não há cache de resultados de busca externa. O App Server experimental e a execução automática Codex continuam desativados. Para usar o prompt, copie-o e revise-o no Codex manualmente.
