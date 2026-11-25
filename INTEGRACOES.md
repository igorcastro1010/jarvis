# Projetos oficiais e instalações locais

Esta branch preserva o histórico do Jarvis próprio e reúne cópias versionadas dos projetos oficiais em diretórios separados. O desenvolvimento do núcleo próprio foi encerrado.

- `integracoes/OpenJarvis`: snapshot do projeto [OpenJarvis](https://github.com/open-jarvis/OpenJarvis), commit oficial `86f75ef7`.
- `integracoes/Habblaud`: snapshot do projeto [Habblaud](https://github.com/marmottajr/habblaud), commit oficial `faa1a01`.

As importações usam `git subtree --squash`: preservam o conteúdo e a referência aos commits de origem, sem incluir o histórico completo dos repositórios oficiais. As licenças originais permanecem nos respectivos diretórios.

## Uso no computador atual

As cópias integradas são para versionamento e não substituem as instalações locais existentes. Use os atalhos **Jarvis Interface** e **Habblaud** na área de trabalho. O OpenJarvis utiliza Ollama local e o modelo `qwen2.5:3b`; o Habblaud monitora sessões locais do Codex conforme seus recursos nativos.

Os scripts e configurações locais, autenticações, memórias, gravações e backups não estão incluídos nesta branch. A interface e o monitoramento não implicam integração nativa entre os dois projetos. A homologação física de voz continua pendente.
