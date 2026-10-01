# Resultados de Teste — Composição em camadas do prompt e do contexto entregues ao agente

- **Issue:** #308 — "Composição em camadas do prompt e do contexto entregues ao
  agente"
- **Etapa:** Execução de Testes
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/308-composicao-em-camadas-do-prompt-e-contexto`
- **Commit sob teste:** `f1b8fc2` — feat(308): composição em camadas do prompt e
  do contexto
- **Base de comparação:** `origin/main` @ `e0304d0`

> Este documento registra a execução dos casos especificados em
> `test-cases.md` (CT-01 a CT-32, cobrindo CA-1..CA-17), com veredito e análise
> de causa das falhas remanescentes. Nenhum código ou caso de teste foi alterado
> nesta etapa.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

A composição em camadas do prompt e do contexto (#308) está **efetiva na branch
de trabalho** e **coberta por testes automatizados verdes** que atravessam as
quatro camadas (política invariável, contexto do projeto, workflow da etapa,
dados da tarefa), o contrato observável de medição por execução, o gate
fail-closed de instruções obrigatórias, a referência sob demanda do manual
`@---`, a resolução única do nome da branch, a continuidade de sessão, os
metadados de projeto no contexto persistente e os cenários de regressão
(diretório/branch/proteção/arquivos/finalização/transição/isolamento).

- **94 testes** nos 10 arquivos novos `tests/test_composicao_camadas_*.py`
  (CT-01..CT-32) passam integralmente.
- **159 testes** (3 skipped) nos arquivos estendidos/reusados citados na
  rastreabilidade (`test_build_prompt_git_setup`, `test_build_prompt_protected_paths`,
  `test_context_generator`, `test_session_continuation`, `test_steering_integrity`,
  `test_snapshot_guard_call_agent`) passam — sem regressão.
- Os **17 critérios de aceitação** (CA-1..CA-17), além de RN-04/RN-05/RN-08,
  têm teste correspondente verde (ver seção 6).

As **26 falhas** remanescentes na suíte completa são **baseline pré-existente**,
provadamente **idênticas** em `origin/main @ e0304d0` (**zero regressão**),
**alheias** ao escopo de #308 (débito de **formato do log diário descritivo** e
de **infra Docker**). Não constituem reprovação de código desta entrega.

Portanto **não** há classificação `falha` (volta ao desenvolvimento) nem
`revisar-caso-de-teste` (volta ao QA): os casos são coerentes com os critérios de
aceitação, exercitam o código real (função pura de composição/medição em
`src/core/composition.py`, sem acionar `kiro-cli` nem `monkeypatch` do símbolo
sob teste) e passam integralmente.

---

## 2. Ambiente de execução

- Python 3.12, pytest 9.1.1
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso `kiro-cli`
  real): os casos de #308 medem e compõem via funções puras e dispatch mockado,
  conforme as convenções fixadas no `test-cases.md`.
- Comandos:
  - `python -m pytest tests/test_composicao_camadas_*.py -q` (os 10 arquivos
    novos de #308)
  - `python -m pytest tests/test_build_prompt_git_setup.py
    tests/test_build_prompt_protected_paths.py tests/test_context_generator.py
    tests/test_session_continuation.py tests/test_steering_integrity.py
    tests/test_snapshot_guard_call_agent.py -q` (estendidos/reusados)
  - `python -m pytest -q` (suíte completa)
  - comparação de baseline em **worktree limpo** de `origin/main`
    (`git worktree add /tmp/baseline-308 origin/main`), com diff exato do conjunto
    de falhas.

---

## 3. Resultado da suíte completa

```
26 failed, 1456 passed, 17 skipped, 1 xpassed, 1 warning in 47.07s
```

- **1456 passed** — inclui os **94 testes novos** de #308.
- **26 failed** — baseline pré-existente (ver seção 5).
- **17 skipped, 1 xpassed** — inalterados em relação ao baseline.

---

## 4. Resultados por caso de teste (CT-01..CT-32)

Execução dirigida dos 10 arquivos novos de #308: **94 passed in 2.20s**.
Execução dos estendidos/reusados: **159 passed, 3 skipped in 2.31s**. Mapeamento
caso → teste → resultado:

### Grupo A — Medição e contrato observável (`tests/test_composicao_camadas_medicao.py`)

| CT | Critério / cenário | Teste | Resultado |
|----|--------------------|-------|-----------|
| CT-01 | Estático do prompt dinâmico reduz ≥ 40% | `TestReducaoEstatico::test_estatico_reduz_pelo_menos_40_porcento` | ✅ PASS |
| CT-02 | Total sempre carregado reduz ≥ 20% | `TestReducaoTotal::test_total_sempre_carregado_reduz_pelo_menos_20` | ✅ PASS |
| CT-03 | Redução real, não transferência (RN-08) | `TestReducaoNaoEhTransferencia::test_aumento_de_camada_menor_que_reducao_da_outra` | ✅ PASS |
| CT-05 | Instruções obrigatórias carregadas = true | `TestInstrucoesObrigatorias::test_carregadas_true` | ✅ PASS |
| CT-06 | Sem instruções → agente NÃO acionado | `TestInstrucoesObrigatorias::test_ausentes_nao_aciona` | ✅ PASS |
| CT-07 | Falha sinalizada com `false` + motivo | `TestInstrucoesObrigatorias::test_ausentes_registra_motivo` | ✅ PASS |
| CT-32 | Adapter sem tokens → `tokens_entrada: null` | `TestTokensAusentes::test_adapter_sem_tokens_registra_null` | ✅ PASS |
| CT-32 | Adapter com tokens → `int` | `TestTokensAusentes::test_adapter_com_tokens_preenche_int` | ✅ PASS |

### Grupo B — Inventário sem regra duplicada (`tests/test_composicao_camadas_inventario.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-04 | Nenhuma regra em mais de uma camada sempre carregada (RN-04) | `TestInventarioSemDuplicidade::test_nenhuma_regra_em_mais_de_uma_camada_sempre_carregada` | ✅ PASS |
| CT-04 | Cada regra sempre carregada tem camada única | `TestInventarioSemDuplicidade::test_cada_regra_sempre_carregada_tem_camada_unica` | ✅ PASS |
| CT-04 | Inventário cobre as quatro responsabilidades | `TestInventarioSemDuplicidade::test_inventario_cobre_as_quatro_responsabilidades` | ✅ PASS |
| CT-04 | Camadas sempre carregadas são apenas o steering | `TestInventarioSemDuplicidade::test_sempre_carregadas_sao_apenas_steering` | ✅ PASS |
| CT-04 | Manual `@---` tem origem única no steering | `TestInventarioSemDuplicidade::test_manual_arroba_tem_origem_unica_no_steering` | ✅ PASS |

