# Casos de Teste — Timeout de execução do agente configurável via pipe.yml (default 3600s)

- **Issue:** #337
- **Story relacionada:** tornar o timeout de execução do agente (hoje
  `_TIMEOUT = 3600` hardcoded em `src/adapters/kiro_cli_agent.py`) configurável
  por pipe via `pipe.yml`, preservando 3600s como default
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-11-04
- **Branch:** `feature/337-timeout_de_execucao_do_agente_configuravel_via_pipeyml_default_3600s`

> Todo caso de teste é vinculado a um critério de aceitação (CA) da issue
> #337. Nenhum caso existe sem CA de origem. Cada caso tem resultado esperado
> explícito e verificável. Os testes são da suíte Python do motor (pytest, em
> `tests/`).

---

## Contexto de arquitetura (baseline do código atual)

Levantamento feito em `/app/repo/main` antes de especificar os casos:

- `src/adapters/kiro_cli_agent.py` define `_TIMEOUT = 3600` (linha 22), módulo
  (global ao processo, não por `AgentParams`/instância). O valor é usado em
  dois pontos de `KiroCliAgent._run`:
  - `subprocess.run(cmd, ..., timeout=_TIMEOUT, ...)`;
  - na captura de `subprocess.TimeoutExpired`, a string retornada
    `f"[TIMEOUT] Agente excedeu {_TIMEOUT}s"` — essa string é o marcador
    estrutural que `_classify`/`_detect_failure` reconhecem como
    `UNKNOWN_OUTCOME` (`"[TIMEOUT]"` em `_classify`, origem `"timeout"`). Os
    dois usos de `_TIMEOUT` precisam refletir o MESMO valor efetivo resolvido.
- `src/core/config.py` não possui hoje nenhuma validação de chave de timeout
  na raiz do `pipe.yml`. O padrão da casa para chaves opcionais de raiz
  (`retry`, `registro`, `safety`, `agent_circuit_break`) é: função
  `validate_<bloco>(config)` chamada em `check_config()` antes de qualquer
  alteração de estado, levantando `ConfigError` citando o caminho do campo;
  `bool` é rejeitado ANTES de `int` (`True`/`False` são instâncias de `int`
  em Python — ver `validate_retry`/`validate_registro`); e uma função
  `resolve_<bloco>(config)` companheira que aplica o default quando a chave
  está ausente, sem revalidar.
- `AgentParams` (`src/core/agent.py`) é o dataclass que viaja de
  `call_agent` (`src/__main__.py`) até `KiroCliAgent.execute`/`_run`; hoje não
  tem campo de timeout. `KiroCliAgent()` é instanciado sem argumentos em
  `call_agent` (`adapter = KiroCliAgent()`). A propagação do valor validado do
  `pipe.yml` até `_run` é decisão do desenvolvimento (via `AgentParams`,
  construtor do adapter, ou outro ponto), desde que:
  - o valor citado na issue (`agent_timeout_seg`) seja resolvido uma única vez
    a partir da config carregada (mesmo padrão de `resolve_retry`/
    `resolve_registro`);
  - a ausência da chave preserve bit a bit o comportamento atual (3600s em
    ambos os usos).
- Não há, na suíte atual, nenhum teste que fixe o valor de `_TIMEOUT` passado a
  `subprocess.run` nem o texto da mensagem `[TIMEOUT]` como contrato explícito
  — é lacuna de cobertura preexistente que esta entrega passa a cobrir
  (CT-01/CT-02), e não regressão.

> **Decisão de implementação — NÃO fixada pela QA (é do desenvolvimento):** o
> nome do parâmetro/atributo interno usado para carregar o valor do
> `AgentParams`/adapter (ex.: `timeout_seg`, `agent_timeout`) e o mecanismo
> exato de propagação. Os casos abaixo testam o **comportamento observável**
> (validação do `pipe.yml`, valor efetivo passado ao `subprocess.run`, texto da
> mensagem de timeout) e, apenas quando necessário para isolar a unidade,
> citam os símbolos já existentes e estáveis hoje (`validate_*`/`resolve_*`,
> `KiroCliAgent._run`, `AgentParams`). Se o desenvolvimento adotar outro nome
> de chave de dataclass/parâmetro, o caso vale sobre o comportamento
> equivalente.

