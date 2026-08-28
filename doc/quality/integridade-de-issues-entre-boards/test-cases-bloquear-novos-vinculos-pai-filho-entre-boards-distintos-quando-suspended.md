# Casos de Teste — Bloquear novos vínculos pai/filho entre boards distintos quando `suspended`

Status: draft
Owner: quality
Last updated: 2026-08-28

## Inputs
- Task #256 — Bloquear novos vínculos pai/filho entre boards distintos quando `suspended`
- User Story #241 — Contingência de suspensão de vínculos entre boards
- Task #255 — Adicionar e validar a chave `safety.cross_board_parent_links` no
  `pipe.yml` (dependência entregue: `load_current_config`,
  `resolve_cross_board_parent_links`, `validate_cross_board_parent_links` em
  `src/core/config.py`, mergeada em `epic` no commit `ad1da07`)
- `src/core/board.py` (`Board.apply_commands`, `_sanitize_relations_with_discards`)
- `src/core/sync.py` (`_apply_change_up`, `_find_snapshot_issue`)
- `src/core/log.py` (`log.warning` com campos extras nomeados)
- ADR-003 (`doc/architecture/integridade-de-issues-entre-boards/decisions/adr-003-operacao-observavel-sem-nova-stack.md`),
  item 1: "`suspended` bloqueia apenas relação nova entre boards distintos,
  registra o fato e não altera vínculos existentes."
- Seção "Como testar" da issue #256 (lista de cenários exigidos)
- `tests/test_sync_optimization.py` (padrão `FakePort`/`_chdir_tmp` a reutilizar)

## CT01 — Novo `parent` bloqueado quando `suspended` e board do alvo é distinto

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 4; critério de aceite da story #241 ("suspensão bloqueia entre boards distintos")

**Pré-condição:**
- `pipe.yml` de teste (`tmp_path` isolado) com `safety.cross_board_parent_links: suspended`.
- `cmds.parent` define um valor novo (ausente em `known.get("parent")`).
- `resolve_board_fn` retorna um `board_id` diferente do board avaliado para o `parent` desejado.

**Passos:**
1. Chamar `board.apply_commands(board_id, issue_id, cmds, known=known, resolve_board_fn=resolve_board_fn)`.

**Resultado esperado:**
- `set_parent` NÃO é chamado no `FakePort`.
- Um log de warning com `event_type="cross_board_link_blocked"` é emitido
  (campos `board_id`, `issue_id`, `target_id`, `relation="parent"`).
- `deltas["parent"]["added"]` não contém o id bloqueado.

## CT02 — Novo `parent` aplicado quando `suspended` mas board do alvo é o mesmo

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 4; critério de aceite da story #241 ("mesmo board não é afetado")

**Pré-condição:**
- Mesmo cenário de CT01, exceto `resolve_board_fn` retorna o **mesmo**
  `board_id` do board avaliado.

**Passos:**
1. Chamar `apply_commands` com esses parâmetros.

**Resultado esperado:**
- `set_parent` é chamado normalmente com o `parent_id` desejado.
- Nenhum log `cross_board_link_blocked` é emitido.
- `deltas["parent"]["added"]` contém o id do novo parent.

## CT03 — Novo `parent` entre boards distintos aplicado quando `enabled` (ou chave ausente)

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 4; critério de aceite da story #241 ("`enabled`/ausente preserva comportamento normal")

**Pré-condição:**
- Mesmo cenário de CT01 (board do alvo distinto), exceto `pipe.yml` com
  `safety.cross_board_parent_links: enabled` (repetir também sem a chave
  `cross_board_parent_links`/sem a seção `safety`).

**Passos:**
1. Chamar `apply_commands` com esses parâmetros, para `enabled` e para
   ausência da chave.

**Resultado esperado:**
- Em ambos os casos, `set_parent` é chamado normalmente.
- Nenhum log `cross_board_link_blocked` é emitido.

## CT04 — Remoção de `parent` existente nunca é bloqueada, mesmo com `suspended` e board distinto

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 4 ("a contingência nunca impede remoção, apenas criação")

**Pré-condição:**
- `safety.cross_board_parent_links: suspended`.
- `cmds.parent` vazio/`None`; `known.get("parent")` preenchido com um id cujo
  board (via `resolve_board_fn`) é distinto do board avaliado.

**Passos:**
1. Chamar `apply_commands` com esses parâmetros.

