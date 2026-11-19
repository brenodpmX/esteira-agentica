# Casos de Teste — Envio telemetria

- **Issue:** #355
- **Story relacionada:** port de telemetria `TelemetryPort` + adapter OTel,
  Contrato de telemetria v1 (eventos, métricas, traces), `compose.telemetria.yml`,
  runbook, bump MINOR.
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA SR)
- **Data:** 2026-11-20
- **Branch:** `feature/355-envio_telemetria`

Status: draft
Owner: quality
Last updated: 2026-11-20

## Inputs

- Issue #355 (Contrato de telemetria v1, Requisitos não funcionais R1–R10,
  Critérios de aceitação CA-1 a CA-7).
- Suíte existente em `tests/` (varredura feita abaixo — **nenhum** teste de
  telemetria existe hoje; `grep -rl "telemetry\|opentelemetry\|OTEL" src/ tests/`
  não retorna nada).

> Todo caso abaixo é derivado de um Critério de Aceitação (CA) e/ou de uma
> linha do Contrato de telemetria v1 (tabela de eventos, métricas ou traces) ou
> de um Requisito não funcional (R1–R10). Resultado esperado explícito e
> verificável em todos. Os testes são da suíte Python do motor (pytest, em
> `tests/`), salvo os marcados **estático** (verificação de arquivo/config, sem
> executar o motor).

---

## Contexto de arquitetura (baseline do código atual)

Nada de telemetria existe hoje — `TelemetryPort`, o adapter OTel e todos os
pontos de emissão são **a construir**. Confirmei no código os pontos de
ancoragem citados nas Referências da issue:

- **Execução de agente** — `src/__main__.py::call_agent()` é o orquestrador
  único: resolve o agente/plataforma, chama `compose_execution_record()` (gate
  fail-closed de composição, `event="composicao_fail_closed"` já existe),
  `_consumption_allows()`, `_admit_circuit_break()`, mede `inicio`/`fim` em
  torno de `_dispatch_with_recovery()`, e finaliza com
  `_write_execution_record()` + `_record_consumption()`. É o ponto natural para
  o span `invoke_agent` (envolvendo ao menos o dispatch) e o evento
  `esteira.agente.execucao` (ao final, qualquer desfecho — mesmo padrão de
  `_write_execution_record`, que já é fail-safe e cobre todo desfecho).
  `compose_execution_record()` devolve `tokens_entrada` (pode ser `None`) e o
  texto do contexto sempre carregado, de onde vêm
  `esteira.composicao.tokens_entrada` e
  `esteira.composicao.caracteres_sempre_carregado` (via `len()`).
- **Admissão negada** — os três `return None`/`return False` antes do dispatch
  em `call_agent()`/`_consumption_allows()`/`_admit_circuit_break()` são os três
  motivos (`composicao_recusada` não está no enum do contrato de
  `esteira.admissao.motivo`, mas o fail-closed de composição também não
  despacha — ver nota de cobertura abaixo) e `cooldown`/`limite_consumo`/
  `circuit_break`.
- **Circuit break de agente** — `src/core/agent_circuit_break.py`: eventos de
  log já existentes `agent_circuit_break_trip` (linha 401) e
  `agent_circuit_break_signal_pending` (linha 440, com `passo` implícito nos
  três estágios da sinalização) são os fatos a espelhar em
  `esteira.agente.circuit_break` com `.passo` ∈ {`persisted`, `labeled`,
  `signaled`}.
- **Limite de consumo** — `src/core/consumption_limit.py`: constantes
  `EVENT_UNAVAILABLE`, `EVENT_UNIT_MISMATCH`, `EVENT_ACCUMULATED`,
  `EVENT_RESUMED`, `EVENT_PERSIST_ERROR`, `EVENT_TZ_FALLBACK` (greps linhas
  244–576) já cobrem bloqueio/retomada/unidade divergente/virada de período —
  são os fatos de `esteira.consumo.limite`. `instance_id(config, repo_id)`
  (linha 256) é o default de `service.instance.id` citado no contrato de
  recurso, já sanitizando userinfo da URL (`_URL_USERINFO`).
