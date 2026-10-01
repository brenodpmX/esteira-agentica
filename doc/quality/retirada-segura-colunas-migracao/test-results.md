# Resultados de Teste — Retirada segura de colunas de board com migração de issues, bloqueio, retomada e evidência

- **Issue:** #305 — "Retirada segura de colunas de board com migração de issues,
  bloqueio, retomada e evidência"
- **Etapa:** Execução de Testes
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/305-retirada-segura-colunas-migracao`
- **Commit sob teste:** `2113552` — feat(305): retirada segura de colunas de
  board com migracao, bloqueio, retomada e evidencia
- **Base de comparação:** `origin/main` @ `4f569cf`

> Este documento registra a execução dos casos especificados em
> `test-cases.md` (CT-01 a CT-17 e sub-casos), com veredito e análise de causa
> das falhas remanescentes. Nenhum código ou caso de teste foi alterado nesta
> etapa.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

A implementação da retirada segura de colunas (#305) está **efetiva na branch de
trabalho** e **coberta por 47 testes automatizados verdes** que atravessam a
política de decisão (núcleo), a validação de forma da configuração, o contrato do
adapter (preparação não destrutiva vs. contração), a ordem do full sync e a
evidência estruturada por tentativa. Todos os 17 cenários obrigatórios
(CT-01..CT-17) e seus sub-casos têm teste correspondente passando.

As **26 falhas** remanescentes na suíte completa são **baseline pré-existente**,
provadamente **idênticas** em `origin/main @ 4f569cf` (**zero regressão**),
**alheias** ao escopo de #305 (débito de **infra Docker** e de **formato do log
descritivo**). Não constituem reprovação de código desta entrega.

Portanto **não** há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste` (volta ao QA): os casos são coerentes com os critérios de
aceitação, exercitam o código real (sem `monkeypatch` do símbolo sob teste) e
passam integralmente.

---

## 2. Ambiente de execução

- Python 3.12.14, pytest 9.1.1, pluggy 1.6.0
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso real): os
  casos de #305 usam um `BoardPort` fake controlável, conforme as convenções
  fixadas no `test-cases.md`.
