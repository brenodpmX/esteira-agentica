# Casos de Teste — Verificação do bloco 1 (fundações de execução e de sincronização)

- **Issue:** #314
- **Story relacionada:** #314 — "Verificação do bloco 1 — fundações de execução
  e de sincronização" (auditoria integrada das entregas #303 e #304)
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/314-verificacao-bloco-1`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da issue
> #314. Cada caso tem resultado esperado explícito e verificável. Os testes são
> da suíte Python do motor (pytest, em `tests/`), salvo os marcados como
> **manual/revisão** (auditoria documental).

---

## Natureza desta entrega (ler antes de implementar os casos)

Esta **não** é uma entrega de funcionalidade: é uma **verificação de bloco**. O
seu produto é um **relatório de verificação** com um **veredito por critério de
aceitação** (atendido / não atendido / não verificável), cada veredito apoiado em
**comportamento observado ou teste executado** — nunca em releitura de texto.

As duas entregas auditadas já estão na linha principal:

- **#303** — classificação de resultado de execução por canais estruturados +
  recuperação segura de interrupção (`src/core/execution.py`,
  `src/__main__.py::_dispatch_with_recovery`, `src/core/config.py::resolve_retry`,
  `src/core/support_paths.py`, `src/core/context_generator.py`). Registrada no
  `CHANGELOG.md` seção **1.16.0**.
- **#304** — modelo único de sincronização (`src/core/sync.py::sync_remote`,
  caminho único de descoberta remota; `src/__main__.py::detect_local_all` /
  `sync_remote_board`). Registrada no `CHANGELOG.md` seção **1.15.0**.

Consequências para a implementação dos casos:

1. **Desfecho "sem divergência" é válido.** Se a verificação confirmar as duas
   entregas efetivas e a suíte verde, o único artefato é o **relatório**: **sem
   alteração de código-fonte e sem incremento de versão** (CA-3 / CT-05).
2. **O único caso que exige código novo de teste é o CT-04** (ponto de
   convergência #303 × #304): a suíte atual **não** possui um teste que exercite
   o código real do loop principal provando a coexistência das duas entregas (ver
   "Avaliação da suíte existente" abaixo). Esse teste é um **teste de regressão da
   verificação**, não ampliação de escopo das entregas — ele apenas comprova,
   automatizando, o CA de convergência que já existe no corpo da issue.
3. Os demais casos (CT-01, CT-02, CT-03, CT-05) são majoritariamente **execução e
   auditoria** da suíte e dos artefatos já presentes; só geram alteração de
   código se uma **divergência** for encontrada (CT-03), situação em que a
   correção exige teste de regressão + bump de versão + entrada no CHANGELOG
   (CA-4).

---

## Avaliação da suíte existente (base da especificação)

Levantamento feito nesta etapa, sobre a linha principal (`origin/main` @
`c700e97`):

| Entrega | Cobertura existente | Veredito preliminar de cobertura |
|---------|---------------------|----------------------------------|
| #303 — classificação por canais estruturados | `tests/test_execucao_autonoma_confiavel.py`, `tests/test_agent_failure_detection.py`, `tests/test_error_classification.py` | Coberto (classes `SUCEDIDO/FALHA/UNKNOWN_OUTCOME/DEFINITE_NOT_STARTED/FALHA_PERSISTENTE`, detecção só-por-canal, retry seguro, defaults `retry.*`) |
| #303 — caminhos de apoio / contexto / doc | `test_execucao_autonoma_confiavel.py` (grupos B/C/E), `test_context_generator.py` | Coberto |
| #304 — modelo único de sync | `tests/test_sync_unico.py`, `tests/test_sync_unico_sem_segundo_modo.py`, `tests/test_sync_unico_nomenclatura.py`, `tests/test_sync_unico_log.py`, `tests/test_sync_unico_deps.py`, `tests/test_detect_local_all.py` | Coberto (caminho único, ausência de 2º modo, sem corte `last_board_update`, sem `detect_board_changes`/`list_issues_since`) |
| **Convergência #303 × #304 no loop principal** | `tests/test_loop_guard.py` | **LACUNA** — ver abaixo |

**Lacuna confirmada (fundamenta CT-04):** `tests/test_loop_guard.py` **reproduz a
lógica do loop `inline` dentro do próprio teste** (ex.:
`had_changes = True; if not had_changes: ...`) em vez de exercitar o código real
de `src/__main__.py`. Ele faz `patch` de `sync_board`/`keep_task`/`call_agent`,
mas reimplementa localmente a decisão `if not had_changes`. É o **mesmo
anti-padrão** do incidente #106 (teste que não exercita o código sob teste e
mascara ausência de cobertura). **Nenhum** teste da suíte assere que:

- o resultado da **classificação de execução** (#303 — o `ExecutionResult`
  devolvido por `_dispatch_with_recovery`/`call_agent`) e
- o resultado da **sincronização** (#304 — os booleanos de `detect_local_all` e
  `sync_remote_board`)

**co-alimentam** a seleção de tarefa (`keep_task`) e o controle de ociosidade
(`sleep_time`) **sem que uma anule ou sombreie a outra**. Essa é exatamente a
coexistência que o CA de convergência exige comprovar — e é o que o CT-04 fixa
como teste de regressão real do loop.

---

## Rastreabilidade (CA → casos)

| # | Critério de aceitação (resumo) | Caso(s) |
|---|--------------------------------|---------|
| CA-1 | Existe relatório que lista **cada critério verificado e seu veredito** | CT-01 (insumo), CT-05 (relatório) + o relatório final consolida CA-1..CA-7 |
| CA-2 | Suíte completa executada; **falha é corrigida ou registrada** com justificativa antes de encerrar | CT-01 |
| CA-3 | **Sem divergência** ⇒ relatório "sem divergência", **sem alteração de código nem bump de versão** | CT-05 |
| CA-4 | Divergência **corrigível no escopo** ⇒ teste de regressão + **incremento de versão** + entrada no CHANGELOG | CT-03 |
| CA-5 | Divergência que **exige escopo novo** ⇒ registrada como **demanda separada**, não implementada aqui | CT-03 |
| CA-6 | **#303 e #304 convergem** no loop principal (seleção de tarefa + ociosidade) e **permanecem efetivas juntas**, sem uma sombrear a outra | **CT-04** |
| CA-7 | Critério **não verificável** com os meios disponíveis ⇒ veredito "não verificável" **com a razão** | CT-02 (quando a lacuna impede verificar), e tratamento transversal no relatório |

> Mapeamento dos cenários obrigatórios da issue → casos: CT-01 (suíte completa),
> CT-02 (critério sem cobertura ⇒ lacuna registrada), CT-03 (comportamento
> declarado ausente ⇒ "não atendido" + correção/demanda), CT-04 (convergência),
> CT-05 (verificação sem divergência). Numeração 1:1 com a tabela de "Cenários de
> teste obrigatórios" do corpo da issue.

---

## CT-01 — Suíte completa executa sem falha na linha principal

- **CA de origem:** CA-2 — "Dado que a suíte completa é executada, quando há
  falha, então a falha é corrigida ou registrada com justificativa explícita
  antes do encerramento." (cenário obrigatório CT-01)
- **Tipo:** execução de suíte (verificação) — não é um novo teste de código.
- **Arquivo/alvo:** suíte inteira em `tests/` via
  `python -m pytest -q` na raiz do repositório, na branch da verificação (base
  `origin/main`).
- **Pré-condição:** bloco concluído; branch `feature/314-verificacao-bloco-1`
  sincronizada com `origin/main`; dependências de teste instaladas; execução
  **offline** (sem rede/subprocesso real — os testes já mockam board/subprocess).
- **Passos:**
  1. Executar `python -m pytest -q` a partir de `/app/repo/main`.
  2. Capturar o sumário (total de testes, passados, falhados, pulados) e os
     identificadores de qualquer falha.
  3. Para cada falha: fazer análise de causa-raiz e **classificar** (falha de
     código → divergência CT-03; caso de teste inadequado → `revisar-caso-de-teste`
     na etapa de execução). Nesta etapa de **especificação**, apenas registrar o
     procedimento; a execução ocorre na etapa `execucao-testes`.
- **Resultado esperado:** a suíte completa **passa** (0 falhas). O resultado é
  **registrado** no relatório (contagem + evidência do sumário). Se houver falha,
  ela é corrigida (quando couber no escopo) **ou** registrada com justificativa
  explícita **antes** do encerramento — nunca silenciada.
- **Observações:** este caso materializa o entregável "suíte de testes completa
  passando na linha principal". A simples leitura de que "as entregas existem"
  **não** satisfaz CA-2; é obrigatório **executar** e registrar o resultado.

## CT-02 — Critério declarado sem cobertura de teste correspondente ⇒ lacuna registrada

- **CA de origem:** CA-1 (veredito por critério com evidência) e CA-7 (veredito
  "não verificável" com razão). Cenário obrigatório CT-02.
- **Tipo:** auditoria de cobertura (verificação).
- **Arquivo/alvo:** mapeamento CA (de #303 e #304) → teste existente em `tests/`.
  Fontes: `doc/quality/execucao-autonoma-confiavel/test-cases.md` (#303) e
  `doc/quality/unificar-sincronizacao-boards/test-cases.md` (#304), confrontados
  com os arquivos reais em `tests/`.
- **Pré-condição:** lista dos critérios de aceitação de #303 e #304 e dos testes
  que os cobrem.
- **Passos:**
  1. Para cada CA atendido de #303/#304, localizar o(s) teste(s) que o cobre(m).
  2. Marcar cada CA como: **coberto** (teste identificado e verde), **lacuna de
     cobertura** (CA atendido no código mas sem teste que o exercite) ou **não
     verificável** (sem meio disponível para verificar — registrar a razão).
  3. Registrar explicitamente no relatório a lacuna detectada nesta etapa: a
     **convergência #303 × #304** (ver CT-04), hoje sem teste real (apenas
     `test_loop_guard.py`, que reimplementa a lógica inline).
- **Resultado esperado:** o relatório contém, por critério, o veredito e a
  evidência (nome do teste / observação). Pelo menos a lacuna da convergência é
  **registrada**; critérios sem meio de verificação recebem **"não verificável"
  com a razão**, nunca "atendido" por suposição.
- **Observações:** a lacuna de convergência, uma vez registrada aqui, é
  **fechada** por CT-04 dentro do escopo deste bloco (teste de regressão), não
  tratada como demanda separada — porque o CA de convergência já pertence ao
  escopo da própria verificação.

## CT-03 — Comportamento declarado ausente na linha principal ⇒ veredito "não atendido"

- **CA de origem:** CA-4 (divergência corrigível ⇒ teste de regressão + versão +
  CHANGELOG) e CA-5 (divergência que exige escopo novo ⇒ demanda separada).
  Cenário obrigatório CT-03.
- **Tipo:** verificação de comportamento + (condicional) teste de regressão.
- **Arquivo/alvo:** comportamento das entregas na linha principal:
  - #303: `src/core/execution.py` (classes de resultado),
    `src/__main__.py::_dispatch_with_recovery` (fail-closed p/ `UNKNOWN_OUTCOME`;
    retry inline **só** p/ `DEFINITE_NOT_STARTED`),
    `src/adapters/kiro_cli_agent.py::_detect_failure` (só canais estruturados),
    `src/core/config.py::resolve_retry` (defaults/validação `retry.*`),
    `src/core/support_paths.py` (resolução por item).
  - #304: `src/core/sync.py::sync_remote` (caminho único, `change-down`
    sempre `fullsync=True`, sem corte `last_board_update`, sem
    `detect_board_changes`/`list_issues_since`).
- **Pré-condição:** para cada CA declarado atendido, há um comportamento
  observável correspondente (teste executável ou inspeção estrutural).
- **Passos:**
  1. Para cada CA, confrontar o declarado com o comportamento presente
     (executando o teste correspondente ou inspecionando o código/estrutura).
  2. Se o comportamento declarado **não** estiver presente (teste ausente/vermelho
     que deveria passar, ou código que contradiz o CA), emitir veredito **"não
     atendido"** com a evidência.
  3. Classificar a divergência:
     - **corrigível no escopo do bloco** → aplicar a correção **com teste de
       regressão** que reproduz a divergência, **incrementar a versão**
       (`src/core/version.py`) e adicionar **entrada no `CHANGELOG.md`** (CA-4);
     - **exige escopo novo** → **não** implementar aqui; registrar como **demanda
       separada** no relatório (CA-5).
- **Resultado esperado:** nenhuma divergência silenciosa. Toda ausência vira
  veredito "não atendido" com evidência e um destino explícito (correção com
  regressão + bump + CHANGELOG, **ou** demanda separada). Se **nenhuma**
  divergência for encontrada, este caso resulta em "não aplicável" e o desfecho é
  o CT-05.
- **Observações:** o incremento de versão e a entrada no CHANGELOG **só** ocorrem
  no ramo "divergência corrigível" (CA-4). É proibido inventar mudança para
  justificar bump (ver CT-05).

## CT-04 — Convergência #303 × #304 no loop principal (coexistência sem sombreamento)

- **CA de origem:** CA-6 — "Dado que #303 (classificação de resultado de execução
  do agente) e #304 (modelo único de sincronização) convergem no loop principal —
  onde o resultado da execução e o resultado da sincronização alimentam juntos a
  seleção de tarefa e o controle de ociosidade —, quando a verificação ocorre,
  então há evidência registrada de que ambas permanecem efetivas em conjunto, sem
  que uma anule ou sombreie a outra nesse ponto." Cenário obrigatório CT-04.
- **Tipo:** integração (teste **novo** — fecha a lacuna registrada em CT-02).
- **Arquivo/alvo:** novo arquivo `tests/test_convergencia_bloco1_loop.py`,
  exercitando o **código real** do loop em `src/__main__.py`
  (`detect_local_all`, `sync_remote_board`, `process_queue`, `keep_task`,
  `call_agent`/`_dispatch_with_recovery`, `sleep_time`). **Vedado** reimplementar
  a lógica do loop dentro do teste (anti-padrão de `test_loop_guard.py` e do
  incidente #106).
- **Pré-condição comum:** `.pipe/` isolado em `tmp_path`; `ChangeQueue`, snapshots
  e `BOARDS_DIR` redirecionados para `tmp_path`; `time.sleep` **mockado**;
  `KiroCliAgent.execute`/board/subprocess **fakes** (offline). O loop é dirigido
  de forma determinística (ex.: executar um número fixo de iterações e então
  erguer `_Shutdown`/`KeyboardInterrupt`, ou extrair uma função de "um ciclo" e
  invocá-la diretamente — desde que seja o código real, não uma cópia).

Os sub-casos abaixo comprovam que **nenhuma das duas entregas sombreia a outra**
no ponto de decisão. Em todos, asserir sobre o **código real** (contadores de
invocação, chamadas de `time.sleep`, resultado classificado propagado):

- **CT-04a — Sync com mudança sombreia a execução (down vence; sem sleep):**
  - **Pré-condição:** `detect_local_all` **ou** `sync_remote_board` retorna
    `True` (há mudança); existe tarefa elegível no board.
  - **Resultado esperado:** o ciclo **não** chama `keep_task`/`call_agent` nesse
    passo (volta ao início para estabilizar) **e não** chama `sleep_time`. Prova
    que o resultado de **sincronização (#304)** tem efeito real no fluxo e **não é
    sombreado** pela presença de tarefa.
- **CT-04b — Sem mudança + tarefa elegível ⇒ executa agente e propaga a
  classificação (#303 efetiva):**
  - **Pré-condição:** `detect_local_all` e `sync_remote_board` retornam `False`;
    fila vazia; `keep_task` devolve uma `task`; o adapter fake produz um
    `ExecutionResult` **classificado** (ex.: `SUCEDIDO`, depois um caso
    `UNKNOWN_OUTCOME` e um `DEFINITE_NOT_STARTED`).
  - **Resultado esperado:** `call_agent` → `_dispatch_with_recovery` é chamado; o
    `ExecutionResult` é **devolvido ao loop** com a classe correta; para
    `UNKNOWN_OUTCOME` há **uma única** invocação do subprocesso e **nenhum**
    `time.sleep` de backoff; para `DEFINITE_NOT_STARTED` o retry inline ocorre
    conforme `retry.*`. Prova que a **classificação de execução (#303)** segue
    efetiva **no ponto de convergência**, não anulada pelo caminho de sync.
    **Não** se executa `sleep_time` quando havia tarefa.
- **CT-04c — Sem mudança + sem tarefa em nenhum board ⇒ ociosidade (sleep):**
  - **Pré-condição:** `detect_local_all` e `sync_remote_board` retornam `False`
    em **todos** os boards; `keep_task` retorna `None` para todos; fila vazia.
  - **Resultado esperado:** após percorrer todos os boards sem tarefa, o loop
    chama `sleep_time` **exatamente uma vez** por varredura ociosa. Prova que o
    controle de **ociosidade** depende **conjuntamente** do resultado de
    sincronização (`had_changes=False`) **e** da seleção de tarefa
    (`keep_task=None`): nenhuma das duas sozinha dispara o sleep.
  - **Contraprova (anti-sombreamento):** com `had_changes=True` **ou**
    `keep_task` devolvendo tarefa, `sleep_time` **não** é chamado — confirmando
    que o sleep não é disparado por uma só das entregas.
- **CT-04d — `AUTO_ADVANCED` mantém o board e força novo sync (sem sleep, sem
  execução):**
  - **Pré-condição:** sem mudança no primeiro passo; `keep_task` retorna
    `AUTO_ADVANCED`.
  - **Resultado esperado:** o loop **reinicia** mantendo o board atual (não chama
    `call_agent` nem `sleep_time` nesse ciclo), forçando nova descoberta —
    comprovando que a seleção de tarefa (#303/loop) e o re-sync (#304) encadeiam
    sem conflito.
- **Resultado esperado (consolidado):** existe **evidência automatizada e
  executável** de que o resultado da classificação de execução (#303) e o
  resultado da sincronização (#304) **co-alimentam** `keep_task` + `sleep_time`
  sem que uma anule ou sombreie a outra. O teste exercita o **código real** do
  loop; se a lógica de convergência regredir (ex.: `sleep` disparado com mudança
  pendente, ou `UNKNOWN_OUTCOME` passando a disparar retry/backoff), o teste
  falha.
- **Observações:**
  - **Isolamento (lição #106):** proibido `monkeypatch` do próprio método sob
    teste ou reimplementação da lógica do loop no teste. Patches permitidos
    **apenas** nas fronteiras (adapter/board/subprocess/`time.sleep`), não na
    decisão sob verificação.
  - Este é o **único** caso desta entrega que adiciona código de teste; é um
    teste de **regressão da verificação**, dentro do escopo (o CA de convergência
    já existe), **sem** ampliar o escopo de #303 ou #304. Como fecha uma lacuna de
    cobertura de um critério já aceito — e não corrige comportamento do produto —
    acompanha o relatório; o bump de versão só se aplica se, ao escrevê-lo, uma
    **divergência de comportamento** do loop for revelada (então vira CT-03/CA-4).

## CT-05 — Verificação sem divergência (relatório, sem código, sem bump)

- **CA de origem:** CA-3 — "Dado que nenhuma divergência é encontrada, quando a
  verificação encerra, então o relatório registra o resultado 'sem divergência' e
  a entrega é válida sem alteração de código-fonte e, portanto, sem incremento de
  versão." Cenário obrigatório CT-05.
- **Tipo:** manual/revisão (fecho da verificação) + guarda objetiva.
- **Arquivo/alvo:** o **relatório de verificação** (entregável da etapa de
  execução de testes, em `doc/quality/verificacao-bloco-1/`); coerência de versão
  e CHANGELOG: `src/core/version.py` (`VERSION`) e `CHANGELOG.md`.
- **Pré-condição:** CT-01 verde (suíte completa passa), CT-02 sem lacuna não
  tratada, CT-03 sem divergência de comportamento, CT-04 verde.
- **Passos:**
  1. Confirmar que todos os vereditos são "atendido" (ou "não verificável" com
     razão), sem nenhum "não atendido" pendente.
  2. Confirmar coerência versão↔CHANGELOG↔entregue: `VERSION` e o `CHANGELOG.md`
     refletem #303 (1.16.0) e #304 (1.15.0), **sem** entrada nova inventada para
     esta verificação.
  3. Registrar no relatório o desfecho **"sem divergência"**.
  4. **Garantir que não há alteração de código-fonte** atribuível a esta
     verificação: `git diff --stat` da branch de verificação contra `origin/main`
     **não** mostra mudanças em `src/` (apenas documentação em `doc/quality/…` e,
     se CT-04 adicionou o teste de convergência, o arquivo de teste em `tests/`).
- **Resultado esperado:** o relatório registra "sem divergência"; **`VERSION`
  inalterada** e **nenhuma entrada nova** no `CHANGELOG.md`; o `diff` contra
  `origin/main` restringe-se a `doc/quality/verificacao-bloco-1/` (relatório +
  estes casos) e, no máximo, ao teste de convergência de CT-04 em `tests/`.
  Nenhuma mudança em `src/`.
- **Observações:** a adição do teste de CT-04 em `tests/` **não** é "alteração de
  código-fonte do produto" (não toca `src/`) e **não** exige bump: fecha cobertura
  de um critério já aceito. O bump/CHANGELOG ficam **estritamente** condicionados
  ao ramo "divergência corrigível" de CT-03/CA-4. Inventar mudança para justificar
  a entrega é **proibido** pelo escopo.

---

## Notas de execução para a etapa `execucao-testes`

- **Suíte completa:** `python -m pytest -q` a partir de `/app/repo/main`;
  registrar sumário e qualquer falha com causa-raiz (CT-01). Foco adicional nos
  arquivos de #303/#304 e no novo `tests/test_convergencia_bloco1_loop.py`
  (CT-04).
- **Offline:** nenhum teste pode depender de rede, `gh` real ou subprocesso real;
  usar fakes/mocks e `tmp_path` (padrão já adotado em `test_detect_local_all.py` e
  `test_loop_guard.py`).
- **Sem espera real:** `time.sleep` sempre mockado (CT-04); asserir chamadas, não
  esperar tempo.
- **Veredito por critério:** o relatório final (`test-results.md` /
  relatório de verificação) deve conter **CA-1..CA-7** com veredito **e evidência**
  (nome do teste executado ou observação estrutural). Critério sem meio de
  verificação → **"não verificável" com razão**.
- **Precedência do desfecho:** se CT-01..CT-04 passam e CT-03 não revela
  divergência, o desfecho é CT-05 ("sem divergência", sem bump). Divergência
  corrigível → CT-03/CA-4 (regressão + bump + CHANGELOG). Divergência que amplia
  escopo → CA-5 (demanda separada).
