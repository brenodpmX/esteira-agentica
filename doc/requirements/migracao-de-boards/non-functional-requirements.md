# Requisitos Não-Funcionais — Migração Segura de Colunas de Boards

Status: aprovado
Owner: requirements
Last updated: 2026-08-22

## Inputs
- `/app/.pipe/boards/epic/requisitos/91-migracao_de_boards-body.md`
- `/app/.pipe/boards/epic/requisitos/91-migracao_de_boards-history.md`
- `doc/requirements/migracao-de-boards/functional-requirements.md`
- `README.md` (seção "Rate Limit (GitHub)")

Este documento explicita atributos de qualidade mensuráveis, derivados dos
critérios de sucesso já definidos no body da issue #91, para uso como
critério de validação por arquitetura e QA. Não redefine escopo funcional —
apenas detalha "quão bem" cada garantia deve se comportar.

## Confiabilidade / Integridade

- Zero issues devem ficar sem coluna (sem opção de `Status` correspondente)
  em consequência de uma retirada de coluna configurada — métrica direta do
  body da issue #91 ("zero issues sem coluna causadas por retirada
  configurada").
- 100% das issues que estavam na coluna retirada devem ser encontradas no
  destino explícito antes da opção de `Status` ser removida do board remoto
  — nenhuma issue pode ficar "no meio do caminho" quando a retirada é
  efetivada.
- Zero perda ou duplicação de issues em qualquer sequência de tentativas
  (incluindo repetição após falha) — métrica direta do body.
- Zero retirada deve ser concluída com a coluna de origem ainda ocupada —
  a verificação de "vazia" deve ser feita imediatamente antes da retirada
  efetiva, não apenas no início da tentativa (ver RN-004 e F-006 do
  documento funcional).
- Zero alteração de classificação de issue deve ocorrer quando o destino for
  ausente ou inválido — a validação do destino deve ocorrer antes de
  qualquer chamada que altere o `Status` de uma issue.

## Continuidade / Recuperação

- Uma migração interrompida por falha (indisponibilidade do provedor, rate
  limit, encerramento do processo) deve poder ser retomada em uma execução
  seguinte sem exigir intervenção manual para "destravar" o estado — a
  esteira pode operar sem supervisão em container (histórico da issue #91,
  resposta 10).
- Uma nova tentativa sobre uma migração parcialmente concluída deve
  reconhecer os itens já corretamente movidos e migrar apenas os itens
  restantes — o custo de uma repetição não deve crescer proporcionalmente ao
  número de tentativas anteriores (não deve haver reprocessamento
  desnecessário de itens já migrados).
- Não há SLA de tempo de conclusão definido para a migração (fora de escopo,
  ver body da issue #91) — a migração pode levar o tempo necessário mediante
  retentativas, respeitando o throttle de rate limit já existente na esteira
  (ver README, seção "Rate Limit (GitHub)").

## Observabilidade

- 100% das tentativas de migração (concluídas, bloqueadas ou interrompidas)
  devem registrar contagem inicial, itens movidos, itens restantes e
  resultado — métrica direta do body da issue #91 ("100% dos eventos com
  contagens e resultado verificáveis").
- A evidência de cada tentativa deve ser acessível ao Operador sem exigir
  leitura de arquivos internos protegidos da esteira (`snapshot.json`,
  `changeQueue.json`), consistente com a proteção de estado interno já
  descrita no `README.md`.
- Um resultado bloqueado (destino ausente ou inválido) deve identificar o
  motivo do bloqueio de forma acionável para o Operador (qual coluna, qual
  board, por que o destino é inválido), sem exigir correlação manual entre
  múltiplos registros para reconstruir a causa.

## Consistência / Idempotência

- A migração deve ser segura para repetição (idempotente do ponto de vista
  de efeito observável): executar a mesma operação de retirada mais de uma
  vez, no mesmo estado ou em estado parcialmente avançado, deve produzir o
  mesmo resultado final, sem efeitos colaterais cumulativos (ex.: uma issue
  já migrada não deve ser recontada como "movida" adicionalmente a cada
  repetição, distorcendo a evidência da tentativa).
- A ordem em que as issues da coluna retirada são migradas para o destino
  não deve afetar o resultado final (todas devem chegar ao destino,
  independentemente da ordem de processamento).

## Compatibilidade com uso de API externa

- A migração deve respeitar o throttle e a lógica de penalty de rate limit já
  existentes na esteira (ver README, seção "Rate Limit (GitHub)") — não deve
  introduzir um caminho de chamadas ao board que ignore o throttle vigente.
- O número de chamadas ao board por issue migrada deve ser proporcional ao
  necessário para mover uma issue de coluna (mesma ordem de grandeza das
  operações de mudança de coluna já existentes na esteira) — não é esperado
  overhead adicional por issue além do necessário para a mudança de
  `Status` e, quando aplicável, a validação de pertinência ao board.

## Critérios de teste de regressão

Os cenários abaixo devem ser cobertos por arquitetura/QA ao validar a
solução, com base nos fluxos do documento funcional:

- Retirada de coluna vazia (F-001): conclui sem exigir destino.
- Retirada de coluna ocupada com destino válido (F-002): todas as issues
  migradas, origem confirmada vazia, retirada concluída, evidência completa.
- Retirada de coluna ocupada sem destino (F-003): bloqueada, nenhuma
  alteração de classificação.
- Retirada de coluna ocupada com destino inválido (F-004): bloqueada,
  nenhuma alteração de classificação, motivo identificado.
- Falha/interrupção durante a migração (F-005): estado parcial preservado,
  nova tentativa completa sem perda/duplicação.
- Issue chega à origem durante a migração, antes da retirada efetiva
  (F-006): a nova issue também é migrada; retirada só ocorre com a coluna
  de fato vazia.
- Repetição da mesma operação de retirada em qualquer dos cenários acima:
  resultado final idêntico, sem perda nem duplicação (RN-006).