**Resultado esperado:**
- `set_parent` é chamado normalmente (remoção aplicada).
- Nenhum log `cross_board_link_blocked` é emitido.
- `deltas["parent"]["removed"]` contém o id do parent removido.

## CT05 — `children`: id em board distinto é bloqueado, id no mesmo board é aplicado (mesma chamada)

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 5

**Pré-condição:**
- `safety.cross_board_parent_links: suspended`.
- `cmds.children` com dois ids novos (ambos ausentes em
  `known.get("children")`): um cujo `resolve_board_fn` retorna board distinto
  (bloqueado) e outro cujo `resolve_board_fn` retorna o mesmo board
  (aplicado).

**Passos:**
1. Chamar `apply_commands` com esses parâmetros.

**Resultado esperado:**
- `set_children` é chamado exatamente uma vez, apenas com o id do mesmo
  board (o id bloqueado não está na lista enviada).
- Um único log `cross_board_link_blocked` é emitido para o id bloqueado
  (`relation="children"`, `target_id=<id bloqueado>`).
- `deltas["children"]["added"]` reflete apenas o id efetivamente aplicado
  (não contém o id bloqueado).

## CT06 — `children`: todos os ids adicionados bloqueados e sem outra diferença não chama `set_children`

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 5 ("a chamada só é pulada por completo se todos os ids adicionados forem bloqueados e não houver diferença remanescente a aplicar")

**Pré-condição:**
- `safety.cross_board_parent_links: suspended`.
- `cmds.children` com um único id novo, cujo `resolve_board_fn` retorna board
  distinto (bloqueado); `known.get("children")` não contém remoções
  pendentes (nenhuma diferença remanescente).

**Passos:**
1. Chamar `apply_commands` com esses parâmetros.

**Resultado esperado:**
- `set_children` NÃO é chamado.
- Um log `cross_board_link_blocked` é emitido para o id bloqueado.
- `deltas["children"]["added"]` não contém o id bloqueado.

## CT07 — `children`: remoção de id existente sempre aplicada, mesmo com `suspended` e board distinto

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 5 ("ids removidos de children sempre continuam sendo aplicados, pelo mesmo motivo do item 4")

**Pré-condição:**
- `safety.cross_board_parent_links: suspended`.
- `known.get("children")` contém um id ausente em `cmds.children` (remoção),
  cujo `resolve_board_fn` retorna board distinto.

**Passos:**
1. Chamar `apply_commands` com esses parâmetros.

**Resultado esperado:**
- `set_children` é chamado; o id removido não está na lista desejada enviada.
- Nenhum log `cross_board_link_blocked` é emitido para o id removido.
- `deltas["children"]["removed"]` contém o id removido.

## CT08 — Ausência de `resolve_board_fn` preserva o comportamento atual (sem regressão)

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 2 ("ausência do parâmetro não deve ser tratada como 'suspenso' nem como 'bloqueia tudo'")

**Pré-condição:**
- `safety.cross_board_parent_links: suspended`.
- Chamar `apply_commands` sem informar `resolve_board_fn` (parâmetro
  omitido/`None`), com `cmds.parent`/`cmds.children` definindo relações
  novas.

**Passos:**
1. Chamar `apply_commands(board_id, issue_id, cmds, known=known)` sem o
   argumento `resolve_board_fn`.

**Resultado esperado:**
- `set_parent`/`set_children` são chamados normalmente, como antes desta
  task (gate ignorado).
- Nenhum log `cross_board_link_blocked` é emitido.
- Todos os testes pré-existentes de `test_apply_commands_*` em
  `tests/test_sync_optimization.py` e `tests/test_sanitize_relations.py`
  continuam passando sem alteração.

## CT09 — Alvo não rastreado (`resolve_board_fn` retorna `None`) não é bloqueado

**Tipo:** unitário
**Critério de aceitação:** issue #256, item 3 (docstring de `_is_cross_board_link_blocked`: "sem prova de 'outro board', não há decisão segura a tomar nesta camada")

**Pré-condição:**
- `safety.cross_board_parent_links: suspended`.
- `resolve_board_fn` retorna `None` para o id do novo `parent` (issue não
  rastreada em nenhum snapshot conhecido).

**Passos:**
1. Chamar `apply_commands` com esses parâmetros.

**Resultado esperado:**
- `set_parent` é chamado normalmente.
- Nenhum log `cross_board_link_blocked` é emitido.

