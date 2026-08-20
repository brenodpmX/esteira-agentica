# User Story — Limpeza de branches órfãs de tarefas arquivadas

Status: requisitos
Owner: product
Epic: #73 "Branches não mergeadas"
Issue: #75
Last updated: 2026-07-24

## História

**Como** operador da esteira,
**quero** tratar as branches órfãs de issues já arquivadas — verificando se a
tarefa foi cancelada ou se o trabalho foi absorvido por outro caminho —,
**para** removê-las com segurança conforme a regra de cancelamento, sem descartar
por engano trabalho que ainda tenha valor.

## Contexto

São branches de tarefas cuja issue **já foi arquivada** (encerrada no board), mas
cujo conteúdo não aparece integrado nem na `main` nem na `epic`. Como a esteira
prevê a remoção da branch ao cancelar uma tarefa (coluna "Cancelado" do fluxo) e
isso não chegou a rodar, sobraram órfãs.

Diferente do resíduo já integrado, aqui **há uma verificação a fazer** antes de
remover, porque a integração não é fato consumado:

- Aplica-se a **regra de negócio 4**: issue que passou por "Cancelado" deveria ter
  tido a branch removida sem merge → é resíduo, remover.
- Aplica-se também a **regra 3**: se o trabalho foi absorvido por outro caminho
  (outra branch/PR), a órfã é resíduo → remover.
- Atenção operacional: várias dessas issues continuam **abertas no GitHub** apesar
  de **arquivadas no board** — o critério que vale é o do board (arquivada = não
  ativa).

## Escopo — branches a verificar/remover

| Branch | Issue | Estado no board |
|--------|-------|-----------------|
| `epic16-16-empacotar_a_esteira_em_imagem_docker` | #16 | Arquivada (fechada no GitHub) |
| `epic17-17-autenticar_dependencias_externas_em_modo_headless` | #17 | Arquivada (fechada no GitHub) |
| `epic18-18-configurar_a_esteira_via_docker_compose_sem_rebuild` | #18 | Arquivada (aberta no GitHub) |
| `epic19-19-persistir_estado_de_runtime_entre_reinicios` | #19 | Arquivada (aberta no GitHub) |
| `epic20-20-operar_de_forma_autonoma_sem_intervencao_no_runtime` | #20 | Arquivada (fechada no GitHub) |
| `epic21-21-documentar_a_operacao_em_docker` | #21 | Arquivada (aberta no GitHub) |
| `epic36-36-bump_de_versao_minor_pela_adicao_do_preflight_de_credenciais` | #36 | Arquivada (aberta no GitHub) |
| `hotfix23-23-avaliacao_de_complexidade_falhando` | #23 | Arquivada (aberta no GitHub) |
| `hotfix24-24-issues_criadas_em_dois_boards_indevidamente` | #24 | Arquivada (aberta no GitHub) |
| `hotfix27-27-log_nao_descritivo` | #27 | Arquivada (fechada no GitHub) |

Total: **10 branches**.

> Nota: as issues #16–#21 são sub-issues do épico #1 ("Rodar no Docker",
> atualmente ativo em Homologação). O trabalho dessas issues foi refeito nas
> branches `feature/` e `epicNN` correspondentes, que já foram integradas à
> branch `epic`.

---

## Análise por branch (resultado dos requisitos)

### epic16–21: sub-issues do épico #1

Contexto comum a todas: essas issues foram as primeiras user stories criadas
para o épico #1. Representavam o design inicial (documentação, arquitetura,
UX). O trabalho foi **retrabalhado** a partir das tasks (`feature33` a
`feature47`), que substituíram o conteúdo com implementações concretas e já
foram integradas à branch `epic` via PRs mergeados.

Diagnóstico técnico: nenhum dos arquivos produzidos por essas branches existe
em `epic` nem em `main` — o trabalho foi feito em caminhos de documento
diferentes (`doc/arquitetura/`, `doc/arch/`, `doc/stories/`, etc.) que foram
deliberadamente **substituídos** pelas tasks posteriores (`doc/architecture/`,
`doc/runbook/`, `docker-compose.yml`, `Dockerfile`, etc.).

