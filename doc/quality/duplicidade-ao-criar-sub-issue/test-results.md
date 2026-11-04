# Resultados de Teste — Duplicidade ao criar sub-issue

- **Issue:** #339 — "Duplicidade ao criar sub-issue"
- **Etapa:** Execução de Testes
- **Autora:** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-11-04
- **Branch:** `feature/339-duplicidade_ao_criar_sub_issue`
- **Commit sob teste:** `90a21aa` — fix(339): propaga config a
  `_apply_create_up` e evita recriar issue no create-up
- **Commit de casos de teste:** `ab6cf0f` — test(339): casos de teste para
  duplicidade ao criar sub-issue

> Este documento registra a execução dos casos especificados em
> `test-cases.md` (CT-01..CT-05, cobrindo CA-1..CA-3), com veredito. Nenhum
> código ou caso de teste foi alterado nesta etapa.

---

## 1. Veredito

**APROVADO — avançar para `documentacao`.**

A correção (propagar `config` como parâmetro de `_apply_create_up` e
repassá-lo a partir de `apply_changes`) elimina o `NameError: name 'config'
is not defined` relatado na issue. Os testes em
`tests/test_create_up_config_nameerror.py`, originalmente especificados para
documentar o bug (RED, antes da correção — ver `test-cases.md`), foram
reescritos pelo desenvolvimento para afirmar o comportamento correto e
**passam integralmente** contra o código corrigido:

- `create_issue` é chamado **exatamente uma vez** por item de fila, mesmo
  com `max_attempts` em `{1, 3, 5}` — não há mais recriação a cada tentativa
  (cobre CA-1/CA-2, grupo que antes demonstrava a triplicação).
- `_apply_create_up` aceita **qualquer** comando não vazio no bloco `@---`
  (`/parent`, `/labels`, `/need_human`, `/blocked_by`) sem levantar exceção,
  e conclui o fluxo (issue criada, arquivo local renomeado) — superfície de
  disparo mais ampla identificada na etapa de Casos de Teste, agora coberta
  pela correção.
- `config` é propagado por `apply_changes` até `_apply_create_up` (espião
  confirma o mesmo dict recebido) e é parâmetro opcional (`config: dict =
  None`), sem quebrar chamadas que não o informam.
