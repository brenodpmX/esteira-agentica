# US — Migrar todas as issues de uma coluna ocupada para o destino válido antes de retirá-la

Status: draft
Owner: product
Last updated: 2026-08-26

## Inputs
- `doc/requirements/migracao-de-boards/functional-requirements.md` (F-002, F-004, F-006, RF-003 a RF-008)
- `doc/requirements/migracao-de-boards/business-rules.md` (RN-002 a RN-004, RN-007)
- `doc/requirements/migracao-de-boards/non-functional-requirements.md`
- `doc/architecture/migracao-segura-colunas/overview.md`
- `doc/architecture/migracao-segura-colunas/decisions/adr-002-intencao-declarativa-e-retomada-remota.md`
- `doc/architecture/migracao-segura-colunas/constraints.md`

## Descrição

Como operador da esteira,
Quero que todas as issues de uma coluna ocupada sejam movidas para o
destino único e válido declarado antes de a opção da coluna ser retirada do
board,
Para que nenhuma issue fique sem classificação e a coluna de origem só deixe
de existir quando estiver de fato vazia no board remoto.

## Regras de negócio

- RN-002: coluna ocupada exige destino único e explícito, do mesmo board,
  antes da retirada — todas as issues da origem vão para o mesmo destino.
- RN-003: destino inválido (inexistente, de outro board, igual à própria
  origem, ou também em retirada na mesma operação) bloqueia a retirada sem
  alterar a classificação — tratado nesta story como validação prévia ao
  primeiro `move_issue`.
- RN-004: a coluna de origem permanece ativa enquanto houver qualquer issue
  nela, inclusive issues que chegam durante a migração — a verificação de
  "vazia" é repetida imediatamente antes da retirada efetiva.
- RN-007: a migração altera exclusivamente o `Status` da issue; id,
  conteúdo, relações e demais atributos não são reenviados nem alterados.
  Eventos `on_in`/`on_out` continuam a cargo do fluxo de sincronização já
  vigente, não desta migração.

## Critérios de aceitação

- Dado uma coluna de origem ocupada por N issues (N > 0) e um destino
  declarado que existe na configuração resultante do mesmo board, é
  diferente da origem e não é outra coluna também em retirada, quando a
  migração é executada, então todas as N issues são movidas para o destino
  e, ao final, uma leitura remota confirma a origem vazia antes da opção de
  `Status` ser retirada.
- Dado o mesmo cenário, quando cada issue é movida, então apenas o campo
  `Status` é alterado — título, body, labels, relações e estado
  aberto/fechado permanecem exatamente como estavam antes da migração.
- Dado um destino inexistente, de outro board, igual à própria origem, ou
  também presente como origem em outra entrada de `column-migrations` na
  mesma operação, quando a migração avalia essa origem, então nenhuma
  chamada de movimentação é feita, a opção de `Status` da origem não é
  retirada, e o motivo da invalidez é identificável (existe, mesmo board,
  diferente da origem, não também retirado).
- Dado uma migração que já moveu todas as N issues inicialmente contadas,
  quando uma issue adicional é classificada na origem antes da retirada
  efetiva (ex.: sincronização concorrente), então essa issue também é
  migrada para o mesmo destino, e a retirada só ocorre quando uma leitura
  imediatamente anterior confirmar a origem vazia.
- Dado duas origens distintas sendo retiradas na mesma execução, uma com
  destino válido e outra com destino inválido, quando a reconciliação é
  executada, então a origem com destino válido é migrada e retirada
  normalmente, independentemente do bloqueio da outra.

## Não objetivos

- Definir o comportamento em caso de falha/interrupção no meio da migração
  ou de nova tentativa sobre estado parcial (fica para a story de bloqueio,
  retomada e observabilidade).
- Registrar o evento estruturado completo de observabilidade por tentativa
  (esta story produz o comportamento correto; o formato e garantia de
  registro ficam concentrados na story seguinte, que também cobre este
  fluxo com sucesso).
- Alterar `on_in`/`on_out` ou qualquer regra de movimentação fora do gatilho
  de retirada estrutural de coluna (RN-009, fora de escopo do épico).

## Rastreabilidade

- F-002, F-004, F-006 (functional-requirements.md).
- RF-003, RF-004, RF-005, RF-006, RF-007, RF-008.
- RN-002, RN-003, RN-004, RN-007 (business-rules.md).
- ADR-002 (validação semântica do destino, retomada pelo estado remoto).
- Constraints: limite de atomicidade do provider (janela residual TOCTOU) —
  tratado por leitura imediatamente anterior à contração, sem operação local
  entre as duas chamadas.

## Dependências

- Depende da story "Declarar destino de migração e preparar a estrutura
  remota" para que o destino já exista no board remoto antes da primeira
  movimentação.
