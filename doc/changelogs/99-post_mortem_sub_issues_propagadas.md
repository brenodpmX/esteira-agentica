# Change File — Post mortem #99: sub-issues propagadas entre boards

- **Data original:** 2026-08-04
- **Atualização:** 2026-08-19
- **Issue:** #99 — post mortem do incidente #88
- **Status:** documentação atualizada; correção final homologada

## Resumo

Esta entrega publica o post mortem do incidente em que sub-issues propagadas
automaticamente pelo GitHub Projects V2, sem `Status`, eram materializadas como
duplicatas locais em boards incorretos.

## Artefatos

- Post mortem: `doc/incidente/sub-issues-propagadas/ticket.md`.
- Roteiro e resultado de homologação:
  `doc/incidente/sub-issues-propagadas/homologacao.md`.
- Resumo operacional: `README.md`.
- Política técnica de GraphQL para Projects V2: `CONTEXT.md`.
- Entrega funcional: `doc/changes/88-sub-issues-propagadas-entre-boards.md`.
- Tentativa cancelada: `doc/changes/98-sub-issues-propagadas-entre-boards.md`.

## Estado da correção

O débito #110 definiu #88/PR #102 como veículo único e cancelou #98/PR #103.
A implementação final foi entregue pelo retrabalho #106 no commit `a00ba7c`,
usando GraphQL real, preservando o project de origem e exigindo prova de
propagação no `create-down`. A homologação foi aprovada em 19/08/2026.

O merge do PR #102 e o deploy ainda são necessários para disponibilidade em
produção.

## Impacto

- **Runtime:** previne novas duplicações e reconcilia ausência de coluna.
- **Configuração:** nenhuma mudança de schema ou de `pipe.yml`.
- **Compatibilidade:** itens multi-board com `Status` e issues novas legítimas
  são preservados.
- **Operação:** resíduos anteriores, como #84/#85/#86, exigem limpeza manual
  com a esteira parada.
