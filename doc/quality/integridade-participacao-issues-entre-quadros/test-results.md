# Resultados de Teste — Integridade de participação de issues entre quadros de trabalho

- **Issue:** #310 — "Integridade de participação de issues entre quadros de
  trabalho"
- **Etapa:** Execução de Testes (reexecução após retrabalho pós Code Review)
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-05
- **Branch:** `feature/310-integridade_de_participacao_de_issues_entre_quadros_de_trabalho`
- **Commit sob teste:** `96422bd` — fix(participation): integra reconciliacao
  de participacao ao fluxo real (#310)
- **Base de comparação:** `3598c91` — Merge pull request #329 (merge-base da
  branch com `origin/main`, anterior a qualquer trabalho de #310)

> Este documento registra a **reexecução** dos casos especificados em
> `doc/quality/integridade-participacao-issues-entre-quadros/test-cases.md`
> (CT-01 a CT-23 e variantes), após o code review (SR) ter **reprovado** o PR
> #330 por falta de integração real das funções de participação ao fluxo
> executado pela esteira (`reconcile_after_link`, `reconcile_remote_presence`,
> `guard_cross_board_link`, `detect_external_removal` só existiam, sem nenhum
> ponto de chamada em produção). O desenvolvimento retrabalhou e ligou cada
> gatilho ao caminho real (commit `96422bd`), adicionando testes de integração
> dedicados. Nenhum código ou caso de teste foi alterado nesta etapa de QA.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

A reexecução confirma que o retrabalho do commit `96422bd` resolveu, de forma
verificável, todos os pontos objetivos levantados pelo code review (Bruno
Ferreira) sobre o PR #330:

| Ponto do code review | Verificação nesta reexecução |
|---|---|
| `reconcile_after_link` nunca chamada em produção (RF-07) | `src/core/sync.py::_apply_change_up` chama via `_reconcile_links_after_apply` quando um vínculo cross-board é aplicado — confirmado por leitura de código e por `test_rf07_change_up_cross_board_parent_triggers_reconcile` (✅ PASS) e `test_rf07_same_board_parent_does_not_reconcile` (✅ PASS, prova de não-ação indevida no mesmo board). |
| `reconcile_remote_presence` nunca chamada; `participation_intent` nunca gravado em `_apply_create_down` (RF-08) | `src/core/sync.py::_apply_create_down` agora usa `reconcile_remote_presence` (o guard antigo `_propagation_proof` foi removido — confirmado ausente no código). `test_rf08_create_down_persists_origin_intent` e `test_rf08_create_down_propagated_removed_and_discarded` (✅ PASS). |
| Duas implementações redundantes de bloqueio cross-board (RF-12) | `_filter_suspended_cross_board_parent` delega a `guard_cross_board_link` — confirmado por leitura de código (fonte única). `test_rf12_suspended_blocks_cross_board_parent` e `test_rf12_suspended_allows_same_board_parent` (✅ PASS). |
| `detect_external_removal` nunca chamada pelo loop principal (RF-13/CT-22) | `src/__main__.py::sync_remote_board` chama `participation_reconcile.detect_external_removal(board, config)` a cada ciclo — confirmado por grep (1 ponto de chamada). `test_rf13_sync_remote_board_detects_external_removal` (✅ PASS). |
| Log de execução de agente sem `participation_intent`/quadro de origem (RF-15) | `AgentParams` carrega `participation_intent`/`origin_board` (`src/core/agent.py`); `kiro_cli_agent.py::_build_log` os registra na seção Parâmetros. `test_rf15_agent_log_contains_participation_intent_and_origin` e `test_rf15_agent_log_omits_participation_fields_when_absent` (✅ PASS). |

**Execução dirigida (10 arquivos pertinentes à mudança, 106 testes):**

```
106 passed in 3.96s
```

Inclui os **7 arquivos já verdes na execução anterior** (classificação, gate,
migração, contingência, evidência, adapter — política pura, sem regressão) e
**3 arquivos centrais desta reexecução**:

- `tests/test_participation_integration.py` (**11 testes novos**) — exercitam
  cada gatilho pelo **caminho real** (`_apply_change_up`, `_apply_create_down`,
  `keep_task`, `sync_remote_board`, `_build_log`), não as funções isoladas.
  Fecha exatamente a lacuna apontada pelo code review ("nenhum teste de
  integração que prove a chamada a partir de
  `_add_sub_issue`/`sync_remote`/`keep_task`/`call_agent`").
- `tests/test_sub_issue_propagation_fix.py` (24 testes, guard atualizado para
  `reconcile_remote_presence`/participação) — confirma que a substituição do
  guard antigo (`_propagation_proof`) não regrediu o comportamento histórico
  do incidente #88/#98/#99/#106 (origin/propagated/propagated-com-coluna/
  autorizada/board-fora-da-config/falha-de-consulta).
- `tests/test_hotfix24_incident_doc_cleanup.py` (14 testes) — invariante do
  guard de propagação ajustado ao símbolo atual; Fenômeno 1 (#106) permanece
  coberto.

Todos os **17 critérios de aceitação** e os **23 cenários obrigatórios**
continuam com teste verde (ver seção 4), agora com a garantia adicional de que
os gatilhos RF-07/RF-08/RF-10/RF-12/RF-13/RF-15 são exercitados pelo caminho
de produção, não apenas pela política isolada.

---

## 2. Ambiente de execução

- Python 3.12.15, pytest 9.1.1
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso `kiro-cli`
  real): os testes de integração chamam diretamente `_apply_change_up`,
  `_apply_create_down`, `keep_task` e `sync_remote_board` com um `Board`/
  `BoardPort` fake (dublês de `list_participations`/`remove_from_board`/
  `set_parent` etc.), `monkeypatch.chdir(tmp_path)` para isolar `.pipe/` e
  `logs/`, e sem `monkeypatch` do próprio símbolo sob teste.
- Comandos:
  - `python -m pytest tests/test_participation_classification.py
    tests/test_participation_reconciliation.py tests/test_participation_gate.py
    tests/test_participation_migration.py tests/test_cross_board_safety.py
    tests/test_participation_evidence.py tests/test_participation_adapter.py
    tests/test_participation_integration.py tests/test_sub_issue_propagation_fix.py
    tests/test_hotfix24_incident_doc_cleanup.py -v` (10 arquivos pertinentes)
  - `python -m pytest -q` (suíte completa)
  - `git merge-base HEAD origin/main` → confirma `3598c91` como baseline de
    comparação (mesmo baseline já isolado via `git worktree` na execução
    anterior desta issue).

---

## 3. Resultado da suíte completa

```
26 failed, 1670 passed, 17 skipped, 1 xpassed, 1 warning in 46.98s
```

- **1670 passed** — 13 testes a mais que a execução anterior (1657 → 1670):
  os **11 testes de integração novos** (`test_participation_integration.py`)
  mais o saldo líquido de ajustes em `test_sub_issue_propagation_fix.py`
  (guard atualizado, +testes cobrindo os novos sub-casos de participação) e
  `test_hotfix24_incident_doc_cleanup.py` (invariante restaurado).
- **26 failed** — mesma contagem e os **mesmos 4 arquivos** da baseline já
  documentada na execução anterior desta issue (`test_agent_log_descritivo.py`,
  `test_agent_failure_detection.py::...test_linha_de_inicio_preserva_formato_do_epic`,
  `test_docker_compose.py`, `test_dockerfile.py`) — ver seção 5.
- **17 skipped, 1 xpassed** — inalterados.

Execução dirigida dos 10 arquivos pertinentes a #310:

```
106 passed in 3.96s
```

---

## 4. Resultados por caso de teste

### Grupo A — Classificação pura de intenção (`tests/test_participation_classification.py`)

| CT | Teste | Resultado |
|----|-------|-----------|
| CT-04 | `test_ct04_authorized_label_regardless_of_column[]` / `[Doing]` | ✅ PASS (2) |
| CT-07 | `test_ct07_label_with_unknown_board_is_ignored_with_warning` | ✅ PASS |
| CT-07 | `test_ct07_malformed_label_does_not_raise` | ✅ PASS |
| CT-01a | `test_ct01a_propagated_when_known_presence_with_column_in_other_board` | ✅ PASS |
| CT-01c | `test_ct01c_isolated_parent_without_proof_is_unresolved` | ✅ PASS |
| CT-01c | `test_ct01c_known_presence_without_known_column_is_unresolved` | ✅ PASS |
| CT-origem-01 | `test_ct_origem_first_presence_is_origin` | ✅ PASS |
| CT-06 | `test_ct06_determinism_across_orderings` | ✅ PASS |

### Grupo B — Reconciliação (política + fila), `tests/test_participation_reconciliation.py`

| CT | Teste | Resultado |
|----|-------|-----------|
| CT-01 | `test_ct01_immediate_reconcile_removes_propagated_preserves_hierarchy` | ✅ PASS |
| CT-01b | `test_ct01b_multiple_children_each_reconcile_isolated` | ✅ PASS |
| CT-02 | `test_ct02_late_reconcile_remote_presence_no_column` | ✅ PASS |
| CT-03 | `test_ct03_late_reconcile_with_filled_column_same_as_ct02` | ✅ PASS |
| CT-05 | `test_ct05_query_failure_is_unresolved_deferred_no_removal` | ✅ PASS |
| CT-15 | `test_ct15_remove_failure_propagates_and_preserves_hierarchy` | ✅ PASS |
| CT-16 | `test_ct16_unresolved_defer_does_not_block_other_items` | ✅ PASS |
| CT-17-retentativa | `test_ct17_defer_skipped_until_due_then_eligible` | ✅ PASS |
| CT-02-genérico | `test_ct02_generico_any_hierarchical_pair[historias-epicos]` / `[tarefas-historias]` / `[iniciativas-squads]` | ✅ PASS (3) |

### Grupo C — Gate final e migração de legados

| CT | Teste | Resultado |
|----|-------|-----------|
| CT-08 | `test_ct08_gate_decision_per_intent[origin-True]` / `[authorized-True]` / `[propagated-False]` / `[unresolved-False]` / `[None-False]` | ✅ PASS (5) |
| CT-10 | `test_ct10_dedup_same_board_column_issue` | ✅ PASS |
| CT-09 | `test_ct09_gate_runs_without_network` | ✅ PASS |
| CT-11 | `test_ct11_single_board_becomes_origin` | ✅ PASS |
| CT-12 | `test_ct12_duplicate_without_authorization_becomes_unresolved_both` | ✅ PASS |
| CT-13 | `test_ct13_idempotent_and_never_overwrites` | ✅ PASS |

### Grupo D — Contingência reversível (`tests/test_cross_board_safety.py`)

| CT | Teste | Resultado |
|----|-------|-----------|
| CT-18 | `test_ct18_suspended_blocks_cross_board_allows_same_board` / `test_ct18_enabled_allows_cross_board` | ✅ PASS (2) |
| CT-19 | `test_ct19_reversible_without_restart` | ✅ PASS |
| CT-20 | `test_ct20_invalid_values_rejected[...]` (7) / `test_ct20_valid_configs_accepted[...]` (4) / `test_ct20_safety_not_a_map_rejected` | ✅ PASS (12) |

### Grupo E — Observabilidade e evidência (`tests/test_participation_evidence.py`)

| CT | Teste | Resultado |
|----|-------|-----------|
| CT-14 | `test_ct14_reconcile_success_and_failure_fields_no_secrets` | ✅ PASS |
| CT-21 | `test_ct21_rollout_evidence_all_present` / `test_ct21_rollout_evidence_missing_commit_signaled` | ✅ PASS (2) |
| CT-22 | `test_ct22_external_removal_recorded` | ✅ PASS |
| CT-23 | `test_ct23_no_secrets_in_any_event` | ✅ PASS |

### Porta real (`tests/test_participation_adapter.py`)

3 testes — mapeamento de itens, issue ausente, falha tipada. ✅ PASS (3)

### Testes de integração — caminho real (`tests/test_participation_integration.py`, NOVO nesta reexecução)

| RF | Teste | Resultado |
|----|-------|-----------|
| RF-07 | `test_rf07_change_up_cross_board_parent_triggers_reconcile` | ✅ PASS |
| RF-07 | `test_rf07_same_board_parent_does_not_reconcile` | ✅ PASS |
| RF-08 | `test_rf08_create_down_persists_origin_intent` | ✅ PASS |
| RF-08 | `test_rf08_create_down_propagated_removed_and_discarded` | ✅ PASS |
| RF-10 | `test_rf10_keep_task_blocks_propagated_intent` | ✅ PASS |
| RF-10 | `test_rf10_keep_task_allows_origin_intent` | ✅ PASS |
| RF-12 | `test_rf12_suspended_blocks_cross_board_parent` | ✅ PASS |
| RF-12 | `test_rf12_suspended_allows_same_board_parent` | ✅ PASS |
| RF-13/CT-22 | `test_rf13_sync_remote_board_detects_external_removal` | ✅ PASS |
| RF-15 | `test_rf15_agent_log_contains_participation_intent_and_origin` | ✅ PASS |
| RF-15 | `test_rf15_agent_log_omits_participation_fields_when_absent` | ✅ PASS |

**11/11 PASS** — prova, pelo caminho real executado pela esteira (não pela
função isolada), que RF-07/RF-08/RF-10/RF-12/RF-13/RF-15 estão de fato
integrados, fechando a lacuna identificada pelo code review.

### Regressão nos testes de propagação/incidente pré-existentes

- `tests/test_sub_issue_propagation_fix.py` — **24/24 PASS**, incluindo os
  sub-casos atualizados para o novo guard baseado em participação
  (`test_create_down_parent_cross_board_sem_prova_fica_unresolved`,
  `test_create_down_presenca_propagada_com_prova_descarta`,
  `test_create_down_propagada_com_coluna_preenchida_tambem_descarta`,
  `test_create_down_autorizada_por_rotulo_cria_arquivos`,
  `test_create_down_prova_de_board_fora_da_config_nao_descarta`,
  `test_create_down_falha_de_consulta_fica_unresolved_adiada`). O
  comportamento histórico do incidente #88/#98/#99/#106 (pós-hook via GraphQL,
  preservação de item com `Status`, múltiplos itens) permanece intacto.
