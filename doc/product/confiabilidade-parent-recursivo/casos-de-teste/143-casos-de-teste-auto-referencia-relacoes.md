# Casos de Teste — Validar auto-referência em relações parent/children/blocked_by/blocks

Issue: #143 — Validar auto-referência em relações parent/children/blocked_by/blocks
Épico: #104 / Story: #138 (US-01)
Etapa: Casos de Teste

## Contexto da verificação

A issue pede uma função pura `sanitize_relations(issue_id, cmds) ->
IssueCommands` em `src/core/commands.py`, chamada em dois pontos de
`src/core/sync.py` (`_apply_create_up`, `_apply_change_up`) e como defesa em
profundidade no início de `Board.apply_commands` (`src/core/board.py`), para
impedir que uma issue seja registrada como sua própria `parent`, `children`,
`blocked_by` ou `blocks` antes de qualquer chamada ao adapter do board.

**Estado no momento desta verificação:** `sanitize_relations` **não existe**
em `src/core/commands.py` na branch `epic` (confirmado por busca no
repositório). Esta é a etapa de Casos de Teste, que antecede a implementação;
os testes abaixo foram escritos test-first e devem falhar (`ImportError`)
até a implementação ser feita, e passar depois — sem alterações nesta task
além dos próprios testes.

Testes automatizados em `tests/test_sanitize_relations.py` (pytest). Este
documento é a versão legível/rastreável dos mesmos casos, mapeada aos
critérios de aceite da issue.

## CT01 — Remoção isolada da auto-referência por relação (AC1)

**Objetivo:** garantir que `sanitize_relations` remove a auto-referência de
cada uma das quatro relações, isoladamente e quando combinadas no mesmo
`IssueCommands`.

**Procedimento:** chamar `sanitize_relations("76", cmds)` com `cmds.parent =
"76"`; depois com `cmds.children = ["76"]`; depois com `cmds.blocked_by =
["76"]`; depois com `cmds.blocks = ["76"]`; por fim com as quatro
combinadas no mesmo objeto.

**Resultado esperado:** cada campo afetado fica vazio/`None` no resultado
(`parent is None`, listas vazias), inclusive quando as quatro relações
aparecem juntas.

**Testes:** `test_sanitize_removes_self_reference_from_parent`,
`test_sanitize_removes_self_reference_from_children`,
`test_sanitize_removes_self_reference_from_blocked_by`,
`test_sanitize_removes_self_reference_from_blocks`,
`test_sanitize_removes_self_reference_from_all_four_combined`.

---

## CT02 — Lista mista: só a auto-referência é descartada (AC2)

**Objetivo:** confirmar que, numa lista com múltiplos IDs, apenas o ID igual
a `issue_id` é removido — os demais permanecem, na ordem original.

**Procedimento:** `children=["76", "10"]`, `blocked_by=["10", "76", "20"]`,
`blocks=["76", "30"]` para `issue_id="76"`; e um caso sem nenhuma
auto-referência (todos os IDs válidos) para confirmar que nada é descartado
indevidamente.

**Resultado esperado:** `children == ["10"]`; `blocked_by == ["10", "20"]`;
`blocks == ["30"]`; no caso sem auto-referência, todos os valores
permanecem idênticos aos de entrada.

**Testes:** `test_sanitize_keeps_valid_ids_in_mixed_children_list`,
`test_sanitize_keeps_valid_ids_in_mixed_blocked_by_list`,
`test_sanitize_keeps_valid_ids_in_mixed_blocks_list`,
`test_sanitize_no_self_reference_is_noop_on_values`.

---

## CT03 — Normalização de tipo antes de comparar (AC3)

**Objetivo:** garantir que a comparação funciona independentemente de
`issue_id` e os IDs das relações serem fornecidos como `str` ou `int`.

**Procedimento:** combinar `issue_id` em `str`/`int` com relações contendo
IDs em `str`/`int` (`parent="76"` com `issue_id="76"` e com `issue_id=76`;
`children=[76, 10]` com `issue_id="76"`; `blocked_by=[76]` com `issue_id=76`).

