# Análise de Negócio — Otimizar prompts, contextos e comandos

Status: recomendação de aprovação
Owner de negócio consultado: Breno de Paula
Responsável pela análise: Helena Costa — Product Manager
Última atualização: 2026-08-22

## Decisão recomendada

**Aprovar o épico com escopo reduzido ao ganho de eficiência do contexto total entregue ao agente.** A dor é estrutural e verificável: a execução atual combina um prompt dinâmico extenso com contexto persistente, repete conteúdo invariável e mistura objetivo da tarefa, políticas de segurança, manual de comandos e procedimentos operacionais. Não há evidência suficiente para afirmar que isso já causa uma taxa específica de erro, “delírio” ou gasto financeiro; esses efeitos permanecem hipóteses.

A aprovação não depende de monetizar tokens. O retorno será demonstrado por redução model-independent de palavras/caracteres sempre carregados, eliminação de duplicidade e preservação do comportamento em cenários de referência. Tokens podem ser observados quando o adapter expuser a informação, mas não serão o único gate.

Não fazem parte desta aprovação uma rearquitetura ampla, a escolha de um arquivo canônico, a remoção de `.kiro/`, suporte novo a outros agentes, multi-repositório, política de upgrade de estado ou decomposição em stories. Esses temas só voltam ao escopo se houver evidência de contribuição direta para o objetivo central.

## Entrevista com o dono e tratamento das hipóteses

A primeira rodada perguntou por incidentes, público, metas, multi-repositório, compatibilidade, upgrade e separação das frentes. O dono respondeu em 22/08/2026 que:

1. não há baseline confiável para classificar custo por tokens neste momento;
2. a necessidade principal é tornar mais eficiente o prompt montado em tempo real;
3. a verbosidade observável nos blocos `## Prompt` dos logs é o sinal que motivou o épico;
4. `pipe.yml` e os contextos escritos pelo operador podem ser avaliados como interfaces, mas o produto não deve prescrever seu conteúdo.

Tratamento das respostas:

- **Validado como fato:** o prompt é extenso e contém blocos invariáveis; isso foi confirmado em `src/core/agent.py` e por benchmark reproduzível.
- **Validado como fato:** há contexto persistente adicional, gerado em `src/core/context_generator.py` e injetado por custom agent do Kiro.
- **Hipótese ainda não provada:** mais palavras causam mais erros ou delírios. Não foi encontrada série operacional que permita atribuir causalidade.
- **Hipótese válida para experimento:** reduzir conteúdo irrelevante ou duplicado libera contexto e diminui pontos de conflito. A documentação dos fornecedores recomenda instruções concisas, focadas e escopadas.
- **Restrição aceita:** não será exigido ROI financeiro por token para aprovar; o produto usará medidas relativas, auditáveis e independentes de modelo.

Os logs mencionados em `/home/breno/pipes/esteira-agentica/logs/<issue-id>/*.md` não existem no ambiente desta análise. Logo, não foram usados para calcular frequência de falhas, volume ou custo.

## Dor de negócio fechada

A esteira não diferencia de modo suficientemente enxuto quatro classes de informação:

1. **políticas invariáveis e guardrails** que devem ser respeitados em toda execução;
2. **contexto do operador/projeto**, cujo conteúdo pertence ao operador;
3. **workflow da etapa**, configurado no board/coluna;
4. **dados exclusivos da tarefa**, como objetivo, caminhos e transição possível.

Como consequência observável, o prompt repete material de referência em toda chamada, a mesma regra pode aparecer em mais de uma camada e o operador não tem um contrato claro para saber o que cada adapter realmente carregou. O problema de Produto não é o tamanho visual do bloco `## Prompt` isoladamente; é o **total de instrução sempre carregada e sua capacidade de ser compreendida sem conflito**. Apenas mover texto do prompt para um contexto sempre incluído esconderia a verbosidade, mas não reduziria consumo de contexto.

## Evidência do produto atual

Foi gerado um cenário controlado com uma coluna de Análise de Negócio, flow `create`, uma transição e o adapter atual. O resultado é uma referência estrutural, não uma amostra de produção:

| Camada | Caracteres | Palavras | Linhas |
|---|---:|---:|---:|
| Prompt dinâmico | 3.723 | 531 | 85 |
| Contexto persistente gerado | 1.792 | 259 | 61 |
| Total sempre carregado no cenário | 5.515 | 790 | 146 |
| Manual `@---` dentro do prompt | 1.741 | 281 | 32 |

