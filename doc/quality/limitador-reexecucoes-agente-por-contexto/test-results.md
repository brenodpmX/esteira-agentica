# Resultados de Teste — Limitador de reexecuções de agente por contexto com contenção e retomada humana

- **Issue:** #306 — "Limitador de reexecuções de agente por contexto com
  contenção e retomada humana"
- **Etapa:** Execução de Testes
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/306-limitador-reexecucoes-agente-por-contexto`
- **Commit sob teste:** `8493643` — feat(306): limitador de reexecucoes de
  agente por contexto
- **Base de comparação:** `83f1f45` — Merge pull request #322 (base da branch,
  anterior a qualquer trabalho de #306)

> Este documento registra a execução dos casos especificados em
> `test-cases.md` (CT-01..CT-21 e CT-SRC-01, cobrindo CA-1..CA-13 e os RNF
> testáveis sem rede), com veredito e análise de causa das falhas remanescentes.
> Nenhum código ou caso de teste foi alterado nesta etapa.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

O limitador de reexecuções de agente por contexto `(board, coluna, issue)` (#306)
está **efetivo na branch de trabalho** e **coberto por testes automatizados
verdes** que atravessam o núcleo de contagem no instante da entrega, a janela
deslizante com borda fechada em `T`, o bloqueio antes do dispatch, a sinalização
idempotente (`need_human` + comentário com os cinco dados mínimos + marcador
oculto), o reinício da franquia e a retomada humana, a persistência atômica
fail-closed, a recuperação de interrupção, a validação estrita da configuração na
inicialização, o gate de capacidade de label do adaptador, a proteção do estado
interno e a fonte única da contagem.

- **112 testes passam** (3 skipped pré-existentes de `generate_native_agents`)
  nos 4 arquivos pertinentes à mudança:
  - `tests/test_agent_circuit_break.py` — núcleo (CT-01..CT-21, CT-SRC-01);
  - `tests/test_agent_circuit_break_config.py` — validação de forma (CT-13/13b);
  - `tests/test_startup_agent_circuit_break.py` — gate de capacidade (CT-18);
  - `tests/test_build_prompt_protected_paths.py` — estado protegido (CT-20).
- Os **13 critérios de aceitação** (CA-1..CA-13) têm teste correspondente verde
  (ver seção 6).

As **26 falhas** remanescentes na suíte completa são **baseline pré-existente**,
provadamente **idênticas** em `83f1f45` (**zero regressão**), **alheias** ao
escopo de #306 (débito de **formato do log diário descritivo** e de **infra
Docker**). Não constituem reprovação de código desta entrega.

Portanto **não** há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste` (volta ao QA): os casos são coerentes com os critérios de
aceitação, exercitam o código real (núcleo em `src/core/agent_circuit_break.py`,
com `BoardPort` fake, relógio controlável e dispatch espião — sem acionar
`kiro-cli` nem fazer `monkeypatch` do símbolo sob teste, lição #106) e passam
integralmente.

---

## 2. Ambiente de execução

- Python 3.12, pytest
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso `kiro-cli`
  real): os casos de #306 exercitam o núcleo via `BoardPort` fake espião, relógio
  controlável (`monkeypatch` de `time.time`) e dispatch espião, conforme as
  convenções fixadas no `test-cases.md`.
