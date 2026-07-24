# User Story — Limpeza de branches órfãs de tarefas arquivadas

Status: draft
Owner: product
Epic: #73 "Branches não mergeadas"
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

## Escopo — branches a verificar/remover (evidência: `panorama-branches.md`, seção 5)

| Branch | Issue | Estado no board |
|--------|-------|-----------------|
| `epic16-16-empacotar_a_esteira_em_imagem_docker` | #16 | Arquivada |
| `epic17-17-autenticar_dependencias_externas...` | #17 | Arquivada |
| `epic18-18-configurar_a_esteira_via_docker_compose...` | #18 | Arquivada |
| `epic19-19-persistir_estado_de_runtime...` | #19 | Arquivada |
| `epic20-20-operar_de_forma_autonoma...` | #20 | Arquivada |
| `epic21-21-documentar_a_operacao_em_docker` | #21 | Arquivada |
| `epic36-36-bump_de_versao_minor...preflight...` | #36 | Arquivada |
| `hotfix23-23-avaliacao_de_complexidade_falhando` | #23 | Arquivada |
| `hotfix24-24-issues_criadas_em_dois_boards...` | #24 | Arquivada |
| `hotfix27-27-log_nao_descritivo` | #27 | Arquivada |

Total: **~10 branches**.

> Nota: as issues #16–#21 são sub-issues do épico #1 ("Rodar no Docker",
> atualmente ativo em Homologação). Verificar se o trabalho de cada uma já foi
> absorvido pela branch `epic1`/`epic` antes de remover a órfã.

## Critérios de aceite

1. Para cada branch, registrar a razão da decisão:
   - **cancelada** (passou por "Cancelado") → remover sem merge; **ou**
   - **absorvida por outro caminho** (trabalho já em `epic`/`main`/outra branch)
     → remover como resíduo; **ou**
   - **dúvida sobre conteúdo vivo** → NÃO remover; encaminhar para análise de
     código (etapa de desenvolvimento).
2. As branches confirmadas como resíduo/canceladas são removidas do remoto.
3. Nenhuma branch de tarefa ativa é tocada.
4. Decisões que dependem de inspeção de código ficam explicitamente registradas
   para a etapa de desenvolvimento (não se economiza em análise).

## Fora de escopo

- Resíduo já comprovadamente integrado (story própria).
- Duplicidade e nomenclatura antiga (story própria).
- Reabrir/desarquivar issues ou alterar seu conteúdo.
