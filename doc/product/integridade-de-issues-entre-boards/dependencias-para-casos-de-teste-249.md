# Dependências para liberar os casos de teste de #249

Data da decisão: 28/08/2026
Responsável: Helena Costa — Product Manager

## Decisão

A issue #249 não deve criar placeholder, copiar nem redefinir a política de
intenção. Seus casos de teste serão retomados somente quando a implementação
real da story #242 estiver integrada à branch base efetiva de #249, junto com
os contratos técnicos e com a baseline documental que define o comportamento.

A definição negocial e arquitetural já foi produzida na linhagem da branch
`epic230-230-integridade_de_issues_entre_boards`: RN-B01, RN-B02, RN-B04 e
RN-B10 definem as regras de negócio; ADR-001 define os quatro resultados da
classificação; ADR-002 define como a reconciliação consome essa classificação.
Isso **não significa que a definição já esteja disponível para #249**. Em
28/08/2026, esses documentos não pertencem à ancestralidade de `origin/epic`,
da branch de origem de #249 nem desta branch de correção.

Portanto, não há nova decisão humana ou arquitetural a tomar nesta issue, mas
há uma dependência documental, de implementação e de integração. A lacuna só
estará materialmente encerrada para QA quando os documentos da linhagem
`epic230`, #264, #265, #242 e os contratos #247/#248 estiverem presentes na
mesma base efetiva de #249. A existência em outra branch ou apenas no body das
issues não libera os testes.

## Contrato negocial consumido por #249

A task #265 especifica o contrato-alvo abaixo; ele é referência de
planejamento, não uma API disponível enquanto #265/#242 não forem integradas:

```python
class ParticipationClassification(str, Enum):
    ORIGIN = "origin"
    AUTHORIZED = "authorized"
    PROPAGATED = "propagated"
    UNRESOLVED = "unresolved"


def classify_participation(
    board_id: str,
    labels: list[str],
    known_participations: list["Participation"],
    config: dict,
) -> ParticipationClassification:
    ...
```

O módulo de importação será o mesmo escolhido por #264 para
`authorized_boards` e só será considerado estável quando #264/#265 forem
implementadas e integradas em #242. Até lá, #249 não deve inventar um caminho
de importação.

Regras que os testes de #249 devem consumir, sem redefinir:

- autorização explícita por `board-intent-<board_id>` tem prioridade e produz
  `authorized`;
- sem outra participação resolvida em board configurado, a participação
  confirmada é `origin`;
- havendo participação em outro board configurado e sem autorização para o
  board avaliado, o resultado é `propagated`;
- evidência ausente, ambígua ou restrita a board não configurado produz
  `unresolved`;
- `Status`, `parent` e a ordem das entradas não alteram a classificação.

Em `reconcile_after_link`, somente participações `propagated` são removidas.
`origin`, `authorized` e `unresolved` são preservadas; falhas de consulta ou
remoção propagam `ParticipationReconciliationError`.

## Ordem de desbloqueio

1. **Baseline documental do épico #230**: integrar na linhagem que alimentará
   a base de #249 os documentos que hoje existem em
   `epic230-230-integridade_de_issues_entre_boards`, em especial
   `business-rules.md`, ADR-001 e ADR-002. Não basta que existam apenas nessa
   branch lateral.
2. **#264 — `authorized_boards`**: implementar, testar e integrar a autorização
   por label reservada na branch da story #242.
3. **#265 — `classify_participation`**: após #264, implementar e integrar a
   política pura na branch da story #242.
4. **#242 — classificação de intenção**: integrar #264/#265 preservando sua
   ancestralidade documental do épico #230 e disponibilizar o contrato real à
   linha de integração do épico.
5. **#247/#248 — infraestrutura de participações**: modelo `Participation`,
   contrato `list_participations` e implementação GraphQL já estão integrados
   em `origin/epic`, mas precisam continuar presentes na base efetiva de #249.
6. **#249 — `reconcile_after_link`**: atualizar sua base somente após os itens
   anteriores convergirem na mesma linhagem; então retomar Casos de Teste com
   os módulos, tipos e documentos reais.

A integração deve seguir o fluxo normal das branches do épico; #249 não deve
copiar isoladamente a política ou os ADRs para contornar a dependência.

## Critério de desbloqueio de QA

#249 pode voltar a Casos de Teste quando, na ancestralidade de sua branch base:

- existirem
  `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`,
  `adr-001-intencao-explicita-e-gate-fail-closed.md` e
  `adr-002-reconciliacao-no-core-com-retentativa.md`;
- `authorized_boards` e `classify_participation` existirem com testes
  aprovados e caminho de importação definitivo;
- a story #242 estiver integrada, sem API temporária;
- `Participation` e `Board.list_participations` estiverem disponíveis;
- não houver divergência entre a implementação integrada e a baseline
  documental.

A mera existência da definição em `epic230` ou nos bodies de #242/#265 não
satisfaz esse critério. Enquanto a linhagem comum não existir, #249 permanece
bloqueada por #242 e não deve criar casos de teste baseados em uma API
inventada.

## Rastreabilidade

- #242 — Classificação de intenção de participação em board.
- #264 — Resolver autorização multi-board via label
  `board-intent-<board_id>`.
- #265 — Implementar política pura `classify_participation`.
- #247/#248 — Modelo/contrato de participação e implementação GraphQL.
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md` —
  RN-B01, RN-B02, RN-B04 e RN-B10.
- `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-001-intencao-explicita-e-gate-fail-closed.md`.
- `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-002-reconciliacao-no-core-com-retentativa.md`.

## Base Git desta definição

Esta branch de correção parte de
`feature249-249-criar_participationintegrityreconcile_after_link_no_core_com_erro_tipado`.
Na verificação de 28/08/2026, a branch de origem estava no commit `88da2cb` e a
baseline documental estava em
`epic230-230-integridade_de_issues_entre_boards` (`f86a786`). A branch
`epic230` não era ancestral de `origin/epic`, da branch de origem de #249 nem
desta correção. Essa ausência é uma dependência explícita de desbloqueio, não
evidência de que as regras ou ADRs ainda precisem ser reinventados.
