# Pesquisa pública experimental V0.8.1

Comandos por texto ou voz: `pesquisar na internet mudanças climáticas`, `últimas notícias` e `resumir página https://agenciabrasil.ebc.com.br/...`. O resultado informa fontes e horário; notícias também apresentam a data fornecida pelo feed. Busca usa Wikipédia e Crossref, cuja cobertura é científica, portanto não equivale a um buscador geral. Notícias usam o feed público da Agência Brasil, não cobrem todos os veículos e podem estar atrasadas.

Para leitura, instale a dependência opcional com `uv pip install --python .venv\Scripts\python.exe -r requirements-research.txt` e tenha o Google Chrome instalado. O download é feito com tamanho e tempo limitados e sem redirecionamentos; somente `www.gov.br`, `agenciabrasil.ebc.com.br` e `pt.wikipedia.org` são aceitos, sem parâmetros, portas alternativas ou credenciais. Playwright carrega uma cópia no Chrome isolado, sem scripts, recursos externos, perfil pessoal ou downloads. Algumas páginas podem rejeitar o acesso ou exigir JavaScript. Pesquisa e notícias não requerem Playwright.

O resumo utiliza o Ollama local e envia apenas um trecho limitado da página. Conteúdo externo é não confiável; o modelo não tem ferramentas, mas ainda pode interpretar mal texto malicioso, inventar detalhes ou truncar respostas: confira sempre a fonte. Nenhuma consulta funciona offline; erros são informados. Consultas são transmitidas aos serviços públicos, portanto não inclua dados privados. Histórico de automação registra somente categorias e status, sem consultas ou URLs.

Homologação física da V0.8 e da voz integrada continua pendente. A V0.8.2, com comparação de modelos na RX 6600, permanece planejada para etapa futura.

Em 25/11/2026 foram testados consulta real às duas fontes, feed real e leitura de uma matéria da Agência Brasil com Chrome/Playwright e Ollama local. Uma execução de resumo levou aproximadamente 11,9 s e terminou truncada; é uma amostra isolada, não um benchmark de qualidade ou desempenho.
