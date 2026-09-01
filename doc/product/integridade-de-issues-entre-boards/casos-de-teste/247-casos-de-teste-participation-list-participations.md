# Casos de Teste — Adicionar modelo `Participation` e contrato `list_participations` ao BoardPort

Issue: #247 — Adicionar modelo `Participation` e contrato `list_participations` ao BoardPort
Épico: #230 / Story: #243 — Reconciliação imediata após vínculo pai/filho
Etapa: Casos de Teste

## Contexto da verificação

A issue pede, exclusivamente em `src/core/board.py`:

1. um novo `@dataclass Participation` (campos: `board_id`, `item_id`,
   `project_id`, `status`, `archived=False`);
2. um método opcional `list_participations(issue_id)` em `BoardPort`, seguindo
   o padrão já existente de operações opcionais (default no-op com
   `log.warning` e retorno de lista vazia — mesmo padrão de
   `remove_from_board`, `reopen_issue`, `set_labels` etc.);
3. um método de delegação pura `Board.list_participations(issue_id)`, que
   apenas repassa a chamada a `self._port.list_participations(issue_id)` —
   mesmo padrão de `Board.connect`/`Board.check_access`.

**Estado no momento desta verificação:** `Participation` e
`list_participations` **não existem** em `src/core/board.py` na branch
`epic` (confirmado por leitura do arquivo). Esta é a etapa de Casos de Teste,
que antecede a implementação; os testes abaixo foram escritos test-first e
devem falhar (`ImportError`/`AttributeError`) até a implementação ser feita,
e passar depois — sem alterações nesta task além dos próprios testes.

Testes automatizados em `tests/test_participation_integrity.py` (pytest).
Este documento é a versão legível/rastreável dos mesmos casos, mapeada ao
critério de aceite e à seção "Como testar" da issue.

Fora de escopo (não testado aqui, conforme a própria issue):
GraphQL real no `GitHubBoardAdapter`, classificação de intenção
(`origin`/`authorized`/`propagated`/`unresolved`), qualquer chamada a
`list_participations` a partir de `_add_sub_issue` ou outro fluxo, e
qualquer alteração de `remove_from_board`.

## CT01 — `Participation` é um dataclass simples instanciável (AC1)

**Objetivo:** confirmar que `Participation` existe em `src/core/board.py` e
pode ser instanciado com os campos descritos na issue, com os tipos e
valores esperados preservados.

**Procedimento:** importar `Participation` de `src.core.board`; instanciar
com `board_id="backlog"`, `item_id="PVTI_1"`, `project_id="PVT_1"`,
`status="Doing"`, `archived=False`; instanciar uma segunda vez sem passar
`archived`; instanciar uma terceira vez com `board_id=None` e `status=None`
(casos explicitamente previstos na issue: item não resolvido a um board
configurado / coluna vazia).

**Resultado esperado:** os atributos lidos de volta (`.board_id`,
`.item_id`, `.project_id`, `.status`, `.archived`) são exatamente os valores
passados; quando `archived` é omitido, o valor default é `False`;
`board_id=None` e `status=None` são aceitos sem erro.

**Testes:** `test_participation_instantiation_with_all_fields`,
`test_participation_archived_defaults_to_false`,
`test_participation_accepts_none_board_id_and_status`.

---

## CT02 — `BoardPort.list_participations` é uma operação opcional com default no-op (AC2)

**Objetivo:** confirmar que `BoardPort` expõe `list_participations` como
método concreto (não abstrato), no mesmo padrão das demais operações
opcionais da classe, e que o default não implementado não impede a
instanciação de um adapter mínimo.

**Procedimento:** usar um `FakePort(BoardPort)` que implementa somente os
métodos abstratos obrigatórios (mesmo padrão de
`tests/test_sub_issue_propagation_fix.py`), sem sobrescrever
`list_participations`; instanciar o fake sem erro; chamar
`fake.list_participations("76")` diretamente.

**Resultado esperado:** a instanciação do `FakePort` não levanta
`TypeError` por método abstrato pendente (confirma que
`list_participations` não é `@abstractmethod`); a chamada direta ao default
retorna `[]` e não levanta exceção.

**Testes:** `test_fake_port_without_override_instantiates_successfully`,
`test_board_port_default_list_participations_returns_empty_list`.

---

## CT03 — Default de `list_participations` loga warning e não lança exceção (AC2)

