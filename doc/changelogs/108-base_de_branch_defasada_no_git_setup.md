# Change File — Bug #108: base de branch defasada no Git Setup

**Data:** 2026-08-03
**Issue:** #108 — PR #105 da story #74 foi criado a partir de branch desatualizada
**Branch:** `fix108-108-criacao_atomica_de_branch_e_guard_de_base_no_git_setup`
**Branch de origem:** `epic` (a branch original `story74-74-remocao_segura_do_residuo_ja_integrado` foi removida após o merge do PR #105)
**Status:** Correção de código entregue; testes verdes

---

## Resumo

O PR #105 (`story74-...` → `epic`) nasceu de uma base errada: a branch foi
cortada de `main` (`26d863e`), não de `epic`, contrariando
`git.flow.story.create: epic`. Isso duplicou o trabalho de Docker nas duas linhas
de histórico e produziu `mergeable: CONFLICTING`.

Esta entrega corrige a causa raiz no código (`src/core/agent.py`) para que a
branch não possa mais nascer de base indeterminada, e adiciona um guard que
impede a abertura de PR a partir de base defasada.

## Alterações entregues

### C1 — Criação atômica da branch (`gitevents: create` / `create-merge`)

`build_prompt` emitia o Git Setup como comandos independentes:

```bash
git checkout <origem> && git pull origin <origem>
git checkout -b <branch>
```

A segunda linha não depende do sucesso da primeira. Se o checkout/pull da origem
falhasse (branch local ausente, divergente, pull recusado), o `checkout -b` ainda
criava a branch **a partir do HEAD corrente** — silenciosamente da base errada.

Agora o prompt emite um único comando sem fallback:

```bash
git fetch origin
git checkout -b <branch> origin/<origem>
```

Se `origin/<origem>` não existir, o comando falha em vez de inventar uma base.
Não se usa `-B`, que reescreveria uma branch local homônima existente.

### C2 — Guard de base atualizada antes do PR (`gitevents: merge` / `create-merge`)

Antes do `gh pr create`, o prompt passa a exigir que a branch contenha a ponta do
alvo de merge:

```bash
git fetch origin
git merge-base --is-ancestor origin/<merge> HEAD || git merge origin/<merge>
git push origin <branch>
```

O PR nasce sem defasagem, eliminando os conflitos por base velha e os falsos
alarmes de "PR destrutivo" que eles produzem.

### Testes

Nova suíte `tests/test_build_prompt_git_setup.py` (22 casos):

- criação a partir de `origin/<origem>` nos flows `story`, `feature`, `hotfix` e
  `epic` (origens `epic` e `main`);
- ausência do encadeamento frágil `git checkout <origem> &&`;
- ausência de `checkout -b <branch>` sem base explícita e de `-B`;
- `fetch` antes do `checkout -b`;
- regressão de `no-branch` (sem bloco de Git Setup) e de `use` (opera na branch
  da issue, não na origem do flow);
- guard `merge-base --is-ancestor` presente em `merge`/`create-merge`, com o alvo
  correto por flow, antes do `gh pr create`, e ausente em `create`/`use`/`no-branch`.

Suíte completa: 729 passaram, 23 skipped. As 3 falhas restantes em
`tests/test_docker_compose.py` são pré-existentes e ambientais (ausência de
`.env` no diretório de trabalho), sem relação com esta correção.

## Nota metodológica (C5) — como medir impacto de merge

O relato original desta issue afirmava que o merge do PR #105 "reverteria ~50
commits de `epic`". **Isso era factualmente incorreto** e custou um ciclo
completo de bug. A avaliação usou:

```bash
git diff origin/epic origin/story74-...   # ERRADO para prever merge
```

`git diff <base> <branch>` mede a **divergência entre duas pontas**, não o
resultado de um merge. Um merge do git é 3-way: um arquivo presente em `base` e
ausente na branch, mas **inalterado desde a merge-base**, é preservado — não
deletado. Por isso o diff exibia 11624 deleções que nenhum merge produziria.

Use, em vez disso:

```bash
git merge-tree --write-tree <base> <branch>   # resultado real do merge 3-way + conflitos
gh pr view <n> --json mergeable               # veredito do GitHub
```

No caso concreto, `git merge-tree` mostrou que o merge **falharia por 4 conflitos
`add/add`** (`.env.example`, `Dockerfile`, `docker-compose.yml`,
`prepare-docker.sh`) — o que explica o `CONFLICTING` —, mas em nenhuma hipótese
reverteria commits. O defeito real era a defasagem de base da branch, grave o
suficiente para justificar a correção, mas por outro motivo.

Verificação após o merge efetivo do PR #105 (`3a1d025`):

```bash
git diff --stat 949fc91 3a1d025                     # 13 arquivos, +1571, -31
git diff --diff-filter=D --name-only 949fc91 3a1d025 # vazio: nenhum arquivo removido
```

## Fora do escopo desta branch

Itens do plano de desenvolvimento que **não** foram executados aqui:

- **C3** — fechar o PR #83 e remover a branch remota
  `epic74-74-remocao_segura_do_residuo_ja_integrado`. Alteram estado
  compartilhado e exigem confirmação humana explícita. Evidência de segurança:
  `git log --oneline origin/epic..origin/epic74-74-...` retorna vazio (branch
  100% contida em `epic`).
- **C4** — forward-integrate `main` → `epic` (5 commits, todos de documentação).
  É operação sobre branch compartilhada, fora da etapa de correção.
