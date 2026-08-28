# Classificação de intenção de participação em board

Como esteira
Quero classificar toda participação (item de Project V2) de uma issue em `origin`, `authorized`, `propagated` ou `unresolved`, usando boards configurados e autorização explícita por label — nunca `Status` ou `parent` isolado
Para ter uma base determinística e sem chamadas de rede que decida, em qualquer ponto do fluxo, se uma participação pode se tornar executável

## Regras de negócio

- RN-B01: participação sem prova de intenção nunca é executável; na ausência de confirmação, é tratada como suspeita de propagação, não como issue nova legítima. Exceção: criação original de uma issue em um board (`create-up`/`create-down` sem relação pai/filho envolvida) já é intencional por definição.
- RN-B02: uma participação sem `Status` só é classificada como propagação quando a mesma issue já está registrada, com coluna conhecida, em outro board presente no `pipe.yml`. Um snapshot de board não mais configurado não serve como prova; `parent` isolado também não basta. Quando a prova não pode ser obtida, a participação permanece em espera (`unresolved`), nunca é tratada como issue nova por omissão.
- RN-B04: participação multi-board só é válida com autorização explícita e verificável (label reservada `board-intent-<board_id>`), nunca por ausência de reconciliação ou omissão de verificação. Ausência de autorização é o padrão — participação em dois boards sem autorização é propagação suspeita.
- RN-B10: a classificação deve valer para qualquer par de boards configurados, sem lista de pares hardcoded (Epics↔User Stories, User Stories↔Tasks ou qualquer par futuro).
- `Status` preenchido ou vazio não prova intenção; a classificação deve ser idêntica para itens com e sem coluna.
- A label `board-intent-<board_id>` só autoriza o board citado no sufixo; o board deve existir no `pipe.yml` — curinga não é permitido e board inexistente gera warning, sem conceder autorização.

## Critérios de aceitação

- Dado que uma issue tem uma única participação confirmada em um board configurado, quando a política classifica essa participação, então o resultado é `origin`.
- Dado que uma issue tem a label `board-intent-<board_id>` para um board configurado, quando a política classifica a participação nesse board, então o resultado é `authorized`, independentemente de `Status` estar vazio ou preenchido.
- Dado que uma issue já está confirmada com coluna conhecida em outro board configurado e não tem autorização para o board atual, quando a política classifica a participação no board atual, então o resultado é `propagated`, com ou sem `Status` preenchido.
- Dado que a consulta de participações falha transitoriamente ou a evidência é ambígua (ex.: duplicidade legada sem autorização), quando a política classifica, então o resultado é `unresolved`.
- Dado o mesmo conjunto de boards configurados, labels e participações confirmadas, quando a classificação é executada em ordens diferentes de avaliação, então o resultado é idêntico (determinismo).
- Dado uma label `board-intent-<board_id>` cujo `<board_id>` não existe em `pipe.yml`, quando a política avalia autorização, então essa label é ignorada para fins de autorização e um warning é registrado.
- A política é uma função pura, sem I/O de rede, testável isoladamente com boards/labels/participações como entrada.

## Não objetivos

- Consultar `projectItems`/GraphQL ou remover participação (coberto pelas stories de reconciliação).
- Persistir `participation_intent` no snapshot ou aplicar o gate em `keep_task` (coberto pela story de gate de despacho).
- Migrar entradas legadas de snapshot sem o campo `participation_intent` (coberto pela story de gate de despacho, que consome o resultado desta classificação na migração).

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-classificacao-de-intencao-de-participacao` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #230 — Integridade de issues entre boards (o épico que originou esta story)
- **Branch da issue pai**: `epic230-230-integridade_de_issues_entre_boards` (branch do épico)

## Rastreabilidade
- RF-01, RF-04, RF-05 de `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`.
- RN-B01, RN-B02, RN-B04, RN-B10 de `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`.
- ADR-001 — modelo de intenção (`origin`/`authorized`/`propagated`/`unresolved`) em `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-001-intencao-explicita-e-gate-fail-closed.md`.
- Ordem relativa: 2 de 6 — depende apenas da contingência existir como conceito de configuração; é a base de política consumida pelas demais stories.
- Documentação completa: `doc/product/integridade-de-issues-entre-boards/stories/classificacao-de-intencao-de-participacao.md`
