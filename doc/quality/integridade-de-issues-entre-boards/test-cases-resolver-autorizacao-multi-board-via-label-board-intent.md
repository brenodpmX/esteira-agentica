# Casos de Teste — Resolver autorização multi-board via label `board-intent-<board_id>`

Status: draft
Owner: quality
Last updated: 2026-08-28

## Inputs
- Task #264 — Resolver autorização multi-board via label `board-intent-<board_id>`
- User Story #242 — Classificação de intenção de participação em board
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md` (RN-B04)
- `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-001-intencao-explicita-e-gate-fail-closed.md`
- `src/core/commands.py` (`AGENT_HUB_PREFIX`, padrão de prefixo de label)

Casos de teste detalhados (procedimento e resultado esperado por CT):
`doc/product/integridade-de-issues-entre-boards/casos-de-teste/264-casos-de-teste-resolver-autorizacao-multi-board-via-label-board-intent.md`

## CT01 — Label com sufixo correspondente a board configurado autoriza

**Tipo:** unitário
**Critério de aceitação:** AC1 (issue #264, seção "Escopo técnico")

**Pré-condição:**
- `config = {"boards": {"epic": {}, "story": {}}}`

**Passos:**
1. Chamar `authorized_boards(["board-intent-epic"], config)`.

**Resultado esperado:**
- Retorno `{"epic"}`.
- `BOARD_INTENT_LABEL_PREFIX == "board-intent-"`.

## CT02 — Sufixo sem board configurado é ignorado e gera warning

**Tipo:** unitário
**Critério de aceitação:** AC2 (issue #264)

**Pré-condição:**
- `config = {"boards": {"epic": {}}}`

**Passos:**
1. Monkeypatch em `log.warning`.
2. Chamar `authorized_boards(["board-intent-inexistente"], config)`.

**Resultado esperado:**
- Retorno `set()`.
- `log.warning` chamado, mencionando a label e o sufixo não configurado.

## CT03 — Sufixo `platform` nunca é um board válido

**Tipo:** unitário
**Critério de aceitação:** AC3 (issue #264 — exclusão explícita de `platform`)

**Pré-condição:**
- `config = {"boards": {"platform": {"name": "github"}, "epic": {}}}`

**Passos:**
1. Chamar `authorized_boards(["board-intent-platform"], config)`.

**Resultado esperado:**
- Retorno `set()`, mesmo com `platform` presente como chave em `boards`.
- `log.warning` chamado.

## CT04 — Labels sem o prefixo são ignoradas silenciosamente

**Tipo:** unitário
**Critério de aceitação:** AC4 (issue #264)

**Pré-condição:**
- `config = {"boards": {"epic": {}}}`

**Passos:**
1. Chamar `authorized_boards(["backend", "agent-hub-high"], config)`.

**Resultado esperado:**
- Retorno `set()`.
- Nenhuma chamada a `log.warning`.

## CT05 — Múltiplas autorizações simultâneas e mistura de labels

**Tipo:** unitário
**Critério de aceitação:** AC5 (issue #264)

**Pré-condição:**
- `config = {"boards": {"epic": {}, "story": {}}}`

**Passos:**
1. Chamar `authorized_boards(["board-intent-epic", "board-intent-story"], config)`.
2. Chamar `authorized_boards(["backend", "board-intent-epic", "board-intent-inexistente", "agent-hub-high", "board-intent-story"], config)`.

**Resultado esperado:**
- Ambas as chamadas retornam `{"epic", "story"}`.
- A segunda chamada gera exatamente 1 warning (referente só à label inválida).

## CT06 — Lista de labels vazia

**Tipo:** unitário
**Critério de aceitação:** AC6 (issue #264 — "Como testar")

**Pré-condição:**
- `config = {"boards": {"epic": {}}}`

**Passos:**
1. Chamar `authorized_boards([], config)`.

**Resultado esperado:**
- Retorno `set()`.

## CT07 — Determinismo independente da ordem das labels

**Tipo:** unitário
**Critério de aceitação:** AC7 (issue #264 — "Como testar")

**Pré-condição:**
- `config = {"boards": {"epic": {}, "story": {}, "task": {}}}`

**Passos:**
1. Chamar `authorized_boards` com uma lista de labels e novamente com a
   mesma lista em ordem invertida (incluindo variante com label inválida
   misturada).
2. Comparar os dois conjuntos retornados.

**Resultado esperado:**
- Os conjuntos retornados são idênticos, independentemente da ordem de
  entrada.

## CT08 — Ausência de I/O e de mutação de entrada

**Tipo:** unitário
**Critério de aceitação:** Requisito não-funcional da issue ("função pura", "não faz I/O de rede")

**Pré-condição:**
- `labels` e `config` com cópias capturadas antes da chamada.

**Passos:**
1. Chamar `authorized_boards(labels, config)`.
2. Comparar `labels`/`config` com as cópias capturadas.

**Resultado esperado:**
- `labels` e `config` permanecem inalterados após a chamada.

## CT09 — Não regressão da suíte existente

**Tipo:** integração (execução de suíte)
**Critério de aceitação:** "Sem quebra de funcionalidades existentes" (issue #264)

**Pré-condição:**
- Suíte de testes completa do repositório.

**Passos:**
```bash
python -m pytest tests/test_participation_policy.py -v
python -m pytest tests/ -v
```

**Resultado esperado:**
- Todos os testes pré-existentes continuam passando (mesma contagem de
  `passed`/`failed` antes e depois da implementação, exceto o novo arquivo
  de teste passando a existir/passar).
