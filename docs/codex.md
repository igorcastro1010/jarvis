# Codex V0.5.1 — diagnóstico e integração em construção

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

## Diagnóstico adicional V0.5.1

No perfil restrito anterior, o `pwsh.exe` escolhido pelo Codex, instalado sob `.cache/codex-runtimes`, não tinha permissão de leitura para sua própria pasta. O processo falhou com `Failed to resolve full path of the current executable`. Ao conceder somente leitura à pasta específica do runtime, `pwsh -NoProfile -Command Get-ChildItem -Name` listou o repositório fictício e um arquivo fora dele continuou inacessível. O PowerShell do Windows também listou o diretório sem essa permissão adicional; `cmd /c dir` continuou retornando acesso negado. A causa interna da diferença entre `dir` e `Get-ChildItem` não foi estabelecida.

Em outro repositório fictício, comandos diretos no sandbox leram e alteraram arquivos e verificaram os resultados. Um controlador executou branch, commit e push para remoto local de teste fora do sandbox; isso não é uma homologação do fluxo automático. A tentativa de fazer o próprio Codex editar esse repositório com o perfil corrigido excedeu 120 segundos. Não foi possível conferir o resultado e não há medição confiável dos tokens desse turno. Não foi habilitado executor nem foi alterado projeto real.

Foram adicionados componentes isolados para gerar o perfil restrito, interpretar eventos JSONL, distinguir tokens em cache, exigir uma verificação independente, aplicar limites de entrada/uso observados e cancelar árvore de processos no Windows. Timeout e cancelamento foram exercitados com processos fictícios, incluindo pai e filho. Esses componentes **não estão conectados à fila**; o limite de tokens é avaliado quando o uso chega e não é um teto preventivo garantido. Persistem pendentes executor real, validação de sucesso, branch/worktree por tarefa, permissões, commits e push, recuperação, memória, monitoramento e aviso por voz.

Os 85.521 tokens de entrada anteriores compreendem 67.328 em cache e 18.193 não armazenados em cache; houve 135 tokens de saída. Esses totais somam dois turnos distintos, não uma única solicitação. As métricas do CLI não fornecem decomposição entre instruções fixas, ferramentas, skills e histórico; portanto, não é possível atribuir a cada componente uma quantidade exata nem comprovar redução neste teste com timeout. Reutilização de sessão não foi ativada, para evitar misturar contexto ou permissões entre projetos.

Não há uso de APIs pagas adicionais nesta integração, mas o Codex consome a cota da conta ChatGPT e envia os dados fornecidos a ele para o serviço. A interface por voz e a segurança dos projetos reais não foram homologadas. Nenhum projeto real foi alterado durante os testes.