---

## Rastreabilidade (CA → casos)

| Critério de aceitação | Caso(s) de teste |
|------------------------|-------------------|
| CA-1 — ausência da chave → timeout efetivo 3600s no `subprocess.run` | CT-01, CT-05 |
| CA-2 — `agent_timeout_seg: 7200` → `subprocess.run` usa 7200s e `[TIMEOUT]` registra 7200s | CT-02, CT-03 |
| CA-3 — valor inválido (`<= 0` ou não inteiro) → `ConfigError` citando a chave, na validação, antes de qualquer execução | CT-04, CT-04b, CT-04c, CT-04d |
| CA-4 — chave ausente → validação do `pipe.yml` passa e valor efetivo assumido é 3600 | CT-05, CT-05b |

---

## Casos de teste

### CT-01 — `subprocess.run` recebe `timeout=3600` quando a chave está ausente

- **CA de origem:** CA-1 (ausência da chave → timeout aplicado ao
  `subprocess.run` é 3600s — comportamento atual preservado)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_kiro_cli_agent_timeout.py::...` (novo arquivo;
  ou outro já existente para o adapter, à critério do desenvolvimento) —
  exercita `KiroCliAgent._run` com `subprocess.run` mockado
- **Pré-condição:** `AgentParams`/config resultante da resolução SEM a chave
  `agent_timeout_seg` no `pipe.yml` em memória (dict de config sem a chave na
  raiz)
- **Passos:**
  1. Montar `AgentParams` a partir de uma config sem `agent_timeout_seg`.
  2. Mockar `subprocess.run` (capturando os kwargs recebidos) para retornar um
     resultado de sucesso simples.
  3. Chamar `KiroCliAgent()._run(params, work_dir)` (ou o ponto de entrada
     equivalente que o desenvolvimento expuser).
- **Resultado esperado:** o kwarg `timeout` recebido por `subprocess.run` é
  exatamente `3600` (int).
- **Observações:** replica o padrão de mock já usado em
  `tests/test_consumo_stream_json.py::TestRunCapturaConsumo` (`patch(
  "subprocess.run", side_effect=fake_run)` capturando `cmd`/`kwargs`).

### CT-02 — `subprocess.run` recebe `timeout=7200` quando `agent_timeout_seg: 7200`

- **CA de origem:** CA-2 (valor configurado → `subprocess.run` usa esse
  timeout)
- **Tipo:** unitário
- **Arquivo/alvo:** mesmo arquivo de CT-01
- **Pré-condição:** config com `agent_timeout_seg: 7200` na raiz, já validada
  e resolvida
- **Passos:**
  1. Montar `AgentParams`/adapter a partir de uma config com
     `agent_timeout_seg: 7200`.
  2. Mockar `subprocess.run` capturando os kwargs.
  3. Executar `_run`.
- **Resultado esperado:** o kwarg `timeout` recebido por `subprocess.run` é
  exatamente `7200` (int), e **não** `3600`.
- **Observações:** garante que o valor configurado de fato substitui o
  default, não apenas que o default funciona (complementa CT-01).

### CT-03 — mensagem `[TIMEOUT]` registra o valor configurado, não o default antigo

- **CA de origem:** CA-2 (a mensagem `[TIMEOUT]` deve refletir o valor
  efetivamente configurado quando a execução excede esse tempo)
- **Tipo:** unitário
- **Arquivo/alvo:** mesmo arquivo de CT-01/CT-02
- **Pré-condição:** config com `agent_timeout_seg: 7200`
- **Passos:**
  1. Montar `AgentParams`/adapter a partir de uma config com
     `agent_timeout_seg: 7200`.
  2. Mockar `subprocess.run` com `side_effect=subprocess.TimeoutExpired(cmd=...,
     timeout=7200)` (simula o estouro do timeout configurado).
  3. Executar `_run` e capturar a string retornada.
- **Resultado esperado:** a string retornada é exatamente
  `"[TIMEOUT] Agente excedeu 7200s"` — contém `7200`, não `3600`.
- **Observações:** cobre a segunda metade do CA-2, que CT-02 não cobre
  (mensagem, não só o kwarg). Sem este caso, uma implementação que
  propagasse o valor só para `subprocess.run` (esquecendo a string) passaria
  incorretamente. Esta string é consumida por `_classify` (
  `"[TIMEOUT]" in clean` → `UNKNOWN_OUTCOME`, origem `"timeout"`); confirmar
  também, neste caso ou em caso complementar, que a classificação por
  `_classify`/`_detect_failure` continua reconhecendo `UNKNOWN_OUTCOME`
  independente do número — a regra é a presença do marcador `[TIMEOUT]`, não
  o valor numérico nele contido (sem regressão na detecção de falha por
  canais estruturados, issue #303).

### CT-04 — `agent_timeout_seg` não positivo (`0` ou negativo) é rejeitado na validação

- **CA de origem:** CA-3 (valor inválido → `ConfigError` citando a chave, antes
  de qualquer execução de agente)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_agent_timeout_config.py::...` (novo arquivo,
  seguindo o padrão de `tests/test_project_config.py`/testes de
  `validate_retry`) — exercita a função de validação em `src/core/config.py`
