# Resultados de Teste — Execução autônoma confiável (detecção de falha fiel + recuperação segura)

- **Issue:** #303 — "Tornar a execução autônoma de agentes confiável, com detecção
  de falha fiel e recuperação segura de interrupções"
- **Etapa:** Execução de Testes
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/303-execucao-autonoma-confiavel`
- **Commit sob teste:** `0d7bc44` — feat(#303): execucao autonoma confiavel -
  deteccao por canais + recuperacao segura

> Este documento registra a execução dos casos especificados em
> `test-cases.md` sobre a implementação entregue pelo desenvolvimento. Cada caso
> tem resultado explícito (PASS/FAIL) e vínculo ao critério de aceitação (CA).

---

## 1. Veredito

**APROVADO (sucesso) — avançar para `documentacao`.**

Todos os 15 casos de teste especificados (CT-01…CT-15, incluindo CT-04b e CT-05b)
foram executados e **passaram**. A implementação cobre fielmente os critérios de
aceitação do escopo reconciliado (ADR #217 + precedência do Grupo A). Não há
reprovação total nem parcial atribuível a #303. As falhas remanescentes na suíte
completa do repositório são **baseline pré-existente**, comprovadamente idênticas
a `origin/main` (zero regressão introduzida — ver seção 4).

---

## 2. Ambiente de execução

- Python 3.12.14, pytest 9.1.1, pluggy 1.6.0
- `rootdir: /app/repo/main`
- Execução offline (sem rede / sem subprocesso real; `time.sleep` mockado nos
  casos de backoff, conforme as notas de execução do `test-cases.md`)
- Comandos:
  - `python -m pytest tests/test_execucao_autonoma_confiavel.py -v`
  - `python -m pytest tests/test_agent_failure_detection.py -v`
  - `python -m pytest -q` (suíte completa)

---

## 3. Resultados por caso (CA → CT → resultado)

### Suíte dedicada — `tests/test_execucao_autonoma_confiavel.py` → **35 passed**

| Grupo | Caso | Alvo (teste) | Resultado |
|-------|------|--------------|-----------|
| A — Detecção de falha | CT-01 — narrativa cita erro sem sinal estruturado → sucesso | `TestDeteccaoFalhaCanaisEstruturados::test_ct01_...` | ✅ PASS |
| A | CT-02 — exit-code ≠ 0 → falha com causa estruturada | `...test_ct02_exit_code_nao_zero_e_falha_com_causa_estruturada` | ✅ PASS |
| A | CT-02b — exit-code 0 não é falha | `...test_ct02b_exit_code_zero_nao_e_falha` | ✅ PASS |
| A | CT-03 — marcador de timeout → falha | `...test_ct03_marcador_timeout_e_falha` | ✅ PASS |
| A | CT-04 — erro de transporte estruturado → falha | `...test_ct04_erro_transporte_estruturado_e_falha` | ✅ PASS |
| A | CT-04b — output vazio/normal sem marcador → sucesso | `...test_ct04b_output_vazio_ou_normal_sem_marcador_e_sucesso` | ✅ PASS |
| A | CT-05 — regressão do falso positivo histórico não recorre | `...test_ct05_regressao_falso_positivo_narrativa_nao_recorre` | ✅ PASS |
| B — Caminhos de apoio | CT-07 — caminho ausente não cancela o lote | `TestCaminhosDeApoio::test_ct07_caminho_inexistente_nao_cancela_lote` | ✅ PASS |
| B | CT-08 — config e código apontam para a mesma fonte válida | `...test_ct08_config_e_codigo_apontam_para_mesma_fonte_valida` | ✅ PASS |
| B | CT-08 — fonte única do repo existe | `...test_ct08_fonte_unica_do_repo_existe` | ✅ PASS |
| C — Contexto | CT-09 — tabelas preenchidas | `TestContextoDerivadoDaConfig::test_ct09_contexto_contem_tabelas_preenchidas` | ✅ PASS |
| C | CT-09 — sem aviso de conflito no caminho feliz | `...test_ct09_sem_aviso_de_conflito_no_caminho_feliz` | ✅ PASS |
| C | CT-09b — artefato congelado vazio não tem precedência | `...test_ct09b_artefato_congelado_vazio_nao_tem_precedencia` | ✅ PASS |
| C | CT-09b — `pipe_context.json` legado não sombreia o steering | `...test_ct09b_pipe_context_legado_nao_sombreia_steering` | ✅ PASS |
| D — Recuperação | CT-10 — `UNKNOWN_OUTCOME` fail-closed (1 invocação, preserva evidências) | `TestRecuperacaoInterrupcao::test_ct10_unknown_outcome_fail_closed_uma_invocacao_preserva` | ✅ PASS |
| D | CT-11 — `DEFINITE_NOT_STARTED` retoma até sucesso (backoff) | `...test_ct11_definite_not_started_retoma_ate_sucesso` | ✅ PASS |
| D | CT-11 — `DEFINITE_NOT_STARTED` esgota limite → falha persistente | `...test_ct11_definite_not_started_esgota_limite` | ✅ PASS |
| D | CT-12 — `UNKNOWN_OUTCOME` não dispara retry/backoff | `...test_ct12_unknown_outcome_nao_dispara_retry_nem_backoff` | ✅ PASS |
| D | CT-13 — observabilidade: causa real + origem do canal | `...test_ct13_log_registra_causa_e_origem_do_canal` | ✅ PASS |
| D (config) | CT-14 — validação/defaults de `retry.*` (14 variações parametrizadas) | `TestRetryConfig::test_ct14_*` | ✅ PASS (14/14) |
| E — Documentação | CT-15 — nenhum identificador de modelo inválido na doc de exemplo | `TestHigieneDocumentacao::test_ct15_doc_exemplo_sem_identificador_de_modelo_invalido` | ✅ PASS |

Saída: `35 passed in 1.34s`.

> **Nota de fronteira (test-first → entregue):** CT-01 e CT-05, especificados como
> `xfail(strict=True)` enquanto a detecção escaneava a narrativa, foram executados
> agora como **PASS plenos** (não XFAIL/XPASS). Isso confirma que o
> desenvolvimento aplicou a classificação só-por-canais e removeu a dependência da
> narrativa — o coração da entrega.

### Suíte congelada — `tests/test_agent_failure_detection.py` → **18 passed, 1 failed**

Validação de CT-05b (precedência de contrato do Grupo A):

- **Reescritos (codificavam o falso positivo) — classificam agora por canal
  estruturado:** `TestDetectFailureFalha::test_cada_marcador_dispara_falha`
  (parametrizado só com `[exit-code: 1]`, `[TIMEOUT]`, `[ERRO]` — sem o parâmetro
  de narrativa), `test_extrai_erro_de_modelo_indisponivel`,
  `test_nao_reduz_a_ultima_linha`, `test_une_linhas_relevantes_com_pipe`,
  `TestExecuteUsaDeteccao::test_falha_loga_error_com_causa`. ✅ PASS. Verificado:
  o termo "Kiro is having trouble responding" só aparece **após** o marcador
  estruturado `[ERRO]` — a classificação vem do canal, nunca da prosa.
- **Preservados (sucesso, legítimos):** `TestDetectFailureSucesso::*`
  (output vazio/normal/palavra "error" sem marcador = sucesso),
  `TestExecuteUsaDeteccao::test_sucesso_loga_info_com_resumo`, toda a classe
  `TestLastMeaningfulLine`. ✅ PASS.
- **1 FAIL:** `TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic`
  — **baseline pré-existente, fora do escopo de #303** (ver seção 4).

---

## 4. Análise de causa-raiz das falhas remanescentes (baseline)

A suíte completa (`python -m pytest -q`) retornou
**26 failed, 1285 passed, 17 skipped, 1 xpassed**. Nenhuma dessas 26 falhas é
atribuível a #303.

**Prova de zero regressão (método objetivo):** comparei o conjunto de testes
falhando na branch de trabalho com o conjunto falhando em `origin/main`,
coletados via `pytest -q | grep '^FAILED'` e comparados com `comm`:

- Falhas **novas** na branch (presentes na branch e ausentes no baseline): **0**.
- Falhas **"corrigidas"** pelo baseline (presentes só no baseline): **0**.
- Conjuntos **idênticos** (26 = 26).

Classificação das 26 falhas de baseline (todas pré-existentes e fora do escopo
reconciliado de #303):

| Arquivo | Qtd | Causa-raiz | Relação com #303 |
|---------|-----|-----------|------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de **formato do log diário descritivo** (linha de início/resumo) | Nenhuma — `__main__`/formatação de log; não toca `_detect_failure` nem o eixo de recuperação |
| `tests/test_agent_failure_detection.py::...test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato: asserta `'"Uma issue"'` com aspas, mas o log emite `#42 Uma issue` sem aspas | Nenhuma — é a **linha de início** do `execute()`, não a classificação de falha; falha idêntica em `origin/main` |
| `tests/test_docker_compose.py` | 4 | Dependem de ambiente Docker/compose não disponível na execução | Nenhuma |
| `tests/test_dockerfile.py` | 3 | Dependem de ambiente Docker | Nenhuma |

