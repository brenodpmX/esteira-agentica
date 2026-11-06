# Runbook — Limitador opcional de consumo de IA por plataforma (#311)

Guia do operador para o limitador de consumo (`agents.<plataforma>.limits`): o
que ele faz, como configurar, como diagnosticar um bloqueio e como ler os
registros.

## O que o limitador faz

Uma mesma conta de uma plataforma de IA pode ser usada por várias instâncias
da esteira, e uma mesma instância pode acionar mais de uma plataforma. Sem uma
cota independente por plataforma, um trabalho de menor prioridade pode
consumir a capacidade que se pretendia reservar para outro.

O limitador acumula o consumo reconhecido de cada plataforma, por instância e
por período (diário/semanal/mensal), usando como insumo o consumo por execução
já capturado pela issue #307 (`.pipe/executionRecords.json`). Antes de acionar
o agente de uma plataforma, verifica se o acumulado de **algum** período
configurado atingiu ou ultrapassou o limite; em caso afirmativo, **a próxima
tentativa é impedida antes do despacho**.

- **Opt-in:** sem o bloco `limits` sob a plataforma, nada é acumulado nem
  verificado — comportamento idêntico ao de antes da #311.
- **Sem teto absoluto:** como o consumo de uma execução só é conhecido ao fim
  dela, uma execução que começou abaixo do limite e o ultrapassa durante a
  execução **nunca é interrompida** — só a próxima tentativa é impedida.
- **Isolamento:** o bloqueio vale para a combinação **instância/plataforma**.
  Outras plataformas da mesma instância, e a mesma plataforma em outra
  instância, não são afetadas (cada instância tem o seu próprio `.pipe/`).
- **Persistente:** o acumulado sobrevive a ciclos ociosos e a reinícios do
  processo.

## Como configurar

Bloco **opcional** `limits`, sob `agents.<plataforma>` (chave irmã das
entradas de agente — não é confundido com um agente):

```yaml
agents:
  kiro-cli:
    dev:
      name: engineering
      model: claude-sonnet-5
    limits:
      timezone: America/Sao_Paulo   # opcional; ausente = fuso local da máquina
      daily:
        limit: 50000                # obrigatório se 'daily' presente
      weekly:
        limit: 300000               # obrigatório se 'weekly' presente
        reset_weekday: 0             # obrigatório se 'weekly' presente (0=segunda..6=domingo)
      monthly:
        limit: 1200000              # obrigatório se 'monthly' presente
        reset_day: 1                 # obrigatório se 'monthly' presente (1-28 ou "last")
```

| Chave | Tipo | Obrigatoriedade | Validação |
|---|---|---|---|
| `limits` | mapa | opcional | Ausente = plataforma sem controle. Campo desconhecido é rejeitado. |
| `limits.timezone` | string | opcional | Se presente, precisa ser identificador de fuso válido (ex.: `America/Sao_Paulo`). |
| `limits.daily.limit` | inteiro | obrigatório se `daily` presente | `>= 1`. |
| `limits.weekly.limit` | inteiro | obrigatório se `weekly` presente | `>= 1`. |
| `limits.weekly.reset_weekday` | inteiro | obrigatório se `weekly` presente | `0` (segunda) a `6` (domingo). |
| `limits.monthly.limit` | inteiro | obrigatório se `monthly` presente | `>= 1`. |
| `limits.monthly.reset_day` | inteiro ou `"last"` | obrigatório se `monthly` presente | `1`-`28` ou `"last"` (último dia do mês). |

- **Períodos combináveis:** diário, semanal e mensal podem ser configurados
  isolada ou conjuntamente; o bloqueio ocorre quando **qualquer um** deles
  atinge o limite, independentemente dos demais.
- **Unidade nativa:** cada plataforma comunica consumo na sua própria unidade
  (ex.: créditos no Kiro); não há conversão para moeda nem entre plataformas.
- **Validação na verificação de configuração:** limite `<= 0`, dia fora de
  faixa ou fuso inexistente impedem o início da esteira com `ConfigError`
  citando o caminho do campo (ex.: `agents.kiro-cli.limits.daily.limit: deve
  ser inteiro >= 1`), antes de qualquer alteração de estado.
- **Compatibilidade retroativa:** configuração existente sem `limits` carrega
  e opera sem erro e sem mudança de comportamento.

### Retomada sem reiniciar o processo

Diferentemente de outras validações do `pipe.yml` (lidas só no startup), o
bloco `limits` é **relido do arquivo em disco a cada avaliação** (com cache
por `mtime`). Isso significa que:

- **aumentar** ou **remover** um limite retoma o acionamento imediatamente,
  sem reiniciar a esteira;
- um bloco inválido editado em runtime **não** derruba a esteira — mantém a
  configuração válida carregada no startup e emite um aviso
  (`consumo_limite_config_runtime_invalida`), uma vez por versão do arquivo.

## O que acontece em um bloqueio

Quando o consumo acumulado de algum período atinge o limite, a próxima
tentativa de acionar aquela plataforma (em qualquer board/coluna/issue) é
impedida **antes** do despacho ao agente:

