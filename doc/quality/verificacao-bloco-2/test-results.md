# Resultados de Teste / Relatório de Verificação — Bloco 2 (estrutura de board, contexto do agente e limites de execução)

- **Issue:** #315 — "Verificação do bloco 2 — estrutura de board, contexto do
  agente e limites de execução" (auditoria integrada das entregas #305, #306,
  #307 e #308)
- **Etapa:** Desenvolvimento
- **Autor(a):** Sofia Carvalho — Engenheira de Software PL
- **Data:** 2026-10-02
- **Branch:** `feature/315-verificacao-bloco-2`
- **Base da verificação:** `origin/main` @ `dd3a634`

> Este documento consolida o **relatório de verificação** do bloco 2, com um
> **veredito por critério de aceitação (CA-1..CA-7)** apoiado em comportamento
> observado no código ou em teste executado — nunca em releitura de texto. Esta
> é uma **entrega de verificação**: o produto é este relatório. O único artefato
> de código é o teste de regressão da convergência (CT-04), que fecha a lacuna
> de cobertura de um critério já aceito (CA-6) — não é alteração de produto.

---

## 1. Veredito

**APROVADO — SEM DIVERGÊNCIA — avançar para `execucao-testes`.**

As quatro entregas do bloco (#305, #306, #307, #308) estão **efetivas na linha
principal** e **coexistem sem que uma anule, sombreie ou mascare a outra** no
ponto de convergência do produto (`src/__main__.py::call_agent`), comprovado por
teste automatizado que exercita o **código real** de `_admit_circuit_break`
(#306) e `_write_execution_record` (#307) juntos
(`tests/test_convergencia_bloco2_execucao.py`).

Resultado "**sem divergência**" (CA-3 / CT-05): **nenhuma alteração em `src/`**
e **sem incremento de versão** atribuíveis a esta verificação
(`git diff --stat origin/main...HEAD` restringe-se a
`doc/quality/verificacao-bloco-2/` + o teste novo em `tests/`). O único código
novo é o teste de regressão da convergência (CT-04), que fecha a lacuna de
cobertura registrada em CT-02 de um critério já aceito (CA-6) — não é alteração
de produto, logo não exige bump nem entrada no `CHANGELOG.md`.

As **26 falhas** remanescentes na suíte completa são **baseline pré-existente**,
provadamente **idênticas** por nome de arquivo antes e depois da mudança (zero
regressão nova), **alheias** a #305/#306/#307/#308 (formato de log descritivo +
infraestrutura Docker), e ficam registradas como **demanda separada** (CA-5).
Portanto **não** há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste`.

---

## 2. Ambiente de execução

- Python 3.12.15, pytest 9.1.1, pluggy 1.6.0
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso real;
  `KiroCliAgent` e `_dispatch_with_recovery` substituídos por espião no teste de
  convergência; relógio real com janela 3600s >> duração do teste)
- Comandos executados:
  - `python -m pytest -q` (suíte completa — CT-01) — **antes** e **depois** da
    adição do teste de convergência;
  - suíte das quatro entregas (24 arquivos) — CT-02/CT-03;
  - `python -m pytest tests/test_convergencia_bloco2_execucao.py -v` (CT-04);
  - `git diff --stat origin/main...HEAD` e `git status --porcelain` (CT-05).

---

## 3. Resultados por caso de teste (CT-01..CT-05)

### CT-01 — Suíte completa na linha principal → **registrada**

- **CA:** CA-2.
- **Execução:** `python -m pytest -q` em `/app/repo/main`.
- **Sumário (baseline, antes da mudança):** **1579 passed, 26 failed, 17
  skipped, 1 xpassed** (63,73s).
- **Sumário (após adicionar o teste de CT-04):** **1583 passed (+4), 26 failed,
  17 skipped, 1 xpassed** (60,08s).
- **Falhas (idênticas nos dois momentos, por arquivo):**
  - `tests/test_agent_log_descritivo.py` — 18 (formato de log descritivo);
  - `tests/test_agent_failure_detection.py` — 1 (formato de linha do log);
  - `tests/test_docker_compose.py` — 4 (infraestrutura Docker);
  - `tests/test_dockerfile.py` — 3 (infraestrutura Docker).
- **Resultado:** a suíte foi executada e registrada integralmente. As 26 falhas
  recebem destino explícito (seção 4) — nenhuma silenciada; **zero regressão
  nova** atribuível ao bloco 2 (o conjunto de arquivos falhos é o mesmo antes e
  depois da única mudança desta verificação). ✅ **PASS** (CA-2 satisfeito).

### CT-02 — Auditoria de cobertura / lacuna registrada → **PASS**

- **CA:** CA-1 (veredito por critério com evidência) e CA-7 ("não verificável"
  com razão).
- **Execução:** mapeamento CA(#305, #306, #307, #308) → testes reais em
  `tests/`, confrontados com os `test-cases.md` de origem (seção 5).
- **Resultado:** cobertura confirmada para todos os CA das quatro entregas (ver
  seção 5 e a suíte das 24 fontes: **261 passed, 0 failed** em 5,04s). A
  **lacuna de convergência** (#306 × #307 no `call_agent` real) registrada na
  etapa de casos de teste — a suíte de integração do #307 sempre mockava
  `_admit_circuit_break` como `True`, nunca exercitando a política real do
  limitador junto da gravação do registro — foi **fechada** por CT-04 dentro do
  escopo do bloco (CA-6). Nenhum CA ficou "não verificável": todos têm meio de
  verificação disponível. ✅ **PASS**.

### CT-03 — Comportamento declarado ausente na linha principal → **não aplicável (sem divergência)**

- **CA:** CA-4 (divergência corrigível ⇒ regressão + bump + CHANGELOG) e CA-5
  (divergência que exige escopo novo ⇒ demanda separada).
- **Execução:** confronto, por CA, do declarado em cada `test-cases.md` de
  origem com o comportamento presente (código + teste verde correspondente).
- **Resultado:** **nenhum comportamento declarado e ausente** foi encontrado nas
  quatro entregas. Todos os pontos de ancoragem citados existem de fato no
  código (`src/core/column_withdrawal.py`, `src/core/agent_circuit_break.py`,
  `src/core/execution_record.py`, `src/core/composition.py`, e os gates
  encadeados em `src/__main__.py::call_agent`) e têm teste verde. Logo **nenhum
  veredito "não atendido"** foi emitido, **nenhuma correção de produto** foi
  aplicada e **nenhum bump/CHANGELOG** foi gerado. O desfecho é CT-05. ✅ **N/A
  — sem divergência**.

### CT-04 — Convergência #306 × #307 no ponto de decisão `call_agent` → **PASS**

- **CA:** CA-6.
- **Arquivo:** `tests/test_convergencia_bloco2_execucao.py` (**novo**, 4
  sub-casos). Exercita o **código real** de `_admit_circuit_break` (#306) e
  `_write_execution_record` (#307) no mesmo `call_agent`; patches **apenas** nas
  fronteiras de ambiente (`KiroCliAgent`, `ensure_steering_integrity`,
  `compose_execution_record`, `_dispatch_with_recovery` como espião) e
  `pipe.board` injetado com capacidade real de label para o caminho de bloqueio.
  **Nenhum** `monkeypatch` dos símbolos sob teste (respeita a lição do incidente
  #106).
- **Execução:** `python -m pytest tests/test_convergencia_bloco2_execucao.py -v`
  → **4 passed** (1,37s).
- **Sub-casos e o que comprovam:**
  - **CT-04a** `test_ct04a_dentro_do_limite_admite_e_grava_registro`: dentro do
    limite, a admissão (#306) conta a entrega (1 ocorrência no contexto, sem
    `trip`) **e** o registro de execução (#307) é gravado (`records_for_issue`
    com 1 item `concluída`, board/etapa coerentes). As duas fontes avançam
    juntas.
  - **CT-04b** `test_ct04b_limite_bloqueia_e_nao_grava_registro_excedente`: com
    3 ocorrências reais semeadas por 3 `call_agent` prévios, a 4ª tentativa é
    **bloqueada** pelo limitador — dispatch **não** ocorre (espião não chamado),
    `need_human` aplicado, e **nenhum registro novo** de #307 é gravado
    (`records_for_issue` permanece em 3). Nenhuma tentativa bloqueada "vaza"
    como registro fantasma — o #307 não mascara o bloqueio do #306.
  - **CT-04c**
    `test_ct04c_falha_composicao_bloqueia_antes_do_limitador_e_do_registro`:
    quando a composição (#308) recusa
    (`instrucoes_obrigatorias_carregadas: False`), `call_agent` retorna **antes**
    de contar no limitador e **antes** de gravar registro — a ordem de gates
    (#308 → #306 → dispatch → #307) é preservada; o contexto do limitador nem
    sequer é criado.
  - **CT-04d**
    `test_ct04d_classificacao_fiel_com_limitador_ativo_dentro_do_limite`: com o
    limitador ativo e dentro do limite, três desfechos sucessivos (`SUCEDIDO`,
    `UNKNOWN_OUTCOME`/dispatch failure, `FALHA`) produzem registros com
    `resultado` fiel (`concluída`, `interrompida`, `falha terminal`) — a
    presença do limitador não altera nem atrasa a classificação do #307, e cada
    entrega é contada pelo limitador.
- **Resultado:** existe **evidência automatizada e executável** de que #306 e
  #307 co-existem no mesmo ponto de decisão sem sombreamento mútuo. Se a
  convergência regredir (registro gravado para tentativa bloqueada, ou limitador
  deixando de contar por causa do registro), o teste falha. ✅ **PASS**.

### CT-05 — Verificação sem divergência (relatório, sem código, sem bump) → **PASS**

- **CA:** CA-3.
- **Execução:**
  - `src/core/version.py` → `VERSION = "1.20.0"` (inalterada);
  - `CHANGELOG.md` → seções `1.17.0` (#305), `1.18.0` (#308), `1.19.0` (#306),
    `1.20.0` (#307) presentes; **nenhuma entrada nova** inventada para esta
    verificação;
  - `git diff --stat origin/main...HEAD` → somente
    `doc/quality/verificacao-bloco-2/test-cases.md` (etapa anterior) +, nesta
    etapa, o relatório e o teste de convergência; **nenhuma mudança em `src/`**.
- **Resultado:** o desfecho é **"sem divergência"**: `VERSION` inalterada,
  CHANGELOG sem entrada nova, diff restrito a documentação de qualidade e ao
  teste de regressão de CT-04. ✅ **PASS**.

---

## 4. Destino das 26 falhas de baseline (CA-2 / CA-5)

As 26 falhas são **pré-existentes** na linha principal, não introduzidas por
esta verificação (o conjunto de arquivos falhos é **idêntico** antes — 1579
passed / 26 failed — e depois — 1583 passed / 26 failed — da única mudança desta
etapa, que apenas **adiciona** 4 testes verdes). Elas se concentram em dois
temas, ambos **alheios** a #305/#306/#307/#308:

| Tema | Arquivos | Nº | Natureza |
|------|----------|----|----------|
| Formato de log descritivo | `test_agent_log_descritivo.py`, `test_agent_failure_detection.py` | 19 | Divergência de formato de linha de log — não toca board/limitador/registro/composição |
| Infraestrutura Docker | `test_docker_compose.py`, `test_dockerfile.py` | 7 | Versões pinadas / SHA-256 / config de compose — ambiente de build, não o motor |

**Destino (CA-5):** registradas como **demanda separada** — já constam como
baseline pré-existente em `doc/quality/verificacao-bloco-1/test-results.md` e nas
notas de execução de
`doc/quality/composicao-em-camadas-do-prompt-e-contexto/test-cases.md`. Corrigi-las
**excede o escopo** da verificação do bloco 2 (não são divergência das quatro
entregas auditadas). Não há, portanto, classificação `falha` nem
`revisar-caso-de-teste` para esta issue.

---

## 5. Veredito por critério de aceitação das entregas (CA-1)

Cada CA abaixo recebe veredito **atendido / não atendido / não verificável** com
evidência (nome do teste executado ou observação estrutural). Todas as suítes
citadas foram executadas em conjunto: **261 passed, 0 failed** (5,04s).

### #305 — Retirada segura de colunas (CHANGELOG 1.17.0)

| Critério (resumo) | Veredito | Evidência |
|---|---|---|
| Política validar→drenar→confirmar→contrair | **Atendido** | `tests/test_column_withdrawal.py` (verde); núcleo `src/core/column_withdrawal.py` |
| Coluna vazia retirada após leitura remota confirmar zero | **Atendido** | `tests/test_column_withdrawal.py`, `tests/test_full_sync_order.py` |
| Destino ausente/inválido bloqueia sem mover | **Atendido** | `tests/test_column_migrations_config.py` (validação de forma), `tests/test_column_withdrawal.py` |
| Retomada após interrupção deriva do estado remoto | **Atendido** | `tests/test_column_withdrawal.py` |
| Evidência `column_migration_attempt` observável | **Atendido** | `tests/test_column_migration_evidence.py` |
| Validação de forma de `column-migrations` | **Atendido** | `tests/test_column_migrations_config.py`, `tests/test_github_board_contract.py` |

### #306 — Limitador de reexecuções por contexto (CHANGELOG 1.19.0)

| Critério (resumo) | Veredito | Evidência |
|---|---|---|
| Teto por janela: bloqueia a N+1 | **Atendido** | `tests/test_agent_circuit_break.py::TestCT01LimiteAtingidoBloqueia` |
| Janela: idade `< T` conta, `== T` expira | **Atendido** | `tests/test_agent_circuit_break.py::TestCT04BordasDaJanela` |
| Identidade `(board, coluna, issue)`; mudar coluna reinicia | **Atendido** | `tests/test_agent_circuit_break.py::TestCT05CT06MudancaDeColuna` |
| Sinalização: `need_human` + comentário idempotente | **Atendido** | `TestCT07SinalizacaoCompleta`, `TestCT14UmComentarioPorEvento`, `TestCT15IdempotenciaComentarioNaRetomada` |
| Reinício de franquia e retomada humana | **Atendido** | `TestCT08CT09ReinicioFranquiaERetomada` |
| Opt-in: sem política nada bloqueia, mas conta | **Atendido** | `TestCT11SemPolitica`, `TestCT12AtivacaoSemRetroacao` |
| Fail-closed em corrupção/persistência | **Atendido** | `TestCT17FalhaFechada`, `TestCT19Recuperacao` |
| Isolamento: issue bloqueada não trava a fila | **Atendido** | `TestCT10Isolamento`, `TestCT11bCoexistenciaCooldown` |
| Validação de config + gate de capacidade de label | **Atendido** | `tests/test_agent_circuit_break_config.py`, `tests/test_startup_agent_circuit_break.py` |
| Estado em `PROTECTED_PATHS`, sem conteúdo sensível | **Atendido** | `TestCT20SegurancaDoEstado` |

### #307 — Registro de execução + linhagem (CHANGELOG 1.20.0)

| Critério (resumo) | Veredito | Evidência |
|---|---|---|
| Um registro por execução em qualquer desfecho | **Atendido** | `tests/test_execution_record_integration.py`, `tests/test_execution_record.py` |
| Taxonomia fechada de `resultado` (nunca vazio) | **Atendido** | `tests/test_execution_record.py` (`map_resultado`) |
| Resultado técnico × avanço são independentes (RN-01) | **Atendido** | `tests/test_execution_record_integration.py::test_call_agent_grava_interrompida_com_avanco` |
| Repetição sem avanço derivada | **Atendido** | `tests/test_execution_record.py` |
| Consumo com proveniência; indisponível ≠ zero | **Atendido** | `tests/test_execution_record.py`, `tests/test_execution_record_surface.py` |
| Linhagem reconstruída dos registros próprios | **Atendido** | `tests/test_execution_lineage.py` |
| Retenção própria `registro.retencao_dias` | **Atendido** | `tests/test_execution_record_retention.py`, `tests/test_execution_record_config.py` |
| Fonte única da contagem (sem contador paralelo) | **Atendido** | `tests/test_execution_record_integration.py::test_call_agent_um_registro_por_execucao` |

### #308 — Composição em camadas (CHANGELOG 1.18.0)

| Critério (resumo) | Veredito | Evidência |
|---|---|---|
| Redução de camadas / inventário sem duplicidade | **Atendido** | `tests/test_composicao_camadas_medicao.py`, `tests/test_composicao_camadas_inventario.py` |
| Gate do manual `@---` sob demanda | **Atendido** | `tests/test_composicao_camadas_sob_demanda.py` |
| Campos de objetivo/passos/git da etapa | **Atendido** | `tests/test_composicao_camadas_campos.py` |
| Nome de branch único por execução | **Atendido** | `tests/test_composicao_camadas_branch.py` |
| Metadados e contexto SEMPRE carregado (steering) | **Atendido** | `tests/test_composicao_camadas_contexto.py` |
| Fail-closed sem instruções obrigatórias | **Atendido** | `tests/test_composicao_camadas_medicao.py`, `tests/test_composicao_camadas_contexto.py` |
| Continuidade de sessão | **Atendido** | `tests/test_composicao_camadas_continuidade.py` |
| Matriz 5×2×2 / versionamento / regressão de prompt | **Atendido** | `tests/test_composicao_camadas_matriz.py`, `tests/test_composicao_camadas_versionamento.py`, `tests/test_composicao_camadas_regressao.py` |
| `tokens_entrada: null` sem falhar (kiro-cli) | **Atendido** | `tests/test_composicao_camadas_medicao.py` |

### Convergência do bloco (CA-6)

| Critério (resumo) | Veredito | Evidência |
|---|---|---|
| #306 e #307 efetivos em conjunto no `call_agent`, sem sombreamento | **Atendido** | `tests/test_convergencia_bloco2_execucao.py` (CT-04a..d, 4 passed) |

---

## 6. Rastreabilidade CA (issue #315) → caso → veredito

| CA | Caso | Veredito |
|----|------|----------|
| CA-1 (relatório com veredito por critério) | CT-01/CT-02 + este relatório (seção 5) | **Atendido** |
| CA-2 (suíte executada; falha corrigida ou registrada) | CT-01 + seção 4 | **Atendido** |
| CA-3 (sem divergência ⇒ sem código/sem bump) | CT-05 | **Atendido** |
| CA-4 (divergência corrigível ⇒ regressão+bump+CHANGELOG) | CT-03 | **N/A** (nenhuma divergência encontrada) |
| CA-5 (divergência que exige escopo novo ⇒ demanda separada) | CT-03 + seção 4 | **Atendido** (26 falhas de baseline registradas como demanda separada) |
| CA-6 (duas entregas no mesmo ponto de decisão, efetivas em conjunto) | CT-04 | **Atendido** |
| CA-7 (critério não verificável ⇒ veredito com razão) | CT-02 | **Atendido** (nenhum CA ficou não verificável; todos têm meio de verificação) |

---

## 7. Conclusão

O bloco 2 está **íntegro na linha principal**: as quatro entregas estão
efetivas, cobertas por teste verde, e **coexistem sem sombreamento** no ponto de
convergência (`call_agent`), agora comprovado por teste de regressão real
(`tests/test_convergencia_bloco2_execucao.py`). Coerência versão↔CHANGELOG
confirmada (1.17.0/1.18.0/1.19.0/1.20.0). **Nenhuma divergência** foi encontrada;
portanto **sem alteração de `src/` e sem incremento de versão**. As 26 falhas de
baseline são alheias ao bloco e ficam como demanda separada.

**Desfecho: SEM DIVERGÊNCIA — avançar para `execucao-testes`.**
