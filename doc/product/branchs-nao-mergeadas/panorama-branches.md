# Panorama de branches — Épico #73

> Inventário completo das branches do repositório, classificado por situação.
> Gerado em 2026-07-24 com base na análise de negócio (#73) e verificação direta
> no repositório remoto + boards do GitHub.
>
> **Referência:** este documento é a fonte de verdade para as stories filhas do
> épico #73. Cada seção mapeia diretamente a uma story de execução.

---

## 1. Base do fluxo (preservar — não tocar)

Branches que definem a linha principal do projeto. Nunca removidas.

| Branch | Papel |
|--------|-------|
| `main` | Linha principal de produção |
| `epic` | Branch épica acumuladora — integra entregas antes de chegar à `main` |

---

## 2. Trabalho vivo (preservar — tarefas ativas)

Issues retiradas do backlog, não arquivadas, com branch ativa.

| Branch | Issue | Board / Coluna | Observação |
|--------|-------|---------------|------------|
| `epic73-73-branchs_nao_mergeadas` | #73 | Epic / Criação de Stories | Esta story (épico em andamento) |
| `epic1-1-rodar_no_docker` | #1 | Epic / Homologação | Ativo em homologação |
| `fix70-70-container_docker_nao_emite_logs_em_tempo_real` (*) | #70 | Bug / Correção | Ativo em correção |

(*) `fix70` não aparece na lista de branches remotas no momento deste levantamento —
confirmar antes de qualquer operação se foi removida ou ainda existe.

---

## 3. Resíduo já integrado (→ story #74)

Branches cujo conteúdo já foi absorvido por `main` ou por `epic`. Remoção
segura e sem risco de perda, pois nenhum commit exclusivo existe fora do
destino de integração.

### 3.1 Integradas em `main`

| Branch | Issue | Evidência |
|--------|-------|-----------|
| `feature7-7-incidente_issue_fantasma_correcao_2_contextmd_gerado_no_startup_a_partir_do_pipeyml` | #7 | Absorvida via `hotfix5` → PR #43 (commit `1ed917e` em `main`). `git log origin/feature7 ^origin/main` = vazio. |
| `hotfix5-5-incidente_issue_fantasma` | #5 | Mergeada diretamente em `main` via PR #43 (commit `1ed917e`). `git log origin/hotfix5 ^origin/main` = vazio. |

### 3.2 Integradas em `epic`

Verificação: `git merge-base --is-ancestor origin/<branch> origin/epic` retorna
sucesso para todas as branches abaixo.

| Branch | Issue | PR de integração (commit em `epic`) |
|--------|-------|-------------------------------------|
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

**Total seção 3:** 12 branches para remoção segura.

---

## 4. Duplicidade e nomenclatura antiga (→ story #76)

Decisão depende de inspeção de código — etapa de desenvolvimento, não de
negócio. O negócio define o alvo e o critério; a decisão caso a caso (integrar
vs. abandonar) é responsabilidade do desenvolvedor.

### 4.1 Nomenclatura antiga (padrão com barra)

| Branch | Issue | Situação |
|--------|-------|----------|
| `feature/1-1-rodar_no_docker` | #1 | Padrão antigo (barra no nome), convive com `epic1-1-rodar_no_docker` da mesma issue. Verificar se há conteúdo não absorvido antes de abandonar. |

### 4.2 Pares `epicNN` × `featureNN` (mesma issue, duas branches)

Issues que têm tanto uma branch `featureNN` (já integrada em `epic`) quanto
uma branch `epicNN` ainda pendente. A `featureNN` foi confirmada como resíduo
integrado (seção 3.2). O que fazer com a `epicNN` depende de inspeção.

| Branch épica | Branch feature (já em `epic`) | Issue |
|-------------|------------------------------|-------|
| `epic33-33-...` | `feature33-33-...` (PR #55) | #33 |
| `epic34-34-...` | `feature34-34-...` (PR #56) | #34 |
| `epic35-35-...` | `feature35-35-...` (PR #57) | #35 |
| `epic40-40-...` | `feature40-40-...` (PR #52) | #40 |
| `epic44-44-...` | `feature44-44-...` (PR #59) | #44 |
| `epic45-45-...` | `feature45-45-...` (PR #60) | #45 |

### 4.3 Issues duplicadas #46 / #47

| Branch | Issue | Situação |
|--------|-------|----------|
| `epic46-46-adicionar_volumes_de_estado_no_docker_composeyml_us_04_d_05` | #46 | Título idêntico à #47. Ambas abertas. |
| `epic47-47-adicionar_volumes_de_estado_no_docker_composeyml_us_04_d_05` | #47 | Título idêntico à #46. Ambas abertas. |

Decisão: definir issue/branch canônica, consolidar conteúdo, remover a
duplicata.

---

## 5. Branches órfãs de tarefas arquivadas (→ story #75)

Issues cujas branches **não** estão integradas em `main` nem em `epic`, mas
cuja issue correspondente já está **arquivada no board** (independente de ainda
estar aberta no GitHub como issue).

Regra de negócio aplicável:
- Issue que passou pela coluna "Cancelado" → remover sem merge.
- Trabalho absorvido por outro caminho → remover como resíduo.
- Conteúdo vivo não absorvido → não remover; encaminhar para análise de código.

### 5.1 Branches `epicNN` de sub-issues do épico #1

Issues #16–#21 são sub-issues do épico #1 (ativo em Homologação). Verificar se
o trabalho já foi absorvido pela branch `epic1` ou `epic` antes de remover.

| Branch | Issue | Título resumido |
|--------|-------|-----------------|
| `epic16-16-empacotar_a_esteira_em_imagem_docker` | #16 | Empacotar a esteira em imagem Docker |
| `epic17-17-autenticar_dependencias_externas_em_modo_headless` | #17 | Autenticar dependências externas em modo headless |
| `epic18-18-configurar_a_esteira_via_docker_compose_sem_rebuild` | #18 | Configurar a esteira via docker-compose sem rebuild |
| `epic19-19-persistir_estado_de_runtime_entre_reinicios` | #19 | Persistir estado de runtime entre reinícios |
| `epic20-20-operar_de_forma_autonoma_sem_intervencao_no_runtime` | #20 | Operar de forma autônoma sem intervenção no runtime |
| `epic21-21-documentar_a_operacao_em_docker` | #21 | Documentar a operação em Docker |
| `epic36-36-bump_de_versao_minor_pela_adicao_do_preflight_de_credenciais` | #36 | Bump de versão minor — preflight de credenciais |

### 5.2 Branches `hotfixNN` de issues arquivadas

| Branch | Issue | Título resumido |
|--------|-------|-----------------|
| `hotfix23-23-avaliacao_de_complexidade_falhando` | #23 | Avaliação de complexidade falhando |
| `hotfix24-24-issues_criadas_em_dois_boards_indevidamente` | #24 | Issues criadas em dois boards indevidamente |
| `hotfix27-27-log_nao_descritivo` | #27 | Conteúdo parcialmente absorvido. Decisão #125: preservar temporariamente, recriar apenas a formatação condicional sobre `epic` e remover após a task corretiva ser integrada. |

**Total seção 5:** ~10 branches para análise e remoção conforme critério.

---

## Resumo executivo

| Categoria | Qtd. branches | Story | Ação |
|-----------|--------------|-------|------|
| Base do fluxo | 2 | — | Preservar |
| Trabalho vivo | 3 | — | Preservar |
| Resíduo já integrado | 12 | #74 | Remover (seguro) |
| Duplicidade / nomenclatura antiga | ~9 | #76 | Analisar código → decidir |
| Órfãs de arquivadas | ~10 | #75 | Analisar → remover ou preservar |

> Levantamento realizado em 2026-07-24. Verificar o estado atual das branches
> antes de executar qualquer remoção — o cenário pode ter mudado.
