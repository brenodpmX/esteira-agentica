# Resultados de Execução — Gate de `participation_intent` em `keep_task` com evento deduplicado

- **Task:** #258 — Adicionar gate de `participation_intent` em `keep_task` com evento deduplicado
- **User Story:** #245 — Gate de elegibilidade por intenção confirmada em `keep_task`
- **Documento de casos de teste:** `doc/quality/integridade-de-issues-entre-boards/casos-de-teste/test-cases-gate-participation-intent-keep-task.md`
- **Branch:** `task/258-adicionar-gate-de-participation-intent-em-keep-task`
- **Commit sob teste:** `982a30c` — Gate de participation_intent em keep_task com evento deduplicado (#258)
- **Executor:** Camila Rocha - Engenheira de Qualidade (QA)
- **Data:** 2026-09-15

## Veredito

**APROVADO.** Todos os casos de teste (CT-01..CT-13) resultaram em `pass`.
Nenhuma regressão introduzida pela task. Aderência arquitetural confirmada
(gate sem chamada de rede, sem uso de `BoardPort`/adapter).

## Comandos executados

1. Subset alvo:
   `python -m pytest tests/ -k "keep_task or participation_intent or auto_advance" -v`
   → **40 passed, 1155 deselected** (inclui os 23 testes de
   `tests/test_participation_intent_gate.py` que cobrem CT-01..CT-13).

2. Suíte completa:
   `python -m pytest`
   → **1138 passed, 34 skipped, 1 xpassed, 22 failed**.

## Resumo

| Métrica | Valor |
|---------|-------|
| Casos de teste (CT-01..CT-13) | 13 |
| Casos aprovados (pass) | 13 |
| Casos reprovados (fail) | 0 |
| Casos bloqueados (blocked) | 0 |
| Testes automatizados executados (subset alvo) | 40 passed |
| Testes da suíte completa | 1138 passed / 34 skipped / 1 xpassed |
| Falhas na suíte completa | 22 (todas pré-existentes, ver abaixo) |
| Regressões introduzidas pela task | 0 |

## Resultado por caso de teste

| Caso | Descrição | Teste automatizado correspondente | Status |
|------|-----------|-----------------------------------|--------|
| CT-01 | `origin` em coluna elegível é selecionada | `TestSelecaoConfirmada::test_intencao_confirmada_e_selecionada[origin]` | ✅ pass |
| CT-02 | `authorized` em coluna elegível é selecionada | `TestSelecaoConfirmada::test_intencao_confirmada_e_selecionada[authorized]` | ✅ pass |
| CT-03 | `propagated` é ignorada na seleção | `TestSelecaoFalhaFechada::test_intencao_nao_confirmada_e_ignorada[propagated]` | ✅ pass |
| CT-04 | `unresolved` é ignorada na seleção | `TestSelecaoFalhaFechada::test_intencao_nao_confirmada_e_ignorada[unresolved]` | ✅ pass |
| CT-05 | campo ausente / `None` / `""` ignorados (falha fechada) | `test_campo_ausente_e_ignorado` + `test_intencao_nao_confirmada_e_ignorada[None]` + `[]` | ✅ pass |
| CT-06 | `_has_confirmed_intent` tabela-verdade (8 entradas) | `TestHasConfirmedIntent::test_tabela_verdade[issue0..issue7]` | ✅ pass |
| CT-07 | `todo` sem intenção não sofre auto-advance | `TestAutoAdvanceGate::test_sem_intencao_nao_faz_auto_advance[propagated]` e `[__omit__]` | ✅ pass |
| CT-08 | `todo` com intenção confirmada faz auto-advance | `TestAutoAdvanceGate::test_com_intencao_confirmada_auto_advance_ocorre` | ✅ pass |
| CT-09 | duas issues na mesma coluna: só a confirmada é candidata | `TestConvivenciaIssues::test_apenas_confirmada_e_candidata` | ✅ pass |
| CT-10 | evento deduplicado por (board, coluna, issue) | `TestEventoDeduplicado::test_evento_emitido_uma_unica_vez` | ✅ pass |
| CT-11 | evento re-emitido ao mudar de coluna (nova chave) | `TestEventoDeduplicado::test_evento_reemitido_ao_mudar_de_coluna` | ✅ pass |
| CT-12 | gate NÃO consome/reinicia o cooldown de reexecução | `TestGateAntesDoCooldown::test_nao_grava_cooldown_para_issue_bloqueada` | ✅ pass |
| CT-13 | gate sem chamada de rede (fake `BoardPort` que falha se chamado) | `TestSemRede::test_gate_nao_toca_board_port` | ✅ pass |

## Rastreamento de critérios de aceite

| Critério | Descrição | Evidência | Status |
|----------|-----------|-----------|--------|
| CA1 | Implementação segue arquitetura (gate lê só o snapshot local, sem rede) | CT-06 (helper puro) + CT-13 (fake `BoardPort` `_ExplodingBoardPort` não é invocado) | ✅ atendido |
| CA2 | Código cobre o cenário descrito (gate nos dois pontos + evento deduplicado) | CT-01..CT-12; gate confirmado em `src/__main__.py` no auto-advance do `todo` (antes de `_auto_advance`) e na seleção (antes de `_in_rerun_cooldown`) | ✅ atendido |
| CA3 | Testes unitários criados | `tests/test_participation_intent_gate.py` (23 testes) | ✅ atendido |
| CA4 | Sem quebra de funcionalidades existentes | Subset de regressão 40 passed; suíte completa sem regressão nova (as 22 falhas são pré-existentes) | ✅ atendido |
| CA-Story-2 | Entrada sem intenção falha fechada + evento deduplicado | CT-03/04/05/07/09/10/11 | ✅ atendido |
| CA-Story-7 | Gate sem chamada de rede, verificável por fake `BoardPort` | CT-13 | ✅ atendido |

## Aderência arquitetural

- O gate vive inteiramente em `src/__main__.py`
  (`_has_confirmed_intent`, `_unconfirmed_intent_logged`,
  `_log_unconfirmed_intent_once`) e lê apenas o `dict` da issue já carregado do
  `Snapshot` local. Nenhum import ou uso de adapter/`BoardPort` no caminho do gate.
- CT-13 substitui `src.__main__.board` por um `_ExplodingBoardPort` cujo
  `__getattr__` levanta `AssertionError` em qualquer método. Os três caminhos do
  gate (seleção confirmada, bloqueio + evento, `todo` não confirmado) executam
  sem disparar o fake — **nenhuma violação de camada / chamada de rede**.
- Verificação por inspeção do código:
  - Auto-advance do `todo`: `if not _has_confirmed_intent(issue): _log_unconfirmed_intent_once(...); continue`
    aplicado **antes** de `_auto_advance`.
  - Seleção: gate aplicado **após** `_is_blocked` e **antes** de
    `_in_rerun_cooldown` / `_mark_rerun`, como exigido (não consome cooldown de
    issue nunca despachada — confirmado por CT-12).

## Falhas pré-existentes (não relacionadas à task)

As 22 falhas da suíte completa estão em:
- `tests/test_dockerfile.py` (3) — verificação SHA256 / `KIRO_CLI_SHA256` no Dockerfile;
- `tests/test_agent_log_descritivo.py` (18) — formatação do log descritivo do agente;
- `tests/test_agent_failure_detection.py` (1) — formato da linha inicial do epic.

Evidência de que são pré-existentes: as mesmas 22 falhas ocorrem no commit base
`faf290c` (anterior a todo o trabalho da task #258), reproduzidas executando
`python -m pytest tests/test_dockerfile.py tests/test_agent_log_descritivo.py tests/test_agent_failure_detection.py`
com o repositório em `faf290c` → **22 failed, 99 passed, 13 skipped**.

O commit de desenvolvimento `982a30c` altera apenas `src/__main__.py` e os
arquivos de teste de participation-intent/cooldown/auto-advance — nenhum desses
arquivos toca Dockerfile ou log de agente. Portanto **não há regressão**
introduzida por esta task.

## Bugs encontrados

Nenhum. Nenhum bug registrado.

— Camila Rocha - Engenheira de Qualidade (QA)
