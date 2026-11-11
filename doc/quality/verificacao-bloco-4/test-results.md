# Resultados de Teste / Relatório de Verificação — Bloco 4 (limite de consumo de IA e vitrine de exemplos)

- **Issue:** #317 — auditoria integrada das entregas #311 e #312
- **Etapa:** Execução de Testes
- **Autor:** André Tavares — Engenheiro de Qualidade PL
- **Branch:** `feature/317-verificacao_do_bloco_4_limite_de_consumo_de_ia_e_vitrine_de_exemplos`
- **Base:** `origin/main` @ `e7ba768` (sem avanço no `git fetch`)
- **Ambiente:** Python 3.12, pytest, execução offline

## 1. Veredito

**APROVADO — SEM DIVERGÊNCIA — avançar para `documentacao`.**

As duas entregas estão efetivas na linha principal. Nenhuma alteração de código-fonte, nenhum bump de versão e nenhuma entrada de CHANGELOG são atribuíveis a esta verificação. Nesta etapa não foram alterados código nem casos de teste.

## 2. Resultados por caso de teste

| Caso | Resultado | Evidência |
|------|-----------|-----------|
| CT-01 Suíte completa | Aprovado (baseline alheio) | `python -m pytest -q`: 2086 passed, 26 failed, 18 skipped, 1 xpassed (~50 s). As 26 falhas: `test_agent_log_descritivo.py` (18), `test_dockerfile.py` (3), `test_docker_compose.py` (4), `test_agent_failure_detection.py` (1). Mesmos 4 arquivos e contagens do baseline dos blocos 1–3. Nenhuma pertence a #311/#312. Zero regressão nova. |
| CT-02 Cobertura dos CAs | Aprovado | Execução dirigida dos 8 arquivos de #311/#312: 200 passed, 1 skipped. O skip é `test_vitrine_governanca.py::test_registro_real_de_reavaliacao_apos_producao` (CT-29 de #312), diferido por design até "Em produção" — não é lacuna. Vereditos de origem: 12/12 CAs de #311 e 12/12 de #312 aprovados nos respectivos `test-results.md`. Nenhuma lacuna de cobertura. |
| CT-03 Comportamento presente / versão × CHANGELOG | Aprovado | #311: `_consumption_allows` em `src/__main__.py:580` e `:749`; `_record_consumption` em `:782`; `validate_consumption_limits` em `src/core/config.py:577`; `.pipe/consumptionLimit.json` em `PROTECTED_PATHS` (`src/core/agent.py:40`). `5116770` toca 4 arquivos de `src/`, coerente com o bump 1.28.0 e a seção `[1.28.0]` do CHANGELOG. #312: `git diff --name-only e7ba768^1 e7ba768 -- src/` vazio e cada commit (`2ffc898`, `0d2b2d6`, `20a4a7f`, `f16af24`) toca 0 arquivos em `src/`. A ausência de bump/CHANGELOG para #312 é coerente, não é divergência. `VERSION = "1.29.0"` vem de #345, fora do bloco. |
| CT-04 Ponto de decisão compartilhado | Aprovado (CA-6 vacuamente atendido) | #312 não toca `src/`; `grep limits exemplos/*/pipe.yml` não encontra nada (exit 1). Sem ponto de decisão compartilhado. Complemento: `tests/test_vitrine_config.py` passa sobre `check_config` já estendido por #311. |
| CT-05 Fecho sem divergência | Aprovado | `git diff --stat origin/main...HEAD`: apenas `doc/quality/verificacao-bloco-4/`. `VERSION` e `CHANGELOG.md` inalterados. |

## 3. Veredito por critério de aceitação da issue

| CA | Veredito | Evidência |
|----|----------|-----------|
| CA-1 Relatório com veredito por critério | Atendido | Este documento (seções 2 e 3). |
| CA-2 Suíte completa executada; falha corrigida ou justificada | Atendido | CT-01: 26 falhas, todas baseline alheio, justificadas. |
| CA-3 Sem divergência ⇒ sem alteração de código nem bump | Atendido | CT-03/CT-05. |
| CA-4 Divergência corrigível ⇒ regressão + bump + CHANGELOG | Não aplicável | Nenhuma divergência encontrada. |
| CA-5 Divergência de escopo novo ⇒ demanda separada | Não aplicável | Nenhuma encontrada. Demandas separadas: nenhuma. |
| CA-6 Mesmo ponto de decisão | Atendido (vacuamente) | CT-04. |
| CA-7 Critério não verificável | Atendido | Nenhum critério ficou "não verificável"; o CT-29 de #312 é diferido por design e está documentado. |

## 4. Observação (não bloqueante)

Os 26 testes falhos são pré-existentes (formato do log diário descritivo e infraestrutura Docker). Já são rastreados desde os blocos anteriores e estão fora do escopo deste bloco.
