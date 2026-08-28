# Contingência de suspensão de vínculos entre boards

Como operador da esteira
Quero poder suspender temporariamente, por configuração e sem reiniciar o processo, a criação de novos vínculos pai/filho entre issues de boards distintos
Para conter a exposição a participações indevidas enquanto a prevenção definitiva ainda não está em produção, sem perder vínculos e hierarquia já existentes

## Regras de negócio

- RN-B07: a contingência é temporária e não retroativa — não substitui a prevenção definitiva (RF-01 a RF-05) e não se aplica a vínculos já estabelecidos antes de sua ativação.
- Vínculos pai/filho dentro do mesmo board nunca são afetados pela contingência, pois não acionam o efeito de propagação entre Projects.
- A chave de configuração é relida por mtime do `pipe.yml`, sem exigir restart ou deploy, tanto para ativar quanto para desativar.
- Ao desativar, o comportamento normal de prevenção/reconciliação (entregue pelas demais stories deste épico) retoma imediatamente, sem novo deploy.
- Um pedido de vínculo recusado durante a suspensão não é reproduzido automaticamente após a reativação; deve ser submetido novamente pelo operador/agente.

## Critérios de aceitação

- Dado `safety.cross_board_parent_links: suspended` no `pipe.yml`, quando uma nova relação pai/filho é solicitada entre issues de boards distintos, então a esteira impede a operação e registra um evento auditável, em vez de executá-la silenciosamente.
- Dado a mesma configuração `suspended`, quando uma relação pai/filho é solicitada entre issues do mesmo board, então a operação é processada normalmente, sem impedimento.
- Dado `safety.cross_board_parent_links: enabled` (ou a chave ausente), quando uma nova relação pai/filho é solicitada entre boards distintos, então o comportamento normal de prevenção/reconciliação das demais stories deste épico se aplica.
- Dado o processo em execução com a chave em `enabled`, quando o `pipe.yml` é alterado para `suspended` e salvo, então a nova tentativa de vínculo entre boards distintos é bloqueada no ciclo seguinte, sem reiniciar a esteira.
- Dado vínculos pai/filho entre boards distintos estabelecidos antes da ativação da contingência, quando a contingência está ativa, então esses vínculos permanecem intactos e continuam sendo processados normalmente (sync, reconciliação, etc.).
- Dado um valor inválido para `safety.cross_board_parent_links` (diferente de `enabled`/`suspended`), quando o `check_config` valida a configuração, então a validação rejeita com mensagem acionável.

## Não objetivos

- Classificar ou reconciliar participações propagadas (coberto pelas demais stories deste épico).
- Definir o gate de elegibilidade em `keep_task` (coberto pela story de gate de despacho).
- Remover ou alterar vínculos pai/filho já existentes.
- Produzir evidência de rollout do épico como um todo (coberto pela story de observabilidade).

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-contingencia-suspensao-vinculos-entre-boards` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #230 — Integridade de issues entre boards (o épico que originou esta story)
- **Branch da issue pai**: `epic230-230-integridade_de_issues_entre_boards` (branch do épico)

## Rastreabilidade
- RF-09 de `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`.
- RN-B07 de `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`.
- ADR-003 (contingência via `safety.cross_board_parent_links`, relida por mtime) em `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-003-operacao-observavel-sem-nova-stack.md`.
- Ordem relativa: 1 de 6 — contenção imediata, sem dependência de outra story deste épico.
- Documentação completa: `doc/product/integridade-de-issues-entre-boards/stories/contingencia-de-suspensao-de-vinculos-entre-boards.md`
