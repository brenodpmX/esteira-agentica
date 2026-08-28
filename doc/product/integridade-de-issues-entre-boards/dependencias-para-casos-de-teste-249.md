# Dependências para liberar os casos de teste de #249

Data da decisão: 28/08/2026
Responsável: Helena Costa — Product Manager

## Decisão

A issue #249 não deve criar placeholder, copiar nem redefinir a política de intenção. Seus casos de teste serão retomados somente quando a implementação real da story #242 estiver integrada à branch base de #249, junto com os contratos técnicos que a orquestração consome.

Não há definição humana ou arquitetural pendente: RN-B01, RN-B02, RN-B04 e RN-B10, ADR-001 e ADR-002 já determinam o comportamento. A lacuna remanescente é de implementação e integração.

## Contrato negocial consumido por #249

A implementação de #265 deve exportar:

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

O módulo de importação será o mesmo escolhido por #264 para `authorized_boards` e só será considerado estável quando #264/#265 forem implementadas e integradas em #242. Até lá, #249 não deve inventar um caminho de importação.

Regras que os testes de #249 devem consumir, sem redefinir:

- autorização explícita por `board-intent-<board_id>` tem prioridade e produz `authorized`;
- sem outra participação resolvida em board configurado, a participação confirmada é `origin`;
- havendo participação em outro board configurado e sem autorização para o board avaliado, o resultado é `propagated`;
- evidência ausente, ambígua ou restrita a board não configurado produz `unresolved`;
- `Status`, `parent` e a ordem das entradas não alteram a classificação.

Em `reconcile_after_link`, somente participações `propagated` são removidas. `origin`, `authorized` e `unresolved` são preservadas; falhas de consulta ou remoção propagam `ParticipationReconciliationError`.

## Ordem de desbloqueio

1. **#264 — `authorized_boards`**: implementar e validar a autorização por label reservada.
2. **#265 — `classify_participation`**: depende de #264 e materializa a política pura da story #242.
3. **#242 — classificação de intenção**: integrar #264/#265 e disponibilizar o contrato real às consumidoras.
4. **#247/#248 — infraestrutura de participações**: modelo `Participation`, contrato `list_participations` e implementação GraphQL já estão integrados em `origin/epic`, mas também precisam estar presentes na branch base efetiva de #249.
5. **#249 — `reconcile_after_link`**: somente após os itens anteriores estarem presentes na mesma base, retomar Casos de Teste usando o módulo e os tipos reais.

## Critério de desbloqueio de QA

#249 pode voltar a Casos de Teste quando, na sua branch base:

- `authorized_boards` e `classify_participation` existirem com testes aprovados;
- a story #242 estiver integrada, sem API temporária;
- `Participation` e `Board.list_participations` estiverem disponíveis;
- o caminho real de importação da política puder ser usado nos testes.

A mera existência da definição no body de #242/#265 não satisfaz esse critério. Enquanto a implementação não estiver integrada, #249 permanece bloqueada por #242.

## Rastreabilidade

- #242 — Classificação de intenção de participação em board.
- #264 — Resolver autorização multi-board via label `board-intent-<board_id>`.
- #265 — Implementar política pura `classify_participation`.
- #247/#248 — Modelo/contrato de participação e implementação GraphQL.
- RN-B01, RN-B02, RN-B04 e RN-B10.
- ADR-001 — intenção explícita e gate fail-closed.
- ADR-002 — reconciliação no core, orientada a evento e retentável.

## Base Git desta definição

A branch declarada de #249 ainda não existia no remoto. Para preservar a genealogia documentada, ela foi materializada localmente a partir de `origin/story243-243-reconciliacao_imediata_apos_vinculo_paifilho`; a presente definição foi então registrada em `debito249-humano-story-242-nao-implementada`.