1. a issue correspondente continua elegível normalmente — ela não é marcada
   com `need_human` nem comentada; o impedimento é silencioso para a issue,
   visível apenas no log;
2. a seleção de tarefas (`keep_task`) também pula issues cuja plataforma está
   bloqueada, para não prendê-las na fila atrás de uma plataforma indisponível
   nem reselecioná-las em loop;
3. um aviso é emitido no terminal e no arquivo de log, e um registro
   estruturado `consumo_limite_bloqueio` é gravado com instância, plataforma,
   unidade, consumo do período, limite, período e a condição de retomada
   (data/hora do próximo reset **ou** aumento/desativação do limite — o que
   vier primeiro);
4. execuções de **outras** plataformas da mesma instância, e da mesma
   plataforma em **outras** instâncias, seguem normalmente.

> Quando mais de um período está estourado ao mesmo tempo, o registro informa
> a condição de retomada do período cujo reset é **mais tardio** — essa é a
> condição real para o acionamento voltar a ocorrer por reset.

## Como diagnosticar e retomar

1. No log (`logs/<data>.json`), procure `consumo_limite_bloqueio` com a
   plataforma afetada; o registro traz o período estourado, o consumo
   acumulado, o limite e a condição de retomada.
2. Decida entre esperar o reset automático do período ou agir imediatamente:
   - **aumentar** o limite (`limits.<periodo>.limit`) no `pipe.yml`; ou
   - **remover** o bloco do período (ou todo o `limits`) para desativar o
     controle daquela plataforma.
3. Qualquer uma das duas ações acima retoma o acionamento **sem reiniciar o
   processo** (ver "Retomada sem reiniciar o processo").
4. Para confirmar a retomada, procure `consumo_limite_retomada` no log — traz
   `tempo_bloqueado_seg`, útil para medir o impacto do bloqueio.

## Observabilidade

| Evento | Nível | Significado |
|---|---|---|
| `consumo_limite_bloqueio` | WARNING | Tentativa impedida antes do agente (instância, plataforma, unidade, consumo, limite, período, condição de retomada) |
| `consumo_indisponivel` | WARNING | Execução concluiu mas a plataforma não reportou consumo; acionamento **não** foi impedido (falha aberta) |
| `consumo_limite_acumulado` | TRACE | Consumo de uma execução somado ao acumulado do período |
| `consumo_limite_retomada` | INFO | Acionamento retomado após bloqueio (`tempo_bloqueado_seg`) |
| `consumo_limite_recuperacao` | WARNING | Estado do acumulado ausente/corrompido foi zerado com segurança (nunca bloqueia por falta de dado) |
| `consumo_limite_fuso_fallback` | WARNING | Fuso configurado indisponível em runtime; usado o fuso local da máquina |
| `consumo_limite_persistencia_falha` | ERROR | Falha ao persistir o acumulado; o consumo da execução não é perdido silenciosamente — fica registrado o valor e a unidade |
| `consumo_limite_unidade_divergente` | ERROR | Unidade reportada diverge da já acumulada para a plataforma; o valor não é somado |
| `consumo_limite_config_runtime_invalida` | WARNING | Bloco `limits` inválido editado em runtime; mantida a configuração do startup |

O arquivo de estado (`.pipe/consumptionLimit.json`) é **estado interno
protegido**: não é editável por agente ou operador e nunca aparece em
prompts, comentários ou logs. Contém apenas o acumulado por plataforma e
período (início do período corrente e consumo somado) — nunca corpo de issue,
prompt, conversa, token ou credencial.

## Falha aberta: o que fazer quando a plataforma para de reportar consumo

Se a plataforma deixar de reportar consumo (`consumo_indisponivel` repetido
para as execuções mais recentes), o limitador **não tem como conter** o
consumo real daquela plataforma enquanto isso persistir — o acionamento
continua normalmente por desenho (falha aberta), para não travar trabalho
legítimo por ausência de medição. Trate `consumo_indisponivel` recorrente como
um alerta de instrumentação a investigar no adapter da plataforma, não como um
bloqueio a destravar.

## Limitações conhecidas

- O controle **não é um teto absoluto**: como o consumo de uma execução só é
  conhecido ao fim dela, a última execução antes do bloqueio pode ultrapassar
  a cota configurada.
- Não há hoje uma segunda plataforma além do Kiro em operação; o contrato de
  consumo (`ExecutionResult.consumo`) já é genérico, e uma plataforma que não
  implemente a captura cai automaticamente em `consumo_indisponivel` (falha
  aberta, sem bloquear).
- As métricas do primeiro ciclo (excedente da última execução,
  indisponibilidade, bloqueios, falsos bloqueios, tempo de retomada e impacto
  em trabalho prioritário) ficam disponíveis via os eventos acima; a definição
  de quem afere o baseline e decide manter/ajustar/retirar o controle é
  decisão de quem implanta a esteira (fora do escopo desta entrega).
