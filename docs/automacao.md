# Automação e internet — V0.8 experimental

O roteador reconhece frases explícitas, por texto ou voz, antes do Ollama. Exemplos:

- `abrir youtube`, `abrir chatgpt`, `abrir github`, `abrir chrome`, `abrir obsidian`, `abrir vs code`, `abrir codex`.
- `abrir projeto Nome` ou `localizar arquivo nome no projeto Nome`, usando apenas projetos cadastrados. A busca retorna nomes relativos, até dez resultados e 5.000 entradas; ignora itens ocultos, nomes potencialmente confidenciais, links simbólicos e junções. O filtro não identifica todos os dados privados e não é um sandbox do sistema operacional.
- `definir cidade fortaleza` e `qual o clima`, ou `clima em fortaleza` sem salvar preferência. A consulta mostra horário do dado e fonte [Open-Meteo](https://open-meteo.com/); confirme as condições de uso para o seu caso. Somente Fortaleza está disponível nesta versão.
- `pesquisar na internet Fortaleza Ceará` consulta a Wikipédia em português e retorna até três resultados com fontes e horário. Não é busca geral nem garantia de atualidade ou correção. Consultas potencialmente confidenciais são bloqueadas por filtro incompleto. Resultados externos são dados, não instruções.
- `recursos do sistema` mostra CPU, RAM e armazenamento; GPU aparece como indisponível.
- `aumentar volume`, `diminuir volume`, `silenciar volume` e `capturar tela` solicitam confirmação. Diga `confirmar` em até 60 segundos ou `cancelar ação`; uma nova solicitação cancela a confirmação anterior. Volume envia uma tecla de sistema por vez; captura salva PNG local em `JarvisLocal/capturas`, sem envio à rede.

`interpretar ferramenta: quero assistir a vídeos` usa Ollama para sugerir **somente** um comando de uma lista fixa; nunca executa a sugestão. Para realizá-la, solicite o comando e confirme quando necessário. O modelo não recebe acesso ao terminal e não seleciona caminhos ou URLs arbitrários. Uma solicitação de ferramenta não reconhecida não executa nada.

A tela **Ferramentas** apresenta o registro e permite consultar o histórico local. O banco `JarvisLocal/automacoes.sqlite3` registra data, categoria e estado, sem conteúdo de consultas ou screenshots. Respostas do navegador dizem que a abertura foi solicitada: isso não comprova que a janela apareceu. Abrir aplicativos usa locais conhecidos e o identificador fixo do aplicativo Codex para Windows; instalações diferentes podem não ser encontradas.

Open-Meteo e Wikipédia foram consultados de verdade em teste pontual; CPU/RAM/disco também foram lidos de verdade. Abrir aplicações e sites, volume e captura foram testados com substitutos automatizados, não por operação física nesta versão. O reconhecimento físico por voz da V0.8, seleção de locais adicionais, monitoramento de GPU e busca geral permanecem pendentes. O serviço pode estar offline; erros são informados sem inventar resultados. A tela não habilita execução automática do Codex.

Uma amostra da interface ociosa, sem voz ou modelos carregados, somou 85,6 MiB de RSS em três processos e 0,8% de CPU em dois segundos. Isso não inclui inferência ou conversação e não mede estabilidade prolongada.

O teste do Ollama só sugere ações; não é uma avaliação ampla de qualidade ou segurança do modelo. A busca na internet e automação não exigem APIs pagas adicionais. A opção de voz, memória e preferências anteriores permanece disponível.