O manual de anotações sozinho equivale a 52,9% das palavras do prompt e 35,6% do total prompt + contexto no cenário. Isso não significa que todo esse conteúdo possa ser removido: significa que há espaço suficiente para exigir uma redução relevante sem especular sobre preço de token.

Outros fatos verificados:

- `build_prompt` inclui regras de diretório, Git setup, commit/push, PR, cleanup, manual completo de anotações e transição.
- `generate_context` cria contexto persistente com restrições, nomeação de issues, boards e branches.
- o workdir é resolvido por board/repositório, com fallback para o primeiro repositório configurado; não há evidência de que multi-repositório seja a causa desta dor.
- a validação de `pipe.yml` cobre estrutura básica, mas a mudança de configuração só deve ocorrer se simplificar e tornar verificável o contrato de instruções.

## Mercado e alternativas

### 1. Manter todo o procedimento no prompt dinâmico

Tem baixo esforço imediato e alta transparência no log, porém repete referência estática em cada execução e amplia a superfície de conflito. Não atende ao objetivo.

### 2. Transferir todo o texto para contexto persistente sempre carregado

Kiro, Copilot e Claude oferecem instruções persistentes. Essa alternativa melhora a aparência do prompt, mas não garante redução do contexto total. No Kiro CLI, a própria documentação alerta que os modos condicionais não estão disponíveis e os arquivos de steering são carregados automaticamente; custom agents também exigem configuração explícita dos recursos. Portanto, “sumir com texto do prompt” não é uma métrica de sucesso.

### 3. Usar apenas um padrão comum como `AGENTS.md`

`AGENTS.md` é um formato aberto difundido e Kiro/Copilot o suportam. Contudo, a adoção não é universal nem idêntica: Claude Code usa `CLAUDE.md` e requer import ou link para consumir `AGENTS.md`. Logo, um nome único não pode ser requisito de negócio. A necessidade correta é um contrato por adapter, com evidência de carregamento.

### 4. Composição em camadas, com conteúdo sob demanda e contrato por adapter — recomendação

O mercado converge para separar instruções persistentes, regras escopadas e procedimentos acionados sob demanda. A alternativa recomendada mantém no prompt apenas o que varia por tarefa, preserva guardrails em uma camada comprovadamente carregada e torna referências extensas disponíveis somente quando necessárias. A implementação concreta será decidida em etapa técnica.

Conteúdo externo foi resumido e parafraseado para conformidade com restrições de licenciamento.

## Resultado de negócio e como medir

### Resultado primário

Cada execução recebe somente instruções relevantes para sua tarefa e adapter, com menos conteúdo sempre carregado e sem perda das garantias operacionais.

### Gates de sucesso

A entrega só é considerada bem-sucedida se, sobre uma matriz fixa de cenários representativos:

1. **reduzir em pelo menos 40% as palavras estáticas do prompt dinâmico** em comparação com o mesmo cenário na versão-base;
2. **reduzir em pelo menos 20% o total de palavras sempre carregadas** (prompt + contextos automáticos) no adapter Kiro atual;
3. **eliminar duplicidades de regra entre camadas sempre carregadas**, registradas em um inventário auditável;
4. **comprovar o carregamento das instruções obrigatórias pelo adapter suportado**, em vez de presumir descoberta de arquivo;
5. **preservar 100% dos cenários de referência** de workdir, branch, proteção de estado, leitura/escrita dos arquivos da issue, finalização e transição;
6. manter **zero acesso indevido a estado protegido** e **zero regressão de isolamento de repositório** nos testes de aceitação.

A meta de 20% para o total é deliberadamente menor que a oportunidade estrutural observada de 35,6% representada pelo manual de anotações, deixando margem para instruções que precisem permanecer sempre disponíveis. A meta de 40% para o prompt impede que a entrega apenas renomeie ou reorganize o bloco atual.

### Métricas de acompanhamento, sem bloquear a primeira aprovação

- caracteres, palavras e, quando disponível, tokens de entrada por execução (p50/p95);
- percentual de execuções que avançam sem correção por instrução ausente ou conflitante;
- reexecuções atribuídas a prompt/contexto;
- falhas de workdir, branch, commit ou PR;
- intervenções humanas para corrigir instruções;
- percentual de execuções com prova de contexto obrigatório carregado.

A classificação causal de falhas deve ser introduzida junto da entrega; antes disso, qualquer taxa seria retroativamente subjetiva.

