# Changelog

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

## [Unreleased] - 2026-08-19

### Corrigido

- Remoção automática de sub-issues propagadas pelo GitHub Projects V2 para
  boards do parent quando o item chega sem `Status`. O pós-hook consulta
  `projectItems`/`fieldValues` via GraphQL e remove por
  `deleteProjectV2Item`; o project de origem é sempre preservado e, se não
  puder ser resolvido, nenhuma remoção é feita.
- Proteção no `create-down` para não criar arquivos locais nem entradas
  duplicadas para itens sem coluna, exigindo prova de propagação: a issue já
  registrada em outro board configurado com coluna conhecida. `parent`
  isolado não autoriza descarte, e snapshots de boards fora do `pipe.yml` não
  servem como prova. A remoção precisa concluir antes de o evento ser
  consumido.
- Detecção de coluna remota vazia como divergência e reconciliação escrevendo a
  coluna conhecida de volta no board, inclusive quando o arquivo local já está
  na coluna correta.
- `create_issue` aplica fallback para a primeira coluna do project, com
  warning, quando a coluna solicitada não existe, em vez de deixar o `Status`
  vazio silenciosamente.
- Nova primitiva `remove_from_board` na porta de board, implementada no adapter
  GitHub com `deleteProjectV2Item`.

### Segurança e compatibilidade

- Itens multi-board com `Status` definido são preservados; a remoção automática
  se restringe a itens de outros projects propagados sem coluna.
- Issues realmente novas, sem prova de presença em outro board configurado,
  usam a primeira coluna local como fallback, inclusive quando possuem
  `parent`.
- Não há mudança de schema nem de `pipe.yml`.
- Resíduos materializados antes desta correção não são apagados automaticamente
  e requerem limpeza manual com a esteira parada.

### Validação e disponibilidade

- Suíte canônica em `tests/test_sub_issue_propagation_fix.py`, exercitando o
  adapter e o core sem `monkeypatch` do método sob teste.
- Implementação final: issue #106, commit `a00ba7c`, no veículo #88/PR #102.
- Homologação aprovada em 19/08/2026. A disponibilidade em produção depende do
  merge do PR #102 e do deploy.

Detalhes: [`doc/changes/88-sub-issues-propagadas-entre-boards.md`](doc/changes/88-sub-issues-propagadas-entre-boards.md).
