# Change #76 — Remover branch `feature/1-1-rodar_no_docker` (nomenclatura antiga)

- **Tipo:** limpeza de repositório (operação de git)
- **Escopo:** remoção de branch remota, sem alteração de código, documentação
  ou configuração
- **Parent:** story #76 (branches não mergeadas — épico #73)

## Contexto

A branch `feature/1-1-rodar_no_docker` usava o padrão antigo de nomenclatura
(com barra) da issue #1 e convivia com a branch atual `epic1-1-rodar_no_docker`,
branch de trabalho ativa da issue #1.

## Evidência (confirmada nos Requisitos e reconfirmada na execução)

`git merge-base --is-ancestor origin/feature/1-1-rodar_no_docker origin/epic1-1-rodar_no_docker`
retornou verdadeiro: o tip de `feature/1-1-rodar_no_docker` era exatamente o
merge-base com `epic1-1-rodar_no_docker`, sem nenhum commit exclusivo após esse
ponto. Todo o conteúdo já estava absorvido pela `epic1-1-rodar_no_docker`.

## Mudança entregue

- Branch remota `feature/1-1-rodar_no_docker` removida (`git push origin
  --delete`).
- Confirmação pós-remoção: `git fetch origin --prune` seguido de `git branch -r
  | grep "feature/1-1-rodar_no_docker"` retorna vazio.

Nenhum código, documentação ou configuração foi alterado — esta é uma operação
exclusiva de git sobre uma branch resíduo já integrada.

## Estado das dependências (issues filhas)

A task estava bloqueada por `/blocked_by #94, #95, #96`. Na verificação mais
recente, apenas a issue #94 foi localizada como filha real de #76, e está
concluída; #95 e #96 não correspondem a issues filhas ativas. Sem duplicação
de arquivos entre boards. Bloqueio considerado resolvido para esta task.

## Épico #73 — verificação de avanço

O épico #73 ("Branches não mergeadas") declara `/blocked_by #75` e
`/children #74, #75, #76`. Na verificação desta execução:

- **Story #75** ("Limpeza de branches órfãs de tarefas arquivadas") ainda está
  ativa na coluna `aguardando-tasks` — **não concluída**.
- **Story #74** não possui arquivo localizado em nenhum board — aparenta não
  ter sido criada/materializada ainda.

Como o bloqueio `/blocked_by #75` do épico #73 permanece ativo e #74 não está
confirmada como concluída, **o épico não atende ao critério para avançar**. A
conclusão desta task (#76) resolve apenas uma das três dependências do épico;
as demais (#74, #75) seguem pendentes. Nenhuma mudança de coluna foi aplicada
ao épico #73.
