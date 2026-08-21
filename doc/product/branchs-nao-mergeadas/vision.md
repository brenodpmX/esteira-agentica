# Vision — Branches não mergeadas

Status: draft
Owner: product
Last updated: 2026-07-24

## Inputs
- Issue #73 "Branches não mergeadas"
- Respostas do usuário na entrevista (histórico da issue #73)
- Panorama real das branches (ver `panorama-branches.md`)
- `pipe.yml` (definição de fluxos, boards e colunas)

## Problema
O repositório acumulou mais de 30 branches além da linha principal, misturando
trabalho vivo, resíduo já entregue, branches órfãs de tarefas encerradas e
duplicidade de nomes. Não há forma segura e rápida de saber o que preservar e o
que descartar, e uma limpeza sem critério pode apagar trabalho legítimo.

## Solução
Uma **faxina pontual e segura** das branches, guiada por regras de negócio
claras. Cada branch é classificada pela sua situação e recebe o tratamento
correspondente:

- **Preservar** todo trabalho de tarefa ativa.
- **Remover com segurança** as branches cujo trabalho já foi integrado (à linha
  principal ou à branch do épico que o originou) — são resíduo puro.
- **Remover** as branches de tarefas que foram canceladas (deveriam ter sido
  apagadas no cancelamento e não foram) e as branches sem qualquer tarefa/razão
  que justifique sua existência.
- **Analisar caso a caso**, na etapa de desenvolvimento, as branches em
  duplicidade e de nomenclatura antiga, para decidir se o trabalho precisa ser
  integrado ou pode ser abandonado.

Não haverá mudança de processo nem automação nova: é uma limpeza do estado
atual, confirmada pelo usuário como suficiente.

## Regras de negócio confirmadas com o usuário

1. **Escopo — faxina pontual, não regra permanente.** Boa parte dessas branches
   nasceu da melhoria contínua do próprio código da esteira. Não é preciso mudar
   o código nem criar automação de encerramento; basta limpar o que existe hoje.

2. **Definição de "tarefa ativa".** Uma tarefa é ativa quando sua issue **já
   saiu do backlog e ainda não foi arquivada**. Tarefas ainda no backlog ou já
   arquivadas não são ativas.

3. **Apetite de risco para remoção (ação irreversível).** Só se pode remover uma
   branch **sem integrá-la (sem merge)** quando:
   - não houver nenhuma issue/razão que justifique sua existência; **ou**
   - ela já tiver sido integrada à branch do épico/tarefa-pai que originou a
     issue.

4. **Trabalho cancelado.** Conforme o fluxo definido no `pipe.yml`, uma issue que
   passou pela coluna **"Cancelado"** deveria ter tido sua branch removida sem
   merge. Essas branches são resíduo e devem ser removidas.

5. **Duplicidade e nomenclatura antiga.** A decisão de integrar ou abandonar
   essas branches **depende de análise do que foi feito no código**, não de uma
   decisão de negócio. Fica registrada como trabalho da etapa de desenvolvimento
   (não se economiza em análise: um padrão pode ser antigo e ainda assim conter
   código funcional).

6. **Bloqueio.** A issue #73 **bloqueia todas as issues ativas** até a resolução
   deste problema, para congelar o cenário durante a limpeza e evitar que novo
   trabalho vivo seja afetado.

## Público-alvo
Quem opera e evolui a esteira e precisa de uma visão limpa e confiável do estado
do repositório para trabalhar com segurança.

## Proposta de valor
Clareza e segurança: a lista de branches volta a refletir só o que está vivo,
sem risco de perder trabalho legítimo e sem o ruído que dava aparência de
projeto desorganizado.

## Critérios de sucesso
- Restam apenas branches de **tarefas ativas** (fora do backlog e não
  arquivadas) e as branches base do fluxo (`main`, `epic`).
- **Nenhum trabalho vivo é perdido.**
- Não há duplicidade de nomes nem branches de nomenclatura antiga sem dono.
- Toda remoção sem merge respeita as regras 3 e 4 (resíduo comprovado ou
  ausência de tarefa que a justifique).

## Fora de escopo
- Modificar conteúdo de entregas ou código de produto.
- Alterar o fluxo da esteira ou criar automação de encerramento de branch.
- Detalhar a mecânica técnica da limpeza.
- Criar user stories (etapa posterior).
