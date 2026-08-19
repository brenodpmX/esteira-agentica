# Change #98 — Tentativa cancelada de correção de sub-issues propagadas

- **Tipo:** registro histórico de tentativa cancelada
- **Issue/PR:** #98 / PR #103
- **Commit de referência:** `01f9e83`
- **Decisão:** cancelada pelo débito #110 em favor de #88/PR #102
- **Disponibilidade:** não integrada; PR #103 fechado sem merge

## Contexto

A issue #98 implementou uma retentativa para impedir que sub-issues propagadas
sem `Status` fossem materializadas em boards incorretos. Embora essa branch
tenha sido homologada isoladamente, ela não foi escolhida como veículo de
entrega e não deve ser anunciada como correção publicada.

## Resultado da decisão

Para evitar duas implementações concorrentes nos mesmos pontos do core e do
adapter GitHub, o débito #110 definiu a issue #88 e o PR #102 como veículo
único. O retrabalho #106 corrigiu nesse veículo os problemas apontados pelo
code review: uso de GraphQL real, preservação explícita do project de origem,
prova de propagação no `create-down` e testes sem `monkeypatch` do método sob
teste.

A entrega efetiva está documentada em
[`doc/changes/88-sub-issues-propagadas-entre-boards.md`](88-sub-issues-propagadas-entre-boards.md)
e foi homologada em 19/08/2026. Este arquivo permanece apenas para preservar a
rastreabilidade da decisão e do PR #103 cancelado.
