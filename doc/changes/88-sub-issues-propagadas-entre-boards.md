# Change #88 — Sub-issues propagadas entre boards sem coluna

- **Tipo:** correção de bug
- **Plataforma afetada:** GitHub Projects V2
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`
- **Veículo:** issue #88 / PR #102
- **Correção final:** issue #106 / commit `a00ba7c`
- **Homologação:** aprovada em 19/08/2026
- **Disponibilidade:** integrada à branch do PR #102; merge e deploy pendentes

## Problema

Ao relacionar uma sub-issue a um parent presente em outro project, o GitHub
pode propagar automaticamente a filha para o project do parent sem definir o
campo `Status`. O sync tratava esse item como issue nova no board de destino e
criava arquivos locais duplicados, permitindo execução pelo agente errado e
atualizações concorrentes sobre a mesma issue.

## Mudanças entregues

- `BoardPort`, `Board` e o adapter GitHub expõem `remove_from_board`, com
  remoção via mutation GraphQL `deleteProjectV2Item`.
- Após `_add_sub_issue`, `_remove_propagated_items_without_status` consulta
  `projectItems`/`fieldValues` via GraphQL e remove itens de outros projects
  sem `Status`.
- O project informado como origem é sempre preservado, mesmo temporariamente
  sem `Status`; se ele não puder ser resolvido, nenhuma remoção é feita.
- Itens com `Status` definido são preservados, inclusive participações
  multi-board intencionais.
- O guard de `create-down` só descarta um item sem coluna quando existe prova
  de propagação: a issue já está registrada em outro board configurado com
  coluna conhecida. A presença de `parent`, isoladamente, não basta.
- A remoção remota precisa concluir antes de o `create-down` ser consumido;
  falhas são reenfileiradas pelo tratamento de erros transitórios.
- Issues realmente novas sem coluna usam a primeira coluna local como fallback.
  Issues rastreadas que perdem o `Status` têm a coluna conhecida reaplicada.
- `create_issue` aplica a primeira opção do project, com warning, quando a
  coluna solicitada não existe.
- Coluna remota vazia passou a ser detectada como divergência.

## Histórico de decisão

O PR #102 original foi reprovado porque usava endpoints REST inexistentes para
Projects V2 e mascarava o defeito com `monkeypatch` do método sob teste. A
retentativa #98/PR #103 foi cancelada pelo débito #110 para evitar dois
veículos concorrentes. A issue #88/PR #102 permaneceu como veículo único, e o
retrabalho #106 entregou a implementação GraphQL final no commit `a00ba7c`.

## Validação

A suíte canônica `tests/test_sub_issue_propagation_fix.py` cobre o pós-hook
GraphQL real, preservação do project de origem, preservação de item com
`Status`, fail-safe de project não resolvido, prova de propagação no
`create-down`, fallback para issue legítima, falha de remoção sem criação de
arquivo local, fallback de `create_issue`, reconciliação de `change-down` e
detecção de coluna vazia. A homologação funcional foi aprovada em 19/08/2026.

## Limitação operacional

A correção previne novas duplicações, mas não remove resíduos anteriores.
Itens como #84/#85/#86 devem ser removidos manualmente do project indevido com
a esteira parada.

Post mortem: [`doc/incidente/sub-issues-propagadas/ticket.md`](../incidente/sub-issues-propagadas/ticket.md).
Tentativa cancelada: [`change #98`](98-sub-issues-propagadas-entre-boards.md).
