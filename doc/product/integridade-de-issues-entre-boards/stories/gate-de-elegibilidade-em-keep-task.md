# Gate de elegibilidade por intenção confirmada em keep_task

Como esteira
Quero que `keep_task` só selecione ou avance uma issue quando `participation_intent` no snapshot for `origin` ou `authorized`, sem chamar rede
Para impedir despacho de agente sobre qualquer participação não confirmada como intencional, mesmo se ela escapar das camadas de reconciliação por falha, resíduo ou regressão

## Regras de negócio

- RN-B01: participação sem prova de intenção nunca é executável — o gate é a barreira final que garante isso mesmo que as camadas anteriores falhem.
- `keep_task` não pode chamar rede; o gate usa exclusivamente a intenção já confirmada e cacheada no snapshot pelas camadas de classificação/reconciliação.
- Toda entrada sem intenção confirmada (ausente, pendente ou conflitante) falha fechada: sem auto-advance, sem seleção e sem execução de agente.
- Entradas de snapshot legadas (sem o campo `participation_intent`) são migradas no full sync de startup, antes do primeiro `keep_task`: issue presente em um único board configurado recebe `origin`; duplicidade sem autorização fica `unresolved`, bloqueada, sem remoção automática de resíduo histórico.
- Itens de fila sem `next_attempt_at` continuam imediatamente elegíveis (compatibilidade retroativa).

## Critérios de aceitação

- Dado que o snapshot de uma issue em um board tem `participation_intent` igual a `origin` ou `authorized`, quando `keep_task` avalia essa issue, então ela permanece candidata normalmente, sujeita aos demais filtros já existentes.
- Dado que o snapshot de uma issue em um board tem `participation_intent` igual a `propagated` ou `unresolved`, ou não tem o campo, quando `keep_task` avalia essa issue, então ela é ignorada para seleção e para auto-advance, e um evento `dispatch_blocked_unconfirmed_intent` deduplicado é registrado.
- Dado que uma issue tem participação intencional confirmada em dois boards (multi-board autorizado), quando `keep_task` avalia qualquer um dos dois boards, então a issue permanece elegível normalmente em ambos.
- Dado que uma participação propagada já foi reconciliada (removida do board indevido), quando `keep_task` roda novamente, então essa issue não é mais candidata no board indevido, pois a participação ali não existe mais.
- Dado um snapshot legado sem `participation_intent`, quando o full sync de startup roda antes do primeiro `keep_task`, então o campo é migrado conforme a regra de unicidade/duplicidade descrita, e nenhuma issue chega a `keep_task` sem o campo preenchido.
- Dado um item de fila sem `next_attempt_at` (formato anterior a esta entrega), quando a fila é processada, então ele continua elegível imediatamente, sem exigir migração adicional.
- O código do gate não realiza nenhuma chamada de rede — verificável por inspeção/teste com fake `BoardPort` que falha se chamado.

## Não objetivos

- Classificar participações ou executar reconciliação (consumido das stories anteriores; esta story apenas lê o resultado já cacheado).
- Registrar os eventos de observabilidade além do `dispatch_blocked_unconfirmed_intent` mínimo necessário ao gate (o conjunto completo de eventos é coberto pela story de observabilidade).
- Migrar ou limpar resíduos materializados antes da entrega deste épico.

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-gate-de-elegibilidade-em-keep-task` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #230 — Integridade de issues entre boards (o épico que originou esta story)
- **Branch da issue pai**: `epic230-230-integridade_de_issues_entre_boards` (branch do épico)

## Rastreabilidade
- RF-01 (fluxo completo) de `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`.
- RN-B01 de `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`.
- ADR-001 — gate em `keep_task`, migração de snapshots legados, campo `participation_intent` cacheado em `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-001-intencao-explicita-e-gate-fail-closed.md`.
- Ordem relativa: 5 de 6 — depende da classificação de intenção (story 2) para o formato do campo; é a barreira final independente das reconciliações (stories 3 e 4), consumindo o mesmo snapshot que elas escrevem.
- Documentação completa: `doc/product/integridade-de-issues-entre-boards/stories/gate-de-elegibilidade-em-keep-task.md`
