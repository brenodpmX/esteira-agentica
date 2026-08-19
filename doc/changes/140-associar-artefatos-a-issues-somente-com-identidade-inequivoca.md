# Change #140 — Associar artefatos a issues somente com identidade inequívoca

- **Tipo:** correção de confiabilidade (US-03 do épico #104, incidente #97)
- **Plataforma afetada:** `src/core/sync.py`
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`; novo arquivo de
  estado interno `.pipe/orphanFiles.json`, já incluído em `PROTECTED_PATHS` e
  no `CONTEXT.md` gerado
- **Implementação:** entregue via decomposição em 3 tasks técnicas, todas
  mergeadas em `main`
- **Integração:** `#146` e `#147` foram mergeadas em `epic` (PRs #159 e #160);
  `#148` foi mergeada em **`main`** (PR #188), fora do `flow.feature.merge`
  configurado (`epic`). Por isso o estado completo desta story — incluindo
  `tests/test_regressao_colisao_76.py` — só chegou a `epic` através da
  reconciliação `main → epic` executada no bug **#190**, e não pelo merge das
  tasks. Antes dessa reconciliação, `epic` era ancestral estrito de `main` (36
  commits atrás) e não continha o teste que fecha o critério de aceite.

## Problema

O fallback de resolução do body de uma issue por prefixo numérico podia
escolher o primeiro arquivo compatível encontrado no filesystem, mesmo sem
garantia de que o arquivo pertencesse de fato à issue. Foi esse fallback que,
no incidente #97/#76, associou um artefato órfão à issue #76 e substituiu seu
conteúdo, disparando um loop de erro que travou o processamento de todos os
boards por ~2h37.

## Mudanças implementadas

Entregues pelas 3 tasks filhas da story (todas mergeadas em `main`):

- **#146 — Resolução determinística do body da issue por identidade**
  (`_find_issue_files` em `src/core/sync.py`): o path do snapshot só é aceito
  com validação completa (existe, pertence ao board, sufixo `-body.md`,
  prefixo do ID, não pertence a outra issue). Em fallback, exige candidato
  único por nome completo ou por prefixo numérico; zero ou múltiplos
  candidatos recusam a resolução em vez de escolher o primeiro resultado do
  filesystem.
- **#147 — Detecção e sinalização de arquivos órfãos sem match confiável**:
  `detect_local_changes` usa a mesma regra de match confiável para classificar
  arquivos com prefixo numérico sem correspondência como órfãos, com evidência
  deduplicada por `(board, identifier, reason, content_fingerprint)` em
  `.pipe/orphanFiles.json`.
- **#148 — Regressão composta da colisão #76**: teste de integração
  (`tests/test_regressao_colisao_76.py`) cobrindo o fluxo completo
  `detect_local_changes` → fila → `apply_changes` → `_apply_change_up`,
  confirmando zero chamadas de atualização e zero substituições de
  título/body/labels/relações quando a identidade do arquivo é ambígua, e a
  aplicação correta quando a resolução é inequívoca.

## Critérios de aceite — verificação

- Caminho do snapshot só aceito com identidade completa validada — entregue
  em #146.
- Arquivo movido: busca por nome completo aceita apenas candidato único —
  entregue em #146.
- Prefixo numérico sem match confiável é sinalizado como órfão, sem criar ou
  alterar issue — entregue em #147.
- Evidência de isolamento com board, ID aparente, caminho, motivo e próximo
  passo, sem alertas repetidos — entregue em #147 (dedupe por fingerprint).
- Reprodução da colisão `76-*` com zero chamadas de atualização e zero
  substituições — entregue e coberto por teste em #148.
- Arquivos novos sem prefixo numérico preservam o fluxo normal de criação —
  coberto pelos testes de `tests/test_orphan_detection.py` e
  `tests/test_orphan_file_collision.py`.

## Estado dos bloqueios

A story #140 dependia das 3 tasks acima (`/blocked_by #146, #147, #148`,
registrado no histórico em 2026-08-04). As três estão hoje na coluna
`encerrado` e mergeadas: `#146` e `#147` em `epic` (PRs #159 e #160), `#148` em
`main` (PR #188). O bloco `@---` atual do body de #140 não lista mais
`/blocked_by` — os bloqueios foram resolvidos. A story está desbloqueada e
pronta para avançar.

### Divergência de branch de destino (bug #190)

O PR #188 (`#148`) foi aberto com base `main` em vez de `epic`, contrariando
`flow.feature.merge` do board. Consequência: o merge desta story em `epic` não
levaria `tests/test_regressao_colisao_76.py` nem ~138 linhas de
`src/core/sync.py` para a branch de integração, e a story fecharia declarando
um critério de aceite que `epic` não podia comprovar. O bug **#190** reconciliou
`main → epic` (fast-forward, 33 arquivos / ~4.296 linhas) por dentro do fluxo do
board, via branch de correção derivada da branch da story. A base da
`feature148` estava correta (`954e5ea` tem como pai o HEAD de `epic`) — o desvio
foi apenas o destino do PR.

## Pendência observada (fora de escopo desta etapa)

O `/children` atual do body de #140 lista apenas `#146, #147`, sem `#148`,
embora #148 seja filha confirmada (existe em
`.pipe/boards/task/encerrado/148-...`) e referenciada no histórico. Não
corrigi essa relação nesta etapa por estar fora do objetivo de Change File;
sinalizado no addcomment para reconciliação.
