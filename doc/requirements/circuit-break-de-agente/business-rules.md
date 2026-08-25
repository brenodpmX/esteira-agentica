# Regras de Negócio — Circuit-break de agente

Status: approved · Owner: requirements · Updated: 2026-08-24
Inputs: `doc/product/circuit-break-de-agente/analise-negocio.md` (RN01–RN09,
critérios de aceite de negócio 1–8), `doc/requirements/circuit-break-de-agente/glossary.md`

Este documento refina, para uso de UX/arquitetura/engenharia/QA, as regras já
aprovadas na análise de negócio. Não redefine escopo — adiciona contexto de
aplicação, exceções e comportamento de borda de cada regra.

## RN-001 — Toda execução iniciada conta

**Regra:** toda execução de agente iniciada é contada para efeito do limite,
independentemente de terminar com erro, sucesso, ou sucesso sem avanço de
coluna.
**Contexto:** aplica-se no instante em que a esteira decide entregar a issue
ao agente (mesmo ponto em que hoje `keep_task` marca o cooldown), antes de
saber o resultado da execução.
**Exceções:** nenhuma. Não há distinção entre causa de repetição (erro de
sincronização, entendimento do agente, bloqueio técnico) — o efeito observável
é contido, não a causa (decisão do dono, ver histórico de 22/08/2026).
**Fonte:** RN01 da análise de negócio; critério de aceite de negócio 2 e 3.

## RN-002 — Identidade do contexto é issue + board + coluna

**Regra:** a contagem é isolada por contexto, definido pela combinação
`(board, coluna, issue)`. Um contexto não compartilha nem herda contagem de
outro.
**Contexto:** aplica-se sempre que uma issue muda de coluna (manualmente no
board ou por auto-advance da esteira) — o contexto anterior fica congelado
(suas ocorrências não são reclassificadas) e o novo contexto começa com
contagem zero.
**Exceções:** nenhuma. A mesma issue, revisitando uma coluna por onde já
passou, inicia contagem nova nesse contexto (não retoma o histórico anterior
daquela combinação específica).
**Fonte:** RN02 da análise de negócio; critério de aceite de negócio 5.

## RN-003 — Somente ocorrências dentro da janela contam

**Regra:** apenas execuções cujo instante de início está dentro da janela `T`,
contada a partir do momento da avaliação, participam da decisão de bloqueio.
Ocorrências mais antigas que a janela deixam de contar.
**Contexto:** aplica-se a cada avaliação de elegibilidade de uma issue para
nova execução.
**Exceções:** nenhuma.
**Comportamento na borda:** uma ocorrência exatamente no limite da janela (
idade igual a `T`) é tratada como fora da janela (não conta), mantendo
simetria com a regra equivalente do cooldown existente (`_in_rerun_cooldown`
usa `>=` como limite de expiração).
**Fonte:** RN03 da análise de negócio; critério de aceite de negócio 4.

## RN-004 — Execução excedente não é iniciada

**Regra:** quando o contexto já possui `N` ou mais ocorrências dentro da
janela `T`, a próxima entrega ao agente para aquele contexto não ocorre.
**Contexto:** aplica-se na seleção de tarefas, antes da entrega ao agente —
mesmo ponto de decisão hoje ocupado pela checagem de cooldown em `keep_task`.
**Exceções:** nenhuma quando a política está configurada. Sem política
configurada, ver RN-007.
**Fonte:** RN04 da análise de negócio; critério de aceite de negócio 1.

## RN-005 — Bloqueio sinaliza `need_human` e motivo completo

**Regra:** todo bloqueio por limite marca a issue com `need_human` e registra
um comentário que identifica, no mínimo: motivo do bloqueio, issue, board,
coluna, limite (`N`) e janela (`T`).
**Contexto:** aplica-se no exato momento em que uma execução seria excedente
(RN-004) — o bloqueio e a sinalização são o mesmo evento, não passos
separados no tempo.
**Exceções:** nenhuma. A ausência de qualquer um dos dados mínimos no
comentário não satisfaz esta regra.
**Comportamento na borda:** a sinalização deve ser suficiente para o operador
diagnosticar sem acessar estado interno protegido (`snapshot.json`,
`changeQueue.json`) — consistente com a proteção de estado interno já vigente
na esteira.
**Fonte:** RN05 da análise de negócio; critério de aceite de negócio 2.

## RN-006 — Bloqueio reinicia a franquia do contexto

**Regra:** no instante em que o bloqueio é acionado, a contagem ativa daquele
contexto é zerada. Após o operador corrigir ou redirecionar a issue e remover
`need_human`, o contexto volta a ter uma franquia completa de `N` execuções
antes de um novo bloqueio.
**Contexto:** aplica-se ao mesmo contexto `(board, coluna, issue)` que sofreu
o bloqueio; não se aplica a um contexto diferente (ex.: a issue avançou de
coluna) — nesse caso a franquia já seria nova por força da RN-002.
**Exceções:** nenhuma decisão adicional do operador é exigida para conceder a
nova franquia — a remoção de `need_human` é suficiente e automática (decisão
do dono, 22/08/2026: "podemos zerar o contador no instante em que
bloqueamos").
**Comportamento na borda:** o reinício ocorre no momento do bloqueio, não no
momento da liberação — isso evita que a issue, ao ser liberada, já esteja
imediatamente sujeita a um novo bloqueio por ocorrências residuais da janela
anterior.
**Fonte:** RN06 da análise de negócio; critério de aceite de negócio 6.

## RN-007 — Controle é opt-in

**Regra:** sem política configurada (limite e janela), nenhuma issue é
bloqueada por este mecanismo, e o comportamento de execução vigente (incluindo
`boards.rerun_cooldown`, se configurado) é preservado.
**Contexto:** aplica-se à ausência de configuração da política de
circuit-break no `pipe.yml`.
**Exceções:** nenhuma. Não há valor padrão implícito quando a política está
ausente (decisão do dono, 22/08/2026: "melhor não definirmos um valor
padrão").
**Comportamento na borda:** a contagem de execuções continua ocorrendo
internamente mesmo sem política configurada (decisão do dono: "o contador
segue contando, só o bloqueio que não vai existir") — apenas o bloqueio e a
sinalização ficam inativos. Isso é relevante para permitir que a política seja
ativada posteriormente sem exigir reprocessamento retroativo de contagem.
**Fonte:** RN07 da análise de negócio; critério de aceite de negócio 7.

## RN-008 — Política é geral para a instância nesta versão

**Regra:** o limite `N` e a janela `T` são únicos para toda a instância da
esteira. Não há diferenciação por board, coluna ou agente nesta primeira
versão.
**Contexto:** aplica-se à leitura da configuração da política.
**Exceções:** nenhuma nesta versão. Diferenciação por board/coluna/agente é
explicitamente fora de escopo (decisão do dono: "nesta primeira versão, vamos
fazer geral, depois podemos evoluir").
**Fonte:** RN08 da análise de negócio.

## RN-009 — Bloqueio de uma issue não afeta outras

**Regra:** o bloqueio de um contexto por limite não impede o processamento de
nenhuma outra issue elegível, no mesmo board ou em outro.
**Contexto:** aplica-se à seleção de tarefas (`keep_task`) em todos os boards
configurados.
**Exceções:** nenhuma. Esta regra é consistente com o isolamento de falha já
estabelecido na esteira (ver RN-004 de
`doc/requirements/confiabilidade-parent-recursivo/business-rules.md`).
**Fonte:** RN09 da análise de negócio; critério de aceite de negócio 8.
