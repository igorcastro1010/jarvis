# Memória V0.4 experimental

O cofre de Jarvis existente fica em `data/Cofre Jarvis`; as notas gerenciadas ficam em `Memoria Jarvis/`, com diretórios separados por contexto e categoria. O restante do cofre não é alterado automaticamente. O índice SQLite local é derivado das notas e pode ser reconstruído; as notas são Markdown com propriedades JSON válidas em YAML, e o texto pode ser editado. Origem e data são gravadas pelo sistema. O contexto temporário é apagado ao trocar de projeto, encerrar ou silenciar. O conteúdo da memória é dado não confiável, não autorização para executar ações.

Exemplos por texto ou voz (a pontuação e o ID precisam ser reconhecidos corretamente):

- `lembre que prefiro respostas curtas`
- `registre preferência: gosto de azul`
- `projeto alfa: registre decisão: usar azul no uniforme`
- `projeto alfa: busque memória sobre uniforme`
- `projeto alfa: resuma memória sobre uniforme`
- `projeto alfa: corrija memória 123456abcdef para usar verde no uniforme`
- `projeto alfa: esqueça memória 123456abcdef`

Os IDs reais são informados ao registrar ou buscar. As categorias aceitas são `pessoal`, `preferência`, `projeto`, `decisão`, `tarefa` e `histórico`. O prefixo `projeto nome:` precisa ser usado em cada fala para acessar aquele contexto; sem ele, só a memória pessoal é pesquisada. A busca é textual por palavras normalizadas, não entende sinônimos. O resumo seleciona trechos existentes, não inventa fatos. Até três trechos de no máximo 300 caracteres são enviados ao Ollama local quando há correspondência. A memória não é criada automaticamente a partir de conversas. Não há exclusão definitiva por comando: esquecer move para `Arquivo/`, e corrigir também preserva versão anterior.

O filtro de segredos é preventivo e incompleto; nunca registre senhas, tokens ou chaves. Notas e backups não são criptografados. **A pasta atual está no OneDrive**: embora esteja ignorada pelo Git, pode ser sincronizada pela Microsoft conforme a configuração da conta. Não equivale a armazenamento apenas no dispositivo. Arquivos derivados de busca e grafos podem conter cópias dos dados. Uma nota editada com sintaxe de propriedades que o índice não reconheça é ignorada até ser corrigida.

## Backup local

Crie uma cópia ZIP fora do cofre, sem sobrescrever outra: `.venv\Scripts\python.exe -m jarvis.memory_backup backup "data/Cofre Jarvis" "backups/cofre-2026-11-24.zip"`. Restaure para uma **pasta nova**: `.venv\Scripts\python.exe -m jarvis.memory_backup restaurar "backups/cofre-2026-11-24.zip" "data/cofre-recuperado"`. O índice SQLite e configuração interna `.obsidian` não são copiados; o índice pode ser reconstruído. O ZIP não é criptografado. Confirme o conteúdo restaurado antes de substituir dados manualmente.

## Graphify

O ambiente isolado pode ser preparado com `powershell -ExecutionPolicy Bypass -File scripts/instalar-memoria.ps1`. Gere um grafo pessoal com `.venv\Scripts\python.exe -m jarvis.graph_memory` ou de um único projeto com `--projeto alfa`. A extração usa explicitamente `http://127.0.0.1:11434/v1`, modelo `qwen2.5:3b`, e salva em `data/grafos/` ignorado pelo Git. Ela é sob demanda, não automática, usa cache incremental próprio e não alimenta ainda a busca conversacional. Após arquivar uma nota, grafos e caches antigos podem manter cópias; revise-os antes de considerar o dado removido. Verifique grafos antes de confiar nas relações inferidas.

## Limitações e medições

Busca semântica por embeddings está pendente; o Graphify fornece relações inferidas, não uma busca semântica integrada. Não há exclusão permanente nem confirmação conversacional para isso. O reconhecimento de voz físico e as versões anteriores seguem sem homologação física. O sistema não dá ferramentas ou execução de comandos ao modelo. Um teste com 100 notas fictícias levou 2,79 s para criar e 41 ms na primeira busca, 35 ms na segunda, com 22 MiB de RSS do processo. Um grafo fictício local levou 15,73 s; uma consulta real ao Ollama com memória fictícia respondeu corretamente em 8,93 s incluindo carga. Não são benchmarks de produção.
