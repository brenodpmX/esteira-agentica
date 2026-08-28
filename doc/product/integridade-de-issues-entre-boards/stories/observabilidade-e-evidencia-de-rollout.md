# Observabilidade de propagação/reconciliação/despacho e evidência de rollout

Como dono/operador da esteira
Quero que todo evento de classificação, reconciliação, falha, remoção externa, despacho bloqueado e contingência seja registrado nos logs JSON estruturados, e que o startup emita evidência verificável de versão/commit/ambiente em execução
Para conseguir auditar a janela de validação de 30 dias e ao menos 17 novas relações entre boards, distinguindo resíduo conhecido de regressão nova, sem depender de inferência ou do relato informal do dono

## Regras de negócio

- RN-B08: a evidência de rollout (commit/versão, ambiente, data) é pré-condição para iniciar a contagem da janela de validação; merge em `main`, isoladamente, não inicia a contagem. Ausência ou perda da evidência bloqueia o fechamento, não é aprovada por omissão.
- RN-B09: toda apuração de meta exige registro auditável, nunca inferência ou ausência de reclamação. Créditos evitados só podem ser calculados a partir de despachos indevidos efetivamente impedidos e do consumo médio observado (baseline: 20,35 créditos em cinco execuções concluídas).
- RN-B05/RF-08: as 17 participações e os 7 despachos indevidos de 25–26/08/2026 (issues #221–#223, #226–#229, #231–#240) compõem baseline de resíduo conhecido; qualquer nova propagação ou despacho indevido identificado após o início da janela é classificado como nova ocorrência, mesmo que a issue já apareça na lista de resíduo.
- Logs não podem conter token, chave SSH, body completo da issue ou conteúdo de arquivos protegidos.

## Critérios de aceitação

- Dado que a esteira inicia (`startup`), quando o processo sobe, então um evento `rollout_evidence` é emitido com `version`, `commit`, `environment` e `started_at`; se qualquer campo não puder ser obtido (ex.: checkout sem `.git` e sem arquivo de build com o hash), o startup registra a ausência de evidência de forma explícita, sem inferir sucesso.
- Dado um `rollout_evidence` completo emitido em um ambiente, quando se consulta os logs, então é possível identificar commit/versão, ambiente e data sem inferência indireta, e essa consulta é o marco de início da janela de validação — merge em `main` sozinho não é suficiente.
- Dado que uma participação é classificada pela política (story de classificação de intenção), quando a classificação ocorre, então um evento `participation_classified` é registrado com issue, board, classificação e evidência usada.
- Dado que uma participação `propagated` é reconciliada (pelas stories de reconciliação imediata ou em `create-down`), quando a remoção é concluída, então um evento `participation_reconciled` é registrado com issue, board de origem, board propagado, timestamp de detecção e de conclusão, permitindo calcular o tempo entre propagação e reconciliação.
- Dado que uma tentativa de classificação ou remoção falha, quando o erro ocorre, então um evento `participation_reconcile_failed` é registrado com issue, board, tentativa, `next_attempt_at` e tipo de erro.
- Dado que uma participação previamente pendente desaparece do board sem `participation_reconciled` correspondente, quando essa ausência é observada, então um evento `participation_removed_externally` é registrado, permitindo apurar intervenção manual sem inventar autoria.
- Dado que `keep_task` bloqueia uma issue por intenção não confirmada, quando o bloqueio ocorre, então um evento `dispatch_blocked_unconfirmed_intent` é registrado de forma deduplicada (issue, board, coluna, classificação).
- Dado que a contingência de suspensão bloqueia uma tentativa de vínculo entre boards distintos, quando o bloqueio ocorre, então um evento `cross_board_link_blocked` é registrado com pai, filho, boards e versão de configuração.
- Dado 30 dias e ao menos 17 novas relações entre boards transcorridos com `rollout_evidence` válido, quando os registros são consultados, então é possível apurar: número de participações propagadas, número de reconciliações automáticas, número de remoções manuais, número de despachos indevidos e créditos consumidos por eles.
- Dado o baseline de resíduo conhecido (issues #221–#223, #226–#229, #231–#240) registrado antes do início da janela, quando uma dessas issues sofre uma **nova** propagação ou despacho indevido **após** o início da janela, então esse evento novo é classificado e contado como nova ocorrência, não como resíduo — a exclusão do resíduo é temporal, não por número de issue.
- Dado o log de execução de um agente (`logs/<issue_id>/<timestamp>.md`), quando um despacho ocorre, então o log é enriquecido com `participation_intent` e board de origem, permitindo correlacionar despachos indevidos ao consumo já registrado.
- Nenhum evento acima contém token, chave SSH, body completo de issue ou conteúdo de arquivo protegido.

## Não objetivos

- Construir dashboard, banco de auditoria ou stack de métricas nova (explicitamente fora de escopo pela arquitetura).
- Decidir se a janela de validação foi bem-sucedida (é apuração operacional/negocial posterior à entrega técnica, feita com base nestes registros).
- Limpar retroativamente os resíduos já materializados (#84/#85/#86 e as 17 participações da janela do incidente).
- Implementar a classificação, a reconciliação ou o gate em si (apenas instrumentá-los; consumido das stories anteriores).

## Referências (obrigatório)
- **Branch desta issue**: `story/<id>-observabilidade-e-evidencia-de-rollout` — branch vinculada a esta story. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #230 — Integridade de issues entre boards (o épico que originou esta story)
- **Branch da issue pai**: `epic230-230-integridade_de_issues_entre_boards` (branch do épico)

## Rastreabilidade
- RF-06, RF-07, RF-08 de `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`.
- RN-B05, RN-B06, RN-B08, RN-B09 de `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`.
- ADR-003 — eventos JSON estáveis, `rollout_evidence`, enriquecimento do log de agente em `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-003-operacao-observavel-sem-nova-stack.md`.
- Ordem relativa: 6 de 6 — depende dos eventos gerados pelas stories de contingência, classificação, reconciliação (imediata e em `create-down`) e gate; instrumenta-os sem alterá-los estruturalmente.
- Documentação completa: `doc/product/integridade-de-issues-entre-boards/stories/observabilidade-e-evidencia-de-rollout.md`
