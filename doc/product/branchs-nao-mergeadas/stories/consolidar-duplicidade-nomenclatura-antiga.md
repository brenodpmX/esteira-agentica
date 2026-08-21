# User Story — Consolidação de duplicidade e nomenclatura antiga

Status: draft
Owner: product
Epic: #73 "Branches não mergeadas"
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

## Escopo — branches a analisar (evidência: `panorama-branches.md`, seção 4)

1. **Nomenclatura antiga (padrão com barra):**
   - `feature/1-1-rodar_no_docker` — padrão antigo da issue #1, que hoje convive
     com a branch atual `epic1-1-rodar_no_docker`. Decidir se há algo não
     absorvido na branch antiga antes de abandoná-la.

2. **Pares `epicNN` × `featureNN` (mesma issue, duas branches):**
   - Issues **#33, #34, #35, #40, #44, #45** têm branch de épico **e** de feature,
     sendo a `featureNN` já integrada na `epic`. Verificar se a `epicNN`
     correspondente ainda carrega algo não absorvido; se não, é duplicata a
     remover.

3. **Issues duplicadas #46 / #47:**
   - `epic46` e `epic47` — issues **#46 e #47 têm título idêntico** ("Adicionar
     volumes de estado no docker-compose.yml"), ambas abertas. Consolidar em uma
     única versão e remover a duplicata.

## Critérios de aceite

1. Para `feature/1`: decisão registrada (integrar o que for útil na branch atual
   `epic1` **ou** abandonar), com justificativa baseada no que foi inspecionado.
2. Para cada par `epicNN`×`featureNN`: confirmado se a `epicNN` tem conteúdo não
   absorvido; consolidada uma única branch por issue, removida a redundante.
3. Para #46/#47: definida a issue/branch canônica, consolidado o conteúdo e
   removida a duplicata (incluindo alinhamento da duplicidade da issue no board).
4. Ao final, não há mais de uma branch representando a mesma tarefa nem branch de
   padrão antigo sem dono.
5. Nenhuma decisão de remoção sem merge ocorre sem a análise de código que a
   fundamente.

## Fora de escopo

- Resíduo já integrado de forma inequívoca (story própria).
- Branches órfãs de tarefas arquivadas sem questão de duplicidade (story própria).
- Alterar o processo/fluxo da esteira ou o conteúdo funcional das entregas além do
  necessário para consolidar as branches.
