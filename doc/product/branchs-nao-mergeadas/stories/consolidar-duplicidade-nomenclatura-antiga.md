# User Story — Consolidação de duplicidade e nomenclatura antiga

Status: aprovado
Owner: product
Epic: #73 "Branches não mergeadas"
Issue: #76
Last updated: 2026-07-24

## História

**Como** operador da esteira,
**quero** resolver a duplicidade de branches e a nomenclatura antiga — decidindo,
com base na análise do código, entre integrar o que houver de vivo ou abandonar —,
**para** que não reste nenhum nome duplicado nem padrão de nomenclatura antigo sem
dono na lista de branches.

## Contexto

Esta é a fatia que **depende de inspeção de código**, não de decisão de negócio
(**regra de negócio 5**). Um nome pode ser antigo e a branch ainda conter código
funcional; por isso não se economiza em análise. O papel do negócio aqui é
delimitar o alvo e o resultado esperado; a decisão caso a caso (integrar vs.
abandonar) é trabalho da etapa de desenvolvimento.

A análise de código foi realizada na etapa de Requisitos para fechar as lacunas
factuais antes da implementação. Os resultados estão registrados na seção
"Análise de código" abaixo e fundamentam as decisões caso a caso.

## Escopo — branches a analisar (evidência: `panorama-branches.md`, seção 4)

1. **Nomenclatura antiga (padrão com barra):**
   - `feature/1-1-rodar_no_docker` — padrão antigo da issue #1, que hoje convive
     com a branch atual `epic1-1-rodar_no_docker`. Decidir se há algo não
     absorvido na branch antiga antes de abandoná-la.

2. **Pares `epicNN` × `featureNN` (mesma issue, duas branches):**
   - Issues **#33, #34, #35, #40, #44, #45** têm branch de épico **e** de feature,
     sendo a `featureNN` já integrada na branch base `epic`. Verificar se a `epicNN`
     correspondente ainda carrega algo não absorvido pela branch base; se não,
     a `featureNN` é duplicata a remover.

3. **Issues duplicadas #46 / #47:**
   - `epic46` e `epic47` — issues **#46 e #47 têm título idêntico** ("Adicionar
     volumes de estado no docker-compose.yml"), ambas abertas. Consolidar em uma
     única versão e remover a duplicata.

## Análise de código (evidência para decisões)

### 1. `feature/1-1-rodar_no_docker` — nomenclatura antiga

**Evidência:**
- `git merge-base --is-ancestor origin/feature/1-1-rodar_no_docker origin/epic1-1-rodar_no_docker`
  → **verdadeiro**: o tip da `feature/1` é exatamente o merge-base com a `epic1`.
- Commits exclusivos em `feature/1` após a base comum com `epic1`: **nenhum**.

**Conclusão:** Todo o conteúdo da `feature/1-1-rodar_no_docker` já foi absorvido
pela `epic1-1-rodar_no_docker`. Não há nada a integrar.

**Decisão:** **Abandonar** (remover sem merge). Justificativa: a branch é resíduo
puro — a `epic1` já contém todo o histórico e arquivos que a `feature/1` tinha.

---

### 2. Pares `epicNN` × `featureNN` — issues #33, #34, #35, #40, #44, #45

**Evidência (aplicada a todos os pares):**

Para cada par verificou-se:

1. `git merge-base --is-ancestor origin/featureNN-... origin/epic`
   → **verdadeiro** para todas as 6 issues: os tips das `featureNN` são
   ancestrais da branch base `epic` (sem número).
   Ou seja, cada `featureNN` **já foi integrada via merge na branch `epic` base**.

2. As `epicNN` específicas (ex.: `epic33-33-...`) **divergiram** da `featureNN`
   correspondente a partir de um merge-base anterior. Nessas branches de trabalho
   há documentação e requisitos produzidos durante o desenvolvimento que ainda
   não chegaram ao `main` (ex.: `doc/stories/rodar-no-docker/ux/error-copy-spec.md`,
   `doc/arch/rodar-no-docker/...`, `doc/arquitetura/rodar-no-docker/...`).
   Esse conteúdo é **trabalho vivo em progresso na branch do épico**, não resíduo.

