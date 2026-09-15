# Change #245 — Gate de elegibilidade por intenção confirmada em keep_task

- **Tipo:** confiabilidade / integridade entre boards (story 5 de 6 do épico
  #230 — Integridade de issues entre boards)
- **Plataforma afetada:** `src/__main__.py` (loop de `keep_task`),
  `src/core/participation_migration.py` (novo módulo)
- **Compatibilidade:** sem mudança em `pipe.yml`; sem novo arquivo de estado
  interno. O campo `participation_intent` já é escrito no snapshot pelas
  camadas de classificação/reconciliação (stories 2–4, tasks #248–#256); esta
  story apenas o **lê** no gate e **migra** entradas legadas que ainda não o
  possuem. Itens de fila sem `next_attempt_at` seguem imediatamente elegíveis
  (compatibilidade retroativa, sem migração adicional).
- **Implementação:** entregue via decomposição em 2 tasks técnicas, ambas
  mergeadas nesta branch de story
  (`story/245-gate_de_elegibilidade_por_intencao_confirmada_em_keep_task`):
  - **#257** — migração de snapshots legados (PR #292)
  - **#258** — gate em `keep_task` com evento deduplicado (PR #293)

## Problema

Antes desta entrega, `keep_task` selecionava e fazia auto-advance de qualquer
issue elegível pelos filtros existentes (status, coluna com `agent`,
`change.advance`, bloqueios, cooldown), **sem exigir prova de que a
participação naquele board fosse intencional**. Uma participação propagada por
efeito colateral do GitHub Projects V2 (sub-issue adicionada a um board por
vínculo de parent, sem `Status`) — ou qualquer resíduo que escapasse das
camadas de reconciliação por falha, resíduo histórico ou regressão — podia ser
despachada ao agente no board errado. A amostra do épico pai já havia
demonstrado o custo: 17/17 relações propagadas, 7 despachos indevidos e ~20,35
créditos consumidos.

Faltava a **barreira final** independente das camadas anteriores: um gate que,
mesmo que a classificação/reconciliação falhe, impeça o despacho sobre qualquer
participação não confirmada como intencional — sem realizar chamadas de rede
dentro de `keep_task`.

## Mudanças implementadas

Entregues pelas 2 tasks filhas da story (ambas mergeadas na branch da story):

- **#257 — Migrar snapshots legados sem `participation_intent` no full sync de
  startup** (`src/core/participation_migration.py`,
  `migrate_legacy_participation_intent`, invocada em `src/__main__.py`): função
  pura sem I/O de rede que lê e escreve apenas os snapshots locais
  (`.pipe/boards/<board_id>/snapshot.json`), rodando uma única vez por issue no
  full sync de startup, **antes** do primeiro `keep_task`. Para cada entrada
  ainda sem o campo (distingue ausente de presente-com-`None`, nunca
  sobrescreve valor já preenchido): issue presente em exatamente **1** board
  configurado recebe `origin`; issue presente em **2+** boards recebe
  `unresolved` em todas as entradas — nenhuma escolha automática de qual board é
  a origem legítima (ADR-001, "Duplicidades legadas sem label permanecem
  bloqueadas"). Não remove resíduo histórico automaticamente.

- **#258 — Gate de `participation_intent` em `keep_task` com evento
  deduplicado** (`src/__main__.py`):
  - `_has_confirmed_intent(issue)` — helper puro, sem I/O: retorna `True`
    apenas se `participation_intent` for `origin` ou `authorized`. Campo
    ausente, `None`, vazio, `propagated` ou `unresolved` retornam `False`
    (falha fechada, RN-B01).
  - `_log_unconfirmed_intent_once(...)` + cache em memória
    `_unconfirmed_intent_logged` — emite o evento
    `dispatch_blocked_unconfirmed_intent` **deduplicado por
    `(board, coluna, issue)`**, seguindo o mesmo padrão efêmero (só em memória
    de processo) do cache de cooldown de reexecução; reloga apenas se a issue
    mudar de coluna (chave nova) ou o processo reiniciar.
  - Gate aplicado nos **dois pontos** do laço de `keep_task`: no auto-advance
    da coluna `todo` e na seleção para despacho. Na seleção, o gate vem
    **antes** do cooldown, para não consumir nem reiniciar o cooldown de uma
    issue que nunca chega a ser executada. Nenhuma chamada de rede.

## Critérios de aceitação — verificação

- `participation_intent` = `origin`/`authorized` → issue permanece candidata,
  sujeita aos demais filtros — coberto por `tests/test_participation_intent_gate.py`.
- `participation_intent` = `propagated`/`unresolved` ou ausente → ignorada para
  seleção e auto-advance, com `dispatch_blocked_unconfirmed_intent` deduplicado
  — coberto por `tests/test_participation_intent_gate.py`.
- Multi-board autorizado (intenção confirmada em dois boards) → elegível em
  ambos — coberto por `tests/test_participation_intent_gate.py`.
- Participação propagada já reconciliada (removida do board) → não é mais
  candidata no board indevido — coberto por `tests/test_participation_intent_gate.py`.
- Snapshot legado sem o campo → migrado no full sync de startup antes do
  primeiro `keep_task` (unicidade → `origin`, duplicidade → `unresolved`);
  nenhuma issue chega a `keep_task` sem o campo — coberto por
  `tests/test_participation_intent_migration.py`.
- Item de fila sem `next_attempt_at` (formato anterior) → continua elegível
  imediatamente, sem migração adicional — comportamento preservado; não houve
  alteração no processamento de fila nesta story.
- Gate sem chamada de rede — `_has_confirmed_intent` e a migração leem
  exclusivamente dados locais já carregados; verificável por inspeção e pelos
  testes que exercitam o gate sem `BoardPort`.

Verificação executada nesta etapa (branch da story):

```
$ python -m pytest tests/test_participation_intent_gate.py \
                   tests/test_participation_intent_migration.py -q
31 passed
```

As fixtures pré-existentes de `keep_task`
(`tests/test_rerun_cooldown.py`, `tests/test_auto_advance_enqueue.py`,
`tests/test_autonomous_operation.py`) foram atualizadas para incluir
`participation_intent='origin'`, refletindo o estado pós-migração.

## Não objetivos (mantidos fora desta entrega)

- Classificar participações ou executar reconciliação — consumido das stories
  2–4 (tasks #248–#256); esta story apenas lê o campo já cacheado.
- Conjunto completo de eventos de observabilidade além do
  `dispatch_blocked_unconfirmed_intent` mínimo do gate.
- Migração ou limpeza de resíduos materializados antes da entrega do épico.

## Estado dos bloqueios

A story #245 dependia das 2 tasks acima. Ambas percorreram todo o fluxo do
board `task` (desenvolvimento → testes → code review → merge) e estão na coluna
terminal `encerrado`, com `/blocks #245` removido pelos próprios bodies das
tasks. O body de #245 não possui `/blocked_by` e o snapshot registra
`blocked_by: []`. A story está desbloqueada.

## Observação de integração (fora de escopo desta etapa)

O trabalho desta story e das demais do épico #230 vive na branch de story
`story/245-...`, derivada de `epic230-230-integridade_de_issues_entre_boards`,
não de `main`. A integração ao épico (e posterior merge à `main`) segue o fluxo
`story → epic` configurado no board e continua pendente. Sinalizado no
addcomment para o Tech Lead de integração.
