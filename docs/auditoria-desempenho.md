# Auditoria de desempenho — 24/11/2026

Medições pontuais em Windows, i5-10400F, 16 GB e RX 6600. O Jarvis já aberto pelo usuário foi preservado. Os testes de voz abaixo usam Piper para sintetizar uma frase em memória e Faster-Whisper para transcrevê-la, sem microfone nem arquivos de áudio. Não representam conversação física completa, todos os sotaques ou estabilidade prolongada. RSS é memória residente do processo, não pico nem memória privada; percentuais de CPU usam um núcleo como 100%.

| Medição | Antes | Depois | Observação |
| --- | ---: | ---: | --- |
| Processo isolado após importar `jarvis.voice` | 77,1 MiB; 1,02 s | 42,8 MiB; 0,43 s | Uma amostra por versão; bibliotecas de inferência agora carregam sob demanda. |
| Piper ao carregar, RSS incremental | 86,5 MiB | 85,8 MiB | Modelo pt-BR Faber; processo também contém bibliotecas. |
| Piper ao sintetizar, RSS incremental | 36,4 MiB | 37,1 MiB | Frase curta, CPU; não mede qualidade física. |
| Primeiro reconhecimento Whisper `small` int8 CPU | 5,65 s | 4,83 s | Inclui carregar o modelo e transcrever; amostras isoladas, não prova de ganho de inferência. |
| Reconhecimento já carregado | 2,97 e 2,91 s | 2,86 e 2,80 s | Mesma frase sintética; CPU próxima de dois núcleos durante inferência. |

Em outro teste de dez reconhecimentos após a mudança, o RSS ao fim de cada turno variou de 532,4 a 536,8 MiB; a mesma frase foi transcrita corretamente em todos. Isso não demonstra ausência de vazamentos em longas sessões. Ao liberar o reconhecedor isolado, o RSS caiu 307 MiB; recarregar e transcrever levou 4,21 s. Para evitar essa latência na palavra de ativação, os modelos permanecem carregados enquanto o assistente espera. Após **120 s silenciado**, o serviço libera Whisper e Piper no próprio thread; a próxima utilização recarrega os modelos e pode demorar. O timer visual do círculo deixa de acordar a cada 100 ms quando não há processamento. Uma nova sessão com áudio real ainda precisa ser homologada.

O processo principal do Jarvis já aberto apresentou 723,9 MiB de RSS e 0,8% de CPU em dois segundos; o lançador `pythonw` usou 6,0 MiB. São dois processos pai/filho, não prova de duas cópias de modelos. O Ollama apresentou um processo servidor (~50,9 MiB) e um aplicativo (~47,6 MiB), sem contar o runner nem somar memória compartilhada. Esses valores são da versão já aberta, não uma comparação antes/depois controlada da interface em produção.

## GPU e modelos

Na chamada local `qwen2.5:3b`, o log do Ollama indicou `Vulkan0 (AMD Radeon RX 6600)` e `37/37` camadas transferidas; `ollama ps` mostrou `100% GPU`. `/api/ps` relatou `size_vram` de 2.085.963.693 bytes para o modelo Q4_K_M com contexto 2048. A chamada de teste demorou 7,19 s, incluindo 7,00 s de carregamento, para resposta curta. Isso comprova o backend informado nessa chamada, não mede utilização percentual ou pico de VRAM por componente. O `keep_alive` do projeto continua em dois minutos: reduz recarregamento entre turnos, mas retém VRAM; não foi alterado sem amostras comparáveis de uso real.

O CTranslate2 instalado é 4.9.1 e informou zero dispositivos via `get_cuda_device_count()`; Faster-Whisper permanece em CPU int8. A documentação oficial [CTranslate2 ROCm no Windows](https://opennmt.net/CTranslate2/building_rocm_windows.html) descreve uma compilação HIP testada em RX 7900 XTX, não demonstra funcionamento nesta RX 6600. O [whisper.cpp](https://github.com/ggml-org/whisper.cpp#vulkan-gpu-support) oferece compilação Vulkan; `vulkaninfo` detectou a RX 6600, mas não havia `whisper-cli` ou CMake disponíveis para uma comparação isolada. Vulkan detectado não comprova Whisper acelerado. Não foram instalados drivers, bibliotecas HIP, ferramentas globais ou modelos alternativos; nenhuma tecnologia foi substituída. Um comparativo de qualidade e latência com áudio PT-BR e hardware físico permanece pendente.

Para reproduzir o teste isolado: `.venv\Scripts\python.exe -m scripts.auditar_componentes --repeticoes 10`. Ele requer os modelos de voz já instalados e usa dados sintéticos, sem chamadas pagas.
