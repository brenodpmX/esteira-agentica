# Casos de Teste — Limitador de reexecuções de agente por contexto com contenção e retomada humana

- **Issue:** #306
- **Story relacionada:** limitador opt-in de reexecuções de agente (confiabilidade); bloqueia #315
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/306-limitador-reexecucoes-agente-por-contexto`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA 1–13) da
> issue #306 e de seus cenários obrigatórios (CT-01 a CT-15). Cada caso tem
> resultado esperado explícito e verificável. Os testes são da suíte Python do
> motor (pytest, em `tests/`), salvo os marcados como **varredura/revisão**
> (guarda estática de código/logs). Os testes de janela usam **relógio
> controlável** (`monkeypatch` de `time.time`), conforme exigido pelos
> entregáveis.

---

## Contexto de arquitetura (baseline do código atual — v1.18.0)

O mecanismo não existe hoje. Os pontos de ancoragem no motor atual, confirmados
na leitura do código, são:

- **Ponto de entrega ao agente** — `src/__main__.py::call_agent(config, task, …)`
  é onde a issue selecionada é efetivamente entregue para execução. Antes de
  despachar, já existe um **gate fail-closed** no mesmo ponto (composição em
  camadas, #308): `compose_execution_record(...)` mede e verifica o contrato de
  instruções obrigatórias e, se `instrucoes_obrigatorias_carregadas` for falso,
  emite `log.error(event="composicao_fail_closed")` e **`return None` ANTES** de
  `_dispatch_with_recovery(...)`. Esse é exatamente o padrão onde o limitador
  deve: (1) **contar a execução no instante da entrega** (independente do
  resultado) e (2) **bloquear antes de despachar** quando o contexto excede o
  limite. A contagem é no instante da entrega — não depende de
  `ExecutionResult` (`src/core/execution.py`: `SUCEDIDO`/`FALHA`/
  `UNKNOWN_OUTCOME`/…).
- **Seleção de tarefas** — `src/__main__.py::keep_task(board_id, config)` varre
  coluna a coluna e devolve a issue elegível. Issues bloqueadas por
  `/need_human` ou `/blocked_by` são puladas por `_is_blocked(issue)` (lê o
  bloco `@---` do `-body.md`). É aqui que uma issue já marcada com `need_human`
  pelo limitador deixa de ser selecionada **sem travar a fila** — as demais
  seguem sendo processadas (isolamento).
- **Cooldown existente é distinto do limitador** — `_rerun_cache` (dict em
  memória, **por processo**), `_cooldown_seconds`, `_in_rerun_cooldown`,
  `_mark_rerun`, `_purge_expired_rerun` em `src/__main__.py` implementam o
  `boards.rerun_cooldown`: apenas **espaçam** reexecuções no mesmo
  `(board, coluna, issue)`, **sem teto**. O limitador é mecanismo **novo e
  complementar**; a chave do cooldown já usa a mesma identidade de contexto
  `(board, coluna, issue)`, o que o planejamento adotou para o limitador. A
  documentação deve deixar a distinção inequívoca (entregável).
- **Porta de board com default inócuo para label** — `src/core/board.py`:
  `BoardPort.set_labels`/`add_label`/`remove_label` têm implementação **padrão
  no-op** que só emite `log.warning("Board", "… não implementado neste
  adapter")`; o adaptador real (`src/adapters/github_board.py`) os sobrescreve.
  `add_comment` e `list_comments` são `@abstractmethod` (todo adapter
  implementa); `list_comments` retorna `list[dict]` no formato
  `{author, date, body}`. Isso sustenta a exigência de **falhar na
  inicialização** quando a política está ativa e o adaptador **não** implementa
  aplicar label (não pode aparentar que sinalizou).
- **Validação de config segue o padrão da casa** — `src/core/config.py`:
  `ConfigError` é a exceção única; blocos opcionais de raiz (`sync`, `retry`,
  `project`) são validados em `check_config()` com mensagem **citando o caminho
  do campo**, e **`bool` é rejeitado ANTES de `int`** (`True/False` são `int` em
  Python — ver `validate_retry`/`validate_max_attempts`). `check_config()` roda
  **antes** de `InstanceLock.acquire()` em `main()`, ou seja, antes de qualquer
  alteração de estado. O mapa `boards` enumera **todo** valor dict como board
  (`_validate_boards` itera `boards.<id>`), então `agent_circuit_break` precisa
  ficar **na raiz**, fora de `boards` — como já previsto no contrato da issue.
  `validate_column_migrations` (#305) é o modelo de bloco opcional recém-somado.
- **Estado interno protegido** — `src/core/agent.py::PROTECTED_PATHS` lista os
  caminhos `.pipe/*` que o agente nunca pode acessar; o novo arquivo de estado
  do limitador deve entrar nessa lista (previsto no contrato). O conteúdo do
  estado nunca é exposto a agente, comentário ou log.
- **Sequência de inicialização** — `main()`: `check_config()` →
  `InstanceLock.acquire()` → `startup()` → `adapter = ADAPTERS[platform]()` →
  `board.connect` → `board.check_access` → `board_startup_sync`. A verificação
  de **capacidade real de aplicar label** do adaptador, quando a política está
  ativa, pertence à inicialização (após instanciar o adaptador, antes do
  processamento).

> **Decisão de design NÃO fixada pela QA (é do desenvolvimento):** o nome e a
> localização do núcleo do limitador (contador por contexto, máquina de estados
> do bloqueio/`trip`, persistência atômica), a assinatura exata das funções e o
> nome do arquivo de estado. Os casos abaixo testam **comportamento e
> invariantes observáveis**, não assinaturas. Onde um caso cita um símbolo
> concreto (`call_agent`, `keep_task`, `check_config`, `PROTECTED_PATHS`), o
> alvo é **provável**; se o desenvolvimento adotar outro nome/local, o caso vale
> sobre o comportamento equivalente. O que a QA fixa é: **fonte única** da
> contagem (ver nota de integração), contagem **no instante da entrega**,
> bloqueio **antes do dispatch**, sinalização **idempotente**, estado
> **protegido e persistido atomicamente**, e a **ordem obrigatória** do bloqueio
> definida no contrato.

### Fonte única da contagem (nota de integração — #307/#315)

A contagem de execuções de agente por contexto deve ter **fonte única** no
produto: a issue #307 (registro de execução por linhagem) registra execuções no
mesmo bloco. A issue #306 já declara `/blocks #315` (verificação de bloco), que
confere a existência de **uma única fonte de verdade** para "quantas execuções
houve neste contexto". A entrega que chegar depois **adere** à fonte existente,
sem criar contador paralelo. CT-SRC-01 trava esse invariante.

---

## Rastreabilidade (CA / cenário → casos)

| CA / Cenário | Requisito | Regra | Caso(s) |
|--------------|-----------|-------|---------|
| CA-1 / CT-01 — limite atingido bloqueia | RF-03, RF-05 | RN-04, RN-05 | CT-01, CT-01b |
| CA-1 / CT-02 — abaixo do limite executa | RF-01, RF-03 | RN-04 | CT-02 |
| CA-2 / CT-03 — sucesso sem avanço conta | RF-01 | RN-01 | CT-03 |
| CA-3 / CT-04 — bordas da janela | RF-04 | RN-03 | CT-04 (param. T-1/T/T+1) |
| CA-4 / CT-05 — mudança de coluna reinicia | RF-02 | RN-02 | CT-05 |
| CA-4 / CT-06 — revisita de coluna | RF-02 | RN-02 | CT-06 |
| CA-5 / CT-01 — sinalização completa | RF-05 | RN-05 | CT-07 |
| CA-6 / CT-07 — reinício da franquia | RF-07 | RN-06 | CT-08 |
| CA-7 / CT-08 — retomada humana sem resíduo | RF-07 | RN-06 | CT-09 |
| CA-8 / CT-09 — isolamento | RF-08 | RN-09 | CT-10 |
| CA-9 / CT-10 — sem política | RF-06 | RN-07 | CT-11, CT-11b |
| CA-10 / CT-10 — ativação sem retroação | RF-06 | RN-07 | CT-12 |
| CA-11 / CT-11 — config inválida | RNF-11 | — | CT-13 (param.) |
| CA-12 / CT-15 — um comentário por evento | RF-05 | RN-10 | CT-14 |
| CA-12 / CT-12 — idempotência de comentário | RF-05 | RN-10 | CT-15 |
| CA-13 / CT-13(issue) — bloqueio não move coluna | — | RN-11 | CT-16 |
| — / CT-13(issue) — falha fechada na persistência | — | — | CT-17a, CT-17b |
| — / CT-14(issue) — adaptador sem label | — | — | CT-18 |
| — / RNF-09 — recuperabilidade (reinício) | RF-07 | RN-06, RN-10 | CT-19a, CT-19b, CT-19c |
| — / RNF-10 — segurança do estado | — | — | CT-20 (varredura) |
| — / RNF-01 — precisão (≥32 execuções) | RF-03 | RN-04 | CT-21 |
| — / integração — fonte única da contagem | — | — | CT-SRC-01 (varredura) |

> **Observação de cobertura:** o escopo da issue está **completo e
> internamente consistente** — os 13 CAs mapeiam limpo sobre a arquitetura
> `__main__`/`core` existente (ponto de entrega `call_agent`, seleção
> `keep_task`, validação `config.py`, porta `board.py`, `PROTECTED_PATHS`), sem
> lacuna ou contradição que exigisse devolver ao planejamento
> (`revisar-escopo`). Os contratos (bloco de config, estado interno, ordem
> obrigatória do bloqueio, marcador oculto do comentário, capacidade exigida da
> porta) estão especificados. Os casos abaixo cobrem os 15 CTs obrigatórios mais
> os invariantes não-funcionais testáveis sem rede (RNF-01/05/06/09/10/11) e a
> fonte única da contagem.

---

## Convenções para o desenvolvimento (todos os casos automatizados)

- **Offline, sem rede:** usar um `BoardPort` **fake espião controlável**,
  no padrão de `tests/test_rerun_cooldown.py`, `tests/test_column_withdrawal.py`
  e `tests/test_sync_optimization.py`. O fake deve registrar as chamadas de
  `add_label`/`set_labels` (label aplicada por issue), `add_comment` (comentário
  publicado, com o corpo) e `list_comments` (retornando a lista corrente, que o
  teste pode **mutar** para simular comentário já presente). Opcionalmente, um
  fake **sem** sobrescrever label (herdando o default no-op de `BoardPort`) para
  CT-18.
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` por teste (fixture
  `autouse`), para que `.pipe/` e `logs/` sejam isolados — mesmo padrão dos
  testes existentes. Qualquer cache de módulo relevante
  (ex.: `src.__main__._rerun_cache` e o novo contador, se expostos no módulo)
  deve ser **limpo** em fixture `autouse` (padrão `cache_limpo` de
  `test_rerun_cooldown.py`), para não vazar estado entre testes.
- **Relógio controlável:** nos casos de janela (CT-03/CT-04/CT-21) e de expiração
  (CT-19), controlar o tempo via `monkeypatch` de `time.time` (ou do relógio que
  o limitador usar) — **nunca** depender de `sleep` real. O relógio é injetado/
  monkeypatchado; o teste avança o tempo deterministicamente.
- **Nunca** fazer `monkeypatch` do próprio símbolo sob teste (lição do incidente
  #106 — mascarava ausência de cobertura real). O núcleo do limitador (contagem,
  decisão de bloqueio, máquina de estados do `trip`) é exercitado **de verdade**;
  só o **provedor** (board port) e o **relógio** são controlados. O dispatch real
  ao agente (`_dispatch_with_recovery`) é substituído por um espião que registra
  **se** foi chamado — assim o teste verifica "agente iniciado / não iniciado"
  sem executar `kiro-cli`.
- **Evidência:** quando um caso verifica log, ler o arquivo do dia
  (`logs/<data>.json`) e localizar a linha do evento correspondente (ex.: evento
  de bloqueio, erro de admissão). **Nunca** inspecionar o arquivo de estado
  interno protegido (`.pipe/...`) para auditar comportamento de negócio — isso é
  o que RNF-10 proíbe. A verificação do **conteúdo** do estado persistido
  (CT-19) é feita só onde o caso explicita que é verificação de teste da
  persistência, e não como fonte de evidência de negócio.
- **Contagem e bloqueio distintos do cooldown:** os casos do limitador
  configuram `agent_circuit_break` (política) e, quando pertinente, mantêm
  `boards.rerun_cooldown` para provar que os dois mecanismos coexistem sem
  interferência (CT-11b).

---

## Grupo A — Contagem, janela e isolamento por contexto

> Alvo principal: o núcleo de contagem e decisão no ponto de entrega
> (`src/__main__.py::call_agent`, antes de `_dispatch_with_recovery`),
> exercitado com `BoardPort` fake, relógio controlável e dispatch espião.

### CT-01 — Limite atingido bloqueia a próxima execução

- **CA de origem (CA-1 / CT-01):** "Dada política válida com limite `N` e janela
  `T`, quando um contexto atinge `N` execuções dentro de `T`, então a próxima
  execução não é iniciada."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py` (novo).
- **Pré-condição:** política ativa `agent_circuit_break: {executions: 3, window:
  3600}`; contexto `(entrega, desenvolvimento, #42)` já com 3 ocorrências dentro
  da janela (semeadas via entregas anteriores reais, não injeção no estado).
  Dispatch substituído por espião.
- **Passos:**
  1. Entregar a issue ao agente 3 vezes (cada entrega conta); verificar que as 3
     foram despachadas.
  2. Entregar a 4ª vez (a excedente).
- **Resultado esperado:** a 4ª entrega **não** aciona o dispatch (o espião NÃO é
  chamado na 4ª); `call_agent` retorna o sinal de bloqueio (ex.: `None`, como no
  gate de composição) sem despachar; a issue fica marcada com `need_human` e
  recebe um comentário completo (ver CT-07). Nenhuma execução acima de `N` em
  nenhum momento.
- **Observações:** cobre RF-03/RF-05, RN-04/RN-05. É o invariante central:
  "nenhuma execução iniciada acima do limite dentro da janela".

### CT-01b — A ocorrência excedente não é contada como entrega efetiva

- **CA de origem (CA-1 / RF-03):** o bloqueio ocorre **antes** de a execução
  começar; a execução excedente (`N+1`) não é iniciada.
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** mesma de CT-01.
- **Passos:**
  1. Após o bloqueio na 4ª tentativa, inspecionar o espião de dispatch e o estado
     de contagem logicamente observável (via comportamento subsequente, não
     leitura do arquivo protegido).
- **Resultado esperado:** o dispatch foi chamado **exatamente 3 vezes** no total
  (as 3 permitidas); a tentativa excedente é interrompida **antes** do dispatch;
  o contexto é zerado pelo bloqueio (confirmado por CT-08). A excedente não gera
  nova ocorrência "entregue".
- **Observações:** reforça que a contagem é de **entregas efetivas** e o bloqueio
  antecede o dispatch (RF-03).

### CT-02 — Abaixo do limite executa normalmente

- **CA de origem (CA-1 / CT-02):** "Política ativa; contexto com menos de `N`
  ocorrências → execução inicia normalmente."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política `{executions: 3, window: 3600}`; contexto novo (zero
  ocorrências) ou com 1–2 ocorrências dentro de `T`.
- **Passos:**
  1. Entregar a issue com o contexto abaixo do limite.
- **Resultado esperado:** o dispatch é acionado normalmente; nenhuma marcação
  `need_human` nova; nenhum comentário de bloqueio publicado; a ocorrência é
  contada (a contagem avança de k para k+1).
- **Observações:** cobre RF-01/RF-03, RN-04 (abaixo do limite = passa).

### CT-03 — Sucesso sem avanço de coluna também conta

- **CA de origem (CA-2 / CT-03):** "Dada uma execução concluída com sucesso sem
  mudança de coluna, quando outra execução é entregue no mesmo contexto, então
  ela também é contada."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; dispatch espião configurado para devolver
  `ExecutionResult(classe=SUCEDIDO)`; a issue permanece na mesma coluna após a
  execução (sem avanço).
- **Passos:**
  1. Entregar a issue (execução 1, sucesso, mesma coluna).
  2. Entregar a issue de novo no mesmo contexto (execução 2).
  3. Repetir até a `N`-ésima; na `N+1`-ésima verificar o bloqueio.
- **Resultado esperado:** cada entrega — inclusive as de sucesso sem avanço —
  **incrementa** a contagem do contexto; ao atingir `N` entregas no mesmo
  `(board, coluna, issue)`, a próxima é bloqueada. A contagem **não** depende do
  resultado (`SUCEDIDO` conta igual a `FALHA`/`UNKNOWN_OUTCOME`).
- **Observações:** cobre RF-01, RN-01. Fecha o buraco de "repetições
  bem-sucedidas escapam da contenção".

### CT-04 — Bordas da janela (`T-1` conta; `T` e `T+1` não)

- **CA de origem (CA-3 / CT-04):** "Dada uma ocorrência com idade igual ou maior
  que `T`, quando o contexto é avaliado, então ela não contribui para a decisão
  de bloqueio." Cenário obrigatório CT-04: idades `T-1`, `T`, `T+1` classificadas
  corretamente.
- **Tipo:** unitário (limitador), **parametrizado** por idade de borda
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política `{executions: 2, window: T}` com relógio
  controlável. Semear **uma** ocorrência real em `t0`; depois avançar o relógio
  para `t0 + (T-1)`, `t0 + T` e `t0 + (T+1)` em três sub-casos.
- **Passos:**
  1. Para cada sub-caso, posicionar o relógio na idade de borda alvo da
     ocorrência semeada.
  2. Entregar uma segunda execução e avaliar se ela é a `N`-ésima dentro da
     janela.
- **Resultado esperado:**
  - idade `T-1`: a ocorrência antiga **conta** → com a nova, há 2 dentro de `T`
    → se política for `N=2`, a **próxima** (3ª) seria bloqueada; com `N=2` a 2ª
    ainda executa, mas a antiga é contada (verificável pelo próximo bloqueio);
  - idade `T` (igual à janela): a ocorrência antiga **não conta** (idade igual a
    `T` já expira — "estritamente menor que `T`");
  - idade `T+1`: a ocorrência antiga **não conta**.
  O invariante preciso: contam **somente** ocorrências com idade **estritamente
  menor que `T`**; `T` e `T+1` são descartadas na decisão.
- **Observações:** cobre RF-04, RN-03, RNF-04. O caso deve asseverar a borda
  **fechada em `T`** (idade `== T` expira). Usar `N` e sequência que isolem
  claramente o efeito "conta vs. não conta" (sugestão: semear `N-1` ocorrências
  dentro de `T` e uma na borda; o bloqueio da próxima ocorre **sse** a de borda
  contar).

### CT-05 — Mudança de coluna reinicia a contagem

- **CA de origem (CA-4 / CT-05):** "Dada uma mudança de coluna, quando o novo
  contexto é avaliado, então ele não contém nenhuma ocorrência do contexto
  anterior."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política `{executions: 2, window: 3600}`; issue `#42` com 2
  ocorrências em `(entrega, desenvolvimento, #42)` (no limite). Depois a issue é
  movida para `(entrega, execucao-testes, #42)`.
- **Passos:**
  1. Acumular 2 ocorrências em `desenvolvimento` (próxima entrega aí seria
     bloqueada).
  2. Mover a issue para `execucao-testes` (contexto novo `(board, coluna, id)`).
  3. Entregar no novo contexto.
- **Resultado esperado:** no novo contexto a contagem começa em **zero**; a
  entrega em `execucao-testes` é despachada normalmente (não bloqueada); o
  contexto anterior é **congelado** (não herdado). O registro lógico do contexto
  `(board, id)` é substituído por um contexto vazio ao detectar a transição
  (contrato: "no máximo um contexto ativo por `(board, issue)`; a coluna completa
  a identidade").
- **Observações:** cobre RF-02, RN-02. Isolamento por `(board, coluna, issue)`.

### CT-06 — Revisita de coluna já usada começa do zero

- **CA de origem (CA-4 / CT-06):** "...mesmo ao revisitar uma coluna já usada."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; sequência de colunas
  `desenvolvimento → execucao-testes → desenvolvimento` para a mesma issue, com
  ocorrências acumuladas na primeira passagem por `desenvolvimento`.
- **Passos:**
  1. Acumular `k` ocorrências em `desenvolvimento`.
  2. Mover para `execucao-testes` (contexto novo).
  3. Retornar para `desenvolvimento`.
  4. Entregar na coluna revisitada.
- **Resultado esperado:** ao retornar para `desenvolvimento`, o contexto
  `(entrega, desenvolvimento, #42)` começa **em zero** — o `k` anterior não é
  recuperado; a entrega é despachada normalmente. Como há no máximo um contexto
  ativo por `(board, issue)`, a transição anterior substituiu o registro; a
  revisita cria contexto limpo.
- **Observações:** cobre RF-02, RN-02. Guarda contra "herdar contagem ao
  revisitar coluna".

### CT-10 — Isolamento: issue bloqueada não trava a fila

- **CA de origem (CA-8 / CT-09):** "Dada uma issue bloqueada, quando existem
  outras issues elegíveis, então elas continuam sendo processadas."
- **Tipo:** unitário (seleção + limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; issue `#42` bloqueada (atingiu `N`, recebeu
  `need_human`); issue `#43` elegível em outro contexto (mesma coluna, outra
  issue; e também um sub-caso em outro board). `keep_task`/`_is_blocked` ativos.
- **Passos:**
  1. Provocar o bloqueio de `#42` (recebe `need_human`).
  2. Rodar a seleção/entrega no mesmo ciclo.
  3. Verificar qual issue é selecionada e despachada.
- **Resultado esperado:** `#42` é **pulada** por `keep_task` (via `_is_blocked`,
  pois tem `need_human`); `#43` é selecionada e despachada no mesmo ciclo, sem
  esperar `#42`. O bloqueio de uma issue não impede o processamento das demais —
  no mesmo board e em outro board.
- **Observações:** cobre RF-08, RN-09, RNF-02. Reutiliza o caminho existente de
  `_is_blocked` (need_human pula a issue), que é como o limitador obtém o
  isolamento sem travar a fila.

### CT-21 — Precisão sob repetição intensa (≥ 32 execuções)

- **CA de origem (RNF-01):** "Zero execuções entregues acima de `N` em qualquer
  contexto, para qualquer `N`/`T`, reproduzindo um cenário de pelo menos 32
  execuções repetidas."
- **Tipo:** unitário (limitador), estressado
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política `{executions: N, window: T}` com relógio
  controlável; um laço que tenta entregar a mesma issue ≥ 32 vezes dentro de `T`,
  contando quantas efetivamente foram despachadas; dispatch espião; sem remoção
  de `need_human` entre as tentativas.
- **Passos:**
  1. Tentar entregar a issue 32+ vezes no mesmo contexto, dentro de `T`.
  2. Contar os dispatches reais e os bloqueios.
- **Resultado esperado:** o total de dispatches efetivos **nunca** excede `N`
  entre bloqueios; cada vez que o limite é atingido, há exatamente um bloqueio
  (um `need_human` + um comentário por evento — ver CT-14); nenhuma execução
  excedente escapa em 32+ tentativas. (Se o teste permitir liberação periódica
  removendo `need_human`, cada franquia liberada permite outras `N` — nunca mais
  — antes de novo bloqueio.)
- **Observações:** cobre RNF-01. Reproduz o cenário mínimo de 32 execuções
  repetidas exigido pela issue.

---

## Grupo B — Sinalização, reinício da franquia e retomada

> Alvo: a sequência obrigatória do bloqueio — persistir evento + esvaziar
> ocorrências → aplicar `need_human` → publicar comentário idempotente
> (checando o marcador) → reconciliar. Exercitada com `BoardPort` fake que
> registra label, comentários e listagem de comentários.

### CT-07 — Sinalização completa do bloqueio (`need_human` + comentário mínimo)

- **CA de origem (CA-5 / CT-01):** "Dado um bloqueio, quando o operador consulta
  a issue, então ela está marcada com `need_human` e tem um comentário com
  motivo, issue, board, coluna, limite e janela, suficiente para diagnóstico sem
  abrir estado interno."
- **Tipo:** unitário (sinalização)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política `{executions: 3, window: 3600}`; contexto
  `(entrega, desenvolvimento, #42)` no limite; fake registra `add_label` e
  `add_comment`.
- **Passos:**
  1. Provocar o bloqueio (4ª entrega).
  2. Inspecionar a label aplicada e o corpo do comentário publicado.
- **Resultado esperado:**
  - a label `need_human` é aplicada pela porta do board (uma chamada registrada
    no fake);
  - **exatamente um** comentário é publicado contendo, no mínimo, os **cinco
    dados**: motivo do bloqueio, identificação da issue (`#42`), board
    (`entrega`), coluna (`desenvolvimento`), limite `N` (`3`) e janela `T`
    (`3600`, formatável para leitura humana sem alterar o valor);
  - o comentário contém o **marcador técnico oculto**
    `<!-- agent-circuit-break:<event_id> -->` associado ao `event_id`;
  - toda a informação necessária ao operador está no comentário — **nenhuma**
    leitura de `.pipe/...` é necessária.
- **Observações:** cobre RF-05, RN-05, RNF-03. Os cinco dados mínimos são
  obrigatórios; a QA fixa o conjunto mínimo, não o texto exato.

### CT-08 — Reinício imediato da franquia no bloqueio

- **CA de origem (CA-6 / CT-07):** "Dado um bloqueio, quando a contagem do
  contexto é consultada imediatamente após, então está zerada."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política `{executions: 3, window: 3600}`; contexto no limite;
  bloqueio provocado.
- **Passos:**
  1. Provocar o bloqueio.
  2. Observar a contagem do contexto imediatamente após, pelo **comportamento**:
     remover `need_human` e verificar quantas execuções a issue aceita antes de
     novo bloqueio.
- **Resultado esperado:** após o bloqueio, a contagem ativa do contexto está
  **zerada** — a issue, uma vez liberada, aceita até `N` novas execuções antes de
  outro bloqueio (não é bloqueada de imediato por resíduo). A ordem obrigatória é
  respeitada: as ocorrências são **esvaziadas antes de qualquer chamada externa**
  (label/comentário).
- **Observações:** cobre RF-07, RN-06. A verificação é comportamental (não
  leitura do arquivo protegido). Interage com CT-09.

### CT-09 — Retomada humana concede franquia completa sem resíduo

- **CA de origem (CA-7 / CT-08):** "Dado um contexto zerado por bloqueio, quando
  o operador remove `need_human` e a issue é selecionada, então ela pode acumular
  até `N` novas execuções antes de novo bloqueio, sem bloqueio residual
  imediato."
- **Tipo:** unitário (limitador + retomada)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política `{executions: 3, window: 3600}`; issue bloqueada
  (zerada); o teste **remove** `need_human` do estado da issue (simula ação do
  operador — editar o `-body.md`/label), tornando-a elegível de novo. Mesma
  janela temporal (sem avançar o relógio além de `T`), para provar que não é a
  expiração que libera, e sim o reinício da franquia.
- **Passos:**
  1. Provocar o bloqueio de `#42` (contexto zerado).
  2. Remover `need_human`.
  3. Entregar a issue `N-1` vezes (ex.: 2) e verificar que todas passam.
  4. Entregar a `N`-ésima e a `N+1`-ésima.
- **Resultado esperado:** as `N` entregas após a liberação são **todas
  despachadas** (nenhuma rejeitada por resíduo da contagem anterior); só a
  `N+1`-ésima é bloqueada de novo. A franquia é completa (`N`), mesmo dentro da
  mesma janela da sequência anterior.
- **Observações:** cobre RF-07, RN-06, RNF-05. É a diferença central para o
  cooldown: a retomada humana devolve franquia **cheia**, sem esperar expirar a
  janela.

### CT-14 — Exatamente um comentário por evento de bloqueio

- **CA de origem (CA-12 / CT-15):** "Dado um bloqueio já sinalizado, quando o
  ciclo se repete com `need_human` presente, então nenhum novo comentário é
  publicado; após a liberação, um novo bloqueio gera um novo evento e uma nova
  evidência."
- **Tipo:** unitário (sinalização)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; issue bloqueada (um comentário já publicado,
  com `event_id` E1); `need_human` **permanece** presente; o fake `list_comments`
  retorna o comentário com o marcador de E1.
- **Passos:**
  1. Provocar o bloqueio (publica comentário com marcador de E1).
  2. Repetir o ciclo várias vezes com `need_human` ainda presente (a issue é
     pulada por `keep_task`; mas se a reconciliação do bloqueio reexecutar,
     verifica-se a não-duplicação).
  3. Remover `need_human`; reacumular até novo bloqueio (evento E2).
- **Resultado esperado:** durante os ciclos com `need_human` presente, **nenhum**
  comentário adicional é publicado (o fake registra exatamente 1 `add_comment`
  para E1); após a liberação e novo bloqueio, é publicado **um novo** comentário
  com um **novo** `event_id` (E2 ≠ E1) e novo marcador — nova evidência.
- **Observações:** cobre RF-05, RN-10. Um comentário por evento; novo evento após
  liberação gera nova evidência.

### CT-15 — Idempotência do comentário na retomada após queda

- **CA de origem (CA-12 / CT-12):** "Queda após publicar o comentário; retomada →
  comentário não duplicado; marcador do evento reconhecido."
- **Tipo:** unitário (sinalização + recuperação)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; simular um bloqueio cujo evento foi
  persistido e o comentário **já publicado** (fake `list_comments` já contém o
  marcador `<!-- agent-circuit-break:E1 -->`), mas o processo "caiu" antes de
  confirmar localmente o passo do comentário (o progresso de sinalização no
  `trip` marca o comentário como ainda-não-confirmado).
- **Passos:**
  1. Montar o estado de retomada (evento E1 persistido, comentário presente no
     board via fake, confirmação local pendente).
  2. Rodar a reconciliação do bloqueio pendente.
- **Resultado esperado:** a reconciliação consulta `list_comments`, **encontra**
  o marcador de E1 e **não** publica um segundo comentário (zero `add_comment`
  adicional); apenas o passo faltante é concluído (confirmação local); a execução
  permanece negada até a sinalização estar reconciliada. Nenhuma duplicação.
- **Observações:** cobre RF-05, RN-10, RNF-09 e a linha "comentário publicado,
  mas o processo cai antes de confirmar localmente" da tabela de falhas. A
  verificação do marcador na listagem é o mecanismo de idempotência.

### CT-16 — O bloqueio não move a issue de coluna

- **CA de origem (CA-13 / CT-13 da issue):** "Dado o bloqueio de uma issue,
  quando ele é aplicado, então a issue não muda de coluna."
- **Tipo:** unitário (sinalização)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; issue `#42` em `desenvolvimento` no limite;
  fake registra chamadas de `move_issue`.
- **Passos:**
  1. Provocar o bloqueio.
  2. Inspecionar as chamadas de `move_issue` e a coluna da issue no estado local.
- **Resultado esperado:** **zero** chamadas de `move_issue` decorrentes do
  bloqueio; a issue permanece em `desenvolvimento`; a parada é a **label**
  (`need_human`) e a retomada é a sua **remoção** — não uma movimentação de
  coluna. Os 3 arquivos da issue não são movidos pelo limitador.
- **Observações:** cobre RN-11. Preserva o modelo de retomada por label.

---

## Grupo C — Sem política e ativação (opt-in, não regressão)

### CT-11 — Sem política: nenhum bloqueio, comportamento preservado, contagem interna ocorre

- **CA de origem (CA-9 / CT-10):** "Dada uma instância sem a política
  configurada, quando qualquer issue é selecionada, então nenhuma é bloqueada
  por este mecanismo e o comportamento vigente é preservado."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** config **sem** o bloco `agent_circuit_break`. Entregar a
  mesma issue muitas vezes (ex.: 10) no mesmo contexto.
- **Passos:**
  1. Entregar a issue repetidamente no mesmo `(board, coluna, id)`.
  2. Verificar dispatches, labels e comentários.
- **Resultado esperado:** **nenhuma** entrega é bloqueada por este mecanismo
  (todas despachadas); **nenhuma** label `need_human` nova aplicada por ele;
  **nenhum** comentário de bloqueio publicado. A **contagem interna continua
  ocorrendo** (as ocorrências são registradas no contexto, apenas não podadas por
  tempo nem usadas para bloquear) — verificável porque, ao **ativar** a política
  depois, não há reprocessamento retroativo (CT-12).
- **Observações:** cobre RF-06, RN-07, RNF-06. Opt-in estrito: sem bloco, zero
  bloqueio.

### CT-11b — Sem política com cooldown ativo: coexistência sem interferência

- **CA de origem (CA-9 / CT-10 / RNF-06):** "...com cooldown ativo → nenhum
  bloqueio novo; comportamento vigente preservado."
- **Tipo:** unitário (limitador + cooldown)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** config **sem** `agent_circuit_break` **e com**
  `boards.rerun_cooldown: 300`. Fixture limpa `_rerun_cache`.
- **Passos:**
  1. Selecionar/entregar a issue; verificar que o cooldown continua espaçando as
     reexecuções exatamente como hoje (issue pulada dentro de 300s).
  2. Verificar que nenhum bloqueio do limitador ocorre.
- **Resultado esperado:** o cooldown opera inalterado (issue reexecutada há menos
  de 300s é pulada em `keep_task`); o limitador **não** adiciona bloqueio nenhum
  (não configurado); os dois mecanismos coexistem sem interferência. Zero
  regressão sobre `test_rerun_cooldown.py`.
- **Observações:** cobre RNF-06. Prova a distinção operacional cooldown vs.
  limitador (um espaça, o outro conteria — mas está inativo).

### CT-12 — Ativação após execuções já contadas: sem reprocessamento retroativo

- **CA de origem (CA-10 / CT-10):** "Dada a ativação da política após execuções
  já contadas, quando a política passa a valer, então não há reprocessamento
  retroativo das ocorrências."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** fase 1 **sem** política — acumular `M` ocorrências (ex.:
  `M=5`) no contexto `(entrega, desenvolvimento, #42)` por entregas reais. Fase 2
  **com** política `{executions: 3, window: 3600}` passando a valer.
- **Passos:**
  1. Fase 1: entregar 5 vezes sem política (contagem interna acumula 5).
  2. Fase 2: ativar a política; entregar de novo no mesmo contexto.
- **Resultado esperado:** a ativação **não** dispara bloqueio retroativo pelas 5
  ocorrências passadas (não há "reprocessamento" que, com `N=3`, bloquearia na
  hora); a política passa a valer **dali para frente** — a decisão considera as
  ocorrências na janela conforme a semântica normal, sem efeito retroativo
  artificial. (A semântica exata — se as ocorrências pré-ativação dentro da
  janela contam na primeira avaliação — segue o contrato "não há reprocessamento
  retroativo das ocorrências": a ativação não re-executa decisões sobre o
  passado; o estado interno existente é respeitado, não recomputado.)
- **Observações:** cobre RF-06, RN-07. O ponto travado: ativar a política não é
  um gatilho que recomputa/bloqueia o histórico; a contagem interna já existente
  é a mesma fonte (ver CT-SRC-01).

---

## Grupo D — Validação da configuração (forma, na inicialização)

> Alvo: `src/core/config.py`, nova função `validate_agent_circuit_break` (ou
> integração em `check_config`), no padrão `ConfigError` que **cita o caminho
> completo do campo** (`agent_circuit_break.executions` / `.window`), com `bool`
> rejeitado **antes** de `int` (padrão de `validate_retry`/
> `validate_max_attempts`). A validação roda em `check_config()`, **antes** de
> `InstanceLock.acquire()` — logo antes de qualquer alteração de estado.

### CT-13 — Config inválida falha na verificação, citando o caminho

- **CA de origem (CA-11 / CT-11):** "Dada configuração parcial ou inválida,
  quando a instância inicia, então a inicialização falha antes de qualquer
  alteração de estado, com mensagem que cita o caminho do campo." Cenário CT-11:
  falta um campo, valor booleano, valor `< 1`, campo desconhecido ou bloco dentro
  do mapa de boards.
- **Tipo:** unitário (config), **parametrizado**
- **Arquivo/alvo:** `tests/test_agent_circuit_break_config.py` (novo).
- **Pré-condição:** cada sub-caso com um `agent_circuit_break` inválido:
  1. só `executions`, sem `window` (exige os dois juntos) → cita
     `agent_circuit_break.window`;
  2. só `window`, sem `executions` → cita `agent_circuit_break.executions`;
  3. `executions: true` (booleano) → cita `agent_circuit_break.executions`
     (bool rejeitado antes de int);
  4. `window: false` (booleano) → cita `agent_circuit_break.window`;
  5. `executions: 0` (`< 1`) → cita `agent_circuit_break.executions`;
  6. `window: 0` (`< 1`) → cita `agent_circuit_break.window`;
  7. `executions: 1.5` / `window: 3600.0` (float não-int) → cita o campo;
  8. `executions: "5"` (string) → cita o campo;
  9. campo desconhecido dentro do bloco (ex.: `foo: 1`) → cita
     `agent_circuit_break.foo` (rejeita campos desconhecidos);
  10. bloco colocado **dentro** do mapa de boards (ex.:
      `boards.agent_circuit_break: {...}` ou dentro de um board/coluna) → é
      rejeitado como board/estrutura inválida ou pela regra "a política não pode
      viver dentro de `boards`" (cita o caminho onde apareceu indevidamente).
- **Passos:** chamar a validação de config (`check_config`/
  `validate_agent_circuit_break`) para cada sub-caso.
- **Resultado esperado:** cada sub-caso levanta `ConfigError` cuja mensagem
  **cita o caminho completo** do campo inválido; a falha ocorre na verificação de
  configuração (antes de `InstanceLock.acquire()` e de `startup()`), portanto
  **antes de qualquer alteração de estado**. Nenhum sub-caso é aceito
  silenciosamente.
- **Observações:** cobre CA-11, RNF-11. Seguir o padrão de `validate_retry`
  (bool antes de int; mensagem acionável citando o caminho). Validação de
  **forma**; a semântica da política é opt-in.

### CT-13b — Config válida (bloco presente e bloco ausente) é aceita

- **CA de origem (CA-11 / contrato):** "Se presente, exige `executions` e
  `window` juntos; ausente = política inativa."
- **Tipo:** unitário (config)
- **Arquivo/alvo:** `tests/test_agent_circuit_break_config.py`
- **Pré-condição:** (i) `agent_circuit_break: {executions: 5, window: 3600}`;
  (ii) config **sem** o bloco.
- **Passos:** chamar a validação nos dois sub-cenários.
- **Resultado esperado:** (i) aceita sem exceção; (ii) aceita sem exceção
  (ausência = política inativa, nunca erro). Valores inteiros `>= 1` em ambos os
  campos são aceitos.
- **Observações:** cobre a obrigatoriedade conjunta e a opcionalidade do bloco.

---

## Grupo E — Falha fechada, capacidade do adaptador, recuperação e segurança

### CT-17a — Falha fechada ao persistir a ocorrência: agente não inicia

- **CA de origem (comportamento em falha / CT-13 da issue):** "Falha ao persistir
  a ocorrência antes da entrega → não iniciar o agente para aquela issue (falha
  fechada); log estruturado de erro de admissão."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; a escrita atômica do estado é forçada a
  falhar **apenas** no ato de persistir a ocorrência (ex.: injetar erro de I/O no
  utilitário de persistência do limitador — **não** no símbolo sob teste; usar um
  diretório de estado sem permissão de escrita ou um substituto de `os.replace`/
  `write` do módulo de persistência). Dispatch espião.
- **Passos:**
  1. Entregar a issue com a persistência da ocorrência falhando.
- **Resultado esperado:** o agente **não** é despachado (espião não chamado);
  `call_agent` retorna sem iniciar execução; é registrado um **log estruturado de
  erro de admissão** daquela issue (evento acionável em `logs/<data>.json`),
  **sem** expor conteúdo interno. Nenhuma execução "escapa" por falha de
  persistência.
- **Observações:** cobre a 1ª linha da tabela de falhas e RNF-07 (sem rede no
  caminho normal). Fail-closed: a dúvida resolve contra executar.

### CT-17b — Estado ilegível/corrompido: admissão negada, sem assumir contagem vazia

- **CA de origem (comportamento em falha):** "Estado ilegível ou corrompido →
  tratar como erro de integridade explícito; negar a admissão daquela issue; não
  assumir contagem vazia; erro acionável sem expor conteúdo interno."
- **Tipo:** unitário (limitador)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; o arquivo de estado existe mas está
  **corrompido** (ex.: JSON inválido / `version` desconhecida). Dispatch espião.
- **Passos:**
  1. Semear estado corrompido.
  2. Entregar a issue.
- **Resultado esperado:** o limitador trata como **erro de integridade
  explícito**; a admissão da issue é **negada** (dispatch não chamado); o sistema
  **não** assume contagem zero (não executa como se o contexto estivesse limpo);
  erro acionável registrado identificando o problema de integridade, **sem**
  vazar o conteúdo. Outras issues (contexto íntegro) seguem o fluxo (interação
  com isolamento — a falha é por issue/estado, capturada sem travar o loop
  global).
- **Observações:** cobre a 2ª e a última linha da tabela de falhas. Integridade
  antes de executar.

### CT-18 — Política ativa + adaptador sem capacidade de label → falha na inicialização

- **CA de origem (contrato / CT-14 da issue):** "Capacidade exigida da porta de
  board: com a política ativa, a operação de aplicar label deve estar
  efetivamente implementada pelo adaptador; um adaptador que não sobrescreva a
  implementação padrão inócua deve provocar falha na inicialização, nunca
  aparentar que aplicou a sinalização."
- **Tipo:** unitário (inicialização)
- **Arquivo/alvo:** `tests/test_startup_agent_circuit_break.py` (novo) ou
  extensão de `tests/test_startup.py`.
- **Pré-condição:** política `agent_circuit_break` **ativa**; um adaptador de
  board que **não** sobrescreve `set_labels`/`add_label` (herda o default no-op
  de `BoardPort`, que só emite `log.warning`). Sub-caso de controle: o adaptador
  **real** (ou um fake que sobrescreve label) + política ativa → inicialização
  **passa**.
- **Passos:**
  1. Rodar a inicialização (`check_config`/`startup`/gate de capacidade) com o
     adaptador sem label e a política ativa.
  2. Sub-caso de controle: idem com adaptador que implementa label.
- **Resultado esperado:** com adaptador **sem** capacidade real de label e
  política ativa, a inicialização **falha** (erro/`SystemExit`) com mensagem que
  **cita a capacidade ausente** (aplicar label); o loop **não** inicia. No
  sub-caso de controle, a inicialização **prossegue** normalmente. Sem política
  ativa, a ausência de label **não** falha a inicialização (o mecanismo está
  desligado).
- **Observações:** cobre a linha "adaptador de board sem capacidade real de
  aplicar label, com política ativa" da tabela de falhas. A detecção deve
  distinguir "default no-op" de "sobrescrito" (ex.: comparar o método da
  instância com o de `BoardPort`, ou um atributo de capacidade declarado pelo
  adapter) — a QA fixa o **comportamento** (falha vs. passa), não o mecanismo.

### CT-19a — Reinício entre persistir bloqueio e aplicar label: execução segue negada

- **CA de origem (RNF-09 / comportamento em falha):** "Reinício/queda entre
  persistir o bloqueio e aplicar a label → manter a execução negada; reconciliar
  o bloqueio pendente no ciclo seguinte."
- **Tipo:** unitário (recuperação)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** política ativa; estado persistido com um `trip` de bloqueio
  cujo progresso indica "evento persistido, label ainda não aplicada" (simula
  queda após o passo 1 da ordem obrigatória). Processo "reiniciado": o estado de
  módulo é limpo, mas o arquivo de estado persiste.
- **Passos:**
  1. Montar o estado com bloqueio pendente (label não aplicada).
  2. Rodar o ciclo seguinte (reconciliação).
  3. Tentar entregar a issue.
- **Resultado esperado:** a execução da issue bloqueada **permanece negada** (não
  despacha); a reconciliação **retoma** a sinalização pendente — aplica a label
  `need_human` e, em seguida, publica o comentário se o marcador ainda não
  existir; o `trip` avança o progresso. Nada é duplicado.
- **Observações:** cobre RNF-09 e a 3ª linha da tabela de falhas. A persistência
  resiste ao reinício (ao contrário do cooldown, que é por processo).

### CT-19b — Label aplicada mas comentário falhou: retoma só o passo faltante

- **CA de origem (comportamento em falha):** "Label aplicada, mas comentário
  falha → retomar somente o passo faltante; não reiniciar a execução; marcadores
  de etapa no evento de bloqueio."
- **Tipo:** unitário (recuperação)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** `trip` persistido indicando "label aplicada, comentário
  pendente"; `list_comments` do fake **não** contém o marcador do evento.
- **Passos:**
  1. Montar o estado (label ok, comentário pendente).
  2. Rodar a reconciliação.
- **Resultado esperado:** a reconciliação **não** reaplica a label
  desnecessariamente nem reinicia a execução; **publica o comentário** faltante
  (um `add_comment` com o marcador do evento); o `trip` passa a "sinalização
  completa". A execução segue negada enquanto `need_human` presente.
- **Observações:** cobre a 4ª linha da tabela de falhas. Retomada por passo, não
  do zero.

### CT-19c — Reinício não apaga ocorrências nem libera execução bloqueada

- **CA de origem (RNF-09):** "Reinício do processo não apaga ocorrências nem
  libera uma execução bloqueada."
- **Tipo:** unitário (recuperação)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** estado persistido com um contexto no limite (ou bloqueado);
  simular reinício limpando qualquer cache de módulo, preservando o arquivo.
- **Passos:**
  1. Semear o estado (contexto no limite / bloqueado).
  2. "Reiniciar" (limpar módulo).
  3. Entregar a issue.
- **Resultado esperado:** após o reinício, as ocorrências **persistem** (a
  próxima entrega continua sendo bloqueada se o contexto estava no limite); uma
  execução bloqueada **não** é liberada pelo reinício — ao contrário do cooldown
  (`_rerun_cache` é por processo e some ao reiniciar). A sinalização pendente é
  retomada sem duplicar comentário (ver CT-19a/b).
- **Observações:** cobre RNF-09. Distinção explícita e testada: cooldown é
  volátil; o limitador é persistente.

### CT-20 — Segurança do estado: sem conteúdo sensível, protegido e não editável

- **CA de origem (RNF-10):** "O estado interno e os marcadores nunca contêm corpo
  de issue, prompt, conversa, token ou credencial; o arquivo de estado não é
  editável por agente ou operador."
- **Tipo:** varredura/revisão (guarda estática do estado e do contrato)
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py` (asserção sobre o
  conteúdo persistido) e `tests/test_build_prompt_protected_paths.py` (extensão:
  o novo caminho de estado está em `PROTECTED_PATHS`).
- **Pré-condição:** issue com corpo contendo um marcador único (ex.:
  `CORPO_SECRETO_123`) e um prompt não trivial; provocar contagem e bloqueio.
- **Passos:**
  1. Provocar contagem + bloqueio.
  2. Ler o arquivo de estado persistido (verificação de teste da persistência).
  3. Verificar que o caminho do estado está em `PROTECTED_PATHS` e que
     `build_prompt` o rejeita se aparecer no prompt.
- **Resultado esperado:** o estado contém apenas identificação de contexto
  (`<board>/<issue>`, `column`), timestamps (`occurrences`) e o `trip`
  (`event_id`, parâmetros do bloqueio `N`/`T`, progresso) — **nunca**
  `CORPO_SECRETO_123`, prompt, conversa, token ou credencial. O novo arquivo de
  estado está listado em `PROTECTED_PATHS` (`src/core/agent.py`); `build_prompt`
  levanta `ValueError` se o caminho aparecer no prompt (mesmo padrão dos demais
  `.pipe/*`). O marcador do comentário (`agent-circuit-break:<event_id>`) carrega
  **apenas** o `event_id`, nunca conteúdo sensível.
- **Observações:** cobre RNF-10. O estado é mínimo e protegido; alinhado à
  política de arquivos protegidos já existente.

### CT-SRC-01 — Fonte única da contagem de execuções (guarda de integração)

- **CA de origem (nota de integração #307/#315 / entregável):** "A contagem de
  execuções de agente por contexto deve ter fonte única no produto; as duas
  entregas não podem manter contadores paralelos."
- **Tipo:** varredura/revisão (guarda estática) + comportamental
- **Arquivo/alvo:** `tests/test_agent_circuit_break.py`
- **Pré-condição:** a base pode ou não já conter a fonte da #307; o caso trava o
  invariante "uma só fonte de verdade".
- **Passos:**
  1. Identificar o ponto único onde a execução é contada no instante da entrega
     (em/junto a `call_agent`, antes de `_dispatch_with_recovery`).
  2. Verificar que o limitador **lê** a contagem dessa fonte, sem instanciar um
     contador paralelo próprio para o mesmo fato ("quantas execuções houve neste
     contexto").
- **Resultado esperado:** existe **um** registro de ocorrência por entrega, no
  mesmo instante lógico; o limitador consome essa contagem como fonte única (não
  há duas estruturas incrementadas independentemente para o mesmo evento de
  entrega). Se a #307 já tiver introduzido a fonte, o limitador **adere** a ela;
  caso contrário, a fonte criada aqui é a única e a #307 adere depois.
- **Observações:** cobre o ponto de atenção de integração e o entregável de
  verificação de bloco (`/blocks #315`). Travado como invariante arquitetural.

---

## Fora de escopo dos casos (alinhado à issue)

Os seguintes **não** são testados aqui por estarem fora de escopo da issue:

- diagnóstico ou correção **automática** da causa raiz de cada repetição;
- limites **diferentes** por board, coluna ou agente (política segmentada — nesta
  versão a política é única para a instância, RN-08);
- painel/dashboard, alertas externos, SLA para resposta humana;
- orçamento agregado de tokens/custo;
- consolidação de telemetria de execução (tempo, tokens, resultado);
- tratamento de loops de **sincronização**;
- movimentação **automática** da issue de coluna como efeito do bloqueio (ao
  contrário: CT-16 garante que o bloqueio **não** move);
- transição automática de "meio-aberto" (retomada **sem** intervenção humana) — a
  retomada é sempre a remoção humana de `need_human`;
- transições remotas de coluna que ocorram inteiramente entre duas leituras e
  deixem a issue na coluna original (limitação documentada: a contagem pode não
  reiniciar nesses casos — não há caso que exija observar o inobservável);
- nome/unidade final da configuração e texto do comentário **além** do mínimo
  (a máquina de estados e a persistência não dependem desse ajuste — os casos
  fixam o conjunto mínimo de dados, não a redação).

---

## Resumo de arquivos de teste propostos

| Arquivo | Cobre |
|---------|-------|
| `tests/test_agent_circuit_break.py` | CT-01, CT-01b, CT-02, CT-03, CT-04 (bordas da janela), CT-05, CT-06, CT-07, CT-08, CT-09, CT-10 (isolamento), CT-11, CT-11b, CT-12, CT-14, CT-15, CT-16, CT-17a, CT-17b, CT-19a, CT-19b, CT-19c, CT-20 (persistência/segurança), CT-21, CT-SRC-01 (núcleo do limitador: contagem, janela, bloqueio, sinalização idempotente, retomada, recuperação) |
| `tests/test_agent_circuit_break_config.py` | CT-13 (validação de forma parametrizada em `config.py`), CT-13b (config válida/ausente) |
| `tests/test_startup_agent_circuit_break.py` (ou extensão de `tests/test_startup.py`) | CT-18 (política ativa + adaptador sem capacidade de label → falha na inicialização) |
| `tests/test_build_prompt_protected_paths.py` (extensão) | CT-20 (novo arquivo de estado em `PROTECTED_PATHS`; `build_prompt` rejeita o caminho) |

### Mapa cenários obrigatórios da issue (CT-01..CT-15) → casos deste documento

| CT da issue | Caso(s) neste documento |
|-------------|-------------------------|
| CT-01 — Limite atingido | CT-01, CT-01b, CT-07 (sinalização) |
| CT-02 — Abaixo do limite | CT-02 |
| CT-03 — Sucesso sem avanço conta | CT-03 |
| CT-04 — Bordas da janela | CT-04 (param. T-1/T/T+1) |
| CT-05 — Mudança de coluna reinicia | CT-05 |
| CT-06 — Revisita de coluna | CT-06 |
| CT-07 — Reinício de franquia | CT-08 |
| CT-08 — Retomada humana | CT-09 |
| CT-09 — Isolamento | CT-10 |
| CT-10 — Sem política | CT-11, CT-11b, CT-12 |
| CT-11 — Config inválida | CT-13 (param.), CT-13b |
| CT-12 — Idempotência de comentário | CT-15 |
| CT-13 — Falha fechada na persistência | CT-17a, CT-17b (e CT-16 para "não move coluna", CA-13) |
| CT-14 — Adaptador sem capacidade de label | CT-18 |
| CT-15 — Um comentário por evento | CT-14 |

> Os 15 cenários obrigatórios (CT-01..CT-15 da issue) estão integralmente
> cobertos; CA-13 (bloqueio não move coluna) é coberto por CT-16; os requisitos
> não funcionais testáveis sem rede (RNF-01/05/06/09/10/11) e a fonte única da
> contagem são cobertos por CT-21, CT-09/CT-11b, CT-19, CT-20 e CT-SRC-01.

### Não regressão

A suíte existente deve continuar passando. Em especial, **sem**
`agent_circuit_break` configurado, o comportamento é idêntico ao atual:
`tests/test_rerun_cooldown.py` (cooldown inalterado), `tests/test_startup.py`,
`tests/test_execucao_autonoma_confiavel.py` e
`tests/test_snapshot_guard_call_agent.py` (caminho de `call_agent`/dispatch)
devem permanecer verdes — o limitador é opt-in e não altera o caminho normal
quando inativo (RNF-06).