## Retorno e custo de não fazer

O retorno mínimo contratado é capacidade de contexto liberada com o mesmo comportamento. No cenário de referência, a carga atual é de 790 palavras sempre incluídas. Com a meta mínima de 20%, a economia será de ao menos 158 palavras por execução equivalente. Para `N` execuções, o benefício direto é `158 × N` palavras não carregadas, além da redução de manutenção por regra duplicada. Isso é mensurável sem converter palavras em moeda.

Sem a mudança, a esteira continuará repetindo até 281 palavras de manual de comandos em toda execução comparável, além das demais instruções fixas. O custo cresce linearmente com o volume, reduz espaço para o conteúdo real da tarefa e mantém o risco de instruções conflitantes. Não é possível quantificar custo financeiro, falhas evitadas ou horas poupadas sem os logs e a classificação operacional; esses benefícios não entram no business case como fatos.

## Escopo aprovado

- inventariar as instruções atuais por responsabilidade e camada;
- compor um prompt de tarefa mínimo, preservando apenas dados e ações relevantes à execução corrente;
- remover duplicidade entre prompt, contexto gerado e contexto do operador;
- definir e verificar o contrato de ingestão de instruções do adapter Kiro atual;
- tornar referências extensas disponíveis de forma que não sejam sempre carregadas quando desnecessárias;
- revisar apenas as opções de `pipe.yml` que influenciam diretamente objetivo da etapa, workflow, branch, repositório/workdir e composição de instruções;
- garantir que mensagens de commit e PR reflitam a mudança realizada, sem obrigar copy mecânico quando o agente dispõe do resultado real;
- fornecer benchmark antes/depois e evidência dos guardrails.

## Fora de escopo

- definir o conteúdo dos contextos mantidos pelo operador;
- escolher nesta etapa tecnologia, arquitetura ou arquivo canônico;
- remover `.kiro/` como objetivo em si;
- implementar adapters adicionais;
- resolver multi-repositório sem caso comprovado ligado à eficiência do prompt;
- alterar ciclo de versão, retenção ou limpeza de `.pipe/`;
- criar stories nesta etapa.

## Ordem relativa de esforço e valor

| Ordem | Frente | Esforço relativo | Motivo |
|---:|---|---|---|
| 1 | Baseline, inventário e contrato comportamental | M | Evita otimização apenas visual e define o que não pode ser perdido. |
| 2 | Simplificação do prompt no adapter atual | M | Maior valor direto e oportunidade já mensurada. |
| 3 | Ajustes mínimos de configuração ligados à composição | M | Remove ambiguidades sem transformar o épico em redesign de `pipe.yml`. |
| 4 | Evidência antes/depois e observabilidade causal | M | Sustenta evolução das metas e detecta regressões. |
| 5 | Portabilidade para adapters futuros | L, diferido | Só gera valor quando outro adapter entrar no produto. |

M = esforço moderado; L = esforço alto/variável. A ordem não representa desenho técnico nem decomposição em stories.

## Aderência a metas e políticas

O dono vinculou o épico à eficiência dos agentes, mas não forneceu OKR formal, compromisso de cliente ou data mandatória. A recomendação se sustenta como melhoria de eficiência operacional e capacidade do produto, não como promessa financeira.

A entrega deve continuar respeitando as políticas existentes: estado interno protegido, isolamento por workdir/repositório, operações Git seguras, contexto do operador como responsabilidade do operador e compatibilidade do comportamento vigente. Nenhuma redução de texto justifica remover um guardrail sem mecanismo equivalente e comprovado.

## Critério para aprovação ou recusa futura

- **Aprovar a entrega** se todos os gates de redução e preservação forem comprovados no mesmo benchmark.
- **Recusar ou devolver** se apenas o tamanho visível do prompt diminuir, se o texto for movido para outra camada sempre carregada, se houver perda de guardrail ou se o escopo se expandir sem evidência.

## Fontes

1. Código do produto: `src/core/agent.py`, `src/core/context_generator.py`, `src/core/config.py` e `src/core/commands.py`.
2. [Kiro — Steering](https://kiro.dev/docs/steering/).
3. [GitHub Copilot CLI — Custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions).
4. [Anthropic — How Claude remembers your project](https://docs.anthropic.com/en/docs/claude-code/memory).
5. [AGENTS.md — formato aberto para instruções de agentes](https://agents.md/).
