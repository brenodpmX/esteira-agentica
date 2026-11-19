# Runbook — Telemetria OpenTelemetry (OTLP)

Guia do operador para ligar a telemetria da esteira e levá-la a uma ferramenta
de dashboard compatível com OpenTelemetry (Grafana, Datadog, Elastic, New Relic,
OpenObserve e outras). A esteira publica eventos crus, métricas de estado e
traces no padrão **OTLP**. Dashboard, coletor e armazenamento ficam fora da
esteira.

## Princípio: monitorar é secundário

- **Perda de telemetria é aceitável; atraso no processamento das tasks não é.**
- Os sinais ficam numa fila **só em memória** (até 2048 itens por sinal). Com a
  fila cheia, o excedente é descartado. Não há arquivo de reserva nem reenvio.
- Cada exportação tem teto de **2 s**, roda em segundo plano e é agendada a cada
  **5 s** (métricas: a cada 60 s, ou `OTEL_METRIC_EXPORT_INTERVAL` em ms).
- Nenhum erro da telemetria chega ao processamento. Coletor fora do ar gera no
  máximo **um aviso no log a cada 10 minutos** (`event=telemetria_export_falha`).
- No encerramento (SIGTERM), a esteira tenta enviar o que está na fila por no
  máximo **2 s** e encerra.

## Ligar e desligar

A configuração usa só as variáveis padrão `OTEL_*`, no `.env` lido pelo compose.
Não existe chave nova no `pipe.yml`.

