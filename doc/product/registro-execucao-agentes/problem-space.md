# Problem Space — Registro de execução de agentes

Status: approved
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

A amostra local de 21–22/08/2026 registrada na entrevista contém 24 arquivos em 11 issues. Em 22 deles havia resumo extraível, totalizando 123,99 créditos e 1,12 hora; mediana de 5,81 créditos e 3,14 minutos, com intervalos de 0,35–11,54 créditos e 0,57–5,73 minutos. Dois arquivos ainda não tinham resumo no instante da aferição. A amostra comprova que a versão observada do Kiro reporta créditos e duração, mas não é baseline histórico e não permite classificar com segurança avanço, falha terminal ou repetição. Sete registros continham marcadores de falha interna de ferramenta, o que não prova sete execuções malsucedidas porque uma falha pode ter sido recuperada.

O dono aceitou como resultados `concluída`, `falha terminal`, `timeout`, `interrompida` e `desconhecida`, separados de `issue avançou: sim/não`. Também aceitou medir “repetição sem avanço” como uma nova execução da mesma issue na mesma etapa após execução que não a fez avançar.

## Problemas
- Não há contagem confiável de execuções por issue, etapa, agente, modelo ou entrega completa.
- Duração e consumo exigem abertura e consolidação manual de logs individuais.
- Não se distingue resultado da execução de avanço da issue, ocultando falhas recuperadas e repetições sem progresso.
- O TTL dos logs remove evidência antes da formação de uma série histórica.
- A hierarquia atual não explica o esforço completo quando um descendente é desvinculado posteriormente; é necessária a linhagem histórica conhecida.
- Tokens, créditos e moeda são unidades distintas. A fonte observada do Kiro oferece créditos; ausência de tokens ou custo não autoriza estimativa.

## Impacto
Sem o registro, operação e SRE continuam investigando arquivos individuais, com tempo de resposta não medido e risco de erro de consolidação. Produto não consegue comparar etapas, agentes ou modelos com evidência longitudinal. Falhas terminais e recuperadas permanecem misturadas, enquanto novas execuções da mesma issue podem consumir capacidade sem que a repetição seja quantificada.

O custo de não fazer cresce com o volume: o histórico desaparece conforme o TTL, impedindo reconstrução posterior do baseline. Decisões de otimização seguem baseadas em amostras ad hoc e o consumo não pode ser atribuído com segurança a uma entrega completa. Adiar também posterga o aprendizado necessário para decidir se dashboard, alertas ou otimizações terão retorno.

Não há baseline que permita monetizar o retorno hoje. O retorno inicial aprovado é capacidade de gestão: cobertura mensurável, consulta em até 5 minutos e publicação do baseline em 30 dias. Qualquer ROI monetário posterior dependerá de dados observados e regra auditável de conversão.

## Oportunidade
O mercado valida o problema. Langfuse e LangSmith tratam uso e custo como dimensões de traces e permitem agregações, desde que o provedor ou a instrumentação forneça uso e preço. Quando a fonte não expõe o consumo necessário, o dado precisa ser enviado ou permanece indisponível; inferência não é universal.

O relatório corporativo do Kiro publica diariamente créditos por usuário e tipo de cliente, além de mensagens e modelo. Ele ajuda em auditoria e alocação de licenças, mas não inclui issue, etapa, resultado, avanço ou linhagem. A documentação pública do modo headless descreve execução e códigos de saída, sem contrato público de tokens ou créditos por execução. Assim, o relatório nativo é complementar, não substituto.

Resolver agora preserva o próximo histórico antes que o TTL dos logs o elimine e cria a base factual necessária para decidir otimizações e um dashboard posterior. O dono aceitou que o dashboard fique fora do primeiro corte e que seu épico seja criado somente após o merge desta entrega na `main`.

## Alternativas consideradas
1. **Manter apenas os logs atuais:** menor esforço imediato, mas não atende análise em lote, linhagem nem retenção independente. Recusada como solução do problema.
2. **Usar somente o relatório corporativo do Kiro:** útil para créditos por usuário/dia, mas sem granularidade e sem semântica de issue. Complementar, não suficiente.
3. **Adotar uma plataforma genérica de observabilidade:** oferece traces, uso, custo e dashboards, mas ainda exige identidade e semântica da esteira. A escolha de tecnologia não pertence à análise de negócio.
4. **Entregar registro + consulta/exportação:** cobre a decisão prioritária sem antecipar dashboard ou conversões sem fonte. Alternativa aprovada.

