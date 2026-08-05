# User Story #74 — Remoção segura do resíduo já integrado

Status: requisitos concluídos
Owner: product / requisitos
Epic: #73 — Branches não mergeadas
Last updated: 2026-07-24

## História

**Como** operador da esteira,
**quero** remover as branches cujo trabalho já foi comprovadamente integrado
(à linha principal `main` ou à branch base do épico `epic`),
**para** eliminar o resíduo óbvio da lista de branches sem qualquer risco de
perder trabalho vivo.

## Contexto

Esta é a fatia de **menor risco e maior retorno imediato** da faxina iniciada
no épico #73. São branches cujo conteúdo já está publicado: o trabalho existe
na linha principal ou já foi absorvido pela branch do épico que o originou.
Manter essas branches só polui a lista e mascara o que ainda está vivo.

Aplica-se diretamente a **regra de negócio 3** (apetite de risco, confirmada
com o usuário em #73): a remoção sem merge é permitida quando a branch já foi
integrada à branch pai/épico que originou a issue. Aqui a integração é fato
consumado — não há decisão de negócio pendente nem necessidade de análise de
código.

## Escopo — 12 branches a remover

### Integradas em `main`

A confirmação usa `git log --oneline origin/<branch> ^origin/main` — saída
vazia significa que todos os commits da branch já estão em `main`.

| Branch | Issue | Evidência de integração |
|--------|-------|------------------------|
| `feature7-7-incidente_issue_fantasma_correcao_2_contextmd_gerado_no_startup_a_partir_do_pipeyml` | #7 | Absorvida via `hotfix5` → PR #43 mergeado em `main` (commit `1ed917e`). Commit `e4d2233` ("Merge correções 2, 3 e 5 (feature7)") presente no log de `main`. Commits exclusivos fora de `main`: **0**. |
| `hotfix5-5-incidente_issue_fantasma` | #5 | Mergeada diretamente em `main` via PR #43 (commit `1ed917e` — "Merge pull request #43"). Commits exclusivos fora de `main`: **0**. |

### Integradas em `epic`

A confirmação usa `git merge-base --is-ancestor origin/<branch> origin/epic` —
resultado positivo significa que o tip da branch é ancestral de `origin/epic`.

| Branch | Issue | PR de integração (commit em `epic`) |
|--------|-------|--------------------------------------|
| `feature28-28-refatoracao_persistir_agent_level_via_label_agent_level_nivel_no_github` | #28 | PR #29 (commit `bacea2e`) |
| `feature33-33-ajustar_copy_das_mensagens_de_erro_de_ssh_para_contexto_docker` | #33 | PR #55 (commit `71bc5a7`) |
| `feature34-34-implementar_funcao_preflight_de_verificacao_de_credenciais_no_arranque` | #34 | PR #56 (commit `1ef0f59`) |
| `feature35-35-integrar_preflight_ao_fluxo_de_boot_da_esteira` | #35 | PR #57 (commit `6019f62`) |
| `feature37-37-criar_docker_composeyml_com_servico_volumes_secret_e_envs` | #37 | PR #63 (commit `1393318`) |
| `feature40-40-criar_dockerfile_com_pythonunbuffered1_e_usuario_nao_root_ac_04ac_05_da_us_01_e_us_05` | #40 | PR #52 (commit `30490ed`) |
| `feature41-41-criar_docker_composeyml_com_credenciais_volumes_e_restart_unless_stopped_us_03_ac_03_da_us_05` | #41 | PR #64 (commit `fb13442`) |
| `feature42-42-validar_e_finalizar_o_runbook_de_operacao_docker_us_06_21_rf_08` | #42 | PR #65 (commit `d9311fa`) |
| `feature44-44-levantar_e_fixar_versoes_exatas_das_dependencias_da_imagem_docker` | #44 | PR #59 (commit `a0a1ae6`) |
| `feature45-45-criar_dockerfile_da_esteira_us_01` | #45 | PR #60 (commit `64252b4`) |

> **Observação sobre pares `epicNN`×`featureNN`:** issues #33, #34, #35, #40,
> #44, #45 têm tanto uma branch `featureNN` (listada acima, já integrada em
> `epic`) quanto uma branch `epicNN` pendente. A `featureNN` integrada entra
> nesta story; a decisão sobre a `epicNN` correspondente é da story de
> duplicidade/nomenclatura antiga (#76).

## Regra de decisão aplicada

> Remoção sem merge é permitida quando a branch já foi integrada à branch do
> épico/pai que originou a issue.

Fonte: regras de negócio do épico #73, confirmadas com o usuário
(ver `doc/product/branchs-nao-mergeadas/vision.md`, regra 3).

## Procedimento de verificação (pré-condição obrigatória para cada remoção)

```bash
# Para branches esperadas em main:
git log --oneline origin/<branch> ^origin/main
# Saída vazia = integrada → seguro remover

# Para branches esperadas em epic:
git merge-base --is-ancestor origin/<branch> origin/epic && echo "INTEGRADA" || echo "NÃO INTEGRADA"
```

Se qualquer verificação revelar commits exclusivos não antecipados, a branch é
**retirada desta story** e encaminhada para análise — não se remove sem
confirmação.

## Critérios de aceite

1. Antes de remover cada branch, confirmar com evidência (`git log` / `git
   merge-base`) que não há commit exclusivo fora do destino de integração
   (`main` ou `epic`).
2. As 12 branches listadas são removidas do repositório remoto
   (`git push origin --delete <branch>`).
3. Nenhuma branch de tarefa ativa (#73, #1, #70) é tocada; `main` e `epic`
   permanecem intactas.
4. Se alguma branch revelar commit não integrado (inesperado), ela é excluída
   desta story e registrada separadamente para análise — **não se remove sem
   confirmação**.
5. Ao final, nenhuma das 12 branches listadas existe no remoto.

## Fora de escopo

- Branches órfãs de tarefas arquivadas (→ story #75).
- Duplicidade e nomenclatura antiga, incluindo os pares `epicNN`×`featureNN`
  (→ story #76).
- Qualquer alteração de conteúdo, código ou configuração.
- Alteração de issues no board além do encerramento natural desta story.

## Referências

- Épico e regras de negócio: `doc/product/branchs-nao-mergeadas/vision.md`
- Inventário completo: `doc/product/branchs-nao-mergeadas/panorama-branches.md` (seção 3)
