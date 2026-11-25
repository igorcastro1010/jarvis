# Ferramentas MCP locais para OpenJarvis

O servidor usa o protocolo MCP do OpenJarvis por stdin/stdout, sem abrir porta de rede. A lista de aplicativos é fixa no código: Chrome, Visual Studio Code, Bloco de Notas, Obsidian e Habblaud. O arquivo de configuração não consegue acrescentar aplicativos. Para autorizar projetos, edite `autorizados.json` localmente, por exemplo:

```json
{
  "aplicativos": {},
  "projetos": {"exemplo": "C:\\Projetos\\exemplo"}
}
```

Use caminhos absolutos confiáveis. O MCP aceita somente nomes exatos, executáveis autorizados sem argumentos e repositórios com `.git` próprio, sem links, junções ou objetos Git externos. A busca de memórias é textual e limitada ao cofre local configurado; não altera notas. Não exponha o arquivo de configuração, que pode conter caminhos pessoais. Logs rotativos guardam nomes de ferramentas e resultado, não os argumentos.

O OpenJarvis usa `orchestrator` com Qwen 2.5 3B e uma lista restrita de ferramentas. O modelo pode inventar capacidades: confirme resultados de ferramentas antes de agir. Uso percentual da GPU e VRAM aparecem como indisponíveis quando não há medição confiável. A delegação Codex permanece desativada. Não há ferramenta disponível para gravar ou excluir arquivos, executar comandos arbitrários, fazer commits, push ou deploy. A interface oficial não oferece uma confirmação humana confiável para essas ações; a lista restrita impede sua execução pelo agente de conversa. Backups locais da configuração e do inicializador anterior permitem retorno ao modo `simple`.
