# ADR-001 — Intenção explícita e gate fail-closed antes do despacho

Status: proposed
Owner: architecture
Last updated: 2026-08-27

## Inputs
- `doc/architecture/integridade-de-issues-entre-boards/overview.md`
- `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`
- `doc/requirements/integridade-de-issues-entre-boards/non-functional-requirements.md`
- `doc/incidente/sub-issues-propagadas/ticket.md`
- `src/__main__.py` (`keep_task`)
- `src/core/sync.py` (`_apply_create_down`, `_propagation_proof`)
- `src/adapters/github_board.py` (`_remove_propagated_items_without_status`)

## Contexto

A implementação vigente considera item sem `Status` suspeito e item com
`Status` legítimo. Na recorrência de 25–26/08/2026, 17 de 17 relações geraram
participações indevidas e seis issues chegaram a sete despachos no fluxo
errado. Logo, coluna não representa decisão humana e não pode ser usada como
prova de intenção.

Também não existe hoje um gate independente em `keep_task`: se uma participação
indevida for materializada no snapshot com `status=ok`, ela pode ser selecionada.
A solução precisa preservar futuras participações multi-board deliberadas sem
interpretar omissão como autorização.

## Decisão

Toda participação será classificada como `origin`, `authorized`, `propagated`
ou `unresolved` antes de se tornar executável.

- `origin`: primeira participação comprovada em board configurado.
- `authorized`: board atual aparece na label reservada
  `board-intent-<board_id>` da issue.
- `propagated`: há participação confirmada em outro board configurado e não há
  autorização para o atual.
- `unresolved`: falta evidência ou existe conflito.

A autorização multi-board reutiliza labels e o comando `/labels` existentes.
Não será criado comando, campo customizado de Project ou cadastro externo nesta
entrega.

O snapshot cacheia `participation_intent` apenas para `origin` e `authorized`.
`keep_task` exige um desses valores além dos filtros atuais. Campo ausente,
valor pendente ou conflito bloqueia auto-advance e despacho. `Status` e
`parent` não concedem intenção.

Na migração, uma issue presente em um único board configurado recebe `origin`.
Duplicidades legadas sem label permanecem bloqueadas e exigem decisão
operacional; não se escolhe uma origem por ordem de filesystem ou prioridade.

## Justificativa

A label é persistida no GitHub, visível, auditável, já sincronizada pela
esteira e identifica o board autorizado no próprio nome. O cache no snapshot
evita rede em `keep_task`, mantendo o loop barato. O gate independente impede
que uma falha de reconciliação se transforme em consumo de agente.

Alternativas rejeitadas:

- **Continuar usando `Status`:** já falhou em produção e confunde automação com
  intenção.
- **Preservar toda participação com coluna:** mantém exatamente a brecha atual.
- **Remover toda ocorrência multi-board:** viola RF-04 e pode destruir uso
  legítimo futuro.
- **Campo customizado em cada Project:** semanticamente local, mas exige setup e
  consultas adicionais em todos os boards; não há caso atual que justifique.
- **Banco/serviço de autorização:** duplica estado e operação para um processo
  sequencial de baixo volume.
- **Inferir pelo tipo Epic/Story/Task:** cria pares hardcoded e viola RN-B10.

## Consequências

- Positivas: despacho passa a ser seguro por padrão; itens com `Status` deixam de
  escapar; multi-board tem autorização explícita; política é determinística e
  testável sem API.
- Negativas: snapshots ganham um campo; labels reservadas precisam ser
  documentadas; entradas legadas ambíguas podem ficar temporariamente sem
  execução.
- Riscos: remoção acidental da label revoga autorização; label com board
  inválido pode induzir falsa expectativa. Mitigação: validação, warning e
  comportamento fail-closed.
- Operação: para autorizar um board adicional, incluir
  `board-intent-<board_id>` em `/labels` ou na UI do GitHub antes de esperar
  execução naquele board. Ausência remove a autorização.