- Comandos:
  - `python -m pytest tests/test_column_withdrawal.py tests/test_column_migrations_config.py tests/test_github_board_contract.py tests/test_full_sync_order.py tests/test_column_migration_evidence.py -v` (os 5 arquivos de #305)
  - `python -m pytest -q` (suíte completa)
  - comparação de baseline em **worktree limpo** de `origin/main`
    (`git worktree add /tmp/baseline-305 origin/main`), com diff exato do conjunto
    de falhas.

---

## 3. Resultado da suíte completa

```
26 failed, 1362 passed, 17 skipped, 1 xpassed, 1 warning in 47.02s
```

- **1362 passed** — inclui os **47 testes novos** de #305.
- **26 failed** — baseline pré-existente (ver seção 5).
- **17 skipped, 1 xpassed** — inalterados em relação ao baseline.

---

## 4. Resultados por caso de teste (CT-01..CT-17)

Execução dirigida dos 5 arquivos de #305: **47 passed in 0.46s**. Mapeamento
caso → teste → resultado:

### Grupo A — Decisão e drenagem (`tests/test_column_withdrawal.py`)

| CT | Critério / cenário | Teste | Resultado |
|----|--------------------|-------|-----------|
| CT-01 | Retirada de coluna vazia (`completed`, `initial_count=0`) | `test_ct01_empty_column_withdrawn_completed` | ✅ PASS |
| CT-01b | Vazia não contrai sem leitura de confirmação imediata | `test_ct01b_empty_reads_before_contract` | ✅ PASS |
| CT-02 | Migração de coluna ocupada com destino válido (`moved_count=N`, `remaining_count=0`) | `test_ct02_occupied_migrated_then_contracted` | ✅ PASS |
| CT-02b | Contração preserva as demais opções | `test_ct02b_contract_preserves_other_options` | ✅ PASS |
| CT-03 | Preservação de atributos (só `move_issue`/`Status`) | `test_ct03_only_move_issue_called` | ✅ PASS |
| CT-04 | Destino ausente → `blocked`, `destino_ausente` | `test_ct04_missing_destination_blocked` | ✅ PASS |
| CT-05a | Destino inexistente → `destino_inexistente` | `test_ct05a_destination_inexistente` | ✅ PASS |
| CT-05b | Destino em outro board → `destino_mesmo_board_invalido` | `test_ct05b_destination_other_board` | ✅ PASS |
| CT-05c | Destino igual à origem → `destino_e_origem` | `test_ct05c_destination_equals_source` | ✅ PASS |
| CT-06 | Destinos em ciclo (ambos bloqueados) → `destino_tambem_retirado` | `test_ct06_cycle_both_blocked` | ✅ PASS |
| CT-06 | Destino assimétrico válido é retirado | `test_ct06_asymmetric_destination_withdrawn` | ✅ PASS |
| CT-07 | Issue chega durante a drenagem (migrada antes de contrair) | `test_ct07_issue_arrives_during_drain` | ✅ PASS |
| CT-08 | Falha parcial e retomada (M de N; move só N−M) | `test_ct08_partial_failure_then_resume` | ✅ PASS |
| CT-09 | Falhas sucessivas: não perda / não duplicação | `test_ct09_successive_failures_no_loss_no_dup` | ✅ PASS |
| CT-10 | Sem progresso → `interrupted`, `sem_progresso` | `test_ct10_no_progress_interrupted` | ✅ PASS |
| CT-11 | Isolamento entre origens | `test_ct11_isolation_between_sources` | ✅ PASS |
| CT-11 | Isolamento entre boards | `test_ct11_isolation_between_boards` | ✅ PASS |
| CT-15 | Exatamente N mutações de `Status` | `test_ct15_exactly_n_status_mutations` | ✅ PASS |
| CT-16 | Idempotência: reexecução sem movimentos extras | `test_ct16_idempotent_no_extra_moves` | ✅ PASS |
| CT-RL-01 | Rate limit (`PenaltyException`) propaga e não contrai | `test_ct_rl01_penalty_propagates_and_no_contract` | ✅ PASS |
| — | Reconciliação prepara estrutura antes de contrair | `test_reconcile_structure_prepares_first` | ✅ PASS |

### Grupo D — Validação de forma da config (`tests/test_column_migrations_config.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-12a | Mapa de destinos válido aceito | `test_ct12a_valid_map_accepted` | ✅ PASS |
| CT-12a | Mapa válido com múltiplas entradas | `test_ct12a_valid_map_multiple_entries` | ✅ PASS |
| CT-12b | Ausência do mapa é válida | `test_ct12b_absent_map_valid` | ✅ PASS |
| CT-12b | Ausência válida em `validate_boards` | `test_ct12b_absent_map_in_full_boards_validation` | ✅ PASS |
| CT-12c | Inválidos rejeitados (7 parametrizações) | `test_ct12c_invalid_rejected[...]` | ✅ PASS (7/7) |
| CT-12c | `ConfigError` cita a entrada que falhou | `test_ct12c_invalid_cites_entry` | ✅ PASS |
| CT-12c | Inválido propaga por `validate_boards` | `test_ct12c_invalid_propagates_through_validate_boards` | ✅ PASS |

### Grupo C — Contrato do adapter (`tests/test_github_board_contract.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-13a | Preparação adiciona novo, preserva coluna retirada | `test_ct13a_prepare_adds_new_preserves_withdrawn` | ✅ PASS |
| CT-13a | Preparação é no-op quando tudo presente | `test_ct13a_prepare_noop_when_all_present` | ✅ PASS |
| CT-13b | Preparação cria campo `Status` ausente | `test_ct13b_prepare_creates_field_when_absent` | ✅ PASS |
| CT-13b | Preparação preserva opção legada extra | `test_ct13b_prepare_preserves_extra_legacy_option` | ✅ PASS |
| CT-02b | Contração remove só a origem, preserva ids | `test_ct02b_contract_removes_only_source_preserves_ids` | ✅ PASS |
| — | `remote_columns` lê as opções publicadas | `test_remote_columns_reads_published_options` | ✅ PASS |

### Grupo — Ordem do full sync (`tests/test_full_sync_order.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-14a | Reconciliar antes de gravar o snapshot | `test_ct14a_reconcile_before_snapshot` | ✅ PASS |
| CT-14b | Snapshot inclui origem retida; diretório local preservado | `test_ct14b_snapshot_includes_retained_source_and_preserves_dir` | ✅ PASS |
| CT-14c | Falha de reconciliação não sobrescreve snapshot anterior | `test_ct14c_reconcile_failure_preserves_prior_snapshot` | ✅ PASS |

### Grupo — Evidência e segurança (`tests/test_column_migration_evidence.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-OBS-01 | Campos e níveis de log (INFO/WARNING) | `test_ct_obs01_fields_and_levels` | ✅ PASS |
| CT-OBS-02 | Mensagem de `blocked` auto-contida | `test_ct_obs02_blocked_message_self_contained` | ✅ PASS |
| CT-17 | Contagens por execução, não acumuladas | `test_ct17_per_execution_counts_not_accumulated` | ✅ PASS |
| CT-SEC-01 | Evidência sem conteúdo sensível (RNF-10) | `test_ct_sec01_no_sensitive_content_in_evidence` | ✅ PASS |

**Total #305:** 47 passed, 0 failed.

---

## 5. Análise de causa das falhas remanescentes (baseline) — zero regressão

A suíte completa retornou **26 failed, 1362 passed, 17 skipped, 1 xpassed**.

**Prova objetiva de zero regressão.** Executei os 4 arquivos que concentram as
falhas na branch de trabalho e, em paralelo, em um **worktree limpo** de
`origin/main @ 4f569cf` (base das branches de #305, anterior aos commits `7971eb3`
e `2113552`). Comparei o conjunto de IDs de teste que falham em cada lado com
`diff`:

```
=== diff (vazio = idêntico) ===
IDENTICAL: 26 failures match exactly
```

- `origin/main @ 4f569cf`: **26 failed, 221 passed, 6 skipped** (nos 4 arquivos).
- branch `feature/305-...`: **mesmas 26 falhas**, byte a byte.
- Falhas **novas** introduzidas por #305: **0**.
- Falhas **"corrigidas"** por #305: **0**.

Classificação das 26 falhas de baseline — todas pré-existentes e **fora do escopo
de #305** (não tocam o núcleo de retirada de coluna, a config, o adapter de
preparação/contração nem o full sync reordenado):