- `tests/test_hotfix24_incident_doc_cleanup.py` — **14/14 PASS**, incluindo o
  invariante do Fenômeno 1 ajustado para o guard atual
  (`test_apply_create_down_has_empty_column_guard`), sem regressão na proteção
  do incidente original.

**Total #310 nesta reexecução (10 arquivos):** 106 passed, 0 failed.

---

## 5. Análise de causa das falhas remanescentes (baseline) — zero regressão

A suíte completa retornou **26 failed, 1670 passed, 17 skipped, 1 xpassed**.

**Confirmação de que a baseline não mudou:** o merge-base da branch com
`origin/main` continua sendo `3598c91` (`git merge-base HEAD origin/main` →
`3598c91cc62f4a34217484ddeefd1f2a42876a7e`), já isolado em `git worktree` e
comparado na execução de testes anterior desta issue (26 failed nos mesmos 4
arquivos). Os 26 testes que falham na suíte completa agora são, pela lista
nominal obtida nesta execução, **exatamente os mesmos** da execução anterior:

| Arquivo | Qtd | Causa-raiz | Relação com #310 |
|---------|-----|-----------|-------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de **formato do log diário descritivo** — já documentado em #306/#325 | Nenhuma — formatação de log em `__main__`; não toca participação |
| `tests/test_agent_failure_detection.py::TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato | Nenhuma |
| `tests/test_docker_compose.py` | 4 | Ambiente/validação Docker Compose não disponível na execução; infra Docker | Nenhuma |
| `tests/test_dockerfile.py` | 3 | Dockerfile atual não declara `ARG KIRO_CLI_SHA256`/verificação de hash esperada; infra Docker | Nenhuma |

Nenhum dos arquivos tocados pelo retrabalho (`src/core/sync.py`,
`src/__main__.py`, `src/core/agent.py`, `src/adapters/kiro_cli_agent.py`,
`src/core/version.py`, `CHANGELOG.md`, mais os 3 arquivos de teste já
cobertos acima) coincide com os 4 arquivos de falha. **Falhas novas
introduzidas pelo retrabalho: 0. Falhas corrigidas pelo retrabalho: 0** (fora
do escopo desta etapa).

**Destino:** as 26 falhas pertencem a frentes próprias (formato de log
descritivo e infra Docker), já conhecidas e documentadas (#305, #306, #308,
#325). Não são corrigidas aqui — esta etapa não altera código. Nenhuma delas
classifica #310 como `falha`.

---

## 6. Veredito por critério de aceitação (CA-1..CA-17) — reconfirmado com integração real

| CA | Critério (resumo) | Veredito | Evidência |
|----|--------------------|----------|-----------|
| CA-1 | Reconciliação imediata pós-vínculo preserva hierarquia | **Atendido** | CT-01, CT-01b + `test_rf07_*` (caminho real) ✅ |
| CA-2 | Reconciliação tardia (com/sem coluna); evento só após remoção | **Atendido** | CT-02, CT-03 + `test_rf08_*` (caminho real) ✅ |
| CA-3 | Rótulo de autorização válido → `authorized`, não removida | **Atendido** | CT-04 ✅ |
| CA-4 | Evidência ambígua/falha transitória → `unresolved`, sem arquivos/remoção, adiada | **Atendido** | CT-05, CT-15, CT-16 ✅ |
| CA-5 | Determinismo entre ordens de avaliação | **Atendido** | CT-06 ✅ |
| CA-6 | Rótulo com quadro inexistente ignorado + aviso | **Atendido** | CT-07 ✅ |
| CA-7 | Intenção confirmada permanece candidata | **Atendido** | CT-08 (origin/authorized) + `test_rf10_keep_task_allows_origin_intent` ✅ |
| CA-8 | Intenção não confirmada ignorada + evento deduplicado | **Atendido** | CT-08, CT-10 + `test_rf10_keep_task_blocks_propagated_intent` ✅ |
| CA-9 | Gate sem nenhuma chamada de rede | **Atendido** | CT-09 ✅ |
| CA-10 | Migração de legados: unicidade/duplicidade/idempotência/não sobrescrita | **Atendido** | CT-11, CT-12, CT-13 ✅ |
| CA-11 | Evidência de execução no startup; campo ausente sinalizado | **Atendido** | CT-21 ✅ |
| CA-12 | Contingência bloqueia cross-board; mesmo quadro e preexistentes intactos; reversível sem reinício | **Atendido** | CT-18, CT-19 + `test_rf12_*` (caminho real, guard unificado) ✅ |
| CA-13 | Valor inválido na chave de contingência rejeitado com mensagem acionável | **Atendido** | CT-20 ✅ |
| CA-14 | Eventos de reconciliação com campos mínimos, sem segredos | **Atendido** | CT-14, CT-23 ✅ |
| CA-15 | Remoção externa registrada sem inferir autoria | **Atendido** | CT-22 + `test_rf13_sync_remote_board_detects_external_removal` (caminho real, loop principal) ✅ |
| CA-16 | Mesmo mecanismo cobre qualquer par hierárquico, sem hardcode | **Atendido** | CT-02-genérico ✅ |
| CA-17 | Apuração sobre registros | **Atendido** (capacidade de apurar via eventos estruturados; veredito da janela em si é fora de escopo) | CT-14, CT-17-retentativa ✅ |

**Cobertura:** 17/17 critérios de aceitação com veredito explícito e teste
verde correspondente — agora com a garantia adicional, exigida pelo code
review, de que RF-07/RF-08/RF-10/RF-12/RF-13/RF-15 são exercitados pelo
**caminho real de produção** (`_apply_change_up`, `_apply_create_down`,
`keep_task`, `sync_remote_board`, `_build_log`), não apenas pela função
isolada.

---

## 7. Aderência à arquitetura

- **Política pura no core, sem I/O de rede:** inalterada e reconfirmada
  (`classify_participation`). ✅
- **Integração via orquestração, não pelo adapter:** `reconcile_after_link` é
  chamada em `src/core/sync.py::_apply_change_up` (ponto de orquestração, onde
  `config` e o wrapper `Board` já estão disponíveis), **não** dentro do
  adapter `_add_sub_issue` — decisão de implementação documentada no histórico
  de desenvolvimento. O adapter GitHub permanece sem conhecer `config`/
  classificação, preservando a separação hexagonal core/adapters. ✅
- **Guard de contingência unificado (RF-12):** confirmado por leitura de
  código que `_filter_suspended_cross_board_parent` delega a
  `guard_cross_board_link`, eliminando a duplicidade apontada no code review.
  `test_rf12_suspended_allows_same_board_parent` prova que vínculos no mesmo
  board não são afetados. ✅
- **Guard antigo removido, não deixado morto:** `_propagation_proof` foi
  removido de `src/core/sync.py` (confirmado por grep — zero ocorrências) em
  vez de manter duas implementações divergentes. ✅
- **Hierarquia nunca tocada pela reconciliação (RN-03):** reconfirmado nos
  testes de integração — nenhuma chamada a `set_parent`/`set_children` nos
  caminhos de reconciliação exercitados por `_apply_change_up`/
  `_apply_create_down`. ✅
- **Gate sem rede (RNF-04):** inalterado, reconfirmado por
  `test_ct09_gate_runs_without_network` e por `test_rf10_*` (que usam dublê
  sem necessidade de rede). ✅
- **Erro tipado, nunca silenciado (RN-09):** inalterado nos gatilhos; a
  integração não introduziu nenhum `except` que converta erro tipado em
  retorno silencioso. ✅
- **Sem segredos nos eventos (RNF-09):** inalterado; nenhum teste novo
  introduziu vazamento. ✅
- **Isolamento de teste (anti-#106):** os 11 testes de integração usam
  `monkeypatch.chdir(tmp_path)` e dublês de porta — **nenhum** faz
  `monkeypatch` do símbolo sob teste (`_apply_change_up`, `_apply_create_down`,
  `keep_task`, `sync_remote_board`, `_build_log` são exercitados de verdade). ✅

Nenhuma violação de arquitetura detectada no retrabalho.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 106 testes dirigidos passam
  (incluindo os 11 novos testes de integração que fecham exatamente a lacuna
  do code review); a suíte completa mantém as mesmas 26 falhas de baseline,
  provadamente idênticas ao merge-base `3598c91` (zero regressão), com 13
  testes novos passando líquidos.
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos de
  `test-cases.md` continuam coerentes com os 17 critérios de aceitação; a
  lacuna identificada pelo code review era de **integração do código**, não
  de especificação de caso de teste — os casos já previam o comportamento
  correto (ex.: CT-01/CT-02/CT-03 descrevem reconciliação nos gatilhos reais),
  e o retrabalho os satisfez adicionando a integração e os testes
  correspondentes, sem necessidade de reescrever nenhum caso.
- Nenhuma alteração de código ou de caso de teste foi feita nesta etapa.

— Camila Rocha - Engenheira de Qualidade (QA)
