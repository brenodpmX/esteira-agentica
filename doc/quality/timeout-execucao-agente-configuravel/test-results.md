# Resultados de Teste — Timeout de execução do agente configurável via pipe.yml (default 3600s)

- **Issue:** #337 — "Timeout de execução do agente configurável via pipe.yml
  (default 3600s)"
- **Etapa:** Execução de Testes
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-11-04
- **Branch:** `feature/337-timeout_de_execucao_do_agente_configuravel_via_pipeyml_default_3600s`
- **Commit sob teste:** `1264afe` — feat(337): timeout de execução do agente
  configurável via pipe.yml (agent_timeout_seg, default 3600s)
- **Base de comparação:** `main` @ `b6c2a94`

> Este documento registra a execução dos casos especificados em
> `test-cases.md` (CT-01 a CT-06, com variantes CT-04b/CT-04c/CT-04d e CT-05b,
> cobrindo CA-1..CA-4), com veredito e análise de causa das falhas
> remanescentes. Nenhum código ou caso de teste foi alterado nesta etapa.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

O timeout de execução do agente configurável via `agent_timeout_seg` (#337)
está implementado na branch de trabalho e coberto por `tests/test_agent_timeout_config.py`
— único arquivo novo desta entrega, cobrindo validação (`validate_agent_timeout`),
resolução (`resolve_agent_timeout`) e o comportamento observável no adapter
(`KiroCliAgent._run`: kwarg `timeout` do `subprocess.run` e texto da mensagem
`[TIMEOUT]`).

- **8 testes** em `tests/test_agent_timeout_config.py` (CT-01..CT-06, variantes
  CT-04b/CT-04c/CT-04d e CT-05b) passam integralmente (7 subtests dentro de
  `test_invalidos`, que cobre 0, -10, 3600.0, "3600", True, False e None num
  único teste parametrizado).
- Os **4 critérios de aceitação** (CA-1..CA-4) têm teste correspondente verde
  (ver seção 6).
- Os testes de detecção de falha por canal estruturado (`_classify`/
  `_detect_failure`, issue #303) continuam reconhecendo `[TIMEOUT]` independente
  do valor numérico — sem regressão (seção 4).

As **26 falhas + 13 erros** remanescentes na suíte completa são **baseline
pré-existente**, provadamente **idênticas** em `main @ b6c2a94` (**zero
regressão**), **alheias** ao escopo de #337 (débito de formato do log diário
descritivo e de infra Docker). Não constituem reprovação de código desta
entrega.

Portanto **não** há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste` (volta ao QA): os 8 casos são coerentes com os 4
critérios de aceitação, exercitam o código real (`src/core/config.py`,
`src/core/agent.py`, `src/adapters/kiro_cli_agent.py`, com `subprocess.run`
mockado, sem acionar `kiro-cli` real) e passam integralmente.

---

## 2. Ambiente de execução

- Python 3.12.16, pytest 9.2.0
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso `kiro-cli`
  real): os casos de #337 exercitam funções puras de validação/resolução e o
  adapter com `subprocess.run` mockado (`patch("subprocess.run", ...)`),
  conforme as convenções fixadas no `test-cases.md`.
- Comandos:
  - `python -m pytest tests/test_agent_timeout_config.py -v` (arquivo novo de
    #337)
  - `python -m pytest tests/test_execucao_autonoma_confiavel.py
    tests/test_agent_failure_detection.py -q -k "timeout or TIMEOUT"`
    (regressão da detecção de falha por canal estruturado, issue #303)
  - `python -m pytest tests/ -q` (suíte completa)
  - comparação de baseline em **worktree limpo** de `main @ b6c2a94`
    (`git worktree add /tmp/baseline_main main`), com diff exato do conjunto de
    falhas/erros.

---

## 3. Resultado da suíte completa

```
26 failed, 1776 passed, 17 skipped, 1 xpassed, 1 warning, 13 errors, 7 subtests passed in 72.70s
```

- **1776 passed** — inclui os **8 testes novos** de #337.
- **26 failed + 13 errors** — baseline pré-existente (ver seção 5).
- **17 skipped, 1 xpassed** — inalterados em relação ao baseline.

---

## 4. Resultados por caso de teste (CT-01..CT-06)

Execução dirigida do arquivo novo de #337: **8 passed, 7 subtests passed in
0.26s**.

| CT | Critério / cenário | Teste | Resultado |
|----|---------------------|-------|-----------|
| CT-01 | `subprocess.run` recebe `timeout=3600` quando a chave está ausente | `TestTimeoutNoAdapter::test_default_3600` | ✅ PASS |
| CT-02 | `subprocess.run` recebe `timeout=7200` quando `agent_timeout_seg: 7200` | `TestTimeoutNoAdapter::test_configurado_7200` | ✅ PASS |
| CT-03 | mensagem `[TIMEOUT]` registra o valor configurado (7200), não o default antigo | `TestTimeoutNoAdapter::test_mensagem_timeout_reflete_valor` | ✅ PASS |
| CT-04 | `agent_timeout_seg` não positivo (`0`/negativo) rejeitado | `TestValidateAgentTimeout::test_invalidos` (subTest `value=0`, `value=-10`) | ✅ PASS |
| CT-04b | `agent_timeout_seg` não inteiro (float/string) rejeitado | `TestValidateAgentTimeout::test_invalidos` (subTest `value=3600.0`, `value='3600'`) | ✅ PASS |
| CT-04c | `agent_timeout_seg` bool (`True`/`False`) rejeitado | `TestValidateAgentTimeout::test_invalidos` (subTest `value=True`, `value=False`) | ✅ PASS |
| CT-04d | validação inválida ocorre dentro de `check_config()`, antes de qualquer execução | `TestValidateAgentTimeout::test_check_config_rejeita_invalido` | ✅ PASS |
| CT-05 | chave ausente: validação passa e resolução retorna `3600` | `TestValidateAgentTimeout::test_ausente_valida_e_resolve_default` | ✅ PASS |
| CT-05b | chave presente (`7200`) válida: validação passa e resolução retorna `7200` | `TestValidateAgentTimeout::test_valor_valido` | ✅ PASS |
| CT-06 | valor mínimo válido (`1`) aceito | `TestValidateAgentTimeout::test_minimo_valido` | ✅ PASS |

**Observação sobre `None`:** o caso de teste não previa explicitamente o valor
`None` como variante, mas o desenvolvimento incluiu-o em `test_invalidos`
(junto com `0`, `-10`, `3600.0`, `"3600"`, `True`, `False`) — coerente com o
espírito de CT-04/CT-04b/CT-04c (qualquer valor não inteiro positivo deve ser
rejeitado) e não contradiz nenhum CA. Não é lacuna de cobertura: é reforço.

**Total #337 (arquivo novo):** 8 passed (7 subtests), 0 failed.

### Regressão da detecção de falha por canal estruturado (issue #303)

```
python -m pytest tests/test_execucao_autonoma_confiavel.py tests/test_agent_failure_detection.py -q -k "timeout or TIMEOUT"
2 passed, 52 deselected in 0.25s
```

Confirma que `_classify`/`_detect_failure` continuam reconhecendo
`UNKNOWN_OUTCOME` pela presença do marcador `[TIMEOUT]`, independente do valor
numérico nele — sem regressão na detecção de falha por canais estruturados.

---

## 5. Análise de causa das falhas remanescentes (baseline) — zero regressão

A suíte completa retornou **26 failed, 1776 passed, 17 skipped, 1 xpassed, 13
errors**.

**Prova objetiva de zero regressão.** Executei a suíte completa na branch de
trabalho e, em paralelo, em um **worktree limpo** de `main @ b6c2a94` (base da
branch de #337, anterior aos commits `c7cc24a` e `1264afe`). Comparei o
conjunto de IDs de teste que falham/erram em cada lado com `diff`:

```
$ diff /tmp/baseline.txt /tmp/with_changes.txt
(sem saída — diff vazio)
IDENTICAL
```

- `main @ b6c2a94`: **26 failed + 13 errors** (39 IDs).
- branch `feature/337-...`: **mesmas 26 falhas + 13 erros**, byte a byte (39
  IDs = 39 IDs).
- Falhas/erros **novos** introduzidos por #337: **0**.
- Falhas/erros **"corrigidos"** por #337: **0**.

Classificação das 39 falhas/erros de baseline — todas pré-existentes e **fora
do escopo de #337** (não tocam `agent_timeout_seg`, `validate_agent_timeout`,
`resolve_agent_timeout`, `AgentParams.timeout_seg` nem o `subprocess.run`/
mensagem `[TIMEOUT]` do adapter):

| Arquivo | Qtd | Causa-raiz | Relação com #337 |
|---------|-----|-----------|-------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de **formato do log diário descritivo** (título entre aspas, posição de `@`, campos no terminal) | Nenhuma — formatação de log em `__main__`; não toca o timeout |
| `tests/test_agent_failure_detection.py::TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato (linha de início do `execute()`) | Nenhuma |
| `tests/test_docker_compose.py` | 4 | Dependem de ambiente/validação Docker Compose não disponível na execução; divergência de **infra Docker** | Nenhuma |
| `tests/test_dockerfile.py` | 3 failed + 13 errors | Dockerfile atual não declara `ARG KIRO_CLI_SHA256`/verificação de hash esperada pelos testes, e a suíte de integração (`TestDockerIntegracao`) depende de imagem Docker construída, indisponível neste ambiente de execução; **infra Docker** | Nenhuma |

**Destino:** as 39 falhas/erros pertencem a frentes próprias (formato de log
descritivo e infra Docker), já conhecidas das execuções anteriores (#305,
#308, #314). **Não** são corrigidas aqui — corrigi-las ampliaria o escopo e
esta etapa não altera código. Permanecem como demanda separada do
planejamento. Nenhuma delas classifica #337 como `falha`.

---

## 6. Veredito por critério de aceitação (CA-1..CA-4)

| CA | Critério (resumo) | Veredito | Evidência (CT) |
|----|--------------------|----------|-----------------|
| CA-1 | Ausência da chave → timeout efetivo 3600s no `subprocess.run` | **Atendido** | CT-01, CT-05 ✅ |
| CA-2 | `agent_timeout_seg: 7200` → `subprocess.run` usa 7200s e `[TIMEOUT]` registra 7200s | **Atendido** | CT-02, CT-03, CT-05b ✅ |
| CA-3 | Valor inválido (`<= 0` ou não inteiro) → `ConfigError` citando a chave, antes de qualquer execução | **Atendido** | CT-04, CT-04b, CT-04c, CT-04d, CT-06 ✅ |
| CA-4 | Chave ausente → validação passa normalmente e valor efetivo assumido é 3600 | **Atendido** | CT-05 ✅ |

**Cobertura:** 4/4 critérios de aceitação com veredito explícito e teste verde
correspondente. Nenhum critério "não verificável" e nenhum "não atendido".

---

## 7. Aderência à arquitetura

- **Padrão `validate_<bloco>`/`resolve_<bloco>` da casa:** `validate_agent_timeout`
  e `resolve_agent_timeout` seguem o mesmo formato de `validate_retry`/
  `resolve_retry` e `validate_registro`/`resolve_registro` — `ConfigError`
  citando a chave, chamada dentro de `check_config()` antes de qualquer
  alteração de estado; `bool` rejeitado antes da checagem de `int` (CT-04c). ✅
- **Resolução única a partir da config carregada:** o valor é resolvido uma
  única vez em `src/__main__.py` (`resolve_agent_timeout(config)`) e propagado
  via `AgentParams.timeout_seg` até `KiroCliAgent._run` — sem resolução
  duplicada ou valor hardcoded remanescente (a constante `_TIMEOUT` foi
  removida de `src/adapters/kiro_cli_agent.py`, confirmado por grep: nenhuma
  ocorrência de `_TIMEOUT` no código fonte). ✅
- **Mesmo valor efetivo nos dois usos:** `subprocess.run(..., timeout=params.timeout_seg)`
  e a mensagem `f"[TIMEOUT] Agente excedeu {params.timeout_seg}s"` leem o mesmo
  campo — CT-02 e CT-03 provam isoladamente que nenhum dos dois pontos ficou
  dessincronizado do outro. ✅
- **Default preservado bit a bit:** CT-01 e CT-05 confirmam que a ausência da
  chave produz exatamente `3600` em ambos os usos — comportamento idêntico ao
  anterior à entrega. ✅
- **Sem acoplamento indevido a `3600` fora do contexto de default:** nenhum
  teste pré-existente precisou de alteração para este escopo passar (confirmado
  pelo diff de baseline idêntico na seção 5). ✅
- **Fora de escopo respeitado:** nenhum caso testa timeout por coluna/etapa,
  mudança de valor efetivo em pipe já em produção, ou timeouts de preflight/`gh`
  — conforme delimitado na issue e no `test-cases.md`. ✅

Nenhuma violação de arquitetura detectada.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 8 testes de #337 passam
  integralmente; as 26 falhas + 13 erros da suíte completa são baseline alheio,
  provadamente idênticos a `main @ b6c2a94` (zero regressão).
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos
  CT-01..CT-06 (com variantes) são coerentes com os 4 critérios de aceitação,
  exercitam o código real e passam integralmente.

— Camila Rocha - Engenheira de Qualidade (QA)
