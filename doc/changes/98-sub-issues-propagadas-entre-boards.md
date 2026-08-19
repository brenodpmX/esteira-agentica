# Change #98 — Sub-issues propagadas entre boards sem coluna

- **Tipo:** correção de bug
- **Versão-alvo:** 1.6.1
- **Plataforma afetada:** GitHub Projects V2
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`
- **Implementação:** commit `01f9e83`, homologado
- **Integração:** pendente; PR #103 fechado sem merge em 03/08/2026

## Problema

Ao relacionar uma sub-issue a um parent presente em outro project, o GitHub
propaga automaticamente a filha para o project do parent sem definir o campo
`Status`. O sync tratava esse item como issue nova no board de destino e criava
arquivos locais duplicados. Isso podia provocar execução pelo agente do board
errado e atualizações concorrentes sobre a mesma issue.

## Mudanças implementadas na hotfix

- Adicionada a operação `remove_from_board` à porta de board e ao adapter
  GitHub, implementada com GraphQL `deleteProjectV2Item`.
- Após vincular uma sub-issue, itens propagados sem `Status` são removidos dos
  projects; itens já posicionados em coluna são preservados.
- `create-down` sem coluna é descartado quando há evidência de propagação de
  outro board, sem materializar body, history ou addcomment.
- Issues realmente novas sem coluna usam a primeira coluna local como fallback;
  issues rastreadas que perdem o `Status` têm a coluna conhecida reaplicada.
- Criações com coluna inexistente usam a primeira opção configurada e emitem
  warning.
- A comparação remota passou a considerar coluna vazia como divergência.

## Estado de disponibilidade

Essas mudanças existem no commit `01f9e83`, mas não estão nesta branch nem em
`main`. O PR #103 foi fechado sem merge. Este change file registra o conteúdo
homologado e a pendência de integração; não constitui anúncio de deploy.

A correção não limpa duplicatas anteriores. Resíduos como #84/#85/#86 devem ser
removidos numa operação manual separada, com a esteira parada.

## Validação

A hotfix terminou com **208 testes aprovados e 3 ignorados**. A cobertura em
`tests/test_sub_issue_propagation_fix.py` exercita oito cenários, incluindo o
adapter via mocks de `_gql`/`_gh`, preservação de item legítimo, fallback de
coluna, detecção de divergência e regressão entre o guard de `create-down` e o
fallback de `change-down`.

Post mortem: [`doc/incidente/sub-issues-propagadas/ticket.md`](../incidente/sub-issues-propagadas/ticket.md).