## CT10 — Releitura de `pipe.yml` sem cache em memória entre duas chamadas na mesma execução

**Tipo:** integração (I/O de arquivo)
**Critério de aceitação:** issue #256, item 3 ("A chave é relida do disco a cada chamada [...] sem cache em memória do processo, para valer sem restart"); critério de aceite da story #241 ("mudança no `pipe.yml` vale no ciclo seguinte sem restart")

**Pré-condição:**
- Diretório temporário isolado (`monkeypatch.chdir(tmp_path)`, mesmo padrão
  de `tests/test_sync_optimization.py`).
- `pipe.yml` em disco com `safety.cross_board_parent_links: enabled`.
- `resolve_board_fn` fixo retornando board distinto do avaliado.
- Nenhum objeto (`Board`, config carregada) é recriado entre as chamadas.

**Passos:**
1. Chamar `apply_commands` com um novo `parent` para um board distinto —
   observar que `set_parent` é chamado (comportamento `enabled`).
2. Sobrescrever o `pipe.yml` em disco para
   `safety.cross_board_parent_links: suspended`.
3. Chamar `apply_commands` novamente, com outro novo `parent` (id diferente)
   para (outro) board distinto, sem recriar nenhum objeto.

**Resultado esperado:**
- Na primeira chamada, `set_parent` é chamado (relação aplicada).
- Na segunda chamada, `set_parent` NÃO é chamado para o novo alvo (relação
  bloqueada) e o log `cross_board_link_blocked` é emitido — confirmando que
  a segunda leitura reflete a alteração em disco, sem cache em memória.

## CT11 — Integração com `_apply_change_up`: `resolve_board_fn` é passado corretamente a partir de `_find_snapshot_issue`

**Tipo:** integração
**Critério de aceitação:** issue #256, item 6

**Pré-condição:**
- Ambiente de teste com snapshots de dois boards distintos (`board-a`,
  `board-b`), cada um com uma issue rastreada.
- `safety.cross_board_parent_links: suspended` no `pipe.yml` de teste.
- Um `ChangeItem` de `change-up` para uma issue de `board-a` com comando
  `/parent` apontando para a issue rastreada em `board-b`.

**Passos:**
1. Processar o item via `_apply_change_up` (ou função equivalente que invoca
   `board_obj.apply_commands(...)` com `resolve_board_fn`).

**Resultado esperado:**
- `resolve_board_fn` passado a `apply_commands` resolve corretamente o
  `board_id` da issue alvo via `_find_snapshot_issue` (retornando o primeiro
  elemento da tupla, ou `None` se não encontrada).
- O vínculo entre `board-a` e `board-b` é bloqueado (mesmo efeito de CT01,
  agora disparado pelo fluxo real de sincronização).
- Nenhuma regressão nos testes existentes de `_apply_change_up`.

## CT12 — Não regressão da suíte existente

**Tipo:** integração (execução de suíte)
**Critério de aceitação:** "Sem quebra de funcionalidades existentes" (issue #256)

**Pré-condição:**
- Suíte de testes completa do repositório.

**Passos:**
```bash
python -m pytest tests/ -k "sync_optimization or sanitize_relations or cross_board or config" -v
python -m pytest
```

**Resultado esperado:**
- Todos os testes pré-existentes continuam passando, inclusive
  `test_apply_commands_*` em `tests/test_sync_optimization.py` e os testes de
  `tests/test_sanitize_relations.py`.
- Os novos testes desta task (CT01–CT11) passam.

## Fora de escopo (não testar nesta task)

- Alterações em `_apply_create_down`, `_add_sub_issue` ou qualquer outro
  ponto de criação de relação pai/filho fora de `_apply_change_up`/
  `apply_commands` — não há hoje outro call site que crie relação nova a
  partir de decisão do core.
- Classificação de participação como `origin`/`authorized`/`propagated`/
  `unresolved` (stories #242/#244).
- Reprocessamento automático, após a reativação, de um vínculo que foi
  bloqueado durante a suspensão — a story define explicitamente que isso não
  deve ocorrer; nenhuma fila ou registro de "pendente de reenvio" deve ser
  testado aqui.
- Validação de `safety.cross_board_parent_links` em `check_config`/
  `validate_cross_board_parent_links`/`resolve_cross_board_parent_links` —
  já coberta em
  `doc/quality/integridade-de-issues-entre-boards/test-cases-adicionar-e-validar-chave-safety-cross-board-parent-links.md`
  (task #255).
