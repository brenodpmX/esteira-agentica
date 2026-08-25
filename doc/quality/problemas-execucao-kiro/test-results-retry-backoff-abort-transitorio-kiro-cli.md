# Resultados de Teste — Avaliar e implementar retry com backoff para abort transitório do kiro-cli (dispatch failure / InternalServerError)

Status: approved
Owner: quality
Last updated: 2026-08-25

## Inputs

- Casos de teste: `doc/quality/problemas-execucao-kiro/test-cases-retry-backoff-abort-transitorio-kiro-cli.md` (CT-001 a CT-010)
- Task #208 (board `task`, etapa Execução de Testes)
- ADR normativa: `doc/architecture/retry-kiro-cli/idempotencia.md`
- Implementação: `src/adapters/kiro_cli_agent.py` (commit `d32c0af`)
- Suíte automatizada nova: `tests/test_kiro_cli_unknown_outcome.py` (40 testes)

## Execução

```
python -m pytest tests/test_kiro_cli_unknown_outcome.py -v
python -m pytest tests/test_agent_failure_detection.py tests/test_error_classification.py -q
python -m pytest tests/test_build_prompt_protected_paths.py tests/test_dead_letter.py tests/test_instance_lock.py tests/test_orphan_detection.py -q
python -m pytest tests/ -q
```

## CT-001 — `dispatch failure` real do incidente #203 gera exatamente uma invocação do subprocesso

**Resultado:** passed

**Observações:**
- `TestCT001DispatchFailureInvocacaoUnica` (4 testes) confirma 1 única chamada
  ao subprocesso, classificação `UNKNOWN_OUTCOME`, marcador `dispatch failure`
  identificado e registro no bloco `## Resultado` do log.

## CT-002 — `InternalServerError` após output parcial gera uma única chamada

**Resultado:** passed

**Observações:**
- `TestCT002InternalServerErrorAposOutputParcial` (3 testes) cobre exit != 0 e
  exit == 0 (erro reportado sem exit-code de falha) — ambos classificados
  `UNKNOWN_OUTCOME`, com 1 única invocação.

## CT-003 — Timeout é classificado como `UNKNOWN_OUTCOME`, não como falha definitiva

**Resultado:** passed

**Observações:**
- `TestCT003TimeoutAmbiguo` (4 testes): marcador `[TIMEOUT]` preservado,
  classificação `UNKNOWN_OUTCOME`, nenhuma segunda invocação, e — ponto que a
  ADR exige e que antes da implementação não era garantido — `session_id`
  preservado mesmo no timeout.

## CT-004 — Output integral, request ID e erro permanecem disponíveis para auditoria

**Resultado:** passed

**Observações:**
- `TestCT004Observabilidade` (6 testes): extração de `request_id` nos dois
  formatos reais (`request_id:` e `Request ID:`), ausência de request_id não
  quebra, erro extraído identifica a causa real, output integral e bloco
  `## Resultado` persistidos no log.

## CT-005 — `session_id` descoberto após o abort é preservado no índice de sessões

**Resultado:** passed

**Observações:**
- `TestCT005SessaoPreservadaNoAbort` (4 testes): `session_id` persistido no
  `SessionIndex` mesmo com abort, exposto no log/observabilidade, e ausência de
  sessão disponível não quebra a execução. Não-regressão confirmada.

## CT-006 — Entrega posterior retoma via `--resume-id` pelo fluxo já existente

**Resultado:** passed

**Observações:**
- `TestCT006RetomadaEmEntregaPosterior` (3 testes): comando usa `--resume-id`
  quando a sessão é conhecida e existe no kiro-cli; retomada não soma
  invocações da entrega anterior; sessão inexistente não usa `--resume-id`.
  Comportamento pré-existente preservado.

## CT-007 — Ausência de retry inline: nenhuma chamada a sleep/backoff seguida de nova invocação

**Resultado:** passed

**Observações:**
- `TestCT007SemRetryInline` (6 testes, parametrizados): zero chamadas a
  `time.sleep` e exatamente 1 chamada ao subprocesso nos três padrões de abort
  reais; `_DeliveryBudget` levanta `SingleInvocationViolation` explicitamente
  numa segunda tentativa simulada. Este é o teste mais diretamente ligado ao
  risco central da ADR (retry ingênuo duplicando efeito colateral) e está
  travado por asserção dedicada, não apenas por ausência incidental de código.

## CT-008 — Caminho de sucesso permanece inalterado

**Resultado:** passed

**Observações:**
- `TestCT008SucessoInalterado` (4 testes): classificação `SUCCEEDED`, formato
  do `log.info` de conclusão inalterado, e narrativa do agente mencionando o
  abort (sem erro estruturado real) não é classificada como `UNKNOWN_OUTCOME`
  — confirma que a correção de #206 (canais estruturados, não narrativa) segue
  intacta.

## CT-009 — Mecanismos de proteção de estado interno não são afetados

**Resultado:** passed

**Observações:**
- `TestCT009EstadoInternoProtegido` (3 testes) confirma que `.pipe/sessions.json`
  é o único arquivo escrito em `.pipe/` pelo novo fluxo, nenhum `PROTECTED_PATHS`
  aparece no comando do subprocesso nem no bloco `## Resultado`.
- Suítes de proteção de estado interno executadas sem alteração:
  `test_build_prompt_protected_paths.py`, `test_dead_letter.py`,
  `test_instance_lock.py`, `test_orphan_detection.py` — 133 passed, 3 skipped,
  1 xpassed. Nenhuma regressão.

## CT-010 — Não regressão da suíte existente

**Resultado:** passed

**Observações:**
- `tests/test_kiro_cli_unknown_outcome.py`: 40/40 passed.
- `tests/test_agent_failure_detection.py` + `tests/test_error_classification.py`:
  56/56 passed (linha de base do adapter, sem regressão).
- Suíte completa (`python -m pytest tests/ -q`): **21 failed, 1183 passed, 28
  skipped, 1 xpassed** — idêntico ao reportado pelo Desenvolvimento. As 21
  falhas são pré-existentes e fora de escopo desta issue:
  - `tests/test_agent_log_descritivo.py` (18 falhas) — formato de log
    descritivo de outra task, já falhando antes de #208.
  - `tests/test_dockerfile.py` (3 falhas) — verificação de SHA-256 pinado do
    kiro-cli no Dockerfile, sem relação com o adapter em Python.
- Confirmado por leitura de `src/adapters/kiro_cli_agent.py` que a
  implementação é fiel ao contrato da ADR/body: `Outcome` fail-closed por
  default, `_DeliveryBudget`/`SingleInvocationViolation` para invocação única,
  `_capture_session` chamado também no ramo de timeout, `_extract_request_id`
  e bloco `## Resultado` no log de execução.

## Resumo

- Total: 10 (CT-001 a CT-010)
- Passou: 10
- Falhou: 0
- Bloqueado: 0

Sem dúvidas ou ambiguidade nos casos de teste. Todos os critérios de aceite de
#208 foram verificados e confirmados. Nenhuma regressão nas suítes existentes
(as 21 falhas pré-existentes são de outras tasks, já documentadas nas etapas
anteriores). Avança para `advance`.
