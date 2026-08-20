# Regras de Negócio — Confiabilidade após o incidente Parent Recursivo

Status: aprovado e implementado na versão 1.10.0
Owner: requirements
Last updated: 2026-08-20

> As regras foram usadas como contrato para C1–C5 e tiveram seu gate final
> aprovado em 20/08/2026. A RN-010 foi satisfeita: as cinco frentes estão
> entregues e o incidente #97 está resolvido.

## Inputs
- `doc/product/confiabilidade-parent-recursivo/vision.md` (RN01–RN09)
- `doc/product/confiabilidade-parent-recursivo/epicos.md`
- `doc/incidente/parent-recursivo/ticket.md`
- Tasks C1–C5 no board `task`

Este documento refina, para uso de arquitetura/engenharia/QA, as regras de
negócio já aprovadas em `vision.md` (RN01–RN09). Não repete a redação de
negócio; adiciona contexto de aplicação, exceções e comportamento esperado nas
bordas de cada regra.

## RN-001 — Nenhuma relação de auto-referência é aceita

**Descrição:** uma issue nunca pode ser registrada como sua própria `parent`,
`children`, `blocked_by` ou `blocks`.
**Contexto:** aplica-se à validação de comandos do bloco `@---` no momento em
que são traduzidos em chamadas ao board (antes de qualquer chamada de rede).
**Exceções:** nenhuma. A regra vale para as quatro relações, isoladamente e em
combinação (uma issue pode se referenciar em mais de uma relação
simultaneamente; todas as ocorrências devem ser rejeitadas).
**Comportamento na borda:** quando a lista de uma relação contém a
auto-referência e também ids válidos (ex.: `/children #76, #10` no body da
própria issue `#76`), apenas a referência inválida é descartada; os ids
válidos continuam sendo processados normalmente. Rejeitar a lista inteira não
atende à regra de negócio de continuidade (RN03).
**Rastreamento:** referencia RN02 de `vision.md`. Task C2.

## RN-002 — Falha definitiva não é retentada

**Descrição:** um erro classificado como definitivo (não recuperável por nova
tentativa) é descartado do fluxo de sincronização imediatamente, sem
reenfileirar.
**Contexto:** aplica-se à aplicação de itens da fila de mudanças
(`change-up`/`delete-up`). Um erro é definitivo quando a mesma entrada,
reenviada sem alteração, produziria o mesmo resultado (ex.: issue inexistente,
relação logicamente impossível, erro 4xx de validação de domínio).
**Exceções:** erros transitórios (indisponibilidade momentânea, rate limit)
não são definitivos e seguem a regra de tentativas (RN-003).
**Comportamento na borda:** a classificação de um erro como definitivo não
pode depender de correspondência de texto na mensagem de erro de forma frágil
a ponto de um erro genuinamente transitório ser descartado por engano; a
classificação deve ser explícita por tipo/categoria de erro.
**Rastreamento:** referencia RN04 de `vision.md`. Task C3.

## RN-003 — Limite de tentativas com dead-letter

**Descrição:** um item da fila que falha repetidamente com erro não
classificado como definitivo tem um número máximo de tentativas; ao atingir o
limite, é retirado da fila ativa e registrado separadamente (dead-letter) em
vez de continuar sendo retentado.
**Contexto:** aplica-se a cada item individual da fila de sincronização,
independentemente do board a que pertence.
**Exceções:** erros já classificados como definitivos (RN-002) não consomem
tentativas — são descartados no primeiro ciclo em que ocorrem.
**Comportamento na borda:** o limite de tentativas é configurável, não
hardcoded, para permitir ajuste sem alteração de código. Um item em
dead-letter não deve impedir o processamento dos demais itens da fila no
mesmo ciclo (isolamento de falha).
**Rastreamento:** referencia RN03, RN04 e RN05 de `vision.md`. Task C3.

## RN-004 — Isolamento de falha por item

**Descrição:** a falha de processamento de um item (issue, board ou execução
de agente) não pode impedir o processamento de outros itens elegíveis, em
qualquer board.
**Contexto:** aplica-se tanto à fila de sincronização (um item malformado não
bloqueia os demais) quanto à seleção de tarefas (`keep_task`): uma issue
bloqueada, com `need_human` ou em dead-letter não impede o avanço de outras
issues elegíveis no mesmo board ou em outros boards.
**Exceções:** nenhuma. Esta é a regra que elimina o head-of-line blocking
observado no incidente #97 (fila única e global travada por um único item).
**Comportamento na borda:** a ordem de prioridade entre boards e colunas
(já definida no núcleo de seleção de tarefas) deve continuar sendo respeitada
para os itens não afetados — isolar a falha não significa alterar a ordem de
processamento dos itens saudáveis.
**Rastreamento:** referencia RN03 de `vision.md`. Task C3.

## RN-005 — Item isolado exige evidência e próximo passo

