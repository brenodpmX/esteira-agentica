# Casos de Teste — Resolver autorização multi-board via label `board-intent-<board_id>`

Issue: #264 — Resolver autorização multi-board via label `board-intent-<board_id>`
Épico: #230 / Story: #242 — Classificação de intenção de participação em board
Etapa: Casos de Teste

## Contexto da verificação

A issue pede a função pura `authorized_boards(labels: list[str], config: dict)
-> set[str]`, que resolve — a partir das labels de uma issue e dos boards
configurados no `pipe.yml` — o conjunto de `board_id`s para os quais existe
autorização explícita de participação multi-board (RN-B04, ADR-001). A label
reservada segue o padrão `board-intent-<board_id>`, no mesmo espírito de
`agent-hub-<valor>` (`AGENT_HUB_PREFIX`, `src/core/commands.py`), mas com
sufixo restrito: só é válido quando corresponde exatamente a uma chave de
`config["boards"]`, excluindo `platform` (que não é um board).

Escopo técnico da issue, em `src/core/participation_policy.py`:

1. constante `BOARD_INTENT_LABEL_PREFIX = "board-intent-"`;
2. função `authorized_boards(labels, config)` que itera `labels`, extrai o
   sufixo de cada label com o prefixo `board-intent-`, e adiciona ao
   resultado apenas os sufixos presentes em
   `set(config.get("boards", {}).keys()) - {"platform"}`; sufixo não
   correspondente é ignorado e gera `log.warning`; labels sem o prefixo são
   ignoradas silenciosamente; não faz I/O.

**Estado no momento desta verificação:** `src/core/participation_policy.py`,
`authorized_boards` e `BOARD_INTENT_LABEL_PREFIX` **não existem** no
repositório (confirmado por busca em `src/`) na branch `epic`. Esta é a etapa
de Casos de Teste, que antecede a implementação; os testes abaixo foram
escritos test-first e devem falhar (`ImportError`) até a implementação ser
feita, e passar depois — sem alterações nesta task além dos próprios testes.

Testes automatizados em `tests/test_participation_policy.py` (pytest). Este
documento é a versão legível/rastreável dos mesmos casos, mapeada aos
cenários descritos na seção "Como testar" da issue.

Fora de escopo (não testado aqui, conforme a própria issue): a política de
classificação completa (`origin`/`authorized`/`propagated`/`unresolved`),
leitura de labels reais de uma issue via API (a função recebe
`labels: list[str]` já carregada) e persistência/cache do resultado no
snapshot.

## CT01 — Label com sufixo correspondente a board configurado autoriza (AC1)

**Objetivo:** confirmar que uma label `board-intent-<board_id>` cujo sufixo
corresponde a uma chave de `config["boards"]` resulta na autorização daquele
board, e que a constante de prefixo tem o valor esperado.

**Procedimento:** chamar `authorized_boards(["board-intent-epic"],
{"boards": {"epic": {}, "story": {}}})`; verificar o valor de
`BOARD_INTENT_LABEL_PREFIX`.

**Resultado esperado:** retorno `{"epic"}`; `BOARD_INTENT_LABEL_PREFIX ==
"board-intent-"`.

**Testes:** `test_single_label_matching_board_authorizes_it`,
`test_prefix_constant_matches_expected_value`.

---

## CT02 — Sufixo sem board configurado é ignorado e gera warning (AC2)

**Objetivo:** garantir que uma label com sufixo que não corresponde a nenhum
board configurado não concede autorização e emite exatamente um
`log.warning` identificando a label e o board ausente.

**Procedimento:** monkeypatch em
`src.core.participation_policy.log.warning`; chamar
`authorized_boards(["board-intent-inexistente"], {"boards": {"epic": {}}})`;
inspecionar a chamada de warning registrada.

**Resultado esperado:** retorno `set()`; `log.warning` chamado; o conteúdo da
chamada menciona a label completa (`board-intent-inexistente`) e o sufixo
não configurado (`inexistente`).

**Testes:** `test_label_with_unconfigured_board_suffix_is_ignored`,
`test_label_with_unconfigured_board_suffix_warning_mentions_label_and_board`.

---

## CT03 — Sufixo `platform` nunca é um board válido (AC3)

**Objetivo:** confirmar que a chave `platform`, mesmo presente no dict de
`config["boards"]` (como no `pipe.yml` real), nunca é aceita como board
autorizável.

**Procedimento:** chamar `authorized_boards(["board-intent-platform"],
{"boards": {"platform": {"name": "github"}, "epic": {}}})` com
`log.warning` monkeypatched.

**Resultado esperado:** retorno `set()`; `log.warning` chamado (mesmo
tratamento de sufixo não configurado).

**Teste:** `test_platform_suffix_never_authorizes_even_if_key_present`.

---

## CT04 — Labels sem o prefixo são ignoradas silenciosamente (AC4)

**Objetivo:** garantir que labels sem o prefixo `board-intent-` (incluindo
outras labels especiais, como `agent-hub-*`) não afetam o resultado e não
geram warning.

