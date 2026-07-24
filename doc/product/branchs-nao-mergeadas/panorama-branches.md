# Panorama das Branches — retrato real (evidência)

Status: atualizado — requisitos story #75
Owner: product
Last updated: 2026-07-24

> Levantamento feito diretamente no repositório e no board (GitHub), cruzando
> cada branch com a issue correspondente, seu estado (ativa / backlog /
> arquivada) e se o trabalho já foi integrado à linha principal (`main`) ou à
> branch base do épico (`epic`). Serve de base factual para a análise; as
> decisões que dependem de inspeção de código ficam para a etapa de
> desenvolvimento.

## Como ler
- **Integrada em `main`**: o trabalho já está na linha principal → é resíduo.
- **Integrada em `epic`**: o trabalho já foi absorvido pela branch do épico que
  o originou → é resíduo (regra de negócio 3).
- **Ativa**: issue fora do backlog e não arquivada → trabalho vivo, preservar.
- **Arquivada**: issue já encerrada → branch órfã; remover se resíduo/sem razão,
  analisar se houver dúvida.

## 1. Branches base do fluxo — PERMANECEM
| Branch | Papel |
|--------|-------|
| `main` | Linha principal |
| `epic` | Branch base do fluxo de épicos (não é resíduo de tarefa) |

## 2. Trabalho vivo (tarefas ativas) — PRESERVAR
| Branch | Issue | Situação da tarefa |
|--------|-------|--------------------|
| `epic73-73-branchs_nao_mergeadas` | #73 | Esta demanda (em Análise de Negócio) |
| `epic1-1-rodar_no_docker` | #1 | Ativa — em Homologação |
| `fix70-70-container_docker_nao_emite_logs...` | #70 | Ativa — em Correção (branch local) |

## 3. Resíduo já integrado — REMOÇÃO SEGURA
Trabalho já entregue; a branch é sobra.

**Integrado na linha principal (`main`):**
| Branch | Issue |
|--------|-------|
| `feature7-7-...contextmd_gerado_no_startup...` | #7 |
| `hotfix5-5-incidente_issue_fantasma` | #5 |

**Integrado na branch do épico (`epic`):**
| Branch | Issue |
|--------|-------|
| `feature28-28-...persistir_agent_level...` | #28 |
| `feature33-33-...copy_mensagens_de_erro_ssh...` | #33 |
| `feature34-34-...preflight_verificacao_credenciais...` | #34 |
| `feature35-35-...integrar_preflight...` | #35 |
| `feature37-37-...docker_compose_servico_volumes...` | #37 |
| `feature40-40-...dockerfile_pythonunbuffered...` | #40 |
| `feature41-41-...docker_compose_credenciais...` | #41 |
| `feature42-42-...runbook_operacao_docker...` | #42 |
| `feature44-44-...fixar_versoes_dependencias...` | #44 |
| `feature45-45-...dockerfile_da_esteira...` | #45 |

## 4. Duplicidade e nomenclatura antiga — ANALISAR NO DESENVOLVIMENTO
Decisão de integrar ou abandonar depende de inspeção do código (regra 5).

- `feature/1-1-rodar_no_docker` — **nomenclatura antiga** (com barra), da issue
  #1; convive com a branch atual `epic1-1-rodar_no_docker`.
- Pares em que a mesma issue tem branch de épico **e** de feature, sendo a
  feature já integrada na `epic`: issues **#33, #34, #35, #40, #44, #45**
  (`epicNN` × `featureNN`). Verificar se a `epicNN` ainda carrega algo não
  absorvido.
- `epic46` e `epic47` — issues **#46 e #47 são duplicadas** (mesmo título,
  "Adicionar volumes de estado no docker-compose.yml"). Consolidar em uma só.

## 5. Órfãs de tarefa arquivada — decisões (story #75)

Análise concluída na etapa de requisitos da story #75. Ver detalhes em
`stories/limpeza-branches-orfas-arquivadas.md`.

### 5a. Remover — absorvidas (8 branches)

Trabalho refeito por tasks posteriores do épico ou código equivalente integrado
via outro PR. Nenhuma branch carrega código funcional ausente de `epic`/`main`.

| Branch | Issue | Razão |
|--------|-------|-------|
| `epic16-16-empacotar_a_esteira_em_imagem_docker` | #16 | Doc de exploração substituída pelas tasks do épico |
| `epic17-17-autenticar_dependencias_externas_em_modo_headless` | #17 | Doc de exploração substituída pelas tasks do épico |
| `epic18-18-configurar_a_esteira_via_docker_compose_sem_rebuild` | #18 | Doc de orquestração substituída por feature37/feature41 |
| `epic19-19-persistir_estado_de_runtime_entre_reinicios` | #19 | Doc de persistência substituída pelas tasks |
| `epic20-20-operar_de_forma_autonoma_sem_intervencao_no_runtime` | #20 | Doc substituída por feature35 (preflight) |
| `epic21-21-documentar_a_operacao_em_docker` | #21 | Runbook refeito por feature42 (já no epic) |
| `epic36-36-bump_de_versao_minor_pela_adicao_do_preflight_de_credenciais` | #36 | Bump e preflight absorvidos por feature34/35 |
| `hotfix27-27-log_nao_descritivo` | #27 | Código absorvido por feature31 (PR #32, integrado ao epic) |

### 5b. Analisar no desenvolvimento (2 branches)

Contêm apenas ticket de incidente (sem código). Decisão pendente: preservar
histórico em `main`/`epic` (merge antes de remover) ou descartar.

| Branch | Issue | Pergunta para o desenvolvimento |
|--------|-------|----------------------------------|
| `hotfix23-23-avaliacao_de_complexidade_falhando` | #23 | Preservar `doc/incidente/avaliacao-complexidade-falhando/ticket.md`? |
| `hotfix24-24-issues_criadas_em_dois_boards_indevidamente` | #24 | Preservar `doc/incidente/issues_criadas_em_dois_boards_indevidamente/ticket.md`? |

## Resumo executivo
- **Total além da `main`:** ~33 branches (2 base + 3 vivas + as demais são
  resíduo ou candidatas a análise).
- **Preservar sem discussão:** `main`, `epic` e as 3 branches de tarefas ativas.
- **Remover com segurança (resíduo integrado):** 12 branches (2 na `main` + 10
  na `epic`). Ver seção 3.
- **Analisar no desenvolvimento (duplicidade/antigas):** a branch de padrão
  antigo `feature/1`, os pares `epicNN`×`featureNN` e a duplicata #46/#47.
  Ver seção 4.
- **Remover — órfãs absorvidas (story #75):** 8 branches confirmadas.
- **Analisar no desenvolvimento — órfãs com ticket de incidente (story #75):**
  2 branches (hotfix23 e hotfix24).
