# Requisitos Funcionais — Circuit-break de agente

Status: approved · Owner: requirements · Updated: 2026-08-24
Inputs: `doc/product/circuit-break-de-agente/analise-negocio.md` (RN01–RN09,
critérios de aceite de negócio 1–8), `doc/requirements/circuit-break-de-agente/business-rules.md`,
`doc/requirements/circuit-break-de-agente/glossary.md`

## Atores

- **Operador da esteira:** pessoa ou organização que configura o `pipe.yml`,
  define (ou não) a política de circuit-break, monitora bloqueios, corrige ou
  redireciona issues bloqueadas e remove `need_human` para liberar retomada.
  Pode ser a mesma pessoa responsável pela conta do agente ou uma equipe;
  a esteira não impõe SLA de resposta (decisão do dono, 22/08/2026).
- **Núcleo da esteira (`keep_task`):** componente que seleciona a próxima
  issue elegível e decide, a cada seleção, se a execução deve ou não ser
  entregue ao agente.
- **Agente:** executor que recebe a issue entregue; não participa da decisão
  de bloqueio e não tem conhecimento da política (o bloqueio ocorre antes da
  entrega).

## Dados

- **Ocorrência de execução:** registro do instante de início de uma execução
  entregue ao agente, identificado por `(board, coluna, issue)`. Não
  armazena resultado (erro/sucesso) — todo início conta (RN-001).
- **Contexto de contagem:** chave `(board, coluna, issue)` sobre a qual as
  ocorrências são agrupadas. Mudança de coluna cria um novo contexto
  (RN-002).
- **Política de circuit-break:** configuração opcional, geral para a
  instância, composta por limite `N` (inteiro positivo, quantidade de
  execuções) e janela `T` (duração de tempo). Ausência de configuração
  equivale a política inativa (RN-007, RN-008).
- **Marcação `need_human`:** label já existente na esteira (ver README,
  seção "Anotações no body"); este épico adiciona sua aplicação pelo núcleo,
  sem depender do agente escrever `/need_human` no body.
- **Comentário de bloqueio:** texto acionável anexado à issue no instante do
  bloqueio, contendo no mínimo: motivo, issue, board, coluna, limite `N` e
  janela `T` (RN-005).

## Requisitos

### RF-001 — Contar toda execução entregue ao agente
- Descrição: o sistema deve registrar uma ocorrência para o contexto
  `(board, coluna, issue)` no instante em que decide entregar a issue ao
  agente, antes de conhecer o resultado da execução.
- Ator: núcleo da esteira.
- Pré-condição: a issue foi selecionada como elegível para execução (mesmo
  ponto de decisão hoje usado pelo cooldown em `keep_task`).
- Fluxo principal: `keep_task` seleciona a issue elegível → registra a
  ocorrência do contexto atual → entrega a issue ao agente.
- Alternativos/exceções: se a política de circuit-break não estiver
  configurada, a ocorrência ainda é registrada (a contagem continua
  internamente), apenas o bloqueio (RF-003) fica inativo.
- Critérios de aceitação:
  - Dado que uma issue é selecionada para execução, quando a entrega ao
    agente ocorre, então uma ocorrência é registrada para o contexto
    `(board, coluna, issue)`, independentemente do resultado futuro da
    execução.
  - Dado que a execução anterior terminou com sucesso técnico sem mudança de
    coluna, quando uma nova execução é entregue no mesmo contexto, então ela
    também gera uma nova ocorrência (não é descartada por ter sido
    "bem-sucedida").
- Fonte: análise de negócio, RN01; RN-001 de business-rules.md.

### RF-002 — Isolar a contagem por contexto e reiniciá-la a cada mudança de coluna
- Descrição: o sistema deve manter contagens independentes por
  `(board, coluna, issue)`; ao mudar de coluna, a issue passa a acumular
  ocorrências em um contexto novo, sem herdar a contagem do contexto
  anterior.
- Ator: núcleo da esteira.
- Pré-condição: a issue muda de coluna, por auto-advance local ou por
  movimentação manual detectada no sync.
- Fluxo principal: a issue é movida de uma coluna para outra → o contexto
  anterior (board, coluna antiga, issue) fica congelado, sem novas
  ocorrências → o contexto novo (board, coluna nova, issue) inicia com zero
  ocorrências.
