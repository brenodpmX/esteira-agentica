# Change File — Branches não mergeadas (#73)

**Data:** 2026-08-20
**Issue:** #73 — Branches não mergeadas
**Filhas:** #74 — Remoção segura do resíduo já integrado; #75 — Limpeza de
branches órfãs de tarefas arquivadas; #76 — Consolidação de duplicidade e
nomenclatura antiga
**Branch:** `epic73-73-branchs_nao_mergeadas`
**Versão:** 1.10.1
**Status:** homologado; pronto para merge/release

## Resumo

Faxina pontual e criteriosa das branches do repositório, sem mudança de
processo nem automação de encerramento de branch. O repositório acumulava
mais de 30 branches além de `main`/`epic`, misturando trabalho vivo, resíduo
já integrado, branches órfãs de tarefas arquivadas e duplicidade de
nomenclatura. Ao final, restam apenas `main`, `epic` e as branches de
tarefas ativas.

## Escopo entregue

- **#74 — Remoção segura do resíduo já integrado:** 12 branches confirmadas
  como já mergeadas em `main` (2) ou `epic` (10) removidas do remoto via
  `git push --delete`.
- **#75 — Limpeza de branches órfãs de tarefas arquivadas:** 8 branches
  órfãs de issues arquivadas removidas. `temp-hotfix23-merge` e
  `temp-hotfix24-merge` foram preservadas deliberadamente — decisão sobre
  manter o histórico de incidente em `main`/`epic` ainda pendente, registrada
  em `doc/product/branchs-nao-mergeadas/stories/limpeza-branches-orfas-arquivadas.md`.
- **#76 — Consolidação de duplicidade e nomenclatura antiga:** branch de
  padrão antigo `feature/1-1-rodar_no_docker` removida; duplicata das issues
  #46/#47 consolidada em uma única branch canônica (`epic47`); issue
  renomeada para refletir a entrega real.

## Natureza da entrega

Esta é uma operação de higiene de repositório (`git branch`/`git push
--delete` no remoto), não uma entrega de código de produto. A branch do
épico não carrega commits de funcionalidade — apenas a documentação de
negócio, o merge de `main` para permitir a homologação do ambiente, e este
change file. Por isso o bump de versão é **PATCH** (1.10.0 → 1.10.1): não há
mudança de comportamento em runtime, schema ou `pipe.yml`.

## Documentação atualizada

- versão em `src/core/version.py`: `1.10.0` → `1.10.1`;
- `CHANGELOG.md` com a entrada 1.10.1;
- `README.md` já referenciava o runbook de homologação (adicionado na etapa
  de pré-produção);
- `doc/runbook/homologacao-branches-nao-mergeadas.md` — runbook específico de
  homologação, cobrindo validação do estado das branches no remoto e subida
  do ambiente Docker Compose;
- `doc/product/branchs-nao-mergeadas/panorama-branches.md` — inventário real
  das branches, evidência branch a branch das decisões tomadas.

## Validação

- Estado do remoto (`git branch -a`) cruzado com o panorama original:
  confirmadas ausentes as 12 branches de resíduo integrado, as 8 branches
  órfãs absorvidas e a branch de nomenclatura antiga.
- Nenhuma branch de tarefa ativa (`main`, `epic`, branches de issues em
  andamento) foi removida.
- Merge de `main` na branch do épico validado sem regressão: suíte de testes
  com 1121 aprovados e as mesmas 24 falhas pré-existentes também em `main`
  isolada (confirmado via `git worktree`).
- Build/`up` reais do Docker Compose não foram executados nesta rodada
  (ambiente de execução sem Docker disponível) — limitação já explicitada no
  runbook de homologação.

## Compatibilidade

- bump PATCH, sem breaking change;
- sem migração de schema ou `pipe.yml`;
- sem mudança de comportamento da esteira em runtime.

## Critério de encerramento

As regras de negócio confirmadas (tarefa ativa preservada; remoção sem merge
apenas com prova de resíduo ou integração; duplicidade/nomenclatura antiga
decidida na etapa de desenvolvimento) foram aplicadas branch a branch, com
evidência registrada no panorama. Nenhum trabalho vivo foi perdido.

## Referências

- `doc/product/branchs-nao-mergeadas/problem-space.md`
- `doc/product/branchs-nao-mergeadas/vision.md`
- `doc/product/branchs-nao-mergeadas/panorama-branches.md`
- `doc/product/branchs-nao-mergeadas/stories/`
- `doc/runbook/homologacao-branches-nao-mergeadas.md`

— Isabela Gomes - Tech Lead
