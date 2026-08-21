# Análise de negócio — Registro de execução de agentes

Status: aguardando validação do dono (`need_human`)
Owner: product
Last updated: 2026-08-21

## Decisão executiva provisória

**Não aprovar nem recusar ainda.** A dor é real e há aderência clara à
confiabilidade e à gestão de consumo da esteira, mas faltam evidências mínimas
para quantificar retorno e fechar o contrato de medição. Também há uma
incompatibilidade a resolver: a proposta pede "custo em tokens", enquanto o
Kiro atualmente comercializa e acompanha uso em créditos. A documentação
pública do modo headless não garante que tokens ou créditos sejam devolvidos
por execução.

A recomendação provisória é validar um primeiro resultado de negócio focado em
um registro confiável de cada execução e em uma consulta consolidada por
hierarquia de issues. O campo de consumo deve registrar somente dado fornecido
por fonte verificável, com unidade e procedência; indisponibilidade não pode ser
convertida em zero nem estimada silenciosamente.

## Dor e evidências

### Dor declarada pelo dono

Hoje não é possível produzir estatísticas de execução dos agentes. A proposta
original pretende registrar cada execução por issue e permitir que um agente
recupere os registros da issue raiz e de suas descendentes.

Essa declaração ainda é uma **hipótese do dono**, pois não veio acompanhada de
volume, frequência de decisões, tempo gasto manualmente ou gasto evitável.

### Fatos verificados no produto

- `src/adapters/kiro_cli_agent.py::KiroCliAgent._create_log` já cria um Markdown
  por execução em `logs/<issue>/<timestamp>.md`.
- `_build_log` registra plataforma, agente, modelo, board, coluna, issue,
  repositório, diretório, prompt e chat. Não mantém campos estruturados de
  duração, consumo ou resultado normalizado.
- `execute` e `_detect_failure` distinguem algumas falhas conhecidas para o log
  operacional, mas esse resultado não está disponível como uma série por issue.
- `src/__main__.py::call_agent` conhece issue, board, coluna, plataforma,
  agente e modelo no momento da chamada. Portanto, parte relevante do contexto
  já existe, embora isso não prove disponibilidade de consumo do provedor.
- Os logs são persistidos no volume `pipe-logs`, porém a configuração do produto
  possui TTL para logs. A retenção do novo registro e o comportamento de
  referências a logs expirados ainda não foram definidos.

### Riscos do enunciado atual

1. **Métrica financeira incorreta:** tokens totais não equivalem a custo. Preços
   podem variar por modelo e por tipo de token; no Kiro, a unidade comercial
   atual é crédito.
2. **Falso dado:** a ausência de telemetria do CLI pode virar `0 tokens`,
   confundindo "indisponível" com "sem consumo".
3. **Hierarquia ambígua:** manter filhos apenas por adição produz uma visão
   histórica. Se a necessidade for a estrutura atual, resultados podem incluir
   issues que deixaram de ser filhas.
4. **Sucesso ambíguo:** processo com exit code zero, resposta do modelo e avanço
   da issue são resultados diferentes. Sem definição, a taxa de sucesso não é
   comparável.
5. **Referência quebrada:** o registro pode sobreviver ao log detalhado removido
   pelo TTL.
6. **Concorrência e integridade:** append de registros não pode perder ou
   duplicar uma execução, mas o nível de garantia exigido ainda não foi aceito
   pelo negócio.
7. **Privacidade e retenção:** o registro agrega metadados de atividade e aponta
   para logs com prompt/chat. Prazo, acesso e exclusão precisam de política.

## Mercado e alternativas

Pesquisa realizada em 2026-08-21; conteúdo das fontes foi resumido.

