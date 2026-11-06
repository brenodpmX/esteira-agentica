# Casos de Teste — Verificação do bloco 3 (integridade de participação entre quadros e resiliência do sincronismo)

- **Issue:** #316
- **Story relacionada:** #316 — "Verificação do bloco 3 — integridade de
  participação entre quadros e resiliência do sincronismo" (auditoria
  integrada das entregas #309 e #310)
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-11-06
- **Branch:** `feature/316-verificacao-bloco-3`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da
> issue #316. Cada caso tem resultado esperado explícito e verificável. Os
> testes são da suíte Python do motor (pytest, em `tests/`), salvo os
> marcados como **manual/revisão** (auditoria documental).

---

## Natureza desta entrega (ler antes de implementar os casos)

Esta **não** é uma entrega de funcionalidade: é uma **verificação de bloco**.
O produto é um **relatório de verificação** com um **veredito por critério de
aceitação** (atendido / não atendido / não verificável) de cada uma das duas
entregas auditadas, cada veredito apoiado em **comportamento observado ou
teste executado** — nunca em releitura de texto.

As duas entregas já estão na linha principal (`origin/main` @ `c8b50eb`):

- **#309** — Circuit-breaker de sincronismo com escalação ao agente e
  encerramento controlado. Núcleo `src/core/sync_circuit_breaker.py`,
  consumido por `src/core/sync.py::apply_changes` e por
  `src/__main__.py::sync_remote_board`/`detect_local_all`/
  `queue_has_actionable`. Registrada no `CHANGELOG.md` seção **1.26.0**.
- **#310** — Integridade de participação de issues entre quadros de
  trabalho. Núcleo `src/core/participation.py` (classificação pura) +
  `src/core/participation_reconcile.py` (reconciliação/efeitos), integrados
  ao caminho real em `src/core/sync.py::_apply_change_up`/`_apply_create_down`
  (via `_reconcile_links_after_apply`/`reconcile_remote_presence`),
  `src/__main__.py::keep_task` (gate `participation.gate_keep`) e
  `src/__main__.py::sync_remote_board` (`detect_external_removal`).
  Registrada no `CHANGELOG.md` seção **1.23.0**, com a integração em
  produção corrigida na seção **1.23.1** (o code review do PR #330 havia
  reprovado a primeira versão por falta de chamada real aos gatilhos).

Consequências para a implementação dos casos:

1. **Desfecho "sem divergência" é válido.** Se a verificação confirmar as
   duas entregas efetivas e a suíte verde, o único artefato é o
   **relatório**: **sem alteração de código-fonte e sem incremento de
   versão** (CA-3/CT-05 da issue).