## Regras de negócio fechadas
- Uma execução e o avanço da issue são dimensões separadas.
- Resultados mínimos: concluída, falha terminal, timeout, interrompida e desconhecida.
- Repetição sem avanço: nova execução da mesma issue na mesma etapa após execução sem avanço.
- A consulta parte de uma issue raiz e inclui sua linhagem histórica conhecida, mesmo após desvinculação, sem ciclos ou dupla contagem.
- Descendentes conhecidos sem registro aparecem sinalizados, não desaparecem do resultado.
- O consumo preserva valor, unidade, fonte e disponibilidade; zero é diferente de indisponível.
- O nome geral solicitado pelo dono é “Tokens”, mas cada plataforma conserva o termo e a unidade nativos, como créditos no Kiro.
- Moeda só é registrada quando for a unidade fornecida pela própria plataforma; não haverá conversão presumida.
- Prompt e chat permanecem no log detalhado e não são duplicados no registro estatístico.
- O registro tem TTL próprio e independente do log. A retenção é configurável em quantidade de dias para a idade de cada registro; ao atingir a idade configurada, ele se torna elegível ao expurgo. Sem configuração, não há expurgo automático.
- Somente a lógica do produto cria ou exclui registros; não se prevê exclusão manual por papel de negócio.
- O operador da esteira governa quem pode consultar e exportar em sua operação.
- Excluir uma issue não exclui, anonimiza nem rompe seus registros; eles permanecem até eventual expurgo pela política própria.

## Políticas, metas e responsabilidade
O registro estatístico não duplica prompt ou chat, reduzindo exposição de conteúdo. Retenção explícita, ausência de expurgo por padrão e preservação após exclusão da issue são decisões conscientes do dono; o operador deve configurar o prazo segundo a política aplicável à sua organização.

Não existe meta/OKR organizacional, prazo externo ou responsável nominal associado. Essa ausência impede alegar alinhamento estratégico ou ROI monetário, mas não invalida o mérito operacional: a capacidade é justamente o pré-requisito para criar o primeiro baseline. Para aferição, cada organização que operar a esteira deve designar um operador responsável antes da janela de 30 dias; as métricas de sucesso deste épico funcionam como critérios de resultado, não como OKR corporativo.

## Ordem de esforço e dependências
Ordem recomendada por valor e dependência de negócio, sem decisão de arquitetura:

1. **Confiabilidade do registro individual:** identidade, tempo, contexto, resultado, avanço e consumo com proveniência. É pré-requisito para qualquer agregado.
2. **Linhagem e agregação:** consolidação histórica da raiz, proteção contra ciclo/dupla contagem e sinalização de lacunas. É o maior risco de completude.
3. **Consulta/exportação operacional:** filtros e saída que permitam responder às perguntas em até 5 minutos e aferir as metas de 30 dias.
4. **Dashboard e alertas:** fora do escopo; novo épico após merge na `main` e após disponibilidade do baseline.

A estimativa de implementação será feita em etapa posterior. Em ordem relativa, o registro individual é a menor unidade entregável; linhagem/agregação concentra maior incerteza; consulta/exportação depende dos dois blocos anteriores.

## Critério de decisão
**Aprovado para avançar.** Dor, público, resultado, taxonomia, primeiro corte, política de retenção, acesso e exclusão, ordem de esforço, custo de não fazer e métricas de 30 dias foram fechados com o dono e confrontados com fatos do produto e alternativas de mercado.

A aprovação aceita explicitamente três limites: não há OKR formal, responsável nominal ou prazo externo; não há baseline para prometer economia; e a escolha de tecnologia permanece para etapas técnicas. O retorno será validado pela cobertura, completude, tempo de resposta e baseline da primeira janela de 30 dias.

> Conteúdo de mercado reescrito e resumido a partir das fontes listadas para conformidade de licenciamento.
