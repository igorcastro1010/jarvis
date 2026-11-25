# Ferramentas MCP locais para OpenJarvis

O servidor usa o protocolo MCP do OpenJarvis por stdin/stdout, sem abrir porta de rede. A lista de aplicativos é fixa no código: Chrome, Visual Studio Code, Bloco de Notas, Obsidian e Habblaud. O arquivo de configuração não consegue acrescentar aplicativos. O único projeto permitido é o Racha Fortalaka; seu cadastro local deve apontar ao caminho já fixado no servidor:

```json
{
  "aplicativos": {},
  "projetos": {"Racha Fortalaka": "C:\\Users\\SEU_USUARIO\\OneDrive\\Documentos\\Racha Fortalaka"}
}
```

O MCP aceita nomes autorizados, executáveis sem argumentos e o repositório fixado, com `.git` próprio, sem links, junções ou objetos Git externos. Consulta de documentação usa uma lista fixa de arquivos; pendências no cofre são obtidas apenas de itens abertos em notas ou seções dedicadas ao Racha Fortalaka. A busca geral do cofre não é exposta ao agente. Não exponha o arquivo de configuração, que pode conter caminhos pessoais. Logs rotativos guardam nomes de ferramentas e resultado, não os argumentos.

O OpenJarvis usa `orchestrator` com Qwen 2.5 3B e uma lista restrita de ferramentas. O modelo pode misturar pendências do Git e do Obsidian ou inventar resultados: confirme as fontes. Uso percentual da GPU e VRAM aparecem como indisponíveis quando não há medição confiável. A delegação Codex permanece desativada. Não há ferramenta disponível para gravar ou excluir arquivos, executar comandos arbitrários, fazer commits, push ou deploy. A interface oficial não oferece uma confirmação humana confiável para essas ações; a lista restrita impede sua execução pelo agente de conversa. Backups locais da configuração e do inicializador anterior permitem retorno ao modo `simple`.

## Lembretes

Peça ao Jarvis para criar ou listar lembretes. O horário é `America/Fortaleza`; recorrências suportadas: única, diária e semanal. Alterações e cancelamentos mostram uma caixa de confirmação local do Windows, com resposta negativa por padrão e tempo limite de 60 segundos. Sem confirmação, a mudança é recusada.

Os dados ficam em `~/.openjarvis/lembretes.db`. Com o Jarvis ativo, lembretes vencidos são enviados ao Windows; após uma parada, os atrasados são sinalizados ao reiniciar. Cada ocorrência é reservada antes de solicitar a notificação para impedir duplicatas entre processos. Se o processo falhar durante o envio, a ocorrência não é repetida automaticamente; consulte o histórico de entrega. A aceitação pelo Windows não garante que o sistema exibiu a notificação, pois as preferências de notificações podem bloqueá-la.