**Procedimento:** chamar `authorized_boards(["backend", "agent-hub-high"],
{"boards": {"epic": {}}})` com `log.warning` monkeypatched.

**Resultado esperado:** retorno `set()`; nenhuma chamada a `log.warning`.

**Teste:** `test_labels_without_prefix_are_ignored_without_warning`.

---

## CT05 — Múltiplas autorizações simultâneas e mistura de labels válidas/invalidas/irrelevantes (AC5)

**Objetivo:** confirmar que múltiplas labels `board-intent-*` válidas
autorizam múltiplos boards ao mesmo tempo, inclusive quando misturadas com
labels sem o prefixo e com uma label de sufixo inválido no mesmo conjunto.

**Procedimento:** chamar `authorized_boards(["board-intent-epic",
"board-intent-story"], {"boards": {"epic": {}, "story": {}}})`; chamar
`authorized_boards(["backend", "board-intent-epic",
"board-intent-inexistente", "agent-hub-high", "board-intent-story"],
{"boards": {"epic": {}, "story": {}}})` com `log.warning` monkeypatched.

**Resultado esperado:** primeiro caso retorna `{"epic", "story"}`; segundo
caso também retorna `{"epic", "story"}`, com exatamente uma chamada de
warning (referente apenas a `board-intent-inexistente`).

**Testes:** `test_multiple_matching_labels_authorize_multiple_boards`,
`test_mix_of_valid_invalid_and_unrelated_labels`.

---

## CT06 — Lista de labels vazia (AC6)

**Objetivo:** confirmar o caso trivial de nenhuma label.

**Procedimento:** chamar `authorized_boards([], {"boards": {"epic": {}}})`.

**Resultado esperado:** retorno `set()`.

**Teste:** `test_empty_labels_returns_empty_set`.

---

## CT07 — Determinismo independente da ordem das labels (AC7)

**Objetivo:** garantir que o resultado não depende da ordem de `labels` na
entrada, tanto no caso totalmente válido quanto misturando labels válidas,
inválidas e irrelevantes.

**Procedimento:** chamar `authorized_boards` duas vezes com a mesma lista de
labels em ordens invertidas — uma vez só com labels válidas
(`board-intent-epic`, `board-intent-story`, `board-intent-task`), outra
misturando `board-intent-inexistente`, `backend` e labels válidas — e
comparar os dois conjuntos retornados.

**Resultado esperado:** os dois conjuntos retornados são idênticos em ambos
os casos (`{"epic", "story", "task"}` e `{"epic", "story"}`,
respectivamente), independentemente da ordem de entrada.

**Testes:** `test_result_is_order_independent`,
`test_result_is_order_independent_with_mixed_valid_and_invalid`.

---

## CT08 — Ausência de I/O e de mutação de entrada

**Objetivo:** confirmar que a função é pura: não faz I/O de rede e não muta
`labels` nem `config` recebidos.

**Procedimento:** capturar cópias de `labels` e `config` antes da chamada;
invocar `authorized_boards`; comparar com as cópias capturadas.

**Resultado esperado:** `labels` e `config` permanecem idênticos aos valores
originais após a chamada.

**Teste:** `test_does_not_mutate_input_labels_or_config`.

---

## CT09 — Não regressão da suíte existente (Critério de aceite: "Sem quebra de funcionalidades existentes")

**Objetivo:** garantir que a adição de `participation_policy.py` não quebra
os testes já existentes.

**Procedimento:**
```bash
python -m pytest tests/test_participation_policy.py -v
python -m pytest tests/ -v
```

**Resultado esperado:** todos os testes pré-existentes continuam passando
após a implementação (comparar contagem de `passed`/`failed` antes e depois
da issue ser implementada).

**Status no momento desta verificação (antes da implementação):**
`tests/test_participation_policy.py` falha em coleta (`ImportError: No
module named 'src.core.participation_policy'`) — esperado nesta etapa,
confirmado por execução real. A suíte completa
(`python -m pytest tests/ --ignore=tests/test_participation_policy.py`) foi
executada antes desta adição: 1255 passed, 29 skipped, 1 xpassed, 21 failed —
as 21 falhas são pré-existentes e não relacionadas a esta issue
(`test_agent_log_descritivo.py` e `test_dockerfile.py`); nenhum arquivo de
produção foi tocado por esta task, apenas o arquivo novo de teste e a
documentação.

---

## Resultado da execução

9 casos de teste (CT01–CT09), somando 12 testes automatizados, cobrem
integralmente os 7 cenários descritos na seção "Como testar" da issue #264
(match, sufixo inválido com warning, `platform` sempre inválido, ausência de
prefixo, múltiplas autorizações, lista vazia, determinismo por ordem),
acrescidos de verificações de pureza (ausência de mutação/I/O) e de
não-regressão. Todos escritos test-first em
`tests/test_participation_policy.py`, falhando por `ImportError` no estado
atual do código (esperado nesta etapa). Nenhum teste cobre a política de
classificação completa, leitura de labels via API ou persistência no
snapshot — explicitamente fora de escopo desta issue.