| Variável | Efeito |
|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Liga a telemetria. Sem ela, nada é enviado. Padrão recomendado: `http://esteira-otlp:4318` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` (padrão, porta `4318`) ou `grpc` (porta `4317`) |
| `OTEL_SDK_DISABLED=true` | Desliga a telemetria mesmo com o endpoint definido |
| `OTEL_EXPORTER_OTLP_HEADERS` | Cabeçalhos do exportador (ex.: autenticação do coletor). Nunca são registrados no log |
| `OTEL_RESOURCE_ATTRIBUTES` | Atributos extras de recurso; aceita `service.instance.id` e `esteira.pipe.nome` |
| `OTEL_METRIC_EXPORT_INTERVAL` | Intervalo de exportação das métricas, em ms (padrão 60000) |
| `PIPE_ENVIRONMENT` | Vira `deployment.environment.name` |
| `ESTEIRA_TELEMETRIA_TITULO=true` | Inclui o título da issue (`esteira.issue.titulo`). Sem ela, o título nunca sai |

Sem endpoint (ou com `OTEL_SDK_DISABLED=true`) a telemetria é no-op: nenhuma
conexão é aberta, o SDK de exportação nem é carregado e a saída de terminal é a
mesma de antes.

Com a telemetria ligada, o startup registra uma linha `[Telemetria]` com
`service.instance.id`, `esteira.pipe.nome` e o endpoint. O endpoint aparece sem
usuário, senha e query string.

## Rede do coletor (`compose.telemetria.yml`)

O coletor roda fora da esteira, numa rede Docker externa chamada
`esteira-telemetria`, onde ele responde pelo nome `esteira-otlp`. O serviço
`pipe` compartilha a rede do serviço `dind`, então é o `dind` que entra na rede
do coletor:

```bash
docker network create esteira-telemetria   # uma vez, pelo dono do coletor
docker compose -f docker-compose.yml -f compose.telemetria.yml up -d
```

O compose base continua funcionando sem o override e sem a rede.

Para conferir o que chega, um OTel Collector com o exportador `debug` na mesma
rede, com alias `esteira-otlp`, mostra cada evento, métrica e span recebido.

## Contrato de telemetria v1

Todo sinal leva os atributos de recurso abaixo.

| Atributo | Valor |
|---|---|
| `service.name` | `esteira-agentica` |
| `service.version` | versão da esteira |
| `service.instance.id` | `OTEL_RESOURCE_ATTRIBUTES`; padrão: URL do repositório de trabalho, sem credencial |
| `esteira.pipe.nome` | `OTEL_RESOURCE_ATTRIBUTES`; padrão: nome do repositório |
| `deployment.environment.name` | `PIPE_ENVIRONMENT`; **ausente** quando a variável não existe (OTel não aceita atributo nulo, então "nulo" é representado pela ausência) |
| `esteira.contrato` | `1` (texto) |

Duas pipes ligadas ao mesmo coletor se distinguem por `service.instance.id`.

### Eventos

Cada evento é um log record OTel com `event.name` (no campo de evento e também
como atributo). Os atributos de contexto são `esteira.board.plataforma`,
`esteira.board`, `esteira.coluna`, `esteira.issue` e `esteira.issue.pai`.

| `event.name` | Quando |
|---|---|
| `esteira.agente.execucao` | fim de toda execução de agente, qualquer desfecho |
| `esteira.agente.admissao_negada` | execução não despachada (`cooldown`, `limite_consumo`, `circuit_break`, `composicao_recusada`) |
| `esteira.agente.circuit_break` | trip do limitador e cada passo da sinalização (`persisted`, `labeled`, `signaled`) |
| `esteira.consumo.limite` | `bloqueio`, `retomada`, `unidade_divergente`, `virada_periodo` (`esteira.consumo.tipo`) |
| `esteira.sync.item` | fim do processamento de cada item da fila (`aplicado`, `reenfileirado`, `dead_letter`) |
| `esteira.board.api` | cada chamada ao provider do board (`ok`, `erro`, `rate_limit`) |
| `esteira.board.throttle` | mudança do throttle (`aumento`, `cooldown`) |
| `esteira.board.penalty` | ativação e desativação do penalty |
| `esteira.sync.circuit_breaker` | transição de estado do breaker (escopo `plataforma` ou `issue`) |
| `esteira.sync.escalacao` | escalação de erro de sync ao agente |
| `esteira.issue.upsert` | sync aplicado (`origem=incremental`) e snapshot completo diário (`origem=full_sync`) |
| `esteira.issue.transicao` | issue mudou de coluna (`esteira.coluna.de`, `esteira.coluna.para`) |
| `esteira.pipe.ciclo` | fim de cada volta do loop |
| `esteira.pipe.ciclo_vida` | `startup` e `shutdown`, com `vcs.ref.head.revision` |
| `esteira.pipe.incidente` | fatos anormais (`esteira.incidente.tipo`) |

Regras de leitura:

- Atributo sem valor conhecido não é enviado. Exemplos: `esteira.consumo.valor`
  só existe com consumo disponível; `esteira.composicao.tokens_entrada` só existe
  quando o adapter do agente mede tokens (o kiro-cli não mede);
  `esteira.execucao.origem` só existe quando houve canal estruturado de falha.
- Listas (`esteira.issue.filhos`, `.bloqueada_por`, `.bloqueia`, `.labels`) são
  sempre enviadas, mesmo vazias.
- `esteira.execucao.inicio` e `.fim` são datas ISO 8601 com fuso.
- `esteira.ciclo.duracao_s` é o tempo de trabalho da volta, **sem** o tempo
  dormido, que vem em `esteira.ciclo.dormiu_s`.
- O snapshot completo (`origem=full_sync`) é enviado no startup e na primeira
  volta de cada novo dia.
- Em `esteira.consumo.limite`, `retomada` usa o período que bloqueou;
  `unidade_divergente` gera um evento por período configurado.
- `esteira.pipe.incidente` usa os tipos `instance_lock_recusado`,
  `preflight_falha`, `steering_reescrito`, `snapshot_restaurado`,
  `arquivo_fantasma` (arquivo com prefixo numérico indevido renomeado),
  `cross_board_bloqueado` e `registro_execucao_falha`.
- A esteira não reenvia execuções agrupadas. Quem consome correlaciona
  `esteira.agente.execucao` com o último `esteira.issue.upsert` pelo par
  (`service.instance.id`, `esteira.issue`).

### Métricas

Gauges observáveis, lidos do estado em memória ou dos arquivos de `.pipe/`.
O id da issue **nunca** é atributo de métrica.

| Métrica | Unidade | Atributos |
|---|---|---|
| `esteira.board.throttle` | `s` | `esteira.board.plataforma` |
| `esteira.board.penalty` | `h` | `esteira.board.plataforma` (`0` inativo) |
| `esteira.sync.circuit_breaker.estado` | `1` | `esteira.board.plataforma` (`0` closed, `1` half_open, `2` open) |
| `esteira.sync.circuit_breaker.issues_abertas` | `{issue}` | `esteira.board.plataforma` |
| `esteira.consumo.acumulado` | `{consumo}` | `esteira.ia.plataforma`, `esteira.consumo.periodo`, `esteira.consumo.unidade` |
| `esteira.consumo.limite` | `{consumo}` | idem; ausente quando não há limite |
| `esteira.consumo.bloqueado` | `1` | `esteira.ia.plataforma` |
| `esteira.sync.fila.profundidade` | `{item}` | `esteira.board`, `esteira.sync.evento` |
| `esteira.sync.fila.idade_maxima` | `s` | `esteira.board` |
| `esteira.sync.dead_letter.total` | `{item}` | `esteira.sync.dead_letter.categoria` |
| `esteira.sync.orfaos.total` | `{arquivo}` | `esteira.board` |

A unidade nativa do consumo (ex.: `credit`) vai no atributo
`esteira.consumo.unidade`, porque a unidade de um instrumento OTel é fixa.

### Traces

| Span | Quando |
|---|---|
| `invoke_agent {gen_ai.agent.name}` | cada execução; `gen_ai.operation.name=invoke_agent` e os atributos de `esteira.agente.execucao` |
| `esteira.sync.item {esteira.sync.evento}` | cada item da fila |
| `esteira.board.api {operacao}` | filho do span de item |

Todo evento emitido dentro de um span leva o `trace_id`/`span_id` dele. Span com
erro recebe status `ERROR` e `error.type`, sem a mensagem da exceção.

**Versão das convenções GenAI:** os nomes `gen_ai.*` seguem as convenções
semânticas do OpenTelemetry **v1.44.0** (status *development*), as mesmas do
pacote `opentelemetry-semantic-conventions` 0.66b2 instalado com o SDK 1.45.2.
O schema `https://opentelemetry.io/schemas/1.44.0` vai junto em cada sinal.

## Dados que nunca saem

Prompt, conversa, body, comentários, conteúdo de arquivos, tokens e
credenciais, URL com usuário e senha, e mensagem de erro bruta. A mensagem de
erro (`esteira.erro.mensagem`) passa sempre pela mesma sanitização do
dead-letter. O título da issue só sai com `ESTEIRA_TELEMETRIA_TITULO=true`.

## Diagnóstico rápido

| Sintoma | O que verificar |
|---|---|
| Nada chega ao coletor | `OTEL_EXPORTER_OTLP_ENDPOINT` no `.env`, linha `[Telemetria]` no startup, rede `esteira-telemetria` criada e override aplicado |
| Aviso `falha ao exportar telemetria` no log | Coletor parado ou inacessível. O processamento segue normal; os sinais do período são descartados |
| `telemetria desativada - falha ao inicializar` | Pacotes OTel ausentes na imagem; reconstrua a imagem |
| Porta errada | `http/protobuf` usa `4318`; `grpc` usa `4317` |
