# Post Mortem — Duplicação e ausência de coluna em sub-issues propagadas entre boards

## Registro

- **Incidente:** #88
- **Post mortem:** #99
- **Tentativa cancelada:** #98 / PR #103
- **Retrabalho final:** #106 / commit `a00ba7c`
- **Veículo único:** #88 / PR #102, por decisão do débito #110
- **Status:** correção implementada e homologada em 19/08/2026; merge e deploy pendentes
- **Owner:** engenharia
- **Abertura:** 2026-08-01
- **Última atualização:** 2026-08-19

## Resumo

Ao vincular uma sub-issue a um parent presente em outro GitHub Project, o
GitHub Projects V2 pode adicionar a filha ao project do parent sem preencher o
campo `Status`. Antes da correção, o sync podia interpretar o item sem coluna
como uma issue nova daquele board, criar arquivos locais duplicados e executar
o agente no contexto errado.

A correção final remove a propagação indevida por GraphQL, impede a
materialização local quando há prova de propagação e reconcilia ausências de
coluna sem remover sub-issues legítimas.

## Impacto observado

- Execução duplicada pelo agente do board incorreto.
- Escritas concorrentes no mesmo número de issue e oscilação de body.
- Itens sem coluna, invisíveis no fluxo normal do project.
- Resíduo em #84/#85/#86 no project `story`, com arquivos locais duplicados.

A correção é preventiva. O resíduo anterior continua exigindo remoção manual
com a esteira parada.

## Reincidência

| Registro | Data | Observação |
|----------|------|------------|
| #24 | 2026-07-06 | Primeiro diagnóstico do “Fenômeno 1” |
| #45 | 2026-07-22 | Segunda ocorrência |
| #88 | 2026-08-01 | Terceira ocorrência, envolvendo #84/#85/#86 |

## Causa raiz

Quatro falhas se combinavam:

1. Não existia primitiva para remover um item de um GitHub Project V2.
2. `_add_sub_issue` não verificava a propagação automática após criar o vínculo.
3. `create-down` não distinguia item propagado de issue nova legítima sem coluna.
4. Coluna remota vazia não era tratada consistentemente como divergência.

A distinção segura não pode depender apenas de `parent`: uma sub-issue nova e
legítima também pode chegar sem coluna. O descarte exige prova de que a própria
issue já está registrada em outro board configurado com coluna conhecida.

## Histórico das tentativas

### PR #102 original — reprovado

A primeira implementação usava endpoints REST inexistentes para Projects V2 e
um teste que substituía o próprio método sob teste. A suíte passava sem
exercitar o caminho produtivo. O code review originou o retrabalho #106.

### Issue #98 / PR #103 — cancelada

Uma implementação concorrente foi homologada isoladamente no commit `01f9e83`,
mas o débito #110 cancelou esse veículo para evitar duas soluções nos mesmos
arquivos. O PR #103 foi fechado sem merge.

### Issue #106 / commit `a00ba7c` — entrega final

O retrabalho foi aplicado no veículo #88/PR #102 e corrigiu os achados do code
review:

- consulta `projectItems`/`fieldValues` via GraphQL;
- remoção via `deleteProjectV2Item`;
- project de origem preservado, inclusive sem `Status`;
- item com `Status` preservado em qualquer project;
- ausência de resolução do project de origem resulta em nenhuma remoção;
- guard de `create-down` exige prova de propagação;
- suíte canônica exercita a implementação real, sem `monkeypatch` do método.

## Correção entregue

1. `remove_from_board` foi adicionada a `BoardPort`, `Board` e ao adapter
   GitHub.
2. `_remove_propagated_items_without_status` consulta os itens após
   `_add_sub_issue` e remove somente itens de outros projects sem `Status`.
3. `_apply_create_down` remove e descarta o evento apenas quando
   `_propagation_proof` encontra a issue em outro board configurado com coluna
   conhecida.
4. Issues novas sem prova de propagação usam a primeira coluna local como
   fallback, ainda que tenham `parent`.
5. `create_issue` usa a primeira opção do project, com warning, quando a coluna
   solicitada não existe.
6. `detect_board_changes` considera coluna vazia uma divergência, e
   `_apply_change_down` reaplica a coluna conhecida para issues rastreadas.

## Garantias de segurança

- O project de origem informado ao pós-hook nunca é removido.
- Participações multi-board com `Status` são preservadas.
- Snapshots de boards fora do `pipe.yml` não servem como prova de propagação.
- O `create-down` só é consumido depois que `remove_from_board` conclui; falhas
  transitórias são reenfileiradas e não criam arquivos locais.
- Se o project de origem não puder ser identificado, o pós-hook não remove
  nenhum item.

## Validação

A suíte canônica está em `tests/test_sub_issue_propagation_fix.py` e cobre o
adapter GraphQL, as preservações, os fallbacks, a prova de propagação, falhas de
remoção, reconciliação de coluna e detecção de divergência. A implementação foi
integrada à branch do PR #102, atualizada com `main` e homologada em
19/08/2026.

A disponibilidade em produção depende do merge do PR #102 e do deploy.

## Aprendizados e ações preventivas

1. Operações de GitHub Projects V2 devem usar GraphQL; REST fica restrito às
   APIs tradicionais de issues e pull requests.
2. Testes não podem substituir o próprio método cuja implementação pretendem
   validar.
3. Cenários de aceite não automatizados precisam de lacuna explícita no PR e
   responsável definido.
4. O code review deve conferir o schema real da API quando um novo endpoint ou
   mutation for introduzido.
5. Resíduos #84/#85/#86 devem ser limpos em operação separada, com a esteira
   parada.

## Referências

- [Change efetivo #88](../../changes/88-sub-issues-propagadas-entre-boards.md)
- [Tentativa cancelada #98](../../changes/98-sub-issues-propagadas-entre-boards.md)
- [Changelog documental #99](../../changelogs/99-post_mortem_sub_issues_propagadas.md)
