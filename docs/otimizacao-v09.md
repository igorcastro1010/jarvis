# V0.9 — auditoria e limitações

## Resultados experimentais

As medições foram feitas em processos isolados com Piper e Faster-Whisper CPU, frase sintética em memória, três repetições e sem microfone. RSS inclui bibliotecas e não equivale a pico ou memória exclusiva. As sínteses variaram entre execuções: a primeira foi reconhecida como “Jarvis” e a segunda como “Jervis”; portanto não há equivalência rigorosa de áudio nem evidência de melhoria de qualidade.

| Medição | Antes | Depois |
| --- | ---: | ---: |
| RSS após importar voz | 43,2 MiB | 43,2 MiB |
| RSS após carregar Piper | 146,8 MiB | 146,7 MiB |
| Primeiro reconhecimento | 9,00 s | 4,70 s |
| Reconhecimentos seguintes | 2,49 / 2,49 s | 2,69 / 2,50 s |
| RSS antes de liberar Whisper | 532,9 MiB | 532,3 MiB |
| Queda de RSS ao liberar Whisper | 303,2 MiB | 303,3 MiB |

As mudanças não otimizaram o motor de reconhecimento, e a diferença de carga fria não prova ganho. Em outra execução sintética com dez reconhecimentos, o RSS variou de 533,3 a 537,6 MiB; não é teste prolongado nem prova de ausência de vazamentos. Não se mediram todos os componentes simultaneamente. Uma consulta local ao diagnóstico do Ollama levou 47 ms; não é latência de inferência.

O Vulkan detectou RX 6600. O whisper.cpp oferece backend Vulkan, mas não havia SDK Vulkan, compilador C++ nem CMake no ambiente, e as releases oficiais consultadas não apresentaram pacote Windows Vulkan identificado. Não foi executada comparação real entre reconhecedores; permanece pendente em ambiente isolado, sem alterar drivers. Faster-Whisper continua padrão.

## Alterações e segurança

O diagnóstico sob demanda consulta CPU, RAM, disponibilidade e latência da API Ollama e VRAM dos modelos carregados reportada por `/api/ps`; utilização total de GPU e VRAM sem modelo são indicadas como indisponíveis. As informações são obtidas fora da thread visual. Após três falhas consecutivas, o serviço de voz aguarda reativação; ao encerrar, solicita liberação dos adaptadores. Cancelamento de uma inferência Ollama em andamento ainda não está implementado.

Uso do Ollama é registrado em arquivo local rotativo com data, modelo, contagens retornadas pela API e duração, sem prompt ou resposta. Cache de tokens indisponível na resposta permanece `null`. A busca de memória já é indexada incrementalmente e limitada por escopo; não foi adicionado cache de notas nem contexto Graphify sem validação de benefício e invalidação. Nenhuma redução de contexto foi homologada nesta etapa.

Junções Windows em pastas de memória agora são rejeitadas junto com links simbólicos; isso não prova proteção contra todas as corridas de alteração do sistema de arquivos. Ferramentas seguem com confirmações existentes e Codex automático desativado. Testes cobrem separação de projetos, comandos não autorizados e página sintética com JavaScript bloqueado por Playwright. Uma varredura limitada por padrões comuns nos arquivos rastreados não encontrou credenciais; não é auditoria completa de segredos ou histórico Git. Memória e histórico locais não são criptografados.

Find Skills foi consultada; candidatos encontrados para Windows e tokens tinham baixa adoção ou não eram apropriados. UI/UX Pro Max foi consultada na origem para rótulos e feedback. Não foram instaladas skills externas. Referências: [whisper.cpp](https://github.com/ggml-org/whisper.cpp), [releases oficiais](https://github.com/ggml-org/whisper.cpp/releases), [API Ollama](https://docs.ollama.com/api/chat), [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill).

Pendências: teste físico da voz integrada e automações, comparação Vulkan de STT, execução prolongada, medição conjunta, cancelamento real de inferência, atualização segura de caches e avaliação de Graphify. Não houve alteração global de driver nem uso de API paga.
