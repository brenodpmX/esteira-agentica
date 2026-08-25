# ADR-002 — Gate em keep_task e sinalização idempotente pelo BoardPort

Status: proposed
Owner: architecture
Last updated: 2026-08-25

## Inputs
- `doc/requirements/circuit-break-de-agente/functional-requirements.md` (RF-003, RF-005, RF-007, RF-008)
- `doc/requirements/circuit-break-de-agente/business-rules.md` (RN-004, RN-005, RN-006, RN-009)
- `doc/requirements/circuit-break-de-agente/non-functional-requirements.md` (NFR-001, NFR-002, NFR-003, NFR-005)
- `doc/ux/circuit-break-de-agente/navigation-flow.md` e protótipos em draft
- `src/__main__.py` (`keep_task`, `_is_blocked`, `call_agent`)
- `src/core/board.py` (`BoardPort`, `add_label`, `list_comments`, `add_comment`)
- `src/core/change_queue.py` e fluxo de sync

## Contexto
O bloqueio deve ocorrer antes da execução excedente, sinalizar a issue e não interromper outras. Label e comentário são duas mutações remotas: qualquer uma pode falhar ou o processo pode cair entre elas. Simplesmente chamar o GitHub e zerar um cache em memória permite execução indevida no retry ou comentários duplicados.

Foram consideradas:

1. verificar dentro de `call_agent` — perto do adapter, mas retorna tarde demais para `keep_task` continuar a mesma varredura de issues;
2. criar middleware no adapter — mistura regra de domínio com plataforma e não consegue selecionar outra tarefa;
3. enfileirar novo tipo de mensagem/outbox completo — robusto, porém amplia a fila de sincronismo e adapters além do necessário;
4. gate em `keep_task` com pequeno estado `trip` e operações existentes de `BoardPort` — mantém a decisão no core e isola a issue.

## Decisão
Dividir a integração em dois pontos do mesmo `for` de `keep_task`:

1. antes de `_is_blocked`, chamar `reconcile_pending` para completar label/comentário de um `trip` anterior; enquanto houver pendência, negar a issue e continuar a varredura;
2. depois dos filtros estruturais atuais e do cooldown, imediatamente antes de retornar a tarefa, chamar `admit` para registrar a entrega ou abrir um novo bloqueio.

Essa ordem é obrigatória: se `need_human` já foi aplicado mas o comentário falhou, executar `_is_blocked` primeiro impediria para sempre a reconciliação do comentário.

`admit` retorna:

- `ALLOW`: ocorrência já persistida; `keep_task` retorna a tarefa;
- `DENY_TRIPPED`: bloqueio recém-persistido; o core inicia sinalização e continua o `for` para procurar outra issue;
- `DENY_PENDING_SIGNAL`: bloqueio anterior ainda incompleto; o core tenta reconciliar apenas as etapas faltantes e continua a varredura.

O evento `trip` é persistido antes de qualquer I/O remoto e contém `event_id`, board, coluna, issue, N, T, instante e flags das etapas. As ocorrências são limpas no mesmo write que cria o evento, concedendo a futura franquia completa já no instante do bloqueio.

Sinalização:

1. `Board.add_label(..., "need_human")`;
2. `Board.list_comments` procura `<!-- agent-circuit-break:<event_id> -->`;
3. se ausente, `Board.add_comment` publica o mínimo de RN-005 e o marcador oculto;
4. o sync reconcilia a issue para materializar `/need_human` no body local;
5. após reconciliação, o gate existente `_is_blocked` mantém a issue inelegível e o `trip` pode ser encerrado.

Cada flag concluída é persistida. Exceções externas são capturadas por issue: mantêm `trip`, geram log estruturado e não saem de `keep_task`. O próximo ciclo retoma a sinalização. Uma etapa remota nunca é condição para voltar a permitir a issue.

Depois que o operador remove `need_human`, `_is_blocked` deixa de barrar a issue e o contexto já possui zero ocorrências. Não existe timer half-open, botão adicional ou reset manual de arquivo.

## Justificativa
`keep_task` já é o ponto que decide elegibilidade, aplica cooldown e pode continuar procurando outro item. Colocar o gate ali preserva a semântica de “execução que seria entregue” e implementa RN-009 sem redesenhar o loop.

Persistir uma máquina de estados mínima antes do I/O dá semântica de at-least-once à sinalização e at-most-N à execução. Label é idempotente; comentário passa a ser idempotente pelo marcador. Isso oferece a robustez necessária sem introduzir serviço de outbox.

## Consequências
- Positivas: nenhuma execução N+1; falha limitada à issue; adapters permanecem genéricos; retry após crash não duplica comentário; retomada reutiliza `need_human`.
- Negativas: `keep_task` passa a orquestrar uma mutação externa somente na transição de bloqueio/pending, embora o caminho normal continue local.
- Negativas: será necessário um helper de reconciliação e testes de falha em cada fronteira da sinalização.
- Riscos: se label e comentário ficarem indisponíveis por longo período, a issue permanece bloqueada apenas pelo estado interno. O log precisa deixar essa pendência visível, enquanto outras issues seguem.
- Riscos: remover `need_human` antes de a primeira reconciliação pode competir com o retry. O contrato operacional considera a marca visível como pré-condição para a liberação; a implementação deve confirmar estado remoto/local antes de concluir `trip`.
- Riscos: comentário externo pode ter o marcador removido. Nesse caso um retry pode publicar nova evidência; isso é preferível a considerar sinalização completa sem prova.
