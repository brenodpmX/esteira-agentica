# Runbook — Limitador de reexecuções de agente por contexto (#306)

Guia do operador para o **limitador de reexecuções** (`agent_circuit_break`): o
que ele faz, como configurar, como reagir a um bloqueio e — ponto crítico — como
ele se **distingue do cooldown** (`boards.rerun_cooldown`).

## O que o limitador faz

A esteira entrega cada issue elegível a um agente. Uma issue que permanece no
mesmo board e coluna após a execução volta a ser elegível e pode ser reexecutada
indefinidamente — inclusive quando cada execução termina com sucesso técnico sem
que a issue avance. Isso queima capacidade de agente e quota/tokens sem
progresso.

O limitador **conta toda execução entregue ao agente** por contexto
`(board, coluna, issue)`, no instante da entrega (independe do resultado). Quando
o operador configura uma **política opcional** de limite por janela de tempo, a
esteira **impede a execução excedente antes de ela começar**, marca a issue com
`need_human`, publica nela um comentário acionável e **zera a contagem** daquele
contexto — de modo que a remoção de `need_human` conceda uma **nova franquia
completa**.

- **Opt-in:** sem a política configurada, nada é bloqueado e o comportamento
  atual é integralmente preservado (a contagem interna continua ocorrendo).
- **Isolamento:** uma issue bloqueada **não trava a fila** — as demais issues
  elegíveis seguem sendo processadas.
- **Mudança de coluna reinicia:** mover a issue de coluna é contexto novo, sem
  herança — a contagem recomeça do zero.
- **Persistente:** o estado de contagem e de bloqueio sobrevive a reinício do
  processo (ao contrário do cooldown, que é por processo).

## Cooldown × Limitador — a diferença (leia antes de configurar)

São **dois mecanismos distintos e complementares**. Confundir os dois leva a
configuração errada.

| Aspecto | **Cooldown** (`boards.rerun_cooldown`) | **Limitador** (`agent_circuit_break`) |
|---|---|---|
| O que faz | **Espaça** reexecuções: impõe um intervalo mínimo entre entregas da mesma issue no mesmo `(board, coluna)` | **Conta e contém**: impõe um **teto** de execuções por janela de tempo |
| Impõe teto? | **Não** — a issue pode ser reexecutada para sempre, só mais devagar | **Sim** — ao atingir `N` execuções em `T`, bloqueia a próxima |
| Efeito ao disparar | Pula a issue no ciclo; ela volta a ser elegível depois do intervalo | Marca `need_human`, comenta e exige intervenção humana para retomar |
| Persistência | **Por processo** (em memória): reiniciar a esteira libera tudo | **Persistente** em arquivo: reiniciar NÃO libera uma issue bloqueada |
| Escopo da config | Por board (`boards.<board>.rerun_cooldown`) | Único para a instância (raiz do `pipe.yml`) |
| Quando usar | Reduzir pressão de loop apertado sem parar o trabalho | Conter repetição patológica que não avança, pedindo olhar humano |

Resumo: **o cooldown desacelera; o limitador contém e pede ajuda.** Os dois podem
estar ativos ao mesmo tempo, sem interferência mútua.

## Como configurar

Bloco **opcional** na **raiz** do `pipe.yml` (fora do mapa `boards`):

```yaml
agent_circuit_break:
  executions: 5     # N: máximo de execuções permitidas no contexto
  window: 3600      # T: janela em segundos (3600 = 1h)
```

| Chave | Tipo | Regra |
|---|---|---|
| `agent_circuit_break` | objeto | Ausente = política **inativa**. Se presente, exige `executions` e `window` juntos; rejeita campos desconhecidos |
| `agent_circuit_break.executions` | inteiro | `>= 1`. É o limite `N`. Booleano não é aceito |
| `agent_circuit_break.window` | inteiro (segundos) | `>= 1`. É a janela `T`. Booleano não é aceito |

- **Não há default**: a ausência do bloco desativa apenas o bloqueio e a
  sinalização, **nunca** a contagem interna.
