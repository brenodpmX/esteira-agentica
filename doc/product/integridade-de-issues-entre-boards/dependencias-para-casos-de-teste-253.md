# Dependências para liberar os casos de teste de #253

Data da decisão: 28/08/2026  
Responsável: Helena Costa — Product Manager

## Decisão

A issue #253 não deve criar placeholder nem redefinir contratos ausentes. Seus casos de teste serão retomados somente quando a cadeia abaixo estiver implementada e integrada à branch base correspondente:

1. **#264 — autorização multi-board por `board-intent-<board_id>`**: entrega `authorized_boards`.
2. **#265 — política pura `classify_participation`**: depende de #264 e entrega `origin`/`authorized`/`propagated`/`unresolved` para concluir a story #242.
3. **#242 — classificação de intenção**: consolida as duas tasks anteriores e disponibiliza o contrato consumido pela reconciliação.
4. **#252 — classificação e reconciliação em `_apply_create_down`**: depende de #242 e entrega `ParticipationUnresolvedError` e o ponto de chamada real.
5. **Task “Adiar evento `unresolved` com `next_attempt_at` sem consumir tentativa nem dead-letter”**: depende de #252; foi criada no backlog sem prefixo numérico e receberá ID no sync. Ela classifica o sinal como `unresolved`, aplica `next_attempt_at = now + sleep` via `ChangeQueue.defer`, preserva `attempts` e impede dead-letter.
6. **#253 — `participation_removed_externally`**: permanece bloqueada até a task de adiamento receber ID, ser vinculada e todas as dependências anteriores estarem integradas. Só então haverá uma retentativa real, com `next_attempt_at` preenchido, sobre a qual os casos de teste possam ser escritos sem inventar API.

## Relações registradas no board

- #265: `/blocked_by #264` e `/blocks #242`.
- #252: `/blocked_by #242`, além de `/parent #244` e `/blocks #244`.
- Task de adiamento sem ID: `/parent #244`, `/blocked_by #252` e `/blocks #244, #253`.
- #253 já permanece bloqueada pelo débito #271 até esta definição ser integrada; após o sync da nova task, o vínculo numérico gerado passa a representar o bloqueio técnico remanescente.

## Critério de desbloqueio

#253 pode voltar a Casos de Teste apenas quando existirem na sua branch base:

- a função real de classificação de #242;
- `ParticipationUnresolvedError` e o ponto de chamada de #252;
- o tratamento que preenche `next_attempt_at` sem incrementar `attempts` nem gerar dead-letter.

A existência isolada da infraestrutura de #251 (`ChangeItem.next_attempt_at`, `ChangeQueue.defer` e `getNext`) não satisfaz esse critério, pois ela ainda não liga o resultado `unresolved` ao fluxo de `apply_changes`.

## Base Git desta definição

A branch declarada de #253 ainda não existia no remoto. Para preservar a genealogia documentada, ela foi materializada localmente a partir de `origin/story244-244-reconciliacao_na_descoberta_remota_com_retentativa_sem_bloqueio`; a presente definição foi então registrada em `debito253-humano-story-242-task-252-nao-implementadas`.
