# Resultados de Teste — Implementar `list_participations` via GraphQL no GitHubBoardAdapter

Status: approved
Owner: quality
Last updated: 2026-08-28

## Inputs

- `doc/product/integridade-de-issues-entre-boards/casos-de-teste/248-casos-de-teste-github-adapter-list-participations.md`
- Issue #248 — Implementar `list_participations` via GraphQL no GitHubBoardAdapter

## CT01 — resolve `board_id`/`status` quando o project corresponde a um board configurado

**Resultado:** passed

**Observações:**
- `test_list_participations_resolve_board_id_e_status_quando_project_configurado` — PASSED.

## CT02 — `board_id=None`/`status=None` quando o project não corresponde a nenhum board configurado

**Resultado:** passed

**Observações:**
- `test_list_participations_board_id_e_status_none_quando_project_nao_configurado` — PASSED.

## CT03 — dois nodes (um resolvido, um não) — cenário exato do "Como testar" da issue

**Resultado:** passed

**Observações:**
- `test_list_participations_dois_items_um_resolvido_um_nao` — PASSED.

## CT04 — `archived` reflete `isArchived`, com default `False` quando ausente

**Resultado:** passed

**Observações:**
- `test_list_participations_archived_reflete_isarchived_com_default_false` — PASSED.

## CT05 — `projectItems` vazio devolve `[]` sem erro

**Resultado:** passed

**Observações:**
- `test_list_participations_projectitems_vazio_retorna_lista_vazia` — PASSED.

## CT06 — falha do `_gql` propaga (RN-B02)

**Resultado:** passed

**Observações:**
- `test_list_participations_falha_do_gql_propaga_excecao` — PASSED.
- Confirmado: não há try/except no método; a exceção do `_gql` propaga sem
  conversão para warning/lista vazia, divergindo deliberadamente do padrão
  legado de `_remove_propagated_items_without_status`.

## CT07 — consulta pelo `number` da issue, mesmo padrão de `_belongs_to_board`

**Resultado:** passed

**Observações:**
- `test_list_participations_consulta_por_number_com_owner_repo_split` — PASSED.

## CT08 — Não regressão da suíte existente

**Resultado:** passed

**Observações:**
- `python -m pytest tests/ -k "participation" -v` → 17 passed (7 novos de
  CT01–CT07 + 10 de `test_participation_integrity.py`, task #247).
- `python -m pytest tests/` (suíte completa) → 1200 passed, 28 skipped,
  1 xpassed, 21 failed. As 21 falhas são pré-existentes em
  `test_agent_log_descritivo.py` e `test_dockerfile.py`, sem relação com
  esta issue — mesma linha de base já registrada na etapa de Casos de
  Teste. Nenhuma regressão introduzida.

## Verificação de escopo

- Nenhuma dúvida ou ambiguidade encontrada nos casos de teste (CT01–CT08):
  descrição, procedimento e resultado esperado de cada CT batem exatamente
  com a implementação lida em `src/adapters/github_board.py`
  (`_PARTICIPATIONS_QUERY`, `list_participations`).
- Implementação não decide remoção nem classificação de intenção; não
  altera `_remove_propagated_items_without_status`; não conecta a chamada
  em `_add_sub_issue` — conforme escopo da issue.
- Nenhum código de produção ou caso de teste foi alterado nesta etapa
  (execução apenas).

## Resumo

- Total: 8
- Passou: 8
- Falhou: 0
- Bloqueado: 0
