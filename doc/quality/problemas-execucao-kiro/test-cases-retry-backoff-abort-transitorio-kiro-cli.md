# Casos de Teste — Avaliar e implementar retry com backoff para abort transitório do kiro-cli (dispatch failure / InternalServerError)

Status: draft
Owner: quality
Last updated: 2026-08-25

## Inputs

- Task #208 — Avaliar e implementar retry com backoff para abort transitório
  do kiro-cli (`dispatch failure`/`InternalServerError`) (board `task`, etapa
  Casos de Teste)
- ADR normativa: `doc/architecture/retry-kiro-cli/idempotencia.md` (decisão
  registrada na resolução do débito #217, commits `d1316e7`/`4c27204`,
  mesclada em `main` pelo MR #218 — **ainda não mesclada em `epic`** no
  momento desta escrita; conteúdo consistente com o body atual de #208, que
  incorpora o mesmo contrato após o alinhamento pós-review)
- Incidente de origem: #203 — Problemas na execução do kiro (defeito **D1**,
  correção **C4**), `doc/incidente/problemas-execucao-kiro/ticket.md`
- Bug upstream referenciado: [kirodotdev/Kiro#6065](https://github.com/kirodotdev/Kiro/issues/6065)
  (fechado como "not planned")
- Log de referência do abort real: `logs/175/2026-08-24_20-38-06.md` (citado
  no body; não verificado nesta etapa — pertence ao ambiente de execução, não
  ao repositório)
- Código sob teste: `KiroCliAgent.execute`/`_run`/`_detect_failure`
  (`src/adapters/kiro_cli_agent.py`)
- Suítes existentes a não regredir: `tests/test_agent_failure_detection.py`,
  `tests/test_error_classification.py`, `tests/test_agent_log_descritivo.py`
  (esta última já tem falhas pré-existentes não relacionadas a #208 — ver
  "Resultado da execução")

## Contexto da verificação

**Mudança de contrato em relação ao título da issue:** o título de #208 e o
texto informal deste prompt mencionam "retry com backoff". A ADR (seção 2,
"Consequência para #208" e "Contrato normativo de entrega de #208")
estabelece explicitamente que esse título **não prevalece** sobre a decisão
arquitetural: não haverá retry/backoff inline dentro da mesma execução do
subprocesso `kiro-cli`. O corpo atual da issue #208 (lido nesta etapa) já
reflete essa correção — objetivo, escopo e critérios de aceite exigem
classificação `UNKNOWN_OUTCOME`, uma única invocação do subprocesso por
entrega, preservação de sessão e observabilidade, sem sleep/backoff seguido de
nova chamada. Os casos de teste abaixo seguem o body/ADR (fonte normativa),
não o título.

**Estado do código no momento desta etapa:** `src/adapters/kiro_cli_agent.py`
hoje:
- não classifica o resultado da execução em estados (`SUCCEEDED`,
  `DEFINITE_NOT_STARTED`, `UNKNOWN_OUTCOME`) — apenas detecta falha/sucesso via
  `_detect_failure` para fins de log (`log.info`/`log.error`);
- já invoca o subprocesso exatamente uma vez por chamada de `_run` (não há
  loop de retry hoje) — logo o requisito "uma única invocação por entrega" já
  é satisfeito estruturalmente, mas não é **verificado/travado** por teste
  dedicado nem **documentado como decisão intencional** (é apenas a ausência
  de um recurso, não uma política);
- não distingue `dispatch failure`/`InternalServerError`/timeout como uma
  categoria própria (`UNKNOWN_OUTCOME`); todos caem genericamente em
  "detectou falha" via `_FAILURE_MARKERS`/`_ERROR_HINTS`;
- já preserva `session_id` via `SessionIndex.set` após a chamada (linha
  `if current_id: index.set(...)`) e já retoma via `--resume-id` quando a
  sessão existir (`_session_exists`) — este comportamento é anterior a #208 e
  não deve regredir;
- já trata timeout (`subprocess.TimeoutExpired` → string `"[TIMEOUT]..."`) e
  ausência do binário (`FileNotFoundError` → `"[ERRO]..."`) sem re-chamar o
  subprocesso.

Esta é a etapa de Casos de Teste, anterior à implementação. Os casos que
exercitam comportamento **ainda não implementado** (classificação explícita
em `UNKNOWN_OUTCOME`, guarda formal de invocação única, preservação de
request ID) devem falhar hoje (`ImportError`/`AttributeError`/asserção) e
passar após a implementação — mesmo padrão de `tests/test_sanitize_
relations.py` e `tests/test_error_classification.py`. Os casos que exercitam
comportamento **já existente e que não pode regredir** (sessão preservada,
timeout tratado, sucesso inalterado) já passam hoje.

Verificado nesta etapa (sem alterar código, apenas leitura/execução):

```
python -m pytest tests/test_agent_failure_detection.py tests/test_error_classification.py -q
```

Ambas as suítes passam integralmente no estado atual de `epic` — linha de
base de não-regressão para esta task.

## CT-001 — `dispatch failure` real do incidente #203 gera exatamente uma invocação do subprocesso

**Tipo:** unitário/integração
**Critério de aceitação:** "cada um desses resultados permite exatamente uma
invocação do subprocesso por entrega, sem sleep/backoff seguido de nova
chamada" (ADR, contrato normativo; critérios de aceite de #208)

**Pré-condição:**
- Output reproduzindo literalmente o padrão real do incidente #203:
  ```
  Kiro is having trouble responding right now:
     0: Failed to receive the next message: request_id: <id>,
        error: dispatch failure (io error): request or response body error
  [exit-code: 1]
  ```

**Passos:**
1. Fazer spy/monkeypatch de `subprocess.run` (ou do ponto de entrada
   equivalente após a implementação) contando as chamadas.
2. Executar `KiroCliAgent()._run(params, work_dir)` (ou `execute`) com o mock
   configurado para retornar o output acima uma única vez.
3. Contar as chamadas ao subprocesso.

**Resultado esperado:**
- Exatamente 1 chamada ao subprocesso `kiro-cli chat` — nenhuma segunda
  chamada é feita dentro da mesma execução, mesmo com o padrão de abort
  reconhecido.
- Nenhuma chamada a `time.sleep`/equivalente de backoff ocorre entre chamadas
  (não há chamadas subsequentes a verificar).
- Este teste hoje já passaria **incidentalmente** (o código atual não faz
  retry), mas deve ser formalizado como teste dedicado que trava a política —
  hoje **não existe** teste que afirme isso explicitamente para o padrão real
  de `dispatch failure`; deve ser adicionado nesta implementação.

---

## CT-002 — `InternalServerError` após output parcial gera uma única chamada

**Tipo:** unitário
**Critério de aceitação:** mesmo contrato do CT-001, aplicado ao segundo
marcador citado explicitamente pela ADR/issue

**Pré-condição:**
- Output com progresso parcial do agente (ex.: linhas de trabalho, tool calls)
  seguido de um bloco de `InternalServerError` antes de qualquer linha de
  conclusão do `kiro-cli`.

**Passos:**
1. Montar o output parcial + `InternalServerError` (`returncode` não-zero ou
   texto reconhecível, conforme o canal estruturado vigente após #206).
2. Executar `_run`/`execute` com spy no subprocesso.

**Resultado esperado:**
- Exatamente 1 chamada ao subprocesso.
- A classificação (após implementada) marca o resultado como
  `UNKNOWN_OUTCOME`, não como sucesso nem como falha definitiva — distinção
  que não existe hoje no código (hoje só há binário
  falha/sucesso via `_detect_failure`).
- Deve falhar hoje na parte da asserção de classificação (não há
  `UNKNOWN_OUTCOME` no código) e passar após a implementação.

---

## CT-003 — Timeout é classificado como `UNKNOWN_OUTCOME`, não como falha definitiva

**Tipo:** unitário
**Critério de aceitação:** "timeout é tratado como `UNKNOWN_OUTCOME`, pois o
processo pode ter produzido efeitos antes de exceder o limite" (ADR, seção 6)

**Pré-condição:**
- `subprocess.run` levanta `subprocess.TimeoutExpired` (comportamento já
  simulável monkeypatchando `subprocess.run` para lançar a exceção).

**Passos:**
1. Monkeypatch `subprocess.run` para levantar `subprocess.TimeoutExpired`.
2. Executar `_run`/`execute`.
3. Inspecionar a classificação do resultado (após implementada).

**Resultado esperado:**
- O output final ainda contém o marcador `"[TIMEOUT]"` (comportamento já
  existente, não deve regredir — ver
  `TestDetectFailureFalha.test_cada_marcador_dispara_falha` em
  `tests/test_agent_failure_detection.py`, parametrizado com `"[TIMEOUT]"`).
- A classificação do resultado (novo comportamento) é `UNKNOWN_OUTCOME`, e
  **não** `DEFINITE_NOT_STARTED` nem um terceiro rótulo genérico de "falha".
- Nenhuma segunda chamada ao subprocesso ocorre após o timeout dentro da
  mesma execução.
- A parte de classificação explícita deve falhar hoje (não existe
  `UNKNOWN_OUTCOME` no código); a parte de marcador/ausência de segunda
  chamada já passa hoje.

---

## CT-004 — Output integral, request ID e erro permanecem disponíveis para auditoria

**Tipo:** unitário
**Critério de aceitação:** "Output integral, request ID quando disponível,
erro e `session_id` permanecem disponíveis para observabilidade e
continuidade" (critério de aceite de #208)

**Pré-condição:**
- Output do padrão real do incidente #203, contendo `request_id: <id>` na
  linha do erro estruturado.

**Passos:**
1. Executar `_run`/`execute` com esse output (via mock do subprocesso).
2. Inspecionar o log de execução persistido (`_append_log`/arquivo em
   `logs/<issue_id>/<timestamp>.md`) e, se a implementação expuser o dado
   estruturado (ex.: em um objeto de resultado), inspecionar esse objeto
   diretamente.

**Resultado esperado:**
- O output integral (sem truncamento) está presente no arquivo de log —
  comportamento já existente hoje via `self._append_log(log_path,
  self._strip_ansi(output) + "\n")`; não pode regredir.
- O `request_id` capturado no texto (`request_id: <id>`) é localizável no log
  e, se a implementação adicionar extração estruturada desse campo, o valor
  extraído corresponde exatamente ao capturado no output real (ex.: via regex
  já usada para UUID de sessão, ou nova regex dedicada a `request_id`).
- A mensagem de erro extraída por `_detect_failure` continua não-vazia e
  identificando a causa real (`dispatch failure`), não apenas a última linha —
  mesmo contrato de `test_nao_reduz_a_ultima_linha`.
- A parte de output/erro já passa hoje; a parte de extração estruturada de
  `request_id` (se adicionada) é nova e deve ser coberta por teste dedicado.

---

## CT-005 — `session_id` descoberto após o abort é preservado no índice de sessões

**Tipo:** unitário
**Critério de aceitação:** "o `session_id` descoberto após a chamada é
preservado quando disponível" (ADR, seção 6; critérios de aceite de #208)

**Pré-condição:**
- Subprocesso `kiro-cli chat` mockado retornando output de abort (`dispatch
  failure`) com `returncode != 0`.
- `_list_session_ids`/`_latest_session_id` mockados para retornar um UUID
  válido simulando que o kiro-cli registrou a sessão antes de abortar.

**Passos:**
1. Executar `_run` com um `SessionIndex` real apontando para um arquivo
   temporário (`tmp_path`), sem sessão prévia conhecida para
   `(board_id, issue_id, agent_id)`.
2. Após a execução, ler `SessionIndex().get(board_id, issue_id, agent_id)`.

**Resultado esperado:**
- O `session_id` mockado foi persistido no índice, mesmo com a execução tendo
  abortado — reproduz o comportamento já existente hoje (`if current_id:
  index.set(...)` roda independentemente de `_detect_failure`/sucesso, pois
  ocorre antes dessa checagem em `_run`).
- Este teste é majoritariamente de **não regressão**: já deve passar hoje.
  Caso a implementação altere o fluxo de `_run` para incorporar a
  classificação `UNKNOWN_OUTCOME`, este teste garante que a preservação da
  sessão não foi removida/movida para um caminho condicional que a puxe do
  caso de abort.

---

## CT-006 — Entrega posterior retoma via `--resume-id` pelo fluxo já existente

**Tipo:** integração
**Critério de aceitação:** "Uma entrega posterior usa `--resume-id` pelo
fluxo existente quando a sessão estiver disponível, somente após o loop
normal reconciliar os estados local e remoto" (critério de aceite de #208)

**Pré-condição:**
- `SessionIndex` já contém um `session_id` para
  `(board_id, issue_id, agent_id)` (simulando uma entrega anterior que
  abortou, mas persistiu a sessão — ver CT-005).
- `_session_exists` mockado para retornar `True` para esse `session_id`.

**Passos:**
1. Executar `_run` para uma nova entrega (nova chamada, simulando o loop
   normal reexecutando a issue depois da reconciliação).
2. Inspecionar o comando montado (`cmd`) passado a `subprocess.run`.

**Resultado esperado:**
- O comando contém `--resume-id <session_id_conhecido>` — mesmo
  comportamento hoje coberto implicitamente pelo fluxo de `_run`
  (`if known_id and self._session_exists(...): cmd += ["--resume-id",
  known_id]`), sem que #208 precise alterar essa lógica.
- Nenhuma chamada extra ao subprocesso ocorre como parte desta retomada além
  da prevista (1 chamada) — reforça que a "nova tentativa" é uma entrega
  distinta do loop normal, não um retry inline dentro da execução anterior.
- Já passa hoje (comportamento pré-existente); serve de trava para não
  regredir ao implementar a classificação `UNKNOWN_OUTCOME`.

---

## CT-007 — Ausência de retry inline: nenhuma chamada a sleep/backoff seguida de nova invocação

**Tipo:** unitário
**Critério de aceitação:** "sem sleep/backoff seguido de nova chamada" (ADR,
contrato normativo)

**Pré-condição:**
- Output de abort (`dispatch failure` ou `InternalServerError`).

**Passos:**
1. Monkeypatch de `time.sleep` (e de qualquer função de backoff que a
   implementação vier a introduzir) registrando chamadas.
2. Monkeypatch de `subprocess.run` registrando chamadas.
3. Executar `_run`/`execute`.

**Resultado esperado:**
- Zero chamadas a `time.sleep`/backoff dentro de `_run`/`execute` para esse
  cenário.
- Exatamente 1 chamada a `subprocess.run` (mesma asserção do CT-001,
  reforçada aqui como o teste que **provaria a ausência** de uma
  implementação ingênua de retry, caso alguém a introduza por engano ao ler
  apenas o título histórico da issue).
- Este é o caso de teste mais diretamente ligado ao risco descrito na ADR
  (retry ingênuo duplicando efeito colateral): deve ser adicionado mesmo que
  já passe hoje "por ausência de código", para travar a decisão
  explicitamente contra regressão futura.

---

## CT-008 — Caminho de sucesso permanece inalterado

**Tipo:** unitário/integração
**Critério de aceitação:** "sucesso continua inalterado" (ADR, seção 6)

**Pré-condição:**
- Output de execução bem-sucedida (`returncode == 0`, sem marcador de falha),
  mesmo padrão de `TestDetectFailureSucesso.test_output_normal_nao_e_falha`.

**Passos:**
1. Executar `_run`/`execute` com esse output.
2. Repetir a suíte `tests/test_agent_failure_detection.py::
   TestExecuteUsaDeteccao::test_sucesso_loga_info_com_resumo` e
   `test_linha_de_inicio_preserva_formato_do_epic` após a implementação.

**Resultado esperado:**
- Classificação (se exposta) é `SUCCEEDED`, nunca `UNKNOWN_OUTCOME`.
- Log de conclusão continua sendo `log.info` com o resumo da última linha
  (formato inalterado).
- Nenhuma chamada extra ao subprocesso, nenhum sleep/backoff.
- Já passa hoje; não pode regredir.

---

## CT-009 — Mecanismos de proteção de estado interno não são afetados

**Tipo:** unitário
**Critério de aceitação:** "Validar que a política não interfere com
`SessionIndex` nem com a proteção de estado interno (`PROTECTED_PATHS`/
`build_prompt`)" (escopo item 5 de #208)

**Pré-condição:**
- Implementação da classificação `UNKNOWN_OUTCOME` concluída.

**Passos:**
1. Executar a suíte existente que cobre `PROTECTED_PATHS`/`build_prompt` (ex.:
   `tests/test_protected_paths.py` ou nome equivalente já presente no
   repositório — a localizar na etapa de implementação) sem alterações.
2. Confirmar que nenhum novo caminho de código introduzido por #208 constrói
   um prompt que referencie os arquivos protegidos
   (`.pipe/boards/*/snapshot.json`, `.pipe/changeQueue.json`,
   `.pipe/throttle*.json`, `.pipe/sessions.json`, etc.) nem escreve fora do
   `SessionIndex` já existente.

**Resultado esperado:**
- A suíte de proteção de estado interno permanece 100% verde, sem alteração
  de comportamento.
- `SessionIndex.set`/`.get` continuam sendo os únicos pontos de escrita/leitura
  de sessão usados pelo novo fluxo — nenhum acesso direto a
  `.pipe/sessions.json` fora dessa classe.

---

## CT-010 — Não regressão da suíte existente

**Tipo:** integração
**Critério de aceitação:** critérios de aceite de #208 (cobertura completa
sem regressão) e ADR seção 6 ("nenhuma alteração é necessária nos mecanismos
de proteção de estado interno")

**Pré-condição:** nenhuma.

**Passos:**
```bash
python -m pytest tests/ -v
```

**Resultado esperado:**
- Todos os testes que já passavam antes da implementação de #208 continuam
  passando.
- Comparação feita nesta etapa (linha de base, antes da implementação):

## Resultado da execução (nesta etapa)

Nesta etapa (Casos de Teste, anterior à implementação), foram definidos 10
casos de teste (CT-001 a CT-010) cobrindo os oito itens da seção "Testes
exigidos para #208" da ADR:

- invocação única por entrega para `dispatch failure` (CT-001) e
  `InternalServerError` após output parcial (CT-002);
- timeout como `UNKNOWN_OUTCOME` (CT-003);
- preservação de output integral/request ID/erro (CT-004);
- preservação do `session_id` descoberto após a chamada (CT-005);
- retomada por `--resume-id` numa entrega posterior (CT-006);
- ausência de retry/backoff inline (CT-007) — reforço explícito do risco
  central da ADR;
- não regressão do caminho de sucesso (CT-008);
- não interferência com `SessionIndex`/`PROTECTED_PATHS` (CT-009);
- suíte completa sem regressão (CT-010).

Executado nesta etapa, sem alterar código de produção:

```
python -m pytest tests/ -q
```

Resultado da linha de base (antes da implementação de #208): **21 failed,
1143 passed, 28 skipped, 1 xpassed**. As 21 falhas são pré-existentes e não
relacionadas a #208:

- `tests/test_agent_log_descritivo.py` (16 falhas) — formato de log
  descritivo (board/issue/agent_name no início do log), tema de outra task,
  já falhando antes de qualquer alteração desta issue.
- `tests/test_dockerfile.py` (3 falhas) — verificação de SHA-256 pinado do
  kiro-cli no Dockerfile, sem relação com o adapter em Python.

Confirmado isoladamente que as suítes diretamente relacionadas ao escopo desta
issue passam integralmente hoje:

```
python -m pytest tests/test_agent_failure_detection.py tests/test_error_classification.py -q
```

Resultado: 20 + 36 = 56 testes, todos passando — linha de base de
não-regressão para a etapa de Desenvolvimento subsequente.

Os testes automatizados correspondentes a CT-001 a CT-009 (a maioria deve
falhar apenas na parte de classificação explícita `UNKNOWN_OUTCOME`, já que a
ausência de retry inline já é o comportamento atual por não haver
implementação de retry no código) não foram adicionados ao código de
produção/testes nesta etapa — a criação do arquivo de teste dedicado (ex.:
`tests/test_kiro_cli_unknown_outcome.py`) e a introdução explícita da
classificação em `src/adapters/kiro_cli_agent.py` pertencem à etapa de
Desenvolvimento, conforme o objetivo desta task ser exclusivamente a definição
dos casos de teste.

Nenhuma dúvida bloqueante ou débito a registrar nesta etapa: a decisão
arquitetural bloqueante (débito #217) já foi resolvida e integrada ao body de
#208 antes desta verificação, e a ADR referenciada é autocontida quanto ao
contrato exigido para os testes.
