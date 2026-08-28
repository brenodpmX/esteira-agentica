# Casos de Teste — Implementar `list_participations` via GraphQL no GitHubBoardAdapter

Issue: #248 — Implementar `list_participations` via GraphQL no GitHubBoardAdapter
Épico: #230 / Story: #243 — Reconciliação imediata após vínculo pai/filho
Etapa: Casos de Teste

## Contexto da verificação

A issue pede, exclusivamente em `src/adapters/github_board.py`:

1. uma nova query GraphQL (seguindo o padrão de `_PROPAGATED_ITEMS_QUERY` e
   `_BELONGS_QUERY` já existentes), trazendo por item de `projectItems`:
   `id` (item_id), `project.id` (project_id), `isArchived` e o valor do
   campo `Status` (via `fieldValues`/`ProjectV2ItemFieldSingleSelectValue`);
2. `list_participations(self, issue_id: str) -> list[Participation]`, que
   consulta pelo `number` da issue (mesmo padrão de `_belongs_to_board`,
   usando `self._repo.split("/")`) e monta uma `Participation` (de
   `src.core.board`) por node, com `board_id` resolvido via `self._projects`
   (mesmo mapeamento de `_board_meta`/`_belongs_to_board`) ou `None` quando o
   `project.id` não corresponder a nenhum board configurado, `status` = nome
   da opção do campo `Status` (ou `None` se vazio) e `archived` = `isArchived`
   (ou `False` se ausente).
3. divergência deliberada do padrão legado de
   `_remove_propagated_items_without_status`: falha do `_gql` **propaga** —
   não é capturada, não loga apenas warning, não retorna lista vazia (RN-B02:
   ausência de prova não pode parecer "sem participações").

