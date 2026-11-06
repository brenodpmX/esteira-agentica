# Casos de Teste — Limitador opcional de consumo de IA por plataforma

- **Issue:** #311
- **Story relacionada:** reaproveita a captura de consumo por execução já
  entregue pela issue #307 (`src/core/execution_record.py`); bloqueia #317
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA) SR
- **Data:** 2026-11-06
- **Branch:** `feature/311-limitador_opcional_de_consumo_de_ia_por_plataforma`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA 1–12) da
> issue #311 e dos 15 cenários obrigatórios (CT-01..CT-15) do seu próprio
> Detalhamento. Os testes são da suíte Python do motor (pytest, em `tests/`).
> Casos de janela/tempo/calendário usam **relógio e fuso controláveis**
> (injeção/`monkeypatch`), nunca `sleep` real nem dependência do relógio real
> da máquina de CI.

---

## Contexto de arquitetura (baseline do código atual)

O mecanismo não existe hoje. O que já existe e os casos abaixo reaproveitam ou
seguem como molde de implementação:

- **Captura de consumo por execução (#307, `src/core/execution_record.py`)** —
  `Consumo` (`disponivel`/`valor`/`unidade`/`origem`) já é extraído pelo
  adapter Kiro (`src/adapters/kiro_cli_agent.py::_parse_stream_json`) e exposto
  em `ExecutionResult.consumo`; `src/__main__.py::_write_execution_record`
  grava um `ExecutionRecord` por execução em `.pipe/executionRecords.json`.
  **Este trabalho não recria essa captura** — consome o `valor`/`unidade`/
  `disponibilidade` já produzidos como insumo do acumulador por
  plataforma/período. Hoje só a plataforma Kiro popula esse valor; RF-05 pede
  estender o mesmo contrato a outras plataformas quando existirem — não há
  segunda plataforma no código hoje, então os casos de isolamento entre
  plataformas (Grupo B) usam um `AgentPort` fake de segunda plataforma, não um
  adapter real.
- **Precedente de bloqueio pré-ação por plataforma
  (`src/core/sync_circuit_breaker.py::SyncCircuitBreaker.platform_blocked`)** —
  já decide, antes de uma ação de sync, se uma plataforma está bloqueada,
  consultando estado persistido local. É o precedente arquitetural mais
  próximo do que este trabalho precisa fazer **antes do acionamento do
  agente** (gate equivalente, decisão diferente: aqui é consumo acumulado
  versus limite, não falhas).
- **Precedente de política opcional + bloqueio pré-execução
  (`src/core/agent_circuit_break.py`)** — molde de qualidade mais próximo
  deste mecanismo: bloco de config opcional de RAIZ com `validate_*`/
  `resolve_*` (`validate_agent_circuit_break`/`resolve_policy`), estado
  persistido atomicamente (arquivo temporário + `fsync` + `os.replace`) em
  JSON protegido com versão lógica, fail-closed em corrupção/ilegibilidade do
  estado, e uma função de admissão (`CircuitBreaker.admit`) chamada em
  `call_agent` **antes** do dispatch (`_admit_circuit_break`, ponto exato:
  `src/__main__.py`, após o gate de composição em camadas e antes do dispatch
  real). **Diferença deliberada de comportamento** que os casos abaixo cobram
  (RN-06/tabela de falha): o `agent_circuit_break` é fail-**closed** em estado
  corrompido (nega admissão); este limitador de consumo é fail-**aberto** por
  natureza do próprio domínio (RN-06/RN-11) — estado acumulado corrompido ou
  ausente deve **zerar e seguir permitindo**, nunca bloquear indevidamente por
  falta de dado (ver CT-B14).
- **Ponto de inserção do gate** — `call_agent` (`src/__main__.py`) já resolve
  `platform` a partir de `agents.<plataforma>.<agente>` antes de montar
  `AgentParams` e despachar o adapter. O novo gate de consumo entra nesse
  mesmo ponto, antes da linha que cria `KiroCliAgent()`/chama
  `_dispatch_with_recovery`, no mesmo espírito de `_admit_circuit_break`.
- **Risco de config concreto e verificável hoje
  (`src/core/config.py::_validate_agents`)** — a função itera **todas** as
  chaves de `agents.<plataforma>` como se fossem agentes
  (`for agent_id, agent_cfg in platform.items(): _require(agent_cfg, "name", ...)`).
  Como RF-06 propõe `agents.<plataforma>.limits` como **irmã** das entradas de
  agente (mesmo nível), uma implementação ingênua faz `_validate_agents`
  tratar `limits` como um agente sem `name` e rejeitar uma configuração
  válida. É o mesmo tipo de bug já resolvido para `boards.agent_circuit_break`
  (ver `tests/test_agent_circuit_break_config.py::TestBlocoDentroDeBoards`) —
  aqui teria o efeito inverso (falso-positivo de erro, não falso-negativo de
  isolamento). CT-A3 fixa esse comportamento.
- **`PROTECTED_PATHS`** (`src/core/agent.py`) lista os arquivos de estado
  interno nunca citáveis em prompt. O novo arquivo de estado do acumulador
  entra nessa lista, mesmo padrão de `.pipe/agentCircuitBreak.json`/
  `.pipe/syncCircuitBreaker.json`.
- **Log estruturado dual** (`src/core/log.py`) — `log.warning`/`log.error`
  emitem para terminal (resumo) e arquivo (`logs/<data>.json`, com campos
  extras). Nos testes, o arquivo é capturado substituindo `log._file` por um
  `io.StringIO()` e lendo `log._file.getvalue()` (padrão de
  `tests/test_sync_circuit_breaker.py::read_events`); o terminal é capturado
  via `capsys`/substituição do stream de saída do logger.

> **Decisão de design NÃO fixada pela QA (é do desenvolvimento):** nome do
> módulo, da classe e das funções do núcleo (`validate_*`/`resolve_*`/
> `admit`-equivalente), nome exato do arquivo de estado
> (`.pipe/consumptionLimit.json` é o nome **provável** pela convenção da
> casa — `agentCircuitBreak.json`/`syncCircuitBreaker.json`), e a forma exata
> de inserir o gate em `call_agent`. Os casos abaixo testam **comportamento e
> invariantes observáveis** descritos nos CAs/RFs/RNs da issue, não
> assinaturas. Onde um caso cita um símbolo concreto, o alvo é **provável**
> pela arquitetura atual; se o desenvolvimento adotar outro nome, o caso vale
> sobre o comportamento equivalente.

### Convenções para o desenvolvimento (todos os casos automatizados)

- **Relógio e fuso controláveis:** todo caso de janela/calendário injeta o
  "agora" (função/clock substituível) e, quando pertinente, o fuso via
  configuração explícita — nunca depende do fuso real da máquina de CI nem de
  `sleep` real.
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` autouse por teste
  (`.pipe/`, `logs/` isolados). Qualquer cache em memória do módulo (se
  houver) é limpo em fixture autouse — mesmo padrão de
  `test_rerun_cooldown.py`/`test_remediation_loop.py`.
- **Fake de plataforma/adapter:** os casos de isolamento entre plataformas
  (Grupo B) e de integração do gate (Grupo E) usam um `AgentPort` fake espião
  (nunca chama `kiro-cli` real), que permite controlar o `Consumo` retornado
  por execução e contar quantas vezes `execute` foi chamado — mesmo padrão de
  `tests/test_agent_circuit_break.py`.
- **Evidência por log estruturado:** verificar o log lendo `logs/<data>.json`
  e localizando o evento pelo campo `event` (nunca inspecionar
  `.pipe/consumptionLimit.json` como fonte de evidência de comportamento de
  negócio, exceto nos casos que a própria QA marca como "verificação de
  persistência", ex.: CT-B12/CT-B14).
- **Config mínima:** cada caso assume um `config: dict` válido com, quando
  pertinente, `agents.<plataforma>.limits` conforme o contrato da issue
  (`timezone`, `daily.limit`, `weekly.limit`/`reset_weekday`,
  `monthly.limit`/`reset_day`).
- **Nunca** fazer `monkeypatch` do próprio símbolo sob teste (lição do
  incidente #106) — só relógio, fuso e o adapter/porta externa são
  substituídos; a decisão de bloqueio é exercitada de verdade.

---

## Rastreabilidade (CA → casos)

| CA (issue #311) | Requisito/Regra | Caso(s) |
|---|---|---|
| CA-1 (CT-01 da issue) | RF-01, RF-07, RF-08 / RN-02 | CT-B1, CT-B2, CT-B3 |
| CA-2 (CT-02 da issue) | RF-01 / RN-01 | CT-A1, CT-B4 |
| CA-3 (CT-03 da issue) | RF-08 / RN-03 | CT-B5 |
| CA-4 (CT-04 da issue) | RF-10 / RN-04 | CT-B6 |
| CA-5 (CT-05 da issue) | RF-10 / RN-04 | CT-B7 |
| CA-6 (CT-06/07/08 da issue) | RF-11 / RN-07 | CT-C1, CT-C2, CT-C3, CT-C4 |
| CA-7 (CT-10/11 da issue) | RF-12 / RN-10 | CT-B9, CT-B10 |
| CA-8 (CT-12 da issue) | RF-13 / RN-06 | CT-B11, CT-D4 |
| CA-9 (todas as tentativas impedidas) | RF-09 / RN-08 | CT-D1, CT-D2, CT-D3 |
| CA-10 (CT-09 da issue) | RF-04 / RNF-04 | CT-C5, CT-C6 |
| CA-11 (CT-13 da issue) | RF-02 / RN-02 | CT-B8 |
| CA-12 (métricas do baseline) | RF-14 | CT-F1 |
| — (contrato de configuração, derivado de RF-01/06) | RF-01, RF-06 | CT-A1..CT-A10 |
| — (robustez/borda, derivado de RN-02) | RN-02 | CT-B1, CT-B2, CT-B3 |
| — (isolamento de unidade, derivado de RN-05) | RN-05 | CT-B13 |
| — (falha de estado, tabela "Comportamento em falha") | — | CT-B14, CT-B15, CT-C7 |
| — (compatibilidade retroativa, RNF-05) | RNF-05 | CT-A10 |
| — (custo de verificação, RNF-01) | RNF-01 | CT-E2 |
| — (robustez de 100% de bloqueio, RN-09) | RN-09 | CT-E3 |
| — (segurança do registro, RNF-06) | RNF-06 | CT-D4 |

> Cobertura: os 15 cenários obrigatórios do corpo da issue (CT-01..CT-15) mapeiam
> para os casos deste documento — ver tabela "Mapa CT da issue → casos" ao
> final. Não há CA sem caso, nem caso sem CA de origem. O escopo está completo
> e internamente consistente para derivar estes casos — não há contradição ou
> lacuna que exija devolver ao planejamento.

---

## Grupo A — Configuração (`agents.<plataforma>.limits`)

### CT-A1 — Bloco `limits` ausente mantém o comportamento atual

- **CA de origem:** CA-2 — "Dado uma plataforma sem qualquer limite
  configurado, quando ela é acionada, então o comportamento é idêntico ao
  atual, sem verificação de cota."
- **Tipo:** unitário (validação de config + resolução de política)
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py` (novo)
- **Pré-condição:** `config["agents"]["kiro"]["<agente>"]` sem a chave
  `limits`.
- **Passos:**
  1. Chamar a validação de forma do bloco (equivalente a
     `validate_agent_circuit_break`, mas para `limits`).
  2. Resolver a política da plataforma `kiro` nesse config.
- **Resultado esperado:** validação não levanta erro; a política resolvida é
  inativa (nenhum período configurado).
- **Observações:** cobre RN-01. Espelha
  `tests/test_agent_circuit_break_config.py::TestResolvePolicy::test_ausente_inativa`.

### CT-A2 — Bloco `limits` válido com períodos isolados e combinados é aceito

- **CA de origem:** CA-11 — combinação de diário/semanal/mensal.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** quatro variações de `limits`: só `daily`; só `weekly`
  (com `reset_weekday`); só `monthly` (com `reset_day`); os três juntos, em
  ordem arbitrária das chaves no mapa.
- **Passos:** validar cada variação.
- **Resultado esperado:** nenhuma variação levanta erro; a política resolvida
  expõe exatamente os períodos presentes, com os valores informados.
- **Observações:** cobre RF-01/RF-02. Parametrizado (4 casos).

### CT-A3 — Chave `limits` não é confundida com um agente

- **CA de origem:** derivado de RF-06 (local da configuração do limite).
- **Tipo:** unitário (regressão de arquitetura)
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** `config["agents"]["kiro"]` com uma entrada de agente real
  (`dev: {name: "Dev"}`) **e** a chave irmã `limits` com um bloco válido
  (`{daily: {limit: 100}}`).
- **Passos:**
  1. Rodar `_validate_agents` (`src/core/config.py`) sobre esse `agents`.
  2. Rodar a validação de `limits`.
  3. Rodar `check_config`/o pipeline completo de validação com este `agents`.
- **Resultado esperado:** `_validate_agents` não trata `limits` como agente
  (não exige `name` dentro dele, não gera `ConfigError` espúrio); a
  configuração completa é aceita.
- **Observações:** regressão análoga a
  `TestBlocoDentroDeBoards` de `test_agent_circuit_break_config.py`, mas no
  sentido inverso (falso-positivo de erro). Decisão de implementação
  (reservar a chave `limits` em `_validate_agents`) é do desenvolvimento; o
  caso fixa o comportamento observável.

### CT-A4 — `timezone`: ausente aceito; identificador válido aceito; identificador inválido rejeitado

- **CA de origem:** CA-10 — fuso configurado/ausente.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** três variações: sem `timezone`; `timezone:
  "America/Sao_Paulo"`; `timezone: "Nao/Existe"`.
- **Passos:** validar cada variação.
- **Resultado esperado:** as duas primeiras não levantam erro; a terceira
  levanta `ConfigError` citando `agents.<plataforma>.limits.timezone` e o
  valor recebido.
- **Observações:** cobre RF-04. A verificação de identificador válido usa a
  mesma biblioteca de fuso que o núcleo usará em runtime (ex.: `zoneinfo`),
  para não validar com uma lista estática divergente.

### CT-A5 — Limite ≤ 0 rejeitado em qualquer período; `bool` rejeitado antes de `int`

- **CA de origem:** derivado de RN-02 (contrato de limite > 0) e do padrão da
  casa de validação (`validate_agent_circuit_break`).
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** `daily.limit`, `weekly.limit`, `monthly.limit`
  parametrizados com `0`, `-1`, `True`, `False`, `1.5`, `"10"`.
- **Passos:** validar cada combinação (período × valor inválido).
- **Resultado esperado:** toda combinação levanta `ConfigError` citando o
  caminho completo (`...limits.daily.limit`/`weekly.limit`/`monthly.limit`) e
  o valor recebido; `True`/`False` são rejeitados pela mesma regra de
  "não é inteiro válido" (nunca aceitos como 1/0).
- **Observações:** cobre a tabela "Comportamento em falha" (config inválida);
  parametrizado (3 períodos × 6 valores = 18 sub-casos).

### CT-A6 — `weekly.reset_weekday`: faixa, obrigatoriedade e tipo

- **CA de origem:** derivado de RF-03.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** `weekly` presente com `reset_weekday` em `-1`, `7`,
  ausente, `"2"`, e nos extremos válidos `0` e `6`.
- **Passos:** validar cada variação.
- **Resultado esperado:** `-1`, `7`, ausente e `"2"` levantam `ConfigError`
  citando `...limits.weekly.reset_weekday`; `0` e `6` são aceitos.
- **Observações:** cobre RF-03/RN-02 (contrato de configuração).

### CT-A7 — `monthly.reset_day`: faixa, `"last"`, obrigatoriedade e tipo

- **CA de origem:** derivado de RF-03.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** `monthly` presente com `reset_day` em `0`, `29`, ausente,
  `"last"`, `"ultimo"`, e nos extremos válidos `1` e `28`.
- **Passos:** validar cada variação.
- **Resultado esperado:** `0`, `29`, ausente e `"ultimo"` levantam
  `ConfigError` citando `...limits.monthly.reset_day`; `"last"`, `1` e `28`
  são aceitos.
- **Observações:** cobre RF-03. `29`/`30`/`31` são rejeitados como número fixo
  (só `1-28` ou o literal `"last"` — o contrato da issue exclui números que
  não existem em todo mês), preservando a correção em meses curtos.

### CT-A8 — Campo desconhecido e bloco com tipo incorreto são rejeitados

- **CA de origem:** derivado do padrão da casa (`validate_agent_circuit_break`
  rejeita campos desconhecidos).
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** (a) `limits: {daily: {limit: 10, foo: 1}}`; (b)
  `limits: {bar: {}}` no nível de período; (c) `limits: [1, 2]` (lista em vez
  de mapa).
- **Passos:** validar cada variação.
- **Resultado esperado:** todas levantam `ConfigError` citando o caminho do
  campo/bloco indevido.
- **Observações:** cobre a tabela "Comportamento em falha" (config inválida,
  "identificando a chave").

### CT-A9 — Validação é pura e ocorre antes de qualquer alteração de estado

- **CA de origem:** derivado da tabela "Comportamento em falha" ("processo não
  sobe com config inválida").
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** config com um valor inválido (ex.: `daily.limit: 0`);
  `tmp_path` sem nenhum arquivo `.pipe/*` pré-existente.
- **Passos:**
  1. Chamar a validação esperando `ConfigError`.
  2. Verificar que nenhum arquivo foi criado em `.pipe/`.
  3. Confirmar que a validação é chamada por `check_config`
     (`src/core/config.py`) antes de `InstanceLock.acquire`/qualquer mutação.
- **Resultado esperado:** `ConfigError` levantado; nenhum arquivo de estado
  criado; a validação está no caminho de `check_config` antes de qualquer
  escrita.
- **Observações:** espelha
  `test_agent_circuit_break_config.py::test_falha_antes_de_qualquer_alteracao_de_estado`.

### CT-A10 — Compatibilidade retroativa: configs existentes continuam íntegras

- **CA de origem:** derivado de RNF-05.
- **Tipo:** unitário/integração leve
- **Arquivo/alvo:** `tests/test_consumption_limit_config.py`
- **Pré-condição:** um `config: dict` completo e válido no formato atual
  (sem nenhuma seção `limits` em nenhuma plataforma), equivalente ao usado
  pelos testes de `config.py` já existentes.
- **Passos:** rodar a validação completa (`check_config`/pipeline de
  validação) sobre esse config.
- **Resultado esperado:** nenhum erro; nenhuma mudança de comportamento (a
  política resolvida para toda plataforma é inativa).
- **Observações:** cobre RNF-05 explicitamente.

---

## Grupo B — Acumulador e decisão de bloqueio

### CT-B1 — Bloqueio quando o consumo acumulado é EXATAMENTE igual ao limite

- **CA de origem:** CA-1 — "...quando o consumo acumulado do dia atinge ou
  ultrapassa o limite, então a próxima tentativa de acionar essa plataforma é
  impedida antes do agente."
- **Tipo:** unitário (núcleo do acumulador/decisão)
- **Arquivo/alvo:** `tests/test_consumption_limit.py` (novo)
- **Pré-condição:** `daily.limit = 100`; acumulado do dia, antes da próxima
  tentativa, igual a `100` (via execuções anteriores reportando consumo
  somado).
- **Passos:**
  1. Registrar execuções cujo consumo somado seja exatamente `100`.
  2. Avaliar a admissão da próxima tentativa.
- **Resultado esperado:** admissão **negada**; o agente não é despachado.
- **Observações:** fixa a fronteira "maior ou igual" (RN-02) — é o cenário
  mais sensível a off-by-one.

### CT-B2 — Bloqueio quando o consumo acumulado ULTRAPASSA o limite

- **CA de origem:** CA-1 (mesma origem; complementa a borda de CT-B1).
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** `daily.limit = 100`; acumulado = `150`.
- **Passos:** avaliar a admissão da próxima tentativa.
- **Resultado esperado:** admissão negada.
- **Observações:** complementa CT-B1/CT-B3 (três pontos da fronteira: abaixo,
  igual, acima).

### CT-B3 — Sem bloqueio quando o consumo acumulado está ABAIXO do limite

- **CA de origem:** CA-1 (fronteira complementar).
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** `daily.limit = 100`; acumulado = `99`.
- **Passos:** avaliar a admissão da próxima tentativa.
- **Resultado esperado:** admissão concedida.
- **Observações:** sem esta fronteira, uma implementação "maior que" em vez de
  "maior ou igual" passaria despercebida.

### CT-B4 — Sem política configurada, o comportamento é idêntico ao atual

- **CA de origem:** CA-2.
- **Tipo:** unitário/integração leve
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** plataforma sem `limits`; nenhuma restrição de consumo.
- **Passos:** avaliar a admissão de N tentativas consecutivas com qualquer
  volume de consumo acumulado.
- **Resultado esperado:** todas as tentativas são admitidas; nenhuma
  verificação de cota ocorre (nenhum log de bloqueio é emitido).
- **Observações:** cobre RN-01 — "bloqueio sem política configurada é defeito
  grave".

### CT-B5 — Execução já em andamento não é interrompida ao ultrapassar o limite

- **CA de origem:** CA-3 — "...quando ela ultrapassa o limite durante a
  execução, então ela não é interrompida e apenas a próxima tentativa é
  impedida."
- **Tipo:** integração (núcleo + adapter fake de execução longa)
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** `daily.limit = 100`; acumulado antes da execução = `90`;
  a execução em curso é ADMITIDA (90 < 100) e, ao concluir, reporta consumo
  de `50` (acumulado final = `140`, acima do limite).
- **Passos:**
  1. Avaliar a admissão da execução (deve admitir, pois 90 < 100).
  2. Simular a execução completa (adapter fake retorna sucesso + consumo 50).
  3. Avaliar a admissão da PRÓXIMA tentativa, após o acumulado atualizado.
- **Resultado esperado:** a execução em curso completa normalmente (não há
  mecanismo de interrupção no meio do caminho — o teste confirma que não
  existe chamada de cancelamento/kill); a execução seguinte é impedida, pois
  o acumulado (140) já é ≥ limite.
- **Observações:** cobre RN-03. O ponto central é que a decisão só acontece
  **antes** do próximo dispatch, nunca durante um já iniciado.

### CT-B6 — Isolamento entre plataformas na mesma instância

- **CA de origem:** CA-4 — "...quando outra plataforma da mesma instância é
  acionada e está abaixo do seu limite, então ela executa normalmente."
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** plataforma `A` bloqueada (acumulado ≥ limite); plataforma
  `B`, mesma instância, com seu próprio `limits` e acumulado abaixo do seu
  limite (ou sem `limits`).
- **Passos:**
  1. Avaliar a admissão de `A` (deve negar).
  2. Avaliar a admissão de `B` (deve admitir), usando um `AgentPort` fake de
     segunda plataforma (ver Convenções).
- **Resultado esperado:** `B` é admitida e executa normalmente; nenhum
  vazamento do acumulado/estado de `A` afeta a decisão de `B`.
- **Observações:** cobre RNF-02 (isolamento comprovável). Chave de estado por
  `(instância, plataforma, período)` é o contrato observável — não a forma
  exata da chave.

### CT-B7 — Isolamento entre instâncias (mesma plataforma)

- **CA de origem:** CA-5 — "...quando outra instância aciona a mesma
  plataforma, então ela não é afetada pelo acumulado da primeira."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** instância `1` com plataforma `kiro` bloqueada (acumulado ≥
  limite), persistida em seu `.pipe/` próprio; instância `2`, outro diretório
  de trabalho (`tmp_path` distinto), mesma plataforma `kiro`, sem nenhuma
  execução prévia.
- **Passos:**
  1. Bloquear a plataforma na instância 1 (seu próprio `.pipe/`).
  2. Em um diretório `.pipe/` isolado (instância 2), avaliar a admissão da
     mesma plataforma.
- **Resultado esperado:** a instância 2 admite normalmente — não herda
  acumulado nem bloqueio da instância 1.
- **Observações:** cobre RN-04. Como "instância" é implícita ao processo (o
  próprio arquivo de config em execução), o isolamento real neste código é
  por **diretório de estado** (`.pipe/` do processo) — o teste usa dois
  `tmp_path`/`chdir` distintos para simular duas instâncias.

### CT-B8 — Combinação de períodos: bloqueio por qualquer um, independente dos demais

- **CA de origem:** CA-11 — "Dado limites diário, semanal e mensal
  simultâneos, quando qualquer um deles é atingido, então o bloqueio ocorre
  independentemente dos demais."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** `daily.limit = 1000` (longe de ser atingido),
  `weekly.limit = 100` (acumulado da semana = 100, atingido),
  `monthly.limit = 5000` (longe de ser atingido).
- **Passos:** avaliar a admissão da próxima tentativa.
- **Resultado esperado:** admissão negada **pelo período semanal**; o registro
  estruturado da tentativa impedida identifica `periodo: "semanal"` (não
  diário nem mensal).
- **Observações:** cobre RF-02/CA-11 (issue CT-13). Variante complementar
  (parametrizada): repetir trocando qual período é o atingido (diário, depois
  mensal), confirmando que cada um bloqueia isoladamente.

### CT-B9 — Aumento do limite retoma o acionamento sem reinício do processo

- **CA de origem:** CA-7 — "...quando o operador aumenta ou desativa o
  limite, então o acionamento é retomado sem reinício do processo."
  (metade "aumenta").
- **Tipo:** integração (núcleo + reconfiguração em memória, sem restart)
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** `daily.limit = 100`, acumulado = `100` (bloqueado).
- **Passos:**
  1. Avaliar a admissão (negada).
  2. Sem reiniciar processo nem recriar nenhum objeto de estado persistido,
     reavaliar a admissão com um `config` atualizado (`daily.limit = 200`,
     mesmo acumulado `100`).
- **Resultado esperado:** a segunda avaliação admite a tentativa — o limite é
  lido do config vigente em cada avaliação, não congelado na primeira leitura.
- **Observações:** cobre RN-10. O teste é explícito em NÃO recriar/zerar o
  estado — só mudar o limite configurado.

### CT-B10 — Desativação do limite retoma o acionamento sem reinício do processo

- **CA de origem:** CA-7 (metade "desativa").
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** `daily.limit = 100`, acumulado = `100` (bloqueado).
- **Passos:**
  1. Avaliar a admissão (negada).
  2. Reavaliar com `limits` removido (ou `daily` removido) do config, mesmo
     acumulado persistido, sem reiniciar processo.
- **Resultado esperado:** admissão concedida — ausência de política vigente
  sempre admite, independentemente do acumulado histórico.
- **Observações:** cobre RN-10/RN-01.

### CT-B11 — Indisponibilidade de medição: falha aberta + registro distinto de zero

- **CA de origem:** CA-8 — "Dado que a plataforma não reporta consumo, quando
  ela é acionada, então a execução continua e um registro de indisponibilidade
  distinto de zero é gravado."
- **Tipo:** integração (núcleo + adapter fake retornando `Consumo.indisponivel`)
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** plataforma com `daily.limit` configurado e abaixo do
  limite; a execução retorna `Consumo(disponivel=False, valor=None, ...)`.
- **Passos:**
  1. Avaliar e admitir a execução.
  2. Executar (fake retorna indisponibilidade).
  3. Verificar o acumulado do período após a execução.
  4. Verificar o registro de indisponibilidade emitido.
- **Resultado esperado:** a execução ocorre normalmente (não é bloqueada por
  causa da indisponibilidade); o acumulado do período **não muda** (não soma
  zero nem qualquer valor); um registro estruturado `consumo_indisponivel` é
  emitido, distinto de um registro de consumo igual a `0`.
- **Observações:** cobre RN-06. Ver também CT-D4 (campos do registro) e
  CT-B13 (nunca confundir indisponível com zero no acumulador).

### CT-B12 — Persistência do acumulado entre ciclos ociosos do processo

- **CA de origem:** derivado de RNF-03/issue CT-15 — "Processo passa por ciclo
  ocioso entre execuções | Acumulado é restaurado sem perda."
- **Tipo:** integração (persistência + reconstrução de objeto do núcleo)
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** acumulado parcial do dia persistido em disco (`.pipe/...`)
  por uma "execução" anterior do processo.
- **Passos:**
  1. Registrar consumo e persistir o estado.
  2. Descartar qualquer instância em memória do núcleo (simulando reinício do
     processo sem apagar `.pipe/`).
  3. Recriar o núcleo a partir do estado em disco e avaliar a admissão de uma
     tentativa que só seria negada se o acumulado anterior estivesse
     presente.
- **Resultado esperado:** o acumulado é restaurado integralmente; a decisão
  de admissão reflete o histórico anterior ao ciclo ocioso.
- **Observações:** cobre RNF-03.

### CT-B13 — Unidade nativa nunca é convertida (não há soma entre unidades distintas)

- **CA de origem:** derivado de RN-05.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** execuções da mesma plataforma reportando a mesma unidade
  nativa (ex.: `"credit"`) ao longo do período.
- **Passos:**
  1. Acumular consumo de várias execuções com a mesma unidade.
  2. Verificar que o acumulado total é a soma aritmética simples dos valores,
     sem qualquer fator de conversão aplicado.
  3. (Robustez) Se uma execução chegasse com unidade divergente da já
     acumulada no período, verificar que o acumulador não mistura
     silenciosamente — registra/sinaliza a divergência em vez de somar como
     se fossem a mesma grandeza.
- **Resultado esperado:** soma exata, sem conversão; nenhuma mistura
  silenciosa de unidades divergentes.
- **Observações:** cobre RN-05. O terceiro passo é defensivo — a issue não
  prevê uma plataforma trocar de unidade em runtime, mas RN-05 exige que a
  unidade nativa nunca seja presumida/convertida.

### CT-B14 — Estado acumulado corrompido ou ausente na retomada: zera com segurança, não bloqueia indevidamente

- **CA de origem:** derivado da tabela "Comportamento em falha" — "Estado
  acumulado corrompido ou ausente na retomada".
- **Tipo:** integração (leitura de estado corrompido)
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** arquivo de estado do acumulador com JSON inválido/
  corrompido (ou ausente após remoção manual), com `limits` ativo e um
  acumulado qualquer que **teria** sido suficiente para bloquear se
  preservado.
- **Passos:**
  1. Corromper (ou remover) o arquivo de estado.
  2. Avaliar a admissão da próxima tentativa.
  3. Verificar o log de recuperação emitido.
- **Resultado esperado:** a admissão **não é negada** por causa da
  corrupção/ausência (zera e segue, fail-**aberto** — comportamento
  deliberadamente diferente do fail-closed de `agent_circuit_break` para
  estado corrompido); um registro estruturado de recuperação do acumulado é
  emitido, citando o motivo (corrompido/ausente).
- **Observações:** fixa a divergência de comportamento (fail-aberto) em
  relação ao molde `agent_circuit_break`/`sync_circuit_breaker` — decisão
  arquitetural explícita desta QA SR (RN-11/RN-06: ausência de teto absoluto
  e falha aberta são princípios do próprio domínio deste limitador).

### CT-B15 — Falha ao persistir o acumulado: consumo não é perdido silenciosamente

- **CA de origem:** derivado da tabela "Comportamento em falha" — "Adapter
  reporta consumo, mas a persistência do acumulado falha".
- **Tipo:** integração (falha de I/O simulada)
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** execução concluída reportando consumo válido; a escrita do
  estado (`save`-equivalente) é forçada a falhar (ex.: `monkeypatch` no
  `os.replace`/permissão do diretório).
- **Passos:**
  1. Executar e obter o consumo reportado.
  2. Tentar persistir o acumulado atualizado (falha simulada).
  3. Verificar o log emitido.
- **Resultado esperado:** a falha de persistência é registrada de forma
  acionável (nunca engolida em silêncio); a execução que já ocorreu não é
  revertida nem perde o seu `ExecutionRecord` (#307) por causa dessa falha —
  mesmo padrão fail-safe de `_write_execution_record`.
- **Observações:** cobre a tabela de falha. Não exige que a esteira pare —
  exige que a falha seja visível.

---

## Grupo C — Reset temporal e fuso

### CT-C1 — Reset diário na virada do dia

- **CA de origem:** CA-6 (recorte diário) — issue CT-06.
- **Tipo:** unitário (relógio controlável)
- **Arquivo/alvo:** `tests/test_consumption_limit_reset.py` (novo)
- **Pré-condição:** `daily.limit` atingido no dia `D`; relógio avançado para
  `D+1 00:00:00` (fuso configurado ou local).
- **Passos:**
  1. Bloquear a plataforma no dia `D`.
  2. Avançar o relógio controlado para a virada de `D` para `D+1`.
  3. Avaliar a admissão.
- **Resultado esperado:** acumulado do dia volta a `0`; admissão concedida
  (salvo se outro período também estiver atingido).
- **Observações:** cobre RF-11 (parte diária).

### CT-C2 — Reset semanal no dia da semana configurado

- **CA de origem:** CA-6 (recorte semanal) — issue CT-07.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_reset.py`
- **Pré-condição:** `weekly.limit` atingido; `reset_weekday` configurado (ex.:
  segunda-feira = `0`); relógio avançado até o próximo dia de reinício.
- **Passos:** avançar o relógio até o `reset_weekday` seguinte e avaliar a
  admissão.
- **Resultado esperado:** acumulado semanal zera exatamente no dia
  configurado (não um dia antes nem depois); admissão concedida.
- **Observações:** cobre RF-03/RF-11 (parte semanal). Parametrizado nos 7
  valores de `reset_weekday`.

### CT-C3 — Reset mensal no dia do mês configurado

- **CA de origem:** CA-6 (recorte mensal) — issue CT-08.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_reset.py`
- **Pré-condição:** `monthly.limit` atingido; `reset_day` = `15`; relógio
  avançado até o dia 15 do mês seguinte.
- **Passos:** avançar o relógio até o `reset_day` e avaliar a admissão.
- **Resultado esperado:** acumulado mensal zera no dia configurado; admissão
  concedida.
- **Observações:** cobre RF-03/RF-11 (parte mensal).

### CT-C4 — Reset mensal com `reset_day: "last"` em meses de tamanhos diferentes

- **CA de origem:** CA-6 (derivado do risco "meses com menos dias").
- **Tipo:** unitário, parametrizado
- **Arquivo/alvo:** `tests/test_consumption_limit_reset.py`
- **Pré-condição:** `monthly.reset_day = "last"`; testar em fevereiro de ano
  não-bissexto (28), fevereiro bissexto (29), mês de 30 dias e mês de 31 dias.
- **Passos:** para cada mês, avançar o relógio até o último dia daquele mês
  específico e avaliar o reset.
- **Resultado esperado:** o reset ocorre no último dia real do mês em cada
  variação — nunca no dia 28/30/31 fixo quando o mês tem outra quantidade de
  dias.
- **Observações:** cobre o risco explícito da issue ("uso de 'last' para o dia
  mensal"); parametrizado (4 sub-casos).

### CT-C5 — Marcos respeitam o fuso configurado explicitamente

- **CA de origem:** CA-10 (parte 1) — issue CT-09.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_reset.py`
- **Pré-condição:** `timezone: "America/Sao_Paulo"` (UTC-3, sem DST desde
  2019); limite diário atingido; relógio controlado representando um instante
  UTC específico, próximo da meia-noite em São Paulo mas não da meia-noite em
  UTC.
- **Passos:** avaliar a admissão em um instante que é "antes da virada" em
  UTC mas "depois da virada" em `America/Sao_Paulo`, e vice-versa.
- **Resultado esperado:** o reset ocorre na virada do dia **no fuso
  configurado**, não em UTC nem no fuso local do processo.
- **Observações:** cobre RF-04/RNF-04.

### CT-C6 — Marcos respeitam o fuso local da máquina quando `timezone` é omitido

- **CA de origem:** CA-10 (parte 2) — issue CT-09.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit_reset.py`
- **Pré-condição:** `limits` sem `timezone`; fuso do processo de teste
  controlado via variável de ambiente `TZ` (ou injeção equivalente) para dois
  fusos distintos entre execuções do mesmo caso.
- **Passos:** repetir a avaliação do reset diário com `TZ` setado para dois
  fusos diferentes, mesmo instante UTC.
- **Resultado esperado:** o instante do reset acompanha o fuso local
  configurado no ambiente em cada execução — confirma que o fallback usa o
  fuso **da máquina**, não um fuso fixo embutido no código.
- **Observações:** cobre RF-04 ("ausente = fuso local da máquina").

### CT-C7 — Fuso/relógio indisponível em runtime cai para o fuso local e registra o fallback

- **CA de origem:** derivado da tabela "Comportamento em falha" — "Relógio/
  fuso indisponível para calcular marco de reset".
- **Tipo:** unitário (falha simulada na resolução do fuso)
- **Arquivo/alvo:** `tests/test_consumption_limit_reset.py`
- **Pré-condição:** `timezone` configurado para um identificador que a
  resolução de fuso em runtime não consegue carregar (ex.: biblioteca de fuso
  indisponível, simulada via `monkeypatch` que faz a função de resolução de
  fuso levantar exceção).
- **Passos:** avaliar o cálculo do próximo marco de reset nessa condição.
- **Resultado esperado:** o cálculo usa o fuso local da máquina como
  fallback (não derruba a avaliação de admissão); um registro estruturado do
  uso do fallback é emitido.
- **Observações:** cobre a tabela de falha. Distinto de CT-A4 (que é erro de
  **configuração**, rejeitado na carga) — aqui a configuração era válida, mas
  a resolução em runtime falhou.

> **Nota sobre DST:** a issue cita "mudanças de fuso/horário de verão" como
> ponto de atenção. `America/Sao_Paulo` não observa DST desde 2019, então
> CT-C5 não exercita a transição em si. Recomenda-se ao desenvolvimento um
> caso adicional (não obrigatório para fechar esta especificação, pois a
> issue não define um fuso-alvo com DST vigente) usando um fuso que ainda
> observa DST (ex.: `America/New_York`) nas datas de transição, se a
> implementação usar aritmética de tempo sensível a DST.

---

## Grupo D — Observabilidade da tentativa impedida e da indisponibilidade

### CT-D1 — Tentativa impedida emite aviso no terminal

- **CA de origem:** CA-9 — "...há aviso no terminal e no arquivo de log..."
- **Tipo:** unitário (captura de saída)
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** plataforma bloqueada (acumulado ≥ limite).
- **Passos:** avaliar a admissão (negada) e capturar a saída de terminal do
  logger (`capsys` ou equivalente).
- **Resultado esperado:** uma linha de aviso (nível `warning`/`error`,
  seguindo o padrão de `SyncCircuitBreaker`/`CircuitBreak`) aparece no
  terminal, mencionando a plataforma e o motivo do bloqueio.
- **Observações:** cobre RF-09 (metade terminal).

### CT-D2 — Tentativa impedida emite aviso no arquivo de log

- **CA de origem:** CA-9 (metade arquivo).
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** mesma de CT-D1.
- **Passos:** avaliar a admissão (negada); ler `logs/<data>.json` e localizar
  o evento.
- **Resultado esperado:** uma entrada estruturada é gravada no arquivo de
  log, com o evento identificável (ex.: `event: "consumo_limite_bloqueio"`).
- **Observações:** cobre RF-09 (metade arquivo). Reaproveita o padrão
  `read_events` de `test_sync_circuit_breaker.py`.

### CT-D3 — Registro estruturado da tentativa impedida contém todos os campos exigidos

- **CA de origem:** CA-9 — "...um registro estruturado com instância,
  plataforma, unidade, consumo, limite, período e condição de retomada."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** plataforma bloqueada pelo período diário, com `timezone`
  configurado.
- **Passos:** avaliar a admissão (negada) e inspecionar o registro estruturado
  emitido.
- **Resultado esperado:** o registro contém, no mínimo, os sete campos do
  contrato da issue:
  `instancia`, `plataforma`, `unidade`, `consumo_periodo`, `limite`,
  `periodo` (um de `diario|semanal|mensal`) e `condicao_retomada` (string
  explicando quando retomará — ex.: horário do próximo reset ou "aumento/
  desativação do limite"); mais `event: "consumo_limite_bloqueio"` e
  `timestamp` em ISO-8601 com fuso.
- **Observações:** cobre RN-08. Verificar explicitamente que nenhum campo é
  `None`/ausente quando deveria estar presente.

### CT-D4 — Registro de indisponibilidade: campos completos, distinto de zero, sem segredo

- **CA de origem:** CA-8 (campos do registro) + derivado de RNF-06.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_consumption_limit.py`
- **Pré-condição:** execução cujo adapter retorna `Consumo.indisponivel(...)`.
- **Passos:**
  1. Executar e provocar o registro de indisponibilidade.
  2. Inspecionar o registro estruturado emitido.
  3. Verificar que nenhum valor de `consumo`/`valor` aparece no registro (é
     omitido, não zerado — mesma invariante de `Consumo.to_dict`).
  4. Verificar que nenhum token/credencial de ambiente aparece no registro,
     mesmo que presente nas variáveis de ambiente do processo durante o
     teste.
- **Resultado esperado:** o registro contém `event: "consumo_indisponivel"`,
  `instancia`, `plataforma`, `motivo` e `timestamp`; nunca contém `valor`
  nem segredos.
- **Observações:** cobre RN-06/RNF-06.

---

## Grupo E — Integração do gate pré-agente (`call_agent`)

### CT-E1 — Plataforma bloqueada: o agente NÃO é despachado

- **CA de origem:** CA-1 (fim-a-fim, ponto de inserção em `call_agent`).
- **Tipo:** integração (`src/__main__.py::call_agent` + adapter fake espião)
- **Arquivo/alvo:** `tests/test_consumption_limit_integration.py` (novo)
- **Pré-condição:** plataforma `kiro` bloqueada (acumulado ≥ `daily.limit`);
  uma `task` elegível para essa plataforma/agente; `AgentPort` fake que
  registra chamadas a `execute`.
- **Passos:** chamar `call_agent(config, task)`.
- **Resultado esperado:** `adapter.execute` **nunca** é chamado; `call_agent`
  retorna sem erro (mesmo padrão de retorno antecipado de
  `_admit_circuit_break`/composição em camadas); nenhum `ExecutionRecord` de
  execução real é gravado para esta tentativa (o bloqueio acontece antes do
  dispatch, não é uma execução que falhou).
- **Observações:** cobre RF-08 no ponto de integração real, não só no núcleo
  isolado (complementa CT-B1).

### CT-E2 — Plataforma liberada: despacho normal, sem chamada de rede síncrona extra

- **CA de origem:** derivado de RNF-01.
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_consumption_limit_integration.py`
- **Pré-condição:** plataforma abaixo do limite; `AgentPort` fake espião que
  também conta quantas "chamadas externas" (ex.: requisições de rede
  simuladas) o gate de decisão realiza.
- **Passos:** chamar `call_agent(config, task)` e inspecionar o fake.
- **Resultado esperado:** `adapter.execute` é chamado normalmente; a decisão
  de bloqueio não realizou nenhuma chamada de rede síncrona ao provedor —
  usa somente estado local acumulado (arquivo/estrutura em memória).
- **Observações:** cobre RNF-01. A verificação é por contagem de chamadas no
  fake/espião, não por medição de tempo (evita teste frágil por performance).

### CT-E3 — 100% das tentativas após o reconhecimento do bloqueio são impedidas

- **CA de origem:** derivado de RN-09.
- **Tipo:** integração, robustez
- **Arquivo/alvo:** `tests/test_consumption_limit_integration.py`
- **Pré-condição:** plataforma bloqueada; N tentativas consecutivas de
  despacho (`call_agent`) para a mesma plataforma, sem qualquer reset entre
  elas.
- **Passos:** chamar `call_agent` N vezes (ex.: `N=10`) seguidas.
- **Resultado esperado:** nenhuma das N chamadas despacha o adapter —
  nenhuma passa pela verificação (zero falsos negativos de bloqueio).
- **Observações:** cobre RN-09 ("nunca há acionamento após decisão de
  bloqueio").

---

## Grupo F — Métricas do baseline do primeiro ciclo

### CT-F1 — Os registros emitidos contêm os campos suficientes para o baseline

- **CA de origem:** CA-12 — "Dado o fim do primeiro ciclo, então há dados
  registrados suficientes para publicar excedente da última execução,
  indisponibilidade, bloqueios, falsos bloqueios, tempo de retomada e impacto
  em trabalho prioritário."
- **Tipo:** integração (schema/completude dos registros, não o cálculo da
  métrica — publicação de baseline é responsabilidade de quem implanta,
  fora de escopo)
- **Arquivo/alvo:** `tests/test_consumption_limit_integration.py`
- **Pré-condição:** um ciclo simulado contendo: (a) uma execução cujo consumo
  final ultrapassa o limite (para excedente da última execução); (b) uma
  execução com indisponibilidade de medição; (c) ao menos um bloqueio; (d)
  um reset de período seguido de retomada (para tempo até retomada); (e)
  informação de prioridade de board/issue disponível no contexto da
  tentativa impedida.
- **Passos:** Para cada métrica do contrato (excedente, indisponibilidade,
  bloqueios, falsos bloqueios, tempo de retomada, impacto em trabalho
  prioritário), identificar e extrair, a partir SOMENTE dos registros
  estruturados emitidos (`consumo_limite_bloqueio`, `consumo_indisponivel`,
  consumo por execução já capturado por #307), os dados brutos necessários
  para computá-la.
- **Resultado esperado:** para cada uma das seis métricas, existe ao menos um
  campo/combinação de campos nos registros emitidos por este trabalho (ou já
  emitidos por #307) a partir do qual a métrica é calculável sem necessidade
  de dado adicional não registrado. Especificamente:
  - **excedente da última execução:** `consumo_periodo` do bloqueio
    subsequente menos `limite`, OU o consumo da execução que ultrapassou
    menos o limite vigente;
  - **indisponibilidade:** contagem de registros `consumo_indisponivel`;
  - **bloqueios:** contagem de registros `consumo_limite_bloqueio`;
  - **falsos bloqueios:** registros de bloqueio em que, após investigação,
    não havia consumo real suficiente (o campo `consumo_periodo` do registro
    permite auditar isso a posteriori, comparando com a fonte de verdade de
    #307);
  - **tempo de retomada:** diferença entre o `timestamp` do bloqueio e o
    `timestamp` da execução seguinte admitida para a mesma
    `(instancia, plataforma, periodo)`;
  - **impacto em trabalho prioritário:** cruzamento de `board`/prioridade do
    `task` bloqueado (disponível no contexto de `call_agent`, mesmo que não
    vá para o registro de consumo) com os registros de bloqueio.
- **Observações:** cobre RF-14. Este caso verifica **completude de dados**,
  não a geração de um relatório/painel (explicitamente fora de escopo). Se
  algum campo necessário não existir nos registros, o caso de teste deve
  falhar citando qual métrica ficou sem insumo — é o único caso em que a
  ausência de um campo é, em si, o resultado observável sob teste.

---

## Mapa: CT da issue (corpo #311) → casos deste documento

| CT da issue | Cenário | Caso(s) deste documento |
|---|---|---|
| CT-01 | Bloqueio no limite diário | CT-B1, CT-E1 |
| CT-02 | Sem política, sem mudança | CT-A1, CT-B4 |
| CT-03 | Execução em andamento não interrompida | CT-B5 |
| CT-04 | Isolamento entre plataformas | CT-B6 |
| CT-05 | Isolamento entre instâncias | CT-B7 |
| CT-06 | Reset diário | CT-C1 |
| CT-07 | Reset semanal | CT-C2 |
| CT-08 | Reset mensal | CT-C3, CT-C4 |
| CT-09 | Fuso configurado vs. local | CT-C5, CT-C6 |
| CT-10 | Aumento de limite retoma | CT-B9 |
| CT-11 | Desativação de limite retoma | CT-B10 |
| CT-12 | Indisponibilidade de medição | CT-B11, CT-D4 |
| CT-13 | Combinação de períodos | CT-B8 |
| CT-14 | Config inválida | CT-A4 a CT-A8 |
| CT-15 | Persistência do acumulado | CT-B12 |

---

## Decisão sobre o escopo

O escopo da issue #311 está completo e internamente consistente para a
derivação destes casos: os 12 critérios de aceitação e os 15 cenários
obrigatórios do Detalhamento são testáveis isoladamente, o contrato de
configuração e os formatos de registro estão especificados por completo
(exemplos YAML/JSON no corpo da issue), e os pontos de integração
(`call_agent`, `execution_record`, adapter Kiro) já existem e foram
localizados no código atual. Não há contradição nem lacuna que exija devolver
a issue ao planejamento — a especificação avança para o desenvolvimento.

— Camila Rocha - Engenheira de Qualidade SR
