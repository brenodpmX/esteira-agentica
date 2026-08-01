# Change #98 — Sub-issues propagadas entre boards sem coluna

- **Tipo:** correção de bug
- **Versão:** 1.6.0
- **Plataforma afetada:** GitHub Projects V2
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`

## Problema

Ao relacionar uma sub-issue a um parent presente em outro project, o GitHub
propaga automaticamente a filha para o project do parent sem definir o campo
`Status`. O sync tratava esse item como uma issue nova no board de destino e
criava arquivos locais duplicados. Isso podia provocar execução pelo agente do
board errado e atualizações concorrentes sobre a mesma issue.

## Mudanças

- Adicionada a operação `remove_from_board` à porta de board e ao adapter
  GitHub, implementada com `deleteProjectV2Item`.
- Após vincular uma sub-issue, itens propagados sem `Status` são removidos dos
  projects; itens já posicionados em uma coluna são preservados.
- `create-down` sem coluna é descartado quando há evidência de que a issue é
  propagada de outro board, sem materializar body, history ou addcomment.
- Issues realmente novas sem coluna usam a primeira coluna local como fallback.
- Issues já rastreadas que perdem o `Status` têm a coluna conhecida reaplicada.
- Criações com coluna inexistente usam a primeira opção configurada e emitem
  warning.
- A comparação remota passou a considerar coluna vazia como divergência.

## Impacto para operação

Não há migração nem alteração de configuração. Depois do deploy, acompanhe os
logs pelas operações `remove_propagated_without_column`, `remove_from_board` e
`create_issue`. Warnings nessas operações indicam falha de consulta/remoção ou
uso do fallback de coluna.

A correção não limpa duplicatas anteriores ao deploy. Resíduos existentes devem
ser removidos em uma operação manual separada, com a esteira parada, para evitar
concorrência com o sync.

## Validação

A preparação da branch registrou **201 testes aprovados e 3 ignorados**, build
Docker bem-sucedido e smoke test de imports. Os dois testes novos cobrem os
caminhos do guard de `create-down`; os comportamentos que exigem o adapter real
continuam no roteiro manual de staging em
[`doc/homologacao-98-sub-issues-propagadas.md`](../homologacao-98-sub-issues-propagadas.md).
