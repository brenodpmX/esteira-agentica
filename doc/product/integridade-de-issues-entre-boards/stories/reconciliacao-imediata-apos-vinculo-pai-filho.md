# Reconciliação imediata após vínculo pai/filho

Como esteira
Quero, imediatamente após criar uma relação pai/filho entre duas issues, consultar as participações da filha e remover qualquer participação classificada como `propagated`, sem alterar a relação pai/filho
Para conter a maior parte das propagações antes que se tornem elegíveis, sem depender apenas da descoberta remota do próximo ciclo

## Regras de negócio

- RN-B02: a prova de propagação exige presença anterior, com coluna conhecida, em outro board configurado; aplica-se também neste fluxo de vínculo (`_add_sub_issue`/equivalente).
- RN-B03: a reconciliação nunca altera, remove ou invalida a relação pai/filho nativa. Se qualquer etapa da remoção arriscar afetar a relação, a operação inteira é abortada em vez de prosseguir parcialmente — é preferível manter uma participação indevida ainda não reconciliada do que perder a hierarquia.
- RN-B05/RN-B06 (fronteira): esta story cobre apenas novas relações criadas a partir de sua entrega; resíduos já materializados antes da entrega não são alvo desta reconciliação imediata.
- A operação usa exclusivamente GraphQL (`projectItems`, `deleteProjectV2Item`) para dados de Project V2; REST permanece reservado às APIs tradicionais de issues/sub-issues.
- Falha na consulta ou na remoção é propagada como erro tipado, nunca silenciada como warning que descarta o caso.

## Critérios de aceitação

- Dado que uma relação pai/filho é criada entre duas issues de boards distintos, quando a filha é consultada imediatamente após o vínculo e possui participação classificada como `propagated` no board do pai, então essa participação é removida via `deleteProjectV2Item` antes de a operação de vínculo ser considerada concluída.
- Dado o cenário acima, quando a remoção é concluída, então a relação pai/filho entre as duas issues continua presente e correta no GitHub e na esteira.
- Dado que a issue tem participação `authorized` no board do pai (label `board-intent-<board_id>`), quando a reconciliação imediata roda, então essa participação não é removida.
- Dado que a consulta ou a remoção falha por erro transitório, quando a operação de vínculo termina, então o erro é propagado de forma tipada e a participação não reconciliada permanece registrada para retentativa pela descoberta remota (story de reconciliação em `create-down`), sem ser silenciosamente descartada.
- Dado uma issue com múltiplos filhos criados em relações separadas, cada um gerando propagação para boards diferentes do seu, quando cada vínculo é reconciliado, então todas as relações pai/filho permanecem intactas simultaneamente.
- O `BoardPort` expõe `list_participations(issue_id)` como contrato normalizado, usado por este fluxo sem que o core dependa de detalhes de GraphQL do adapter.

## Não objetivos

- Cobrir propagação que chega de forma assíncrona, depois da consulta imediata (coberto pela story de reconciliação em `create-down`).
- Definir o modelo de classificação em si (consumido da story de classificação de intenção).
- Aplicar o gate final em `keep_task` (coberto pela story de gate de despacho).
- Suspender a criação do vínculo por contingência (coberto pela story de contingência, que decide antes desta reconciliação ser acionada).

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-reconciliacao-imediata-apos-vinculo-pai-filho` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #230 — Integridade de issues entre boards (o épico que originou esta story)
- **Branch da issue pai**: `epic230-230-integridade_de_issues_entre_boards` (branch do épico)

## Rastreabilidade
- RF-02 (fluxo principal), RF-03 de `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`.
- RN-B02, RN-B03 de `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`.
- ADR-002 — gatilho 1 (após relação pai/filho), contrato `BoardPort.list_participations`/`remove_from_board` em `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-002-reconciliacao-no-core-com-retentativa.md`.
- Ordem relativa: 3 de 6 — depende da classificação de intenção (story 2) existir para decidir o que remover.
- Documentação completa: `doc/product/integridade-de-issues-entre-boards/stories/reconciliacao-imediata-apos-vinculo-pai-filho.md`
