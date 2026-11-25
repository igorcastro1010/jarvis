# Interface desktop V0.7.1 experimental

A interface inicia o serviço residente de voz no mesmo processo. Diga “Jarvis” ou use o texto; transcrições aceitas e respostas aparecem no chat. Silenciar interrompe a captura ou reprodução e invalida resultados pendentes. A janela acompanha os estados do serviço e o círculo responde ao nível medido do microfone. Texto e voz ainda têm contextos temporários separados. A voz unificada não foi homologada fisicamente.

Nas configurações, liste e selecione dispositivos, escolha `small` ou `tiny` para reconhecimento local e ajuste o volume do Piper; os modelos precisam estar instalados localmente. Após salvar, reinicie a aplicação para aplicar dispositivos e modelos. Índices de dispositivos podem mudar quando periféricos são reconectados: confira a lista novamente. A opção de histórico desliga novos registros e não apaga os existentes. Botões explícitos habilitam ou desabilitam a inicialização Windows da interface; ela começa desabilitada e nenhuma ação de inicialização é realizada automaticamente.

PySide6 Essentials foi escolhido por integrar Qt Widgets ao núcleo Python e à bandeja Windows sem servidor web, navegador ou processo Rust. Tauri usa WebView e Rust e exigiria comunicação com o backend Python; uma aplicação web local exigiria servidor e proteção de uma interface HTTP local. Não foi realizado benchmark comparativo entre as três opções. A interface é nativa, portanto Playwright não se aplica.

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-desktop.txt
.venv\Scripts\python.exe -m jarvis.desktop
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/criar-atalho-interface.ps1
```

O script cria `Jarvis Interface.lnk` na área de trabalho, apontando para `pythonw.exe`; não sobrescreve um atalho existente e não habilita inicialização automática. Fechar a janela minimiza para a bandeja quando ela está disponível; use **Sair** no menu da bandeja para encerrar. O botão compacto reduz a janela. As telas adaptam-se à largura disponível, mas ultrawide ainda não foi homologado fisicamente.

CPU e RAM são medições gerais do sistema via psutil; GPU é apresentada como indisponível. Chat usa o roteador e Ollama existentes em segundo plano. Quando ativado, o histórico é salvo localmente em `JarvisLocal/conversas.sqlite3`, sem criptografia; o filtro de segredos é incompleto, portanto não inclua dados confidenciais. Histórico é visual e não restaura automaticamente o contexto do modelo após reiniciar.

Projetos podem ser cadastrados por nome e diretório Git existente, e pedidos podem ser enfileirados. Nenhum pedido é executado automaticamente. Memórias podem ser buscadas e corrigidas por ID e escopo, usando o cofre local existente. O grafo já gerado pode ser consultado sob demanda como lista de relações, limitada a 300 nós e conexões. O catálogo permite buscar, ativar sugestões e gerar/copiar prompts; ativação não instala skills.

Faltam testes de microfone e de fala acionados pela interface, visualização gráfica interativa, cancelamento de tarefas pela janela e métricas GPU AMD. A seleção de áudio, notificações, bandeja, voz integrada e ultrawide precisam de homologação física. O indicador de fala informa estado, mas a animação reativa ao nível mede somente a captura de microfone. Não há execução automática do Codex. A V0.2 anterior teve homologação física inicial relatada em [voz.md](voz.md).

Verificação pontual Windows: interface ociosa sem modelos carregados, três processos incluindo lançadores, 86,3 MiB de RSS somados e 0,0% de CPU em janela de 2 segundos. Esta não é uma medição prolongada nem inclui inferência, áudio ou GPU. Capturas com dados de teste: [painel](screenshots/v07-dashboard.png) e [conversa](screenshots/v07-conversa.png).