- Alternativos/exceções: se a issue retorna a uma coluna por onde já havia
  passado, o contexto correspondente inicia contagem nova — não retoma o
  histórico anterior daquela combinação específica.
- Critérios de aceitação:
  - Dado um contexto que acumulou ocorrências em uma coluna, quando a issue
    muda de coluna, então o novo contexto não contém nenhuma das ocorrências
    do contexto anterior.
- Fonte: análise de negócio, RN02, critério de aceite de negócio 5; RN-002 de
  business-rules.md.

### RF-003 — Bloquear execução que excederia o limite configurado
- Descrição: o sistema deve impedir que uma issue seja entregue ao agente
  quando o contexto já possui `N` ou mais ocorrências dentro da janela `T`
  configurada.
- Ator: núcleo da esteira.
- Pré-condição: a política de circuit-break está configurada (`N` e `T`
  definidos); a issue foi identificada como elegível pelos demais critérios
  de `keep_task` (não bloqueada por `/blocked_by`, não em cooldown, etc.).
- Fluxo principal: `keep_task` seleciona a issue elegível → verifica a
  quantidade de ocorrências do contexto dentro da janela `T` → se
  `quantidade >= N`, não entrega a issue ao agente e aciona RF-004 e RF-005
  → se `quantidade < N`, segue o fluxo normal (RF-001).
- Alternativos/exceções: sem política configurada, este requisito não se
  aplica (ver RF-006).
- Critérios de aceitação:
  - Dado um contexto com `N` ou mais ocorrências dentro da janela `T`,
    quando a issue seria selecionada para nova execução, então a execução
    não é iniciada.
  - Dado um contexto com menos de `N` ocorrências dentro da janela `T`,
    quando a issue é selecionada, então a execução é iniciada normalmente.
- Fonte: análise de negócio, RN04, critério de aceite de negócio 1; RN-004 de
  business-rules.md.

### RF-004 — Desconsiderar ocorrências fora da janela configurada
- Descrição: o sistema deve considerar, para a decisão de bloqueio (RF-003),
  apenas as ocorrências cujo instante de início está dentro da janela `T`
  contada a partir do momento da avaliação.
- Ator: núcleo da esteira.
- Pré-condição: existem ocorrências registradas para o contexto avaliado.
- Fluxo principal: no momento da avaliação, o sistema descarta ocorrências
  com idade maior que `T` → conta as ocorrências restantes → usa esse total
  na decisão de RF-003.
- Alternativos/exceções: uma ocorrência com idade exatamente igual a `T` é
  tratada como fora da janela (não conta), por simetria com o comportamento
  já existente do cooldown (`_in_rerun_cooldown`).
- Critérios de aceitação:
  - Dada uma ocorrência mais antiga que a janela `T`, quando o contexto é
    avaliado, então essa ocorrência não contribui para o total usado na
    decisão de bloqueio.
  - Dada uma ocorrência com idade igual a `T`, quando o contexto é avaliado,
    então essa ocorrência é tratada como fora da janela.
- Fonte: análise de negócio, RN03, critério de aceite de negócio 4; RN-003 de
  business-rules.md.

### RF-005 — Sinalizar o bloqueio com `need_human` e motivo acionável
- Descrição: no instante em que uma execução é bloqueada por exceder o
  limite (RF-003), o sistema deve marcar a issue com `need_human` e registrar
  um comentário identificando motivo, issue, board, coluna, limite `N` e
  janela `T`.
- Ator: núcleo da esteira.
- Pré-condição: uma execução foi bloqueada por RF-003.
- Fluxo principal: o bloqueio ocorre → o sistema marca `need_human` na issue
  → o sistema registra um comentário com os dados mínimos exigidos, no mesmo
  evento do bloqueio (não como passo posterior).
- Alternativos/exceções: nenhuma — a ausência de qualquer um dos dados
  mínimos no comentário não satisfaz este requisito.
- Critérios de aceitação:
  - Dado um bloqueio acionado, quando o operador consulta a issue, então ela
    está marcada com `need_human` e possui um comentário contendo motivo,
    issue, board, coluna, limite e janela.
  - Dado o comentário de bloqueio, quando o operador o lê, então consegue
    diagnosticar a causa sem acessar arquivos de estado interno protegidos
    (ex.: `snapshot.json`, `changeQueue.json`).
