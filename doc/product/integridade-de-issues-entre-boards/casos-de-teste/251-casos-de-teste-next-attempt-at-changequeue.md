# Casos de Teste — Adicionar `next_attempt_at` e rotação sem bloqueio ao `ChangeQueue`

Issue: #251 — Adicionar `next_attempt_at` e rotação sem bloqueio ao `ChangeQueue`
Story pai: #244 — Reconciliação na descoberta remota com retentativa sem bloqueio
Etapa: Casos de Teste

## Contexto da verificação

A issue pede exclusivamente o mecanismo genérico de retentativa por instante
no `ChangeItem`/`ChangeQueue`: campo `next_attempt_at: str | None = None` em
`ChangeItem` (`src/core/board.py`), e dois métodos novos em `ChangeQueue`
(`src/core/change_queue.py`): `getNext(now=None)` (passa a pular itens com
`next_attempt_at` no futuro, sem removê-los) e `defer(item, next_attempt_at)`
(atualiza apenas esse campo por `uuid`, sem alterar posição FIFO nem
`attempts`).

**Estado no momento desta verificação:** confirmado por leitura direta do
código em `epic` que `ChangeItem` não tem `next_attempt_at` e que
`ChangeQueue.getNext()` não aceita argumento `now` nem existe `defer()`.
Esta é a etapa de Casos de Teste, que antecede a implementação; os testes
abaixo foram escritos test-first e devem falhar (`AttributeError`) até a
implementação ser feita, e passar depois — sem alterações nesta task além
dos próprios testes.

Explicitamente fora de escopo (não testado aqui, ver seção "Fora de escopo"
da issue): qualquer chamada a `defer()` a partir de `_apply_create_down` ou
de lógica de classificação/participação; alteração de `apply_changes()` para
usar `getNext(now=...)` com política de classificação; persistência ou
interpretação de `participation_intent`.

Testes automatizados em `tests/test_change_queue.py` (pytest). Este
documento é a versão legível/rastreável dos mesmos casos.

## CT01 — `ChangeItem.next_attempt_at`: campo novo, independente de `attempts`

**Objetivo:** confirmar que o campo existe com default `None`, é
independente de `attempts` (não o incrementa) e não afeta `same_target`
(deduplicação da fila continua ignorando este campo, mesmo padrão já usado
por `attempts`).

**Procedimento:** instanciar `ChangeItem.of(...)` e inspecionar
`next_attempt_at` (default); atribuir um valor e reler; criar dois itens
equivalentes exceto por `next_attempt_at` e chamar `same_target`; atribuir
`next_attempt_at` e verificar que `attempts` permanece `0`; simular um item
legado persistido sem a chave `next_attempt_at` no JSON e confirmar que
`ChangeQueue._read()` o carrega com `next_attempt_at = None` (mesmo padrão
de compatibilidade já usado para `attempts` — campos desconhecidos/ausentes
não quebram a leitura).

**Resultado esperado:** `next_attempt_at` é `None` por default; aceita
atribuição; não influencia `same_target` (retorna `True` mesmo com valores
diferentes); não incrementa `attempts`; item legado sem o campo no JSON
carrega com `None` (elegível imediatamente).

**Testes:** `test_default_next_attempt_at_is_none`,
`test_next_attempt_at_settable`, `test_same_target_ignores_next_attempt_at`,
`test_setting_next_attempt_at_does_not_increment_attempts`,
`test_legacy_persisted_item_without_next_attempt_at_defaults_none`.

---

## CT02 — `getNext()`: rotação sem bloqueio (pula pendente, não remove)

**Objetivo:** garantir que um item com `next_attempt_at` no futuro não
bloqueia os itens elegíveis seguintes (sem head-of-line blocking), que ele
não é removido da fila ao ser pulado, que chamadas repetidas continuam
retornando o mesmo item elegível (espiar é idempotente), que passar `now`
explicitamente respeita a comparação lexicográfica ISO 8601, que uma fila
totalmente pendente no futuro retorna `None` sem erro, e que a assinatura
sem argumento (compatibilidade) continua funcionando.

**Procedimento:** montar uma fila com 3 itens — o primeiro com
`next_attempt_at` no futuro, o segundo e o terceiro sem o campo (elegíveis)
— e chamar `getNext()`; conferir o tamanho da fila após a chamada; chamar
`getNext()` de novo sem remover nem `defer`; chamar `getNext(now=...)` com
um instante posterior ao `next_attempt_at` do primeiro item (que já venceu);
chamar `getNext(now=...)` com um instante anterior ao vencimento; montar uma
fila onde todos os itens têm `next_attempt_at` no futuro e chamar
`getNext()`; chamar `getNext()` numa fila vazia; e, por fim, o cenário de
regressão — um item **sem** `next_attempt_at` (caso legado/comum) numa
chamada `getNext()` sem argumento, replicando o uso existente em
`src/core/sync.py:818`.

**Resultado esperado:** retorna o segundo item (pula o primeiro sem
removê-lo — `size()` permanece `3`); chamadas repetidas retornam o mesmo
item elegível (mesmo `uuid`); com `now` após o vencimento, o primeiro item
(antes pendente) passa a ser retornado; com `now` antes do vencimento,
continua pulando; fila toda pendente no futuro retorna `None`; fila vazia
retorna `None`; chamada sem argumento continua retornando itens elegíveis
normalmente (sem quebra de compatibilidade).

**Testes:** `test_getnext_pula_primeiro_pendente_retorna_segundo_elegivel`,
`test_getnext_nao_remove_item_pendente_pulado`,
`test_getnext_repetido_sem_remover_retorna_mesmo_item_elegivel`,
`test_getnext_com_now_apos_vencimento_retorna_item_antes_pendente`,
`test_getnext_now_explicito_antes_do_vencimento_ainda_pula`,
`test_getnext_fila_toda_pendente_no_futuro_retorna_none`,
`test_getnext_fila_vazia_retorna_none`,
`test_getnext_sem_argumento_continua_funcionando_regressao`.

