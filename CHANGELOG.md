# Changelog

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

## [1.6.1] - 2026-08-01

### Corrigido

- Remoção automática de sub-issues propagadas pelo GitHub Projects V2 para
  boards do parent quando o item chega sem `Status`. O pós-hook consulta
  `projectItems`/`fieldValues` via GraphQL (Projects V2 não existe na REST API)
  e remove por `deleteProjectV2Item`; o project informado é sempre preservado e,
  se não puder ser resolvido, nenhuma remoção é feita.
- Proteção no `create-down` para não criar arquivos locais nem entradas
  duplicadas para itens sem coluna, exigindo prova de propagação: a issue já
  registrada em outro board configurado com coluna conhecida. `parent` isolado
  não autoriza descarte, e snapshots de boards fora do `pipe.yml` não servem
  como prova. Falha na remoção propaga em vez de descartar o evento.
- Detecção de coluna remota vazia como divergência e reconciliação escrevendo a
  coluna conhecida de volta no board, inclusive quando o arquivo local já está
  na coluna correta (antes a divergência retornava em todo full sync).
  Movimentação remota legítima deixou de reescrever a coluna no board.
- `create_issue` aplica fallback para a primeira coluna do project (com warning)
  quando a coluna solicitada não existe, em vez de pular o `Status` em silêncio.
- Nova primitiva `remove_from_board` na porta de board, implementada no adapter
  GitHub com `deleteProjectV2Item`.

### Segurança e compatibilidade

- Itens multi-board com `Status` definido são preservados; a remoção automática
  se restringe a itens propagados sem coluna, em projects distintos do informado.
- Issues realmente novas, sem prova de presença em outro board configurado,
  mantêm o fallback local para a primeira coluna configurada — inclusive quando
  possuem `parent`.
- Resíduos já materializados antes desta versão não são apagados
  automaticamente e requerem limpeza manual com a esteira parada.

### Testes

- Suíte canônica de regressão em `tests/test_sub_issue_propagation_fix.py`
  exercitando a implementação real (sem monkeypatch do método sob teste):
  pós-hook em GraphQL com `_gh`/`_api` proibidos, preservações (project de
  origem e itens com `Status`), fail-safe de project não resolvido, fallback de
  `create_issue`, prova exigida pelo guard do `create-down`, falha de remoção
  que não consome o evento, reconciliação do `change-down` e detecção de
  divergência de coluna vazia.
