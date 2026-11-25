# Pendências

- V0.9.1: resolver aplicação comprovada de sandbox Windows restrito; repetir homologação real em repositório fictício apenas após diagnóstico, validar encerramento da árvore, leitura/edição/testes, cancelamento e recuperação; integrar fila, aprovações separadas, memória, skills, progresso e voz antes de habilitar execução.

- V0.9: comparar whisper.cpp Vulkan e Faster-Whisper com o mesmo áudio, qualidade e medições reais; avaliar estabilidade prolongada e componentes simultâneos, cancelamento efetivo da inferência, cache seguro e contexto Graphify; homologar diagnóstico e voz fisicamente.

- V0.8.1: homologar pesquisa e leitura por voz fisicamente, ampliar cobertura de pesquisa e fontes de notícias, avaliar qualidade de resumos e defesa contra instruções maliciosas; páginas protegidas, dinâmicas ou fora da lista não são acessíveis.
- V0.8.2: concluir download e benchmark do Qwen 3 8B; ampliar avaliação de qualidade, memória Obsidian, estabilidade, picos e latência controlada; investigar compatibilidade de `think=false` no servidor instalado antes de recomendar Qwen 3; validar UI e voz fisicamente. Não substituir o modelo padrão sem evidências.

- Instalar e testar OpenJarvis isolado em Python 3.12; avaliar dependências e telemetria.
- Ampliar a homologação física inicial da V0.2, relatada pelo usuário em 24/11/2026, com ruído e medições de estabilidade e latência fim a fim.
- Ampliar avaliação de modelos e medir consumo elétrico e VRAM separadamente; repetir testes de CPU e GPU em carga sustentada.
- Homologar a V0.3 em dispositivos reais, validar bandeja e inicialização após login; medir estabilidade e falsos acionamentos.
- Avaliar detector de palavra-chave local mais leve e confiável, descarregamento de modelos ociosos e interrupção por voz durante a fala.
- Homologar memória por voz e edição no Obsidian; avaliar embeddings locais, política de exclusão definitiva com confirmação e limpeza de cópias em caches e backups.
- Corrigir e validar acesso a diretórios em perfil MXC restrito antes de habilitar execução Codex; integrar executor em segundo plano, cancelamento real, aprovação, progresso e notificação por voz.
- Diagnosticar timeout do Codex com runtime PowerShell autorizado, testar sessão real completa e conectar componentes de eventos, timeout e cancelamento à fila com isolamento e verificação independente.
- Investigar processo Codex principal que permanece vivo após turno com ferramentas, inclusive sem pipes; não habilitar produção até validar ciclo completo e término da árvore.
- V0.5.3: validar como aplicar perfil MXC restrito ao App Server instalado, com teste negativo de leitura fora do projeto; implementar transporte, gerenciamento de árvore, cancelamento e integração à fila apenas após comprovação. O handshake sem inferência encerrou, mas não comprova ciclo de turno com ferramentas.
- Implementar orçamento efetivo por tarefa e comparar consumo com mesma tarefa concluída; verificar os limites de uso disponíveis antes de prometer um teto.
- Implementar permissões por projeto, worktrees, commits, push e auditoria sem ampliar acesso; integrar contexto Graphify e registrar resultados seguros.
- Proteger dados locais com criptografia apropriada e tratar ciclos concorrentes de indexação/invalidação de grafos.
- Validar melhor isolamento de projetos por voz e relações do Graphify; integrar consulta ao grafo sem enviar conteúdo a serviços externos.
- Criar catálogo de skills e cadastrar Fortalaka e Jack Motos sem copiar dados privados.
- V0.6: validar consulta de Graphify por escopo e notas atuais; avaliar cache de descoberta e instalação/revisão explícita de skills. O catálogo inicial contém sugestões, não integrações executáveis; homologar voz física e cópia para a área de transferência.
- V0.7: integrar voz e seus estados reais à janela; implementar visualização de grafos, seleção de dispositivos, volume, modelos, inicialização, cancelamento de tarefas e GPU; homologar bandeja, notificações e ultrawide com dispositivos reais. Proteger histórico local e definir retenção.
- V0.7.1: homologar fisicamente a voz integrada, seleção de dispositivos, volume, interrupção, bandeja e ultrawide; adicionar testes de microfone e saída na interface, métricas GPU AMD e política de retenção do histórico. A lista textual do grafo precisa de visualização interativa e validação com grafos reais.
- V0.7.2: homologar fisicamente vocabulário de reconhecimento e alternância voz/texto; comparar modelos locais com conjunto representativo, qualidade, latência e memória antes de qualquer substituição. Medir consumo elétrico; não usar uma única resposta como benchmark de qualidade.
- Medir consumo e qualidade em conversação física, GPU/VRAM por componente e estabilidade prolongada. Comparar Whisper Vulkan/HIP em ambiente isolado com o modelo CPU atual; verificar recarga após 120 s silenciado antes de homologar a mudança.
- V0.8: homologar fisicamente abertura de aplicativos, sites, captura, volume e comandos por voz; medir GPU com fonte confiável, ampliar cidades e fontes públicas, validar instalações alternativas e melhorar seleção de diretórios autorizados. A sugestão do Ollama não executa ações e não foi amplamente avaliada.
- Validar e instalar Habblaud em ambiente compatível, com acesso local e sem hooks até revisão.
- Criar permissões por ferramenta, confirmações, parada de emergência, backups testados e rollback.
- Integrar Excel, resolver ambiguidades e persistir alterações com backup; a função atual só manipula registros em memória.
- Integrar automações Windows/Chrome, Codex, branches, PRs, artes, vídeos, sites e testes visuais.
- Implementar Instagram oficial somente após autorização e configuração da conta; não há publicação automática.
- Integrar ferramentas 3D e impressora; nunca iniciar impressão sem confirmação.
- Medir uso real de CPU, RAM, GPU, latência e consumo; não existem medições de inferência ainda.
