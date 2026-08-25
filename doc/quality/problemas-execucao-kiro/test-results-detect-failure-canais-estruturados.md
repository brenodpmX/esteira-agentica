# Resultados de Teste — `_detect_failure` não deve avaliar a narrativa do agente, só os canais estruturados do kiro-cli

Status: approved
Owner: quality
Last updated: 2026-08-25

## Inputs

- `doc/quality/problemas-execucao-kiro/test-cases-detect-failure-canais-estruturados.md`
  (CT-001 a CT-008)
- Task #206 — `_detect_failure` não deve avaliar a narrativa do agente, só os
  canais estruturados do kiro-cli (board `task`, etapa Execução de Testes)
- Implementação sob teste: `KiroCliAgent._detect_failure` e `KiroCliAgent._run`
  (`src/adapters/kiro_cli_agent.py`), já concluída na etapa de Desenvolvimento
  (commits `dd8e314`, `90038ed`)
- Suíte automatizada dedicada: `tests/test_detect_failure_canais_estruturados.py`
- Suítes de não regressão: `tests/test_agent_failure_detection.py`,
  `tests/test_error_classification.py`

## Execução

```
python -m pytest tests/test_detect_failure_canais_estruturados.py \
  tests/test_agent_failure_detection.py tests/test_error_classification.py -v
```

Todos os 8 casos de teste do documento de casos (CT-001 a CT-008) estão
implementados como testes automatizados em
`tests/test_detect_failure_canais_estruturados.py` e foram executados nesta
etapa. Mapeamento caso → teste(s):

## CT-001 — Marcador de falha citado só na narrativa do agente não é falha

**Resultado:** passed

**Observações:**
- `TestNarrativaCitandoMarcadorNaoEFalha::test_citacao_kiro_trouble_na_narrativa_com_exit_0`
  reproduz literalmente o caso real de `logs/203/2026-08-24_21-39-38.md`
  (`returncode=0`, citação da frase de erro na narrativa, linha final
  `▸ Credits: ...`) e confirma `_detect_failure` retorna `None`.
- `test_citacao_kiro_trouble_longa_narrativa` cobre a mesma citação em uma
  narrativa com mais de `_TAIL_LINES` (30) linhas, garantindo que o corte para
  tail não reintroduz o falso positivo por acidente de posição.

## CT-002 — Múltiplas citações da narrativa a marcadores diferentes, ainda sucesso

**Resultado:** passed

**Observações:**
- `TestMultiplosMarcadoresNaNarrativa` parametriza os 4 marcadores de
  `_FAILURE_MARKERS` (`[TIMEOUT]`, `[ERRO]`, `Kiro is having trouble
  responding`, `[exit-code:`) citados na narrativa com `returncode=0` — todos
  retornam `None`. `test_todos_marcadores_juntos_na_narrativa` cobre a
  combinação dos quatro no mesmo output.

## CT-003 — `returncode != 0` real continua detectado como falha (não regressão)

**Resultado:** passed

**Observações:**
- Cobertura direta em `TestReturnCodeNaoZeroEFalha` (`exit_code_1_com_marcador`,
  `exit_code_2_sem_hints_usa_ultimas_linhas`) e mantida em
  `TestDetectFailureFalha::test_cada_marcador_dispara_falha` em
  `test_agent_failure_detection.py`. Nenhuma expectativa de falha real foi
  alterada.

## CT-004 — Bloco real de erro do kiro-cli no encerramento continua detectado

**Resultado:** passed

**Observações:**
- `TestBlocoRealDeErroDetectado::test_dispatch_failure_com_exit_code_1` e
  `test_kiro_trouble_com_exit_0_no_tail`/`test_modelo_indisponivel_com_exit_0`
  reproduzem o padrão real do incidente #203 (dispatch failure / Tool approval
  required) como encerramento estruturado (seguido de `[exit-code:` ou como
  único conteúdo do tail sem indicador de sucesso) e confirmam extração de
  causa preservada.

## CT-005 — Menção a "error"/"Error:" na narrativa sem canal estruturado não é falha

**Resultado:** passed

**Observações:**
- `TestPalavraErrorSemMarcadorNaoEFalha::test_narrativa_sobre_error_handling`
  passa, assim como o teste equivalente pré-existente
  `test_palavra_error_sem_marcador_nao_e_falha` em
  `test_agent_failure_detection.py`. Nenhuma sensibilidade nova à palavra
  "error" isolada foi introduzida.

## CT-006 — Timeout e kiro-cli não encontrado no PATH continuam detectados

**Resultado:** passed

**Observações:**
- `TestSaidasSinteticasDoAdapter::test_timeout` e
  `test_kiro_cli_nao_encontrado` confirmam que as saídas sintéticas do adapter
  (`returncode=None`) continuam sinalizando falha, tratadas explicitamente
  como canal estruturado (Caso 1 de `_detect_failure`).

## CT-007 — Assinatura/contrato: decisão depende do canal estruturado, não só do texto

**Resultado:** passed

**Observações:**
- `TestContratoDecisaoPorCanalEstruturado::test_mesma_narrativa_resultados_diferentes_por_returncode`
  prova que a mesma narrativa produz `None` com `returncode=0` (sem bloco de
  erro) e mensagem de erro com `returncode=1`/bloco real presente.
  `test_assinatura_aceita_returncode` confirma que `_detect_failure` aceita o
  parâmetro `returncode`. Contrato implementado conforme AC2/AC3 do body.

## CT-008 — Não regressão da integração em `execute()`

**Resultado:** passed

**Observações:**
- `TestIntegracaoExecute::test_narrativa_com_marcador_nao_falha_via_execute` e
  `test_falha_real_via_execute` cobrem `execute()` fim a fim via
  monkeypatch de `_run`. A suíte completa de `test_agent_failure_detection.py`
  (18 testes, incluindo `TestExecuteUsaDeteccao`) e `test_error_classification.py`
  (38 testes) passam integralmente, sem alteração de expectativa nos casos de
  falha real (D1/D2) nem no formato de log de conclusão.

## Verificação adicional (fora dos CT, escopo de regressão geral)

Executada a suíte completa do projeto (`python -m pytest -q`) para garantir
ausência de efeito colateral fora do escopo direto da issue:

- 1143 passed, 28 skipped, 1 xpassed, **21 failed**.
- As 21 falhas (`tests/test_agent_log_descritivo.py` — 18,
  `tests/test_dockerfile.py` — 3) foram confirmadas como **pré-existentes**:
  reproduzidas de forma idêntica em `main` (`0f8dce4`), num worktree isolado,
  sem qualquer alteração desta branch. Não relacionadas a `_detect_failure`
  nem a canais estruturados do kiro-cli — portanto fora do escopo desta task,
  conforme já registrado na etapa de Desenvolvimento.
- Nenhum código de produção ou de teste foi alterado nesta etapa; verificação
  somente leitura/execução.

## Resumo

- Total: 8 (CT-001 a CT-008, todos com teste automatizado correspondente)
- Passou: 8
- Falhou: 0
- Bloqueado: 0

Suíte automatizada em escopo (`test_detect_failure_canais_estruturados.py` +
`test_agent_failure_detection.py` + `test_error_classification.py`): **75
passed, 0 failed**. Nenhuma dúvida ou ambiguidade encontrada nos casos de
teste — todos estavam claros, autocontidos e diretamente executáveis contra a
implementação entregue.