### Grupo C — Referência sob demanda / manual `@---` (`tests/test_composicao_camadas_sob_demanda.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-15 | Etapa sem comando de anotação NÃO carrega o manual | `TestManualArroba::test_etapa_sem_comando_nao_carrega` | ✅ PASS |
| CT-16 | Etapa com comando disponibiliza o manual | `TestManualArroba::test_etapa_com_comando_carrega` | ✅ PASS |
| CT-16 | Etapa default carrega sob demanda | `TestManualArroba::test_etapa_default_carrega_sob_demanda` | ✅ PASS |
| CT-17 | Gate derivado dos comandos permitidos (inclusão) | `TestGateDerivado::test_inclusao_e_funcao_dos_comandos_permitidos` | ✅ PASS |
| CT-17 | Gate derivado — subconjunto sem anotação não inclui | `TestGateDerivado::test_subconjunto_sem_anotacao_nao_inclui` | ✅ PASS |
| CT-17 | Gate derivado — determinismo | `TestGateDerivado::test_determinismo` | ✅ PASS |

### Grupo D — Campos objetivo/passo a passo (`tests/test_composicao_camadas_campos.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-18 | Objetivo e passo a passo em campos próprios | `TestObjetivoPasso::test_ambos_presentes` | ✅ PASS |
| CT-19 | Só objetivo (passo ausente) permanece válido | `TestObjetivoPasso::test_so_objetivo` | ✅ PASS |
| CT-19 | Passo ausente por chave inexistente | `TestObjetivoPasso::test_passo_ausente_chave_inexistente` | ✅ PASS |