- **Pré-condição:** dict de config com `agent_timeout_seg: 0` (e variante
  `agent_timeout_seg: -10`)
- **Passos:**
  1. Chamar a função de validação da chave (`validate_<bloco>` ou
     equivalente) com a config de pré-condição.
- **Resultado esperado:** levanta `ConfigError` cuja mensagem cita a chave
  `agent_timeout_seg`. Testar `0` e um valor negativo (dois asserts/dois
  testes parametrizados).
- **Observações:** segue o padrão de `validate_retry`/`validate_registro` —
  `ConfigError` nomeando o caminho do campo.

### CT-04b — `agent_timeout_seg` não inteiro (float ou string) é rejeitado na validação

- **CA de origem:** CA-3 (valor inválido — "não inteiro" é condição explícita
  do CA)
- **Tipo:** unitário
- **Arquivo/alvo:** mesmo arquivo de CT-04
- **Pré-condição:** config com `agent_timeout_seg: 3600.0` e, em teste
  separado, `agent_timeout_seg: "3600"`
- **Passos:**
  1. Chamar a função de validação com cada valor de pré-condição.
- **Resultado esperado:** levanta `ConfigError` citando a chave
  `agent_timeout_seg` em ambos os casos (float e string não são aceitos,
  mesmo representando um número positivo).
- **Observações:** mesmo espírito de `validate_retry.max_tentativas`, que
  rejeita float para um campo que exige inteiro.

### CT-04c — `agent_timeout_seg: true`/`false` (bool) é rejeitado na validação

- **CA de origem:** CA-3 (valor inválido — "não inteiro"; bool é instância de
  int em Python e precisa de rejeição explícita, replicando o padrão da casa)
- **Tipo:** unitário
- **Arquivo/alvo:** mesmo arquivo de CT-04
- **Pré-condição:** config com `agent_timeout_seg: True`
- **Passos:**
  1. Chamar a função de validação com a config de pré-condição.
- **Resultado esperado:** levanta `ConfigError` citando a chave
  `agent_timeout_seg` (bool não é aceito como valor válido, mesmo
  `True == 1`).
- **Observações:** replica o teste que já existe para
  `retry.max_tentativas`/`registro.retencao_dias` — `bool` é rejeitado ANTES
  da checagem de `int`, pois em Python `isinstance(True, int)` é `True`.

### CT-04d — validação de `agent_timeout_seg` inválido ocorre antes de qualquer execução de agente

- **CA de origem:** CA-3 ("antes de qualquer execução de agente")
- **Tipo:** unitário/integração
- **Arquivo/alvo:** mesmo arquivo de CT-04, ou
  `tests/test_agent_timeout_config.py` integrando com `check_config()`
- **Pré-condição:** `pipe.yml` (ou dict equivalente passado a `check_config`)
  válido em todos os outros aspectos, exceto `agent_timeout_seg: -1` na raiz
- **Passos:**
  1. Chamar `check_config()` (ou a função de validação de topo) sobre essa
     config.
