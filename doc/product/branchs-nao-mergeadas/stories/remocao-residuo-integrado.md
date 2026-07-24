# User Story — Remoção segura do resíduo já integrado

Status: draft
Owner: product
Epic: #73 "Branches não mergeadas"
Last updated: 2026-07-24

## História

**Como** operador da esteira,
**quero** remover as branches cujo trabalho já foi comprovadamente integrado
(à linha principal `main` ou à branch base do épico `epic`),
**para** eliminar o resíduo óbvio da lista de branches sem qualquer risco de
perder trabalho vivo.

## Contexto

Esta é a fatia de **menor risco e maior retorno imediato** da faxina. São
branches cujo conteúdo já está publicado: o trabalho existe na linha principal
ou já foi absorvido pela branch do épico que o originou. Manter essas branches
só polui a lista e mascara o que ainda está vivo.

Aplica-se diretamente a **regra de negócio 3** (apetite de risco): a remoção sem
merge é permitida quando a branch já foi integrada à branch pai/épico que
originou a issue. Aqui a integração é fato consumado — não há decisão de negócio
pendente nem necessidade de análise de código.

## Escopo — branches a remover (evidência: `panorama-branches.md`, seção 3)

**Integradas na linha principal (`main`):**
- `feature7-7-...contextmd_gerado_no_startup...` (issue #7)
- `hotfix5-5-incidente_issue_fantasma` (issue #5)

**Integradas na branch do épico (`epic`):**
- `feature28-28-...persistir_agent_level...` (#28)
- `feature33-33-...copy_mensagens_de_erro_ssh...` (#33)
- `feature34-34-...preflight_verificacao_credenciais...` (#34)
- `feature35-35-...integrar_preflight...` (#35)
- `feature37-37-...docker_compose_servico_volumes...` (#37)
- `feature40-40-...dockerfile_pythonunbuffered...` (#40)
- `feature41-41-...docker_compose_credenciais...` (#41)
- `feature42-42-...runbook_operacao_docker...` (#42)
- `feature44-44-...fixar_versoes_dependencias...` (#44)
- `feature45-45-...dockerfile_da_esteira...` (#45)

Total: **12 branches**.

> Observação: os pares `epicNN`×`featureNN` (mesma issue com branch de épico e de
> feature) NÃO são tratados aqui — a `featureNN` integrada entra nesta lista, mas
> a decisão sobre a `epicNN` correspondente é da story de duplicidade/nomenclatura
> antiga.

## Critérios de aceite

1. Antes de cada remoção, confirmar (com evidência) que a branch está integrada
   na `main` ou na `epic` — nenhum commit exclusivo fora do destino.
2. As 12 branches acima são removidas do repositório remoto.
3. Nenhuma branch de tarefa **ativa** (#73, #1, #70) é tocada.
4. As branches base (`main`, `epic`) permanecem intactas.
5. Se, ao verificar, alguma branch revelar commit não integrado, ela é retirada
   desta story e encaminhada para análise (não se remove sem confirmação).

## Fora de escopo

- Branches órfãs de tarefas arquivadas (story própria).
- Duplicidade e nomenclatura antiga, incluindo os pares `epicNN`×`featureNN`
  (story própria).
- Qualquer alteração de conteúdo/código.
