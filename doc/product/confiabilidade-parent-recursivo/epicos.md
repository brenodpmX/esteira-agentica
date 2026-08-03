# Épicos — Confiabilidade após o incidente Parent Recursivo

Status: draft
Owner: requirements
Last updated: 2026-08-03

## Inputs
- Issue #104 — Post Mortem do incidente reportado em 01/08/2026
- `doc/product/confiabilidade-parent-recursivo/problem-space.md`
- `doc/product/confiabilidade-parent-recursivo/vision.md`
- `doc/product/confiabilidade-parent-recursivo/post-mortem.md`
- `doc/incidente/parent-recursivo/ticket.md`
- Tasks C1–C5 no board `task` (backlog), derivadas do incidente #97

## Critério de decomposição

Cada épico abaixo corresponde a uma das cinco frentes acordadas em
`vision.md` e mapeia diretamente para a correção técnica já dimensionada no
ticket do incidente #97 (colunas "Task" referenciam os arquivos de task já
criados no board `task`). A ordem de entrega segue a sequência acordada:
**1 → 2 → 3 → 4 → 5**.

## Épico 1: Validação de relações antes do board

**Objetivo:** rejeitar relações logicamente impossíveis (uma issue como pai,
filha, bloqueadora ou bloqueada por ela mesma) antes de qualquer chamada à API
do board.
**Escopo:**
- Validação de auto-referência em `parent`, `children`, `blocked_by` e
  `blocks` na camada de domínio (`src/core/board.py`).
- Descarte apenas da referência inválida, preservando as demais referências
  válidas do mesmo comando.
- Log de warning identificando a issue e o comando descartado.
**Fora de escopo:**
- Tratamento do erro HTTP retornado pela API em relações inválidas que já
  tenham sido enviadas (isso pertence ao Épico 2).
**Task correspondente:** C2 — `validar_auto_referencia_em_relacoes_parentchildrenblocked_byblocks-body.md`.

## Épico 2: Contenção de falhas definitivas e fim da repetição ilimitada

**Objetivo:** impedir que um item com falha definitiva ou recorrente
monopolize o processamento de todos os boards.
**Escopo:**
- Classificação de erros como definitivos (descarte imediato) ou
  transitórios (nova tentativa).
- Contador de tentativas por item da fila e mecanismo de dead-letter ao
  atingir o limite.
- Garantia de que a falha de um item não impede o processamento dos demais
  itens elegíveis na mesma fila.
**Fora de escopo:**
- A validação de auto-referência propriamente dita (pré-requisito, Épico 1).
- A causa raiz do dado inválido que chega à fila (isso pertence ao Épico 3).
**Task correspondente:** C3 — `erro_definitivo_nao_reenfileira_contador_de_tentativas_e_dead_letter_na_fila-body.md`.

## Épico 3: Associação segura entre artefato e issue

**Objetivo:** impedir que um artefato ambíguo ou órfão seja tratado como o
conteúdo de uma issue existente.
**Escopo:**
- Resolução do arquivo de body de uma issue sem aceitar às cegas o primeiro
  resultado de um fallback por prefixo numérico.
- Recusa de sincronização (com log e sinalização) quando não houver match
  confiável entre arquivo e issue.
- Reporte visível de arquivos órfãos com prefixo numérico que não
  correspondem a nenhuma issue conhecida, em vez de ignorá-los silenciosamente.
**Fora de escopo:**
- Reparo do estado de dados já corrompido no incidente concreto (já executado
  como ação operacional, fora desta entrega).
**Task correspondente:** C1 — `fallback_seguro_na_resolucao_do_body_da_issue_e_reporte_de_arquivos_orfaos-body.md`.

## Épico 4: Proteção da memória operacional

**Objetivo:** impedir que uma execução de agente produza alteração
persistente na memória interna da esteira (snapshot por board, no escopo
inicial).
**Escopo:**
- Verificação de integridade do `snapshot.json` de cada board antes e depois
  da execução do agente.
- Restauração automática do conteúdo original quando uma alteração indevida
  for detectada, com log identificando board, issue e agente envolvidos.
**Fora de escopo:**
- Impedir a leitura/escrita a nível de sistema operacional (sandboxing de
  processo) — o mecanismo é detecção e restauração pós-execução, não
  prevenção por permissão de arquivo.
- Extensão da mesma proteção a `changeQueue.json`/`throttle*.json` (pode ser
  aplicada com o mesmo padrão em entrega futura, mas não é critério de aceite
  desta frente).
**Task correspondente:** C4 — `verificacao_de_integridade_do_snapshot_na_execucao_do_agente-body.md`.

## Épico 5: Exclusividade de instância

**Objetivo:** impedir que duas instâncias da esteira operem simultaneamente
sobre o mesmo estado (`.pipe/`).
**Escopo:**
- Lock de instância única baseado em arquivo (`.pipe/pipe.lock`), verificado
  no `startup()`.
- Recusa de inicialização com mensagem clara quando outra instância com
  processo vivo já detém o lock.
- Liberação do lock ao encerrar normalmente e tratamento de lock órfão
  (processo referenciado não existe mais) permitindo nova inicialização.
**Fora de escopo:**
- Coordenação distribuída entre múltiplas máquinas/hosts — o lock é local ao
  diretório de estado, não um mecanismo distribuído.
**Task correspondente:** C5 — `lock_de_instancia_unica_da_esteira-body.md`.

## Rastreabilidade

| Épico | Regra de negócio relacionada (vision.md) | Task técnica |
|---|---|---|
| 1 | RN02 | C2 |
| 2 | RN03, RN04, RN05 | C3 |
| 3 | RN01 | C1 |
| 4 | RN06, RN08 | C4 |
| 5 | RN07 | C5 |

RN09 (mitigação do caso concreto não equivale à resolução definitiva) é
transversal aos cinco épicos: o incidente só pode ser encerrado após a
homologação integral das cinco frentes, não apenas de parte delas.