- Fonte: análise de negócio, RN05, critério de aceite de negócio 2; RN-005 de
  business-rules.md.

### RF-006 — Preservar o comportamento vigente sem política configurada
- Descrição: quando a política de circuit-break não está configurada
  (`N`/`T` ausentes no `pipe.yml`), o sistema não deve bloquear nenhuma issue
  por este mecanismo, preservando o comportamento de execução atual
  (incluindo `boards.rerun_cooldown`, se configurado).
- Ator: núcleo da esteira.
- Pré-condição: `pipe.yml` não define a política de circuit-break.
- Fluxo principal: `keep_task` avalia a issue → não há limite `N`/janela `T`
  configurados → o fluxo de seleção e entrega segue sem a verificação de
  RF-003 → a contagem de ocorrências (RF-001) continua sendo feita.
- Alternativos/exceções: nenhuma. Não há valor padrão implícito para `N` ou
  `T` quando a política está ausente.
- Critérios de aceitação:
  - Dada uma instância sem a política configurada, quando qualquer issue é
    selecionada, então nenhuma execução é impedida por este mecanismo.
  - Dada uma instância sem a política configurada, quando a política é
    configurada posteriormente, então o sistema passa a aplicar RF-003 sem
    exigir reprocessamento retroativo das ocorrências já registradas.
- Fonte: análise de negócio, RN07, critério de aceite de negócio 7; RN-007 de
  business-rules.md.

### RF-007 — Reiniciar a franquia do contexto no instante do bloqueio
- Descrição: no instante em que o bloqueio (RF-003/RF-005) é acionado, o
  sistema deve zerar a contagem ativa daquele contexto, de modo que, após o
  operador remover `need_human`, a issue receba uma nova franquia completa de
  `N` execuções antes de um novo bloqueio no mesmo contexto.
- Ator: núcleo da esteira.
- Pré-condição: um bloqueio foi acionado para o contexto `(board, coluna,
  issue)`.
- Fluxo principal: o bloqueio ocorre (RF-003) → o sistema zera a contagem
  ativa do contexto no mesmo instante → o operador corrige/redireciona a
  issue e remove `need_human` → a próxima avaliação do contexto encontra
  contagem zero e permite até `N` novas execuções antes do próximo bloqueio.
- Alternativos/exceções: se a issue muda de coluna após o bloqueio, o novo
  contexto já teria contagem zero por força de RF-002, independentemente
  deste requisito.
- Critérios de aceitação:
  - Dado um bloqueio acionado, quando a contagem do contexto é consultada
    imediatamente após o bloqueio, então ela está zerada.
  - Dado um contexto zerado por bloqueio, quando o operador remove
    `need_human` e a issue é selecionada novamente, então ela pode acumular
    até `N` novas ocorrências antes de um novo bloqueio.
- Fonte: análise de negócio, RN06, critério de aceite de negócio 6; RN-006 de
  business-rules.md.

### RF-008 — Não afetar o processamento de outras issues elegíveis
- Descrição: o bloqueio de um contexto por limite não deve impedir a seleção
  e execução de nenhuma outra issue elegível, no mesmo board ou em outro.
- Ator: núcleo da esteira.
- Pré-condição: existe pelo menos uma issue bloqueada por RF-003 e pelo menos
  uma outra issue elegível em qualquer board configurado.
- Fluxo principal: `keep_task` avalia a issue bloqueada → não a entrega ao
  agente → continua a varredura e seleciona a próxima issue elegível
  (bloqueada ou não) normalmente.
- Alternativos/exceções: nenhuma.
- Critérios de aceitação:
  - Dada uma issue bloqueada pelo limite, quando existem outras issues
    elegíveis, então elas continuam sendo selecionadas e executadas no mesmo
    ciclo ou em ciclos subsequentes.
- Fonte: análise de negócio, RN09, critério de aceite de negócio 8; RN-009 de
  business-rules.md.

## Fora de escopo (não requisitos funcionais deste baseline)

Diagnóstico automático de causa raiz, dashboard, definição de SLA de resposta
humana, política segmentada por board/coluna/agente, orçamento agregado de
tokens (tratado no épico #177), tratamento de loops de sincronização (épico
#184) e qualquer decisão de arquitetura, armazenamento ou tecnologia —
conforme escopo aprovado na análise de negócio.
