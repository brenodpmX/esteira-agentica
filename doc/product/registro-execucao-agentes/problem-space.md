# Problem Space — Registro de execução de agentes

Status: draft
Owner: product
Last updated: 2026-08-25

## Inputs
- Issue #176 e histórico de entrevista com o dono, consultados em 2026-08-25.
- Amostra dos logs locais de 21–22/08/2026 registrada no histórico da issue.
- [Kiro — Viewing per-user activity](https://kiro.dev/docs/enterprise/monitor-and-track/user-activity/)
- [Kiro CLI — Headless mode](https://kiro.dev/docs/cli/headless/)
- [Kiro — Billing](https://kiro.dev/docs/billing/)
- [Langfuse — Model Usage & Cost Tracking](https://langfuse.com/docs/model-usage-and-cost)
- [LangSmith — Cost tracking](https://docs.langchain.com/langsmith/cost-tracking)

## Contexto
A esteira gera um Markdown detalhado por execução com parâmetros, prompt e chat. Esse artefato atende à inspeção individual, mas é sujeito ao TTL dos logs e não constitui uma série estruturada para análise em lote ou consolidação pela hierarquia de issues.

O dono confirmou como usuários o operador de IA, SRE, monitoramento e pessoas interessadas no custo operacional. A decisão desejada é entender uma execução individual e, depois, o total de uma entrega ponta a ponta: volume, duração, consumo, resultados e repetições de uma issue principal somada aos seus descendentes históricos.

A amostra local de 21–22/08/2026 registrada na entrevista contém 24 arquivos em 11 issues. Em 22 deles havia resumo extraível, totalizando 123,99 créditos e 1,12 hora; mediana de 5,81 créditos e 3,14 minutos, com intervalos de 0,35–11,54 créditos e 0,57–5,73 minutos. Dois arquivos ainda não tinham resumo no instante da aferição. Ela comprova que a versão observada do Kiro reporta créditos e duração, mas não é baseline histórico e não permite classificar com segurança avanço, falha terminal ou repetição. Sete registros continham marcadores de falha interna de ferramenta, o que não prova sete execuções malsucedidas porque uma falha pode ter sido recuperada.

O dono aceitou como resultados `concluída`, `falha terminal`, `timeout`, `interrompida` e `desconhecida`, separados de `issue avançou: sim/não`. Também aceitou medir “repetição sem avanço” como uma nova execução da mesma issue na mesma etapa após execução que não a fez avançar.

## Problemas
- Não há contagem confiável de execuções por issue, etapa, agente, modelo ou entrega completa.
- Duração e consumo exigem abertura e consolidação manual de logs individuais.
- Não se distingue resultado da execução de avanço da issue, ocultando falhas recuperadas e repetições sem progresso.
- O TTL dos logs remove evidência antes da formação de uma série histórica.
- A hierarquia atual não basta para explicar o custo completo quando um descendente é desvinculado posteriormente; é necessária a linhagem histórica conhecida.
- Tokens, créditos e moeda são unidades distintas. A fonte observada do Kiro oferece créditos; ausência de tokens ou custo não autoriza estimativa.
- Ainda não existem regras aprovadas de retenção do registro, acesso, exportação e exclusão.
- A demanda ainda não está vinculada a uma meta/OKR, prazo e responsável pela aferição.

## Impacto
Sem o registro, operação e SRE continuam investigando em arquivos individuais, com tempo de resposta não medido e risco de erro de consolidação. Produto não consegue comparar etapas, agentes ou modelos com evidência longitudinal. Falhas terminais e recuperadas permanecem misturadas, enquanto novas execuções da mesma issue podem consumir capacidade sem que o retrabalho seja quantificado.

O custo de não fazer cresce com o volume: o histórico desaparece conforme o TTL, impedindo reconstrução posterior do baseline. Decisões de otimização seguem baseadas em amostras ad hoc e o consumo não pode ser atribuído com segurança a uma entrega completa.

Não há baseline que permita monetizar o retorno hoje. Portanto, o retorno inicial aprovado pelo dono é capacidade de gestão: cobertura, consulta em até 5 minutos e publicação do baseline em 30 dias. Qualquer ROI monetário posterior dependerá de dados observados e regra auditável de conversão.

## Oportunidade
O mercado valida o problema. Langfuse e LangSmith tratam uso e custo como dimensões de traces e permitem agregações, desde que o provedor ou a instrumentação forneça uso/preço. Ambas também evidenciam que inferência não é universal: quando a fonte não expõe o consumo necessário, o dado precisa ser enviado ou permanece indisponível.

O relatório corporativo do Kiro publica diariamente créditos por usuário e tipo de cliente, além de mensagens e modelo. Ele ajuda em auditoria e alocação de licenças, mas não inclui issue, etapa, resultado, avanço ou linhagem. A documentação pública do modo headless descreve execução e códigos de saída, sem contrato de tokens/créditos por execução. Assim, o relatório nativo é complementar, não substituto.

Resolver agora preserva o próximo histórico antes que o TTL o elimine e cria a base factual necessária para decidir otimizações e um dashboard posterior. O dono aceitou que o dashboard fique fora do primeiro corte e que seu épico seja criado somente após o merge desta entrega na `main`.

## Alternativas consideradas

1. **Manter apenas os logs atuais:** menor esforço imediato, mas não atende análise em lote, linhagem nem retenção independente. Recusada como solução do problema.
2. **Usar somente o relatório corporativo do Kiro:** útil para créditos por usuário/dia, mas sem granularidade e sem semântica de issue. Complementar, não suficiente.
3. **Adotar uma plataforma genérica de observabilidade:** oferece traces, uso, custo e dashboards, mas ainda exige fornecer a identidade e a semântica da esteira. A escolha de tecnologia não pertence à análise de negócio; fica para etapa posterior.
4. **Primeiro corte próprio de capacidade de negócio — registro + consulta/exportação:** cobre a decisão prioritária sem antecipar dashboard ou conversões sem fonte. Recomendado.

## Regras de negócio fechadas
- Uma execução e o avanço da issue são dimensões separadas.
- Resultados mínimos: concluída, falha terminal, timeout, interrompida e desconhecida.
- Repetição sem avanço: nova execução da mesma issue na mesma etapa após execução sem avanço.
- A consulta parte de uma issue raiz e inclui sua linhagem histórica conhecida, mesmo após desvinculação, sem ciclos ou dupla contagem.
- Descendentes conhecidos sem registro aparecem sinalizados, não desaparecem do resultado.
- O consumo preserva valor, unidade, fonte e disponibilidade; zero é diferente de indisponível.
- O nome geral solicitado pelo dono é “Tokens”, mas a apresentação por plataforma conserva o termo/unidade nativa, como créditos no Kiro.
- Moeda só é registrada quando for a unidade fornecida pela própria plataforma; não haverá conversão presumida.
- Prompt e chat permanecem no log detalhado e não são duplicados no registro estatístico.
- O registro terá TTL próprio, independente do TTL do log; a duração e os eventos de início e exclusão desse TTL ainda aguardam definição.

## Ordem de esforço e dependências
Ordem recomendada por valor e dependência de negócio, sem decisão de arquitetura:

1. **Confiabilidade do registro individual:** identidade, tempo, contexto, resultado, avanço e consumo com proveniência. É pré-requisito para qualquer agregado.
2. **Linhagem e agregação:** consolidação histórica da raiz, proteção contra ciclo/dupla contagem e sinalização de lacunas. É o maior risco de completude.
3. **Consulta/exportação operacional:** filtros e saída que permitam responder às perguntas em até 5 minutos e aferir as metas de 30 dias.
4. **Dashboard e alertas:** fora do escopo; novo épico após merge na `main` e após disponibilidade do baseline.

A estimativa de implementação será feita em etapa posterior. Em ordem relativa, o registro individual é a menor unidade entregável; linhagem/agregação tende a concentrar maior incerteza; consulta/exportação depende dos dois blocos anteriores.

## Critério de decisão
**Recomendação condicional: aprovar o mérito e o recorte, mas não avançar ainda.** Dor, público, resultado, taxonomia, primeiro corte, ordem de esforço, custo de não fazer e métricas de 30 dias estão fechados. A aprovação de negócio depende das seguintes respostas do dono:

1. TTL exato do registro, evento que inicia a contagem e tratamento após expiração.
2. Quem pode consultar/exportar e quem pode excluir.
3. Se excluir uma issue apaga seus registros, os anonimiza ou preserva a trilha histórica.
4. Meta/OKR ou objetivo organizacional, prazo desejado e pessoa responsável pela aferição dos 30 dias.

Sem essas decisões não é possível afirmar aderência às políticas de dados nem responsabilização pela medição. A issue deve permanecer em Análise de Negócio com `need_human`.

> Conteúdo de mercado reescrito e resumido a partir das fontes listadas para conformidade de licenciamento.