- A validação ocorre na **verificação de configuração**, antes de qualquer
  alteração de estado. Configuração parcial ou inválida **impede o início** da
  esteira com uma mensagem que cita o caminho completo do campo (ex.:
  `agent_circuit_break.window: deve ser inteiro >= 1 (segundos)`).

### Semântica da janela (bordas)

Contam **somente** as execuções com idade **estritamente menor que `T`**. Uma
ocorrência com idade **igual a `T`** já expira e não conta. Ex.: com `window:
3600`, uma execução de exatamente 3600 s atrás não pesa na decisão.

### Capacidade exigida do adaptador

Com a política **ativa**, o adaptador de board precisa saber **aplicar label**
(para marcar `need_human`). Um adaptador que não implemente isso faria a
sinalização parecer aplicada sem efeito — por isso a esteira **falha na
inicialização** nesse caso, citando a capacidade ausente. O adaptador GitHub
(padrão) atende ao requisito.

## O que acontece em um bloqueio

Quando um contexto atinge `N` execuções dentro de `T`, no ato do bloqueio a
esteira executa, **nesta ordem**:

1. persiste o evento de bloqueio e **esvazia** as ocorrências do contexto;
2. aplica a label `need_human` na issue;
3. publica **um** comentário acionável (só se ainda não houver um para o evento);
4. reconcilia a marcação; a execução segue negada até a sinalização estar
   completa.

O comentário contém, no mínimo: **motivo**, **issue**, **board**, **coluna**,
**limite `N`** e **janela `T`** — o suficiente para diagnosticar **sem abrir
estado interno**. Ele carrega um marcador técnico oculto
(`<!-- agent-circuit-break:<event_id> -->`) usado para **não duplicar** o
comentário em retomadas após queda.

> O bloqueio **não move** a issue de coluna. A parada é a label `need_human`; a
> retomada é a sua remoção.

## Como retomar uma issue bloqueada

1. Abra a issue marcada com `need_human` e leia o comentário do bloqueio.
2. Diagnostique e **corrija/redirecione** a causa (o agente não conseguia
   avançar, a tarefa estava ambígua, dependência externa, etc.).
3. **Remova a label `need_human`** (ou o comando `/need_human` do `-body.md`).
4. A issue volta a ser elegível com uma **franquia completa de `N` execuções** —
   sem bloqueio residual imediato da janela anterior.

## Observabilidade

Os eventos do limitador são emitidos no log diário da esteira
(`logs/<data>.json`), **sem** expor estado interno protegido:

| Evento | Nível | Significado |
|---|---|---|
| `agent_circuit_break_trip` | WARNING | Bloqueio acionado (board, issue, coluna, `N`, `T`, `event_id`) |
| `agent_circuit_break_signal_pending` | ERROR | Sinalização pendente (falha externa) — será retomada no ciclo seguinte |
| `agent_circuit_break_admission_error` | ERROR | Admissão negada por erro de integridade/persistência (fail-closed) |
| `agent_circuit_break_count_write_skipped` | WARNING | Contagem interna não persistida (política inativa, best-effort) |

O arquivo de estado (`.pipe/agentCircuitBreak.json`) é **estado interno
protegido**: não é editável por agente ou operador e seu conteúdo nunca aparece
em prompts, comentários ou logs. Ele contém apenas identificação de contexto,
timestamps das ocorrências e os parâmetros do evento de bloqueio — nunca corpo de
issue, prompt, conversa, token ou credencial.

## Limitações conhecidas

- A política é **única para a instância** nesta versão — sem limites diferentes
  por board, coluna ou agente.
- Sem política, as ocorrências do contexto ativo não são podadas por tempo; o
  crescimento é linear e termina em mudança de coluna, remoção da issue ou
  ativação da janela.
- Transições remotas de coluna que ocorram inteiramente entre duas leituras e
  deixem a issue na coluna original não são observáveis; a contagem pode não
  reiniciar nesses casos.
