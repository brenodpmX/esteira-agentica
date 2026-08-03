# Change File — Story #74: Remoção segura do resíduo já integrado

**Data:** 2026-07-24
**Story:** #74 — Remoção segura do resíduo já integrado
**Épico:** #73 — Branches não mergeadas
**Branch:** `epic74-74-remocao_segura_do_residuo_ja_integrado`
**Status:** Concluído

---

## Resumo

Remoção das 12 branches cujo conteúdo já estava comprovadamente integrado à
`main` ou à branch base do épico `epic`. A verificação git foi executada antes
de cada remoção (sem commit exclusivo fora do destino) e os critérios de aceite
foram 100% satisfeitos.

---

## Alterações entregues

### 1. Documentação criada

#### `doc/product/branchs-nao-mergeadas/panorama-branches.md`
- Inventário completo de todas as branches do repositório, classificado por
  situação: base do fluxo / trabalho vivo / resíduo integrado / duplicidade /
  órfãs arquivadas.
- Inclui commits de merge específicos, números de PR e procedimento git de
  verificação para cada branch.
- Serve de fonte de verdade para as três stories filhas do épico #73.
- Commit: `b39a8e6` ("Requisitos: Remoção segura do resíduo já integrado")

#### `doc/product/branchs-nao-mergeadas/stories/remocao-residuo-integrado.md`
- Especificação completa da story #74 com tabelas de evidências e procedimento
  de verificação pré-remoção.
- Commit: `b39a8e6` ("Requisitos: Remoção segura do resíduo já integrado")

---

### 2. Branches remotas removidas

Executadas pelas tasks filhas #77, #78 e #79. Todas as remoções foram
precedidas de evidência de integração.

#### Tasks executadas

| Task | Escopo | PR mergeado |
|------|--------|------------|
| #77 | Verificar e remover branches integradas em `main` (feature7, hotfix5) | PR #80 → `epic` |
| #78 | Remover branches integradas em `epic` — lote A (feature28, 33, 34, 35, 37) | PR #81 → `epic` |
| #79 | Remover branches integradas em `epic` — lote B (feature40, 41, 42, 44, 45) | PR #82 → `epic` |

#### Branches integradas em `main` — removidas

| Branch | Issue | Evidência de integração |
|--------|-------|------------------------|
| `feature7-7-incidente_issue_fantasma_correcao_2_contextmd_gerado_no_startup_a_partir_do_pipeyml` | #7 | Absorvida via `hotfix5` → PR #43 (`1ed917e`). `git log origin/feature7 ^origin/main` = vazio. |
| `hotfix5-5-incidente_issue_fantasma` | #5 | Mergeada em `main` via PR #43 (`1ed917e`). `git log origin/hotfix5 ^origin/main` = vazio. |

#### Branches integradas em `epic` — removidas

| Branch | Issue | PR de integração |
|--------|-------|-----------------|
| `feature28-28-refatoracao_persistir_agent_level_via_label_agent_level_nivel_no_github` | #28 | PR #29 (`bacea2e`) |
| `feature33-33-ajustar_copy_das_mensagens_de_erro_de_ssh_para_contexto_docker` | #33 | PR #55 (`71bc5a7`) |
| `feature34-34-implementar_funcao_preflight_de_verificacao_de_credenciais_no_arranque` | #34 | PR #56 (`1ef0f59`) |
| `feature35-35-integrar_preflight_ao_fluxo_de_boot_da_esteira` | #35 | PR #57 (`6019f62`) |
| `feature37-37-criar_docker_composeyml_com_servico_volumes_secret_e_envs` | #37 | PR #63 (`1393318`) |
| `feature40-40-criar_dockerfile_com_pythonunbuffered1_e_usuario_nao_root_ac_04ac_05_da_us_01_e_us_05` | #40 | PR #52 (`30490ed`) |
| `feature41-41-criar_docker_composeyml_com_credenciais_volumes_e_restart_unless_stopped_us_03_ac_03_da_us_05` | #41 | PR #64 (`fb13442`) |
| `feature42-42-validar_e_finalizar_o_runbook_de_operacao_docker_us_06_21_rf_08` | #42 | PR #65 (`d9311fa`) |
| `feature44-44-levantar_e_fixar_versoes_exatas_das_dependencias_da_imagem_docker` | #44 | PR #59 (`a0a1ae6`) |
| `feature45-45-criar_dockerfile_da_esteira_us_01` | #45 | PR #60 (`64252b4`) |

---

### 3. Testes adicionados

| Task | Testes adicionados |
|------|--------------------|
| #77 | 21 casos |
| #78 | 26 casos |
| #79 | 26 casos |
| **Total** | **73 casos** |

---

## Critérios de aceite — verificação

| Critério | Status |
|----------|--------|
| Cada remoção precedida de evidência de integração (`git log` / `git merge-base`) | ✅ |
| 12 branches removidas do repositório remoto | ✅ |
| Nenhuma branch ativa (#73, #1, main, epic) foi tocada | ✅ |
| Nenhuma branch revelou commit não integrado (exceção ao escopo) | ✅ |

---

## Impacto

- **Repositório:** 12 branches removidas do remoto.
- **Código/funcionalidade:** sem alteração — nenhum arquivo de código foi
  modificado, apenas branches já integradas foram limpas.
- **Documentação:** dois arquivos criados em
  `doc/product/branchs-nao-mergeadas/`.
- **Branches preservadas:** `main`, `epic`, `epic73-73-branchs_nao_mergeadas`,
  `epic1-1-rodar_no_docker`, `fix70-70-container_docker_nao_emite_logs_em_tempo_real`.

---

## Fora de escopo (não entregue nesta story)

- Branches órfãs de tarefas arquivadas → story #75
- Duplicidade e nomenclatura antiga (`epicNN`×`featureNN`) → story #76

---

## Addendum — correção de branch desatualizada (2026-08-03)

O code review anterior (PR #105) reprovou o merge porque a branch
`story74-74-remocao_segura_do_residuo_ja_integrado` havia divergido de `epic`
desde o commit `26d863e`: cada lado acumulou histórico próprio (78 commits em
`epic` — Docker, preflight, correções do incidente Issue Fantasma — vs. 10
commits na story, incluindo hotfix5). Um merge direto teria revertido/apagado
esse trabalho publicado em `epic`.

**Correção aplicada:** merge de `origin/epic` na branch da story
(commit `6d4d5d9`), resolvendo manualmente os 4 conflitos de conteúdo
(`.env.example`, `Dockerfile`, `docker-compose.yml`, `prepare-docker.sh`) em
favor da versão mais recente de `epic` — a story não tinha alterações próprias
nesses arquivos, apenas versões antigas herdadas do ponto de divergência.

**Resultado:**
- `gh pr view 105` → `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`.
- Diff do PR #105 caiu de 1710 inserções / 11624 deleções para
  **1541 inserções / 31 deleções**, restrito à documentação da story e ao
  próprio merge de sincronização — sem perda de trabalho de `epic`.
- Suíte de testes: 707 passed, 23 skipped, 3 failed (falhas pré-existentes em
  `epic` por dependência de `.env` local ausente no ambiente — não
  relacionadas a esta story nem introduzidas pelo merge).

O bug reportado em `bug/backlog/correcao-story74-branch-desatualizada-gera-pr-destrutivo`
está resolvido por este addendum e pode ser encerrado/arquivado quando
sincronizado ao board.
