# Resultados de Teste — Integridade de participação de issues entre quadros de trabalho

- **Issue:** #310 — "Integridade de participação de issues entre quadros de
  trabalho"
- **Etapa:** Execução de Testes
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-05
- **Branch:** `feature/310-integridade_de_participacao_de_issues_entre_quadros_de_trabalho`
- **Commit sob teste:** `c016de0` — feat(participation): integridade de
  participacao entre quadros (#310)
- **Base de comparação:** `3598c91` — Merge pull request #329 (base da
  branch, anterior a qualquer trabalho de #310)

> Este documento registra a execução dos casos especificados em
> `doc/quality/integridade-participacao-issues-entre-quadros/test-cases.md`
> (CT-01 a CT-23 e variantes, cobrindo os 17 critérios de aceitação da issue),
> com veredito e análise de causa das falhas remanescentes. Nenhum código ou
> caso de teste foi alterado nesta etapa.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

A entrega de integridade de participação entre quadros (#310) está
**implementada na branch de trabalho** e **coberta por testes automatizados
verdes** que atravessam a classificação pura de intenção (origem/autorizada/
propagada/não resolvida, sem rede e determinística), os dois gatilhos de
reconciliação (imediato pós-vínculo e tardio na descoberta remota), a
retentativa sem bloqueio de fila, a barreira final na seleção de tarefas sem
rede, a migração de legados no startup, a contingência reversível
`safety.cross_board_parent_links`, os eventos estruturados sem segredos, a
evidência de execução no startup e a generalização sem hardcode por par de
quadros.

- **53 testes novos passam** (0 falhas) nos 7 arquivos pertinentes à mudança:
  - `tests/test_participation_classification.py` (9) — Grupo A, classificação pura;
  - `tests/test_participation_reconciliation.py` (11) — Grupo B, reconciliação e retentativa;
  - `tests/test_participation_gate.py` (7) — Grupo C, gate final;
  - `tests/test_participation_migration.py` (3) — Grupo C, migração de legados;
  - `tests/test_cross_board_safety.py` (18) — Grupo D, contingência reversível;
  - `tests/test_participation_evidence.py` (6) — Grupo E, observabilidade e evidência;
  - `tests/test_participation_adapter.py` (3) — porta real (`list_participations`).
- Os **17 critérios de aceitação** (CA-1..CA-17) e os **23 cenários
  obrigatórios** (CT-01..CT-23, incluindo variantes CT-01a/b/c, CT-02-genérico
  e CT-17-retentativa) têm teste correspondente verde (ver seções 4 e 6).

As **26 falhas** remanescentes na suíte completa são **baseline
pré-existente**, confirmadas **idênticas** em `3598c91` (**zero regressão**),
**alheias** ao escopo de #310 (débito de **formato do log diário descritivo**
e de **infra Docker**, já documentado nas entregas #306/#325). Não constituem
reprovação de código desta entrega.

Portanto **não** há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste` (volta ao QA): os casos especificados em
`test-cases.md` são coerentes com os critérios de aceitação, exercitam o
código real (`src/core/participation.py`, `src/core/participation_reconcile.py`,
`BoardPort`/adapter real via GraphQL, `keep_task`, `config.py`) com dublês de
porta e sem `monkeypatch` do símbolo sob teste (lição #106), e passam
integralmente.

---

## 2. Ambiente de execução

- Python 3.12.15, pytest 9.1.1
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso `kiro-cli`
  real): os casos de #310 exercitam a política pura e a reconciliação via
  `BoardPort` fake (dublês de `list_participations`/`remove_from_board`,
  inclusive dublê que levanta `AssertionError` se chamado para provar ausência
  de I/O no gate — CT-09), `monkeypatch.chdir(tmp_path)` para isolar `.pipe/` e
  `logs/`, e sem `monkeypatch` do próprio símbolo sob teste.
- Comandos:
  - `python -m pytest tests/test_participation_classification.py
    tests/test_participation_reconciliation.py tests/test_participation_gate.py
    tests/test_participation_migration.py tests/test_cross_board_safety.py
    tests/test_participation_evidence.py tests/test_participation_adapter.py -v`
    (os 7 arquivos pertinentes)
  - `python -m pytest -q` (suíte completa)
  - comparação de baseline por `git worktree add` em `3598c91` (base da
    branch, anterior ao trabalho de #310), rodando os 4 arquivos que
    concentram as falhas e confrontando o conjunto de IDs.

---

## 3. Resultado da suíte completa

```
26 failed, 1657 passed, 17 skipped, 1 xpassed, 1 warning in 50.65s
```

- **1657 passed** — inclui os **53 testes** novos de #310.
- **26 failed** — baseline pré-existente (ver seção 5).
- **17 skipped, 1 xpassed** — inalterados em relação ao baseline.

Execução dirigida dos 7 arquivos de #310:

```
53 passed in 1.72s
```

---

## 4. Resultados por caso de teste

Mapeamento caso → teste → resultado. Todos os casos do `test-cases.md` têm
teste automatizado verde correspondente.

### Grupo A — Classificação pura de intenção (`tests/test_participation_classification.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-04 | Presença autorizada por rótulo válido, com/sem coluna (param.) | `test_ct04_authorized_label_regardless_of_column[]` / `[Doing]` | ✅ PASS (2) |
| CT-07 | Rótulo com quadro inexistente é ignorado, com aviso | `test_ct07_label_with_unknown_board_is_ignored_with_warning` | ✅ PASS |
| CT-07 | Rótulo malformado não lança exceção | `test_ct07_malformed_label_does_not_raise` | ✅ PASS |
| CT-01a | Propagação por presença conhecida com coluna em outro quadro | `test_ct01a_propagated_when_known_presence_with_column_in_other_board` | ✅ PASS |
| CT-01c | Relação pai/filho isolada sem prova vira não resolvida | `test_ct01c_isolated_parent_without_proof_is_unresolved` | ✅ PASS |
| CT-01c | Presença conhecida sem coluna conhecida vira não resolvida | `test_ct01c_known_presence_without_known_column_is_unresolved` | ✅ PASS |
| CT-origem-01 | Primeira presença em quadro configurado vira origem | `test_ct_origem_first_presence_is_origin` | ✅ PASS |
| CT-06 | Determinismo entre ordens de avaliação diferentes | `test_ct06_determinism_across_orderings` | ✅ PASS |

### Grupo B — Reconciliação (imediata/tardia), falha e retentativa (`tests/test_participation_reconciliation.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-01 | Reconciliação imediata pós-vínculo preserva a hierarquia | `test_ct01_immediate_reconcile_removes_propagated_preserves_hierarchy` | ✅ PASS |
| CT-01b | Múltiplos filhos: reconciliação isolada por vínculo | `test_ct01b_multiple_children_each_reconcile_isolated` | ✅ PASS |
| CT-02 | Reconciliação tardia na descoberta remota, sem coluna | `test_ct02_late_reconcile_remote_presence_no_column` | ✅ PASS |
| CT-03 | Reconciliação tardia com coluna preenchida (coluna não isenta) | `test_ct03_late_reconcile_with_filled_column_same_as_ct02` | ✅ PASS |
| CT-05 | Falha transitória de consulta vira não resolvida, sem remoção | `test_ct05_query_failure_is_unresolved_deferred_no_removal` | ✅ PASS |
| CT-15 | Falha na remoção propaga erro tipado, hierarquia preservada | `test_ct15_remove_failure_propagates_and_preserves_hierarchy` | ✅ PASS |
| CT-16 | Não resolvida adiada sem bloquear outros itens | `test_ct16_unresolved_defer_does_not_block_other_items` | ✅ PASS |
| CT-17-retentativa | Pendência pulada antes do prazo; elegível depois | `test_ct17_defer_skipped_until_due_then_eligible` | ✅ PASS |
| CT-02-genérico | Mesmo mecanismo cobre qualquer par hierárquico (param., incl. par sintético) | `test_ct02_generico_any_hierarchical_pair[historias-epicos]` / `[tarefas-historias]` / `[iniciativas-squads]` | ✅ PASS (3) |

### Grupo C — Gate final (`tests/test_participation_gate.py`) e migração de legados (`tests/test_participation_migration.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-08 | Gate confirma origem/autorizada; bloqueia propagada/não resolvida/ausente (param.) | `test_ct08_gate_decision_per_intent[origin-True]` / `[authorized-True]` / `[propagated-False]` / `[unresolved-False]` / `[None-False]` | ✅ PASS (5) |
| CT-10 | Deduplicação do evento de despacho bloqueado por (board, coluna, issue) | `test_ct10_dedup_same_board_column_issue` | ✅ PASS |
| CT-09 | Gate roda sem nenhuma chamada de rede (dublê que falha se chamado) | `test_ct09_gate_runs_without_network` | ✅ PASS |
| CT-11 | Migração: board único vira origem | `test_ct11_single_board_becomes_origin` | ✅ PASS |
| CT-12 | Migração: duplicidade sem autorização vira não resolvida em ambas | `test_ct12_duplicate_without_authorization_becomes_unresolved_both` | ✅ PASS |
| CT-13 | Migração: idempotência e não sobrescrita | `test_ct13_idempotent_and_never_overwrites` | ✅ PASS |

### Grupo D — Contingência reversível (`tests/test_cross_board_safety.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-18 | Suspensa bloqueia cross-board; mesmo quadro permitido | `test_ct18_suspended_blocks_cross_board_allows_same_board` | ✅ PASS |
| CT-18 | Habilitada permite vínculo cross-board | `test_ct18_enabled_allows_cross_board` | ✅ PASS |
| CT-19 | Reversível sem reinício (relida do disco, sem cache) | `test_ct19_reversible_without_restart` | ✅ PASS |
| CT-20 | Valores inválidos rejeitados (param.: caixa, espaços, vazio, tipo, bool) | `test_ct20_invalid_values_rejected[Enabled]` / `[ enabled ]` / `[disabled]` / `[]` / `[123]` / `[True]` / `[SUSPENDED]` | ✅ PASS (7) |
| CT-20 | Configurações válidas aceitas (param.) | `test_ct20_valid_configs_accepted[config0..3]` | ✅ PASS (4) |
| CT-20 | Chave fora do mapa (`safety` não-mapa) rejeitada | `test_ct20_safety_not_a_map_rejected` | ✅ PASS |

### Grupo E — Observabilidade e evidência de execução (`tests/test_participation_evidence.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-14 | Eventos de reconciliação (sucesso/falha) com campos mínimos, sem segredos | `test_ct14_reconcile_success_and_failure_fields_no_secrets` | ✅ PASS |
| CT-21 | Evidência de execução com todos os campos presentes | `test_ct21_rollout_evidence_all_present` | ✅ PASS |
| CT-21 | Commit ausente sinalizado explicitamente | `test_ct21_rollout_evidence_missing_commit_signaled` | ✅ PASS |
| CT-22 | Remoção externa registrada sem inferir autoria | `test_ct22_external_removal_recorded` | ✅ PASS |
| CT-23 | Nenhum evento contém segredos (varredura agregada) | `test_ct23_no_secrets_in_any_event` | ✅ PASS |

### Porta real (`tests/test_participation_adapter.py`)

| Cenário | Teste | Resultado |
|---------|-------|-----------|
| Mapeamento de itens de projeto para quadros configurados | `test_list_participations_maps_items_to_boards` | ✅ PASS |
| Issue ausente retorna lista vazia (não é falha) | `test_list_participations_absent_issue_returns_empty` | ✅ PASS |
| Falha de consulta propaga como erro tipado | `test_list_participations_query_failure_is_typed_error` | ✅ PASS |

**Total #310 (7 arquivos):** 53 passed, 0 failed.

---

## 5. Análise de causa das falhas remanescentes (baseline) — zero regressão

A suíte completa retornou **26 failed, 1657 passed, 17 skipped, 1 xpassed**.

**Prova objetiva de zero regressão.** Isolei a base da branch (`3598c91`,
merge-base entre a branch de trabalho e `origin/main`, anterior aos commits
`ca36195` e `c016de0` de #310) em um `git worktree` separado e executei os 4
arquivos que concentram as falhas:

```
=== BASELINE 3598c91 — tests/test_agent_failure_detection.py tests/test_agent_log_descritivo.py tests/test_docker_compose.py tests/test_dockerfile.py ===
26 failed, 221 passed, 6 skipped, 1 warning
```

- `3598c91` (baseline, sem #310): **26 failed** — mesmos 26 testes, mesmos arquivos.
- branch `feature/310-...` (com #310): **as mesmas 26 falhas** na suíte completa.
- Falhas **novas** introduzidas por #310: **0**.
- Falhas **"corrigidas"** por #310: **0**.

Os arquivos tocados pelo commit `c016de0` (`src/core/participation.py` [novo],
`src/core/participation_reconcile.py` [novo], `src/core/config.py`,
`src/core/board.py`, `src/core/agent.py`, `src/core/sync.py`,
`src/adapters/github_board.py`, `src/__main__.py`, mais os 7 arquivos de teste
novos e a documentação) não incluem nenhum dos 4 arquivos de teste que falham.

Classificação das 26 falhas de baseline — todas pré-existentes e **fora do
escopo de #310** (não tocam classificação de intenção, reconciliação, gate,
migração, contingência, eventos nem evidência de execução):

| Arquivo | Qtd | Causa-raiz | Relação com #310 |
|---------|-----|-----------|-------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de **formato do log diário descritivo** (título entre aspas, posição de `@`, campos no terminal) — já documentado em #306/#325 | Nenhuma — formatação de log em `__main__`; não toca participação |
| `tests/test_agent_failure_detection.py::TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato (linha de início do `execute()`) | Nenhuma |
| `tests/test_docker_compose.py` | 4 | Dependem de ambiente/validação Docker Compose não disponível na execução; divergência de **infra Docker** | Nenhuma |
| `tests/test_dockerfile.py` | 3 | Dockerfile atual não declara `ARG KIRO_CLI_SHA256`/verificação de hash esperada pelos testes; **infra Docker** | Nenhuma |

**Destino:** as 26 falhas pertencem a frentes próprias (formato de log
descritivo e infra Docker), já conhecidas das execuções anteriores (#305,
#306, #308, #325). **Não** são corrigidas aqui — corrigi-las ampliaria o
escopo e esta etapa não altera código. Permanecem como demanda separada do
planejamento. Nenhuma delas classifica #310 como `falha`.

---

## 6. Veredito por critério de aceitação (CA-1..CA-17)

| CA | Critério (resumo) | Veredito | Evidência (CT) |
|----|--------------------|----------|-----------------|
| CA-1 | Reconciliação imediata pós-vínculo preserva hierarquia | **Atendido** | CT-01, CT-01b ✅ |
| CA-2 | Reconciliação tardia (com/sem coluna); evento só após remoção | **Atendido** | CT-02, CT-03 ✅ |
| CA-3 | Rótulo de autorização válido → `authorized`, não removida | **Atendido** | CT-04 ✅ |
| CA-4 | Evidência ambígua/falha transitória → `unresolved`, sem arquivos/remoção, adiada | **Atendido** | CT-05, CT-15, CT-16 ✅ |
| CA-5 | Determinismo entre ordens de avaliação | **Atendido** | CT-06 ✅ |
| CA-6 | Rótulo com quadro inexistente ignorado + aviso | **Atendido** | CT-07 ✅ |
| CA-7 | Intenção confirmada permanece candidata | **Atendido** | CT-08 (origin/authorized) ✅ |
| CA-8 | Intenção não confirmada ignorada + evento deduplicado | **Atendido** | CT-08 (propagated/unresolved/ausente), CT-10 ✅ |
| CA-9 | Gate sem nenhuma chamada de rede | **Atendido** | CT-09 ✅ |
| CA-10 | Migração de legados: unicidade/duplicidade/idempotência/não sobrescrita | **Atendido** | CT-11, CT-12, CT-13 ✅ |
| CA-11 | Evidência de execução no startup; campo ausente sinalizado | **Atendido** | CT-21 ✅ |
| CA-12 | Contingência bloqueia cross-board; mesmo quadro e preexistentes intactos; reversível sem reinício | **Atendido** | CT-18, CT-19 ✅ |
| CA-13 | Valor inválido na chave de contingência rejeitado com mensagem acionável | **Atendido** | CT-20 ✅ |
| CA-14 | Eventos de reconciliação com campos mínimos, sem segredos | **Atendido** | CT-14, CT-23 ✅ |
| CA-15 | Remoção externa registrada sem inferir autoria | **Atendido** | CT-22 ✅ |
| CA-16 | Mesmo mecanismo cobre qualquer par hierárquico, sem hardcode | **Atendido** | CT-02-genérico ✅ |
| CA-17 | Apuração sobre registros (presenças, reconciliações, remoções, despachos, créditos) | **Atendido** (capacidade de apurar via eventos estruturados; o veredito da janela de observação em si é fora de escopo, conforme a issue) | CT-14, CT-17-retentativa, estrutura de eventos (seção 4) ✅ |

**Cobertura:** 17/17 critérios de aceitação com veredito explícito e teste
verde correspondente. Nenhum critério "não verificável" e nenhum "não
atendido".

---

## 7. Aderência à arquitetura

- **Política pura no core, sem I/O de rede:** `classify_participation` em
  `src/core/participation.py` depende apenas dos parâmetros recebidos
  (issue, quadro, rótulos, presenças conhecidas, config); nenhuma chamada de
  rede, nenhum estado mutável compartilhado entre chamadas — CT-06/CT-09. ✅
- **Contrato de porta explícito:** `list_participations`/`remove_from_board`
  são o único canal de I/O consumido pela reconciliação
  (`src/core/participation_reconcile.py`); a implementação real usa
  exclusivamente GraphQL (`list_participations` em
  `src/adapters/github_board.py`), confirmado por
  `tests/test_participation_adapter.py`. ✅
- **Erro tipado, nunca silenciado:** `ParticipationQueryError` propaga em
  falha de consulta/remoção (RN-09); nenhum caminho de código a converte em
  lista vazia silenciosa ou aviso que descarta o caso — CT-05/CT-15. ✅
- **Hierarquia nunca tocada pela reconciliação (RN-03):** `remove_from_board`
  opera só sobre o item de projeto; nenhuma chamada de
  `set_parent`/`set_children` ocorre nos caminhos de reconciliação — CT-01,
  CT-01b, CT-15. ✅
- **Gate sem rede (RNF-04):** `gate_allows`/`gate_keep` em
  `src/core/participation.py` leem somente `issue["participation_intent"]` do
  dict do snapshot; o teste `test_ct09_gate_runs_without_network` usa um dublê
  cujo qualquer método levanta `AssertionError` se chamado, e passa. ✅
- **Determinismo (RNF-05):** mesmo estado de entrada produz o mesmo resultado
  independentemente da ordem de avaliação — CT-06, verificado por ordens
  embaralhadas e invertidas. ✅
- **Generalização sem hardcode (RNF-07):** o par sintético
  `squads`→`iniciativas`, inexistente no código de produção, é classificado e
  reconciliado pelo mesmo mecanismo que `epicos`→`historias` e
  `historias`→`tarefas` — CT-02-genérico, sem condição `if board_id == ...`
  no código avaliado. ✅
- **Contingência relida sem cache (RNF-06):** `cross_board_links_suspended`
  relê o `pipe.yml` do disco a cada avaliação; CT-19 comprova efeito imediato
  sem reinício do processo de teste. ✅
- **Validação de config no padrão da casa:** `safety.cross_board_parent_links`
  segue o padrão `ConfigError` citando a chave e o valor recebido, comparação
  exata sem normalizar caixa/espaços — CT-20 (7 valores inválidos + 4 válidos
  parametrizados). ✅
- **Estado protegido:** `.pipe/participationPending.json` é estado interno de
  retentativa, fora do snapshot, seguindo o precedente de
  `.pipe/agentCircuitBreak.json`; adicionado a `PROTECTED_PATHS` em
  `src/core/agent.py` (confirmado por grep — 1 ocorrência de
  `participationPending`/padrão correspondente no módulo). Nenhum teste desta
  entrega ou da suíte geral de proteção de estado (`test_build_prompt_protected_paths.py`)
  falhou com a mudança. ✅
- **Sem segredos nos eventos (RNF-09):** CT-14 e CT-23 plantam um marcador de
  corpo e um token fictício e varrem todos os eventos
  `participation_*`/`dispatch_blocked_unconfirmed_intent`/
  `cross_board_link_blocked`/`rollout_evidence` emitidos — nenhuma ocorrência
  do marcador ou do token. ✅
- **Isolamento de teste (anti-#106):** os casos exercitam o código real com
  `BoardPort` fake e `monkeypatch.chdir(tmp_path)`; nenhum `monkeypatch` do
  símbolo sob teste (`classify_participation`, `reconcile_after_link`,
  `reconcile_remote_presence`, `gate_allows` não são substituídos por dublê em
  nenhum teste). ✅

Nenhuma violação de arquitetura detectada.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 53 testes novos de #310
  passam; as 26 falhas da suíte completa são baseline alheio, provadamente
  idêntico ao commit base `3598c91` (zero regressão), isolado via `git
  worktree`.
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos
  especificados em `test-cases.md` (CT-01 a CT-23, incluindo variantes) são
  coerentes com os 17 critérios de aceitação, exercitam o código real e
  passam integralmente — a implementação satisfez os casos escritos antes
  dela, sem necessidade de ajuste.
- Nenhuma alteração de código ou de caso de teste foi feita nesta etapa.

— Camila Rocha - Engenheira de Qualidade (QA)
