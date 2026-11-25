# Inteligência e modelos locais — V0.8.2

Na interface, Configurações permite selecionar Qwen 2.5 3B, Qwen 3 4B, Qwen 2.5 7B ou Qwen 3 8B instalados no Ollama, perfil de geração e permanência de 0, 2 ou 5 minutos. Econômico, equilibrado e inteligente definem limites de 160, 320 e 512 tokens de saída, não mudam o modelo automaticamente nem ampliam permissões. O padrão permanece Qwen 2.5 3B. Com `0`, o Ollama libera o modelo depois da chamada; prazos maiores favorecem latência, mas modelos de outras aplicações podem permanecer carregados. Não há controle global sobre elas.

O contexto é limitado a 4096 tokens. Uma resposta encerrada pelo limite pode ser refeita uma única vez com até 512 tokens; se continuar truncada, isso é informado. O Qwen 3 recebe `think=false`, mas o servidor instalado 0.40.18 ignorou essa opção e também `/no_think` em testes; seu uso é experimental. A opção não garante ausência de raciocínio, nem de respostas truncadas ou incorretas.

Roteamento de ferramentas continua determinístico e suas permissões são independentes do modelo; memória e identidade compartilhadas são mantidas. Roteamento automático de modelos por complexidade não foi habilitado: os dados ainda não sustentam uma política segura e vantajosa.

## Método de medição

O script `python -m scripts.benchmark_ollama MODELO...` usa perguntas fictícias iguais sobre português, comandos, memória contextual e resumo. Mede tempo até primeiro conteúdo, carga e velocidade reportados pelo Ollama, e RSS dos processos cujo nome contém Ollama mais VRAM reportada pela API `/api/ps`, numa amostra após o primeiro token. RSS não é RAM exclusiva nem pico; VRAM é valor reportado pelo Ollama, não uso total ou pico. A carga fria ocorreu em paralelo a downloads, portanto não representa comparação controlada de inicialização. Cada caso tem uma amostra: não constitui avaliação estatística de qualidade ou estabilidade, e não substitui homologação física.

A Find Skills encontrou o catálogo oficial `amd/skills`; a skill `local-ai-use` é voltada a outro servidor e explicitamente não se aplica à integração de IA numa aplicação, portanto não foi instalada. As instruções de UI/UX Pro Max foram consultadas na origem; aplicam-se rótulos explícitos e feedback às opções da interface. Sem instalação de skills externas ou mudanças de drivers.

## Amostras observadas

| Modelo Q4_K_M | VRAM reportada | RSS Ollama amostrado | Carga fria / primeiro token | Tokens/s, quente | Qualidade nas quatro perguntas |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen 2.5 3B | 2,09 GB | 0,11 GB | 45,0 / 45,14 s | 81–101 | Português, comando, contexto e resumo corretos; nenhuma resposta truncada. |
| Qwen 3 4B | 2,88 GB | 0,11 GB | 71,21 / 71,34 s | 64–65 | Quatro respostas truncadas, gerando raciocínio em inglês; não foi possível avaliar respostas finais. |
| Qwen 2.5 7B | 4,64 GB | 0,11 GB | 100,03 / 100,28 s | 43–55 | Português, comando, contexto e resumo corretos; nenhuma resposta truncada. |
| Qwen 3 8B | pendente | pendente | pendente | pendente | Download interrompido após progresso oscilar; teste pendente. |

O log do Ollama apontou Vulkan e 37/37 camadas na GPU para o 4B e 29/29 para o 7B; o teste anterior do 3B apontou 37/37. Os dados brutos e respostas fictícias estão em `benchmark-v082.json`. A carga concorria com downloads, e as amostras não devem ser interpretadas como tempos típicos. O teste de contexto usa fatos fictícios no prompt, não comprova recuperação da memória Obsidian em conversação real. Mantenha o 3B como padrão; não há evidência para recomendar a troca.

Referências: [API de chat Ollama](https://docs.ollama.com/api/chat), [controle de raciocínio Qwen](https://qwen.readthedocs.io/en/stable/getting_started/quickstart.html), [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), [skills AMD](https://github.com/amd/skills).