### Grupo E — Resolução de branch (`tests/test_composicao_camadas_branch.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-20 | Nome idêntico em criação e merge (RN-05) | `TestBranchResolvidaUnica::test_nome_identico_em_criacao_e_merge` | ✅ PASS |
| CT-20 | Resolução pura e determinística | `TestBranchResolvidaUnica::test_resolucao_pura_deterministica` | ✅ PASS |
| CT-21 | Marcador não resolvível → erro | `TestBranchMarcadorInvalido::test_marcador_nao_resolvivel_erro` | ✅ PASS |
| CT-21 | `build_prompt` propaga `ConfigError` | `TestBranchMarcadorInvalido::test_build_prompt_propaga_config_error` | ✅ PASS |
| CT-21 | Pattern vazio → erro | `TestBranchMarcadorInvalido::test_pattern_vazio_erro` | ✅ PASS |
| CT-22 | Não emite nome parcial/inconsistente | `TestBranchMarcadorInvalido::test_nao_emite_nome_parcial` | ✅ PASS |

### Grupo F — Contexto persistente / metadados (`tests/test_composicao_camadas_contexto.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-23 | Três metadados no contexto persistente | `TestMetadadosProjeto::test_tres_metadados_no_contexto` | ✅ PASS |
| CT-23 | Sem humanos ainda tem nome e descrição | `TestMetadadosProjeto::test_sem_humanos_ainda_tem_nome_e_descricao` | ✅ PASS |
| CT-26 | Steering nunca aparece como gravável no prompt | `TestContextoProtegidoNoPrompt::test_steering_nunca_aparece_como_gravavel_no_prompt` | ✅ PASS |
| CT-26 | Steering entre os protegidos | `TestContextoProtegidoNoPrompt::test_steering_entre_os_protegidos` | ✅ PASS |
| CT-27 | Reescreve quando diverge | `TestIntegridadeContexto::test_reescreve_quando_diverge` | ✅ PASS |
| CT-27 | Íntegro retorna `False` | `TestIntegridadeContexto::test_integro_retorna_false` | ✅ PASS |

### Grupo G — Continuidade de sessão (`tests/test_composicao_camadas_continuidade.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-24 | Continuidade instrui continuar e aponta arquivos | `TestContinuidadeConteudo::test_instrui_continuar_e_aponta_arquivos` | ✅ PASS |
| CT-25 | Continuidade não maior em palavras que a 1ª execução | `TestContinuidadeTamanho::test_continuacao_nao_maior_em_palavras` | ✅ PASS |

### Grupo H — Matriz fixa de medição (`tests/test_composicao_camadas_matriz.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-28 | 20 combinações da matriz fixa | `TestMatrizMedicao::test_vinte_combinacoes` | ✅ PASS |
| CT-28 | Registro presente com campos obrigatórios | `TestMatrizMedicao::test_registro_presente_com_campos_obrigatorios` | ✅ PASS |
| CT-29 | Campos de medição com tipos corretos | `TestMatrizTipos::test_tipos_corretos` | ✅ PASS |

### Grupo I — Versionamento (`tests/test_composicao_camadas_versionamento.py`)

| CT | Cenário | Teste | Resultado |
|----|---------|-------|-----------|
| CT-30 | Seção "Versionar" presente para fluxos Git | `TestVersionamentoObrigatorio::test_secao_versionar_presente_para_fluxos_git` | ✅ PASS |
| CT-30 | `no-branch` não versiona | `TestVersionamentoObrigatorio::test_no_branch_nao_versiona` | ✅ PASS |
| CT-31 | Instrui mensagem que descreve a etapa | `TestMensagemReflecteMudanca::test_instrui_mensagem_que_descreve_etapa` | ✅ PASS |

### Grupo J — Regressões (`tests/test_composicao_camadas_regressao.py` + estendidos)

