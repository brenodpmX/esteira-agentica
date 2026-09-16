# ADR-004 — Convergência de linhagem numa base única para #249

Status: accepted
Owner: architecture
Last updated: 2026-09-16

## Inputs
- `doc/architecture/integridade-de-issues-entre-boards/overview.md`
- `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-001-intencao-explicita-e-gate-fail-closed.md`
- `doc/architecture/integridade-de-issues-entre-boards/decisions/adr-002-reconciliacao-no-core-com-retentativa.md`
- `doc/architecture/integridade-de-issues-entre-boards/integracao/convergencia-de-linhagem-249.md`
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md` (RN-B01/RN-B02/RN-B03/RN-B10)
- `doc/product/integridade-de-issues-entre-boards/dependencias-para-casos-de-teste-249.md` (critério de desbloqueio de QA + Addendum #296)
- Débito arquitetural #296 e sua avaliação de produto (Helena Costa, 2026-09-16)
- Topologia real das branches em `/app/repo/main` após `git fetch origin` (2026-09-16)

## Contexto

A task #249 (`ParticipationIntegrity.reconcile_after_link` no core, etapa
**Casos de Teste**) depende de dois insumos que, por definição da própria issue
e do critério de QA, precisam estar presentes na **ancestralidade da branch
base de #249**:

1. a implementação da política de classificação de #242
   (`src/core/participation_policy.py` com `classify_participation` →
   `origin`/`authorized`/`propagated`/`unresolved`, além de
   `Board.list_participations`, `remove_from_board` e o modelo `Participation`); e
2. a baseline documental do épico #230 — `business-rules.md`, `adr-001` e
   `adr-002` — como régua de aderência dos casos de teste.

A verificação de topologia (2026-09-16) mostrou que os dois insumos existem,
porém em **linhagens git divergentes** que só se reencontram no ancestral comum
`fec6fe1` (merge do PR #197, 2026-08-19):

| Branch | HEAD | Baseline docs (#230) | Implementação (#242) |
|--------|------|:---:|:---:|
| `origin/epic/230-integridade_de_issues_entre_boards` | `a19768a` | presente | ausente |
| `origin/epic-integration` | `895e5e9` | ausente | presente |
| `feature/249-…` (base atual da task) | `ca09e86` | ausente | ausente |

Evidências relevantes:

- `git merge-base origin/epic/230-… origin/epic-integration` = `fec6fe1`;
  nenhuma das duas é ancestral da outra.
- `git merge-base --is-ancestor origin/epic/230-… feature/249` → **não**;
  `git merge-base --is-ancestor origin/epic-integration feature/249` → **não**.
  O único ancestral comum de `feature/249` com ambas é `fec6fe1`.
- Em `epic-integration`, `src/core/participation_policy.py` existe (cadeia
  #248/#264/#265, PR #289); em `epic/230`, não existe.
- Em `epic/230`, `business-rules.md`, `adr-001`, `adr-002` (e `adr-003`)
  existem; em `epic-integration`, não existem.
- `feature/249` (`ca09e86`) carrega apenas a gestão do débito (#280/#296) e não
  possui nenhum dos dois insumos.

A avaliação de produto (débito #296) concluiu que **não há lacuna negocial
nova**: a implementação em `epic-integration` referencia e adere às mesmas
RN/ADR da baseline; o critério de desbloqueio de QA de 28/08/2026 permanece
válido. O que falta é exclusivamente **convergência de linhagem git** — decisão
de arquitetura de integração, e não de negócio. Este ADR registra essa decisão.

## Decisão

**Convergir numa base única** (opção 1 do débito #296), reunindo baseline
documental (#230) e implementação (#242) numa mesma linha de ancestralidade, e
então (re)criar `feature/249` a partir dela. A opção 2 (afrouxar o critério de
QA para referenciar a baseline por outro caminho) é **rejeitada**.

A convergência segue esta topologia-alvo:

```text
        fec6fe1 (ancestral comum, PR #197)
        /                         \
epic/230 (docs baseline)     epic-integration (impl #242)
        \                         /
         v                       v
        epic-integration' (merge de convergência)
                    |
                    v
        feature/249 recriada sobre a base convergida
```

Passos executáveis (detalhados na nota de integração
`integracao/convergencia-de-linhagem-249.md`):

1. Consolidar em `epic-integration` (linha da implementação, a mais viva) o
   conteúdo documental de `epic/230` por `git merge origin/epic/230-…`,
   preservando a ancestralidade das duas linhas.
2. Resolver os dois conflitos previstos — `src/core/version.py` (bump de versão)
   e `doc/architecture/retry-kiro-cli/idempotencia.md` (add/add) — mantendo a
   maior versão e a união do conteúdo documental. Os arquivos executáveis do
   core (`sync.py`, `board.py`, `agent.py`, `config.py`, `__main__.py`)
   fazem auto-merge sem conflito.
3. (Re)criar `feature/249` a partir da base convergida, transportando apenas os
   commits de gestão do débito que não conflitem com a nova ancestralidade.
4. Confirmar o critério de encerramento por comandos git (seção Consequências).

A execução dos passos 1–3 é operação de integração de branches, atribuída ao
fluxo de merge/integração do épico; este ADR fixa a **decisão** e o **critério
objetivo de convergência**.

## Justificativa

- **Uma única fonte de verdade na ancestralidade.** Casos de teste de #249
  devem validar a implementação real contra a baseline que a governa. Manter
  código e régua em linhagens separadas é dívida estrutural que reapareceria a
  cada nova task do épico, não só em #249.
- **Custo de convergência baixo e comprovado.** O trial-merge
  `epic-integration + epic/230` (executado sem commit em 2026-09-16) produziu
  **apenas 2 conflitos triviais** (`version.py`, `idempotencia.md`); todo o
  core auto-mesclou. O risco técnico da convergência é mínimo.
- **Preserva o critério negocial como régua.** A opção escolhida não altera as
  RN/ADR nem o critério de QA — apenas os torna alcançáveis pela ancestralidade,
  como exigido.
- **Fail-closed com a governança existente.** A convergência não introduz stack,
  serviço ou processo novo; reusa branches e o fluxo de merge do épico, coerente
  com ADR-003 (operar sobre mecanismos existentes).

Alternativas rejeitadas:

- **Afrouxar o critério de QA (opção 2):** aceitaria divergência permanente
  entre implementação integrada e baseline na ancestralidade. Documentar a
  régua "por outro caminho" enfraquece a rastreabilidade RF→RN→código e desloca
  para QA uma decisão de topologia que não lhe cabe.
- **Recriar a política dentro de #249:** proibido pelo corpo da issue ("se #242
  ainda não tiver sido mesclada, PARE") e duplicaria código já implementado.
- **Rebasear `feature/249` diretamente sobre uma das duas branches:** deixaria
  faltando o outro insumo (docs ou impl), sem resolver a divergência.
- **Convergir dentro de `epic/230` em vez de `epic-integration`:** possível, mas
  `epic-integration` concentra a cadeia de implementação viva (#241/#248/#256/
  #263/#264/#265/#259/#251); mover a documentação até ela minimiza o transporte
  de commits e o risco de conflito.

## Consequências

- **Positivas:** base única e rastreável para #249 e demais tasks do épico;
  desbloqueio de Casos de Teste sem inventar contrato nem afrouxar QA; risco de
  merge comprovadamente baixo; nenhuma mudança de regra de negócio.
- **Negativas:** exige uma operação de integração de branches (merge + resolução
  de 2 conflitos + recriação de `feature/249`) antes de QA prosseguir; o número
  de commit da base de #249 muda, exigindo re-sync da branch no board.
- **Riscos:**
  - *Deriva das branches após esta análise* — novos commits em `epic/230` ou
    `epic-integration` podem alterar a superfície de conflito. Mitigação:
    executar a convergência a partir de um `git fetch` imediatamente anterior e
    reconfirmar o trial-merge antes do commit.
  - *Perda dos commits de gestão do débito de `feature/249`* na recriação.
    Mitigação: a nova `feature/249` só precisa da ancestralidade convergida; os
    artefatos de débito (#280/#296) já estão registrados como documentação e
    comentários de board.
  - *Conflito de `version.py`* — resolver sempre para a maior versão, jamais
    regredindo o número de versão.

## Critério objetivo de convergência (encerramento)

O débito #296 e esta decisão são satisfeitos quando, na branch base de #249:

- `git cat-file -e <base>:src/core/participation_policy.py` **existe** e
  `classify_participation`, `list_participations`, `remove_from_board` e
  `Participation` estão na ancestralidade; **e**
- `git cat-file -e <base>:doc/requirements/integridade-de-issues-entre-boards/business-rules.md`,
  `…/decisions/adr-001-*.md` e `…/decisions/adr-002-*.md` **existem** na
  ancestralidade; **e**
- `git merge-base --is-ancestor <base> feature/249-…` retorna verdadeiro (a base
  convergida está refletida em `feature/249`).