Conclusão: as branches #16–#21 contêm **exclusivamente documentação
intermediária de processo** (requisitos, arquitetura e UX de exploração) que
foi **substituída e superada** pelas entregas finais. Não há risco de perder
código funcional. A razão do arquivamento é que o trabalho foi absorvido e
refeito pelas tasks do épico.

| Branch | Decisão | Razão |
|--------|---------|-------|
| `epic16` (#16) | **Remover — absorvida** | Documentação de exploração substituída pelas tasks do épico. Arquivos em `doc/arquitetura/`, `doc/ux/` e `CHANGES/` inexistentes em `epic`/`main`. Issue #16 fechada no GitHub. |
| `epic17` (#17) | **Remover — absorvida** | Documentação de arquitetura e UX substituída pelas tasks. Arquivos em `doc/arch/`, `doc/stories/ux/` inexistentes em `epic`/`main`. Issue #17 fechada no GitHub. |
| `epic18` (#18) | **Remover — absorvida** | Documentação de orquestração docker-compose substituída pela `feature37`/`feature41` (já em `epic`). Arquivos em `doc/arquitetura/us-03*`, `doc/ux/us-03*` inexistentes em `epic`/`main`. |
| `epic19` (#19) | **Remover — absorvida** | Documentação de persistência de estado substituída pela implementação concreta (`epic46`/`epic47`). Arquivos em `doc/stories/arquitetura.md`, `doc/stories/change-file.md` inexistentes em `epic`/`main`. |
| `epic20` (#20) | **Remover — absorvida** | Documentação de operação autônoma substituída pela `feature35` (preflight). Arquivos em `doc/architecture/us05-*`, `doc/changelogs/us05-*` inexistentes em `epic`/`main`. Issue #20 fechada. |
| `epic21` (#21) | **Remover — absorvida** | Runbook de operação Docker refeito pela `feature42` (já em `epic`). Arquivo `doc/runbook/docker.md` da feature42 existe em `epic`; o `doc/changelogs/21-*` e UX de epic21 são resíduo. |

### epic36: bump de versão MINOR

Contexto: issue #36 foi criada para registrar o bump de versão semântica
consequente à adição do preflight de credenciais (#34). Contém apenas 1 commit:
`Requisitos: Bump de versão MINOR pela adição do preflight de credenciais`.

Diagnóstico técnico: os arquivos produzidos pela branch são documentação
intermediária de requisitos (`doc/arch/rodar-no-docker/us-02-autenticacao-headless.md`,
`doc/stories/rodar-no-docker/ux/error-copy-spec.md`, `doc/stories/rodar-no-docker/ux/terminal-prototypes.md`,
`doc/arch/rodar-no-docker/decisions/adr-04-preflight-credenciais.md`). Nenhum
desses arquivos existe em `epic` nem em `main`. O bump de versão efetivo foi
implementado via `src/core/version.py` na branch `epic` (que já contém o
código do preflight).

Decisão: **Remover — absorvida**. A task de implementação do preflight
(`feature34`/`feature35`) e o arquivo de versão já estão integrados em `epic`.
O que sobrou nesta branch é documentação de processo que não chegou a ser
aproveitada.

### hotfix23: avaliação de complexidade falhando

Contexto: issue #23 (aberta no GitHub, arquivada no board) registra o bug de
perda do `agent_level` no ciclo de sync down. A branch `hotfix23` contém apenas
documentação de incidente (`doc/incidente/avaliacao-complexidade-falhando/ticket.md`):
triagem, análise técnica e decisão de tratamento. **Sem código de correção.**

Diagnóstico técnico: a decisão de tratamento concluiu que o bug seria corrigido
por tarefa separada. O arquivo do ticket não existe em `epic` nem em `main`. A
correção do bug em si foi implementada em outra branch (ainda pendente ou não
identificada nesta análise).

Decisão: **Encaminhar para análise no desenvolvimento**. A branch contém apenas
um ticket de incidente com análise e decisão de tratamento. Duas perguntas
precisam ser respondidas pela etapa de desenvolvimento:
1. A correção do `agent_level` já foi implementada em outra branch/PR?
2. O ticket de incidente (`doc/incidente/avaliacao-complexidade-falhando/ticket.md`)
   deve ser integrado a `main` ou `epic` como histórico permanente?

Se a resposta a (2) for "sim", a branch deve receber merge antes de ser removida.
Se for "não", pode ser removida sem merge.

### hotfix24: issues criadas em dois boards indevidamente

Contexto: issue #24 (aberta no GitHub, arquivada no board) registra o incidente
de issues sendo criadas em dois boards simultaneamente. A branch `hotfix24`
contém apenas documentação de incidente (`doc/incidente/issues_criadas_em_dois_boards_indevidamente/ticket.md`):
triagem e decisão de tratamento. **Sem código de correção.**

Diagnóstico técnico: mesmo padrão do hotfix23 — é um ticket de análise e
decisão, sem implementação. O arquivo não existe em `epic` nem em `main`.

Decisão: **Encaminhar para análise no desenvolvimento**. Mesmas duas perguntas
do hotfix23:
1. A correção (isolamento de boards) já foi implementada em outra branch/PR?
2. O ticket de incidente deve ser preservado em `main`/`epic`?

### hotfix27: log não descritivo

Contexto: issue #27 (fechada no GitHub, arquivada no board). A branch `hotfix27`
contém triagem, decisão de tratamento e **código de correção** (3 commits,
incluindo `Execução de tratamento: Log não descritivo`).

Diagnóstico técnico: o código do hotfix27 (`src/__main__.py`, `src/adapters/kiro_cli_agent.py`,
`src/core/agent.py`) adiciona `col_name` e `title` ao log do agente. Esse
**mesmo código** foi implementado via `feature31-31-tornar_log_de_execucao_de_agente_descritivo_etapa_titulo`
e integrado à branch `epic` via PR #32. O `epic` **já contém** a implementação
equivalente. O diff de hotfix27 vs `epic` mostra apenas variações menores de
style (ex.: `.resolve()` no path).

Decisão: **Remover — absorvida**. O código funcional do hotfix27 foi absorvido
pela feature31 (PR #32, integrado ao `epic`). A branch hotfix27 é resíduo.

---

## Decisões consolidadas

| Branch | Issue | Decisão | Tipo |
|--------|-------|---------|------|
| `epic16` | #16 | ✅ Remover | Absorvida (trabalho refeito nas tasks do épico) |
| `epic17` | #17 | ✅ Remover | Absorvida (trabalho refeito nas tasks do épico) |
| `epic18` | #18 | ✅ Remover | Absorvida (trabalho refeito pelas features) |
| `epic19` | #19 | ✅ Remover | Absorvida (trabalho refeito pelas features) |
| `epic20` | #20 | ✅ Remover | Absorvida (trabalho refeito pelas features) |
| `epic21` | #21 | ✅ Remover | Absorvida (runbook refeito pela feature42 no epic) |
| `epic36` | #36 | ✅ Remover | Absorvida (bump e preflight integrados via feature34/35) |
| `hotfix23` | #23 | ⚠️ Analisar no desenvolvimento | Ticket sem código; decidir se preservar histórico |
| `hotfix24` | #24 | ⚠️ Analisar no desenvolvimento | Ticket sem código; decidir se preservar histórico |
| `hotfix27` | #27 | ✅ Remover | Absorvida (feature31 integrou código equivalente ao epic) |

**Resumo:**
- 8 branches com decisão de remoção confirmada
- 2 branches encaminhadas para análise no desenvolvimento (hotfix23 e hotfix24)

---

## Critérios de aceite

1. Para cada branch, registrar a razão da decisão (feito acima).
2. As 8 branches confirmadas como resíduo/absorvidas são removidas do remoto.
3. As branches hotfix23 e hotfix24 são encaminhadas à etapa de desenvolvimento
   com as perguntas documentadas acima.
4. Nenhuma branch de tarefa ativa é tocada.

## Fora de escopo

- Resíduo já comprovadamente integrado (story #74).
- Duplicidade e nomenclatura antiga (story própria).
- Reabrir/desarquivar issues ou alterar seu conteúdo.
- Decidir sobre a preservação dos tickets de incidente hotfix23/hotfix24
  (cabe à etapa de desenvolvimento).