- Nenhum evento `participation_classified` / `participation_reconciled` /
  `participation_reconcile_failed` / `dispatch_blocked_unconfirmed_intent` é
  emitido no cenário mesmo-board, e `_board_of_issue` resolve `None` sem
  presença conhecida em outro board — confirma que `participation_intent`
  (#310) não participa da causa (CA-3).
- O débito identificado na suíte existente (`test_sanitize_relations.py` com
  `id=` em vez de `identifier=`) foi corrigido; o teste agora de fato
  exercita `_apply_create_up` e confirma que `item.id` isolado (sem
  `identifier`) não aciona o adapter — comportamento preservado.

**46/46 testes pertinentes passam** (15 em
`tests/test_create_up_config_nameerror.py` + 31 em
`tests/test_sanitize_relations.py`, incluindo o caso corrigido). A suíte
completa roda com **as mesmas 26 falhas e 13 erros pré-existentes**, todos
de Docker/ambiente/log-descritivo — nenhuma regressão.

Não há classificação `falha` (as mudanças de código e de teste estão
corretas e cobertas) nem `revisar-caso-de-teste` (os casos de
`test-cases.md`, embora escritos antes da correção existir, continuam
coerentes com os critérios de aceitação; passaram a VERDE porque o
comportamento que documentavam como bug foi corrigido — não há caso
inadequado ou que precise de revisão).

---

## 2. Ambiente de execução

- Python 3.12.16, pytest 9.2.0
- `rootdir: /app/repo/main`
- Execução **offline** (sem rede / sem `gh` real / sem subprocesso
  `kiro-cli` real): os casos exercitam `src/core/sync.py` com `BoardPort`
  fake (`FakePort`, padrão de `tests/test_sanitize_relations.py` e
  `tests/test_error_classification.py`), sem `monkeypatch` do símbolo sob
  teste (lição do incidente #106).
- Comandos:
  - `python -m pytest tests/test_create_up_config_nameerror.py
    tests/test_sanitize_relations.py -v` (arquivos pertinentes à mudança)
  - `python -m pytest tests/ -q` (suíte completa)

---

## 3. Resultado da execução dirigida (arquivos pertinentes)

```
46 passed in 0.38s
```

| Arquivo | Testes | Resultado |
|---------|--------|-----------|
| `tests/test_create_up_config_nameerror.py` | 15 | ✅ 15 passed |
| `tests/test_sanitize_relations.py` | 31 | ✅ 31 passed |

---

## 4. Resultado da suíte completa

```
26 failed, 1707 passed, 17 skipped, 1 xpassed, 1 warning, 13 errors in 75.69s
```

Confirmação de que nenhuma falha/erro toca os arquivos da mudança: busca por
`sync|create_up|sanitize|339|participation` nos nomes de teste reprovados
não retorna nenhuma ocorrência. As 26 falhas e 13 erros são os mesmos já
reportados nas etapas anteriores desta issue (Casos de Teste e
Desenvolvimento) — débito de **formato do log diário descritivo**
(`tests/test_agent_log_descritivo.py`, `tests/test_agent_failure_detection.py`)
e de **infraestrutura Docker** (`tests/test_docker_compose.py`,
`tests/test_dockerfile.py`), nenhum relacionado a `_apply_create_up`, ao
parâmetro `config` ou a `participation_intent`.

---

## 5. Resultados por caso de teste

| CT | Cenário | Teste(s) | Resultado |
|----|---------|----------|-----------|
| CT-01 | `create_up` com `/parent` conclui sem erro; `set_parent` aplicado; arquivo renomeado | `TestCreateUpComComandos::test_parent_e_aplicado_e_arquivo_renomeado_com_id`, `test_config_e_opcional` | ✅ PASS |
| CT-02 | `apply_changes` chamado N vezes (N em 1/3/5) não recria a issue — `create_issue` chamado 1 única vez; `config` propagado | `TestApplyChangesNaoDuplicaIssue::test_create_issue_chamado_uma_unica_vez[1\|3\|5]`, `test_apply_changes_propaga_config_ao_create_up` | ✅ PASS (4) |
| CT-03 | Qualquer comando não vazio (`/parent`, `/labels`, `/need_human`, `/blocked_by`) conclui sem erro; sem bloco de comandos também conclui | `TestCreateUpComComandos::test_create_up_com_comandos_conclui_sem_erro[...]` (4 variações), `test_sem_bloco_de_comandos_conclui` | ✅ PASS (5) |
| CT-04 | Nenhum evento `participation_*` emitido; `_board_of_issue` não resolve board distinto sem presença conhecida | `TestParticipationIntentNaoParticipa::test_nenhum_evento_de_participation_e_emitido`, `test_board_of_issue_nao_resolve_board_distinto_sem_presenca` | ✅ PASS |
| CT-05 | Item com `id=` (em vez de `identifier=`) não chama o adapter — teste da suíte existente corrigido | `TestCreateUpIdentificadorDoItem::test_item_com_id_em_vez_de_identifier_nao_chama_adapter` (novo) + `tests/test_sanitize_relations.py::test_apply_create_up_self_reference_not_sent_to_adapter` (corrigido) | ✅ PASS |

**Nota sobre CT-01/CT-02/CT-03 em relação ao `test-cases.md`:** os casos
foram especificados na etapa de Casos de Teste para confirmar o bug (RED,
`NameError` esperado) antes de a correção existir. O desenvolvimento
reescreveu as asserções desses mesmos testes para afirmar o comportamento
corrigido (sem exceção, 1 `create_issue`, `config` propagado), mantendo o
vínculo com os mesmos CAs (CA-1/CA-2) e o mesmo cenário (qualquer comando
não vazio no `@---`, não só `/parent`). Não há caso de teste órfão: todo
teste continua rastreável a um CT e a um CA.

---

## 6. Veredito por critério de aceitação (CA-1..CA-3)

| CA | Critério (resumo) | Veredito | Evidência |
|----|--------------------|----------|-----------|
| CA-1 | Investigação reproduz/confirma a causa da triplicação via `create-up` | **Atendido** — e corrigido: CT-02 confirma que, pós-fix, `create_issue` é chamado exatamente 1 vez por item, independente de `max_attempts` | ✅ |
| CA-2 | Causa documentada com precisão de arquivo/função/variável/chamada (`_apply_create_up`, `config`, `_filter_suspended_cross_board_parent`) | **Atendido** — `config` agora é parâmetro de `_apply_create_up` (linha 1188) e propagado na chamada da linha 1219; CT-01/CT-03 confirmam ausência do `NameError` para toda a superfície de disparo identificada | ✅ |
| CA-3 | Confirmação de que `participation_intent` (#310) não participa da causa no cenário mesmo-board | **Atendido** | CT-04 ✅ |

**Cobertura:** 3/3 critérios de aceitação com veredito explícito e teste
verde correspondente.

---

## 7. Aderência à arquitetura

- **Escopo da correção é mínimo e cirúrgico:** `_apply_create_up` ganhou
  apenas o parâmetro `config: dict = None` e `apply_changes` passou a
  repassá-lo; nenhuma outra assinatura ou contrato de `BoardPort` foi
  alterado. ✅
- **Compatibilidade retroativa:** `config` é opcional (`= None`);
  `test_config_e_opcional` confirma que chamadas que não informam `config`
  continuam funcionando. ✅
- **Isolamento de teste (anti-#106):** os testes exercitam
  `sync._apply_create_up` e `sync.apply_changes` reais, com `BoardPort` fake
  e, quando necessário, espião por `monkeypatch` apenas sobre o próprio
  `_apply_create_up` para capturar o `config` recebido — sem jamais
  monkeypatchar o código sob teste de forma a mascarar a ausência de
  cobertura (lição do incidente #106: PR #102 original). ✅
- **`participation_intent` (#310) permanece intocado:** nenhuma alteração
  em `src/core/participation_reconcile.py` ou no guard de
  `_filter_suspended_cross_board_parent`; CT-04 confirma que o mecanismo
  simplesmente não é alcançado neste cenário, hoje e após a correção. ✅
- **Teste da suíte existente corrigido no mesmo lote:** `id=` →
  `identifier=` em `test_sanitize_relations.py`, conforme o débito (CT-05)
  identificado na etapa de Casos de Teste — a suíte agora oferece a
  cobertura que o teste sempre afirmou ter. ✅

Nenhuma violação de arquitetura detectada.

---

## 8. Classificação final

- **Sucesso** → **advance** para a coluna `documentacao`.
- **Não** há reprovação de código (`falha`): os 46 testes pertinentes
  passam; as 26 falhas / 13 erros da suíte completa são baseline alheio
  (Docker/ambiente/log-descritivo), já reportado idêntico nas etapas
  anteriores desta mesma issue — zero regressão.
- **Não** há caso de teste inadequado (`revisar-caso-de-teste`): os casos
  CT-01..CT-05 continuam rastreáveis aos CA-1..CA-3, a mudança de asserção
  (de RED documentando o bug para GREEN confirmando a correção) foi feita
  pelo desenvolvimento no mesmo commit da correção de código, de forma
  coerente com o cenário especificado — não há ambiguidade nem contradição a
  devolver ao QA.
