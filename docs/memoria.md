# Memória V0.4 experimental

O cofre ativo é migrado na primeira utilização para `%USERPROFILE%\JarvisLocal\Cofre Jarvis`; `JARVIS_LOCAL_DIR` permite definir outra pasta fora do OneDrive. A migração copia sem excluir nem sobrescrever a origem em `data/Cofre Jarvis`, que pode continuar sincronizada. Abra a nova pasta no Obsidian. As notas gerenciadas ficam em `Memoria Jarvis/`, separadas por contexto e categoria. O índice SQLite é derivado; notas são Markdown editável. Origem e data são gravadas pelo sistema. O contexto temporário é apagado ao trocar de projeto, encerrar ou silenciar. Memórias não são autorização para executar ações.

Exemplos por texto ou voz (a pontuação e o ID precisam ser reconhecidos corretamente):

- `lembre que prefiro respostas curtas`
- `registre preferência: gosto de azul`
- `projeto alfa: registre decisão: usar azul no uniforme`
- `projeto alfa: busque memória sobre uniforme`
- `projeto alfa: resuma memória sobre uniforme`
- `projeto alfa: corrija memória 123456abcdef para usar verde no uniforme`
- `projeto alfa: esqueça memória 123456abcdef`

Os IDs reais são informados ao registrar ou buscar. As categorias aceitas são `pessoal`, `preferência`, `projeto`, `decisão`, `tarefa` e `histórico`. O prefixo `projeto nome:` precisa ser usado em cada fala para acessar aquele contexto; sem ele, só a memória pessoal é pesquisada. A busca é textual por palavras normalizadas, não entende sinônimos. O resumo seleciona trechos existentes, não inventa fatos. Até três trechos de no máximo 300 caracteres são enviados ao Ollama local quando há correspondência. A memória não é criada automaticamente a partir de conversas. Não há exclusão definitiva por comando: esquecer move para `Arquivo/`, e corrigir também preserva versão anterior.

O filtro de segredos é preventivo e incompleto; nunca registre senhas, tokens ou chaves. Notas e backups não são criptografados. A cópia antiga e backups anteriores continuam no OneDrive e podem ser sincronizados; a migração não os apaga. A pasta local fica fora do OneDrive detectado, mas outros serviços de backup podem sincronizá-la. Arquivos derivados podem conter cópias dos dados. Notas com propriedades não reconhecidas são ignoradas pelo índice.

## Backup local

Crie uma cópia ZIP local fora do cofre, sem sobrescrever outra: `.venv\Scripts\python.exe -m jarvis.memory_backup backup "$env:USERPROFILE\JarvisLocal\Cofre Jarvis" "$env:USERPROFILE\JarvisLocal\backup.zip"`. Restaure para uma **pasta nova**: `.venv\Scripts\python.exe -m jarvis.memory_backup restaurar "$env:USERPROFILE\JarvisLocal\backup.zip" "$env:USERPROFILE\JarvisLocal\cofre-recuperado"`. O índice SQLite e configuração `.obsidian` não são copiados. O ZIP não é criptografado.

## Graphify

O ambiente isolado pode ser preparado com `powershell -ExecutionPolicy Bypass -File scripts/instalar-memoria.ps1`. Gere um grafo pessoal com `.venv\Scripts\python.exe -m jarvis.graph_memory` ou de um único projeto com `--projeto alfa`. A extração usa `http://127.0.0.1:11434/v1`, modelo `qwen2.5:3b`, e grava no cofre local. Ao corrigir ou arquivar, o grafo ativo e seus caches são movidos para `.jarvis-grafos-invalidados`, não reutilizados; eles ainda contêm dados e não são apagados. Grafos antigos em `data/grafos/` também permanecem. Não rode geração de grafo simultaneamente com edição ou arquivamento. A busca conversacional ainda não consulta o grafo.

## Limitações e medições

Busca semântica por embeddings está pendente; o Graphify fornece relações inferidas, não uma busca semântica integrada. Não há exclusão permanente nem confirmação conversacional para isso. O reconhecimento de voz físico e as versões anteriores seguem sem homologação física. O sistema não dá ferramentas ou execução de comandos ao modelo. Um teste com 100 notas fictícias levou 2,79 s para criar e 41 ms na primeira busca, 35 ms na segunda, com 22 MiB de RSS do processo. Um grafo fictício local levou 15,73 s; uma consulta real ao Ollama com memória fictícia respondeu corretamente em 8,93 s incluindo carga. Não são benchmarks de produção.