- **Resultado esperado:** `check_config()` levanta `ConfigError` (citando
  `agent_timeout_seg`) e nenhuma chamada de execução de agente ocorre — a
  validação falha antes do `main()` chegar ao loop (mesma garantia que as
  demais chaves opcionais de raiz já têm: `validate_retry`, `validate_registro`
  etc. rodam dentro de `check_config()`, que roda antes de `InstanceLock.acquire`
  em `main()`).
- **Observações:** se o desenvolvimento optar por testar só a função
  `validate_<bloco>` isoladamente (como CT-04/CT-04b/CT-04c), este caso garante
  adicionalmente que ela está de fato registrada dentro de `check_config()` —
  evita o caso de uma validação escrita mas nunca chamada.

### CT-05 — chave ausente: validação passa e o valor efetivo resolvido é 3600

- **CA de origem:** CA-4 (chave ausente → validação passa normalmente e valor
  efetivo assumido é 3600)
- **Tipo:** unitário
- **Arquivo/alvo:** mesmo arquivo de CT-04
- **Pré-condição:** config sem a chave `agent_timeout_seg` na raiz
- **Passos:**
  1. Chamar a função de validação (`validate_<bloco>`) com a config de
     pré-condição — não deve levantar.
  2. Chamar a função de resolução (`resolve_<bloco>`) com a mesma config.
- **Resultado esperado:** a validação não levanta `ConfigError`; a resolução
  retorna exatamente `3600` (int).
- **Observações:** caso espelha `validate_retry`/`resolve_retry` quando
  `retry` está ausente. Cobre a mesma condição de CT-01, mas na camada de
  config (resolução), não na chamada ao `subprocess.run` — as duas são
  necessárias porque a propagação entre `config.py` e `kiro_cli_agent.py`
  é o que a issue pede para corrigir (hoje não existe elo algum).

### CT-05b — chave presente com valor válido: validação passa e resolução retorna o valor configurado

- **CA de origem:** CA-2/CA-4 (confirma simetricamente que a resolução
  funciona para valor presente, não só para ausência)
- **Tipo:** unitário
- **Arquivo/alvo:** mesmo arquivo de CT-04
- **Pré-condição:** config com `agent_timeout_seg: 7200` (valor válido, `> 0`,
  inteiro)
- **Passos:**
  1. Chamar a função de validação — não deve levantar.
  2. Chamar a função de resolução.
- **Resultado esperado:** a validação não levanta; a resolução retorna
  exatamente `7200` (int).
- **Observações:** completa a matriz de CT-04/CT-04b/CT-04c/CT-05 (valor
  inválido vs. ausente vs. presente e válido).

### CT-06 — valor mínimo válido (`agent_timeout_seg: 1`) é aceito

- **CA de origem:** CA-3 (contorno da regra `> 0` — `1` é o menor inteiro
  positivo e deve ser aceito, não só valores "grandes" como 7200)
- **Tipo:** unitário
- **Arquivo/alvo:** mesmo arquivo de CT-04
- **Pré-condição:** config com `agent_timeout_seg: 1`
- **Passos:**
  1. Chamar a função de validação — não deve levantar.
  2. Chamar a função de resolução.
- **Resultado esperado:** validação não levanta `ConfigError`; resolução
  retorna `1`.
- **Observações:** caso de contorno (boundary) complementar a CT-04 (que testa
  `0`, já inválido). Garante que a regra implementada é estritamente `> 0`
  (não `>= algum mínimo operacional maior).

---

## Observações gerais de execução

- Os testes dos canais estruturados de falha (`_classify`/`_detect_failure`,
  issue #303) já cobertos em `tests/test_execucao_autonoma_confiavel.py` e
  `tests/test_agent_failure_detection.py` **não são alterados** por esta
  entrega — apenas o valor numérico dentro do marcador `[TIMEOUT]` passa a
  variar; a presença do marcador continua sendo o único sinal relevante.
  Nenhum teste existente deve precisar mudar para este escopo passar; se
  algum teste atual fixar literalmente `3600` fora do contexto de "valor
  default ausente", é sinal de acoplamento indevido a investigar no
  desenvolvimento, não objetivo desta entrega.
- Fora de escopo (conforme a issue): timeout por coluna/etapa, mudança do
  valor efetivo em pipe já em produção, e timeouts de preflight/`gh` (15s) —
  nenhum caso acima testa essas dimensões.
