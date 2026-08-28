# Resultados de Teste — Merge request da story #241 usa branch com base incorreta e traz alterações fora de escopo para o epic

Status: approved
Owner: quality
Last updated: 2026-08-28

## Inputs
- Bug #287 — Merge request da story #241 usa branch com base incorreta e traz
  alterações fora de escopo para o epic (board Bug)
- Issue original #241 — Contingência de suspensão de vínculos entre boards
- Branch de correção: `bugfix241-merge-request-story241-branch-base-incorreta`
  (`01a90c8`)
- Histórico da correção (etapas Reteste anteriores: Análise Técnica e
  Correção aplicada, ambas de Bruno Ferreira — Engenheiro de Software SR)

Não existe documento de casos de teste dedicado para este bug: é um defeito
topológico de branch (base de git incorreta), não uma falha de lógica de
negócio com casos de teste pré-escritos. Os critérios abaixo replicam
exatamente o "portão de aceite" (seção 5, Passo 2) e as evidências de escopo
e regressão registradas nas etapas anteriores (Análise Técnica e Correção
aplicada), reexecutados de forma independente nesta etapa de Reteste.

## CT01 — Branch de correção contém a ponta de `origin/epic`

**Resultado:** passed

**Observações:**
- `git merge-base --is-ancestor origin/epic HEAD` → `OK`. Confirma que
  `bugfix241-merge-request-story241-branch-base-incorreta` (`01a90c8`) tem
  `origin/epic` (`cdf79cf`) como ancestral direto — a base agora é a correta,
  conforme exigido pelo flow `story` (`create`/`merge: epic`).

## CT02 — Diff contra `origin/epic` contém exatamente 1 arquivo, apenas inserções

**Resultado:** passed

**Observações:**
- `git diff --stat origin/epic HEAD` → `1 file changed, 116 insertions(+)`,
  arquivo
  `doc/changelogs/241-contingencia-suspensao-vinculos-entre-boards.md`. Sem
  deleções. Idêntico ao valor esperado registrado no portão de aceite da
  correção.

## CT03 — Exatamente 1 commit acima de `origin/epic`

**Resultado:** passed

**Observações:**
- `git log --oneline origin/epic..HEAD` → apenas `01a90c8` ("Change File:
  Contingência de suspensão de vínculos entre boards"). Nenhum commit
  intermediário sobrevivente do merge de sincronização (`b7aa9b8`) ou da base
  antiga (`88da2cb`).

## CT04 — Branch não descende mais do commit antigo de `main` (`88da2cb`)

**Resultado:** passed

**Observações:**
- `git merge-base --is-ancestor 88da2cb HEAD` → falso ("does NOT descend").
  Confirma que a reescrita da base removeu a ancestralidade problemática
  identificada na Análise Técnica (`merge-base b0dcf58 origin/epic` = `fec6fe1`,
  não `cdf79cf`).

## CT05 — Guarda de escopo: nenhum arquivo fora do escopo da story #241

**Resultado:** passed

**Observações:**
- `git diff --name-only origin/epic HEAD` filtrado por
  `src/|README.md|CONTEXT.md|CHANGELOG.md|parent-recursivo|branchs-nao-mergeadas`
  → nenhum match. O único arquivo do diff é o changelog da própria story.

## CT06 — `src/` byte-idêntico a `origin/epic` (confirmação por conteúdo, não só por nome de arquivo)

**Resultado:** passed

**Observações:**
- `git diff origin/epic HEAD -- src/` → vazio (0 linhas). Reconfirma, nesta
  etapa de Reteste e de forma independente, o mesmo resultado já registrado
  na etapa de Correção.

## CT07 — Rename `agent-hub` ausente; `override-agent`/`agent_level` preservados

**Resultado:** passed

**Observações:**
- `grep -r "agent-hub" src/` → 0 ocorrências (após remover `__pycache__`
  obsoleto do checkout anterior, que poluiu uma busca intermediária com
  binário compilado — mesmo artefato não versionado já observado e descartado
  na etapa de Correção; removido nesta execução antes da busca final).
- `grep -r "override-agent" src/` → 7 ocorrências; `grep -r "agent_level"
  src/` → 37 ocorrências. Ambos presentes, sem o rename de `main`
  (`0f8dce4`) reintroduzido.

## CT08 — `migrate_agent_level_labels` preservada (definição e call site)

**Resultado:** passed

**Observações:**
- `grep -n "migrate_agent_level_labels" src/core/sync.py src/__main__.py` →
  definição em `src/core/sync.py:1347` e import + chamada em
  `src/__main__.py:7` e `:189`. A remoção que veio de `main` **não** entrou
  na branch corrigida.

## CT09 — Suíte completa sem regressão em relação à linha de base de `epic`

**Resultado:** passed

**Observações:**
- `python -m pytest tests/ -q` na branch de correção →
  **21 failed, 1295 passed, 29 skipped, 1 xpassed**. Valor idêntico ao
  registrado na etapa de Correção (mesma contagem) e ao baseline de
  `origin/epic` isolado já validado em ciclos de QA anteriores (#255/#256)
  nesta mesma base de código.
- As 21 falhas pertencem integralmente a `tests/test_dockerfile.py`
  (pinagem de versão/SHA256 do `kiro-cli`) e `tests/test_agent_log_descritivo.py`
  (formato de log descritivo do agente) — arquivos não tocados por esta
  correção (que altera apenas um `.md` de changelog) e sem qualquer relação
  com o defeito de base de branch. `git status --short` confirma árvore de
  trabalho limpa (nenhuma alteração de código de produção fora do commit já
  registrado).
- Como `src/`, `tests/`, `Dockerfile` e `docker/` são byte-idênticos a
  `origin/epic` (CT06), o conjunto de falhas é determinístico e não podia
  divergir do baseline.

## Resumo

- Total: 9
- Passou: 9
- Falhou: 0
- Bloqueado: 0

## Conclusão

Bug confirmado corrigido, sem regressão. A branch de correção
(`bugfix241-merge-request-story241-branch-base-incorreta`, `01a90c8`) tem
agora `origin/epic` como base real, contém exatamente 1 commit
(`+116/-0`, apenas o changelog da story #241) e não carrega nenhuma das
~2500 linhas fora de escopo identificadas no bug original (rename
`agent-hub`, remoção de `migrate_agent_level_labels`, documentação de
`parent-recursivo`/`branchs-nao-mergeadas`). A suíte completa reproduz
exatamente o mesmo resultado (21 failed / 1295 passed / 29 skipped / 1
xpassed) já atribuído a falhas pré-existentes em `epic`, não relacionadas a
esta correção.

Nota sobre o objetivo desta etapa: nenhum código de produção foi criado ou
alterado no Reteste — apenas reexecução independente das verificações de
escopo, ancestralidade e regressão já descritas nas etapas de Análise Técnica
e Correção, confirmando que continuam válidas.

Nota sobre escopo remanescente (já registrada nas etapas anteriores, não
bloqueante para este reteste): o PR #286 ainda não foi atualizado com o
conteúdo desta branch (`force-with-lease` para o head ref
`story241-241-contingencia_de_suspensao_de_vinculos_entre_boards`) — isso é
ato de integração, correto ficar fora do escopo de Correção/Reteste e
pertencer à etapa de Merge Request. A causa raiz (board `story` sem coluna
com `gitevents: create` no `pipe.yml`) permanece fora do alcance de qualquer
PR deste repositório, por ser configuração de operador não versionada.

Aprovado — avançar para **advance** (merge-request).

— Camila Rocha - Engenheira de Qualidade (QA)