Conclusão da causa-raiz: **não há falha de código de #303**. As 26 falhas são
débito/ambiente pré-existentes, já registrados pelo desenvolvimento e pelas
iterações anteriores de QA, e explicitamente fora do escopo reconciliado desta
entrega. Portanto **não** há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste` — os casos de #303 estão todos verdes e consistentes com a
suíte congelada preservada.

> **Débito a tratar em separado (recomendação, não bloqueante):** o planejamento
> pode abrir uma issue dedicada para o formato do log descritivo
> (`test_agent_log_descritivo.py` + a linha de início do `epic`), que vem falhando
> no baseline independentemente de #303.

---

## 5. Rastreabilidade de cobertura (todos os CA cobertos)

| Critério de aceitação (resumo) | Caso(s) | Resultado |
|--------------------------------|---------|-----------|
| Narrativa com frase de erro, sem sinal → sucesso | CT-01 | ✅ |
| Exit-code ≠ 0 → falha com causa estruturada | CT-02 (+CT-02b) | ✅ |
| Marcador de timeout → falha | CT-03 | ✅ |
| Erro de transporte estruturado → falha | CT-04 | ✅ |
| Output vazio/normal sem marcador → sucesso | CT-04b | ✅ |
| Regressão do falso positivo não recorre | CT-05 | ✅ |
| Suíte congelada reescrita (precedência #303) | CT-05b | ✅ |
| Caminho ausente não cancela o lote | CT-07 | ✅ |
| Config e código mesma fonte válida | CT-08 | ✅ |
| Contexto com tabelas preenchidas, sem aviso | CT-09 | ✅ |
| Congelado (tabelas vazias) sem precedência | CT-09b | ✅ |
| `UNKNOWN_OUTCOME` fail-closed, preserva evidências | CT-10 | ✅ |
| `DEFINITE_NOT_STARTED` retry+backoff até limite | CT-11 | ✅ |
| `UNKNOWN_OUTCOME` sem retry/backoff | CT-12 | ✅ |
| Observabilidade: causa + origem do canal | CT-13 | ✅ |
| Validação/defaults de `retry.*` | CT-14 | ✅ |
| Nenhum identificador de modelo inválido | CT-15 | ✅ |

Cobertura: **100% dos critérios de aceitação** com caso verde correspondente.
Aderência à arquitetura (ADR #217): nenhum retry inline para `UNKNOWN_OUTCOME`
(CT-12 garante); retry inline exclusivo de `DEFINITE_NOT_STARTED` (CT-11) — sem
violação de arquitetura.

---

## 6. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- Sem reprovação de código (`falha`) e sem caso de teste inadequado
  (`revisar-caso-de-teste`).
