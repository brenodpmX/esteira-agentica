# Panorama das Branches — retrato real (evidência)

Status: aprovado
Owner: product
Last updated: 2026-07-24 (seção 4 atualizada pela issue #76 — Requisitos)

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

## 4. Duplicidade e nomenclatura antiga — ANÁLISE CONCLUÍDA (issue #76)

A análise de código foi realizada na etapa de Requisitos (issue #76).
Decisões registradas abaixo; detalhamento completo em
`stories/consolidar-duplicidade-nomenclatura-antiga.md`.

### 4.1 `feature/1-1-rodar_no_docker` — nomenclatura antiga
| Item | Resultado |
|------|-----------|
| Tip da feature é ancestral de `epic1`? | **Sim** |
| Commits exclusivos após merge-base | **Nenhum** |
| **Decisão** | **Abandonar** — conteúdo 100% absorvido pela `epic1` |

### 4.2 Pares `epicNN` × `featureNN` — issues #33, #34, #35, #40, #44, #45
| Branch | Integrada na `epic` base? | Conteúdo não absorvido? | Decisão |
|--------|--------------------------|------------------------|---------|
| `feature33` | Sim | Não | Remover |
| `feature34` | Sim | Não | Remover |
| `feature35` | Sim | Não | Remover |
| `feature40` | Sim | Não | Remover |
| `feature44` | Sim | Não | Remover |
| `feature45` | Sim | Não | Remover |

As `epicNN` específicas carregam documentação viva (requisitos, ADRs, specs UX)
ainda não no `main` — **preservar** como branches de trabalho ativas.

### 4.3 Issues duplicadas #46 / #47
| Branch | Commits únicos | Conteúdo extra | Decisão |
|--------|----------------|----------------|---------|
| `epic46` | 1 (2026-07-22 15:03) | — | **Remover** (duplicata) |
| `epic47` | 1 (2026-07-22 15:13) | Seção §9 em `arquitetura.md` | **Preservar** (canônica) |

- Branch canônica: `epic47`; issue canônica: **#47**
- Branch/issue a remover: `epic46` / **#46** (fechar como `not_planned`)

## 5. Órfãs de tarefa arquivada, não integradas — ANALISAR / REMOVER
Issues já arquivadas cujo branch não aparece integrado nem em `main` nem em
`epic`. Verificar, na etapa de desenvolvimento, se o trabalho foi absorvido por
outro caminho (então é resíduo) ou se a tarefa foi cancelada (regra 4 → remover
sem merge) ou abandonada.

| Branch | Issue | Estado da issue |
|--------|-------|-----------------|
| `epic16-16-empacotar_a_esteira_em_imagem_docker` | #16 | Arquivada (fechada) |
| `epic17-17-autenticar_dependencias_externas...` | #17 | Arquivada (fechada) |
| `epic18-18-configurar_a_esteira_via_docker_compose...` | #18 | Arquivada |
| `epic19-19-persistir_estado_de_runtime...` | #19 | Arquivada |
| `epic20-20-operar_de_forma_autonoma...` | #20 | Arquivada (fechada) |
| `epic21-21-documentar_a_operacao_em_docker` | #21 | Arquivada |
| `epic36-36-bump_de_versao_minor...preflight...` | #36 | Arquivada |
| `hotfix23-23-avaliacao_de_complexidade_falhando` | #23 | Arquivada |
| `hotfix24-24-issues_criadas_em_dois_boards...` | #24 | Arquivada |
| `hotfix27-27-log_nao_descritivo` | #27 | Arquivada (fechada) |

## Resumo executivo
- **Total além da `main`:** ~33 branches (2 base + 3 vivas + as demais são
  resíduo ou candidatas a análise).
- **Preservar sem discussão:** `main`, `epic` e as 3 branches de tarefas ativas.
- **Remover com segurança (resíduo integrado):** 12 branches (2 na `main` + 10
  na `epic`).
- **Analisar no desenvolvimento (duplicidade/antigas):** a branch de padrão
  antigo `feature/1`, os pares `epicNN`×`featureNN` e a duplicata #46/#47.
- **Analisar/remover (órfãs arquivadas):** ~10 branches, aplicando a regra do
  cancelamento e verificando integração por outro caminho.
