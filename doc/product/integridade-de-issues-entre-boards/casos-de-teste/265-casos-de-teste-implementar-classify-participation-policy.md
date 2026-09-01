# Casos de Teste — Implementar política pura `classify_participation` (origin/authorized/propagated/unresolved)

Issue: #265 — Implementar política pura `classify_participation`
(origin/authorized/propagated/unresolved)
Épico: #230 / Story: #242 — Classificação de intenção de participação em board
Etapa: Casos de Teste

## Contexto da verificação

A issue pede a função pura `classify_participation(board_id, labels,
known_participations, config) -> ParticipationClassification`, que classifica
a participação de uma issue em um board avaliado em um dos quatro estados
definidos em ADR-001: `origin`, `authorized`, `propagated` ou `unresolved`.
É a função central da story #242, consumida por todas as demais stories do
épico (#243, #244, #245) sem redefinição de regra.

Regras, em ordem de prioridade estrita (ADR-001, RN-B01, RN-B02, RN-B04,
RN-B10):

1. Autorização explícita (`board_id` em `authorized_boards(labels, config)`)
   tem prioridade sobre qualquer outra evidência → `AUTHORIZED`.
2. Nenhuma participação confirmada com `board_id` resolvido e diferente do
   avaliado → `ORIGIN`.
3. Ao menos uma participação com `board_id` resolvido, diferente do
   avaliado, presente em `config["boards"]` (exceto `platform`) → `PROPAGATED`,
   independentemente de `status` estar preenchido (RN-B02: `Status` nunca
   isenta a classificação).
4. Qualquer outro caso (participação apenas em board fora de
   `config["boards"]`, ou `board_id=None` sem outra evidência) → `UNRESOLVED`
   — nunca `ORIGIN` por omissão quando há dúvida.

A função deve ser determinística (independente de ordem de lista/dict) e não
recebe `parent` como parâmetro — só participações e labels, sem I/O de rede,
sem `BoardPort`/adapter.

**Estado no momento desta verificação:** `classify_participation` e
`ParticipationClassification` **não existem** em `src/core/participation_policy.py`
nesta branch (confirmado por busca em `src/` e `tests/`); apenas
`authorized_boards`/`BOARD_INTENT_LABEL_PREFIX` (entregues por #264) já
existem e são a base consumida por esta função. Esta é a etapa de Casos de
Teste, que antecede a implementação; os testes abaixo são escritos test-first
e devem falhar (`ImportError`/`AttributeError`) até a implementação ser
feita.

Testes automatizados adicionados a `tests/test_participation_policy.py`
(mesmo arquivo da task anterior desta story, conforme instruído na seção
"Como testar" da issue). Este documento é a versão legível/rastreável dos
mesmos casos.

Fora de escopo (não testado aqui, conforme a própria issue): `authorized_boards`
(já coberta por #264), consulta real a `list_participations`/GraphQL,
remoção de participação, persistência de `participation_intent` no snapshot
e o gate em `keep_task` (stories #243/#244/#245).

## CT01 — Única participação confirmada no próprio board → ORIGIN

**Objetivo:** confirmar que, sem nenhuma participação comprovada em outro
board, a participação no próprio `board_id` avaliado é tratada como origem.

**Procedimento:** chamar `classify_participation("epic", [], [participação
com board_id="epic"], {"boards": {"epic": {}, "story": {}}})`.

**Resultado esperado:** retorno `ParticipationClassification.ORIGIN`.

**Teste:** `test_single_confirmed_participation_in_evaluated_board_returns_origin`.

---

## CT02 — Label de autorização sem outra participação → AUTHORIZED

**Objetivo:** confirmar que a label `board-intent-<board_id>` concede
`AUTHORIZED` mesmo sem qualquer participação conhecida.

**Procedimento:** chamar `classify_participation("story",
["board-intent-story"], [], {"boards": {"epic": {}, "story": {}}})`.

**Resultado esperado:** retorno `ParticipationClassification.AUTHORIZED`.

**Teste:** `test_authorization_label_without_other_participation_returns_authorized`.

---

## CT03 — Autorização prevalece sobre evidência de propagação

**Objetivo:** garantir que, havendo autorização explícita, o resultado é
`AUTHORIZED` mesmo com participação confirmada em outro board configurado
(que isoladamente seria `PROPAGATED`).

**Procedimento:** chamar `classify_participation("story",
["board-intent-story"], [participação em board_id="epic", status
preenchido], {"boards": {"epic": {}, "story": {}}})`.

**Resultado esperado:** retorno `ParticipationClassification.AUTHORIZED`.

**Teste:** `test_authorization_takes_priority_over_propagation_evidence`.

---

## CT04 — Participação em outro board configurado, sem autorização, com `status` → PROPAGATED

**Objetivo:** confirmar a classificação `PROPAGATED` quando há prova de
participação confirmada em outro board presente em `config["boards"]`.

**Procedimento:** chamar `classify_participation("story", [], [participação
em board_id="epic", status="Doing"], {"boards": {"epic": {}, "story": {}}})`.

**Resultado esperado:** retorno `ParticipationClassification.PROPAGATED`.

**Teste:** `test_confirmed_participation_in_other_configured_board_with_status_returns_propagated`.

---

## CT05 — Mesmo cenário do CT04 sem `status` → PROPAGATED (RN-B02)

**Objetivo:** confirmar que `status` vazio na participação de outro board
não altera o resultado — `Status` nunca isenta a classificação.

**Procedimento:** repetir CT04 com `status=None` na participação de
`"epic"`.

**Resultado esperado:** retorno `ParticipationClassification.PROPAGATED`,
idêntico ao CT04.

**Teste:** `test_confirmed_participation_in_other_configured_board_without_status_returns_propagated`.

---

## CT06 — Participação apenas com `board_id=None` → UNRESOLVED

**Objetivo:** garantir que dado ambíguo (`board_id` não resolvido) nunca é
tratado como origem por omissão.

**Procedimento:** chamar `classify_participation("story", [], [participação
com board_id=None], {"boards": {"epic": {}, "story": {}}})`.

**Resultado esperado:** retorno `ParticipationClassification.UNRESOLVED`.

**Teste:** `test_participation_with_unresolved_board_id_returns_unresolved`.

---

## CT07 — Participação em board removido de `config["boards"]` → UNRESOLVED

**Objetivo:** confirmar que participação em um board que não está mais
configurado não serve como prova de propagação (RN-B02).

**Procedimento:** chamar `classify_participation("story", [], [participação
com board_id="board-removido"], {"boards": {"story": {}}})` — `"board-removido"`
ausente de `config["boards"]`.

**Resultado esperado:** retorno `ParticipationClassification.UNRESOLVED`.

**Teste:** `test_participation_in_board_removed_from_config_returns_unresolved`.

---

## CT08 — Determinismo por ordem de `known_participations` e de `config["boards"]`

**Objetivo:** garantir que o resultado não depende da ordem de avaliação da
lista de participações nem das chaves do dict de boards.

**Procedimento:** chamar `classify_participation` com um mesmo cenário de
propagação, uma vez com `known_participations` e `config["boards"]` em uma
ordem, e outra vez com a lista embaralhada e o dict reconstruído com chaves
invertidas; comparar os resultados.

**Resultado esperado:** os dois resultados são idênticos.

**Teste:** `test_result_is_deterministic_regardless_of_input_order`.

---

## CT09 — Regressão Story→Epic e Task→User Story (RN-B10)

**Objetivo:** confirmar que a lógica não depende do nome/nível hierárquico
do board, reproduzindo os cenários de CT01/CT04/CT06/CT07 com os pares
`epic`/`story` e `story`/`task`.

**Procedimento:** parametrizar os testes correspondentes trocando apenas
`board_id` avaliado e as chaves de `config["boards"]` pelos pares indicados,
mantendo a mesma estrutura lógica de cada cenário.

**Resultado esperado:** mesma classificação obtida em cada par de boards,
para o mesmo cenário lógico.

**Teste:** `test_classification_is_independent_of_board_name_or_hierarchy_level`
(parametrizado).

---

## CT10 — `ParticipationClassification` segue o padrão `str, Enum` com os quatro valores

**Objetivo:** confirmar a forma do enum conforme "Escopo técnico" da issue.

**Procedimento:** inspecionar `ParticipationClassification` e seus membros.

**Resultado esperado:** subclasse de `(str, Enum)`; membros
`ORIGIN="origin"`, `AUTHORIZED="authorized"`, `PROPAGATED="propagated"`,
`UNRESOLVED="unresolved"`.

**Teste:** `test_participation_classification_enum_matches_expected_values`.

---

## CT11 — Não regressão da suíte existente (Critério de aceite: "Sem quebra de funcionalidades existentes")

**Objetivo:** garantir que a adição de `classify_participation` não quebra
os testes já existentes, incluindo os de `authorized_boards` (#264) no mesmo
arquivo.

**Procedimento:**
```bash
python -m pytest tests/test_participation_policy.py -v
python -m pytest tests/ -v
```

**Resultado esperado:** todos os testes pré-existentes continuam passando
após a implementação (comparar contagem de `passed`/`failed` antes e depois
da issue ser implementada).

**Status no momento desta verificação (antes da implementação):** os novos
testes de `classify_participation` falham em coleta/execução
(`ImportError`/`AttributeError` — símbolo ainda não existe em
`src/core/participation_policy.py`), esperado nesta etapa; os testes
pré-existentes de `authorized_boards` no mesmo arquivo continuam passando
normalmente. Nenhum arquivo de produção foi tocado por esta task, apenas o
arquivo de teste e a documentação.

---

## Resultado da execução

11 casos de teste (CT01–CT11) cobrem integralmente os 9 cenários descritos na
seção "Como testar" da issue #265 (origin, autorização sem outra evidência,
autorização com prioridade sobre propagação, propagação com e sem `status`,
`board_id` não resolvido, board removido da config, determinismo por ordem,
regressão epic→story/story→task), acrescidos da verificação de forma do enum
e de não-regressão. Todos escritos test-first em
`tests/test_participation_policy.py`, falhando no estado atual do código
(esperado nesta etapa) sem afetar os testes pré-existentes de
`authorized_boards`. Nenhum teste cobre consulta real a `list_participations`,
persistência de `participation_intent` no snapshot ou o gate em `keep_task`
— explicitamente fora de escopo desta issue.
