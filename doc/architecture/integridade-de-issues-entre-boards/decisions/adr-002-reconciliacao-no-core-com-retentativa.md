# ADR-002 — Reconciliação no core, orientada a evento e retentável

Status: proposed
Owner: architecture
Last updated: 2026-08-27

## Inputs
- `doc/architecture/integridade-de-issues-entre-boards/overview.md`
- `doc/architecture/integridade-de-issues-entre-boards/constraints.md`
- `doc/changes/88-sub-issues-propagadas-entre-boards.md`
- `doc/incidente/sub-issues-propagadas/ticket.md`
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md`
- `src/core/board.py`, `src/core/sync.py`, `src/core/change_queue.py`
- `src/adapters/github_board.py`
- `tests/test_sub_issue_propagation_fix.py`

## Contexto

A proteção vigente está parcialmente dentro do adapter GitHub. O método
`_remove_propagated_items_without_status` decide o que é legítimo, recebe um
`exclude_board_id` com significado assimétrico entre `set_parent` e
`set_children`, ignora itens com `Status` e captura falhas de consulta/remoção
apenas como warning. Além disso, a propagação pode aparecer depois da consulta
imediata.

A fila do core já oferece persistência, deduplicação, rotação e isolamento de
falha. Criar outro mecanismo de execução seria redundante.

## Decisão

Mover a política e a orquestração para um serviço
`ParticipationIntegrity` no core.

O `BoardPort` expõe um contrato normalizado:

```text
list_participations(issue_id) -> [Participation]
remove_from_board(board_id, issue_id) -> None
```

`Participation` contém somente identificadores, board configurado quando
resolvido, `Status` e arquivamento. O adapter consulta `projectItems` por
GraphQL e não classifica intenção.

O serviço roda em dois gatilhos complementares:

1. após adicionar uma relação pai/filho, para contenção imediata; e
2. em todo `create-down`, com ou sem `Status`, para cobrir propagação tardia.

Uma participação `propagated` é removida por `deleteProjectV2Item`; a relação
pai/filho permanece intacta. O evento somente é confirmado depois da remoção.
Falhas são propagadas como erros tipados.

`unresolved` e falhas transitórias permanecem na `ChangeQueue`, com
`next_attempt_at = now + config.sleep`. Itens ainda não vencidos são
rotacionados, não bloqueiam a fila e não contam para dead-letter por esgotamento
de tentativas. Erros definitivos de contrato continuam isolados conforme a
política atual. Enquanto pendente, nenhum arquivo executável é criado.

A função privada do adapter que remove por `Status` deve ser eliminada ou
reduzida a primitiva de transporte; não haverá duas políticas concorrentes.

## Justificativa

A decisão mantém uma única fonte de regra no core e reutiliza componentes já
homologados. Dois gatilhos são necessários porque uma leitura síncrona não
oferece garantia contra consistência eventual do GitHub. A fila persistente
fornece retry e isolamento sem broker.

Alternativas rejeitadas:

- **Apenas pós-hook síncrono:** não observa propagação tardia e já falhou no
  caminho assimétrico.
- **Apenas full scan diário:** janela grande demais para impedir despacho.
- **Webhook obrigatório:** aumenta operação, exposição de endpoint e estado de
  entrega; polling por board já existe e atende ao volume.
- **Saga/event sourcing:** complexidade desproporcional; há uma única mutação
  compensatória idempotente.
- **Engolir falha e confiar no próximo sync:** perde causalidade e evidência.
- **Usar REST para Projects V2:** API inexistente/inadequada, erro já ocorrido
  na tentativa original da issue #88.

## Consequências

- Positivas: elimina assimetria de call sites; cobre item com coluna e chegada
  tardia; falhas ficam auditáveis; nenhuma infraestrutura nova.
- Negativas: `BoardPort` ganha um contrato e a fila um instante de próxima
  tentativa; adapters futuros precisam declarar suporte ou falhar fechados.
- Riscos: uma indisponibilidade longa mantém pendências na fila. Mitigação:
  rotação, atraso, deduplicação e gate de despacho.
- Performance: uma consulta de participações por candidata e, quando
  necessário, uma remoção. Não existe varredura adicional de todas as issues.
- Compatibilidade: itens antigos sem `next_attempt_at` são elegíveis
  imediatamente; `remove_from_board` existente é preservado.
