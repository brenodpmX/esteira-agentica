# US — Bloquear destino ausente/inválido, retomar após falha e registrar evidência de cada tentativa

Status: draft
Owner: product
Last updated: 2026-08-26

## Inputs
- `doc/requirements/migracao-de-boards/functional-requirements.md` (F-003, F-005, RF-005, RF-009 a RF-012)
- `doc/requirements/migracao-de-boards/business-rules.md` (RN-003, RN-005, RN-006, RN-008)
- `doc/requirements/migracao-de-boards/non-functional-requirements.md`
- `doc/architecture/migracao-segura-colunas/overview.md` (seção "Observabilidade")
- `doc/architecture/migracao-segura-colunas/constraints.md`

## Descrição

Como operador da esteira,
Quero que uma retirada de coluna sem destino declarado seja bloqueada sem
alterar nenhuma issue, que uma migração interrompida por falha retome do
ponto em que parou sem perder nem duplicar issues, e que toda tentativa
registre contagem inicial, itens movidos, itens restantes e resultado,
Para poder confiar na operação não assistida da esteira e auditar cada
mudança estrutural sem depender de arquivos internos protegidos.

## Regras de negócio

- RN-003: destino ausente para coluna ocupada bloqueia a retirada sem
  alterar a classificação atual de nenhuma issue — mesmo tratamento de F-004
  (destino inválido), já coberto pela story de migração; aqui o foco é o
  caso de ausência total de `column-migrations` para a origem.
- RN-005: falha ou interrupção durante a migração preserva a origem ativa e
  permite nova tentativa sem intervenção manual prévia — a esteira pode
  operar sem supervisão em container.
- RN-006: repetir a migração (após falha ou reprocessamento) não perde nem
  duplica issues — uma issue já no destino não é recontada como movida nem
  reprocessada como erro.
- RN-008: toda tentativa — concluída, bloqueada ou interrompida — produz
  evidência com contagem inicial, itens movidos, itens restantes e
  resultado, acessível sem leitura de `snapshot.json`/`changeQueue.json`.

## Critérios de aceitação

- Dado uma coluna ocupada por N issues (N > 0) sem nenhuma entrada
  correspondente em `column-migrations`, quando a reconciliação avalia essa
  origem, então nenhuma issue é movida, a opção de `Status` não é retirada,
  e o resultado registrado é "bloqueada" com motivo "destino ausente".
- Dado uma migração de N issues que falha (indisponibilidade do provedor,
  rate limit, encerramento do processo) após M issues movidas (0 ≤ M < N),
  quando uma nova execução da esteira ocorre, então as M issues permanecem
  no destino, a origem contém as N-M restantes, a opção de `Status` da
  origem não foi retirada, e a nova tentativa migra apenas as N-M restantes
  sem reprocessar as M já corretamente movidas.
- Dado o cenário acima repetido múltiplas vezes (ex.: falha a cada
  tentativa antes de completar), quando a soma de todas as tentativas é
  observada, então nenhuma das N issues originais é perdida (fica sem
  coluna) nem duplicada (contada como movida mais de uma vez, ou movida por
  engano de volta à origem).
- Dado uma passagem completa de leitura da origem que não reduz o número de
  issues observadas (ausência de progresso), quando a esteira detecta essa
  condição, então a tentativa é interrompida com resultado "interrompida" e
  motivo "sem progresso", a origem permanece ativa, e não ocorre laço
  infinito de tentativas na mesma execução.
- Dado qualquer tentativa (concluída, bloqueada ou interrompida), quando o
  operador consulta os logs da esteira, então encontra ao menos:
  `board`, `source`, `destination` (quando aplicável), `initial_count`,
  `moved_count`, `remaining_count`, `result`, `reason` (quando bloqueada ou
  interrompida) — sem necessidade de ler `snapshot.json` ou
  `changeQueue.json`.
- Dado um resultado "bloqueada", quando o operador lê o log, então o motivo
  identifica de forma acionável qual coluna/board e por que o destino é
  ausente ou inválido, sem exigir correlação manual entre múltiplos
  registros.

## Não objetivos

- Definir a política de rate limit/throttle (reutiliza o mecanismo já
  existente descrito no README, seção "Rate Limit (GitHub)").
- Criar journal de migração, banco, broker ou qualquer estado persistido
  novo — a retomada deriva exclusivamente do estado remoto (ADR-002).
- Implementar rollback dos itens já movidos em caso de falha parcial —
  decisão arquitetural já fechada (ADR-001) de que o estado parcial é válido
  e convergente.
- Métricas agregadas de produto por 90 dias (fica para infraestrutura de
  observabilidade externa, fora desta entrega).

## Rastreabilidade

- F-003, F-005 (functional-requirements.md).
- RF-005, RF-009, RF-010, RF-011, RF-012.
- RN-003 (caso ausência), RN-005, RN-006, RN-008 (business-rules.md).
- Overview — seção "Observabilidade" (campos do evento
  `column_migration_attempt`).
- Constraints: "Não usar sleep arbitrário como prova de quiescência"; "Não
  persistir uma lista paralela de IDs já movidos".

## Dependências

- Depende da story "Migrar todas as issues de uma coluna ocupada para o
  destino válido" para o caminho feliz de migração sobre o qual a retomada e
  o bloqueio se apoiam.