**Descrição:** todo item retirado do fluxo normal (dead-letter, associação
ambígua não resolvida, ou qualquer outra forma de isolamento) deve registrar
motivo, evidência suficiente para diagnóstico e indicação de que necessita
intervenção humana.
**Contexto:** aplica-se a qualquer mecanismo de isolamento introduzido pelos
Épicos 1 a 3 (auto-referência descartada, item em dead-letter, arquivo órfão
sem match confiável).
**Exceções:** nenhuma.
**Comportamento na borda:** a evidência e o motivo devem ser acessíveis ao
operador sem exigir leitura de arquivos internos protegidos (`snapshot.json`,
`changeQueue.json`) — devem estar em log e/ou sinalização visível na issue
(ex.: label, comentário), não apenas em estrutura de dados interna.
**Rastreamento:** referencia RN05 de `vision.md`. Tasks C1 e C3.

## RN-006 — Associação de artefato a issue exige match confiável

**Descrição:** um arquivo de body só é tratado como pertencente a uma issue
quando há confirmação inequívoca dessa pertinência; na ausência de match
confiável, nenhuma issue existente é alterada.
**Contexto:** aplica-se à resolução do arquivo de body de uma issue durante o
sync (`_find_issue_files`), incluindo o cenário em que o caminho registrado no
snapshot está obsoleto e um fallback por convenção de nome é necessário.
**Exceções:** quando o `body_path` registrado no snapshot ainda existe e é
válido, ele é a fonte de verdade — não há necessidade de fallback nem de
verificação adicional de match.
**Comportamento na borda:** havendo mais de um candidato possível no
fallback (ambiguidade), a regra é não escolher arbitrariamente o primeiro
resultado — a sincronização deve ser recusada e sinalizada, nunca aplicada
"no palpite".
**Rastreamento:** referencia RN01 de `vision.md`. Task C1.

## RN-007 — Arquivo órfão é sinalizado, nunca ignorado

**Descrição:** um arquivo local com prefixo numérico que não corresponde a
nenhuma issue conhecida no snapshot deve gerar sinalização visível (log de
warning/erro), nunca ser silenciosamente descartado da detecção de mudanças.
**Contexto:** aplica-se à detecção de mudanças locais (`detect_local_changes`
ou equivalente) durante o sync.
**Exceções:** arquivos sem prefixo numérico seguem o fluxo normal de criação
(`create-up`) e não se qualificam como órfãos.
**Comportamento na borda:** a sinalização não deve, por si só, criar ou
alterar issues — o objetivo é visibilidade para intervenção humana, não
resolução automática da ambiguidade.
**Rastreamento:** referencia RN01 de `vision.md`. Task C1.

## RN-008 — Memória operacional só é escrita pelo núcleo

**Descrição:** os arquivos de estado interno da esteira (a começar pelo
`snapshot.json` de cada board) só podem ser alterados pelo núcleo de
sincronização; qualquer alteração originada de uma execução de agente deve
ser detectada e revertida.
**Contexto:** aplica-se ao ciclo de execução de um agente (`call_agent`):
verificação de integridade antes e depois da execução.
**Exceções:** a lista de arquivos protegidos cobertos nesta primeira entrega
é o `snapshot.json` por board — `changeQueue.json` e `throttle*.json` seguem
protegidos apenas declarativamente (prompt/contexto) até uma entrega futura
que estenda a mesma verificação a eles.
**Comportamento na borda:** a detecção deve identificar claramente qual
board, issue e execução de agente produziram a alteração, e a reversão deve
restaurar o conteúdo exatamente como estava antes da execução — não uma
reconciliação parcial.
**Rastreamento:** referencia RN06 e RN08 de `vision.md`. Task C4.

## RN-009 — Uma única instância ativa por estado

**Descrição:** apenas uma instância da esteira pode operar sobre o mesmo
diretório de estado (`.pipe/`) a qualquer momento.
**Contexto:** aplica-se ao `startup()`, antes de qualquer leitura/escrita do
estado persistido.
**Exceções:** um lock cujo processo referenciado não está mais ativo (lock
órfão, por exemplo após um crash sem cleanup) não impede uma nova
inicialização — ela é permitida e o lock é substituído.
**Comportamento na borda:** a recusa de inicialização de uma segunda
instância não pode alterar ou apagar o estado da instância em execução (foi
exatamente essa falha — apagar a fila de mudanças — que ocorreu no incidente
#97 quando uma segunda instância iniciou).
**Rastreamento:** referencia RN07 de `vision.md`. Task C5.

## RN-010 — Mitigação não é resolução

**Descrição:** o reparo operacional de um caso concreto (ex.: a restauração
manual da issue #76) não altera a classificação de risco do incidente; o
incidente #97 só pode ser considerado resolvido após a homologação integral
dos cinco épicos.
**Contexto:** aplica-se à comunicação de status do incidente em qualquer
etapa do fluxo (aprovação de negócio, homologação, encerramento).
**Exceções:** nenhuma.
**Comportamento na borda:** a entrega parcial de um subconjunto dos cinco
épicos (por exemplo, apenas Épicos 1 e 2) reduz o risco de paralisação, mas
não permite declarar o incidente resolvido — a integridade (Épico 3) e a
proteção de estado/exclusividade (Épicos 4 e 5) continuam pendentes até serem
entregues e homologadas.
**Rastreamento:** referencia RN09 de `vision.md`. Transversal a C1–C5.