**Resultado esperado:** a auto-referência é detectada e removida em todas as
combinações de tipo; IDs válidos remanescentes são normalizados para `str`
na saída (consistente com o restante do domínio, que trata IDs como `str`).

**Testes:** `test_sanitize_str_issue_id_str_relation_ids`,
`test_sanitize_int_issue_id_str_relation_ids`,
`test_sanitize_str_issue_id_int_relation_ids_in_children`,
`test_sanitize_int_issue_id_int_relation_id_in_blocked_by`.

---

## CT04 — Imutabilidade do objeto de entrada (AC4)

**Objetivo:** confirmar que `sanitize_relations` não muta o `IssueCommands`
recebido e retorna uma nova instância.

**Procedimento:** capturar os valores de `cmds` antes da chamada, invocar
`sanitize_relations`, e comparar `cmds` (entrada) com os valores capturados;
verificar `result is not cmds`; verificar que campos não relacionados a
relações (`labels`, `agent_level`, `close`, `reopen`, `archive`,
`need_human`) permanecem inalterados no resultado.

**Resultado esperado:** `cmds` original inalterado após a chamada; `result`
é uma instância distinta; campos não-relacionais preservados.

**Testes:** `test_sanitize_does_not_mutate_input_parent`,
`test_sanitize_does_not_mutate_input_lists`,
`test_sanitize_returns_new_instance`,
`test_sanitize_preserves_other_fields_unchanged`.

---

## CT05 — `log.warning` por auto-referência descartada (AC5)

**Objetivo:** garantir que cada auto-referência descartada gera exatamente
um `log.warning`, contendo a relação e o ID descartado; e que nenhum warning
é emitido quando não há auto-referência.

**Procedimento:** monkeypatch em `src.core.commands.log.warning`; chamar
`sanitize_relations` com as quatro relações apontando para o próprio
`issue_id` e contar as chamadas; inspecionar o conteúdo de uma chamada
isolada (`blocked_by=["76"]`); chamar com IDs válidos (sem auto-referência)
e confirmar ausência de warnings; confirmar via `inspect.signature` que a
função não recebe `board_id` (é pura).

**Resultado esperado:** 4 chamadas de warning para as 4 relações
combinadas (uma por relação afetada); a mensagem/extra contém a relação
(`blocked_by`) e o ID (`76`); zero chamadas quando não há auto-referência;
assinatura da função é `sanitize_relations(issue_id, cmds)`, sem `board_id`.

**Testes:** `test_sanitize_logs_warning_for_each_discarded_relation`,
`test_sanitize_logs_warning_contains_relation_name_and_id`,
`test_sanitize_no_warning_when_no_self_reference`,
`test_sanitize_pure_function_no_board_id_required`.

---

## CT06 — Integração com `Board.apply_commands` (AC6)

**Objetivo:** confirmar que a defesa em profundidade em `apply_commands`
impede que o adapter (`BoardPort`) receba uma auto-referência, mesmo que o
`IssueCommands` chegue não-sanitizado — inclusive quando o `known` (snapshot)
já estivesse corrompido com a mesma auto-referência.

**Procedimento:** usar um `FakePort` (mesmo padrão de
`tests/test_sync_optimization.py`) e chamar `Board.apply_commands("b", "76",
cmds, known=...)` com `cmds.parent`/`children`/`blocked_by`/`blocks`
contendo `"76"` (igual ao `issue_id`); verificar as chamadas registradas no
fake; repetir com `known={"parent": "76", ...}` para garantir que o valor
conhecido desatualizado não reintroduz a auto-referência; verificar que o
warning emitido a partir de `apply_commands` inclui `board_id`.

**Resultado esperado:** nenhuma chamada a `set_parent`/`set_children`/
`set_blocked_by`/`set_blocks` contém `"76"` como valor relacionado a si
mesma; IDs válidos remanescentes (ex.: `"10"` em `children=["76", "10"]`)
continuam sendo enviados; o log de `apply_commands` inclui `board_id`.