- O [OpenAI Agents SDK — Usage](https://openai.github.io/openai-agents-python/usage/)
  trata consumo por execução com requisições, tokens de entrada, saída e total,
  além de detalhes como cache e reasoning. Isso mostra que apenas `tokens` é um
  contrato pobre para análise de consumo.
- O [OpenAI Agents SDK — Tracing](https://openai.github.io/openai-agents-python/tracing/)
  organiza uma execução ponta a ponta em trace e spans e alerta que entradas e
  saídas podem conter dados sensíveis. O padrão de mercado combina identidade,
  duração, resultado, uso e correlação, com política explícita de dados.
- [LangSmith — Cost tracking](https://docs.langchain.com/langsmith/cost-tracking)
  e [Arize Phoenix — Cost tracking](https://arize.com/docs/phoenix/tracing/how-to-tracing/cost-tracking)
  calculam custo a partir de contagens separadas, modelo/provedor e tabela de
  preços; ambos agregam por execução e por projeto/sessão. Logo, tokens sem
  unidade detalhada, preço temporal e fonte não fecham custo monetário.
- O [Kiro — Pricing](https://kiro.dev/pricing/) define crédito como unidade de
  trabalho, com multiplicadores diferentes por modelo e adicional atualmente a
  US$ 0,04 por crédito. O painel da assinatura mostra uso mensal, mas não resolve
  por si só a atribuição por issue da esteira.
- O [Kiro — Headless mode](https://kiro.dev/docs/cli/headless/) documenta prompt,
  permissões e códigos de saída, mas não documenta saída de tokens/créditos por
  execução. A viabilidade desse campo precisa ser comprovada no ambiente real.
- O [Kiro Enterprise — Monitoring and tracking](https://kiro.dev/docs/enterprise/monitor-and-track/)
  oferece atividade agregada, relatórios por usuário e prompt logs. É uma
  alternativa para governança de conta, não um substituto comprovado para a
  correlação issue/board/filhos.
- As convenções de IA generativa do
  [OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/gen-ai/) indicam
  interoperabilidade como direção de mercado, mas a escolha de padrão ou
  ferramenta é decisão técnica posterior.

### Alternativas de negócio consideradas

| Alternativa | Benefício | Limite/risco | Indicação atual |
|---|---|---|---|
| Manter logs e análise manual | nenhum investimento novo | não produz série confiável; custo humano cresce com volume | somente se volume e decisões forem irrelevantes |
| Usar apenas painel nativo do Kiro | visão de consumo da conta | não há prova de correlação por issue, etapa e hierarquia | complemento para conciliação |
| Registro mínimo por execução + consulta hierárquica | atende auditabilidade e análise local sem exigir dashboard | depende de definições e qualidade da fonte de consumo | hipótese preferida para validar |
| Plataforma completa de observabilidade | filtros, traces, custo e dashboards maduros | custo, operação, retenção externa e possível duplicação | reavaliar após provar necessidade e escala |

Nenhuma alternativa técnica foi selecionada nesta análise.

## Resultado esperado e como medir

### Resultado de negócio proposto

Permitir que operação e produto respondam, com dado rastreável e sem leitura
manual de cada chat:

1. quantas execuções ocorreram por issue, board, etapa, agente e modelo;
2. quanto tempo levaram e qual resultado normalizado tiveram;
3. qual uso mensurável foi reportado, em que unidade e por qual fonte;
4. onde está o log detalhado correspondente;
5. como os resultados se agregam da issue raiz às descendentes, sem loop nem
   dupla contagem.

### Indicadores propostos — metas pendentes do dono

| Indicador | Cálculo | Baseline | Meta/Janela |
|---|---|---|---|
| Cobertura de registro | execuções com exatamente um registro / execuções iniciadas | medir antes da entrega | dono deve definir; hipótese: >=99% em 30 dias |
| Completude mínima | registros com identidade, início/fim, duração, resultado e referência / total | inexistente | dono deve definir |
| Cobertura de consumo | registros com uso verificável / total, segmentado por plataforma/modelo | desconhecida | depende da fonte real |
| Tempo para responder uma análise | minutos entre pedido e visão consolidada conferida | dono deve informar amostra atual | dono deve definir redução alvo |
| Taxa de falha por agente/modelo/etapa | falhas normalizadas / execuções | hoje não calculável | monitorar; alvo depende da baseline |
| Reexecução sem avanço | novas execuções da mesma issue/coluna sem avanço / total | hoje não calculável | reduzir após baseline, fora de uma promessa causal deste épico |
| Integridade hierárquica | consultas sem ciclo, duplicação ou filho ilegível / consultas | inexistente | hipótese: 100% |

A entrega deve incluir um período de aferição de baseline. Não há base factual
para prometer economia ou redução percentual agora.

## Retorno e custo de não fazer

### Mecanismos de retorno

- redução do tempo manual para consolidar logs;
- identificação de falhas, timeouts e reexecuções concentradas;
- comparação operacional entre agentes/modelos/etapas;
- conciliação do consumo por execução quando a fonte permitir;
- evidência para priorizar melhoria de prompts, agentes e fluxo.

### Modelo de cálculo a preencher

`retorno mensal = horas de análise evitadas × custo-hora carregado + créditos/adicionais evitados + custo esperado de incidentes evitados`

`custo de não fazer = horas atuais de consolidação + consumo não atribuído + reexecuções não detectadas + atraso de decisões/incidentes`

Faltam: execuções/mês, horas/mês de análise, falhas e retries, créditos e
adicionais/mês, custo-hora, decisões afetadas e incidentes atribuíveis. Sem
esses dados, qualquer ROI numérico seria inventado.

O custo já observável de postergar é a impossibilidade de produzir baseline e
tomar decisões comparáveis. O custo monetário permanece não quantificado.

## Ordem preliminar de esforço

Ordem relativa para planejamento; tamanhos não são compromisso de engenharia e
não escolhem arquitetura.

1. **Fechar definições, fonte e política de dados — S/M.** Taxonomia de
   resultados, unidade de uso, hierarquia, retenção e acesso.
2. **Registrar identidade, tempos, resultado e referência por execução — M.**
   Valor mínimo e base para qualquer estatística.
3. **Garantir integridade e compatibilidade operacional — M.** Evitar perda,
   duplicação e quebra quando o log expirar ou a execução falhar.
4. **Consultar e agregar issue raiz/descendentes — M.** Exige semântica atual ou
   histórica e proteção contra ciclos/dupla contagem.
5. **Capturar e conciliar consumo real — L/incerto.** Depende do que CLI, conta
   ou provedor efetivamente expõem; pode ser entregue como indisponível até
   existir fonte confiável.
6. **Dashboards, alertas e avaliações de qualidade — L.** Só depois de volume e
   decisões recorrentes justificarem; não faz parte do escopo mínimo proposto.

## Aderência a metas e políticas

- **Aderência ao produto:** alta para confiabilidade, auditabilidade e controle
  de loops/reexecuções, temas já presentes no produto.
- **Aderência operacional:** alta ao permitir análise por issue e hierarquia,
  contexto que painéis genéricos não comprovam oferecer.
- **Meta formal/OKR:** não encontrada na issue nem na documentação consultada;
  o dono precisa indicar qual meta financia e prioriza o épico.
- **Minimização de dados:** o registro estatístico não deve duplicar prompt/chat
  sem necessidade; referências a logs existentes reduzem exposição. Requisito
  de negócio, implementação a definir.
- **Transparência:** consumo ausente deve ser `indisponível` com motivo/fonte,
  nunca zero estimado.
- **Retenção e acesso:** pendentes. Devem ser compatíveis com TTL dos logs,
  exclusão operacional e acesso ao volume persistente.
- **Portabilidade:** nomes e unidades precisam distinguir plataforma/provedor;
  não se deve presumir que todas exponham os mesmos dados.

## Entrevista pendente com o dono

As respostas devem ser tratadas como hipóteses e confrontadas com baseline e
amostra real. Para liberar decisão, o dono deve responder no histórico/comentário:

1. Quem toma qual decisão com o relatório, com que frequência, e qual exemplo
   recente não pôde ser respondido pelos logs atuais?
2. Nos últimos 30 ou 90 dias, quantas execuções, falhas/timeouts/reexecuções,
   horas de análise manual e créditos/adicionais ocorreram? Anexar fonte ou
   indicar onde medir.
3. O objetivo de consumo é **tokens técnicos**, **créditos faturados pelo Kiro**,
   **custo monetário**, ou os três? É aceitável registrar `indisponível` quando
   não houver fonte confiável?
4. "Sucesso" significa processo concluído, resposta válida do agente, avanço de
   coluna, PR/entrega aceita ou outra regra? Quais estados fechados são exigidos?
5. A árvore de filhos deve refletir a relação **atual** ou o histórico de todos
   os vínculos? Como tratar issue removida, movida, sem registro ou com ciclo?
6. Por quanto tempo estatísticas e referências devem existir? Quem pode acessar,
   exportar e excluir? O que deve acontecer quando o log detalhado expirar?
7. Qual tempo máximo aceitável para o registro não impactar o loop e qual
   garantia é necessária diante de crash/restart: sem perda, sem duplicidade,
   ou reconciliação posterior?
8. Qual meta/OKR, prazo e responsável pela aferição justificam prioridade? O
   primeiro corte pode ser registro + consulta exportável, sem dashboard e sem
   prometer consumo que o CLI não forneça?

## Critérios para aprovar

Aprovar somente quando houver:

- usuário, decisão e frequência confirmados;
- baseline ou plano de baseline com responsável e prazo;
- unidade/fonte de consumo verificável e regra para indisponibilidade;
- taxonomia de resultado e semântica da hierarquia aceitas;
- metas de cobertura, completude e tempo de análise;
- retenção, acesso, exclusão e relação com TTL definidas;
- meta de negócio e prazo explícitos;
- aceite do recorte mínimo e da exclusão de dashboards/tecnologia desta etapa.

Recusar ou reescrever se o painel nativo já responder às decisões com evidência,
se o volume não justificar o custo, ou se não houver fonte confiável nem uso
real para os dados solicitados.