| CT | Cenário | Alvo | Resultado |
|----|---------|------|-----------|
| CT-08 | Diretório de trabalho obrigatório no prompt | `test_composicao_camadas_regressao.py::TestDiretorioTrabalho` + `test_build_prompt_git_setup.py` | ✅ PASS |
| CT-09 | Preparação de branch (criar/reutilizar) | `TestBranch` + `test_build_prompt_git_setup.py` | ✅ PASS |
| CT-10 | Proteção de estado interno no prompt | `test_build_prompt_protected_paths.py` | ✅ PASS |
| CT-11 | Leitura/escrita dos arquivos da tarefa | `TestArquivosDaTarefa` | ✅ PASS |
| CT-12 | Finalização e transição de coluna | `TestTransicao` | ✅ PASS |
| CT-13 | Nenhum acesso indevido a estado protegido | `test_build_prompt_protected_paths.py` + `test_snapshot_guard_call_agent.py` | ✅ PASS |
| CT-14 | Isolamento de repositório/diretório (RN-06) | `TestIsolamentoRepo` | ✅ PASS |

**Total #308 (10 arquivos novos):** 94 passed, 0 failed.
**Total estendidos/reusados (6 arquivos):** 159 passed, 3 skipped, 0 failed.

---

## 5. Análise de causa das falhas remanescentes (baseline) — zero regressão

A suíte completa retornou **26 failed, 1456 passed, 17 skipped, 1 xpassed**.

**Prova objetiva de zero regressão.** Executei os 4 arquivos que concentram as
falhas na branch de trabalho e, em paralelo, em um **worktree limpo** de
`origin/main @ e0304d0` (base da branch de #308, anterior aos commits `6257fc0`
e `f1b8fc2`). Comparei o conjunto de IDs de teste que falham em cada lado com
`diff`:

```
=== DIFF of FAILED test IDs (empty = identical) ===
IDENTICAL: failures match exactly
```

- `origin/main @ e0304d0`: **26 failed, 221 passed, 6 skipped** (nos 4 arquivos).
- branch `feature/308-...`: **mesmas 26 falhas**, byte a byte (26 ids = 26 ids).
- Falhas **novas** introduzidas por #308: **0**.
- Falhas **"corrigidas"** por #308: **0**.

Classificação das 26 falhas de baseline — todas pré-existentes e **fora do escopo
de #308** (não tocam a composição em camadas, o contrato de medição, o gate
fail-closed, a resolução de branch nem o contexto persistente):

