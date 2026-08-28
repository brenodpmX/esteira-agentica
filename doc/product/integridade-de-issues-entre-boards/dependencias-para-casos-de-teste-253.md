# Dependências para liberar os casos de teste de #253

Data da decisão: 28/08/2026  
Responsável: Helena Costa — Product Manager

## Decisão

A issue #253 não deve criar placeholder nem redefinir contratos ausentes. Seus casos de teste serão retomados somente quando a cadeia abaixo estiver implementada e integrada à branch base correspondente:

1. **#264 — autorização multi-board por `board-intent-<board_id>`**: entrega `authorized_boards`.
2. **#265 — política pura `classify_participation`**: depende de #264 e entrega `origin`/`authorized`/`propagated`/`unresolved` para concluir a story #242.
3. **#242 — classificação de intenção**: consolida as duas tasks anteriores e disponibiliza o contrato consumido pela reconciliação.
4. **#252 — classificação e reconciliação em `_apply_create_down`**: depende de #242 e entrega `ParticipationUnresolvedError` e o ponto de chamada real.
5. **#278 — adiar evento `unresolved` com `next_attempt_at` sem consumir tentativa nem dead-letter**: já existe no backlog, está vinculada a #244 e depende de #252. Ela classifica o sinal como `unresolved`, aplica `next_attempt_at = now + sleep` via `ChangeQueue.defer`, preserva `attempts` e impede dead-letter.
6. **#253 — `participation_removed_externally`**: permanece bloqueada até que as cinco entregas da cadeia #264 → #265 → #242 → #252 → #278 estejam implementadas e mescladas em `epic`. Só então haverá uma retentativa real, com `next_attempt_at` preenchido, sobre a qual os casos de teste possam ser escritos sem inventar API.

## Relações registradas no board

- #264: `/blocks #242, #265`.
- #265: `/blocked_by #264` e `/blocks #242`.
- #242: `/blocked_by #264, #265` e `/blocks #252` (entre outras entregas consumidoras da story).
- #252: `/parent #244`, `/blocked_by #242` e `/blocks #244, #278`.
- #278: `/parent #244`, `/blocked_by #252` e `/blocks #244, #253`.
- #253 já possui o bloqueio técnico numérico de #278. O débito #271 a bloqueia apenas até esta definição corrigida ser integrada.

## Critério de desbloqueio

#253 pode voltar a Casos de Teste somente quando as cinco entregas #264, #265, #242, #252 e #278 estiverem concluídas e mescladas em `epic`, disponibilizando em conjunto:

- `authorized_boards`, entregue por #264;
- a função pura de classificação `origin`/`authorized`/`propagated`/`unresolved`, entregue por #265 e consolidada por #242;
- `ParticipationUnresolvedError` e o ponto de chamada real em `_apply_create_down`, entregues por #252;
- o tratamento de #278 que preenche `next_attempt_at` sem incrementar `attempts` nem gerar dead-letter.

A criação, a atribuição do ID e o vínculo de #278 já estão concluídos e não são condições pendentes. A existência isolada da infraestrutura de #251 (`ChangeItem.next_attempt_at`, `ChangeQueue.defer` e `getNext`) tampouco satisfaz o critério, pois ela ainda não liga o resultado `unresolved` ao fluxo de `apply_changes`.

## Base Git desta definição

A branch declarada de #253 ainda não existia no remoto. Para preservar a genealogia documentada, ela foi materializada localmente a partir de `origin/story244-244-reconciliacao_na_descoberta_remota_com_retentativa_sem_bloqueio`; a presente definição foi então registrada em `debito253-humano-story-242-task-252-nao-implementadas`.