**Testes:** `test_apply_commands_blocks_self_reference_in_parent`,
`test_apply_commands_blocks_self_reference_in_children`,
`test_apply_commands_blocks_self_reference_in_blocked_by`,
`test_apply_commands_blocks_self_reference_in_blocks`,
`test_apply_commands_self_reference_not_reintroduced_via_stale_known`,
`test_apply_commands_logs_warning_with_board_id`.

---

## CT07 — Integração com `_apply_create_up` e `_apply_change_up` (AC7)

**Objetivo:** confirmar que os dois pontos de chamada em `sync.py` sanitizam
antes de qualquer chamada ao adapter.

**Procedimento:**
- `_apply_change_up`: montar um snapshot e um arquivo `-body.md` local com
  `/blocked_by #76, #10` para uma issue cujo `item.id` já é `"76"`; executar
  `sync._apply_change_up` com um `FakePort`; inspecionar as chamadas de
  `set_blocked_by`.
- `_apply_create_up`: montar um `-body.md` de uma issue ainda sem ID com
  `/blocked_by #76, #10`, usando um `FakePort` cujo `create_issue` retorna
  deliberadamente o ID `"76"` (simulando a coincidência entre o ID recém
  atribuído pelo board e uma referência já escrita no body); executar
  `sync._apply_create_up`; inspecionar as chamadas de `set_blocked_by`.

**Resultado esperado:** em ambos os fluxos, nenhuma chamada a
`set_blocked_by` contém `"76"`; o ID válido `"10"` continua presente na
chamada (quando ela ocorre).

**Testes:** `test_apply_change_up_self_reference_not_sent_to_adapter`,
`test_apply_create_up_self_reference_not_sent_to_adapter`.

---

## CT08 — Não regressão da suíte existente (AC8)

**Objetivo:** garantir que a implementação não quebra os testes já
existentes de `tests/test_sync_optimization.py` e demais arquivos de
`board.py`/`commands.py`/`sync.py`.

**Procedimento:**
```bash
python -m pytest tests/ -v
```

**Resultado esperado:** todos os testes pré-existentes continuam passando
após a implementação (comparar contagem de `passed`/`failed` antes e depois
da issue ser implementada).

**Status no momento desta verificação (antes da implementação):** suíte
completa executada — `tests/test_sanitize_relations.py` falha com
`ImportError` (esperado, pois `sanitize_relations` ainda não existe); os
778 testes restantes passam, 23 são skipped e há falhas/erros pré-existentes
e não relacionados a esta issue em `test_docker_compose.py` e
`test_dockerfile.py` (ambiente sem `.env`/Docker configurado neste
sandbox — não pertencem ao escopo desta task).

---

## Observação — documentação de referência ainda não mesclada em `epic`

A issue cita como documentação já aprovada (a não repetir aqui):
- `doc/requirements/confiabilidade-parent-recursivo/business-rules.md` (RN-001, RN-005)
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md` (ADR-02)

Nenhum dos dois caminhos existe ainda em `epic`/`main` (busca por
`confiabilidade-parent-recursivo` sem resultado em `doc/` nestas branches).
Ambos existem na branch `origin/epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026`
(ainda não mesclada) — não é um gap de conteúdo, apenas de merge pendente do
épico #104. Confirmado que o texto de ADR-02 e RN-001 nessa branch é
consistente com o que a issue #143 descreve (função pura
`sanitize_relations`, normalização para `str`, preservação de ids válidos em
listas mistas, warning por relação descartada, defesa em profundidade em
`Board.apply_commands`). Os casos de teste acima foram escritos com base no
texto da própria issue #143, que é autocontida, e validados cruzando com
ADR-02/RN-001 dessa branch pendente.

## Resultado da execução

7 dos 8 critérios de aceite (CT01–CT07) têm testes automatizados dedicados
em `tests/test_sanitize_relations.py`, escritos test-first e falhando por
`ImportError` no estado atual do código (esperado nesta etapa). O CT08
(não-regressão) foi verificado executando a suíte completa: sem regressões
atribuíveis a esta task; as falhas presentes são pré-existentes e fora do
escopo desta issue (Docker/`.env`).
