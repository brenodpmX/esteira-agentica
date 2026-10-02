# Resultados de Teste — Execução de Testes (etapa `execucao-testes`) — Verificação do Bloco 2

- **Issue:** #315 — "Verificação do bloco 2 — estrutura de board, contexto do
  agente e limites de execução"
- **Etapa:** Execução de Testes
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-02
- **Branch:** `feature/315-verificacao-bloco-2`
- **Base no momento desta execução:** `origin/main` @ `0d81ac3` (avançou de
  `dd3a634`, base original do desenvolvimento, por um merge não relacionado —
  `fix(sync): confirma ausência antes de delete-down`, PR #326 — sem relação
  com #305/#306/#307/#308; não altera o veredito desta verificação)

> Esta execução **reproduz e confirma de forma independente** o relatório já
> produzido na etapa de desenvolvimento
> (`doc/quality/verificacao-bloco-2/test-results.md`), sem alterar código nem
> os casos de teste, conforme o papel desta etapa.

---

## Veredito

**APROVADO — avançar para `documentacao`.**

Todos os resultados reproduzidos nesta execução **coincidem exatamente** com os
relatados pelo desenvolvimento. Nenhuma reprovação, nenhuma regressão, nenhuma
divergência nova.

---

## Ambiente de execução

- Python 3.12.15, pytest 9.1.1, pluggy 1.6.0 (instalados nesta sessão via
  `pip install pytest pyyaml` — ambiente não trazia as dependências pré-instaladas)
- `rootdir: /app/repo/main`
- `git fetch origin` executado antes da verificação; `origin/main` avançou para
  `0d81ac3` (merge do PR #326, fora do escopo do bloco 2). Branch de trabalho
  `feature/315-verificacao-bloco-2` já estava sincronizada com seu remoto, sem
  mudanças pendentes.

## Comandos executados e resultados

### CT-01 — Suíte completa (`python -m pytest -q`)

```
26 failed, 1583 passed, 17 skipped, 1 xpassed, 1 warning in 47.24s
```

Conjunto de arquivos com falha (contagem por arquivo):

| Arquivo | Falhas |
|---|---|
| `tests/test_agent_log_descritivo.py` | 18 |
| `tests/test_agent_failure_detection.py` | 1 |
| `tests/test_docker_compose.py` | 4 |
| `tests/test_dockerfile.py` | 3 |

**Idêntico** ao baseline registrado em `test-results.md` da etapa de
desenvolvimento (1583 passed, 26 failed, mesmos arquivos). Confirma **zero
regressão nova** — as 26 falhas são baseline pré-existente alheio às entregas
#305/#306/#307/#308 (formato de log descritivo + infraestrutura Docker),
já documentadas em `doc/quality/verificacao-bloco-1/test-results.md`.

### CT-02/CT-03 — Suíte focada das quatro entregas (24 arquivos)

```
261 passed in 2.95s
```

Nenhuma falha. Confirma cobertura e ausência de comportamento declarado e
ausente para #305, #306, #307 e #308.

### CT-04 — Convergência #306 × #307 (`tests/test_convergencia_bloco2_execucao.py`)

```
test_ct04a_dentro_do_limite_admite_e_grava_registro PASSED
test_ct04b_limite_bloqueia_e_nao_grava_registro_excedente PASSED
test_ct04c_falha_composicao_bloqueia_antes_do_limitador_e_do_registro PASSED
test_ct04d_classificacao_fiel_com_limitador_ativo_dentro_do_limite PASSED

4 passed in 1.39s
```

Confirma que o limitador de reexecuções (#306) e o registro de execução (#307)
coexistem no mesmo ponto de decisão (`call_agent`) sem sombreamento mútuo.

### CT-05 — Sem divergência (versão, CHANGELOG, diff)

- `src/core/version.py` → `VERSION = "1.20.0"` (**inalterada**).
- `CHANGELOG.md` → seções `1.17.0`, `1.18.0`, `1.19.0`, `1.20.0` presentes;
  **nenhuma entrada nova**.
- `git diff --stat origin/main...HEAD`:

```
doc/quality/verificacao-bloco-2/test-cases.md   | 439 +++++++++++++++
doc/quality/verificacao-bloco-2/test-results.md | 290 +++++++++
tests/test_convergencia_bloco2_execucao.py      | 302 +++++++++
3 files changed, 1031 insertions(+)
```

**Nenhuma mudança em `src/`.** `git status --porcelain` sem pendências.

---

## Classificação

**Sucesso — avançar.** Todos os sub-resultados (CT-01..CT-05) foram reproduzidos
de forma independente nesta etapa e coincidem com o relatório do desenvolvimento.
Não há reprovação total nem parcial, logo não há análise de causa-raiz a fazer
nem classificação `falha` ou `revisar-caso-de-teste`. As 26 falhas de baseline
permanecem registradas como demanda separada (CA-5), fora do escopo desta
issue.

Nenhum código-fonte, caso de teste ou documento de casos foi alterado nesta
etapa — apenas este relatório de execução foi adicionado, conforme o papel.
