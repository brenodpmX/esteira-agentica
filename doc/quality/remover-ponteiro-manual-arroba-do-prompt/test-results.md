# Resultados de Teste — Remover do prompt o ponteiro do manual `@---` (manter apenas no steering)

- **Issue:** #325
- **Etapa:** Execução de Testes
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-02
- **Branch:** `feature/325-remover-do-prompt-o-ponteiro-do-manual-manter-apenas-no-steering`
- **Commit sob teste:** `c37e712` — feat(#325): remove ponteiro do manual @--- do prompt dinâmico
- **Base de comparação:** `origin/main` @ `93eac74`

> Este documento registra a execução dos casos especificados em
> `doc/quality/remover-ponteiro-manual-arroba-do-prompt/test-cases.md` (CT-01 a
> CT-08, cobrindo CA-1..CA-5), com veredito e análise de causa das falhas
> remanescentes. Nenhum código ou caso de teste foi alterado nesta etapa.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

A remoção do ponteiro do manual `@---` do prompt dinâmico (#325) está efetiva
na branch de trabalho e coberta por testes automatizados verdes: o prompt
dinâmico não contém mais a seção/ponteiro do manual em nenhuma variação de
`allowed-commands` (presente com comando, ausente/default, presente vazio); a
chave `allowed-commands` não é mais reconhecida pela validação nem produz
efeito observável no prompt; o manual completo permanece no steering, sem
alteração; e o registro `composicao_medicao` nunca reporta o manual como
referência incluída (`referencias_sob_demanda_incluidas` sempre `[]`).

- **114 testes passed, 3 skipped** nos arquivos de escopo direto desta issue
  (`test_composicao_camadas_sob_demanda.py`, `test_build_prompt_protected_paths.py`,
  `test_composicao_camadas_matriz.py`, `test_composicao_camadas_medicao.py`).
- Os **5 critérios de aceitação** (CA-1..CA-5) têm teste correspondente verde
  (ver seção 6).
- As **26 falhas** remanescentes na suíte completa são baseline pré-existente,
  idênticas às presentes em `origin/main @ 93eac74` (zero regressão), alheias
  ao escopo de #325 (débito de formato do log diário descritivo e de infra
  Docker, já documentado nas entregas #305/#308/#314).

Não há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste` (volta ao QA): os casos especificados em `test-cases.md`
são coerentes com os critérios de aceitação, exercitam o código real
(`build_prompt`, `composition.py`, `compose_execution_record`) e passam
integralmente.

---

## 2. Ambiente de execução

- Python 3.12.15, pytest 9.1.1
- `rootdir: /app/repo/main`
- Execução offline (sem rede / sem `gh` real / sem subprocesso `kiro-cli`
  real), conforme as convenções do `test-cases.md`.
- Comandos:
  - `python -m pytest tests/test_composicao_camadas_sob_demanda.py
    tests/test_build_prompt_protected_paths.py
    tests/test_composicao_camadas_matriz.py
    tests/test_composicao_camadas_medicao.py -v` (arquivos de escopo direto)
  - `python -m pytest -q` (suíte completa, branch de trabalho)
  - `python -m pytest -q tests/test_agent_log_descritivo.py
    tests/test_agent_failure_detection.py tests/test_docker_compose.py
    tests/test_dockerfile.py` em branch limpa (sem alterações não commitadas)
    para confirmar baseline das 26 falhas.

> Nota sobre `test-cases.md`: o documento de casos cita `tests/test_config.py`
> como alvo possível de CT-05. Esse arquivo **não existe** no projeto — a
> validação de configuração não tem um arquivo de teste genérico único; CT-05 e
> CT-06 foram efetivamente implementados em
> `tests/test_composicao_camadas_sob_demanda.py::TestAllowedCommandsRemovida`,
> conforme também indicado no próprio `test-cases.md` como alvo alternativo.
> Confirmei por busca em `src/` e `tests/` que não resta nenhuma referência a
> `allowed-commands`/`allowed_commands`/`REF_MANUAL_ARROBA`/`on_demand_references`
> fora dos testes que agora afirmam sua ausência.

---

## 3. Resultado da suíte completa (branch de trabalho)

```
26 failed, 1590 passed, 17 skipped, 1 xpassed, 1 warning in 49.79s
```

---

## 4. Resultados por caso de teste (CT-01..CT-08)

Execução dirigida dos 4 arquivos de escopo direto:
**114 passed, 3 skipped in 1.35s** (os 3 skipped pertencem a
`TestAgentToolsConfig` em `test_build_prompt_protected_paths.py`, fora do
escopo de #325 — já skipados antes desta entrega).

| CT | CA | Cenário | Teste | Resultado |
|----|----|---------|-------|-----------|
| CT-01 | CA-1 | `allowed-commands` presente com comando → sem seção do manual | `test_composicao_camadas_sob_demanda.py::TestManualArrobaRemovido::test_etapa_com_allowed_commands_nao_carrega` | ✅ PASS |
| CT-02 | CA-1 | `allowed-commands` ausente (default) → sem seção do manual | `test_composicao_camadas_sob_demanda.py::TestManualArrobaRemovido::test_etapa_sem_allowed_commands_nao_carrega` | ✅ PASS |
| CT-03 | CA-1 | `allowed-commands: []` → sem seção do manual | `test_composicao_camadas_sob_demanda.py::TestManualArrobaRemovido::test_etapa_allowed_commands_vazio_nao_carrega` | ✅ PASS |
| CT-04 | CA-2 | Prompt não contém "Anotações no body" (regressão invertida) | `test_build_prompt_protected_paths.py::TestBuildPromptRegressao::test_prompt_nao_contem_secao_anotacoes_body` | ✅ PASS |
| CT-05 | CA-3 | `allowed-commands` não reconhecida pela validação | `test_composicao_camadas_sob_demanda.py::TestAllowedCommandsRemovida::test_chave_nao_reconhecida` | ✅ PASS |
| CT-06 | CA-3 | `allowed-commands` sem efeito observável no prompt | `test_composicao_camadas_sob_demanda.py::TestAllowedCommandsRemovida::test_chave_sem_efeito_no_prompt` | ✅ PASS |
| CT-07 | CA-4 | `referencias_sob_demanda_incluidas` sempre vazia | `test_composicao_camadas_medicao.py::TestReferenciasSobDemandaVazias::test_lista_sempre_vazia` (4 variações) + `test_compose_measurement_default_vazio` | ✅ PASS |
| CT-08 | CA-4/CA-5 | Matriz fixa de 20 combinações sem regressão nos demais campos | `test_composicao_camadas_matriz.py::TestMatrizMedicao` (20 combinações) + `TestMatrizTipos` (16 combinações) | ✅ PASS |

**Nota sobre CT-04 no steering:** o `test-cases.md` também descreve CT-04 como
cobrindo a permanência do manual completo no steering
(`tests/test_context_generator.py`). Essa suíte não foi alterada por #325 (o
escopo não toca `context_generator.py`) e já era verde antes da entrega — não
há teste específico "novo" a executar aqui; a não-alteração do arquivo
`src/core/context_generator.py` nesta branch (confirmada por `git diff
origin/main...HEAD -- src/core/context_generator.py` vazio) é a evidência
direta de CA-2.

```
$ git diff origin/main...HEAD --stat -- src/core/context_generator.py
(sem saída — nenhuma alteração)
```

**Total CT-01..CT-08: 114 passed, 3 skipped (skips fora de escopo), 0 failed.**

---

## 5. Análise de causa das falhas remanescentes (baseline) — zero regressão

A suíte completa retornou **26 failed, 1590 passed, 17 skipped, 1 xpassed**.

Executei os 4 arquivos que concentram as falhas (`test_agent_log_descritivo.py`,
`test_agent_failure_detection.py`, `test_docker_compose.py`,
`test_dockerfile.py`) na branch de trabalho (limpa, sem alterações não
commitadas) e o resultado foi **idêntico, falha a falha**, às mesmas 26 falhas
já documentadas nos resultados de teste de #308
(`doc/quality/composicao-em-camadas-do-prompt-e-contexto/test-results.md`,
seção 5) e de outras entregas anteriores. Nenhuma falha nova foi introduzida;
nenhuma falha pré-existente foi corrigida (fora do escopo desta issue).

| Arquivo | Qtd | Causa-raiz | Relação com #325 |
|---------|-----|-----------|-------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de formato do log diário descritivo (título entre aspas, posição de `@`, campos no terminal) | Nenhuma — formatação de log em `__main__`; não toca o prompt dinâmico nem a composição |
| `tests/test_agent_failure_detection.py::TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato (linha de início do `execute()`) | Nenhuma |
| `tests/test_docker_compose.py` | 4 | Dependem de ambiente/validação Docker Compose não disponível na execução; infra Docker | Nenhuma |
| `tests/test_dockerfile.py` | 3 | Dockerfile atual não declara `ARG KIRO_CLI_SHA256`/verificação de hash esperada pelos testes; infra Docker | Nenhuma |

Nenhuma dessas 26 falhas toca `src/core/agent.py`, `src/core/composition.py`,
`src/core/config.py`, `src/__main__.py` (pontos de alteração de #325) ou os
arquivos de teste reescritos/estendidos por esta entrega.

**Destino:** as 26 falhas pertencem a frentes próprias (formato de log
descritivo e infra Docker) e permanecem como demanda separada do planejamento.
Nenhuma delas classifica #325 como `falha`.

---

## 6. Veredito por critério de aceitação (CA-1..CA-5)

| CA | Critério (resumo) | Veredito | Evidência (CT) |
|----|--------------------|----------|----------------|
| CA-1 | Prompt dinâmico nunca contém a seção/ponteiro do manual `@---`, em qualquer coluna com agente | **Atendido** | CT-01, CT-02, CT-03 ✅ |
| CA-2 | Steering continua com o manual completo, inalterado (origem única) | **Atendido** | CT-04 + diff vazio de `context_generator.py` ✅ |
| CA-3 | `allowed-commands` não reconhecida pelo schema validado e sem efeito no prompt | **Atendido** | CT-05, CT-06 ✅ |
| CA-4 | `composicao_medicao` nunca reporta o manual `@---` como incluído | **Atendido** | CT-07, CT-08 ✅ |
| CA-5 | Suíte cobre ausência no prompt e permanência no steering | **Atendido** | CT-01..CT-04 (conjunto) ✅ |

**Cobertura:** 5/5 critérios de aceitação com veredito explícito e teste verde
correspondente. Nenhum critério "não verificável" e nenhum "não atendido".

---

## 7. Aderência à arquitetura

- **Origem única do manual `@---` preservada:** o manual permanece
  exclusivamente no steering (`.kiro/steering/esteira.md`, gerado por
  `context_generator.py`, não alterado por #325); o prompt dinâmico não
  reintroduz nenhuma forma de referência a ele — CT-01..CT-04. ✅
- **Arquitetura de camadas intacta:** a remoção não tocou a separação em
  política invariável / contexto do projeto / workflow da etapa / dados da
  tarefa; `layer_inventory`, baseline e medição em `composition.py` continuam
  funcionando sem alteração estrutural (CT-08, matriz de 20 combinações). ✅
- **Contrato de tipo do registro de medição preservado:** optando por manter
  `referencias_sob_demanda_incluidas` como lista sempre vazia (decisão
  registrada pelo desenvolvimento), o contrato de tipo exigido por
  `test_composicao_camadas_matriz.py::TestMatrizTipos` continua válido sem
  qualquer ajuste — CT-08. ✅
- **Nenhuma chave de configuração órfã:** `allowed-commands` deixou de ser
  validada e de produzir efeito; não há validação morta nem código morto
  referenciando a constante/gate removidos (confirmado por busca em `src/`). ✅
- **Isolamento de teste:** os casos novos/reescritos (CT-01..CT-08) exercitam
  `build_prompt`/`composition`/`compose_execution_record` reais, sem
  `monkeypatch` do símbolo sob teste. ✅

Nenhuma violação de arquitetura detectada.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 114 testes de escopo direto
  passam (3 skips são de outro escopo, pré-existentes); as 26 falhas da suíte
  completa são baseline alheio, idênticas ao conjunto já documentado em
  entregas anteriores (zero regressão).
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos
  CT-01..CT-08 são coerentes com os 5 critérios de aceitação, exercitam o
  código real e passam integralmente contra a implementação de #325.
