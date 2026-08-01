# Changelog

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

## [1.6.1] - 2026-08-01

### Corrigido

- Remoção automática de sub-issues propagadas pelo GitHub Projects V2 para
  boards do parent quando o item chega sem `Status`.
- Proteção no `create-down` para não criar arquivos locais nem entradas
  duplicadas para itens sem coluna que já pertencem a outro board ou possuem
  parent.
- Detecção de coluna remota vazia como divergência e reconciliação com a coluna
  conhecida localmente.
- Nova primitiva `remove_from_board` na porta de board, implementada no adapter
  GitHub com `deleteProjectV2Item`.

### Segurança e compatibilidade

- Itens multi-board com `Status` definido são preservados; a remoção automática
  se restringe a itens propagados sem coluna.
- Issues realmente novas, sem parent e sem presença em outro board, mantêm o
  fallback local para a primeira coluna configurada.
- Resíduos já materializados antes desta versão não são apagados
  automaticamente e requerem limpeza manual com a esteira parada.

### Testes

- Adicionados nove testes de regressão para remoção do project, pós-hook de
  sub-issue, guards do `create-down`, fallback de issue nova, reconciliação de
  coluna e detecção de divergência.