---

## CT03 — `defer()`: atualiza apenas `next_attempt_at`, idempotente por `uuid`

**Objetivo:** confirmar que `defer(item, next_attempt_at)` atualiza somente
esse campo (por `uuid`), sem alterar a posição relativa do item na fila
(ordem FIFO original) nem o próprio `uuid`, sem incrementar `attempts`, que
é idempotente (chamadas repetidas apenas atualizam o instante, sem duplicar
entradas), e que a tolerância a `uuid` inexistente segue o mesmo padrão já
usado por `remove()` (não faz nada, não levanta erro).

**Procedimento:** adicionar um item à fila e chamar `defer(item,
next_attempt_at_futuro)`; verificar via `getNext(now=...)` que o item passa
a ser pendente; confirmar que `remove(uuid_original)` ainda funciona após o
`defer`; montar uma fila com 3 itens, deferir o do meio para o futuro e
confirmar que a ordem relativa dos dois itens elegíveis restantes (primeiro
e terceiro) não muda; inspecionar `attempts` antes e depois do `defer`;
chamar `defer` duas vezes com instantes diferentes no mesmo item e verificar
que apenas o último instante prevalece e que a fila não duplicou a entrada;
chamar `defer` com um item cujo `uuid` não existe na fila e confirmar que a
fila permanece inalterada; por fim, confirmar que `remove(uuid)` continua
funcionando pelo mesmo `uuid` após um `defer`.

**Resultado esperado:** `next_attempt_at` atualizado corretamente;
`uuid` inalterado (remoção pelo uuid original funciona); posição FIFO
relativa preservada; `attempts` permanece `0` (não incrementado por
`defer`); chamada repetida apenas atualiza o instante (fila com o mesmo
tamanho, sem duplicar); `uuid` inexistente não altera a fila nem levanta
exceção; `remove()` funciona normalmente pelo mesmo `uuid` depois do
`defer`.

**Testes:** `test_defer_atualiza_next_attempt_at`,
`test_defer_nao_altera_uuid`, `test_defer_nao_altera_posicao_fifo`,
`test_defer_nao_incrementa_attempts`,
`test_defer_idempotente_atualiza_apenas_instante`,
`test_defer_uuid_inexistente_nao_faz_nada`,
`test_defer_remove_ainda_funciona_pelo_mesmo_uuid`.

---

## CT04 — Não regressão da suíte existente

**Objetivo:** garantir que a implementação não quebra os testes já
existentes de `src/core/board.py`/`src/core/change_queue.py`/`src/core/sync.py`,
em especial `test_error_classification.py::TestChangeItemAttempts` (campo
`attempts`, já existente) e o único ponto de chamada de produção
(`src/core/sync.py:818`, `queue.getNext()` sem argumento).

**Procedimento:**
```bash
python -m pytest tests/ -k "change_queue or queue" -v
python -m pytest tests/ -v
```

**Resultado esperado:** todos os testes pré-existentes continuam passando
após a implementação (comparar contagem de `passed`/`failed` antes e depois
da issue ser implementada).

**Status no momento desta verificação (antes da implementação):** suíte
completa executada — `tests/test_change_queue.py` tem 16 falhas esperadas
(`AttributeError`: `next_attempt_at` inexistente em `ChangeItem`, `getNext`
não aceita `now`, `defer` inexistente em `ChangeQueue`) e 4 passam (as que
não dependem do mecanismo novo — regressão do campo `attempts` e do
comportamento atual de `getNext()`/fila vazia). As 21 falhas restantes na
suíte completa (`test_agent_log_descritivo.py`, `test_dockerfile.py`) são
pré-existentes e não relacionadas a esta issue — confirmado reexecutando a
suíte completa sem `tests/test_change_queue.py`: as mesmas 21 falhas
persistem, comprovando que não são causadas por este trabalho.

---

## Observação — documentação de referência ainda não mesclada em `epic`/`main`

A issue cita como documentação já aprovada:
- ADR-002 (`doc/architecture/integridade-de-issues-entre-boards/decisions/adr-002-reconciliacao-no-core-com-retentativa.md`)

Esse caminho não existe ainda em `epic`/`main` (busca no repositório sem
resultado). O arquivo existe na branch
`origin/epic230-230-integridade_de_issues_entre_boards` (ainda não
mesclada) — não é um gap de conteúdo, apenas merge pendente do épico #230.
Confirmado que o texto do ADR-002 nessa branch é consistente com o que a
issue #251 descreve: "`unresolved` e falhas transitórias permanecem na
`ChangeQueue`, com `next_attempt_at = now + config.sleep`. Itens ainda não
vencidos são rotacionados, não bloqueiam a fila e não contam para
dead-letter por esgotamento de tentativas." e "itens antigos sem
`next_attempt_at` são elegíveis imediatamente". Os casos de teste acima
foram escritos com base no texto da própria issue #251 (autocontida),
validados cruzando com o ADR-002 dessa branch pendente.

## Resultado da execução

Os 4 critérios de aceite mecânicos da issue (campo novo em `ChangeItem`;
`getNext(now=...)` com rotação sem bloqueio; `defer()`; e não-regressão) têm
testes automatizados dedicados em `tests/test_change_queue.py`, escritos
test-first e falhando por `AttributeError` no estado atual do código
(esperado nesta etapa). A não-regressão (CT04) foi verificada executando a
suíte completa: sem regressões atribuíveis a esta task; as falhas presentes
são pré-existentes e fora do escopo desta issue (log descritivo de agente e
Dockerfile/versões pinadas).
