# Conversação V0.7.2

A identidade do Jarvis fica no código como instrução persistente; o Ollama recebe orientação para português brasileiro, concisão e não alegar ações inexistentes. Pergunte “o que você pode fazer?” para consultar um resumo determinístico, com projetos cadastrados, sugestões de skills ativas e disponibilidade básica das ferramentas. Sugestões de skills não são execução. O modelo não recebe ferramentas de automação e o Codex automático permanece desativado.

O contexto temporário é compartilhado entre texto e voz na interface, com limite de quatro pares e processamento serializado fora da thread de interface. Silenciar ou encerrar a conversa por voz limpa o contexto; o histórico visual salvo é independente e não restaura o contexto após reiniciar. Cancelamentos descartam contexto pendente. A V0.7.1 ainda não tem homologação física da integração; a nova alternância voz/texto e transcrição também precisam de teste físico.

Faster-Whisper recebe `initial_prompt` com Jarvis, Codex, ChatGPT, Chrome, Obsidian, Graphify, GitHub e Fortalaka. Esse vocabulário é uma pista, não correção automática nem garantia de acerto. Continuam os parâmetros locais existentes (`small`, CPU int8, beam 3 e VAD); o modelo `tiny` pode ser selecionado. Não foram alteradas frases transcritas por substituição de palavras.

O chat identifica emissor, modalidade e horário de novas mensagens, com rolagem automática. Mensagens antigas sem horário mostram `--:--`. O histórico opcional continua em SQLite local sem criptografia; o filtro de segredos é incompleto. A [captura](screenshots/v072-conversa.png) usa mensagens fictícias.

## Avaliação pontual do modelo

O único modelo presente na verificação foi `qwen2.5:3b`. Em uma chamada real e curta ao Ollama local, perguntou-se a capital do Ceará; respondeu corretamente Fortaleza, em 19,05 s, incluindo 18,71 s de carregamento informados pelo Ollama; 49 tokens de entrada e 11 de saída. `/api/ps` informou 2.163.558.317 bytes de `size_vram` após a chamada. É uma única amostra, sem comparação de qualidade, medição de energia ou teste de voz fim a fim.

Alternativas para avaliação futura: [Qwen 2.5 1.5B](https://ollama.com/library/qwen2.5%3A1.5b), arquivo de aproximadamente 986 MB, e [Llama 3.2 3B](https://ollama.com/library/llama3.2%3A3b), com suporte declarado a português. Não foram baixadas ou medidas nesta etapa; tamanhos de arquivos não estabelecem consumo em execução nem qualidade. O modelo atual não foi substituído.
