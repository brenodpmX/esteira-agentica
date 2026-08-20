# Requisitos Não-Funcionais — Confiabilidade após o incidente Parent Recursivo

Status: aprovado e validado na versão 1.10.0
Owner: requirements
Last updated: 2026-08-20

> Os requisitos abaixo permanecem como critérios de regressão. A entrega
> conjunta C1–C5 foi homologada em 20/08/2026; os resultados e limitações da
> rodada estão registrados no change file do épico #104.

## Inputs
- `doc/product/confiabilidade-parent-recursivo/vision.md`
- `doc/product/confiabilidade-parent-recursivo/post-mortem.md`
- `doc/incidente/parent-recursivo/ticket.md`
- Tasks C1–C5 no board `task`

Este documento explicita atributos de qualidade mensuráveis derivados das
métricas de sucesso já definidas em `vision.md`, para uso como critério de
validação por arquitetura e QA. Não redefine escopo funcional — apenas
detalha "quão bem" cada garantia deve se comportar.

## Disponibilidade / Continuidade

- Uma falha localizada em um único item (issue, board ou execução de agente)
  não pode reduzir a disponibilidade de processamento dos demais itens
  elegíveis, em nenhum board — 100% dos itens elegíveis não afetados devem
  continuar avançando no mesmo ciclo em que a falha ocorre.
- Não deve existir head-of-line blocking: a fila de sincronização não pode
  ficar bloqueada indefinidamente pelo mesmo item na cabeça — um item que
  atinge o limite de tentativas ou é classificado como erro definitivo deve
  ser removido da fila ativa no mesmo ciclo em que essa condição é detectada.
- Uma rejeição definitiva não pode gerar mais de N tentativas antes de ser
  isolada, onde N é o limite configurável de tentativas (ver Task C3). No
  incidente #97, o mesmo erro se repetiu 225 vezes em 2h37 sem isolamento —
  este é o cenário de regressão de referência a não reproduzir.
- Reinicialização legítima (ex.: restart de container em ambiente Docker) não
  pode ser impedida pelo mecanismo de exclusividade de instância quando a
  instância anterior já terminou (lock órfão deve permitir nova
  inicialização sem intervenção manual).

## Integridade

- Zero ocorrências de substituição de conteúdo (título, body, labels) de uma
  issue pelo conteúdo de outro artefato, nos cenários de regressão e após a
  liberação — esta é a métrica de integridade mais crítica herdada de
  `vision.md` e a que motivou a task C1.
- A resolução de arquivo de body para uma issue deve ser determinística: dado
  o mesmo conjunto de arquivos e o mesmo snapshot, o resultado (arquivo
  escolhido, ou recusa por ambiguidade) deve ser sempre o mesmo — sem
  dependência de ordem de iteração do sistema de arquivos.
- A verificação de integridade do `snapshot.json` (Task C4) deve comparar o
  conteúdo completo antes/depois da execução do agente, não apenas metadados
  (timestamp, tamanho) — alterações que preservem timestamp/tamanho mas
  alterem conteúdo devem ser detectadas.

## Desempenho

- A verificação de integridade do snapshot (hash antes/depois da execução do
  agente) não deve introduzir overhead perceptível no ciclo de execução —
  o cálculo de hash de um arquivo de snapshot (tipicamente pequeno, na ordem
  de KB) deve ser da ordem de milissegundos, não de segundos.
- A verificação de lock de instância única no `startup()` deve ser O(1) em
  relação ao tamanho do estado (não deve escanear todo o `.pipe/` para
  determinar se há outra instância ativa).
- O custo adicional de validação de auto-referência (Épico 1) e classificação
  de erro definitivo/transitório (Épico 2) deve ser desprezível frente ao
  custo de rede já existente (chamadas ao board) — a validação ocorre antes
  de qualquer chamada de rede, portanto não adiciona latência de I/O.

## Escalabilidade

- O contador de tentativas e o mecanismo de dead-letter (Task C3) devem
  suportar múltiplos itens em dead-letter simultaneamente, em boards
  diferentes, sem que o crescimento da lista de dead-letter degrade o tempo
  de processamento dos itens ativos da fila.
- O isolamento de falha por item (RN-004) deve continuar válido
  independentemente do número de boards configurados no `pipe.yml` — a
  garantia de que "falha de um item não afeta os demais" não pode depender
  do número total de boards ou do tamanho da fila.

## Segurança / Integridade de estado

- Nenhuma execução de agente deve conseguir produzir alteração persistente
  nos arquivos listados em `PROTECTED_PATHS` (a começar pelo `snapshot.json`
  por board, conforme escopo da Task C4) — toda alteração detectada é
  revertida antes do próximo ciclo de sync.
- O lock de instância única (Task C5) deve identificar de forma confiável se
  o processo referenciado ainda está ativo (verificação de PID vivo), para
  evitar tanto falso positivo (bloquear inicialização legítima por lock
  órfão) quanto falso negativo (permitir duas instâncias simultâneas por não
  detectar processo vivo).
- Toda alteração de estado protegido detectada e revertida deve ser
  auditável — presente em log com timestamp, board/issue/agente envolvidos —
  sem exigir que o operador leia diretamente `snapshot.json` ou
  `changeQueue.json` para entender o que ocorreu (consistente com RN-005 e
  RN-008).

## Observabilidade

- Todo evento de isolamento (auto-referência descartada, item em
  dead-letter, arquivo órfão sinalizado, alteração de snapshot revertida,
  inicialização concorrente recusada) deve gerar uma entrada de log
  identificável por board, issue (quando aplicável) e motivo — sem exigir
  correlação manual entre múltiplos arquivos de log para reconstruir o que
  aconteceu.
- A distinção entre "processo ativo" e "processamento saudável" (levantada em
  `post-mortem.md` como uma das lacunas do incidente) deve ser observável:
  deve ser possível, a partir dos logs, diferenciar um ciclo em que houve
  avanço de trabalho de um ciclo em que a esteira apenas repetiu a mesma
  falha sem produzir avanço.

## Critérios de teste de regressão (cenários do incidente #97)

Os cinco épicos devem ser validados, em conjunto, contra a reprodução do
cenário do incidente #97 (ver `doc/incidente/parent-recursivo/ticket.md`,
seção "Causa raiz"): um arquivo órfão com prefixo numérico coincidente,
resolvido pelo fallback de `_find_issue_files`, contendo um comando `/parent`
que aponta para a própria issue. Nesse cenário reproduzido:

- nenhuma issue deve ter conteúdo substituído (Épico 3);
- a relação de auto-referência deve ser rejeitada antes de qualquer chamada
  ao board (Épico 1);
- caso algum erro ainda chegue à fila, ele não deve se repetir indefinidamente
  nem bloquear outros boards (Épico 2);
- nenhuma alteração deve persistir em `snapshot.json` fora do controle do
  núcleo (Épico 4); e
- o cenário deve ser reproduzido com apenas uma instância ativa, validando
  que o lock não interfere no fluxo normal de execução única (Épico 5).
