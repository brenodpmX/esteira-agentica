# Nota de arquitetura de integração — Convergência de linhagem para #249

Status: accepted
Owner: architecture
Last updated: 2026-09-16

## Inputs
- Débito arquitetural #296 (`Baseline documental (#230) e implementação de #242 não convergem numa base única para #249`)
- `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-004-convergencia-de-linhagem-para-base-unica-de-249.md`
- `doc/architecture/integridade-de-issues-entre-boards/overview.md`
- `doc/product/integridade-de-issues-entre-boards/dependencias-para-casos-de-teste-249.md`
- Topologia real das branches em `/app/repo/main` após `git fetch origin` (2026-09-16)

## Objetivo

Registrar, em nível de arquitetura de integração, **por que** as duas
dependências de #249 estão em linhagens separadas, **qual** é a base única
alvo, e **como** convergir de forma executável e verificável. Este documento
complementa a decisão em ADR-004: aqui está o passo a passo e os critérios de
verificação; lá está a justificativa e as alternativas rejeitadas.

Este documento **não** define regra de negócio nem detalha a implementação da
política (isso pertence a #242/#249). Ele trata exclusivamente da topologia de
branches e do procedimento de convergência.

## Topologia atual (evidência de 2026-09-16)

```text
                       fec6fe1  (PR #197 — ancestral comum, 2026-08-19)
                      /        \
                     /          \
   epic/230 (a19768a)            epic-integration (895e5e9)
   • business-rules.md           • src/core/participation_policy.py
   • adr-001 / adr-002 / adr-003 •   classify_participation
   • overview.md / constraints   • Board.list_participations
   • stories #245/#257/#258      •   remove_from_board / Participation
   (DOCS, sem impl de #242)      • cadeia #241/#248/#256/#263/#264/#265/#259/#251
                                 (IMPL, sem baseline documental)

   feature/249 (ca09e86)
   • deriva de 88da2cb (PR #218), não de nenhuma das duas
   • só possui commits de gestão do débito (#280, #296)
   • merge-base com ambas = fec6fe1
```

Fatos verificados por comando:

| Verificação | Resultado |
|---|---|
| `merge-base(epic/230, epic-integration)` | `fec6fe1` |
| `epic-integration` é ancestral de `epic/230`? | não |
| `epic/230` é ancestral de `epic-integration`? | não |
| `epic/230` é ancestral de `feature/249`? | não |
| `epic-integration` é ancestral de `feature/249`? | não |
| `participation_policy.py` em `epic/230` | ausente |
| `participation_policy.py` em `epic-integration` | presente |
| `business-rules.md`/`adr-001`/`adr-002` em `epic-integration` | ausentes |
| `business-rules.md`/`adr-001`/`adr-002` em `epic/230` | presentes |

## Base única alvo

`epic-integration` é a linha viva da implementação e concentra a maior parte da
cadeia de commits do épico. A convergência traz a **documentação** de `epic/230`
até `epic-integration`, formando `epic-integration'` (merge de convergência), e
`feature/249` passa a derivar dessa base.

Escolheu-se convergir **para** `epic-integration` (e não o contrário) porque
minimiza o volume de commits transportados e a superfície de conflito: a
documentação de `epic/230` toca sobretudo `doc/**`, enquanto o core vivo está em
`epic-integration`.

## Estratégia executável

> Pré-condição: `git fetch origin --prune` imediatamente antes, para operar
> sobre HEADs atuais. Reconfirmar o trial-merge antes de efetivar (as branches
> podem ter derivado após 2026-09-16).

### 1. Merge de convergência

```bash
git checkout -B epic-integration origin/epic-integration
git merge --no-ff origin/epic/230-integridade_de_issues_entre_boards
```

### 2. Resolver os conflitos previstos

O trial-merge de 2026-09-16 (executado sem commit e abortado) produziu **apenas
2 conflitos**; todo o core (`sync.py`, `board.py`, `agent.py`, `config.py`,
`__main__.py`) fez auto-merge limpo.

| Arquivo | Tipo | Resolução |
|---|---|---|
| `src/core/version.py` | content | Manter a **maior** versão. Nunca regredir o número. |
| `doc/architecture/retry-kiro-cli/idempotencia.md` | add/add | Unir o conteúdo das duas versões, sem perder seções. |

```bash
# após resolver manualmente os dois arquivos:
git add src/core/version.py doc/architecture/retry-kiro-cli/idempotencia.md
git commit    # mensagem: "merge: convergência baseline #230 + impl #242 (débito #296)"
```

### 3. (Re)criar a base de #249

```bash
git checkout -B feature/249-<slug> epic-integration
# transportar apenas os commits de gestão do débito que ainda façam sentido
# (cherry-pick seletivo); artefatos de #280/#296 já estão em docs e board.
git push --force-with-lease origin feature/249-<slug>
```

> `--force-with-lease` (nunca `--force` puro) protege contra sobrescrever
> trabalho remoto concorrente. A recriação muda o commit-base de #249; o board
> re-sincroniza a branch no ciclo seguinte.

## Critério de verificação (executável)

Após a convergência, na branch base de #249 (`<base>`):

```bash
# 1. Implementação presente na ancestralidade
git cat-file -e <base>:src/core/participation_policy.py
git grep -l "def classify_participation" <base> -- src/core/participation_policy.py
git grep -l "def list_participations"    <base> -- src/core/board.py

# 2. Baseline documental presente na ancestralidade
git cat-file -e <base>:doc/requirements/integridade-de-issues-entre-boards/business-rules.md
git cat-file -e <base>:doc/architecture/integridade-de-issues-entre-boards/decisions/adr-001-intencao-explicita-e-gate-fail-closed.md
git cat-file -e <base>:doc/architecture/integridade-de-issues-entre-boards/decisions/adr-002-reconciliacao-no-core-com-retentativa.md

# 3. Base convergida refletida em feature/249
git merge-base --is-ancestor <base> feature/249-<slug> && echo CONVERGIDO
```

As três verificações passando encerram o débito #296 e desbloqueiam a etapa de
Casos de Teste de #249 sem afrouxar o critério de QA de 28/08/2026.

## Fora de escopo

- Implementar ou alterar a política `classify_participation` (é #242/#249).
- Alterar regras de negócio ou o critério de desbloqueio de QA.
- Limpeza de resíduos históricos de propagação (permanece como no overview).