| Arquivo | Qtd | Causa-raiz | Relação com #308 |
|---------|-----|-----------|-------------------|
| `tests/test_agent_log_descritivo.py` | 18 | Débito de **formato do log diário descritivo** (título entre aspas, posição de `@`, campos no terminal) | Nenhuma — formatação de log em `__main__`; não toca a composição |
| `tests/test_agent_failure_detection.py::TestExecuteUsaDeteccao::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Mesmo débito de formato (linha de início do `execute()`) | Nenhuma |
| `tests/test_docker_compose.py` | 4 | Dependem de ambiente/validação Docker Compose não disponível na execução; divergência de **infra Docker** | Nenhuma |
| `tests/test_dockerfile.py` | 3 | Dockerfile atual não declara `ARG KIRO_CLI_SHA256`/verificação de hash esperada pelos testes; **infra Docker** | Nenhuma |

**Destino:** as 26 falhas pertencem a frentes próprias (formato de log descritivo
e infra Docker), já conhecidas das execuções anteriores (#305, #314). **Não** são
corrigidas aqui — corrigi-las ampliaria o escopo e esta etapa não altera código.
Permanecem como demanda separada do planejamento. Nenhuma delas classifica #308
como `falha`.

---

## 6. Veredito por critério de aceitação (CA-1..CA-17)

| CA | Critério (resumo) | Veredito | Evidência (CT) |
|----|-------------------|----------|----------------|
| CA-1 | Estático do prompt dinâmico ≥ 40% menor | **Atendido** | CT-01 ✅ |
| CA-2 | Total sempre carregado ≥ 20% menor (real) | **Atendido** | CT-02, CT-03 ✅ |
| CA-3 | Nenhuma regra em mais de uma camada (RN-04) | **Atendido** | CT-04 ✅ |
| CA-4 | Registro `instrucoes_obrigatorias_carregadas: true` | **Atendido** | CT-05 ✅ |
| CA-5 | Sem instruções → não aciona + sinaliza falha + motivo | **Atendido** | CT-06, CT-07 ✅ |
| CA-6 | Cenários de referência sem regressão | **Atendido** | CT-08..CT-12 ✅ |
| CA-7 | Sem acesso indevido a estado protegido + isolamento (RN-06) | **Atendido** | CT-13, CT-14 ✅ |
| CA-8 | Manual `@---` sob demanda (gate por comandos) | **Atendido** | CT-15, CT-16, CT-17 ✅ |
| CA-9 | Objetivo + passo a passo em campos próprios; passo opcional | **Atendido** | CT-18, CT-19 ✅ |
| CA-10 | Nome de branch resolvido idêntico (RN-05) | **Atendido** | CT-20 ✅ |
| CA-11 | Marcador não resolvível → erro, sem nome inconsistente | **Atendido** | CT-21, CT-22 ✅ |
| CA-12 | Metadados de projeto no contexto persistente | **Atendido** | CT-23 ✅ |
| CA-13 | Continuidade: não maior em palavras, instrui continuar | **Atendido** | CT-24, CT-25 ✅ |
| CA-14 | Contexto persistente na raiz protegido (RN-02) | **Atendido** | CT-26, CT-27 ✅ |
| CA-15 | Matriz fixa (20 combinações) com medição p/ todas | **Atendido** | CT-28, CT-29 ✅ |
| CA-16 | Commit/PR refletem a mudança; versionamento não é pulado | **Atendido** | CT-30, CT-31 ✅ |
| CA-17 | Adapter sem tokens → `tokens_entrada: null`, sem falhar | **Atendido** | CT-32 ✅ |

**Cobertura:** 17/17 critérios de aceitação com veredito explícito e teste verde
correspondente. Nenhum critério "não verificável" e nenhum "não atendido".

---

## 7. Aderência à arquitetura

- **Composição como função pura no núcleo (não no adapter):** a classificação de
  camadas, o inventário auditável e a medição vivem em `src/core/composition.py`
  (`layer_inventory`, `find_duplicated_rules`, composição/medição); o adapter e o
  orquestrador consomem — conforme a nota de implementação do `test-cases.md`. ✅
- **Camada sempre carregada com origem única (RN-04):** o manual `@---` passou a
  ter origem única no steering; no prompt dinâmico entra, no máximo, um ponteiro
  sob demanda — CT-04 e CT-15/16/17 comprovam. ✅
- **Redução real, não transferência (RN-08):** CT-03 assegura economia líquida
  (o aumento de uma camada sempre carregada é estritamente menor que a redução da
  outra). ✅
- **Fail-closed de instruções obrigatórias:** sem o contexto obrigatório, o
  agente **não é acionado** e a falha é registrada
  (`instrucoes_obrigatorias_carregadas: false` + motivo) — CT-06/CT-07. ✅
- **Estado protegido preservado (RN-02):** `.kiro/steering/**/*.md` permanece em
  `PROTECTED_PATHS`; `ensure_steering_integrity` reescreve em divergência —
  CT-26/CT-27, mais `test_build_prompt_protected_paths` e
  `test_snapshot_guard_call_agent` verdes. ✅
- **Isolamento de repositório (RN-06):** CT-14 confina o agente ao `work_dir` do
  clone resolvido, sem referência ao diretório da esteira. ✅
- **Isolamento de teste (anti-#106):** os casos medem via função pura e dispatch
  mockado; não há `monkeypatch` do símbolo sob teste. ✅

Nenhuma violação de arquitetura detectada.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 94 testes de #308 e os 159
  estendidos/reusados passam; as 26 falhas da suíte são baseline alheio,
  provadamente idênticas a `origin/main @ e0304d0` (zero regressão).
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos
  CT-01..CT-32 são coerentes com os 17 critérios de aceitação, exercitam o código
  real e passam integralmente. Os casos `[novo]`, escritos antes do código,
  agora passam porque a implementação os satisfez — não houve reprovação por
  ausência de implementação.