| Arquivo | Qtd | Causa-raiz | Relação com #305 |
|---------|-----|-----------|-------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de **formato do log diário descritivo** (título entre aspas, posição de `@`, campos no terminal) | Nenhuma — formatação de log em `__main__`; não toca retirada de coluna |
| `tests/test_agent_failure_detection.py::TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato (linha de início do `execute()`) | Nenhuma |
| `tests/test_docker_compose.py` | 4 | Dependem de ambiente/validação Docker Compose não disponível na execução; divergência de **infra Docker** | Nenhuma |
| `tests/test_dockerfile.py` | 3 | Dockerfile atual não declara `ARG KIRO_CLI_SHA256`/verificação de hash esperada pelos testes; **infra Docker** | Nenhuma |

**Destino:** as 26 falhas pertencem a frentes próprias (formato de log descritivo
e infra Docker), já conhecidas da verificação do bloco 1 (#314). **Não** são
corrigidas aqui — corrigi-las ampliaria o escopo e esta etapa não altera código.
Permanecem como demanda separada do planejamento. Nenhuma delas classifica #305
como `falha`.

---

## 6. Veredito por critério de aceitação (CA-1..CA-14)

| CA | Critério (resumo) | Veredito | Evidência (CT) |
|----|-------------------|----------|----------------|
| CA-1 | Retirada de coluna vazia | **Atendido** | CT-01, CT-01b ✅ |
| CA-2 | Migração de coluna ocupada com destino válido | **Atendido** | CT-02, CT-02b, CT-16 ✅ |
| CA-3 | Preservação de atributos na migração | **Atendido** | CT-03 (só `move_issue`) ✅ |
| CA-4 | Bloqueio por destino ausente/inválido | **Atendido** | CT-04, CT-05a/b/c, CT-06 ✅ |
| CA-5 | Issue que chega durante a drenagem | **Atendido** | CT-07 ✅ |
| CA-6 | Falha parcial e retomada | **Atendido** | CT-08, CT-16 ✅ |
| CA-7 | Não perda / não duplicação | **Atendido** | CT-09 ✅ |
| CA-8 | Interrupção por ausência de progresso | **Atendido** | CT-10 (`sem_progresso`) ✅ |
| CA-9 | Isolamento entre origens | **Atendido** | CT-11 (origens e boards) ✅ |
| CA-10 | Preparação não destrutiva | **Atendido** | CT-13a, CT-13b ✅ |
| CA-11 | Validação de forma da configuração | **Atendido** | CT-12a/b/c (cita o caminho) ✅ |
| CA-12 | Evidência consultável por tentativa | **Atendido** | CT-OBS-01/02, CT-17, CT-SEC-01 ✅ |
| CA-13 | Ordem do full sync e snapshot efetivo | **Atendido** | CT-14a/b/c ✅ |
| CA-14 | Contagem de chamadas (N mutações) | **Atendido** | CT-15, CT-RL-01 ✅ |

**Cobertura:** 14/14 critérios de aceitação com veredito explícito e teste verde
correspondente. Nenhum critério "não verificável" e nenhum "não atendido".

---

## 7. Aderência à arquitetura

- **Política no núcleo de decisão (não no adapter):** a lógica de
  validar/drenar/confirmar/contrair está em `src/core/column_withdrawal.py`; o
  adapter só expõe primitivas (`prepare_structure`, `contract_column`,
  `remote_columns`). Conforme o item de "Riscos" da issue que veda mover a decisão
  para a camada de acesso. ✅
- **Preparação estritamente aditiva vs. contração explícita:** CT-13 comprova que
  `prepare_structure` nunca remove opções e preserva ids; a contração só ocorre
  após confirmação de origem vazia (CT-01b/CT-02). ✅
- **Sem estado persistente paralelo:** a retomada deriva do estado remoto
  (CT-08/CT-09), sem journal/fila nova — conforme o veto da issue. ✅
- **Isolamento de teste (anti-#106):** os casos usam `BoardPort` fake e exercitam
  o código real; não há `monkeypatch` do símbolo sob teste. ✅
- **Compatibilidade (RNF-09):** boards sem `column-migrations` mantêm o
  comportamento vigente — a suíte de sync existente (`test_sync_*`,
  `test_startup`, etc.) permanece verde. ✅

Nenhuma violação de arquitetura detectada.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 47 testes de #305 passam e as 26
  falhas da suíte são baseline alheio, provadamente idênticas a `origin/main`
  (zero regressão).
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos
  CT-01..CT-17 são coerentes com os 14 critérios de aceitação, exercitam o código
  real e passam integralmente.
