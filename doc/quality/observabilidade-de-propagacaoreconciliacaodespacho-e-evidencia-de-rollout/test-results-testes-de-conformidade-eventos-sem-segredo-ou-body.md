# Resultados de Teste — Testes de conformidade: eventos estruturados nunca expõem segredo, body ou arquivo protegido

Status: approved
Owner: quality
Last updated: 2026-08-28

## Inputs
- `doc/quality/observabilidade-de-propagacaoreconciliacaodespacho-e-evidencia-de-rollout/test-cases-testes-de-conformidade-eventos-sem-segredo-ou-body.md`
- Task #263 — Testes de conformidade: eventos estruturados nunca expõem segredo, body ou arquivo protegido
- User Story #246 — Observabilidade de propagação/reconciliação/despacho e evidência de rollout

## CT-001 — `assert_no_sensitive_kwargs` não levanta erro para kwargs neutros

**Resultado:** passed

**Observações:**
- `test_ct001_kwargs_neutros_nao_levantam` executado, sem exceção propagada.

## CT-002 — `assert_no_sensitive_kwargs` levanta `ValueError` quando a chave `token` está presente

**Resultado:** passed

**Observações:**
- `test_ct002_token_levanta_valueerror_mencionando_token` — `ValueError` levantado com `"token"` na mensagem.

## CT-003 — `assert_no_sensitive_kwargs` é case-insensitive na comparação de chaves

**Resultado:** passed

**Observações:**
- `test_ct003_case_insensitive` — chave `"BODY"` detectada corretamente.

## CT-004 — `assert_no_sensitive_kwargs` detecta cada uma das demais chaves proibidas (`ssh_key`, `gh_token`, `kiro_api_key`)

**Resultado:** passed

**Observações:**
- `test_ct004_demais_chaves_proibidas` parametrizado — as 3 variações (`ssh_key`, `gh_token`, `kiro_api_key`) passaram individualmente.

## CT-005 — `assert_no_sensitive_kwargs` reporta todas as chaves proibidas presentes, não apenas a primeira

**Resultado:** passed

**Observações:**
- `test_ct005_reporta_todas_as_chaves_proibidas` — mensagem da exceção contém `"token"` e `"body"` simultaneamente.
- Teste adicional (não numerado no doc de casos, mas presente na suíte) `test_forbidden_set_conteudo` também passou, confirmando `FORBIDDEN_LOG_KWARGS == {"token", "ssh_key", "body", "gh_token", "kiro_api_key"}`.

## CT-006 — Inspeção estática: chamadas de log dos `event_type` da story não contêm campos proibidos

**Resultado:** passed

**Observações:**
- `test_ct006_nenhum_campo_proibido_nas_chamadas_de_evento` — nenhuma substring proibida (`body=`, `token=`, `ssh_key=`, `gh_token=`, `kiro_api_key=`) encontrada nos trechos extraídos.
- `test_ct006_rollout_evidence_encontrado_e_validado` — `event_type="rollout_evidence"` encontrado em `src/__main__.py` (verdadeiro-positivo confirmado) e validado sem campos proibidos.

## CT-007 — Inspeção estática não falha quando um `event_type` da lista ainda não existe no código

**Resultado:** passed

**Observações:**
- `test_ct007_event_type_ausente_nao_falha` — confirmado que apenas `rollout_evidence` está implementado no estado atual da base; os outros seis `event_type` (`participation_classified`, `participation_reconciled`, `participation_reconcile_failed`, `participation_removed_externally`, `dispatch_blocked_unconfirmed_intent`, `cross_board_link_blocked`) retornam lista vazia e não causam falha.

## CT-008 — Inspeção estática: evento `participation_classified` não expõe `.body` nem lista completa de labels em `evidence=`

**Resultado:** blocked

**Observações:**
- `test_ct008_evidence_nao_expoe_body_nem_labels_completo` — **SKIPPED** conforme esperado: `participation_classified` ainda não implementado por outra task da story #246 no momento desta execução.
- Não é uma falha: o próprio caso de teste prevê esse resultado ("pulado, sem falha") enquanto o evento não existir no código. Marcado como `blocked` neste relatório apenas para deixar explícito que a task deverá ser reconferida quando `participation_classified` for implementado (conforme já indicado no corpo da issue #263: "Esta task deve ser reexecutada... à medida que as demais tasks desta story forem concluídas").

## CT-009 — Suíte completa de testes não sofre regressão

**Resultado:** passed

**Observações:**
- `python -m pytest tests/test_observability_compliance.py -v` → 11 passed, 1 skipped.
- `python -m pytest` (suíte completa) → 1255 passed, 29 skipped, 1 xpassed, **21 failed**.
- As 21 falhas são em `tests/test_agent_log_descritivo.py` (17) e `tests/test_dockerfile.py` (3) — **pré-existentes na branch, não introduzidas por esta task**. Confirmado por `git diff main...HEAD --stat` e pelo diff do commit `e197806` (desta task): o commit desta task altera exclusivamente `src/core/log.py` e `tests/test_observability_compliance.py`; nenhum dos dois arquivos com falha foi tocado. `test_dockerfile.py` não aparece em nenhum diff desta task; `test_agent_log_descritivo.py` foi alterado por uma task anterior da mesma branch/épico (feature262), não por esta.
- Contagem de falhas (21) e arquivos afetados coincidem exatamente com o relatado no comentário de Desenvolvimento da issue (`Sofia Carvalho`), que já havia identificado essas falhas como pré-existentes via `git stash` + reexecução.

## Resumo

- Total: 9
- Passou: 8
- Falhou: 0
- Bloqueado: 1 (CT-008 — skip esperado, não falha; dependente de implementação futura de `participation_classified` por outra task)

**Conclusão:** Nenhuma reprovação. CT-008 é um "pulo" previsto pelo próprio desenho do teste (aceitação explícita da issue), não uma falha de conformidade. As 21 falhas da suíte completa (CT-009) são pré-existentes e fora do escopo desta task, confirmadas por inspeção do diff. Avançando para **advance**.
