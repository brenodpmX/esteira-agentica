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

A preparação da branch registrou **208 testes aprovados e 3 ignorados** (7 novos em relação
à revisão anterior, que somava 201). Uma revisão de código anterior (PR #103) havia reprovado
a primeira versão desta correção: o pós-hook de remoção (`_remove_propagated_without_column`)
chamava um endpoint REST inexistente na API do GitHub e falhava silenciosamente em produção;
foi reescrito usando GraphQL, no mesmo padrão já usado por `_belongs_to_board`/`get_issue`.
Os 4 cenários do escopo original agora têm teste exercitando o adapter real (mock de
`_gql`/`_gh`, sem substituir o método sob teste), incluindo um teste de regressão para a
interação entre o guard do `create-down` e o fallback do `change-down`. Build Docker
bem-sucedido, com smoke test confirmando dentro da imagem que o pós-hook usa GraphQL. Os
comportamentos que exigem a API real do GitHub (timing de propagação, schema exato de
resposta) continuam no roteiro manual de staging em
[`doc/homologacao-98-sub-issues-propagadas.md`](../homologacao-98-sub-issues-propagadas.md).
