# Resultados de Teste — Circuit-breaker de sincronismo com escalação ao agente e encerramento controlado

- **Issue:** #309 — "Circuit-breaker de sincronismo com escalação ao agente e
  encerramento controlado"
- **Etapa:** Execução de Testes
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-11-04
- **Branch:** `feature/309-circuit-breaker-sincronismo-escalacao-agente`
- **Commit sob teste:** `88adcce` — feat(309): circuit-breaker de sincronismo
  com escalação ao agente e encerramento controlado
- **Base de comparação:** `f76951d` — Merge pull request #340 (base da
  branch, anterior a qualquer trabalho de #309; confirmado via
  `git merge-base main HEAD`)

> Este documento registra a execução dos casos especificados em
> `test-cases.md` (CT-01..CT-22, incluindo CT-08b e CT-17b, cobrindo os 14
> critérios de aceitação da issue), com veredito e análise de causa das
> falhas remanescentes. Nenhum código, caso de teste ou arquivo da suíte foi
> alterado nesta etapa.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

O circuit-breaker de sincronismo (#309) — bloqueio por issue e por
plataforma, meio-aberto, escalação ao agente dedicado, encerramento
controlado, descida sempre completa, idempotência de relação de bloqueio
existente, gravação de progresso antes de propagar falha, exclusão de rate
limit da contagem e absorção da remediação E4 — está **implementado na
branch de trabalho** e **coberto por testes automatizados verdes** que
exercitam o núcleo real (`src/core/sync_circuit_breaker.py`), sua integração
com `apply_changes`/`sync.py`, a escalação em `src/__main__.py` e a validação
de configuração em `config.py`.

- **90 testes passam** nos arquivos pertinentes à mudança:
  - `tests/test_sync_circuit_breaker.py` — núcleo e integração (CT-01..CT-22,
    CT-08b, CT-17b incluídos nas suas respectivas classes);
  - `tests/test_sync_circuit_breaker_config.py` — validação de forma e
    defaults (CT-17/CT-17b);
  - `tests/test_remediation_loop.py` — `classify_error` (não regressão,
    classificação inalterada apesar da migração de dono da escalação);
  - `tests/test_sync_unico_deps.py` — descida sempre `fullsync`/com
    dependências reconciliadas (não regressão/CT-12);
  - `tests/test_composicao_camadas_medicao.py` — não regressão da composição
    de prompt/contexto (arquivo tocado pelo commit por efeito colateral de
    medição, sem relação funcional direta com o circuit-breaker).
- Os **14 critérios de aceitação** (CA-1..CA-14) têm teste correspondente
  verde (ver seção 6).

As **26 falhas e 13 erros** remanescentes na suíte completa são **baseline
pré-existente**, provadamente **idênticas** em `f76951d` (**zero regressão**),
**alheias** ao escopo de #309 (débito de **formato do log diário descritivo**
e de **infra Docker/Dockerfile**, já conhecido de entregas anteriores — #306).
Não constituem reprovação de código desta entrega.

Portanto **não** há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste` (volta ao QA): os casos são coerentes com os
critérios de aceitação, exercitam o código real com `BoardPort` fake, relógio
controlável e dispatch espião ao agente dedicado — sem `monkeypatch` do
símbolo sob teste (lição do incidente #106) — e passam integralmente.

---

## 2. Ambiente de execução

- Python 3.12.16, pytest 9.2.0
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso `kiro-cli`
  real): os casos exercitam o núcleo via `BoardPort` fake espião, relógio
  controlável (`monkeypatch` de `time.time`) e dispatch espião ao agente
  dedicado, conforme as convenções fixadas no `test-cases.md`.
- Comandos:
  - `python -m pytest tests/test_sync_circuit_breaker.py
    tests/test_sync_circuit_breaker_config.py tests/test_remediation_loop.py
    tests/test_sync_unico_deps.py tests/test_composicao_camadas_medicao.py -v`
    (os 5 arquivos pertinentes à mudança)
  - `python -m pytest -q` (suíte completa)
  - comparação de baseline por `git worktree add` de `main` (`f76951d`,
    confirmado idêntico ao commit-base da branch via `git merge-base`),
    rodando a suíte completa nesse worktree e confrontando o conjunto de
    falhas/erros com o obtido na branch de trabalho.

---

## 3. Resultado da suíte completa

Branch `feature/309-circuit-breaker-sincronismo-escalacao-agente`:

```
26 failed, 1768 passed, 17 skipped, 1 xpassed, 1 warning, 13 errors in 73.26s (0:01:13)
```

Baseline `main` (`f76951d`, worktree isolado, sem as mudanças de #309):

```
26 failed, 1707 passed, 17 skipped, 1 xpassed, 1 warning, 13 errors in 75.68s (0:01:15)
```

- **1768 passed** na branch vs. **1707 passed** no baseline: diferença de
  **61 testes**, correspondente aos testes novos/estendidos da entrega
  (`test_sync_circuit_breaker.py`, `test_sync_circuit_breaker_config.py` e os
  ajustes em `test_remediation_loop.py`/`test_sync_unico_deps.py`/
  `test_composicao_camadas_medicao.py`).
- **26 failed, 13 errors** — idênticos em quantidade, arquivo e nome de teste
  entre branch e baseline (ver seção 5).
- **17 skipped, 1 xpassed** — inalterados em relação ao baseline.

Execução dirigida dos 5 arquivos pertinentes à mudança:

```
90 passed in 1.34s
```

---

## 4. Resultados por caso de teste

Mapeamento caso → teste → resultado. Todos os casos do `test-cases.md` têm
teste automatizado verde correspondente em `tests/test_sync_circuit_breaker.py`
(classes nomeadas pelo próprio grupo temático do documento de casos) e
`tests/test_sync_circuit_breaker_config.py`.

### Grupo A — Bloqueio de issue por falhas de sincronismo

| CT | Critério / cenário | Teste | Resultado |
|----|--------------------|-------|-----------|
| CT-01 | Bloqueio ao atingir `issue.max_failures` falhas consecutivas | `TestIssueBlock::test_ct01_bloqueia_apos_max_failures` | ✅ PASS |
| CT-02 | Issue bloqueada: mudanças retidas na fila sem reprocessamento | `TestIssueBlock::test_ct02_issue_bloqueada_retem_item_sem_reprocessar` | ✅ PASS |
| CT-19 | Borda exata da duração do bloqueio | `TestIssueBlock::test_ct19_borda_da_duracao_do_bloqueio` | ✅ PASS |
| — | Duração vem da configuração (parametrização) | `TestIssueBlock::test_duracao_vem_da_configuracao` | ✅ PASS |
| — | Log de bloqueio com campos mínimos | `TestIssueBlock::test_log_de_bloqueio_tem_campos_minimos` | ✅ PASS |

### Grupo B — Meio-aberto: expiração, fechamento e reabertura

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-03 | Expiração do bloqueio leva a meio-aberto e retentativa | `TestHalfOpen::test_ct03_expiracao_leva_a_meio_aberto_e_retenta` | ✅ PASS |
| CT-04 | Amostra de sucessos em meio-aberto fecha o circuito | `TestHalfOpen::test_ct04_amostra_de_sucessos_fecha_o_circuito` | ✅ PASS |
| — | `success_threshold` vem da configuração | `TestHalfOpen::test_success_threshold_vem_da_configuracao` | ✅ PASS |
| CT-05 | Falha em meio-aberto reabre o bloqueio | `TestHalfOpen::test_ct05_falha_em_meio_aberto_reabre_o_bloqueio` | ✅ PASS |

### Grupo C — Bloqueio de plataforma

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-06 | Bloqueio de plataforma com issues distintas na janela | `TestPlatformBlock::test_ct06_bloqueia_plataforma_com_issues_distintas` | ✅ PASS |
| — | Mesma issue reaberta conta como uma issue distinta | `TestPlatformBlock::test_mesma_issue_reaberta_conta_como_uma` | ✅ PASS |
| — | Issues fora da janela não contam | `TestPlatformBlock::test_issues_fora_da_janela_nao_contam` | ✅ PASS |
| CT-07 | Plataforma bloqueada não processa a fila | `TestPlatformBlock::test_ct07_plataforma_bloqueada_nao_processa_fila` | ✅ PASS |
| — | Plataforma meio-aberta fecha com sucessos | `TestPlatformBlock::test_plataforma_meio_aberta_fecha_com_sucessos` | ✅ PASS |
| CT-20 | Plataformas distintas são independentes | `TestPlatformBlock::test_ct20_plataformas_distintas_sao_independentes` | ✅ PASS |

### Grupo D — Escalação ao agente dedicado e encerramento controlado

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-08 | Escala uma vez após `issue.max_blocks` | `TestEscalation::test_ct08_escala_uma_vez_apos_max_blocks` | ✅ PASS |
| — | Agente dedicado vem da configuração | `TestEscalation::test_agente_dedicado_vem_da_configuracao` | ✅ PASS |
| CT-09 | Sync retentado no ciclo seguinte à correção | `TestEscalation::test_ct09_sync_e_retentado_no_ciclo_seguinte` | ✅ PASS |
| CT-10 | Falha após correção encerra o processo | `TestEscalation::test_ct10_falha_apos_correcao_encerra` | ✅ PASS |
| CT-11 | Registro do encerramento com os 5 campos mínimos | `TestEscalation::test_ct11_registro_do_encerramento_completo` | ✅ PASS |
| CT-08b | Sem segunda escalação no mesmo episódio | `TestEscalation::test_ct08b_sem_segunda_escalacao_no_mesmo_episodio` | ✅ PASS |
| — | Sucesso após correção fecha e zera o episódio | `TestEscalation::test_sucesso_apos_correcao_fecha_e_zera_episodio` | ✅ PASS |
| — | Prompt de escalação contém fato + log + instrução | `TestEscalationPrompt::test_contem_fato_log_e_instrucao` | ✅ PASS |
| — | `main()`: fatal encerra com código ≠ 0 | `TestFatalNoMain::test_fatal_encerra_com_codigo_diferente_de_zero` | ✅ PASS |
| — | `escalate_pending` aciona o agente com erro completo | `TestEscalatePending::test_aciona_agente_dedicado_com_erro_completo` | ✅ PASS |
| — | Agente de escalação não configurado encerra | `TestEscalatePending::test_agente_nao_configurado_encerra` | ✅ PASS |
| — | Issue não resolvível na escalação encerra | `TestEscalatePending::test_issue_nao_resolvivel_encerra` | ✅ PASS |

### Grupo E — Descida sempre completa e idempotência de relação existente

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-12 | `get_issue` sem modo parcial | `TestDescidaCompleta::test_ct12_get_issue_nao_tem_modo_parcial` | ✅ PASS |
| CT-12 | Descida (`_apply_*_down`) busca issue sem flag de modo | `TestDescidaCompleta::test_ct12_apply_down_busca_issue_sem_flag` | ✅ PASS |
| CT-13 | Relação existente é sucesso e processa as seguintes | `TestRelacaoExistente::test_ct13_relacao_existente_e_sucesso_e_continua` | ✅ PASS |
| — | Outros erros continuam propagando normalmente | `TestRelacaoExistente::test_outros_erros_continuam_propagando` | ✅ PASS |
| — | `set_blocks` com relação existente também é sucesso | `TestRelacaoExistente::test_set_blocks_relacao_existente_e_sucesso` | ✅ PASS |

### Grupo F — Persistência de progresso do corpo antes de propagar falha

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-14 | `body_mtime` gravado antes de propagar a exceção | `TestProgressoGravadoEmFalha::test_ct14_body_mtime_gravado_antes_de_propagar` | ✅ PASS |

### Grupo G — Rate limit fora do circuit-breaker

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-15 | Rate limit não incrementa contadores | `TestRateLimit::test_ct15_rate_limit_nao_incrementa_contadores` | ✅ PASS |
| CT-16 | Rate limit intercalado não acelera o bloqueio | `TestRateLimit::test_ct16_rate_limit_intercalado_nao_acelera_bloqueio` | ✅ PASS |

### Grupo H — Configuração e defaults (`tests/test_sync_circuit_breaker_config.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-17 | Ausência aceita e aplica defaults (7 sub-casos param.) | `TestDefaults::test_ct17_ausencia_aceita_e_aplica_defaults[config0..config6]` | ✅ PASS (7) |
| — | Valores default sem bloco | `TestDefaults::test_valores_default_sem_bloco` | ✅ PASS |
| — | Valores presentes são respeitados | `TestDefaults::test_valores_presentes_sao_respeitados` | ✅ PASS |
| CT-17b | Rejeição citando o caminho (13 sub-casos param.) | `TestInvalid::test_ct17b_rejeita_citando_o_caminho[block0..block12]` | ✅ PASS (13) |
| — | Bloco não-mapa rejeitado | `TestInvalid::test_bloco_nao_mapa_e_rejeitado` | ✅ PASS |
| — | Agente de escalação precisa existir em `agents` | `TestInvalid::test_agente_de_escalacao_precisa_existir_em_agents` | ✅ PASS |

### Grupo I — Absorção da remediação E4

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-18 | Erro corrigível escala pelo circuit-breaker | `TestE4Absorbed::test_ct18_erro_corrigivel_escala_pelo_circuit_breaker` | ✅ PASS |
| — | Mecanismo antigo (`RemediationSignal`/`RemediationFailStop`) foi removido | `TestE4Absorbed::test_mecanismo_antigo_foi_removido` | ✅ PASS |

### Grupo J — Interação com `sync.max_attempts`

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| — | Dead-letter por `max_attempts` libera o contador do circuit-breaker | `TestMaxAttemptsInteraction::test_dead_letter_por_max_attempts_libera_o_contador` | ✅ PASS |
| — | Bloqueio reinicia as tentativas do item (`attempts=0`) | `TestMaxAttemptsInteraction::test_bloqueio_reinicia_tentativas_do_item` | ✅ PASS |

### Grupo K — Persistência configurável e segurança do estado

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-22 | `memory` não sobrevive a reinício | `TestPersistence::test_ct22_memory_nao_sobrevive_a_reinicio` | ✅ PASS |
| CT-22 | `file` sobrevive a reinício (sub-caso de controle) | `TestPersistence::test_ct22_file_sobrevive_a_reinicio` | ✅ PASS |
| — | Estado corrompido reinicia sem derrubar a esteira | `TestPersistence::test_estado_corrompido_reinicia_sem_derrubar` | ✅ PASS |
| CT-21 | Estado não expõe conteúdo sensível; arquivo protegido | `TestPersistence::test_ct21_estado_nao_expoe_conteudo_e_arquivo_e_protegido` | ✅ PASS |

### Grupo L — Fila acionável (apoio ao loop principal)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| — | Fila só com itens bloqueados não é acionável | `TestQueueActionable::test_fila_so_com_itens_bloqueados_nao_e_acionavel` | ✅ PASS |
| — | Fila com item livre é acionável | `TestQueueActionable::test_fila_com_item_livre_e_acionavel` | ✅ PASS |

### Grupo M — Não regressão (`classify_error`, descida com deps, composição)

| Arquivo | Teste | Resultado |
|---------|-------|-----------|
| `tests/test_remediation_loop.py` | `TestClassifyError::test_422_e_corrigivel` | ✅ PASS |
| `tests/test_remediation_loop.py` | `TestClassifyError::test_definitivo_tem_precedencia_sobre_corrigivel` | ✅ PASS |
| `tests/test_remediation_loop.py` | `TestClassifyError::test_issue_fantasma_e_definitivo` | ✅ PASS |
| `tests/test_remediation_loop.py` | `TestClassifyError::test_outro_erro_e_transitorio` | ✅ PASS |
| `tests/test_remediation_loop.py` | `TestClassifyError::test_penalty_e_rate_limit` | ✅ PASS |
| `tests/test_remediation_loop.py` | `TestClassifyError::test_validation_failed_e_corrigivel` | ✅ PASS |
| `tests/test_sync_unico_deps.py` | `test_ct02b_change_down_is_fullsync` | ✅ PASS |
| `tests/test_sync_unico_deps.py` | `test_ct02b_dependencies_reconciled_after_apply` | ✅ PASS |
| `tests/test_composicao_camadas_medicao.py` | 9 testes (reducao/instrucoes/tokens) | ✅ PASS (9) |

**Total #309 (5 arquivos pertinentes):** 90 passed, 0 failed.

---

## 5. Análise de causa das falhas remanescentes (baseline) — zero regressão

A suíte completa retornou **26 failed, 1768 passed, 17 skipped, 1 xpassed, 13
errors** na branch de trabalho.

**Prova objetiva de zero regressão.** Executei a suíte completa em um
`git worktree` isolado apontando para `main` (`f76951d`) — confirmado, via
`git merge-base main HEAD`, como exatamente o commit-base da branch, anterior
a qualquer trabalho de #309:

```
=== BASELINE main (f76951d), suíte completa ===
26 failed, 1707 passed, 17 skipped, 1 xpassed, 1 warning, 13 errors in 75.68s
```

- `main` (`f76951d`, baseline, sem #309): **26 failed, 13 errors** — mesmos
  arquivos e mesmos nomes de teste, conferidos linha a linha contra a saída da
  branch.
- branch `feature/309-...` (com #309): **as mesmas 26 falhas e 13 erros** na
  suíte completa.
- Falhas/erros **novos** introduzidos por #309: **0**.
- Falhas/erros **"corrigidos"** por #309: **0**.
- Testes adicionais que passam na branch e não existem no baseline: **61**
  (90 testes pertinentes à mudança, descontados os 29 testes reaproveitados/
  ajustados que já existiam e continuam contados em ambos os lados pelas
  categorias que não mudaram de nome).

Classificação das 26 falhas + 13 erros de baseline — todas pré-existentes e
**fora do escopo de #309** (não tocam contadores de falha de sync, bloqueio
de issue/plataforma, meio-aberto, escalação, encerramento controlado, descida
completa, idempotência de relação ou gravação de progresso):

| Arquivo | Qtd (fail+error) | Causa-raiz | Relação com #309 |
|---------|-------------------|-----------|-------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de **formato do log diário descritivo** (título entre aspas, posição de `@`, campos no terminal) — já documentado em #306/#308 | Nenhuma — formatação de log de execução de agente em `__main__`; não toca o circuit-breaker de sync |
| `tests/test_agent_failure_detection.py::TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato (linha de início do `execute()`) | Nenhuma |
| `tests/test_docker_compose.py` | 4 | Dependem de ambiente/validação Docker Compose não disponível na execução; divergência de **infra Docker** | Nenhuma |
| `tests/test_dockerfile.py` (failed) | 3 | Dockerfile atual não declara `ARG KIRO_CLI_SHA256`/verificação `sha256sum` esperada pelos testes; **infra Docker** | Nenhuma |
| `tests/test_dockerfile.py::TestDockerIntegracao` (error) | 13 | Erros de coleta/fixture de integração Docker (`docker build` não executável no ambiente de teste) | Nenhuma |

**Destino:** as 26 falhas e 13 erros pertencem a frentes próprias (formato de
log descritivo e infra Docker), já conhecidas das execuções anteriores (#305,
#306, #308). **Não** são corrigidas aqui — corrigi-las ampliaria o escopo e
esta etapa não altera código. Permanecem como demanda separada do
planejamento. Nenhuma delas classifica #309 como `falha`.

---

## 6. Veredito por critério de aceitação (CA-1..CA-14)

| CA | Critério (resumo) | Veredito | Evidência (CT) |
|----|--------------------|----------|----------------|
| CA-1 | `issue.max_failures` falhas consecutivas bloqueiam a issue; fila retida | **Atendido** | CT-01, CT-02 ✅ |
| CA-2 | Bloqueio expira → meio-aberto → retentativa no ciclo seguinte | **Atendido** | CT-03 ✅ |
| CA-3 | Amostra de sucessos em meio-aberto fecha o circuito e zera contadores | **Atendido** | CT-04 ✅ |
| CA-4 | Falha em meio-aberto reabre o bloqueio por `issue.block_duration` | **Atendido** | CT-05 ✅ |
| CA-5 | `platform.max_blocked_issues` na janela bloqueia a plataforma; outras seguem | **Atendido** | CT-06, CT-07, CT-20 ✅ |
| CA-6 | `issue.max_blocks` bloqueios consecutivos escalam ao agente dedicado 1x | **Atendido** | CT-08, CT-08b ✅ |
| CA-7 | Correção do agente dedicado → sync retentado no ciclo seguinte | **Atendido** | CT-09 ✅ |
| CA-8 | Falha após correção → encerramento com código ≠ 0 e registro completo | **Atendido** | CT-10, CT-11 ✅ |
| CA-9 | Descida sempre completa, sem modo parcial | **Atendido** | CT-12 ✅ |
| CA-10 | Relação de bloqueio já existente é sucesso idempotente; segue processando | **Atendido** | CT-13 ✅ |
| CA-11 | `body_mtime` gravado antes de propagar falha de aplicação de comandos | **Atendido** | CT-14 ✅ |
| CA-12 | Rate limit/penalty não incrementa nenhum contador do circuit-breaker | **Atendido** | CT-15, CT-16 ✅ |
| CA-13 | Parâmetro ausente → default aplicado sem erro | **Atendido** | CT-17, CT-17b ✅ |
| CA-14 | Erro hoje tratado por E4 é conduzido pelo circuit-breaker, sem mecanismo paralelo | **Atendido** | CT-18 ✅ |

**Cobertura:** 14/14 critérios de aceitação com veredito explícito e teste
verde correspondente. Nenhum critério "não verificável" e nenhum "não
atendido".

Robustezes de borda e isolamento adicionais também cobertas e verdes: CT-19
(bordas exatas de duração — `t0+299`/`t0+300`/`t0+301`), CT-20 (plataformas
distintas independentes), CT-21 (segurança/proteção do arquivo de estado),
CT-22 (distinção comportamental `file` vs. `memory`), e a interação
`sync.max_attempts` × contador de bloqueio de issue (ponto de atenção
explicitamente deixado como detalhe de implementação pelo corpo da issue,
coberto nos testes de `TestMaxAttemptsInteraction`).

---

## 7. Aderência à arquitetura

- **Núcleo independente de plataforma:** a decisão de bloqueio/meio-aberto/
  escalação/fatal vive em `src/core/sync_circuit_breaker.py` (novo módulo
  isolado), consumido por `src/core/sync.py::apply_changes` — mesma separação
  de responsabilidades (domínio vs. adaptador) exigida por RNF-05. ✅
- **Dono único (RNF-06/RN-11 — absorção da E4):** `RemediationSignal`/
  `RemediationFailStop` foram removidos (`TestE4Absorbed::
  test_mecanismo_antigo_foi_removido`); o erro `corrigivel_pelo_agente`
  escala exclusivamente pelo caminho do novo circuit-breaker (CT-18). Não há
  dois mecanismos paralelos tratando a mesma responsabilidade. ✅
- **Exclusão estrutural do rate limit (RN-10):** a exclusão usa
  `PenaltyException` real, nunca varredura textual — mesmo princípio de
  `test_rate_limit_detection.py` aplicado à exclusão da contagem (CT-15,
  CT-16). ✅
- **Descida sempre completa (RF-14/RN-12):** `get_issue` e os caminhos de
  `_apply_*_down` não têm mais bifurcação de modo parcial (CT-12);
  `tests/test_sync_unico_deps.py` confirma `fullsync` sempre e dependências
  reconciliadas após aplicação. ✅
- **Idempotência de relação existente (RF-15/RN-13):** tratada no adaptador
  (`src/adapters/github_board.py`), sem abortar o lote; demais relações
  seguem processando (CT-13). ✅
- **Persistência de progresso antes de propagar falha (RF-16/RN-14):**
  `_apply_change_up` grava `body_mtime` antes de a exceção de
  `apply_commands` propagar (CT-14) — rompe exatamente o padrão de loop do
  incidente "Issue Fantasma" descrito na própria issue. ✅
- **Persistência configurável (RF-17/RNF-03):** `sync.circuit_breaker.
  persistence: file|memory`, com distinção comportamental verificada (CT-22);
  arquivo de estado atômico e protegido. ✅
- **Estado protegido:** `.pipe/syncCircuitBreaker.json` listado em
  `PROTECTED_PATHS`; conteúdo sem corpo de issue, prompt ou credencial
  (CT-21). ✅
- **Validação de config no padrão da casa:** `ConfigError` citando o caminho
  completo do campo, bloco opcional e ausente ⇒ defaults sem erro, agente de
  escalação obrigatoriamente existente em `agents` (CT-17, CT-17b). ✅
- **Isolamento de teste (anti-#106):** os casos exercitam o núcleo real com
  `BoardPort` fake, relógio controlável e dispatch espião ao agente dedicado;
  sem `monkeypatch` do símbolo sob teste. ✅

Nenhuma violação de arquitetura detectada.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 90 testes pertinentes a #309
  passam; as 26 falhas e 13 erros da suíte completa são baseline alheio,
  provadamente idênticos a `main` (`f76951d`, zero regressão).
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos
  CT-01..CT-22 (incluindo CT-08b e CT-17b) são coerentes com os 14 critérios
  de aceitação, exercitam o código real e passam integralmente. Os casos,
  escritos antes do código na etapa de Casos de Teste, agora passam porque a
  implementação os satisfez — não houve reprovação por ausência de
  implementação.

— Camila Rocha - Engenheira de Qualidade (QA)
