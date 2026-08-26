# Requisitos Não-Funcionais — Integridade de issues entre boards

Status: baseline de requisitos
Owner: requirements
Last updated: 2026-08-26

## Inputs
- `doc/product/integridade-de-issues-entre-boards/vision.md`
- `doc/product/integridade-de-issues-entre-boards/problem-space.md`
- `doc/product/integridade-de-issues-entre-boards/epicos.md`
- `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`
- Histórico de entrevista com o dono (issue #230, 2026-08-26)

Este documento explicita atributos de qualidade mensuráveis derivados das
métricas de sucesso de `vision.md` e dos requisitos funcionais RF-01 a RF-09,
para uso como critério de validação por arquitetura e QA. Não redefine
escopo funcional nem propõe mecanismo técnico — apenas "quão bem" cada
garantia deve se comportar e como medi-la.

## Integridade

- **Zero execução de agente em board não intencional** durante 30 dias
  corridos após a disponibilização em produção, com evidência de rollout
  (RN-B08) — esta é a métrica de integridade mais crítica, herdada
  diretamente de `vision.md`.
- **100% das participações não intencionais reconciliadas antes de receber
  `Status` executável** — medido pela comparação entre o timestamp da
  propagação e o timestamp em que a participação recebeu `Status`
  (quando recebeu). Nenhuma reconciliação pode ocorrer depois que a
  participação já se tornou elegível a despacho.
- **Zero relação pai/filho perdida ou alterada** como efeito colateral de
  qualquer reconciliação, verificado antes/depois de cada operação de
  reconciliação, para 100% das relações pai/filho ativas.
- **Zero participação multi-board explicitamente autorizada removida** por
  engano — verificado em 100% das participações classificadas como
  autorizadas (RN-B04) durante a janela de validação.
- A distinção entre "participação propagada sem prova" e "issue nova
  legítima sem coluna" deve ser determinística: dado o mesmo estado de
  snapshot e de board remoto, o mesmo par (issue, board) deve produzir
  sempre a mesma classificação — sem depender de ordem de execução ou de
  condição de corrida entre ciclos de sync.

## Disponibilidade / Continuidade

- Uma participação em espera por falta de prova de propagação (RN-B01/RN-B02)
  não pode impedir o processamento de outras issues elegíveis no mesmo board
  ou em outros boards — isolamento de falha por item, na mesma linha já
  exigida para o incidente #97 (`doc/requirements/confiabilidade-parent-recursivo/non-functional-requirements.md`).
- Uma falha transitória ao consultar a prova de propagação (RN-B02) ou ao
  executar a reconciliação (RF-02) deve ser retentada em ciclos
  subsequentes, sem descartar o evento e sem, nesse intervalo, permitir
  despacho sobre a participação não resolvida.
- A ativação ou desativação da contingência de suspensão de vínculos
  (RF-09/RN-B07) deve ter efeito a partir do próximo vínculo avaliado, sem
  exigir reinício da esteira ou novo deploy.

## Desempenho

- A verificação de intencionalidade de uma participação recém-detectada não
  deve adicionar mais do que uma quantidade pequena e limitada de chamadas
  de rede adicionais por participação avaliada (ordem de unidades, não de
  dezenas) — o custo já observado hoje é de uma consulta GraphQL adicional
  por operação destrutiva equivalente (`_belongs_to_board`); a prova de
  propagação deve seguir esse mesmo patamar de custo.
- A reconciliação de uma participação detectada como não intencional deve
  concluir (ou falhar de forma retentável) dentro do mesmo ciclo de sync em
  que a propagação foi detectada, salvo falha transitória do board externo.
- A verificação de intencionalidade não deve depender de varrer todas as
  issues de todos os boards a cada ciclo — deve ser acionada pelo evento que
  cria a relação pai/filho ou pela descoberta remota já existente
  (`create-down`), sem introduzir um novo laço de varredura completa.

## Escalabilidade

- A prevenção e a reconciliação (RN-B10) devem continuar válidas
  independentemente do número de boards configurados em `pipe.yml` e do
  número de pares de fluxo hierárquico existentes — nenhuma lista hardcoded
  de pares de board é aceitável como mecanismo de cobertura.
- O volume de participações em espera (RN-B01) tratadas simultaneamente não
  deve degradar o tempo de ciclo de sync dos boards não afetados — mesmo
  princípio de isolamento por item já aplicado à fila de sincronização.
- A meta de validação (30 dias, mínimo 17 novas relações entre boards) deve
  ser mensurável independentemente de o volume real ser maior ou menor que
  17 no período — se for menor, a janela se estende até atingir a amostra
  (RN-B05), sem exigir mudança de instrumentação.

## Observabilidade

- Todo evento relevante (detecção de propagação, reconciliação automática,
  falha de reconciliação, despacho indevido, remoção manual) deve ser
  registrável com issue, board de origem, board propagado/indevido e
  timestamp — permitindo calcular o tempo entre propagação e reconciliação
  para qualquer issue da amostra (RF-07).
- Deve ser possível, a partir dos registros, apurar isoladamente: número de
  participações propagadas, número de reconciliações automáticas, número de
  remoções manuais (que devem ser zero durante a janela de validação),
  número de despachos indevidos e créditos consumidos por eles — sem
  necessidade de correlação manual entre múltiplas fontes de log.
- Deve ser possível distinguir, nos registros, resíduo da janela do
  incidente (25–26/08/2026) de nova ocorrência dentro da janela de validação
  (RN-B05) — a fronteira temporal entre as duas deve estar explícita no
  registro, não inferida por número de issue.
- A evidência de rollout (commit/versão, ambiente, data) exigida por RF-06 e
  RN-B08 deve ser consultável sem inferência indireta — não basta confirmar
  que o commit está em `main`; deve ser possível identificar que ele está
  em execução no ambiente observado.

## Segurança / Integridade de estado

- Nenhuma operação de reconciliação pode remover ou alterar uma participação
  cujo `Status` já esteja preenchido sem antes confirmar, por prova de
  propagação (RN-B02), que se trata de propagação não intencional — o
  padrão seguro é preservar a participação com `Status` na ausência de
  prova, mesmo que isso implique investigação adicional.
- A verificação e a reconciliação de participações não podem ler, escrever
  ou modificar os arquivos de estado interno protegidos
  (`.pipe/boards/*/snapshot.json`, `.pipe/changeQueue.json`,
  `.pipe/throttle*.json`, listados em `PROTECTED_PATHS`) — a mesma restrição
  já aplicada a toda execução de agente se estende a qualquer novo mecanismo
  introduzido por este épico.
- Toda reconciliação automática e toda ativação/desativação da contingência
  (RF-09) devem ser auditáveis — presentes em log com timestamp e
  identificação de issue/board — sem exigir leitura de estrutura de dados
  interna para reconstruir o que ocorreu.

## Critérios de teste de regressão (cenário da amostra de 25–26/08/2026)

A solução técnica deve ser validada, no mínimo, contra a reprodução dos três
padrões já comprovados na amostra de negócio (ver `problem-space.md`, seção
"Evidência observada"):

- **Story→Epic:** ao vincular uma story (board User Stories) como filha de
  um épico (board Epics), a propagação ao Project do épico deve ser
  reconciliada antes que qualquer agente do fluxo de épicos seja despachado
  sobre a story — reprodução do padrão de #221–#223 e #226–#229.
- **Task→User Story:** ao vincular uma task (board Tasks) como filha de uma
  story (board User Stories), a propagação ao Project da story deve ser
  reconciliada antes que qualquer agente do fluxo de stories seja despachado
  sobre a task — reprodução do padrão de #231–#240 (com despacho indevido
  comprovado em #232 e #235).
- **Multi-board autorizado (regressão negativa):** uma participação marcada
  como autorizada explicitamente (RN-B04) não deve ser removida nem impedida
  de despacho pelo mesmo mecanismo que reconcilia propagações — a ausência
  desse caso de teste seria insuficiente para comprovar que a prevenção não
  produz falso positivo.
- **Falha transitória na prova de propagação:** se a consulta de
  intencionalidade falhar de forma transitória, a participação deve
  permanecer em espera (RN-B01) e ser reavaliada no ciclo seguinte, sem
  despacho no intervalo e sem descarte do evento.
- Nos três cenários positivos, a relação pai/filho entre as issues envolvidas
  deve permanecer íntegra depois da reconciliação (RN-B03), verificável por
  consulta direta à API do GitHub.
