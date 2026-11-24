# Assistente residente — V0.3 experimental

Instale com `powershell -ExecutionPolicy Bypass -File scripts/instalar-assistente.ps1` e inicie com `powershell -ExecutionPolicy Bypass -File scripts/iniciar-assistente.ps1`. O processo usa `pythonw.exe` e aparece na bandeja do Windows; procure também nos ícones ocultos. Uma segunda sessão de voz, inclusive a V0.2, é recusada. A instalação não habilita inicialização automática.

Na bandeja: veja o estado, ative uma conversa sem falar a palavra, silencie ou reative o microfone, ajuste o tempo de inatividade e o limiar, ou saia. Diga “Jarvis” para começar e “encerrar conversa” para voltar a aguardar. O contexto é apagado no encerramento, na inatividade e ao silenciar. A gravação é temporária em memória, não é salva em arquivo. Silenciar interrompe a captura em até um bloco de áudio e descarta respostas pendentes; uma geração do Ollama já em andamento pode continuar no servidor, mas sua resposta é descartada. As opções ficam em `data/configuracao.json`; os registros rotativos em `logs/assistente.log` não contêm falas.

Para permitir inicialização automática somente quando desejar, execute `powershell -ExecutionPolicy Bypass -File scripts/inicializacao-windows.ps1 -Acao Habilitar`. Para verificar, use `-Acao Status`; para desfazer, `-Acao Desabilitar`. O atalho é criado apenas para o usuário atual. O script de desinstalação remove esse atalho e preserva ambiente, dados e modelos; encerre o processo pela bandeja.

## Limites e testes

Em espera há filtro simples de volume e transcrição Whisper `small` sob demanda: não é detector dedicado de palavra-chave, podendo falhar ou ativar por engano. O modelo permanece carregado após uso. V0.3 não oferece interrupção por voz enquanto fala; silencie pela bandeja. O reconhecimento e os dispositivos físicos ainda não foram homologados. Falhas de microfone, modelo ou fala entram em estado de erro e são tentadas novamente; falhas persistentes exigem corrigir a causa. O servidor Ollama precisa estar disponível com `qwen2.5:3b`. Não há execução arbitrária de comandos nem chamadas a APIs pagas.

Para testar V0.2 e V0.3, use-as em sequência: encerre o processo residente na bandeja antes de rodar `powershell -ExecutionPolicy Bypass -File scripts/iniciar-voz.ps1` (opcional `-PushToTalk`). Encerre a V0.2 com Ctrl+C antes de iniciar a V0.3. O modo texto permanece `python -m jarvis`. Para testes automatizados use `.venv\Scripts\python.exe -m unittest discover -s tests -v`.

Medições locais pontuais: processo da bandeja silenciado, sem modelos carregados, 89,4 MiB de RSS somando launcher e processo Python e 0% de CPU em uma janela de 2 s. Teste de integração com áudio sintetizado, transcrição real `small`, roteamento horário e síntese sem dispositivo físico levou 5,09 s com carregamento. Um teste de modelo `tiny` transcreveu incorretamente a palavra de ativação e foi descartado. As medições não representam estabilidade prolongada, uso de VRAM ou consumo elétrico.
