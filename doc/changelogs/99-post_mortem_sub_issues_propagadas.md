# Change File — Post mortem #99: sub-issues propagadas entre boards

**Data:** 2026-08-04
**Versão:** 1.6.1
**Issue:** #99 — Post mortem do incidente de duplicação e ausência de coluna
**Branch:** `epic99-99-post_mortem_do_incidente_corrigir_duplicacao_e_ausencia_de_coluna_em_sub_issues_propagadas_entre_boards_github_projects_v2`
**Status:** documentação homologada; correção de runtime pendente de integração

## Resumo

Esta entrega publica o post mortem do incidente em que sub-issues propagadas
automaticamente pelo GitHub Projects V2, sem `Status`, eram materializadas como
duplicatas locais em boards incorretos.

## Alterações entregues

- Post mortem completo em `doc/incidente/sub-issues-propagadas/ticket.md`.
- Histórico de homologação em
  `doc/incidente/sub-issues-propagadas/homologacao.md`.
- Resumo operacional e alerta de disponibilidade no `README.md`.
- Política técnica de uso de GraphQL para GitHub Projects V2 no `CONTEXT.md`.
- Change funcional #98 em
  `doc/changes/98-sub-issues-propagadas-entre-boards.md`.
- Versão da Pipe incrementada de 1.6.0 para 1.6.1.

## Estado da correção #98

A implementação final foi homologada no commit `01f9e83` com 208 testes
aprovados e 3 ignorados. O PR #103, porém, foi fechado sem merge em 03/08/2026;
o código não está em `main` nem nesta branch. Assim, esta release documenta a
solução e sua pendência, mas não altera o comportamento de runtime relacionado
a sub-issues propagadas.

## Impacto

- **Código-fonte:** somente `src/core/version.py` foi alterado.
- **Runtime:** sem a correção #98; risco residual explicitamente documentado.
- **Configuração:** nenhuma mudança em `pipe.yml`.
- **Operação:** monitorar itens sem `Status` e realizar limpeza de resíduos com
  a esteira parada.