3. As `featureNN` específicas são **mais recentes** que as `epicNN` específicas
   (branch criada mais tarde por fork da linha de desenvolvimento), mas todo o
   código funcional que elas carregam (`.dockerignore`, `src/core/preflight.py`,
   `src/core/agent_guard.py`, `tests/`) **já está na branch `epic` base** (ponto 1).

**Conclusão:**
- As `featureNN` específicas são resíduo: todo o seu conteúdo já foi integrado
  na branch base `epic`.
- As `epicNN` específicas são trabalho vivo: carregam documentação e requisitos
  em progresso, ainda não no `main`.
- Não há conteúdo não absorvido nas `featureNN` que precise ser integrado antes
  da remoção.

**Decisão:**
- **Remover as `featureNN`** (resíduo integrado): `feature33`, `feature34`,
  `feature35`, `feature40`, `feature44`, `feature45`.
- **Preservar as `epicNN`** (trabalho vivo): as branches de épico específicas
  continuam como branches de trabalho até o merge.
- Não há necessidade de consolidação de conteúdo antes da remoção.

**Nota:** A remoção das `featureNN` é segura pois o conteúdo está na `epic` base,
confirmado por `merge-base --is-ancestor`. Nenhuma remoção sem análise.

---

### 3. Issues duplicadas #46 / #47 — `epic46` × `epic47`

**Evidência:**

Ambas as issues têm título idêntico: "Adicionar volumes de estado no
docker-compose.yml (US-04 — D-05)". Cada branch tem um único commit após a
base comum (`1ed917e`):

| Branch | Commit | Data | Linhas adicionadas |
|--------|--------|------|--------------------|
| `epic46` | `3f92999` | 2026-07-22 15:03 | 425 |
| `epic47` | `694667e` | 2026-07-22 15:13 | 443 |

O diff entre os dois commits mostra que `epic47` adiciona a seção `§9 —
.gitignore e os diretórios de estado` ao arquivo
`doc/stories/rodar-no-docker/arquitetura.md`. Essa seção registra uma análise
importante: o `.gitignore` existente já exclui os diretórios de runtime
corretamente, logo nenhuma alteração é necessária para D-05.

Os outros arquivos afetados (`user-stories.md`, `.env.prototipo`,
`docker-compose.prototipo.yml`) são **idênticos** nas duas branches.

**Conclusão:** `epic47` é a versão canônica — é mais recente e contém um
refinamento de requisito válido que `epic46` não tem. A `epic46` é a duplicata
a ser removida.

**Decisão:**
- **Branch canônica:** `epic47-47-adicionar_volumes_de_estado_no_docker_composeyml_us_04_d_05`
- **Branch duplicata:** `epic46-46-adicionar_volumes_de_estado_no_docker_composeyml_us_04_d_05` → remover
- **Issue canônica:** #47
- **Issue duplicata:** #46 → fechar como `not_planned` e desvincular do board

## Critérios de aceite

1. `feature/1-1-rodar_no_docker` removida do repositório remoto.
   Justificativa registrada: conteúdo 100% absorvido pela `epic1` (merge-base
   idêntico ao tip da feature).

2. Branches `feature33`, `feature34`, `feature35`, `feature40`, `feature44`,
   `feature45` removidas do repositório remoto.
   Justificativa registrada: todas são ancestrais da branch base `epic` —
   conteúdo integrado via merge, confirmado por `merge-base --is-ancestor`.

3. Branch `epic46` removida do repositório remoto.
   Issue #46 fechada como `not_planned` no board.
   Branch `epic47` e issue #47 preservadas como versão canônica.

4. Ao final, não há mais de uma branch representando a mesma tarefa nem branch
   de padrão antigo sem dono.

5. Nenhuma remoção ocorreu sem a análise de código que a fundamenta
   (registrada na seção "Análise de código" acima).

## Fora de escopo

- Resíduo já integrado de forma inequívoca (story própria — #74).
- Branches órfãs de tarefas arquivadas sem questão de duplicidade (story própria — #75).
- Alterar o processo/fluxo da esteira ou o conteúdo funcional das entregas além do
  necessário para consolidar as branches.