- Comandos:
  - `python -m pytest tests/test_agent_circuit_break.py
    tests/test_agent_circuit_break_config.py
    tests/test_startup_agent_circuit_break.py
    tests/test_build_prompt_protected_paths.py -v` (os 4 arquivos pertinentes)
  - `python -m pytest -q` (suíte completa)
  - comparação de baseline por checkout de `83f1f45` (base da branch, anterior ao
    trabalho de #306), rodando os 4 arquivos que concentram as falhas e
    confrontando o conjunto de IDs.

---

## 3. Resultado da suíte completa

```
26 failed, 1516 passed, 17 skipped, 1 xpassed, 1 warning in 494.30s (0:08:14)
```

- **1516 passed** — inclui os **112 testes** de #306.
- **26 failed** — baseline pré-existente (ver seção 5).
- **17 skipped, 1 xpassed** — inalterados em relação ao baseline.

Execução dirigida dos 4 arquivos de #306:

```
112 passed, 3 skipped in 1.85s
```

(os 3 skips são de `generate_native_agents` em
`tests/test_build_prompt_protected_paths.py`, pré-existentes e alheios a #306.)

---

## 4. Resultados por caso de teste

Mapeamento caso → teste → resultado. Todos os casos do `test-cases.md` têm teste
automatizado verde correspondente.

### Grupo A — Contagem, janela e isolamento por contexto (`tests/test_agent_circuit_break.py`)

| CT | Critério / cenário | Teste | Resultado |
|----|--------------------|-------|-----------|
| CT-01 | Limite atingido bloqueia a 4ª entrega | `TestCT01LimiteAtingidoBloqueia::test_limite_bloqueia_quarta_entrega` | ✅ PASS |
| CT-01b | Excedente não conta como entrega efetiva | `TestCT01LimiteAtingidoBloqueia::test_excedente_nao_conta_como_entrega` | ✅ PASS |
| CT-02 | Abaixo do limite executa normalmente | `TestCT02AbaixoDoLimite::test_abaixo_do_limite_executa` | ✅ PASS |
| CT-03 | Sucesso sem avanço também conta | `TestCT03SucessoSemAvancoConta::test_cada_entrega_conta_independente_do_resultado` | ✅ PASS |
| CT-04 | Bordas da janela `T-1` conta; `T`/`T+1` não (param.) | `TestCT04BordasDaJanela::test_bordas_T_menos_1_T_T_mais_1[-1-True / 0-False / 1-False]` | ✅ PASS (3) |
| CT-05 | Mudança de coluna reinicia contagem | `TestCT05CT06MudancaDeColuna::test_mudanca_de_coluna_reinicia` | ✅ PASS |
| CT-06 | Revisita de coluna começa do zero | `TestCT05CT06MudancaDeColuna::test_revisita_de_coluna_comeca_do_zero` | ✅ PASS |
| CT-10 | Isolamento: issue bloqueada não trava a fila | `TestCT10Isolamento::test_issue_com_need_human_e_pulada_outra_e_selecionada` | ✅ PASS |
| CT-21 | Precisão sob repetição intensa (≥ 32 execuções) | `TestCT21PrecisaoSobRepeticaoIntensa::test_nunca_excede_N_em_32_tentativas` | ✅ PASS |
| CT-21 | Nunca excede `N` entre bloqueios com liberação | `TestCT21PrecisaoSobRepeticaoIntensa::test_nunca_excede_N_entre_bloqueios_com_liberacao` | ✅ PASS |

### Grupo B — Sinalização, reinício da franquia e retomada (`tests/test_agent_circuit_break.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-07 | Label `need_human` aplicada pela porta do board | `TestCT07SinalizacaoCompleta::test_label_aplicada` | ✅ PASS |
| CT-07 | Um comentário com os cinco dados + marcador oculto | `TestCT07SinalizacaoCompleta::test_um_comentario_com_cinco_dados_e_marcador` | ✅ PASS |
| CT-08/09 | Contagem zerada no bloqueio e franquia completa na retomada | `TestCT08CT09ReinicioFranquiaERetomada::test_contagem_zerada_apos_bloqueio_e_franquia_completa` | ✅ PASS |
| CT-14 | Um comentário por evento; novo evento após liberação | `TestCT14UmComentarioPorEvento::test_um_comentario_por_evento_e_novo_evento_apos_liberacao` | ✅ PASS |
| CT-15 | Idempotência: marcador presente não republica | `TestCT15IdempotenciaComentarioNaRetomada::test_marcador_presente_nao_republica` | ✅ PASS |
| CT-16 | Bloqueio não move a issue de coluna (zero `move_issue`) | `TestCT16BloqueioNaoMoveColuna::test_zero_move_issue_no_bloqueio` | ✅ PASS |

### Grupo C — Sem política e ativação (opt-in, não regressão) (`tests/test_agent_circuit_break.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-11 | Sem política: nunca bloqueia, mas conta internamente | `TestCT11SemPolitica::test_sem_politica_nunca_bloqueia_mas_conta` | ✅ PASS |
| CT-11b | Coexistência com cooldown ativo, sem interferência | `TestCT11bCoexistenciaCooldown::test_cooldown_opera_sem_limitador` | ✅ PASS |
| CT-12 | Ativação após execuções já contadas, sem retroação | `TestCT12AtivacaoSemRetroacao::test_ativar_politica_nao_bloqueia_retroativamente` | ✅ PASS |

### Grupo D — Validação da configuração (`tests/test_agent_circuit_break_config.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-13 | Só `executions`, sem `window` → cita o caminho | `TestConfigInvalida::test_so_executions_sem_window` | ✅ PASS |
| CT-13 | Só `window`, sem `executions` → cita o caminho | `TestConfigInvalida::test_so_window_sem_executions` | ✅ PASS |
| CT-13 | `executions` booleano rejeitado antes de int | `TestConfigInvalida::test_executions_booleano_rejeitado_antes_de_int` | ✅ PASS |
| CT-13 | `window` booleano rejeitado antes de int | `TestConfigInvalida::test_window_booleano_rejeitado_antes_de_int` | ✅ PASS |
| CT-13 | `executions < 1` → cita o caminho | `TestConfigInvalida::test_executions_menor_que_1` | ✅ PASS |
| CT-13 | `window < 1` → cita o caminho | `TestConfigInvalida::test_window_menor_que_1` | ✅ PASS |
| CT-13 | `executions` float não-int rejeitado | `TestConfigInvalida::test_executions_float_rejeitado` | ✅ PASS |
| CT-13 | `window` float não-int rejeitado | `TestConfigInvalida::test_window_float_rejeitado` | ✅ PASS |
| CT-13 | `executions` string rejeitada | `TestConfigInvalida::test_executions_string_rejeitado` | ✅ PASS |
| CT-13 | Campo desconhecido no bloco rejeitado | `TestConfigInvalida::test_campo_desconhecido_rejeitado` | ✅ PASS |
| CT-13 | Bloco não-mapa rejeitado | `TestConfigInvalida::test_bloco_nao_e_mapa` | ✅ PASS |
| CT-13 | Falha antes de qualquer alteração de estado | `TestConfigInvalida::test_falha_antes_de_qualquer_alteracao_de_estado` | ✅ PASS |
| CT-13 | Bloco dentro de `boards` rejeitado como board inválido | `TestBlocoDentroDeBoards::test_dentro_de_boards_e_rejeitado_como_board_invalido` | ✅ PASS |
| CT-13b | Bloco válido aceito | `TestConfigValida::test_bloco_valido_aceito` | ✅ PASS |
| CT-13b | Bloco ausente aceito (política inativa) | `TestConfigValida::test_bloco_ausente_aceito` | ✅ PASS |
| CT-13b | Inteiros `>= 1` aceitos (param.) | `TestConfigValida::test_inteiros_maiores_igual_1_aceitos[1-1 / 5-3600 / 10-86400]` | ✅ PASS (3) |
| CT-13b | Política ausente resolve como inativa | `TestResolvePolicy::test_ausente_inativa` | ✅ PASS |
| CT-13b | Política presente resolve ativa com valores | `TestResolvePolicy::test_presente_ativa_com_valores` | ✅ PASS |

### Grupo E — Falha fechada, capacidade do adaptador, recuperação e segurança

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-17a | Persistência da ocorrência falha → admissão negada | `TestCT17FalhaFechada::test_persistencia_falha_nega_admissao` | ✅ PASS |
| CT-17b | Estado corrompido → admissão negada, sem assumir vazio | `TestCT17FalhaFechada::test_estado_corrompido_nega_admissao` | ✅ PASS |
| CT-17b | `version` desconhecida → admissão negada | `TestCT17FalhaFechada::test_versao_desconhecida_nega_admissao` | ✅ PASS |
| CT-18 | Política ativa + adaptador sem label → falha na init | `TestCheckLabelCapability::test_politica_ativa_sem_label_falha` | ✅ PASS |
| CT-18 | Política ativa + adaptador com label → init passa | `TestCheckLabelCapability::test_politica_ativa_com_label_passa` | ✅ PASS |
| CT-18 | Política ativa + adaptador real GitHub → init passa | `TestCheckLabelCapability::test_politica_ativa_adaptador_real_passa` | ✅ PASS |
| CT-18 | Sem política → não falha mesmo sem label | `TestCheckLabelCapability::test_sem_politica_nao_falha_mesmo_sem_label` | ✅ PASS |
| CT-18 | Detecção de capacidade (sem/com/real) | `TestAdapterCapability::test_sem_capacidade_detectado` / `test_com_capacidade_detectado` / `test_adaptador_real_github_tem_capacidade` | ✅ PASS (3) |
| CT-19a | Reinício entre persistir e label: segue negada e reconcilia | `TestCT19Recuperacao::test_19a_reinicio_entre_persistir_e_label_segue_negada_e_reconcilia` | ✅ PASS |
| CT-19b | Label ok, comentário pendente: retoma só o faltante | `TestCT19Recuperacao::test_19b_label_ok_comentario_pendente_retoma_so_o_faltante` | ✅ PASS |
| CT-19c | Reinício não apaga ocorrências nem libera bloqueio | `TestCT19Recuperacao::test_19c_reinicio_nao_apaga_ocorrencias_nem_libera` | ✅ PASS |
| CT-20 | Estado não contém corpo/prompt/token | `TestCT20SegurancaDoEstado::test_estado_nao_contem_corpo_prompt_token` | ✅ PASS |
| CT-20 | Arquivo de estado em `PROTECTED_PATHS` | `TestCT20SegurancaDoEstado::test_arquivo_de_estado_em_protected_paths` | ✅ PASS |

### Grupo F — Fonte única da contagem (integração #307/#315)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-SRC-01 | Uma ocorrência por entrega (fonte única) | `TestCTSRC01FonteUnica::test_uma_ocorrencia_por_entrega` | ✅ PASS |

### Grupo G — Proteção do estado em `PROTECTED_PATHS` (`tests/test_build_prompt_protected_paths.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-20 | Guard levanta para `agentCircuitBreak.json` | `TestAssertNoProtected::test_guard_levanta_para_agent_circuit_break` | ✅ PASS |
| CT-20 | Estado do limitador em `PROTECTED_PATHS` | `TestCircuitBreakStateProtegido::test_arquivo_de_estado_em_protected_paths` | ✅ PASS |
| CT-20 | Padrão declarado + mensagem identifica o arquivo | `TestCircuitBreakStateProtegido::test_padrao_declarado` / `test_guard_mensagem_identifica_arquivo` | ✅ PASS (2) |
| CT-20 | Sem falso positivo para nomes similares / `throttle.yaml` | `TestCircuitBreakStateProtegido::test_guard_nao_falso_positivo_para_nomes_similares` / `test_guard_nao_falso_positivo_para_throttle_yaml` | ✅ PASS (2) |

**Total #306 (4 arquivos):** 112 passed, 0 failed (3 skipped pré-existentes de
`generate_native_agents`).

---

## 5. Análise de causa das falhas remanescentes (baseline) — zero regressão

A suíte completa retornou **26 failed, 1516 passed, 17 skipped, 1 xpassed**.

**Prova objetiva de zero regressão.** Executei os 4 arquivos que concentram as
falhas em `83f1f45` (base da branch, anterior aos commits `898a554` e `8493643`
de #306):

```
=== BASELINE 83f1f45 — tests/test_agent_failure_detection.py tests/test_agent_log_descritivo.py tests/test_docker_compose.py tests/test_dockerfile.py ===
26 failed, 221 passed, 6 skipped
```

- `83f1f45` (baseline, sem #306): **26 failed** — mesmas 26 falhas, mesmos
  arquivos.
- branch `feature/306-...` (com #306): **as mesmas 26 falhas** na suíte completa.
- Falhas **novas** introduzidas por #306: **0**.
- Falhas **"corrigidas"** por #306: **0**.

Além disso, o commit `8493643` toca **apenas** arquivos de #306
(`src/core/agent_circuit_break.py` [novo], `src/core/config.py`,
`src/__main__.py`, `src/core/agent.py` [+1 linha em `PROTECTED_PATHS`], os 4
arquivos de teste e a documentação). Nenhum dos arquivos de teste que falham é
tocado pela entrega.

Classificação das 26 falhas de baseline — todas pré-existentes e **fora do escopo
de #306** (não tocam contagem, janela, bloqueio, sinalização, persistência,
validação de config nem o gate de capacidade):

| Arquivo | Qtd | Causa-raiz | Relação com #306 |
|---------|-----|-----------|-------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de **formato do log diário descritivo** (título entre aspas, posição de `@`, campos no terminal) | Nenhuma — formatação de log em `__main__`; não toca o limitador |
| `tests/test_agent_failure_detection.py::TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato (linha de início do `execute()`) | Nenhuma |
| `tests/test_docker_compose.py` | 4 | Dependem de ambiente/validação Docker Compose não disponível na execução; divergência de **infra Docker** | Nenhuma |
| `tests/test_dockerfile.py` | 3 | Dockerfile atual não declara `ARG KIRO_CLI_SHA256`/verificação de hash esperada pelos testes; **infra Docker** | Nenhuma |

**Destino:** as 26 falhas pertencem a frentes próprias (formato de log descritivo
e infra Docker), já conhecidas das execuções anteriores (#305, #308). **Não** são
corrigidas aqui — corrigi-las ampliaria o escopo e esta etapa não altera código.
Permanecem como demanda separada do planejamento. Nenhuma delas classifica #306
como `falha`.

---

## 6. Veredito por critério de aceitação (CA-1..CA-13)

| CA | Critério (resumo) | Veredito | Evidência (CT) |
|----|-------------------|----------|----------------|
| CA-1 | `N` execuções em `T` → próxima não inicia | **Atendido** | CT-01, CT-01b, CT-02 ✅ |
| CA-2 | Sucesso sem avanço de coluna também conta | **Atendido** | CT-03 ✅ |
| CA-3 | Ocorrência com idade `>= T` não contribui | **Atendido** | CT-04 (T-1/T/T+1) ✅ |
| CA-4 | Mudança de coluna reinicia; revisita começa do zero | **Atendido** | CT-05, CT-06 ✅ |
| CA-5 | Bloqueio → `need_human` + comentário com os 5 dados | **Atendido** | CT-07 ✅ |
| CA-6 | Contagem zerada imediatamente após o bloqueio | **Atendido** | CT-08 ✅ |
| CA-7 | Retomada humana → franquia completa, sem resíduo | **Atendido** | CT-09 ✅ |
| CA-8 | Issue bloqueada não trava a fila | **Atendido** | CT-10 ✅ |
| CA-9 | Sem política: nenhum bloqueio, comportamento preservado | **Atendido** | CT-11, CT-11b ✅ |
| CA-10 | Ativação sem reprocessamento retroativo | **Atendido** | CT-12 ✅ |
| CA-11 | Config inválida → falha citando o caminho, antes de estado | **Atendido** | CT-13, CT-13b ✅ |
| CA-12 | Um comentário por evento; idempotência na retomada | **Atendido** | CT-14, CT-15 ✅ |
| CA-13 | O bloqueio não move a issue de coluna | **Atendido** | CT-16 ✅ |

**Cobertura:** 13/13 critérios de aceitação com veredito explícito e teste verde
correspondente. Nenhum critério "não verificável" e nenhum "não atendido".

RNF testáveis sem rede também cobertos e verdes: RNF-01 (CT-21, ≥32 execuções),
RNF-05 (CT-09), RNF-06 (CT-11/CT-11b), RNF-09 (CT-19a/b/c), RNF-10 (CT-20),
RNF-11 (CT-13); e a **fonte única** da contagem (CT-SRC-01).

---

## 7. Aderência à arquitetura

- **Núcleo no core, não no adapter:** a contagem por contexto, a janela
  deslizante, a máquina de estados do `trip` e a persistência atômica vivem em
  `src/core/agent_circuit_break.py`; `src/__main__.py::call_agent` consome o gate
  **antes** de `_dispatch_with_recovery` — mesmo padrão fail-closed do gate de
  composição (#308). ✅
- **Fonte única da contagem (RN-01, integração #307/#315):** há **um** registro
  de ocorrência por entrega, no instante da entrega; o limitador consome essa
  fonte sem instanciar contador paralelo — CT-SRC-01 trava o invariante. ✅
- **Identidade do contexto `(board, coluna, issue)` (RN-02):** mudar de coluna
  substitui o registro por um contexto vazio; revisita começa do zero —
  CT-05/CT-06. ✅
- **Borda da janela fechada em `T` (RN-03):** contam só ocorrências com idade
  **estritamente menor que `T`** — CT-04 param. ✅
- **Opt-in estrito (RN-07):** sem o bloco, zero bloqueio e comportamento vigente
  preservado, inclusive com cooldown ativo; a contagem interna continua —
  CT-11/CT-11b/CT-12. ✅
- **Validação de config no padrão da casa (RNF-11):** `ConfigError` citando o
  caminho, `bool` rejeitado antes de `int`, bloco opcional de **raiz** (fora de
  `boards`), em `check_config()` antes de `InstanceLock.acquire()` — CT-13. ✅
- **Gate de capacidade do adaptador:** política ativa + adaptador sem label real
  → falha na inicialização, sem aparentar que sinalizou — CT-18. ✅
- **Estado protegido (RNF-10):** `.pipe/agentCircuitBreak.json` em
  `PROTECTED_PATHS`; `build_prompt` rejeita o caminho; o estado não contém corpo
  de issue, prompt, conversa, token ou credencial — CT-20. ✅
- **Fail-closed na persistência / integridade:** falha ao persistir ou estado
  corrompido nega a admissão (não assume contagem vazia) — CT-17a/b. ✅
- **Recuperabilidade (RNF-09):** reinício não apaga ocorrências nem libera
  bloqueio; sinalização pendente retomada sem duplicar comentário — CT-19a/b/c. ✅
- **Isolamento de teste (anti-#106):** os casos exercitam o núcleo real com
  `BoardPort` fake, relógio controlável e dispatch espião; sem `monkeypatch` do
  símbolo sob teste. ✅

Nenhuma violação de arquitetura detectada.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 112 testes de #306 passam; as 26
  falhas da suíte são baseline alheio, provadamente idênticas a `83f1f45` (zero
  regressão).
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos
  CT-01..CT-21 e CT-SRC-01 são coerentes com os 13 critérios de aceitação,
  exercitam o código real e passam integralmente. Os casos, escritos antes do
  código na etapa de Casos de Teste, agora passam porque a implementação os
  satisfez — não houve reprovação por ausência de implementação.