**Objetivo:** confirmar que o comportamento do default segue o mesmo padrão
de logging das demais operações opcionais (`remove_from_board`,
`set_labels`, etc.): `log.warning` na chamada, sem propagar exceção.

**Procedimento:** monkeypatch em `src.core.board.log.warning`; chamar o
default de `list_participations` a partir de uma instância de `BoardPort`
concreta mínima (via `FakePort` sem override); inspecionar a chamada
registrada.

**Resultado esperado:** exatamente uma chamada a `log.warning` ocorre;
nenhuma exceção é levantada; o retorno da chamada é `[]`.

**Teste:** `test_default_list_participations_logs_warning_without_raising`.

---

## CT04 — `Board.list_participations` delega ao port e retorna exatamente o que o port devolveu (AC3 / "Como testar")

**Objetivo:** confirmar que `Board.list_participations(issue_id)` é
delegação pura — sem lógica adicional, sem filtrar/transformar o retorno do
port.

**Procedimento:** criar um `FakePort` que sobrescreve `list_participations`
para retornar uma lista fixa de `Participation` (incluindo pelo menos um
item com `board_id` resolvido e outro com `board_id=None`, refletindo o caso
de item não resolvido a um board configurado); instanciar `Board(fake_port)`
e chamar `board.list_participations("76")`; registrar o `issue_id` recebido
pelo fake.

**Resultado esperado:** o valor retornado por `Board.list_participations` é
exatamente (identidade de conteúdo, mesma lista e mesmos objetos) o que o
`FakePort.list_participations` devolveu; o `issue_id` repassado ao port é
`"76"`, sem transformação.

**Testes:** `test_board_list_participations_delegates_to_port`,
`test_board_list_participations_returns_same_objects_as_port`,
`test_board_list_participations_passes_issue_id_unchanged`.

---

## CT05 — `Board.list_participations` com port sem override retorna `[]` sem lançar exceção ("Como testar")

**Objetivo:** confirmar o comportamento fim-a-fim descrito explicitamente na
issue: um `FakePort` que **não** sobrescreve `list_participations` (usa o
default de `BoardPort`), acessado através de `Board`, retorna `[]` e apenas
loga warning — sem propagar exceção através da camada de delegação.

**Procedimento:** instanciar `Board(FakePort())` com o `FakePort` mínimo
(sem override de `list_participations`); chamar
`board.list_participations("76")`.

**Resultado esperado:** retorno `== []`; nenhuma exceção levantada.

**Teste:** `test_board_list_participations_with_default_port_returns_empty_list`.

---

## CT06 — Não regressão da suíte existente (Critério de aceite: "Sem quebra de funcionalidades existentes")

**Objetivo:** garantir que a adição de `Participation`/`list_participations`
não quebra os testes já existentes de `board.py` e demais módulos.

**Procedimento:**
```bash
python -m pytest tests/ -k "participation or board" -v
python -m pytest tests/ -v
```

**Resultado esperado:** todos os testes pré-existentes continuam passando
após a implementação (comparar contagem de `passed`/`failed` antes e depois
da issue ser implementada); nenhum teste de `board.py`/adapters é afetado.

**Status no momento desta verificação (antes da implementação):**
`tests/test_participation_integrity.py` falha em coleta (`ImportError:
cannot import name 'Participation' from 'src.core.board'`) — esperado nesta
etapa, confirmado por execução real. A suíte completa
(`python -m pytest tests/ --ignore=tests/test_participation_integrity.py`)
foi executada antes desta adição: 1183 passed, 28 skipped, 1 xpassed, 21
failed — as 21 falhas são pré-existentes e não relacionadas a esta issue
(`test_agent_log_descritivo.py` e `test_dockerfile.py`; nenhum arquivo de
produção foi tocado por esta task, apenas os dois arquivos novos de teste e
documentação).

---

## Resultado da execução

6 casos de teste (CT01–CT06) cobrem os três itens do escopo técnico da issue
(`Participation`, `BoardPort.list_participations` default, delegação em
`Board.list_participations`) e os três cenários da seção "Como testar":
instanciação do dataclass, delegação com `FakePort` que sobrescreve, e
`FakePort` que usa o default. Todos escritos test-first em
`tests/test_participation_integrity.py`, falhando por `ImportError` no
estado atual do código (esperado nesta etapa). Nenhum teste cobre GraphQL
real, classificação de intenção ou chamadas a partir de `_add_sub_issue` —
explicitamente fora de escopo desta issue.
