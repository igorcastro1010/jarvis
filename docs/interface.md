# Interface desktop V0.7 experimental

PySide6 Essentials foi escolhido por integrar Qt Widgets ao núcleo Python e à bandeja Windows sem servidor web, navegador ou processo Rust. Tauri usa WebView e Rust e exigiria comunicação com o backend Python; uma aplicação web local exigiria servidor e proteção de uma interface HTTP local. Não foi realizado benchmark comparativo entre as três opções. A interface é nativa, portanto Playwright não se aplica.

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-desktop.txt
.venv\Scripts\python.exe -m jarvis.desktop
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/criar-atalho-interface.ps1
```

O script cria `Jarvis Interface.lnk` na área de trabalho, apontando para `pythonw.exe`; não sobrescreve um atalho existente e não habilita inicialização automática. Fechar a janela minimiza para a bandeja quando ela está disponível; use **Sair** no menu da bandeja para encerrar. O botão compacto reduz a janela. As telas adaptam-se à largura disponível, mas ultrawide ainda não foi homologado fisicamente.

O painel circular indica o estado da **interface de texto**: disponível, processando ou erro. A animação durante processamento não simula o microfone. CPU e RAM são medições gerais do sistema via psutil; GPU é apresentada como indisponível. Chat usa o roteador e Ollama existentes em segundo plano. O histórico visível é salvo localmente em `JarvisLocal/conversas.sqlite3`, sem criptografia; o filtro de segredos é incompleto, portanto não inclua dados confidenciais. Histórico é visual e não restaura automaticamente o contexto do modelo após reiniciar.

Projetos podem ser cadastrados por nome e diretório Git existente, e pedidos podem ser enfileirados. Nenhum pedido é executado automaticamente. Memórias podem ser buscadas e corrigidas por ID e escopo, usando o cofre local existente. O catálogo permite buscar, ativar sugestões e gerar/copiar prompts; ativação não instala skills. A tela de configuração salva apenas inatividade e limiar do serviço de voz existente; reinicie esse serviço para aplicar. Ela não altera a inicialização Windows.

O serviço de voz e bandeja da V0.3 continuam separados: a janela ainda não captura áudio nem mostra o estado real desse serviço. Também faltam seleção de microfone/saída, volume/modelos, controles de inicialização, visualização dos grafos, cancelamento de tarefas pela janela, métricas GPU, e uma homologação física das notificações, bandeja, voz e ultrawide. Use [assistente.md](assistente.md) e [voz.md](voz.md) para os recursos existentes. Não há execução automática do Codex.

Verificação pontual Windows: interface ociosa sem modelos carregados, três processos incluindo lançadores, 86,3 MiB de RSS somados e 0,0% de CPU em janela de 2 segundos. Esta não é uma medição prolongada nem inclui inferência, áudio ou GPU. Capturas com dados de teste: [painel](screenshots/v07-dashboard.png) e [conversa](screenshots/v07-conversa.png).