2. **O ponto de convergência do bloco (CT-04 da issue) é #309 × #310**, e
   ocorre em **dois** pontos de decisão do produto, ambos dentro do caminho
   real de sincronismo:
   - `src/core/sync.py::apply_changes` — o circuit-breaker (#309) decide,
     **antes** de despachar qualquer item da fila, se a issue/plataforma
     está bloqueada (`breaker.issue_blocked`/`breaker.platform_blocked`); só
     quando **não** está bloqueada é que `_apply_change_up`/
     `_apply_create_down` executam, e é exatamente aí que os gatilhos de
     reconciliação de participação (#310) rodam. Qualquer falha desses
     gatilhos (`ParticipationQueryError` ao consultar, ou exceção ao
     remover) propaga como erro tipado para o `except Exception` genérico de
     `apply_changes`, que a classifica (`classify_error`) e a **conta** pelo
     mesmo circuit-breaker — tratando-a como qualquer outra falha de
     sincronismo da issue, podendo levar a bloqueio e, por persistência, à
     escalação ao agente dedicado (#309).
   - `src/__main__.py::sync_remote_board` — quando a **plataforma** está
     bloqueada pelo circuit-breaker (#309), a função retorna antes de chamar
     tanto `sync_remote` quanto `participation_reconcile.detect_external_removal`
     (#310): o bloqueio de plataforma suprime **também** a detecção de
     remoção externa de participação, não apenas o sync de issues.
3. A suíte já cobre cada entrega isoladamente com o outro mecanismo **fora do
   cenário** (o `FakePort` de `tests/test_sync_circuit_breaker.py` não
   implementa `list_participations`/`remove_from_board` — nunca é exercitado
   com participação; os testes de participação nunca usam
   `SyncCircuitBreaker`/`apply_changes` com um `breaker` real — ver
   "Avaliação da suíte existente"). **Não há** hoje um teste que prove, sobre
   o código real, que as duas políticas convivem sem que uma mascare a
   outra nesses dois pontos — essa é a lacuna que fundamenta os casos novos
   desta verificação (CT-04a e CT-04b).
4. Os demais casos (CT-01, CT-02, CT-03, CT-05) são majoritariamente
   **execução e auditoria** da suíte e dos artefatos já presentes; só geram
   alteração de código se uma **divergência** for encontrada (CT-03),
   situação em que a correção exige teste de regressão + bump de versão +
   entrada no CHANGELOG (CA-4/CA-5 da issue).

---

## Avaliação da suíte existente (base da especificação)

Levantamento feito nesta etapa, sobre a linha principal (`origin/main` @
`c8b50eb`), com a suíte completa executada (`python -m pytest -q`):
**1785 passed, 26 failed, 17 skipped, 1 xpassed, 13 errors** (271,62s).

| Entrega | Cobertura existente (arquivos) | Veredito preliminar de cobertura |
|---------|--------------------------------|-----------------------------------|
| #309 — circuit-breaker de sincronismo | `tests/test_sync_circuit_breaker.py` (90+ testes, grupos A–L), `tests/test_sync_circuit_breaker_config.py` | Coberto (bloqueio por issue/plataforma, meio-aberto, escalação, encerramento controlado, descida completa, idempotência de relação, persistência de progresso, exclusão de rate limit, absorção da E4, defaults/validação) |
| #310 — integridade de participação entre quadros | `tests/test_participation_classification.py`, `tests/test_participation_reconciliation.py`, `tests/test_participation_gate.py`, `tests/test_participation_migration.py`, `tests/test_cross_board_safety.py`, `tests/test_participation_evidence.py`, `tests/test_participation_adapter.py`, `tests/test_participation_integration.py`, `tests/test_sub_issue_propagation_fix.py`, `tests/test_hotfix24_incident_doc_cleanup.py` | Coberto (classificação pura, reconciliação imediata/tardia, gate final em `keep_task`, migração de legados, contingência cross-board, evidência/observabilidade, porta real, integração pelo caminho real pós code review) |
| **Convergência #309 × #310 em `apply_changes` (issue bloqueada ⇒ reconciliação não tentada; falha de reconciliação ⇒ contada pelo circuit-breaker)** | — | **LACUNA** — ver abaixo |
| **Convergência #309 × #310 em `sync_remote_board` (plataforma bloqueada ⇒ `detect_external_removal` também suprimida)** | — | **LACUNA** — ver abaixo |

**Lacuna confirmada (fundamenta CT-04).** Duas evidências, por inspeção
direta dos dublês usados em cada suíte:

- Em `tests/test_sync_circuit_breaker.py`, o `FakePort(BoardPort)` implementa
  apenas os métodos de sincronismo "clássicos" (`get_issue`, `update_issue`,
  `apply_commands`-adjacentes via `Board`, etc.) — **não** sobrescreve
  `list_participations`/`remove_from_board` (`BoardPort` cai no default de
  `src/core/board.py`, que só faz `log.warning` e retorna `[]`/`None`). Os
  cenários de bloqueio/escalação desse arquivo nunca envolvem uma issue com
  vínculo cross-board real nem presença propagada — a interação do
  circuit-breaker com uma falha **originada em participação** não é
  exercitada.
- Em `tests/test_participation_reconciliation.py`,
  `tests/test_participation_integration.py` e demais arquivos de #310, os
  testes chamam `_apply_change_up`/`_apply_create_down`/`sync_remote_board`
  diretamente ou via um `apply_changes` **sem** circuit-breaker real ativo
  (sem issue/plataforma bloqueada no cenário) — nenhum teste verifica que
  uma falha de `reconcile_after_link`/`reconcile_remote_presence` é **contada**
  pelo `SyncCircuitBreaker`, nem que uma issue/plataforma já bloqueada pelo
  circuit-breaker impede a tentativa de reconciliação (nenhuma chamada a
  `list_participations`/`remove_from_board` deveria ocorrer nesse caso).

Isso é exatamente o ponto de convergência que a issue exige comprovar:
**ambos os mecanismos permanecem efetivos em conjunto**, sem que um mascare
o outro — em particular, (a) quando o circuit-breaker bloqueia a issue ou a
plataforma, nenhuma tentativa de reconciliação de participação ocorre para
aquele item/plataforma (nenhuma reconciliação "escapa" através do bloqueio
sem deixar rastro, e nenhuma chamada de rede de participação é feita
enquanto bloqueado); e (b) quando a issue/plataforma está livre, uma falha
de reconciliação de participação é **contada** pelo circuit-breaker com a
mesma política de qualquer outra falha de sincronismo — as duas fontes
avançam juntas, cada uma com sua responsabilidade, sem contagem suprimida
nem duplicada.

---

## Rastreabilidade (CA → casos)

| # | Critério de aceitação (resumo) | Caso(s) |
|---|--------------------------------|---------|
| CA-1 | Existe relatório que lista **cada critério de #309/#310 e seu veredito** | CT-01 (insumo), CT-05 (relatório) + o relatório final consolida CA-1..CA-7 |
| CA-2 | Suíte completa executada; **falha é corrigida ou registrada** com justificativa antes de encerrar | CT-01 |
| CA-3 | **Sem divergência** ⇒ relatório "sem divergência", **sem alteração de código nem bump de versão** | CT-05 |
| CA-4 | Divergência **corrigível no escopo** ⇒ teste de regressão + **incremento de versão** + entrada no CHANGELOG | CT-03 |
| CA-5 | Divergência que **exige escopo novo** ⇒ registrada como **demanda separada**, não implementada aqui | CT-03 |
| CA-6 | Duas entregas do bloco no **mesmo ponto de decisão do produto** permanecem efetivas em conjunto, sem uma sombrear a outra | **CT-04** |
| CA-7 | Critério **não verificável** com os meios disponíveis ⇒ veredito "não verificável" com a razão | CT-02 (quando a lacuna impede verificar), e tratamento transversal no relatório |

> Mapeamento dos cenários obrigatórios da issue → casos: CT-01 (suíte
> completa), CT-02 (critério sem cobertura ⇒ lacuna registrada), CT-03
> (comportamento declarado ausente ⇒ "não atendido" + correção/demanda),
> CT-04 (convergência #309 × #310), CT-05 (verificação sem divergência).
> Numeração 1:1 com a tabela de "Cenários de teste obrigatórios" do corpo da
> issue.

---

## Convenções para o desenvolvimento (todos os casos automatizados)

- **Offline, sem rede:** usar o `FakePort(BoardPort)` já existente em
  `tests/test_sync_circuit_breaker.py` como base, **estendido** para
  implementar `list_participations`/`remove_from_board` de forma
  controlável (padrão já usado em `tests/test_participation_reconciliation.py`),
  em vez de criar um dublê novo e desacoplado — isso é o que garante que o
  teste de convergência exercita o **mesmo** `apply_changes`/
  `sync_remote_board` reais usados pelas suítes de origem, não uma cópia.
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` autouse por teste
  (`.pipe/`, `logs/` isolados); reset do estado em memória do
  circuit-breaker (`scb.reset_memory_state()`) e de qualquer pendência de
  participação (`.pipe/participationPending.json` fica no `tmp_path`,
  isolado por natureza).
- **Relógio controlável:** o circuit-breaker usa relógio injetável
  (`Clock`, já usado em `tests/test_sync_circuit_breaker.py`) — nunca
  `sleep` real.
- **Nunca** fazer `monkeypatch` dos símbolos sob teste (lição do incidente
  #106): `SyncCircuitBreaker`/`apply_changes`/`sync_remote_board` e os
  gatilhos de participação (`reconcile_after_link`,
  `reconcile_remote_presence`, `detect_external_removal`) são exercitados de
  verdade; só a **porta** (`BoardPort` fake) e o **relógio** são
  substituídos.
- **Evidência:** verificar tanto o estado observável (chamadas ao dublê de
  porta, estado do `breaker`, conteúdo da fila) quanto o log estruturado
  (`logs/<data>.json`) quando o caso já exige evidência de log por origem
  (`test-cases.md` de #309/#310).

---

## CT-01 — Suíte completa na linha principal

- **CA de origem:** CA-2 — "Dado que a suíte completa é executada, quando há
  falha, então a falha é corrigida ou registrada com justificativa explícita
  antes do encerramento desta issue." (cenário obrigatório CT-01)
- **Tipo:** execução de suíte (verificação) — não é um novo teste de código.
- **Arquivo/alvo:** suíte inteira em `tests/` via `python -m pytest -q` na
  raiz do repositório, na branch da verificação (base `origin/main`).
- **Pré-condição:** bloco concluído; branch `feature/316-verificacao-bloco-3`
  sincronizada com `origin/main`; dependências de teste instaladas
  (`pytest`, `pyyaml`); execução **offline** (sem rede/subprocesso real — os
  testes já mockam board/subprocess).
- **Passos:**
  1. Executar `python -m pytest -q` a partir de `/app/repo/main`.
  2. Capturar o sumário (total de testes, passados, falhados, pulados) e os
     identificadores de qualquer falha.
  3. Para cada falha: fazer análise de causa-raiz e **classificar** (falha
     de código → divergência CT-03; caso de teste inadequado →
     `revisar-caso-de-teste` na etapa de execução). Nesta etapa de
     **especificação**, apenas registrar o procedimento; a execução ocorre
     na etapa `execucao-testes`.
- **Resultado esperado:** a suíte completa **passa** (0 falhas atribuíveis
  ao bloco 3). O resultado é **registrado** no relatório (contagem +
  evidência do sumário). Se houver falha, ela é corrigida (quando couber no
  escopo) **ou** registrada com justificativa explícita **antes** do
  encerramento — nunca silenciada.
- **Observações:** levantamento preliminar nesta etapa já mostra
  **1785 passed, 26 failed, 17 skipped, 1 xpassed, 13 errors**; as 26
  falhas + 13 erros, confirmados por nome de arquivo/teste, são o **mesmo
  baseline pré-existente** já registrado em
  `doc/quality/verificacao-bloco-1/test-results.md`,
  `doc/quality/verificacao-bloco-2/test-cases.md` e nos `test-results.md`
  próprios de #309 e #310 (formato de log diário descritivo —
  `tests/test_agent_log_descritivo.py` + 1 caso de
  `tests/test_agent_failure_detection.py` — e infraestrutura Docker —
  `tests/test_dockerfile.py`/`tests/test_docker_compose.py`), alheias a
  #309/#310. Execução dirigida dos 11 arquivos pertinentes a #309 e #310
  (listados na tabela "Avaliação da suíte existente") nesta etapa:
  **157 passed, 0 failed**. A confirmação definitiva de que o baseline da
  suíte completa é **exatamente** o mesmo (zero regressão nova) é tarefa da
  etapa `execucao-testes` (comparação de conjuntos de nomes de teste
  falhos contra um worktree isolado de `origin/main`, mesma técnica das
  verificações de bloco anteriores).

## CT-02 — Critério declarado sem cobertura de teste correspondente ⇒ lacuna registrada

- **CA de origem:** CA-1 (veredito por critério com evidência) e CA-7
  (veredito "não verificável" com razão). Cenário obrigatório CT-02.
- **Tipo:** auditoria de cobertura (verificação).
- **Arquivo/alvo:** mapeamento CA (de #309 e #310) → teste existente em
  `tests/`. Fontes:
  `doc/quality/circuit-breaker-sincronismo-escalacao-agente/test-cases.md`
  (#309, CA-1..CA-14) e
  `doc/quality/integridade-participacao-issues-entre-quadros/test-cases.md`
  (#310, CA-1..CA-17), confrontados com os arquivos reais em `tests/` e com
  os respectivos `test-results.md` (vereditos já publicados nas etapas de
  execução de testes de cada entrega).
- **Pré-condição:** lista dos critérios de aceitação de #309 e #310 e dos
  testes que os cobrem (ver tabela "Avaliação da suíte existente").
- **Passos:**
  1. Para cada CA atendido de #309/#310, localizar o(s) teste(s) que o
     cobre(m), usando o mapa de rastreabilidade já publicado nos respectivos
     `test-cases.md`/`test-results.md` de origem.
  2. Marcar cada CA como: **coberto** (teste identificado e verde), **lacuna
     de cobertura** (CA atendido no código mas sem teste que o exercite) ou
     **não verificável** (sem meio disponível para verificar — registrar a
     razão).
  3. Registrar explicitamente no relatório as duas lacunas detectadas nesta
     etapa: a **convergência #309 × #310** em `apply_changes` (issue
     bloqueada ⇒ reconciliação de participação não tentada; falha de
     reconciliação ⇒ contada pelo circuit-breaker) e em `sync_remote_board`
     (plataforma bloqueada ⇒ `detect_external_removal` também suprimida) —
     ver CT-04.
- **Resultado esperado:** o relatório contém, por critério, o veredito e a
  evidência (nome do teste / observação). As duas lacunas de convergência
  são **registradas**; critérios sem meio de verificação recebem **"não
  verificável" com a razão**, nunca "atendido" por suposição.
- **Observações:** as lacunas de convergência, uma vez registradas aqui, são
  **fechadas** por CT-04 dentro do escopo deste bloco (teste de regressão),
  não tratadas como demanda separada — porque o CA de convergência já
  pertence ao escopo da própria verificação (CA-6 da issue #316).

## CT-03 — Comportamento declarado ausente na linha principal ⇒ veredito "não atendido"

- **CA de origem:** CA-4 (divergência corrigível ⇒ teste de regressão +
  versão + CHANGELOG) e CA-5 (divergência que exige escopo novo ⇒ demanda
  separada). Cenário obrigatório CT-03.
- **Tipo:** verificação de comportamento + (condicional) teste de
  regressão.
- **Arquivo/alvo:** comportamento das duas entregas na linha principal:
  - #309: `src/core/sync_circuit_breaker.py` (`SyncCircuitBreaker.record_failure`/
    `record_success`/`issue_blocked`/`platform_blocked`, meio-aberto,
    escalação, `SyncCircuitBreakerFatal`), `src/core/sync.py::apply_changes`
    (gate antes do dispatch, contagem após falha/sucesso), `src/__main__.py`
    (`escalate_pending`, `_sync_fatal`, encerramento com código ≠ 0).
  - #310: `src/core/participation.py` (`classify_participation`, quatro
    estados), `src/core/participation_reconcile.py` (`reconcile_after_link`,
    `reconcile_remote_presence`, `detect_external_removal`,
    `guard_cross_board_link`), `src/core/sync.py`
    (`_reconcile_links_after_apply`, `_apply_change_up`, `_apply_create_down`,
    `_filter_suspended_cross_board_parent`), `src/__main__.py::keep_task`
    (`participation.gate_keep`, `participation.backfill_intent_if_absent`) e
    `sync_remote_board` (`detect_external_removal`).
- **Pré-condição:** para cada CA declarado atendido, há um comportamento
  observável correspondente (teste executável ou inspeção estrutural).
- **Passos:**
  1. Para cada CA, confrontar o declarado com o comportamento presente
     (executando o teste correspondente ou inspecionando o código/estrutura).
  2. Se o comportamento declarado **não** estiver presente (teste
     ausente/vermelho que deveria passar, ou código que contradiz o CA),
     emitir veredito **"não atendido"** com a evidência.
  3. Classificar a divergência:
     - **corrigível no escopo do bloco** → aplicar a correção **com teste
       de regressão** que reproduz a divergência, **incrementar a versão**
       (`src/core/version.py`) e adicionar **entrada no `CHANGELOG.md`**
       (CA-4);
     - **exige escopo novo** → **não** implementar aqui; registrar como
       **demanda separada** no relatório (CA-5).
- **Resultado esperado:** nenhuma divergência silenciosa. Toda ausência vira
  veredito "não atendido" com evidência e um destino explícito (correção com
  regressão + bump + CHANGELOG, **ou** demanda separada). Se **nenhuma**
  divergência for encontrada, este caso resulta em "não aplicável" e o
  desfecho é o CT-05.
- **Observações:** o incremento de versão e a entrada no CHANGELOG **só**
  ocorrem no ramo "divergência corrigível" (CA-4). É proibido inventar
  mudança para justificar bump (ver CT-05). A leitura de código feita nesta
  etapa (ver "Avaliação da suíte existente" e "Natureza desta entrega") não
  encontrou nenhum comportamento declarado e ausente nas duas entregas —
  todos os pontos de ancoragem citados nos `test-cases.md`/`test-results.md`
  de origem (#309/#310) existem de fato no código e têm teste verde
  correspondente; a confirmação definitiva (execução real, incluindo os
  casos novos de CT-04) ocorre na etapa `execucao-testes`.

## CT-04 — Convergência #309 × #310 nos pontos de decisão `apply_changes` e `sync_remote_board` (coexistência sem sombreamento)

- **CA de origem:** CA-6 — "Dado duas entregas do bloco que atuam no mesmo
  ponto de decisão do produto, quando a verificação ocorre, então há
  evidência registrada de que ambas permanecem efetivas em conjunto, sem que
  uma anule a outra." Cenário obrigatório CT-04.
- **Tipo:** integração (testes **novos** — fecham as lacunas registradas em
  CT-02).
- **Arquivo/alvo:** novo arquivo `tests/test_convergencia_bloco3_sync.py`,
  exercitando o **código real** de `src/core/sync.py::apply_changes` e de
  `src/__main__.py::sync_remote_board`. **Vedado** reimplementar a lógica de
  bloqueio do circuit-breaker ou de classificação/reconciliação de
  participação dentro do teste (anti-padrão de `test_loop_guard.py`/
  incidente #106, já identificado e corrigido nas verificações dos blocos 1
  e 2).
- **Pré-condição comum:** `monkeypatch.chdir(tmp_path)` autouse; `.pipe/`
  isolado; `SyncCircuitBreaker` real com relógio controlável (`Clock`,
  reaproveitado de `tests/test_sync_circuit_breaker.py`); um `BoardPort`
  fake que estenda o `FakePort` já existente em
  `tests/test_sync_circuit_breaker.py` para também implementar
  `list_participations`/`remove_from_board` de forma controlável (padrão de
  `tests/test_participation_reconciliation.py`) — **nenhum** dos dois é
  mockado via `monkeypatch` do símbolo sob teste; snapshot populado com uma
  issue com vínculo pai/filho cross-board (ou presença propagada, conforme o
  sub-caso).

Os sub-casos abaixo comprovam que **nenhuma das duas entregas sombreia a
outra** nos dois pontos de decisão:

- **CT-04a — Issue bloqueada pelo circuit-breaker: reconciliação de
  participação NÃO é tentada (bloqueio não é mascarado por #310):**
  - **Pré-condição:** issue `#42` do board `entrega` já bloqueada pelo
    circuit-breaker (`issue.max_failures` falhas consecutivas reais,
    seguindo a mesma sequência de `block_issue`/`cycle` de
    `tests/test_sync_circuit_breaker.py`); um item `CHANGE_UP` para `#42`
    enfileirado, com um comando `/parent` para uma issue de outro board
    configurado (vínculo cross-board que dispararia
    `_reconcile_links_after_apply` se processado).
  - **Resultado esperado:** `apply_changes` retém o item na fila sem
    tentativa (mesmo invariante de CT-02 de #309); **nenhuma** chamada a
    `list_participations`/`remove_from_board` ocorre no fake de porta — a
    reconciliação de participação não é sequer avaliada para a issue
    bloqueada. Prova que o bloqueio do circuit-breaker (#309) tem efeito
    real sobre o fluxo de participação (#310) e não é contornado por ele.
- **CT-04b — Issue livre, falha na reconciliação de participação: o
  circuit-breaker CONTA a falha como qualquer outra falha de sincronismo
  (participação não mascara o circuit-breaker):**
  - **Pré-condição:** issue `#42` sem bloqueio ativo; o mesmo `CHANGE_UP`
    com vínculo cross-board; o fake de porta configurado para
    `list_participations`/`remove_from_board` levantar uma exceção
    (`ParticipationQueryError` ou erro genérico, conforme o sub-caso) ao ser
    chamado para `#42`.
  - **Resultado esperado:** a exceção de participação propaga por
    `_apply_change_up`/`_reconcile_links_after_apply` até o
    `except Exception` de `apply_changes`; `classify_error` a classifica
    (tipicamente `transitorio`, pela ausência de substring de
    validação/definitivo na mensagem); `breaker.record_failure` é chamado
    com essa falha, incrementando o contador de falhas consecutivas da
    issue exatamente como incrementaria para qualquer outro erro de
    sincronismo. Repetindo o cenário `issue.max_failures` vezes, a issue
    **bloqueia** pelo circuit-breaker em decorrência de falhas cuja causa
    raiz é a reconciliação de participação — provando que #310 não tem um
    caminho de erro "invisível" ao circuit-breaker de #309.
- **CT-04c — Plataforma bloqueada: `detect_external_removal` também não é
  chamada (bloqueio de plataforma suprime igualmente a detecção de remoção
  externa de participação):**
  - **Pré-condição:** plataforma do board `entrega` bloqueada pelo
    circuit-breaker (`platform.max_blocked_issues` issues distintas
    bloqueadas na janela, reaproveitando a sequência de
    `tests/test_sync_circuit_breaker.py::TestPlatformBlock`); uma pendência
    de participação já registrada em `.pipe/participationPending.json` para
    uma issue desse board (simulando uma presença `unresolved` adiada
    anteriormente).
  - **Passos:** chamar `sync_remote_board(board_id, config)` com a
    plataforma bloqueada.
  - **Resultado esperado:** `sync_remote_board` retorna `False` antes de
    chamar tanto `sync_remote` quanto
    `participation_reconcile.detect_external_removal` — **nenhuma** chamada
    a `list_participations` ocorre no fake de porta para a pendência
    registrada; a pendência permanece inalterada (nem resolvida, nem
    removida por "remoção externa" presumida). Prova que o bloqueio de
    plataforma (#309) é a fonte única de decisão sobre QUALQUER I/O de
    sincronismo daquele board nesse ciclo, incluindo o da detecção de
    remoção externa de participação (#310) — sem que esta última "escape"
    do bloqueio por rodar em um caminho de chamada separado.
  - **Contraprova (anti-sombreamento):** com a plataforma desbloqueada no
    mesmo cenário, `detect_external_removal` **é** chamada normalmente — a
    supressão é estritamente condicionada ao bloqueio ativo, não a um efeito
    colateral permanente introduzido por #309 sobre #310.
- **Resultado esperado (consolidado):** existe **evidência automatizada e
  executável** de que o bloqueio do circuit-breaker de sincronismo (#309) e
  a reconciliação/detecção de participação (#310) **co-existem** nos dois
  pontos de decisão (`apply_changes`, `sync_remote_board`) sem que uma
  mascare o efeito da outra: bloqueio real impede qualquer tentativa de
  reconciliação (de issue ou de plataforma); falha real de reconciliação é
  contada pelo circuit-breaker com a mesma política de qualquer falha de
  sincronismo. Se a convergência regredir (ex.: uma issue bloqueada ainda
  assim disparar `remove_from_board`, ou uma falha de participação deixar
  de incrementar o contador de falhas da issue), o teste falha.
- **Observações:**
  - **Isolamento (lição #106):** proibido `monkeypatch` dos símbolos sob
    teste (`SyncCircuitBreaker.record_failure`/`issue_blocked`/
    `platform_blocked`, `apply_changes`, `sync_remote_board`,
    `reconcile_after_link`, `reconcile_remote_presence`,
    `detect_external_removal`). Patches permitidos **apenas** nas
    fronteiras reais de ambiente/execução (o `BoardPort` fake e o relógio).
  - Este é o **único** caso desta entrega que adiciona código de teste; é
    um teste de **regressão da verificação**, dentro do escopo (o CA de
    convergência já existe na issue #316), **sem** ampliar o escopo de
    #309 ou #310. Fecha uma lacuna de cobertura de um critério já aceito —
    não corrige comportamento do produto —, logo acompanha o relatório; o
    bump de versão só se aplica se, ao escrevê-lo, uma **divergência de
    comportamento** real for revelada (então vira CT-03/CA-4).

## CT-05 — Verificação sem divergência (relatório, sem código, sem bump)

- **CA de origem:** CA-3 — "Dado que nenhuma divergência é encontrada,
  quando a verificação encerra, então o relatório registra o resultado 'sem
  divergência' e a entrega é válida sem alteração de código-fonte e,
  portanto, sem incremento de versão." Cenário obrigatório CT-05.
- **Tipo:** manual/revisão (fecho da verificação) + guarda objetiva.
- **Arquivo/alvo:** o **relatório de verificação** (entregável da etapa de
  execução de testes, em `doc/quality/verificacao-bloco-3/`); coerência de
  versão e CHANGELOG: `src/core/version.py` (`VERSION`, hoje `1.27.5`) e
  `CHANGELOG.md`.
- **Pré-condição:** CT-01 verde (suíte completa passa, descontadas as
  falhas de baseline alheias ao bloco), CT-02 sem lacuna não tratada, CT-03
  sem divergência de comportamento, CT-04 verde.
- **Passos:**
  1. Confirmar que todos os vereditos são "atendido" (ou "não verificável"
     com razão), sem nenhum "não atendido" pendente.
  2. Confirmar coerência versão↔CHANGELOG↔entregue: `CHANGELOG.md` reflete
     #309 (1.26.0) e #310 (1.23.0/1.23.1), **sem** entrada nova inventada
     para esta verificação.
  3. Registrar no relatório o desfecho **"sem divergência"**.
  4. **Garantir que não há alteração de código-fonte de produto** atribuível
     a esta verificação: `git diff --stat origin/main...HEAD` **não** mostra
     mudanças em `src/` (apenas documentação em `doc/quality/…` e, se CT-04
     adicionou o teste de convergência, o arquivo de teste em `tests/`).
- **Resultado esperado:** o relatório registra "sem divergência"; **`VERSION`
  inalterada** (`1.27.5`) e **nenhuma entrada nova** no `CHANGELOG.md`; o
  `diff` contra `origin/main` restringe-se a `doc/quality/verificacao-bloco-3/`
  (relatório + estes casos) e, no máximo, ao teste de convergência de CT-04
  em `tests/`. Nenhuma mudança em `src/`.
- **Observações:** a adição do teste de CT-04 em `tests/` **não** é
  "alteração de código-fonte do produto" (não toca `src/`) e **não** exige
  bump: fecha cobertura de um critério já aceito. O bump/CHANGELOG ficam
  **estritamente** condicionados ao ramo "divergência corrigível" de
  CT-03/CA-4. Inventar mudança para justificar a entrega é **proibido** pelo
  escopo (seção "Fora de escopo" e "Riscos e pontos de atenção" do corpo da
  issue).

---

## Notas de execução para a etapa `execucao-testes`

- **Suíte completa:** `python -m pytest -q` a partir de `/app/repo/main`;
  registrar sumário e qualquer falha com causa-raiz (CT-01). Comparar o
  **conjunto de nomes** de testes falhos contra o baseline conhecido
  (`tests/test_agent_log_descritivo.py` + 1 caso de
  `tests/test_agent_failure_detection.py` + `tests/test_dockerfile.py`/
  `tests/test_docker_compose.py`) para provar **zero regressão nova** (mesma
  técnica usada nas verificações dos blocos 1 e 2: comparação via worktree
  limpo de `origin/main`).
- **Foco adicional** nos 11 arquivos de #309/#310 listados na tabela de
  "Avaliação da suíte existente" e no novo
  `tests/test_convergencia_bloco3_sync.py` (CT-04a/b/c).
- **Offline:** nenhum teste pode depender de rede, `gh` real ou subprocesso
  real; usar fakes/mocks e `tmp_path` (padrão já adotado em toda a suíte das
  duas entregas).
- **Relógio controlável:** onde pertinente (janela/duração do
  circuit-breaker, intervalo de adiamento de participação), relógio sempre
  mockado — nunca `sleep` real.
- **Veredito por critério:** o relatório final (`test-results.md` /
  relatório de verificação) deve conter **CA-1..CA-7** com veredito **e
  evidência** (nome do teste executado ou observação estrutural). Critério
  sem meio de verificação → **"não verificável" com razão**.
- **Precedência do desfecho:** se CT-01..CT-04 passam e CT-03 não revela
  divergência, o desfecho é CT-05 ("sem divergência", sem bump). Divergência
  corrigível → CT-03/CA-4 (regressão + bump + CHANGELOG). Divergência que
  amplia escopo → CA-5 (demanda separada).

## Devolução ao planejamento (quando aplicável)

Não aplicável: o escopo da issue #316 está completo e internamente
consistente para derivar os casos. As duas entregas auditadas (#309, #310)
estão identificadas, versionadas e com `test-cases.md`/`test-results.md`
próprios já publicados; a leitura do código confirmou os pontos de
ancoragem citados (núcleos em `src/core/sync_circuit_breaker.py`,
`src/core/participation.py`, `src/core/participation_reconcile.py`, e os
dois pontos de convergência em `src/core/sync.py::apply_changes` e
`src/__main__.py::sync_remote_board`). Nenhuma decisão de negócio em aberto
impede a especificação. Avançar para `desenvolvimento`.
