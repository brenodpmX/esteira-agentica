# Resultados de Teste — Bloquear novos vínculos pai/filho entre boards distintos quando `suspended`

Status: approved
Owner: quality
Last updated: 2026-08-28

## Inputs
- `doc/quality/integridade-de-issues-entre-boards/test-cases-bloquear-novos-vinculos-pai-filho-entre-boards-distintos-quando-suspended.md`
- Task #256 — Bloquear novos vínculos pai/filho entre boards distintos quando `suspended`
- Implementação: `src/core/board.py` (`_is_cross_board_link_blocked`,
  `Board.apply_commands`), `src/core/sync.py` (`_apply_change_up`),
  `tests/test_cross_board_contingency.py`

## CT01 — Novo `parent` bloqueado quando `suspended` e board do alvo é distinto

**Resultado:** passed

**Observações:**
- `test_parent_new_blocked_when_suspended_cross_board` cobre exatamente o
  cenário: `set_parent` não é chamado, log `cross_board_link_blocked` emitido
  uma vez com `relation="parent"`, `target_id="10"`, `board_id="board-a"`,
  `issue_id="1"`; `deltas["parent"]["added"]` não contém `"10"`.

## CT02 — Novo `parent` aplicado quando `suspended` mas board do alvo é o mesmo

**Resultado:** passed

**Observações:**
- `test_parent_new_applied_when_same_board`: `set_parent` chamado
  normalmente, nenhum log de bloqueio, `deltas["parent"]["added"]` contém o
  novo parent.

## CT03 — Novo `parent` entre boards distintos aplicado quando `enabled` (ou chave ausente)

**Resultado:** passed

**Observações:**
- `test_parent_new_applied_when_not_suspended` parametrizado para `enabled`
  e ausência da chave (`None`); ambos aplicam `set_parent` normalmente, sem
  log de bloqueio.

## CT04 — Remoção de `parent` existente nunca é bloqueada, mesmo com `suspended` e board distinto

**Resultado:** passed

**Observações:**
- `test_parent_removal_never_blocked`: `set_parent` chamado com `None`
  (remoção aplicada), nenhum log de bloqueio, `deltas["parent"]["removed"]`
  contém o id removido.

## CT05 — `children`: id em board distinto é bloqueado, id no mesmo board é aplicado (mesma chamada)

**Resultado:** passed

**Observações:**
- `test_children_partial_block`: `set_children` chamado uma única vez apenas
  com `["20"]` (mesmo board); um único log de bloqueio para `"10"`
  (`relation="children"`); `deltas["children"]["added"] == {"20"}`.

## CT06 — `children`: todos os ids adicionados bloqueados e sem outra diferença não chama `set_children`

**Resultado:** passed

**Observações:**
- `test_children_all_blocked_skips_set`: `set_children` não é chamado; log de
  bloqueio emitido para `"10"`; id bloqueado ausente de
  `deltas["children"]["added"]`.

## CT07 — `children`: remoção de id existente sempre aplicada, mesmo com `suspended` e board distinto

**Resultado:** passed

**Observações:**
- `test_children_removal_always_applied`: `set_children` chamado com lista
  vazia (remoção aplicada); nenhum log de bloqueio; `"10"` presente em
  `deltas["children"]["removed"]`.

## CT08 — Ausência de `resolve_board_fn` preserva o comportamento atual (sem regressão)

**Resultado:** passed

**Observações:**
- `test_no_resolve_fn_preserves_behavior`: gate ignorado, `set_parent` e
  `set_children` aplicados normalmente sem `resolve_board_fn`. Suítes
  pré-existentes (`test_sync_optimization.py`, `test_sanitize_relations.py`)
  também passaram sem alteração (ver seção "Regressão").

## CT09 — Alvo não rastreado (`resolve_board_fn` retorna `None`) não é bloqueado

**Resultado:** passed

**Observações:**
- `test_untracked_target_not_blocked`: `set_parent` aplicado normalmente,
  nenhum log de bloqueio, conforme "sem prova de outro board, sem bloqueio".

## CT10 — Releitura de `pipe.yml` sem cache em memória entre duas chamadas na mesma execução

**Resultado:** passed

**Observações:**
- `test_config_reread_no_memory_cache`: 1ª chamada com `enabled` aplica
  `set_parent`; após sobrescrever o `pipe.yml` para `suspended` sem recriar
  nenhum objeto, a 2ª chamada bloqueia o novo alvo — confirma releitura do
  disco a cada chamada, sem cache em memória.

## CT11 — Integração com `_apply_change_up`: `resolve_board_fn` é passado corretamente a partir de `_find_snapshot_issue`

**Resultado:** passed

**Observações:**
- `test_integration_apply_change_up_blocks_cross_board`: fluxo real via
  `_apply_change_up` com snapshots de `board-a`/`board-b` e arquivo
  `-body.md` com `/parent #99` bloqueia corretamente o vínculo cross-board,
  mesmo efeito de CT01 disparado pelo caminho de sincronização real.

## CT12 — Não regressão da suíte existente

**Resultado:** passed

**Observações:**
- `python -m pytest tests/ -k "sync_optimization or sanitize_relations or cross_board or config" -v`:
  **122 passed, 11 skipped** — sem regressão nos testes pré-existentes de
  `apply_commands` (`test_sync_optimization.py`) e de sanitização de relações
  (`test_sanitize_relations.py`).
- `python -m pytest` (suíte completa): **21 failed, 1295 passed, 29 skipped,
  1 xpassed**. As 21 falhas estão integralmente em
  `tests/test_agent_log_descritivo.py` e `tests/test_dockerfile.py` — arquivos
  não tocados por esta task (formatação de log de agente e verificação de
  SHA256/versão pinada do kiro-cli no Dockerfile). Confirmado que são
  **pré-existentes e independentes** desta alteração: reexecutados isolados
  na base atual (sem qualquer modificação local — working tree limpo antes e
  depois), apresentam exatamente as mesmas 21 falhas, coerente com o relato
  já registrado na etapa de Desenvolvimento (verificação via `git stash`).

## Resumo

- Total: 12
- Passou: 12
- Falhou: 0
- Bloqueado: 0

Nenhuma dúvida ou ambiguidade nos casos de teste. Todos os cenários descritos
na seção "Como testar" da issue #256 foram cobertos e confirmados. Nenhum
código ou caso de teste foi alterado durante esta execução — apenas leitura e
execução da suíte já implementada.
