# Ferramentas MCP locais para OpenJarvis

O servidor usa o protocolo MCP do OpenJarvis por stdin/stdout, sem abrir porta de rede. O cadastro inicial está vazio. Para autorizar recursos, edite `autorizados.json` localmente, por exemplo:

```json
{
  "aplicativos": {"bloco de notas": "C:\\Windows\\System32\\notepad.exe"},
  "projetos": {"exemplo": "C:\\Projetos\\exemplo"}
}
```

Use caminhos absolutos confiáveis. O MCP aceita somente nomes exatos, executáveis `.exe` sem argumentos e repositórios com `.git` próprio, sem links, junções ou objetos Git externos. Não exponha o arquivo de configuração, que pode conter caminhos pessoais. Logs rotativos guardam nomes de ferramentas e resultado, não os argumentos.

O OpenJarvis precisa reiniciar para carregar a configuração MCP. Para testes explícitos, selecione `orchestrator`; o padrão permanece `simple` e Qwen 2.5 3B. O modelo pode inventar capacidades: confirme resultados de ferramentas antes de agir. Uso percentual da GPU e VRAM aparecem como indisponíveis quando não há medição confiável. A delegação Codex permanece desativada.