- **Fila de sincronismo e dead-letter** — `src/core/change_queue.py`
  (`ChangeItem`: `uuid`, `event`, `attempts`, `timestamp` de enfileiramento) e
  `src/core/dead_letter.py` (`DeadLetterEntry.category`,
  `sanitize_reason()` — **já existe** e é a função a reutilizar para
  `esteira.erro.mensagem sanitizada** e para o dado proibido "mensagem de erro
  sem `sanitize_reason`"). `src/core/sync.py::apply_changes()` (linha 1032) é
  onde cada item termina seu processamento (aplicado/reenfileirado/
  dead-letter) — ponto do evento `esteira.sync.item` e do span do mesmo nome.
- **Board GitHub** — `src/adapters/github_board.py`: `_throttle_hit()` (linha
  117) e `_penalty_hit()` (linha 90) são os pontos de `esteira.board.throttle`
  e `esteira.board.penalty`; toda chamada ao provider (ex.: `move_issue`) é
  candidata a `esteira.board.api` + span filho do item de sync.
- **Circuit breaker de sync** — `src/core/sync_circuit_breaker.py`: evento de
  log já existente `sync_circuit_breaker_transition` (linhas 239–287, com
  `escopo` plataforma/issue implícito nos argumentos) mapeia 1:1 para
  `esteira.sync.circuit_breaker`; `sync_circuit_breaker_escalation` (linha 408)
  para `esteira.sync.escalacao`.
- **Ciclo e ciclo de vida** — `src/__main__.py::main()` (loop `while True`,
  linha 174) e `startup()`/`_handle_sigterm` (shutdown, `_Shutdown`, já testado
  em `tests/test_sigterm_shutdown.py`) são os pontos de `esteira.pipe.ciclo` e
  `esteira.pipe.ciclo_vida`.
- **Issue upsert/transição** — `src/core/sync.py::_fire_column_events()`
  (linha 361) já dispara `on_in`/`on_out`; é o ponto natural de
  `esteira.issue.transicao`; `apply_changes()`/`sync_remote()` (criação, estado,
  arquivamento, full sync) para `esteira.issue.upsert`.
- **Versão** — `src/core/version.py::VERSION = "1.29.0"` (baseline desta
  entrega; o bump MINOR esperado é `1.30.0`).

> **Decisão de design NÃO fixada pela QA (é do desenvolvimento):** nome exato
> do módulo/classe do port (`src/core/telemetry.py`/`TelemetryPort` e
> `src/adapters/otel_telemetry.py` são os nomes dados pelo escopo — a QA os usa
> como alvo provável, mas testa **comportamento observável via API pública do
> port**, não a implementação interna do adapter), estratégia de
> instrumentação (decorator vs. chamada direta em cada ponto), formato interno
> de configuração lida de `OTEL_*`. O que a QA fixa é: a **assinatura
> observável** do contrato (nome dos eventos/métricas/spans e seus atributos),
> as regras de resiliência (R1–R5) e de dados proibidos, testáveis por fora —
> via exportador OTel em memória (ver Convenções) — sem depender de como o
> adapter é implementado por dentro.

### Nota de cobertura — "composição recusada" e `esteira.admissao.motivo`

O contrato lista `esteira.admissao.motivo` ∈ {`cooldown`, `limite_consumo`,
`circuit_break`, `composicao_recusada`} — os quatro valores já cobrem os quatro
pontos de `return`/`return None`/`return False` antes do dispatch em
`call_agent()` identificados acima (composição, consumo, circuit break, e
cooldown que é verificado em `keep_task`/`_in_rerun_cooldown` antes de a issue
chegar a `call_agent`). Não há lacuna: os quatro motivos têm ponto de código
confirmado. Este contrato está **completo e consistente** com a arquitetura
atual — não há necessidade de devolver a issue a `revisar-escopo`.

---

## Rastreabilidade (CA / Contrato → casos)

| CA / cláusula do contrato | Grupo | Caso(s) |
|---|---|---|
| CA-1 — evento `esteira.agente.execucao` + span `invoke_agent` completos | B | CT-EXEC-01, CT-EXEC-02, CT-TRACE-01 |
| CA-2 — cada fato da tabela de eventos emitido ≥1 vez, com atributos | C | CT-EVT-01..CT-EVT-14 |
| CA-3 — métricas periódicas com atributos corretos, sem id de issue | D | CT-MET-01..CT-MET-11, CT-MET-CARD |
| CA-4 — coletor parado/inacessível não trava o loop, ciclo ≤5% de variação | E | CT-RES-01..CT-RES-05 |
| CA-5 — sem `OTEL_EXPORTER_OTLP_ENDPOINT`/`OTEL_SDK_DISABLED=true` ⇒ no-op, zero conexão | F | CT-NOOP-01..CT-NOOP-04 |
| CA-6 — `service.instance.id` distingue pipes em eventos/métricas/traces | G | CT-RES-ATTR-01..04, CT-DIST-01 |
| CA-7 — suíte completa passa, bump MINOR, runbook e CONTEXT.md atualizados | H | CT-VER-01..CT-VER-04 |
| R9 — core não importa `opentelemetry` | A | CT-ARCH-01, CT-ARCH-02 |
| Traces (tabela própria) — spans e relação pai/filho | B/J | CT-TRACE-01..CT-TRACE-03 |
| Dados proibidos (cláusula própria) | I | CT-PRIV-01..CT-PRIV-05 |
| R6/R7/R8 — infraestrutura (Dockerfile, compose, startup log) | K | CT-INFRA-01..CT-INFRA-04 |

> **Observação de cobertura geral:** os 7 CAs e as cláusulas normativas do
> Contrato de telemetria v1 mapeiam de forma limpa sobre pontos de código já
> existentes (ver seção anterior) — sem lacuna ou contradição que exija devolver
> ao planejamento. Decido com os critérios de aceitação e a arquitetura atual.

---

## Convenções para o desenvolvimento (todos os casos automatizados)

- **Sem rede real, sempre:** nenhum teste depende de um OTel Collector de
  verdade. Usar os exportadores/leitores **em memória** do próprio
  `opentelemetry-sdk` (dependência já exigida por R6 — `pip install
  opentelemetry-sdk` + exporters, pinados no `Dockerfile`):
  - traces: `InMemorySpanExporter` (`opentelemetry.sdk.trace.export`);
  - métricas: `InMemoryMetricReader` (`opentelemetry.sdk.metrics.export`) ou
    equivalente leitor síncrono que force a coleta das observable gauges sem
    esperar o `schedule_delay`;
  - logs/eventos: um `LogRecordProcessor`/exporter em memória equivalente do
    SDK de logs (`opentelemetry.sdk._logs.export`) **ou**, se a versão pinada
    não o expuser, um processor fake mínimo que implementa `emit`/`on_emit` e
    guarda os `LogRecord` recebidos — desde que não seja o próprio código sob
    teste (nunca mockar o `TelemetryPort`/adapter que está sendo validado,
    só o transporte OTel abaixo dele).
  - Esses três coletores em memória são injetados no `TracerProvider`/
    `MeterProvider`/`LoggerProvider` configurados pelo adapter sob teste — o
    teste nunca abre uma porta real nem depende de rede.
- **Isolamento de ambiente:** fixture `autouse` que limpa todas as `OTEL_*` e
  `PIPE_ENVIRONMENT`/`ESTEIRA_TELEMETRIA_TITULO` do `os.environ` antes de cada
  teste e restaura depois (`monkeypatch.delenv`/`monkeypatch.setenv`). Nenhum
  teste depende de variável de ambiente deixada por outro.
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` por teste (mesmo
  padrão já usado em `tests/test_rerun_cooldown.py` etc.), para que `.pipe/` e
  `logs/` fiquem isolados. Qualquer provider/estado global do SDK OTel
  (ex.: provider já setado por um teste anterior) precisa ser resetado entre
  testes — o SDK não permite múltiplas chamadas de `set_tracer_provider` sem
  aviso; usar a API de reset de teste do próprio SDK ou reconstruir o adapter
  a cada teste, nunca reaproveitar provider global entre casos.
- **Relógio e `BoardPort` fake controláveis:** reaproveitar os fakes já usados
  em `tests/test_rerun_cooldown.py`, `tests/test_sync_optimization.py` e
  `tests/test_agent_circuit_break.py` para provocar os fatos de sync/board sem
  rede. Dispatch do agente sempre via espião (nunca aciona `kiro-cli` real).
- **Nunca** mockar o próprio símbolo sob teste (lição do incidente #106): o que
  é substituído é o transporte (coletor em memória), o relógio e os fakes de
  porta — a emissão real do evento/métrica/span é exercitada de verdade.
- **Verificação por atributo, não por posição:** ao inspecionar um `LogRecord`/
  `Span`/ponto de métrica, buscar o evento pelo nome (`event.name` / nome do
  span / nome da métrica) dentre todos os capturados, nunca assumir índice
  fixo — vários sinais podem ser emitidos na mesma execução.
- **Nenhum teste de telemetria pode ficar flaky por fila assíncrona:** usar
  `SimpleSpanProcessor`/leitor síncrono (ou `force_flush()` do provider) nos
  testes de contrato, para obter o sinal imediatamente. Os testes de fila
  assíncrona/descarte (R2) são os únicos que exercitam o `BatchProcessor` real
  com fila cheia — ver Grupo E.

---

## Grupo A — Arquitetura hexagonal (R9)

### CT-ARCH-01 — Nenhum módulo de `src/core/` importa `opentelemetry`

- **Tipo:** estático
- **Arquivo/alvo:** `tests/test_telemetry_architecture.py` (novo)
- **Critério de aceitação:** R9.
- **Passos:**
  1. Varrer todos os arquivos `.py` de `src/core/` (`ast.parse` ou regex de
     `import`/`from`) procurando por `opentelemetry`.
- **Resultado esperado:** zero ocorrências em `src/core/`. Toda referência a
  `opentelemetry` fica restrita a `src/adapters/` (e a própria biblioteca,
  fora do repo). `src/core/telemetry.py` (o port) define apenas tipos/
  protocolo próprios (ex.: `Protocol`/ABC com métodos `emit_event`,
  `record_metric`, `start_span` ou equivalente) — sem importar o SDK.
- **Observações:** mesmo padrão arquitetural de `BoardPort`/`AgentPort`
  existentes (core só conhece a porta).

### CT-ARCH-02 — Core funciona com `TelemetryPort` no-op por default

- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_telemetry_architecture.py`
- **Pré-condição:** nenhum adapter OTel configurado/injetado.
- **Passos:**
  1. Instanciar/usar o `TelemetryPort` default (ou chamar os pontos de
     instrumentação de `src/core/`/`src/__main__.py` sem injetar nenhum
     adapter real).
- **Resultado esperado:** nenhuma exceção; o comportamento de negócio
  (execução, sync, consumo) é idêntico ao atual sem telemetria — nenhum
  `event=`/log existente é removido ou alterado por esta entrega (regressão).
- **Observações:** fecha o requisito "core só conhece a porta" com um teste de
  uso real (não apenas estático).

---

## Grupo B — Execução de agente: evento + span completos (CA-1)

### CT-EXEC-01 — `esteira.agente.execucao` emitido com todos os atributos do contrato

- **Tipo:** integração (motor + adapter OTel com exportador em memória)
- **Arquivo/alvo:** `tests/test_telemetry_contract.py` (novo)
- **Pré-condição:** adapter OTel configurado com `LoggerProvider` cujo
  processor é o coletor em memória; `BoardPort` fake; dispatch espião
  devolvendo um `ExecutionResult` de sucesso com consumo disponível
  (`Consumo(valor=..., unidade=..., disponivel=True, origem=...)`).
- **Passos:**
  1. Chamar `call_agent(config, task)` com a issue/coluna/board conhecidos.
  2. Coletar o(s) `LogRecord` emitidos com `event.name == "esteira.agente.execucao"`.
- **Resultado esperado:** exatamente um record com `event.name` igual, contendo
  **todos** os atributos próprios listados na linha correspondente do
  contrato: `esteira.execucao.id`, `esteira.ia.plataforma`,
  `gen_ai.agent.id`, `gen_ai.agent.name`, `gen_ai.request.model`, board,
  coluna, issue, issue.pai, `esteira.coluna.destino`,
  `esteira.execucao.resultado` ∈ taxonomia fechada de
  `execution_record.RESULTADOS`, `esteira.execucao.avancou`,
  `esteira.execucao.repeticao_sem_avanco`, `esteira.execucao.classe`,
  `esteira.execucao.origem`, `esteira.execucao.tentativas`,
  `esteira.execucao.sessao` ∈ {`nova`, `retomada`},
  `esteira.execucao.inicio`, `esteira.execucao.fim`,
  `esteira.execucao.duracao_s` (≈ `fim - inicio`), `esteira.execucao.timeout_s`,
  `esteira.consumo.disponivel`, `esteira.consumo.valor` (presente porque
  disponível), `esteira.consumo.unidade`, `esteira.consumo.origem`,
  `esteira.composicao.tokens_entrada`,
  `esteira.composicao.caracteres_sempre_carregado`. Mais os atributos de
  contexto (`esteira.board.plataforma`, `esteira.board`, `esteira.coluna`,
  `esteira.issue`, `esteira.issue.pai`) e de recurso (ver Grupo G). Nenhum
  atributo da lista está ausente ou com nome diferente do contrato.
- **Observações:** cobre CA-1 (parte do evento) e é o caso-mestre de
  correlação de atributos — serve de modelo para CT-EVT-01.

### CT-EXEC-02 — `esteira.consumo.valor` ausente quando consumo indisponível

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_contract.py`
- **Pré-condição:** mesma de CT-EXEC-01, mas dispatch devolve consumo
  indisponível (`Consumo.indisponivel(origem=...)`).
- **Passos:**
  1. Chamar `call_agent` e coletar o evento de execução.
- **Resultado esperado:** `esteira.consumo.disponivel=False`;
  `esteira.consumo.valor` **ausente** do conjunto de atributos (não `0`, não
  `null` como valor presente — a regra do contrato é "só se disponível");
  `esteira.consumo.unidade`/`.origem` presentes conforme proveniência.
- **Observações:** fecha a regra "nunca inventar valor de consumo quando
  indisponível" (RN-04/RN-05 de #307, já testado para `execution_record`;
  aqui é a mesma regra aplicada ao sinal de telemetria).

### CT-EXEC-03 — Título da issue só com opt-in `ESTEIRA_TELEMETRIA_TITULO=true`

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_contract.py`
- **Pré-condição:** duas execuções idênticas, uma com
  `ESTEIRA_TELEMETRIA_TITULO` ausente/`false`, outra com `=true`.
- **Passos:**
  1. Rodar `call_agent` nos dois ambientes e inspecionar
     `esteira.issue.titulo` no evento de execução (e em qualquer outro evento
     que carregue atributos de contexto).
- **Resultado esperado:** sem a variável (ou `false`),
  `esteira.issue.titulo` está **ausente** de todos os sinais; com
  `=true`, está presente com o título real da issue.
- **Observações:** cobre a cláusula "Dados proibidos" sobre o título —
  ligação direta com Grupo I (CT-PRIV-05).

---

## Grupo C — Contrato de eventos: cada fato emitido ao menos uma vez (CA-2)

> Um caso por linha da tabela de eventos do contrato (exceto
> `esteira.agente.execucao`, já cobrindo em CT-EXEC-01/02/03). Todos no mesmo
> arquivo `tests/test_telemetry_contract.py`, cada um provocando o fato real
> (sem injetar o evento diretamente) e verificando `event.name` + atributos
> próprios + atributos de contexto aplicáveis.

| Caso | `event.name` | Como provocar o fato | Atributos próprios mínimos a verificar |
|---|---|---|---|
| CT-EVT-01 | `esteira.agente.admissao_negada` | Forçar cada um dos 4 motivos (cooldown ativo, limite de consumo atingido, circuit break no limite, composição com `instrucoes_obrigatorias_carregadas=False`) em 4 sub-casos parametrizados | `esteira.admissao.motivo` correto por sub-caso; `esteira.consumo.periodo` presente **apenas** no sub-caso `limite_consumo` |
| CT-EVT-02 | `esteira.agente.circuit_break` | Provocar `trip` do limitador (`CircuitBreaker.admit` no limite) e, em sub-caso, cada estágio da sinalização | `esteira.circuit_break.contagem`, `.limite`, `.janela_s`, `.passo` nos três valores (`persisted`, `labeled`, `signaled`) ao longo da sequência |
| CT-EVT-03 | `esteira.consumo.limite` | 4 sub-casos: bloqueio por limite, retomada, unidade divergente (`EVENT_UNIT_MISMATCH`), virada de período | `esteira.consumo.periodo` ∈ {`diario`,`semanal`,`mensal`}, `.tipo`, `.acumulado`, `.limite`, `.unidade`, `.periodo_inicio`, `.periodo_fim` |
| CT-EVT-04 | `esteira.sync.item` | Processar um item em cada desfecho (`aplicado`, `reenfileirado` por erro transitório, `dead_letter` por erro definitivo) via `apply_changes` | `esteira.sync.uuid`, `.evento` (um dos 6 valores do enum), `.fullsync`, board, issue, `.tentativa`, `.desfecho`, `.dead_letter.categoria` só no sub-caso dead-letter, `.lag_s` ≥0, `.duracao_s` ≥0; `error.type`/`esteira.erro.mensagem` só nos desfechos com erro, e **sanitizada** (usar `sanitize_reason`) |
| CT-EVT-05 | `esteira.board.api` | Chamada real ao `BoardPort` fake (ex.: `move_issue`) dentro do processamento de um item | `esteira.board.plataforma`, `.operacao`, board, issue, `.duracao_s`, `.status` ∈ {`ok`,`erro`,`rate_limit`} (3 sub-casos), `error.type` só quando `erro`/`rate_limit` |
| CT-EVT-06 | `esteira.board.throttle` | Forçar `_throttle_hit()` a mudar o valor corrente (aumento e cooldown, 2 sub-casos) | `esteira.board.plataforma`, `.valor_anterior_s`, `.valor_novo_s`, `.motivo` ∈ {`aumento`,`cooldown`} |
| CT-EVT-07 | `esteira.board.penalty` | Forçar `_penalty_hit()` a ativar e depois desativar o penalty (2 sub-casos) | `.estado` ∈ {`ativo`,`inativo`}, `.horas` (só ativo), `.retorno_em` (só ativo) |
| CT-EVT-08 | `esteira.sync.circuit_breaker` | Provocar as 3 transições reais de `sync_circuit_breaker` (closed→open, open→half_open, half_open→closed) nos dois escopos (`plataforma` e `issue`) | `esteira.breaker.escopo`, plataforma, board/issue só no escopo `issue`, `.estado_anterior`, `.estado_novo` ∈ {`closed`,`half_open`,`open`} |
| CT-EVT-09 | `esteira.sync.escalacao` | Provocar `escalate_pending`/`sync_circuit_breaker_escalation` real | board, issue, `error.type` |
| CT-EVT-10 | `esteira.issue.upsert` | 2 sub-casos: sync incremental aplicando criação/coluna/relação/estado/arquivamento; e snapshot completo do full sync diário | board, issue, coluna, issue.pai, `.filhos`/`.bloqueada_por`/`.bloqueia`/`.labels` (listas, podem ser vazias mas presentes), `.estado` ∈ {`open`,`closed`}, `.arquivada`, `.origem` ∈ {`incremental`,`full_sync`} coerente com o sub-caso |
| CT-EVT-11 | `esteira.issue.transicao` | Provocar `_fire_column_events` com mudança real de coluna | board, issue, `esteira.coluna.de`, `.para` (diferentes entre si) |
| CT-EVT-12 | `esteira.pipe.ciclo` | Uma volta real do loop principal (ou da função isolada que representa uma volta) | `.duracao_s` ≥0, `.houve_mudanca` (bool), `.dormiu_s` ≥0 |
| CT-EVT-13 | `esteira.pipe.ciclo_vida` | `startup()` e shutdown via `_Shutdown` (2 sub-casos) | `.fase` ∈ {`startup`,`shutdown`}, `vcs.ref.head.revision` presente (mesmo valor nos dois sub-casos de uma mesma execução) |
| CT-EVT-14 | `esteira.pipe.incidente` | Ao menos 2 sub-casos de tipos distintos (ex.: `instance_lock_recusado` via `tests/test_instance_lock*.py`, e `steering_reescrito` via `ensure_steering_integrity`) | `.incidente.tipo` ∈ enum fechado do contrato; board/issue presentes só quando aplicável ao tipo |

### CT-EVT-ENUM — Todo `event.name` emitido pertence ao conjunto fechado do contrato

- **Tipo:** estático + integração
- **Arquivo/alvo:** `tests/test_telemetry_contract.py`
- **Passos:**
  1. Reunir a lista fechada dos 15 `event.name` do contrato (14 da tabela +
     `esteira.agente.execucao`) em uma constante de teste.
  2. Rodar os cenários de CT-EXEC-* e CT-EVT-* capturando todos os
     `event.name` observados ao longo da suíte de contrato.
- **Resultado esperado:** todo `event.name` observado está no conjunto fechado;
  nenhum evento com nome fora do padrão `esteira.*`/`vcs.*` previsto aparece
  nos cenários cobertos.
- **Observações:** guarda contra "vazamento" de nomes de evento não
  especificados (ex.: usar o literal do `event=` de log existente sem
  traduzir para o `event.name` do contrato).

---

## Grupo D — Métricas (CA-3)

> Um caso por métrica, todos lendo o `MeterProvider` com leitor em memória
> forçando a coleta (sem esperar o intervalo de exportação periódica).

| Caso | Métrica | Cenário | Atributos e valor esperado |
|---|---|---|---|
| CT-MET-01 | `esteira.board.throttle` | throttle atual > 0 | atributo `plataforma`; valor = segundos de espera correntes (mesmo valor lido por `_throttle_hit`) |
| CT-MET-02 | `esteira.board.penalty` | penalty ativo e inativo (2 sub-casos) | `0` quando inativo; horas restantes quando ativo |
| CT-MET-03 | `esteira.sync.circuit_breaker.estado` | 3 sub-casos (closed/half_open/open, escopo plataforma) | valor `0`/`1`/`2` respectivamente |
| CT-MET-04 | `esteira.sync.circuit_breaker.issues_abertas` | 0, 1 e 2+ issues com breaker ≠ closed | contagem exata; **sem** id de issue como atributo (ver CT-MET-CARD) |
| CT-MET-05 | `esteira.consumo.acumulado` | acumulado > 0 no período corrente | atributos `esteira.ia.plataforma`, `.periodo`, `.unidade`; valor = acumulado lido de `ConsumptionLimiter` |
| CT-MET-06 | `esteira.consumo.limite` | limite configurado e ausente (2 sub-casos) | presente com valor quando configurado; **ausente** (não zero) quando não há limite |
| CT-MET-07 | `esteira.consumo.bloqueado` | bloqueado e não bloqueado (2 sub-casos) | `1`/`0` |
| CT-MET-08 | `esteira.sync.fila.profundidade` | fila com N itens de eventos distintos | atributos board, `esteira.sync.evento`; valor = contagem por combinação |
| CT-MET-09 | `esteira.sync.fila.idade_maxima` | item mais antigo com idade conhecida (relógio controlado) | atributo board; valor = idade em segundos do item mais antigo |
| CT-MET-10 | `esteira.sync.dead_letter.total` | dead-letter com entradas em 2+ categorias | atributo `.categoria`; valor = contagem por categoria |
| CT-MET-11 | `esteira.sync.orfaos.total` | 0 e N órfãos registrados (2 sub-casos) | atributo board; valor = contagem |

### CT-MET-CARD — Regra de cardinalidade: id de issue nunca é atributo de métrica

- **Tipo:** estático + integração
- **Arquivo/alvo:** `tests/test_telemetry_metrics.py` (novo)
- **Passos:**
  1. Rodar todos os cenários de CT-MET-01..11 (inclusive com issues reais
     presentes no estado, como em CT-MET-04/08/09/11).
  2. Coletar todos os pontos de métrica exportados e inspecionar o conjunto de
     chaves de atributo de cada um.
- **Resultado esperado:** nenhuma chave de atributo de nenhuma métrica
  coincide com `esteira.issue` (ou qualquer nome que carregue id de issue). O
  teste falha explicitamente se encontrar, listando a métrica e a chave
  infratora.
- **Observações:** cobre a regra de cardinalidade do contrato — é a única
  forma automatizada de impedir series temporais sem limite (uma por issue).

---

## Grupo E — Resiliência e não-bloqueio (CA-4, R2–R5)

### CT-RES-01 — Coletor inacessível não trava nem falha o ciclo

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_resilience.py` (novo)
- **Pré-condição:** adapter OTel real configurado com
  `OTEL_EXPORTER_OTLP_ENDPOINT` apontando para um host/porta que recusa a
  conexão (ex.: porta fechada em `localhost`); `export_timeout` curto (igual
  ao configurado — ≤2s, R2).
- **Passos:**
  1. Rodar um ciclo completo do loop (ou a sequência equivalente de
     sync+execução) com o export falhando sempre.
- **Resultado esperado:** o ciclo completa normalmente (mesmo resultado de
  negócio de um ciclo sem telemetria); nenhuma exceção da telemetria escapa
  para o chamador; o tempo do ciclo não é dominado pelo timeout de export
  (não há espera síncrona bloqueante maior que o `export_timeout` configurado
  no caminho crítico).
- **Observações:** cobre AC-4 e R3 (fail-open) diretamente.

### CT-RES-02 — Variação de tempo médio de ciclo ≤5% com coletor fora do ar

- **Tipo:** integração (comparativo)
- **Arquivo/alvo:** `tests/test_telemetry_resilience.py`
- **Pré-condição:** mesmo cenário de negócio (N ciclos, com `time.sleep`
  mockado ou removido do cálculo) rodado duas vezes: (a) sem
  `OTEL_EXPORTER_OTLP_ENDPOINT` configurado (sem telemetria) e (b) com
  endpoint configurado apontando para porta fechada (telemetria tentando e
  falhando).
- **Passos:**
  1. Medir a duração de processamento (excluindo `sleep` de ociosidade) de N
     ciclos idênticos nos dois cenários.
  2. Comparar a média.
- **Resultado esperado:** a média do cenário (b) não excede a média do
  cenário (a) em mais de 5%.
- **Observações:** teste de desempenho determinístico — usar operações
  simuladas (fakes) suficientes para que a variação medida reflita apenas o
  overhead de telemetria, não ruído de I/O real. Se o ambiente de CI for
  instável para limiares de tempo, documentar no `test-results.md` a
  metodologia usada (N, iterações, desvio) ao reportar o resultado.

### CT-RES-03 — Fila em memória descarta sob pressão sem bloquear o emissor

- **Tipo:** unitário (adapter)
- **Arquivo/alvo:** `tests/test_telemetry_resilience.py`
- **Pré-condição:** adapter configurado com export que nunca completa
  (bloqueado) ou é artificialmente lento; `max_queue_size` ≤2048 (conforme
  configurado por R2); emitir mais eventos que a capacidade da fila.
- **Passos:**
  1. Emitir um número de eventos maior que `max_queue_size` em sequência
     rápida.
- **Resultado esperado:** nenhuma chamada de emissão bloqueia o chamador
  (chamadas retornam rapidamente, sem esperar o export); eventos excedentes
  são descartados (não há arquivo de overflow, não há reenvio — R2); nenhuma
  exceção propaga ao chamador.
- **Observações:** cobre R2 e R4 diretamente — "nenhuma chamada de emissão
  bloqueia o loop".

### CT-RES-04 — No máximo um aviso de falha de export por janela de 10 min

- **Tipo:** unitário (adapter)
- **Arquivo/alvo:** `tests/test_telemetry_resilience.py`
- **Pré-condição:** export configurado para falhar sempre; relógio
  controlável.
- **Passos:**
  1. Provocar múltiplas falhas de export dentro de uma janela de 10 minutos
     (simulada via relógio controlado).
  2. Avançar o relógio para além de 10 minutos e provocar nova falha.
- **Resultado esperado:** no máximo **um** `log.warning`/`log.error` de falha
  de export é emitido na primeira janela, independente de quantas falhas
  ocorreram dentro dela; após passar os 10 minutos, uma nova falha pode gerar
  um novo aviso único.
- **Observações:** cobre R3 ("no máximo um aviso de falha de export por
  janela de 10 min"). Verificar via `logs/<data>.json`, nunca via leitura de
  estado interno protegido.

### CT-RES-05 — SIGTERM: flush com teto de 2s, shutdown não piora

- **Tipo:** integração (regressão + nova verificação)
- **Arquivo/alvo:** `tests/test_sigterm_shutdown.py` (estendido) ou novo
  `tests/test_telemetry_resilience.py`
- **Pré-condição:** telemetria configurada com export lento/bloqueado (nunca
  completa); handler de `SIGTERM` registrado (comportamento já existente,
  `_Shutdown`).
- **Passos:**
  1. Disparar `_handle_sigterm` com telemetria pendente de flush.
  2. Medir o tempo até o processo concluir o shutdown.
- **Resultado esperado:** `tests/test_sigterm_shutdown.py` **continua
  passando sem alteração de comportamento** (regressão explícita, R5); o
  flush da telemetria respeita um teto de 2s (não aguarda indefinidamente um
  export que nunca completa) e o shutdown ocorre dentro do tempo total já
  validado por aquela suíte.
- **Observações:** é o único caso que toca o arquivo de teste existente —
  qualquer alteração nele deve preservar os testes atuais (nenhum removido ou
  enfraquecido).

---

## Grupo F — No-op sem configuração (CA-5, R1)

### CT-NOOP-01 — Sem `OTEL_EXPORTER_OTLP_ENDPOINT`: nenhuma conexão para 4317/4318

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_noop.py` (novo)
- **Pré-condição:** nenhuma variável `OTEL_*` configurada; monkeypatch em
  `socket.socket.connect`/`connect_ex` (ou equivalente no nível de transporte
  usado pelo exporter OTLP) para registrar qualquer tentativa de conexão a
  qualquer host nas portas `4317` ou `4318`.
- **Passos:**
  1. Rodar um ciclo completo (sync + execução de agente) com a instrumentação
     de telemetria ativa no código, mas sem endpoint configurado.
- **Resultado esperado:** zero tentativas de conexão registradas para as
  portas `4317`/`4318`, em qualquer host. Nenhum exporter OTLP é instanciado/
  inicializado (o adapter nem tenta configurar o SDK de exportação).
- **Observações:** é o teste mais direto do critério de aceitação CA-5 —
  "nenhuma conexão de saída é aberta".

### CT-NOOP-02 — `OTEL_SDK_DISABLED=true` tem o mesmo efeito, mesmo com endpoint configurado

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_noop.py`
- **Pré-condição:** `OTEL_EXPORTER_OTLP_ENDPOINT` configurado para um host
  real **e** `OTEL_SDK_DISABLED=true`.
- **Passos:**
  1. Rodar o mesmo ciclo de CT-NOOP-01.
- **Resultado esperado:** mesmo resultado de CT-NOOP-01 — zero conexões,
  nenhum custo perceptível — mesmo com o endpoint presente, porque o SDK está
  desabilitado.
- **Observações:** cobre a segunda forma do R1 ("ou `OTEL_SDK_DISABLED=true`").

### CT-NOOP-03 — Saída de terminal idêntica à de hoje sem telemetria

- **Tipo:** integração (snapshot/comparação)
- **Arquivo/alvo:** `tests/test_telemetry_noop.py`
- **Pré-condição:** mesma entrada de negócio rodada em duas branches/estados:
  o código **antes** desta entrega (ou a mesma execução com a instrumentação
  interceptada/desativada) e o código **depois**, sem nenhuma `OTEL_*`
  configurada.
- **Passos:**
  1. Capturar a saída de terminal (stdout) de um ciclo representativo nos dois
     cenários.
- **Resultado esperado:** a saída de terminal é a mesma (mesmas linhas de log
  coloridas, mesmo formato) — a instrumentação não adiciona, remove nem
  reordena nenhuma linha do log de terminal existente quando no-op.
- **Observações:** é um teste de regressão de UX de operação — garante que
  "mesma saída de terminal de hoje" (R1) não é quebrada silenciosamente.

### CT-NOOP-04 — No-op não falha ao medir custo (sem overhead perceptível)

- **Tipo:** integração (comparativo, leve)
- **Arquivo/alvo:** `tests/test_telemetry_noop.py`
- **Pré-condição:** mesmo cenário de negócio rodado sem `OTEL_*` configurada,
  medido antes de existir qualquer chamada de instrumentação (baseline) e
  depois de instrumentado (no-op).
- **Passos:**
  1. Medir tempo de N execuções do mesmo cenário puramente local, nos dois
     momentos.
- **Resultado esperado:** overhead do caminho no-op é não perceptível (mesmo
  limiar de variação de CT-RES-02, ≤5%, aplicado ao caso mais favorável —
  sem telemetria configurada o overhead deve ser menor, nunca maior, que o
  cenário "coletor fora do ar").
- **Observações:** complementa CT-RES-02; aqui o pior caso nem chega a tentar
  exportar.

---

## Grupo G — Atributos de recurso e distinguibilidade entre pipes (CA-6)

### CT-RES-ATTR-01 — Atributos de recurso fixos e corretos em todo sinal

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_resource.py` (novo)
- **Passos:**
  1. Emitir ao menos um evento, uma métrica e um span (ex.: via cenários de
     CT-EXEC-01) e inspecionar o `Resource` associado a cada um.
- **Resultado esperado:** todo sinal carrega `service.name="esteira-agentica"`,
  `service.version` igual a `src.core.version.VERSION`,
  `esteira.contrato="1"` (fixo), e os demais atributos de recurso do contrato.
- **Observações:** cobre a tabela "Atributos de recurso" do contrato, parte
  fixa.

### CT-RES-ATTR-02 — `service.instance.id` via `OTEL_RESOURCE_ATTRIBUTES` ou default de `instance_id(config)`

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_resource.py`
- **Pré-condição:** 2 sub-casos: (a) `OTEL_RESOURCE_ATTRIBUTES` contendo
  `service.instance.id=<valor>`; (b) variável ausente.
- **Passos:**
  1. Emitir um sinal em cada sub-caso e inspecionar `service.instance.id`.
- **Resultado esperado:** (a) usa o valor explícito da env var; (b) usa
  `consumption_limit.instance_id(config)` (URL do repositório configurado,
  sem userinfo).
- **Observações:** reusa a função já existente e testada — telemetria não
  duplica a lógica de sanitização de URL.

### CT-RES-ATTR-03 — `esteira.pipe.nome` via env ou default do nome do repositório

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_resource.py`
- **Pré-condição:** 2 sub-casos, análogos a CT-RES-ATTR-02, para
  `esteira.pipe.nome`.
- **Resultado esperado:** valor explícito da env var quando presente; nome de
  exibição do repositório (derivado da config) quando ausente.

### CT-RES-ATTR-04 — `deployment.environment.name` é `null` quando `PIPE_ENVIRONMENT` ausente

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_resource.py`
- **Pré-condição:** 2 sub-casos: `PIPE_ENVIRONMENT` ausente e presente.
- **Resultado esperado:** ausente ⇒ atributo `deployment.environment.name`
  presente com valor `null`/ausente conforme a semântica OTel de atributo
  nulo (documentar no runbook qual das duas formas o adapter usa); presente
  ⇒ valor igual à env var.

### CT-DIST-01 — Duas pipes com `service.instance.id` diferentes são distinguíveis em eventos, métricas e traces

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_resource.py`
- **Pré-condição:** duas instâncias do adapter configuradas com
  `service.instance.id` distintos (`pipe-a`, `pipe-b`), cada uma emitindo para
  o **mesmo** coletor em memória (simulando "mesmo coletor recebendo de
  ambas").
- **Passos:**
  1. Emitir um evento, uma métrica e um span de cada instância.
  2. Agrupar os sinais recebidos pelo atributo `service.instance.id`.
- **Resultado esperado:** os sinais de `pipe-a` e `pipe-b` são perfeitamente
  separáveis pelo atributo em todos os três tipos de sinal — nenhum sinal de
  uma instância aparece sem o `service.instance.id` correto, e não há
  mistura/perda de atribuição.
- **Observações:** cobre CA-6 de ponta a ponta.

---

## Grupo H — Traces (parte de CA-1/CA-2)

### CT-TRACE-01 — Span `invoke_agent {gen_ai.agent.name}` com atributos de execução

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_traces.py` (novo)
- **Pré-condição:** mesma de CT-EXEC-01, com `SpanExporter` em memória.
- **Passos:**
  1. Chamar `call_agent` e coletar o span emitido.
- **Resultado esperado:** nome do span começa com `invoke_agent` e contém o
  `gen_ai.agent.name` resolvido; atributo `gen_ai.operation.name=invoke_agent`;
  os mesmos atributos próprios de `esteira.agente.execucao` (CT-EXEC-01) estão
  presentes no span. O evento `esteira.agente.execucao` (quando emitido dentro
  do span) carrega `trace_id`/`span_id` iguais aos do span.
- **Observações:** fecha CA-1 (evento + span juntos).

### CT-TRACE-02 — Span `esteira.sync.item {evento}` e filho `esteira.board.api {operacao}`

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_traces.py`
- **Pré-condição:** processamento real de um item de sync que dispara ao
  menos uma chamada ao `BoardPort` fake.
- **Passos:**
  1. Processar o item via `apply_changes`.
  2. Coletar os spans e verificar a relação pai/filho pelo `parent_id`/
     `span_id`.
- **Resultado esperado:** um span `esteira.sync.item {evento}` com os mesmos
  atributos de CT-EVT-04; um span filho `esteira.board.api {operacao}` com os
  atributos de CT-EVT-05, cujo `parent_span_id` é o `span_id` do span de item.
- **Observações:** verifica a hierarquia de spans exigida pelo contrato
  ("filho do span de item").

### CT-TRACE-03 — Evento emitido dentro de um span carrega `trace_id`/`span_id`

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_traces.py`
- **Passos:**
  1. Reusar o cenário de CT-TRACE-02; coletar o `LogRecord` de
     `esteira.sync.item` emitido dentro do span correspondente.
- **Resultado esperado:** `trace_id` e `span_id` do `LogRecord` coincidem com
  os do span `esteira.sync.item` ativo no momento da emissão.
- **Observações:** regra geral do contrato ("todo evento emitido dentro de um
  span carrega trace_id/span_id dele"), verificada num segundo caso (além do
  de execução, CT-TRACE-01) para confirmar que não é específico de um único
  ponto de instrumentação.

---

## Grupo I — Dados proibidos (privacidade/segurança)

### CT-PRIV-01 — Nenhum sinal contém prompt, conversa, body ou comentário

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_privacy.py` (novo)
- **Pré-condição:** cenário de execução real com um prompt/body volumoso e
  reconhecível (string marcadora única, ex.: `"PROMPT-MARCADOR-XYZ"`).
- **Passos:**
  1. Rodar o cenário com telemetria ativa (coletores em memória capturando
     eventos, métricas e spans).
  2. Buscar a string marcadora em **todos** os atributos de **todos** os
     sinais coletados (serializando cada atributo para string).
- **Resultado esperado:** a string marcadora não aparece em nenhum atributo
  de nenhum sinal.
- **Observações:** teste de varredura ampla — mais confiável que verificar
  atributo por atributo, pois pega vazamento por qualquer caminho não
  previsto.

### CT-PRIV-02 — Nenhum sinal contém tokens/credenciais

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_privacy.py`
- **Pré-condição:** config com uma URL de repositório contendo userinfo
  (`https://user:TOKEN-MARCADOR@host/...`) e/ou uma credencial de board
  configurada.
- **Passos:**
  1. Rodar um cenário que utiliza `instance_id(config)` e demais pontos que
     leem config/credenciais.
  2. Buscar o marcador de credencial em todos os atributos coletados.
- **Resultado esperado:** `service.instance.id` e qualquer outro atributo
  derivado da URL **não** contêm o userinfo (mesma regra já aplicada por
  `_URL_USERINFO.sub`); nenhum token aparece em nenhum atributo.

### CT-PRIV-03 — URL com userinfo nunca aparece crua em nenhum atributo

- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_telemetry_privacy.py`
- **Passos:**
  1. Repetir CT-RES-ATTR-02 (sub-caso default) com uma URL de repositório
     contendo userinfo.
- **Resultado esperado:** `service.instance.id` tem o userinfo removido
  (mesmo padrão de `_URL_USERINFO`), igual ao comportamento já validado para
  `consumption_limit.instance_id`.

### CT-PRIV-04 — Mensagem de erro sem `sanitize_reason` nunca é emitida

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_privacy.py`
- **Pré-condição:** provocar um erro de sync cuja mensagem bruta contenha um
  token de GitHub reconhecível (`ghp_...`) ou um caminho protegido
  (`.pipe/changeQueue.json`).
- **Passos:**
  1. Processar o item até o evento `esteira.sync.item`/`esteira.pipe.incidente`
     que carrega `esteira.erro.mensagem`.
- **Resultado esperado:** o atributo `esteira.erro.mensagem` é exatamente o
  resultado de `dead_letter.sanitize_reason(msg)` aplicado à mensagem bruta —
  token mascarado, caminho protegido substituído por `<arquivo interno>`.
  Nunca a mensagem bruta.
- **Observações:** reusa a função já existente e testada
  (`tests/test_dead_letter.py` já cobre `sanitize_reason` isoladamente); aqui
  o teste é de **integração com o emissor de telemetria**, garantindo que o
  caminho de telemetria não contorna a sanitização.

### CT-PRIV-05 — Título da issue ausente sem opt-in (revisão cruzada com CT-EXEC-03)

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_telemetry_privacy.py`
- **Observações:** mesmo caso de CT-EXEC-03, listado aqui para fechar a
  rastreabilidade da cláusula "Dados proibidos" (o título só é dado
  potencialmente sensível com opt-in explícito).

---

## Grupo J — Infraestrutura (R6, R7, R8)

### CT-INFRA-01 — Dependências OTel pinadas no Dockerfile e em `docker/versions.env`

- **Tipo:** estático
- **Arquivo/alvo:** `tests/test_dockerfile.py` (estendido)
- **Passos:**
  1. Verificar no `Dockerfile` uma camada `pip install` com
     `opentelemetry-sdk==<versão>` e `opentelemetry-exporter-otlp==<versão>`
     (ou os pacotes de exporter equivalentes exigidos pelo adapter), no mesmo
     padrão de `pip install --no-cache-dir pyyaml==6.0.2`.
  2. Verificar que as mesmas versões estão documentadas em
     `docker/versions.env` (padrão `PYYAML_VERSION`, ver ADR-04).
- **Resultado esperado:** versões exatas (sem `>=`/`~=`) pinadas nos dois
  arquivos, e iguais entre si.
- **Observações:** segue o padrão já testado para `pyyaml`/`gh`/`git` em
  `tests/test_dockerfile.py`.

### CT-INFRA-02 — `compose.telemetria.yml` liga `dind` à rede externa sem quebrar o compose base

- **Tipo:** estático (+ opcional `docker compose config`, mascarado se Docker
  ausente — mesmo padrão `DOCKER_SKIP` de `tests/test_docker_compose.py`)
- **Arquivo/alvo:** `tests/test_docker_compose.py` (estendido) ou novo
  `tests/test_compose_telemetria.py`
- **Passos:**
  1. Verificar que `compose.telemetria.yml` existe na raiz e declara a rede
     externa `esteira-telemetria` e o serviço `dind` conectado a ela
     (`networks: - esteira-telemetria`, com `external: true` na definição da
     rede).
  2. Rodar `docker compose -f docker-compose.yml -f compose.telemetria.yml
     config` (pulado se Docker ausente) e confirmar que não há erro de
     sintaxe.
  3. Rodar `docker compose -f docker-compose.yml config` (sem o override) e
     confirmar que continua válido — a base funciona sem o override.
- **Resultado esperado:** ambos os comandos de `config` saem sem erro; o
  serviço `dind` aparece conectado a `esteira-telemetria` apenas quando o
  override é aplicado.

### CT-INFRA-03 — Startup loga `service.instance.id`, `esteira.pipe.nome` e endpoint, sem credencial

- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_startup_agent_circuit_break.py` é o padrão
  de teste de startup existente — criar `tests/test_telemetry_startup.py`
  (novo), seguindo o mesmo padrão.
- **Pré-condição:** `OTEL_EXPORTER_OTLP_ENDPOINT` configurado com uma URL
  contendo, por exemplo, uma query string; config com `service.instance.id`
  derivável de uma URL com userinfo.
- **Passos:**
  1. Rodar `startup(config)`.
  2. Inspecionar `logs/<data>.json` do dia.
- **Resultado esperado:** uma linha de log de startup contém
  `service.instance.id`, `esteira.pipe.nome` e o endpoint OTLP resolvido;
  nenhuma credencial (userinfo da URL do endpoint, se houver, ou token)
  aparece na linha.
- **Observações:** cobre R8 de ponta a ponta, inclusive a exigência "sem
  credencial".

### CT-INFRA-04 — `compose.telemetria.yml` não altera o comportamento do compose base sem o override

- **Tipo:** estático
- **Arquivo/alvo:** mesmo de CT-INFRA-02
- **Passos:**
  1. Comparar a saída de `docker compose -f docker-compose.yml config` antes
     e depois de `compose.telemetria.yml` existir no repositório (sem
     aplicá-lo via `-f`).
- **Resultado esperado:** saída idêntica — a mera existência do arquivo de
  override não é aplicada automaticamente.

---

## Grupo K — Versão, runbook, `CONTEXT.md`, suíte completa (CA-7)

### CT-VER-01 — Bump MINOR da versão

- **Tipo:** estático
- **Arquivo/alvo:** `tests/test_version_bump.py` (estendido, mesmo padrão já
  usado nos bumps anteriores — baseline `>=`)
- **Passos:**
  1. Verificar `src.core.version.VERSION` ≥ `1.30.0` (MINOR acima do baseline
     `1.29.0` confirmado nesta entrega) e com `PATCH` mantido em `.0` se for
     bump limpo (ou documentar no histórico da issue se houver patch
     intermediário).
- **Resultado esperado:** versão segue `MAJOR.MINOR.PATCH`; MINOR estritamente
  maior que `29`; `MAJOR` inalterado.

### CT-VER-02 — Runbook `doc/runbook/telemetria.md` existe e cobre o contrato operacional

- **Tipo:** estático
- **Arquivo/alvo:** `tests/test_telemetry_runbook.py` (novo, mesmo padrão de
  `tests/test_docker_runbook.py`)
- **Passos:**
  1. Verificar que o arquivo existe.
  2. Verificar presença de seções mínimas: como configurar `OTEL_*` (endpoint,
     protocolo gRPC/HTTP), como ligar à rede `esteira-telemetria` via
     `compose.telemetria.yml`, a versão das convenções GenAI usada (exigida
     pelo contrato: "fixar a versão usada no runbook"), e uma menção explícita
     de que perda de telemetria é aceitável e atraso de processamento não é.
- **Resultado esperado:** todas as seções mínimas presentes; nenhuma
  divergência entre o endpoint padrão documentado e
  `http://esteira-otlp:4318` do contrato.

### CT-VER-03 — `CONTEXT.md` documenta a entrega

- **Tipo:** estático
- **Arquivo/alvo:** `tests/test_version_bump.py` (estendido) ou
  `tests/test_telemetry_runbook.py`
- **Passos:**
  1. Verificar uma nova seção em `CONTEXT.md` (padrão `## <título> (vX.Y.Z)`
     já usado nas entregas anteriores) descrevendo o port de telemetria, o
     contrato v1 e a versão do bump.
- **Resultado esperado:** seção presente, com a versão citada igual à de
  CT-VER-01.

### CT-VER-04 — Suíte completa passa após a entrega

- **Tipo:** execução completa (não é um único `assert`, é o veredito da etapa
  de execução de testes)
- **Passos:**
  1. `python -m pytest` completo.
- **Resultado esperado:** 100% dos testes existentes antes desta entrega
  continuam passando (nenhuma regressão, nenhum teste removido/enfraquecido
  sem justificativa), mais todos os novos casos deste documento.
- **Observações:** verificado na etapa de Execução de Testes desta mesma
  issue — não é um teste unitário isolado, é o critério de veredito final.

---

## Resumo de cobertura

- **7/7 CAs** cobertos (tabela de rastreabilidade).
- **15/15 `event.name`** do contrato cobertos (CT-EXEC-01 + CT-EVT-01..14),
  mais CT-EVT-ENUM fechando o conjunto.
- **11/11 métricas** cobertas (CT-MET-01..11) + regra de cardinalidade
  (CT-MET-CARD).
- **3/3 spans** cobertos (CT-TRACE-01..03).
- **R1–R10**: R1→Grupo F, R2→CT-RES-03, R3→CT-RES-01/04, R4→CT-RES-03,
  R5→CT-RES-05, R6→CT-INFRA-01, R7→CT-INFRA-02/04, R8→CT-INFRA-03,
  R9→Grupo A, R10→este documento inteiro é a resposta a R10 (contrato,
  no-op, descarte, coletor fora do ar, dados proibidos).
- **Dados proibidos**: 5 casos (Grupo I), incluindo reuso explícito de
  `sanitize_reason` e `_URL_USERINFO` já existentes.
