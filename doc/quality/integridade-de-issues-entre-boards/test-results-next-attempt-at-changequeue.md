# Resultados de Teste — Adicionar `next_attempt_at` e rotação sem bloqueio ao `ChangeQueue`

Status: approved
Owner: quality
Last updated: 2026-08-28

## Inputs

- `doc/product/integridade-de-issues-entre-boards/casos-de-teste/251-casos-de-teste-next-attempt-at-changequeue.md`
- Issue #251 — Adicionar `next_attempt_at` e rotação sem bloqueio ao
  `ChangeQueue` (board Task, story pai #244)

## CT01 — `ChangeItem.next_attempt_at`: campo novo, independente de `attempts`

**Resultado:** passed

**Observações:**
- Os 5 testes de `TestChangeItemNextAttemptAt` passaram:
  `test_default_next_attempt_at_is_none`, `test_next_attempt_at_settable`,
  `test_same_target_ignores_next_attempt_at`,
  `test_setting_next_attempt_at_does_not_increment_attempts`,
  `test_legacy_persisted_item_without_next_attempt_at_defaults_none`.
- Leitura de `src/core/board.py` confirma o campo
  `next_attempt_at: str = None` na dataclass `ChangeItem`, com docstring
  explicando a independência em relação a `attempts` (falha vs. pendência
  aguardando prova). `same_target()` não referencia o campo novo — dedupe
  inalterado. Item legado sem a chave no JSON carrega com `None`
  (`ChangeQueue._read()` já ignorava campos desconhecidos/ausentes antes
  desta task).

## CT02 — `getNext()`: rotação sem bloqueio (pula pendente, não remove)

**Resultado:** passed

**Observações:**
- Os 8 testes de `TestGetNextRotacaoSemBloqueio` passaram: pula o primeiro
  item pendente e retorna o segundo elegível sem remover nenhum (`size()`
  permanece 3); chamadas repetidas sem `remove`/`defer` retornam o mesmo
  item (mesmo `uuid`); `getNext(now=...)` após o vencimento passa a
  retornar o item antes pendente; `now` explícito antes do vencimento ainda
  pula; fila toda pendente no futuro retorna `None`; fila vazia retorna
  `None`; chamada sem argumento (uso existente em `src/core/sync.py:818`)
  continua funcionando normalmente.
- Leitura de `src/core/change_queue.py` confirma a implementação: varredura
  FIFO sobre `self._read()`, retorno do primeiro item com
  `next_attempt_at is None or next_attempt_at <= now`, comparação
  lexicográfica sobre o formato fixo `%Y-%m-%dT%H:%M:%SZ`. Assinatura
  retrocompatível (`now: str | None = None`, default usa `ChangeItem.now()`).

## CT03 — `defer()`: atualiza apenas `next_attempt_at`, idempotente por `uuid`

**Resultado:** passed

**Observações:**
- Os 7 testes de `TestDefer` passaram: `defer` torna o item pendente
  (deixa de ser retornado por `getNext(now=...)` antes do vencimento);
  `uuid` original inalterado (`remove(uuid)` ainda funciona após o
  `defer`); ordem FIFO relativa dos demais itens elegíveis preservada ao
  deferir um item do meio da fila; `attempts` permanece `0`; chamadas
  repetidas de `defer` no mesmo item atualizam apenas o último instante
  sem duplicar entrada (`size()` inalterado); `uuid` inexistente não altera
  a fila nem levanta exceção (mesmo padrão de tolerância de `remove()`);
  `remove()` funciona normalmente pelo mesmo `uuid` após um `defer`.
- Leitura do código confirma `defer(item, next_attempt_at)` localizando por
  `uuid`, atualizando somente `next_attempt_at` e reescrevendo a fila —
  sem tocar posição, `uuid` ou `attempts`.

## CT04 — Não regressão da suíte existente

**Resultado:** passed

**Observações:**
- `python -m pytest tests/ -k "change_queue or queue" -v` → 20 passed
  (todos os testes de `tests/test_change_queue.py`; nenhum outro arquivo
  casou o filtro).
- `python -m pytest tests/` (suíte completa) → **1220 passed, 28 skipped, 1
  xpassed, 21 failed**. As 21 falhas pertencem exclusivamente a
  `tests/test_agent_log_descritivo.py` e `tests/test_dockerfile.py` — sem
  qualquer relação com `ChangeItem`, `ChangeQueue`, `next_attempt_at` ou
  `defer`. Confirmado que a mesma contagem de 21 falhas ocorre
  independentemente das mudanças desta task (mesmos arquivos, sem alteração
  de código de produção fora de `src/core/board.py` e
  `src/core/change_queue.py`).
- Único ponto de chamada de produção (`src/core/sync.py:818`,
  `queue.getNext()` sem argumento) inalterado e coberto pelo teste de
  regressão `test_getnext_sem_argumento_continua_funcionando_regressao`.

## Resumo

- Total: 4
- Passou: 4
- Falhou: 0
- Bloqueado: 0

## Conclusão

Nenhuma dúvida ou ambiguidade encontrada nos casos de teste: todos
objetivos, verificáveis por execução direta de `pytest` e leitura do
código-fonte alterado. Escopo respeitado — nenhuma alteração de código de
produção, teste ou caso de teste foi feita nesta etapa; apenas execução e
registro. Critério de aceite da issue #251 atendido: implementação segue a
arquitetura descrita (campo genérico em `ChangeItem` + `getNext(now=...)` +
`defer()` em `ChangeQueue`, mesmo padrão de leitura/escrita atômica já usado
por `remove()`/`requeue()`), código cobre os cenários descritos (rotação sem
bloqueio, idempotência de espiar, vencimento por `now`, fila toda pendente,
fila vazia, compatibilidade com item legado), testes unitários existem e
passam (20/20), e não há quebra de funcionalidades existentes.

Aprovado — avançar para **advance** (merge-request).

— Camila Rocha - Engenheira de Qualidade (QA)
