# Casos de Teste — Implementar política pura `classify_participation` (origin/authorized/propagated/unresolved)

Status: draft
Owner: quality
Last updated: 2026-09-01

## Inputs
- Task #265 — Implementar política pura `classify_participation`
  (origin/authorized/propagated/unresolved)
- User Story #242 — Classificação de intenção de participação em board
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`
  (RN-B01, RN-B02, RN-B04, RN-B10)
- `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-001-intencao-explicita-e-gate-fail-closed.md`
- `src/core/participation_policy.py` (`authorized_boards`, `BOARD_INTENT_LABEL_PREFIX`
  — entregues por #264, consumidos diretamente por `classify_participation`)
- `src/core/board.py` (`SyncEvent(str, Enum)` — padrão seguido por
  `ParticipationClassification`)

Casos de teste detalhados (procedimento e resultado esperado por CT):
`doc/product/integridade-de-issues-entre-boards/casos-de-teste/265-casos-de-teste-implementar-classify-participation-policy.md`

## CT01 — Única participação confirmada no próprio board retorna ORIGIN

**Tipo:** unitário
**Critério de aceitação:** regra 2 ("Como testar", item 1 da issue #265)

**Pré-condição:**
- `board_id = "epic"`
- `labels = []`
- `known_participations` contém apenas uma entrada com `board_id="epic"`
  (o próprio board avaliado) — nenhuma outra entrada com `board_id` resolvido
  diferente de `"epic"`.
- `config = {"boards": {"epic": {}, "story": {}}}`

**Passos:**
1. Chamar `classify_participation("epic", labels, known_participations, config)`.

**Resultado esperado:**
- Retorno `ParticipationClassification.ORIGIN`.

## CT02 — Label de autorização sem qualquer outra participação retorna AUTHORIZED

**Tipo:** unitário
**Critério de aceitação:** regra 1 ("Como testar", item 2)

**Pré-condição:**
- `board_id = "story"`
- `labels = ["board-intent-story"]`
- `known_participations = []`
- `config = {"boards": {"epic": {}, "story": {}}}`

**Passos:**
1. Chamar `classify_participation("story", labels, [], config)`.

**Resultado esperado:**
- Retorno `ParticipationClassification.AUTHORIZED`.

## CT03 — Autorização tem prioridade sobre evidência de propagação

**Tipo:** unitário
**Critério de aceitação:** regra 1, prioridade sobre regra 3 ("Como testar",
item 3; ADR-001)

**Pré-condição:**
- `board_id = "story"`
- `labels = ["board-intent-story"]`
- `known_participations` contém uma entrada confirmada em outro board
  configurado (ex.: `board_id="epic"`, `status` preenchido).
- `config = {"boards": {"epic": {}, "story": {}}}`

**Passos:**
1. Chamar `classify_participation("story", labels, known_participations, config)`.

**Resultado esperado:**
- Retorno `ParticipationClassification.AUTHORIZED` (autorização explícita
  prevalece mesmo havendo evidência de propagação).

## CT04 — Participação em outro board configurado, sem autorização, com `status` preenchido retorna PROPAGATED

**Tipo:** unitário
**Critério de aceitação:** regra 3 ("Como testar", item 4; RN-B02)

**Pré-condição:**
- `board_id = "story"`
- `labels = []`
- `known_participations` contém uma entrada com `board_id="epic"` e `status`
  preenchido (ex.: `"Doing"`).
- `config = {"boards": {"epic": {}, "story": {}}}`

**Passos:**
1. Chamar `classify_participation("story", [], known_participations, config)`.

**Resultado esperado:**
- Retorno `ParticipationClassification.PROPAGATED`.

## CT05 — Mesmo cenário do CT04 sem `status` preenchido também retorna PROPAGATED

**Tipo:** unitário
**Critério de aceitação:** regra 3, independência de `Status` (RN-B02 —
"Como testar", item 5; critério de aceitação da story #242)

**Pré-condição:**
- Igual ao CT04, exceto `status=None` na participação em `"epic"`.

**Passos:**
1. Chamar `classify_participation("story", [], known_participations, config)`
   com a participação de `"epic"` tendo `status=None`.

**Resultado esperado:**
- Retorno `ParticipationClassification.PROPAGATED` — idêntico ao CT04,
  confirmando que `status` (preenchido ou vazio) não altera a classificação.

## CT06 — Participação apenas com `board_id=None` retorna UNRESOLVED (não ORIGIN)

**Tipo:** unitário
**Critério de aceitação:** regra 4 ("Como testar", item 6 — dado ambíguo não
pode ser tratado como "só este board" por omissão)

**Pré-condição:**
- `board_id = "story"`
- `labels = []`
- `known_participations` contém apenas uma entrada com `board_id=None`.
- `config = {"boards": {"epic": {}, "story": {}}}`

**Passos:**
1. Chamar `classify_participation("story", [], known_participations, config)`.

**Resultado esperado:**
- Retorno `ParticipationClassification.UNRESOLVED` (nunca `ORIGIN` por
  omissão quando o dado é ambíguo).

## CT07 — Participação em board removido de `config["boards"]` não conta como prova e retorna UNRESOLVED

**Tipo:** unitário
**Critério de aceitação:** regra 4 ("Como testar", item 7; RN-B02 — snapshot
de board não configurado não serve como prova)

**Pré-condição:**
- `board_id = "story"`
- `labels = []`
- `known_participations` contém uma entrada com `board_id="board-removido"`,
  que **não** está em `config["boards"]`.
- `config = {"boards": {"story": {}}}`

**Passos:**
1. Chamar `classify_participation("story", [], known_participations, config)`.

**Resultado esperado:**
- Retorno `ParticipationClassification.UNRESOLVED` (sem outra evidência,
  participação em board fora da config não autoriza `PROPAGATED` nem
  `ORIGIN`).

## CT08 — Determinismo: ordem de `known_participations` e de `config["boards"]` não altera o resultado

**Tipo:** unitário
**Critério de aceitação:** "A função deve ser determinística" ("Como
testar", item 8; requisito não funcional da issue)

**Pré-condição:**
- Um mesmo conjunto de `known_participations` (contendo ao menos uma
  participação comprovada em outro board configurado) e um mesmo
  `config["boards"]`.

**Passos:**
1. Chamar `classify_participation` com `known_participations` em uma ordem.
2. Chamar novamente com a lista embaralhada (ordem inversa) e com o dict de
   `config["boards"]` reconstruído com as chaves em ordem inversa.
3. Comparar os dois resultados.

**Resultado esperado:**
- Os dois resultados são idênticos, independentemente da ordem de
  `known_participations` ou das chaves de `config["boards"]`.

## CT09 — Regressão Story→Epic e Task→User Story (RN-B10): mesma bateria de casos com outros nomes de board

**Tipo:** unitário (parametrizado)
**Critério de aceitação:** RN-B10 ("Como testar", item 9)

**Pré-condição:**
- Os cenários de CT01, CT04, CT06 e CT07 reaplicados trocando apenas os
  valores de `board_id` avaliado e de `config["boards"]` para os pares
  `"epic"`/`"story"` e `"story"`/`"task"` (mantendo a mesma estrutura de
  `known_participations` e labels de cada cenário original).

**Passos:**
1. Parametrizar os testes de CT01/CT04/CT06/CT07 pelo par de boards.
2. Executar cada combinação.

**Resultado esperado:**
- Mesma classificação obtida em cada par de boards que no cenário original
  (ex.: par `"story"`/`"task"` reproduz o resultado do par `"story"`/`"epic"`
  original para o mesmo cenário lógico), confirmando que nenhuma lógica
  depende do nome ou nível hierárquico do board.

## CT10 — `ParticipationClassification` segue o padrão `str, Enum` com os quatro valores esperados

**Tipo:** unitário
**Critério de aceitação:** "Escopo técnico", item 1 da issue #265

**Pré-condição:** nenhuma.

**Passos:**
1. Inspecionar `ParticipationClassification`.

**Resultado esperado:**
- É subclasse de `(str, Enum)`, no mesmo padrão de `SyncEvent`
  (`src/core/board.py`).
- Contém exatamente os quatro membros com os valores string:
  `ORIGIN = "origin"`, `AUTHORIZED = "authorized"`,
  `PROPAGATED = "propagated"`, `UNRESOLVED = "unresolved"`.

## CT11 — Não regressão da suíte existente

**Tipo:** integração (execução de suíte)
**Critério de aceitação:** "Sem quebra de funcionalidades existentes"
(issue #265)

**Pré-condição:**
- Suíte de testes completa do repositório.

**Passos:**
```bash
python -m pytest tests/test_participation_policy.py -v
python -m pytest tests/ -v
```

**Resultado esperado:**
- Todos os testes pré-existentes (incluindo os de `authorized_boards`,
  entregues por #264, no mesmo arquivo) continuam passando; os novos testes
  de `classify_participation` passam a existir e, até a implementação ser
  feita, falham por ausência de `classify_participation`/
  `ParticipationClassification` (estado RED esperado nesta etapa).