**Estado no momento desta verificação:** o contrato `Participation` e o
default de `BoardPort.list_participations`/`Board.list_participations` já
existem em `src/core/board.py` (task #247, mergeada em `epic`). Confirmado
por leitura de `src/adapters/github_board.py` na branch de trabalho desta
task (`feature248-...`, criada a partir de `origin/epic`): a classe
`GitHubBoardAdapter` **não** sobrescreve `list_participations` — não há
`_PARTICIPATIONS_QUERY` nem qualquer ocorrência de `list_participations` no
arquivo. Esta é a etapa de Casos de Teste, que antecede a implementação; os
testes abaixo foram escritos test-first e devem falhar (via `AttributeError`
ao tentar sobrescrever comportamento, ou por exercitar o default herdado de
`BoardPort` que retorna `[]`/loga warning em vez do comportamento GraphQL
descrito) até a implementação ser feita, e passar depois — sem alterações
nesta task além dos próprios testes.

Segue o mesmo padrão de mock de `_gql` (sem tocar rede, `_gh`/`_api`
proibidos no caminho produtivo) já usado em
`tests/test_sub_issue_propagation_fix.py` para
`_remove_propagated_items_without_status`.

Fora de escopo (não testado aqui, conforme a própria issue): decisão de
remoção/classificação de intenção, qualquer alteração de
`_remove_propagated_items_without_status`, e qualquer chamada a
`list_participations` a partir de `_add_sub_issue` ou outro fluxo (ambos
ficam para tasks seguintes).

## CT01 — `list_participations` resolve `board_id`/`status` quando o project corresponde a um board configurado

**Objetivo:** confirmar que, para um node de `projectItems` cujo `project.id`
corresponde a um board presente em `self._projects`, `list_participations`
devolve uma `Participation` com `board_id` resolvido para a chave do board e
`status` igual ao nome da opção do campo `Status`.

**Procedimento:** instanciar `GitHubBoardAdapter` com `_repo="owner/repo"` e
`_projects={"backlog": {"project_id": "PVT_1", ...}}`; mockar `_gql` para
devolver um `projectItems.nodes` com um item `id="PVTI_1"`,
`project.id="PVT_1"`, `isArchived=False`, `fieldValues` contendo
`Status="Doing"`; chamar `adapter.list_participations("76")`.

**Resultado esperado:** a lista retornada tem exatamente 1 `Participation`
com `item_id="PVTI_1"`, `project_id="PVT_1"`, `board_id="backlog"`,
`status="Doing"`, `archived=False`; a query é enviada com `number=76`
(inteiro, mesmo padrão de `_belongs_to_board`).

**Teste:** `test_list_participations_resolve_board_id_e_status_quando_project_configurado`.

---

## CT02 — `list_participations` devolve `board_id=None` e `status=None` quando o project não corresponde a nenhum board configurado

**Objetivo:** confirmar que um node cujo `project.id` não bate com nenhum
board em `self._projects` gera uma `Participation` com `board_id=None`, e
que a ausência do campo `Status` nos `fieldValues` resulta em `status=None`
(não `""`).

**Procedimento:** mockar `_gql` devolvendo um node com `project.id`
diferente de todos os `project_id` configurados em `self._projects` e sem
nenhum `fieldValues` de `Status`; chamar `list_participations`.

**Resultado esperado:** a `Participation` correspondente tem `board_id is
None` e `status is None`.

**Teste:** `test_list_participations_board_id_e_status_none_quando_project_nao_configurado`.

---

## CT03 — `list_participations` com dois nodes (um resolvido, um não) — cenário exato do "Como testar" da issue

**Objetivo:** reproduzir literalmente o cenário descrito na seção "Como
testar" da issue: dois `projectItems`, um cujo `project.id` corresponde a um
board configurado (com `Status="Doing"`) e outro cujo `project.id` não
corresponde a nenhum board configurado (sem `Status`).

**Procedimento:** mockar `_gql` devolvendo os dois nodes descritos acima;
chamar `adapter.list_participations("76")`.

**Resultado esperado:** a lista retornada tem exatamente 2
`Participation`; a do project configurado tem `board_id` resolvido para o
board correspondente e `status="Doing"`; a do project não configurado tem
`board_id=None` e `status=None`.

**Teste:** `test_list_participations_dois_items_um_resolvido_um_nao`.

---

## CT04 — `archived` reflete `isArchived` do node, com default `False` quando ausente

**Objetivo:** confirmar que `archived` é lido de `isArchived` quando
presente, e assume `False` quando o campo estiver ausente do node (mesmo
padrão de "ou `False` se ausente" descrito na issue).

**Procedimento:** mockar `_gql` devolvendo dois nodes: um com
`isArchived=True` e outro sem a chave `isArchived` no dict.

**Resultado esperado:** a `Participation` do primeiro node tem
`archived=True`; a do segundo tem `archived=False`.

**Teste:** `test_list_participations_archived_reflete_isarchived_com_default_false`.

---

## CT05 — `list_participations` com `projectItems` vazio devolve `[]` sem erro

**Objetivo:** confirmar o terceiro cenário da seção "Como testar": lista
vazia de `projectItems` não é tratada como erro.

**Procedimento:** mockar `_gql` devolvendo `projectItems.nodes = []`; chamar
`adapter.list_participations("76")`.

**Resultado esperado:** retorno `== []`; nenhuma exceção levantada.

**Teste:** `test_list_participations_projectitems_vazio_retorna_lista_vazia`.

---

## CT06 — falha do `_gql` propaga (não é capturada, não retorna `[]`, não apenas loga warning)

**Objetivo:** confirmar a divergência deliberada do padrão legado de
`_remove_propagated_items_without_status`: uma exceção levantada por `_gql`
deve propagar através de `list_participations`, sem try/except que a
converta em warning + lista vazia. Cobre RN-B02 (ausência de prova não pode
resultar em "sem participações" silencioso).

**Procedimento:** mockar `_gql` para levantar uma exceção (`RuntimeError`);
chamar `adapter.list_participations("76")` dentro de
`pytest.raises(RuntimeError)`.

**Resultado esperado:** a exceção propaga até o chamador; nenhum valor é
retornado; nenhum warning substitui a propagação (diferente do padrão de
`_remove_propagated_items_without_status`, que loga e retorna).

**Teste:** `test_list_participations_falha_do_gql_propaga_excecao`.

---

## CT07 — `list_participations` consulta pelo `number` da issue, no mesmo padrão de `_belongs_to_board`

**Objetivo:** confirmar que a consulta usa `owner`/`repo` extraídos de
`self._repo.split("/")` e `number=int(issue_id)`, mesmo padrão de
`_belongs_to_board`/`_remove_propagated_items_without_status`.

**Procedimento:** mockar `_gql` para capturar `query` e `variables`
recebidos; chamar `adapter.list_participations("76")` com
`_repo="owner/repo"`.

**Resultado esperado:** `_gql` é chamado com `owner="owner"`, `repo="repo"`,
`number=76` (inteiro); a string da query contém `projectItems`, `isArchived`
e `ProjectV2ItemFieldSingleSelectValue` (confirma que a query nova traz os
campos exigidos pela issue).

**Teste:** `test_list_participations_consulta_por_number_com_owner_repo_split`.

---

## CT08 — Não regressão da suíte existente (Critério de aceite: "Sem quebra de funcionalidades existentes")

**Objetivo:** garantir que a implementação de `list_participations` no
adapter não quebra `_remove_propagated_items_without_status`,
`_belongs_to_board` nem os demais testes já existentes do adapter e do core.

**Procedimento:**
```bash
python -m pytest tests/ -k "participation" -v
python -m pytest tests/ -v
```

**Resultado esperado:** todos os testes pré-existentes continuam passando
após a implementação; nenhum teste de `test_sub_issue_propagation_fix.py`
ou `test_participation_integrity.py` (task #247) é afetado.

**Status no momento desta verificação (antes da implementação):** os testes
novos de CT01–CT07, escritos test-first em
`tests/test_github_adapter_list_participations.py`, falham no estado atual
do código porque `GitHubBoardAdapter` ainda não sobrescreve
`list_participations` — os mocks de `_gql` não são exercitados (o default
herdado de `BoardPort` responde antes, retornando `[]`/logando warning em
vez do comportamento GraphQL esperado), confirmado por execução real. A
suíte completa (`python -m pytest tests/`) permanece com a mesma linha de
base já registrada na etapa de Casos de Teste da #247 (1193 passed, 28
skipped, 1 xpassed, 21 failed pré-existentes, não relacionadas a esta
issue) mais as falhas esperadas dos novos testes desta task.

---

## Resultado da execução

8 casos de teste (CT01–CT08) cobrem a query GraphQL nova (campos exigidos:
`id`, `project.id`, `isArchived`, `Status`), a resolução de `board_id` via
`self._projects` (resolvido/`None`), o default de `status`/`archived`
quando ausentes, os três cenários da seção "Como testar" da issue (dois
items resolvido/não-resolvido, exceção propagada, lista vazia) e o padrão
de consulta por `number`/`owner`/`repo`. Todos escritos test-first em
`tests/test_github_adapter_list_participations.py`, falhando no estado
atual do código (esperado nesta etapa, pois o adapter ainda usa o default
herdado de `BoardPort`). Nenhum teste cobre decisão de remoção,
classificação de intenção ou chamadas a partir de `_add_sub_issue` —
explicitamente fora de escopo desta issue.
