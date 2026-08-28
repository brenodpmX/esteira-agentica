# Reconciliação na descoberta remota com retentativa sem bloqueio

Como esteira
Quero, em todo `create-down`, classificar toda participação nova (com ou sem `Status`) e reconciliar as que forem `propagated`, mantendo as `unresolved` pendentes com retentativa por `next_attempt_at` sem bloquear a fila
Para cobrir propagação que chega de forma assíncrona depois do vínculo, incluindo os pares Story→Epic e Task→User Story, sem depender de intervenção manual nem travar outros itens da fila

## Regras de negócio

- RN-B02: prova de propagação exige presença anterior, com coluna conhecida, em outro board configurado; aplica-se também na descoberta remota (`create-down`).
- RN-B03: a reconciliação nunca altera a relação pai/filho.
- RN-B05: resíduo já ocorrido (issues #221–#223, #226–#229, #231–#240) não conta contra a meta de validação; esta story trata apenas de participações novas observadas pelo `create-down` a partir de sua entrega.
- RN-B10: cobertura por comportamento de fluxo, sem hardcode por par de boards — inclui Story→Epic, Task→User Story e qualquer par futuro.
- Falha transitória de classificação/consulta/remoção não pode consumir o evento nem virar dead-letter apenas por atingir `sync.max_attempts`; deve ser retentada com atraso (`next_attempt_at`) e sem bloquear outros itens da fila.
- Enquanto uma participação estiver `unresolved` ou `propagated` não reconciliada, nenhum arquivo local executável (`-body.md`, `-history.md`, `-addcomment.md`) é criado para ela.

## Critérios de aceitação

- Dado que uma issue nova aparece em um board via `create-down` já com `Status` preenchido, quando a classificação roda, então ela é tratada da mesma forma que uma sem `Status` — `Status` preenchido não isenta da classificação.
- Dado que uma story é vinculada como filha de um épico em outro board e a propagação chega tardiamente ao `create-down` do board de épicos, quando a classificação identifica `propagated`, então a participação é removida via `remove_from_board`, o evento só é consumido após a remoção, e nenhum agente do fluxo de épicos é despachado sobre a story.
- Dado que uma task é vinculada como filha de uma story em outro board e a propagação chega tardiamente ao `create-down` do board de stories, quando a classificação identifica `propagated`, então o mesmo comportamento se aplica, sem tratamento hardcoded específico para esse par.
- Dado que a classificação resulta em `unresolved` (evidência ambígua ou falha transitória na consulta ao outro board), quando o `create-down` processa o evento, então nenhum arquivo local é criado, o item recebe `next_attempt_at = now + sleep` e é rotacionado na fila sem bloquear outros itens do mesmo ou de outros boards.
- Dado um item `unresolved` cujo `next_attempt_at` ainda não venceu, quando a fila é processada no ciclo seguinte, então ele é pulado sem consumir tentativa adicional, e outros itens elegíveis continuam sendo processados normalmente.
- Dado que uma participação previamente detectada como pendente desaparece do board sem que a reconciliação automática tenha registrado sucesso, quando o próximo ciclo observa essa ausência, então o evento correspondente de remoção externa é registrado (consumido pela story de observabilidade) em vez de ser silenciosamente ignorado.
- Dado que uma issue é classificada como `origin` ou `authorized`, quando o `create-down` processa o evento, então os três arquivos locais são criados normalmente, sem alteração de comportamento em relação ao fluxo atual.

## Não objetivos

- Reconciliação imediata após a criação do vínculo (coberta pela story anterior; esta story é a segunda camada de defesa, para chegada tardia).
- Definir o modelo de classificação em si (consumido da story de classificação de intenção).
- Aplicar o gate final em `keep_task` (coberto pela story de gate de despacho).
- Reclassificar ou limpar retroativamente os resíduos já materializados da janela de 25–26/08/2026.

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-reconciliacao-em-create-down-com-retentativa` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #230 — Integridade de issues entre boards (o épico que originou esta story)
- **Branch da issue pai**: `epic230-230-integridade_de_issues_entre_boards` (branch do épico)

## Rastreabilidade
- RF-02 (fluxo alternativo), RF-05 de `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`.
- RN-B02, RN-B05, RN-B10 de `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`.
- ADR-002 — gatilho 2 (`create-down`), retentativa via `ChangeQueue`/`next_attempt_at`, eliminação da política concorrente no adapter em `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-002-reconciliacao-no-core-com-retentativa.md`.
- Ordem relativa: 4 de 6 — depende da classificação de intenção (story 2); complementa a reconciliação imediata (story 3) como segunda camada de defesa.
- Documentação completa: `doc/product/integridade-de-issues-entre-boards/stories/reconciliacao-em-create-down-com-retentativa.md`
