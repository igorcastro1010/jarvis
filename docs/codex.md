# Codex V0.5 — integração em construção

O cadastro e a fila locais estão disponíveis; **o executor automático ainda está bloqueado**. Nenhuma tarefa da fila é enviada ao Codex por enquanto. Os estados e solicitações ficam em `%USERPROFILE%\JarvisLocal\tarefas.sqlite3`, sem criptografia. Não inclua senhas, tokens ou dados sensíveis. O filtro automático é incompleto.

Cadastre apenas projetos que existem e que você autoriza o Jarvis a consultar:

```powershell
.venv\Scripts\python.exe -m jarvis.task_cli cadastrar --nome "Meu Projeto" --diretorio "C:\caminho\do\repositorio" --alias "projeto exemplo" --github "conta/repositorio"
```

O diretório deve ser a raiz de um repositório Git existente; `--github` é opcional e, se informado, deve coincidir com o `origin`. Todos os projetos são cadastrados sem permissão de escrita ou push. A identificação exige nome ou alias exato; aliases ambíguos são rejeitados. Não é criada branch nem worktree.

Envie um pedido pela interface por texto ou voz dizendo `codex projeto Meu Projeto: analise o README`. Também são aceitos `listar tarefas`, `status tarefa <id>` e `cancelar tarefa <id>`; o reconhecimento correto de ID por voz ainda não foi homologado. Ou use:

```powershell
.venv\Scripts\python.exe -m jarvis.task_cli enfileirar --projeto "Meu Projeto" "Analise o README"
.venv\Scripts\python.exe -m jarvis.task_cli listar
.venv\Scripts\python.exe -m jarvis.task_cli status <id>
.venv\Scripts\python.exe -m jarvis.task_cli cancelar <id>
```

O cancelamento de uma tarefa aguardando é efetivo. A sinalização de cancelamento de tarefa executando e a recuperação de estado foram testadas como componentes, mas não há executor ativo para homologar interrupção de processos. Trabalhos interrompidos são marcados para revisão manual pelo método de recuperação, nunca reiniciados automaticamente. Não há notificação por voz de conclusão, integração GitHub, commits automáticos, leitura de Graphify pelo Codex ou captura de progresso real do executor.

## Validação e bloqueio

O CLI detectado foi `codex-cli 0.163.0-alpha.10.2`, autenticado via ChatGPT. Sua opção `exec --json` emite eventos e uso de tokens. Uma solicitação simples, em repositório fictício, respondeu `OK` com `--ignore-user-config`, `--ephemeral` e sandbox somente leitura; informou 21.251 tokens de entrada, dos quais 12.416 em cache, e 6 de saída. Um teste separado do sandbox MXC leu um arquivo autorizado e negou a leitura de outro fora do diretório.

No entanto, ao solicitar leitura de README em um repositório fictício com o perfil MXC restrito, o processo retornou código zero mas o próprio Codex informou que não conseguiu acessar o README; listagem de diretório foi negada. Esse turno consumiu 64.270 tokens de entrada (54.912 em cache) e 129 de saída. Código zero não prova conclusão. Até resolver e testar essa diferença, o Jarvis só enfileira tarefas e não invoca o Codex automaticamente. Um MCP pré-configurado também reportou erro de autenticação; não houve alteração de suas configurações.

Não há uso de APIs pagas adicionais nesta integração, mas o Codex consome a cota da conta ChatGPT e envia os dados fornecidos a ele para o serviço. A interface por voz e a segurança dos projetos reais não foram homologadas. Nenhum projeto real foi alterado durante os testes.
