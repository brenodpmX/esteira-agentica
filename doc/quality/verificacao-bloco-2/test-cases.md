# Casos de Teste — Verificação do bloco 2 (estrutura de board, contexto do agente e limites de execução)

- **Issue:** #315
- **Story relacionada:** #315 — "Verificação do bloco 2 — estrutura de board,
  contexto do agente e limites de execução" (auditoria integrada das entregas
  #305, #306, #307 e #308)
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-02
- **Branch:** `feature/315-verificacao-bloco-2`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da issue
> #315. Cada caso tem resultado esperado explícito e verificável. Os testes são
> da suíte Python do motor (pytest, em `tests/`), salvo os marcados como
> **manual/revisão** (auditoria documental).

---

## Natureza desta entrega (ler antes de implementar os casos)

Esta **não** é uma entrega de funcionalidade: é uma **verificação de bloco**. O
produto é um **relatório de verificação** com um **veredito por critério de
aceitação** (atendido / não atendido / não verificável) de cada uma das quatro
entregas auditadas, cada veredito apoiado em **comportamento observado ou teste
executado** — nunca em releitura de texto.

As quatro entregas já estão na linha principal (`origin/main` @ `dd3a634`):

- **#305** — Retirada segura de colunas de board com migração, bloqueio,
  retomada e evidência. Núcleo `src/core/column_withdrawal.py`. Registrada no
  `CHANGELOG.md` seção **1.17.0**.
- **#306** — Limitador de reexecuções de agente por contexto com contenção e
  retomada humana. Núcleo `src/core/agent_circuit_break.py`. Registrada na
  seção **1.19.0**.
- **#307** — Registro de execução de agentes com consolidação por linhagem
  histórica. Núcleo `src/core/execution_record.py`. Registrada na seção
  **1.20.0**.
- **#308** — Composição em camadas do prompt e do contexto entregues ao agente.
  Núcleo `src/core/composition.py`. Registrada na seção **1.18.0**.

Consequências para a implementação dos casos:

1. **Desfecho "sem divergência" é válido.** Se a verificação confirmar as
   quatro entregas efetivas e a suíte verde, o único artefato é o
   **relatório**: **sem alteração de código-fonte e sem incremento de versão**
   (CA-3/CT-05 da issue).
2. **O ponto de convergência do bloco (CT-04 da issue) é #306 × #307** no
   mesmo ponto de decisão do produto (`src/__main__.py::call_agent`): o
   limitador de reexecuções (#306, via `_admit_circuit_break`) e o registro de
   execução (#307, via `_write_execution_record`) atuam em sequência no mesmo
   `call_agent`, cada um declarando explicitamente que a contagem de
   "execuções por contexto" tem **fonte única** em
   `src/core/agent_circuit_break.py` (ver "Avaliação da suíte existente"). A
   suíte já cobre cada entrega isoladamente com esse boundary mockado; **não
   há** hoje um teste que exercite as duas políticas reais, juntas, dentro do
   mesmo `call_agent` real — essa é a lacuna que fundamenta o único caso novo
   desta verificação (CT-04).
3. Os demais casos (CT-01, CT-02, CT-03, CT-05) são majoritariamente **execução
   e auditoria** da suíte e dos artefatos já presentes; só geram alteração de
   código se uma **divergência** for encontrada (CT-03), situação em que a
   correção exige teste de regressão + bump de versão + entrada no CHANGELOG
   (CA-4/CA-5 da issue).

---

## Avaliação da suíte existente (base da especificação)

Levantamento feito nesta etapa, sobre a linha principal (`origin/main` @
`dd3a634`), com a suíte completa executada (`python -m pytest -q`):
**1579 passed, 26 failed, 17 skipped, 1 xpassed** (79,16s).

| Entrega | Cobertura existente (arquivos) | Veredito preliminar de cobertura |
|---------|--------------------------------|-----------------------------------|
| #305 — retirada segura de colunas | `tests/test_column_withdrawal.py`, `tests/test_column_migrations_config.py`, `tests/test_github_board_contract.py`, `tests/test_full_sync_order.py`, `tests/test_column_migration_evidence.py` | Coberto (política validar→drenar→confirmar→contrair, validação de forma, preparação não destrutiva, ordem do full sync, evidência) |
| #306 — limitador de reexecuções | `tests/test_agent_circuit_break.py`, `tests/test_agent_circuit_break_config.py`, `tests/test_startup_agent_circuit_break.py` | Coberto (contagem/janela/bloqueio, validação de forma, falha fechada na inicialização sem capacidade de label) |
| #307 — registro de execução + linhagem | `tests/test_execution_record.py`, `tests/test_execution_record_config.py`, `tests/test_execution_record_retention.py`, `tests/test_execution_record_surface.py`, `tests/test_execution_record_integration.py`, `tests/test_execution_lineage.py` | Coberto (identidade/resultado/avanço/repetição, retenção, superfície, integração com `call_agent`, linhagem) |
| #308 — composição em camadas | `tests/test_composicao_camadas_medicao.py`, `tests/test_composicao_camadas_inventario.py`, `tests/test_composicao_camadas_sob_demanda.py`, `tests/test_composicao_camadas_campos.py`, `tests/test_composicao_camadas_branch.py`, `tests/test_composicao_camadas_contexto.py`, `tests/test_composicao_camadas_continuidade.py`, `tests/test_composicao_camadas_matriz.py`, `tests/test_composicao_camadas_versionamento.py`, `tests/test_composicao_camadas_regressao.py` | Coberto (redução de camadas, inventário sem duplicidade, gate sob demanda, campos de objetivo/passos, branch única, metadados, continuidade, matriz 5×2×2, versionamento, regressão de prompt) |
| **Convergência #306 × #307 no ponto de decisão (`call_agent`)** | `tests/test_execution_record_integration.py` | **LACUNA PARCIAL** — ver abaixo |

**Lacuna confirmada (fundamenta CT-04):** a leitura de
`src/__main__.py::call_agent` (linhas 707–750) mostra as três capacidades do
bloco atuando em sequência no mesmo ponto de decisão:

```python
record = compose_execution_record(...)              # #308
if not record["instrucoes_obrigatorias_carregadas"]:  # fail-closed #308
    return None
if not _admit_circuit_break(config, board_id, col_id, issue):  # #306
    return None
result = _dispatch_with_recovery(...)
_write_execution_record(..., result=result, ...)      # #307
```

Em **todos** os testes de `tests/test_execution_record_integration.py`
(`test_call_agent_grava_concluida_sem_avanco`,
`test_call_agent_grava_interrompida_com_avanco`,
`test_call_agent_grava_em_falha_terminal`,
`test_call_agent_grava_mesmo_com_result_none`,
`test_call_agent_captura_issue_parent`,
`test_call_agent_registro_sem_prompt_nem_conversa`,
`test_call_agent_um_registro_por_execucao`), `_admit_circuit_break` é
substituído por `MagicMock`/`patch.object(..., return_value=True)` — a política
**real** do limitador nunca é exercitada nesses testes. Simetricamente, os
testes de `tests/test_agent_circuit_break.py` que chegam a `call_agent`
(isolamento CT-10, coexistência com cooldown CT-11b) não verificam se o
registro de execução (#307) é de fato gravado quando a admissão passa, nem o
inverso (se o registro **não** é gravado quando o limitador bloqueia antes do
dispatch).

Isso é exatamente o ponto de convergência que a issue exige comprovar: **ambos
os mecanismos permanecem efetivos em conjunto**, sem que um mascare o outro —
em particular, (a) quando o limitador bloqueia, o dispatch e a gravação do
registro de execução **não** ocorrem para aquela tentativa (nenhuma execução
"vaza" através do bloqueio sem deixar rastro); e (b) quando o limitador admite,
a entrega **é** contada por ele e **também** produz um registro de execução
pela via normal de #307 — as duas fontes avançam juntas, cada uma com sua
responsabilidade, sem contagem duplicada nem suprimida.

---

## Rastreabilidade (CA → casos)

| # | Critério de aceitação (resumo) | Caso(s) |
|---|--------------------------------|---------|
| CA-1 | Existe relatório que lista **cada critério de #305/#306/#307/#308 e seu veredito** | CT-01 (insumo), CT-05 (relatório) + o relatório final consolida CA-1..CA-7 |
| CA-2 | Suíte completa executada; **falha é corrigida ou registrada** com justificativa antes de encerrar | CT-01 |
| CA-3 | **Sem divergência** ⇒ relatório "sem divergência", **sem alteração de código nem bump de versão** | CT-05 |
| CA-4 | Divergência **corrigível no escopo** ⇒ teste de regressão + **incremento de versão** + entrada no CHANGELOG | CT-03 |
| CA-5 | Divergência que **exige escopo novo** ⇒ registrada como **demanda separada**, não implementada aqui | CT-03 |
| CA-6 | Duas entregas do bloco no **mesmo ponto de decisão do produto** (classificação de desfecho de execução, contagem de execuções por contexto) permanecem efetivas em conjunto, sem uma sombrear a outra | **CT-04** |
| CA-7 | Critério **não verificável** com os meios disponíveis ⇒ veredito "não verificável" com a razão | CT-02 (quando a lacuna impede verificar), e tratamento transversal no relatório |

> Mapeamento dos cenários obrigatórios da issue → casos: CT-01 (suíte
> completa), CT-02 (critério sem cobertura ⇒ lacuna registrada), CT-03
> (comportamento declarado ausente ⇒ "não atendido" + correção/demanda), CT-04
> (convergência #306 × #307), CT-05 (verificação sem divergência). Numeração
> 1:1 com a tabela de "Cenários de teste obrigatórios" do corpo da issue.

---

## CT-01 — Suíte completa na linha principal

- **CA de origem:** CA-2 — "Dado que a suíte completa de testes é executada,
  quando há falha, então a falha é corrigida ou registrada com justificativa
  explícita antes do encerramento desta issue." (cenário obrigatório CT-01)
- **Tipo:** execução de suíte (verificação) — não é um novo teste de código.
- **Arquivo/alvo:** suíte inteira em `tests/` via `python -m pytest -q` na raiz
  do repositório, na branch da verificação (base `origin/main`).
- **Pré-condição:** bloco concluído; branch
  `feature/315-verificacao-bloco-2` sincronizada com `origin/main`;
  dependências de teste instaladas (`pytest`, `pyyaml`); execução **offline**
  (sem rede/subprocesso real — os testes já mockam board/subprocess).
- **Passos:**
  1. Executar `python -m pytest -q` a partir de `/app/repo/main`.
  2. Capturar o sumário (total de testes, passados, falhados, pulados) e os
     identificadores de qualquer falha.
  3. Para cada falha: fazer análise de causa-raiz e **classificar** (falha de
     código → divergência CT-03; caso de teste inadequado →
     `revisar-caso-de-teste` na etapa de execução). Nesta etapa de
     **especificação**, apenas registrar o procedimento; a execução ocorre na
     etapa `execucao-testes`.
- **Resultado esperado:** a suíte completa **passa** (0 falhas atribuíveis ao
  bloco 2). O resultado é **registrado** no relatório (contagem + evidência do
  sumário). Se houver falha, ela é corrigida (quando couber no escopo) **ou**
  registrada com justificativa explícita **antes** do encerramento — nunca
  silenciada.
- **Observações:** levantamento preliminar nesta etapa já mostra
  **1579 passed, 26 failed, 17 skipped, 1 xpassed**; as 26 falhas, confirmadas
  por nome de teste, são as mesmas já registradas como baseline pré-existente
  em `doc/quality/verificacao-bloco-1/test-results.md` e nas notas de execução
  de `doc/quality/composicao-em-camadas-do-prompt-e-contexto/test-cases.md`
  (formato de log descritivo — `test_agent_log_descritivo.py` + um caso de
  `test_agent_failure_detection.py` — e infraestrutura Docker —
  `test_dockerfile.py`/`test_docker_compose.py`), alheias a #305/#306/#307/#308.
  A confirmação de que são **exatamente** as mesmas (zero regressão nova) é
  tarefa da etapa `execucao-testes` (comparação de conjuntos de nomes de teste
  falhos, não apenas a contagem).

## CT-02 — Critério declarado sem cobertura de teste correspondente ⇒ lacuna registrada

- **CA de origem:** CA-1 (veredito por critério com evidência) e CA-7 (veredito
  "não verificável" com razão). Cenário obrigatório CT-02.
- **Tipo:** auditoria de cobertura (verificação).
- **Arquivo/alvo:** mapeamento CA (de #305, #306, #307, #308) → teste existente
  em `tests/`. Fontes: `doc/quality/retirada-segura-colunas-migracao/test-cases.md`
  (#305), `doc/quality/limitador-reexecucoes-agente-por-contexto/test-cases.md`
  (#306), `doc/quality/registro-execucao-agentes-linhagem-historica/test-cases.md`
  (#307) e `doc/quality/composicao-em-camadas-do-prompt-e-contexto/test-cases.md`
  (#308), confrontados com os arquivos reais em `tests/`.
- **Pré-condição:** lista dos critérios de aceitação das quatro entregas e dos
  testes que os cobrem (ver tabela "Avaliação da suíte existente").
- **Passos:**
  1. Para cada CA atendido de #305/#306/#307/#308, localizar o(s) teste(s) que
     o cobre(m), usando o mapa de rastreabilidade já publicado em cada
     `test-cases.md` de origem.
  2. Marcar cada CA como: **coberto** (teste identificado e verde), **lacuna de
     cobertura** (CA atendido no código mas sem teste que o exercite) ou **não
     verificável** (sem meio disponível para verificar — registrar a razão).
  3. Registrar explicitamente no relatório a lacuna detectada nesta etapa: a
     **convergência #306 × #307** no `call_agent` real (ver CT-04), hoje
     coberta apenas com o limitador mockado nos testes de integração do
     registro (e vice-versa).
- **Resultado esperado:** o relatório contém, por critério, o veredito e a
  evidência (nome do teste / observação). Pelo menos a lacuna da convergência é
  **registrada**; critérios sem meio de verificação recebem **"não verificável"
  com a razão**, nunca "atendido" por suposição.
- **Observações:** a lacuna de convergência, uma vez registrada aqui, é
  **fechada** por CT-04 dentro do escopo deste bloco (teste de regressão), não
  tratada como demanda separada — porque o CA de convergência já pertence ao
  escopo da própria verificação (CA-6 da issue #315).

## CT-03 — Comportamento declarado ausente na linha principal ⇒ veredito "não atendido"

- **CA de origem:** CA-4 (divergência corrigível ⇒ teste de regressão + versão +
  CHANGELOG) e CA-5 (divergência que exige escopo novo ⇒ demanda separada).
  Cenário obrigatório CT-03.
- **Tipo:** verificação de comportamento + (condicional) teste de regressão.
- **Arquivo/alvo:** comportamento das quatro entregas na linha principal:
  - #305: `src/core/column_withdrawal.py` (política
    validar→drenar→confirmar→contrair), `src/adapters/github_board.py`
    (preparação não destrutiva vs. contração), `src/core/config.py`
    (`boards.<board>.column-migrations`), ordem do full sync em
    `src/__main__.py::board_startup_sync`.
  - #306: `src/core/agent_circuit_break.py` (`CircuitBreaker.admit`, janela
    deslizante, máquina de estados do bloqueio), `src/__main__.py::call_agent`
    (`_admit_circuit_break` antes do dispatch), `src/core/config.py`
    (`agent_circuit_break.*`), guarda de capacidade de label na inicialização.
  - #307: `src/core/execution_record.py` (`record_from_execution_result`,
    `consulta_linhagem`, taxonomia de `resultado`), `src/__main__.py::call_agent`
    (`_write_execution_record` ao final de qualquer desfecho), retenção
    `registro.retencao_dias`.
  - #308: `src/core/composition.py` (`compose_measurement`,
    `check_required_instructions`, `on_demand_references`,
    `resolve_branch_name`), `src/__main__.py::call_agent` (gate fail-closed
    antes do limitador e do dispatch).
- **Pré-condição:** para cada CA declarado atendido, há um comportamento
  observável correspondente (teste executável ou inspeção estrutural).
- **Passos:**
  1. Para cada CA, confrontar o declarado com o comportamento presente
     (executando o teste correspondente ou inspecionando o código/estrutura).
  2. Se o comportamento declarado **não** estiver presente (teste
     ausente/vermelho que deveria passar, ou código que contradiz o CA), emitir
     veredito **"não atendido"** com a evidência.
  3. Classificar a divergência:
     - **corrigível no escopo do bloco** → aplicar a correção **com teste de
       regressão** que reproduz a divergência, **incrementar a versão**
       (`src/core/version.py`) e adicionar **entrada no `CHANGELOG.md`**
       (CA-4);
     - **exige escopo novo** → **não** implementar aqui; registrar como
       **demanda separada** no relatório (CA-5).
- **Resultado esperado:** nenhuma divergência silenciosa. Toda ausência vira
  veredito "não atendido" com evidência e um destino explícito (correção com
  regressão + bump + CHANGELOG, **ou** demanda separada). Se **nenhuma**
  divergência for encontrada, este caso resulta em "não aplicável" e o desfecho
  é o CT-05.
- **Observações:** o incremento de versão e a entrada no CHANGELOG **só**
  ocorrem no ramo "divergência corrigível" (CA-4). É proibido inventar mudança
  para justificar bump (ver CT-05). A leitura de código feita nesta etapa (ver
  "Avaliação da suíte existente") **não** encontrou nenhum comportamento
  declarado e ausente nas quatro entregas — todos os pontos de ancoragem citados
  nos `test-cases.md` de origem (#305/#306/#307/#308) existem de fato no código
  e têm teste verde correspondente; a confirmação definitiva (execução real)
  ocorre na etapa `execucao-testes`.

## CT-04 — Convergência #306 × #307 no ponto de decisão `call_agent` (coexistência sem sombreamento)

- **CA de origem:** CA-6 — "Dado duas entregas do bloco que atuam no mesmo
  ponto de decisão do produto (ex.: classificação de desfecho de execução,
  contagem de execuções por contexto), quando a verificação ocorre, então há
  evidência registrada de que ambas permanecem efetivas em conjunto, sem que
  uma anule ou mascare o efeito da outra." Cenário obrigatório CT-04.
- **Tipo:** integração (teste **novo** — fecha a lacuna registrada em CT-02).
- **Arquivo/alvo:** novo arquivo `tests/test_convergencia_bloco2_execucao.py`,
  exercitando o **código real** de `src/__main__.py::call_agent` —
  `_admit_circuit_break` (#306, real, sem mock) **e** `_write_execution_record`
  (#307, real, sem mock) **no mesmo** `call_agent`. **Vedado** reimplementar a
  lógica de admissão ou de gravação dentro do teste (anti-padrão de
  `test_loop_guard.py`/incidente #106, já identificado e corrigido na
  verificação do bloco 1).
- **Pré-condição comum:** `monkeypatch.chdir(tmp_path)` (padrão da suíte);
  `.pipe/` isolado; `KiroCliAgent`, `ensure_steering_integrity` e
  `compose_execution_record` (#308) neutralizados como pré-condição de
  ambiente (retornando `instrucoes_obrigatorias_carregadas: True`), pois não são
  o objeto deste caso — o objeto é a dupla #306×#307. `_dispatch_with_recovery`
  substituído por espião controlável (devolve `ExecutionResult` configurável,
  registra se foi chamado). `_admit_circuit_break` e `_write_execution_record`
  **não** são mockados — rodam de verdade sobre o estado real do
  `agent_circuit_break` e do `execution_record`.

Os sub-casos abaixo comprovam que **nenhuma das duas entregas sombreia a
outra** no ponto de decisão:

- **CT-04a — Dentro do limite: admissão real conta a entrega E o registro de
  execução real é gravado (ambas efetivas):**
  - **Pré-condição:** `agent_circuit_break: {executions: 3, window: 3600}`
    ativo; contexto `(entrega, desenvolvimento, #42)` com 0–2 ocorrências
    prévias (abaixo do limite).
  - **Resultado esperado:** `call_agent` despacha o agente (espião chamado);
    `_write_execution_record` grava **exatamente um** registro de execução
    (`er.records_for_issue("42")` com 1 item, `resultado` coerente com o
    `ExecutionResult` do espião); a ocorrência fica registrada no contador do
    limitador (`agent_circuit_break`). As duas fontes avançam **juntas**: uma
    entrega produz um incremento de contagem no limitador **e** um registro de
    negócio no #307, sem que uma substitua a outra.
- **CT-04b — Limite atingido: admissão real BLOQUEIA e nenhum registro de
  execução é gravado para a tentativa excedente (limitador não é mascarado):**
  - **Pré-condição:** mesma política; contexto já no limite (3 ocorrências
    reais, semeadas por 3 chamadas prévias de `call_agent` com o mesmo
    contexto, dentro da janela).
  - **Resultado esperado:** a 4ª chamada de `call_agent` **não** aciona o
    dispatch (espião **não** chamado); `_write_execution_record` **não** é
    executado para essa tentativa — nenhum registro novo de execução é gravado
    (`er.records_for_issue` permanece com a contagem das 3 entregas anteriores,
    não 4); a issue fica marcada `need_human`. Prova que o bloqueio do
    limitador (#306) tem efeito real sobre o fluxo e **não é mascarado** pela
    gravação de registro de #307 — nenhuma tentativa bloqueada "escapa" como um
    registro de execução fantasma.
- **CT-04c — Falha de composição (#308) bloqueia ANTES do limitador: nem
  admissão nem registro ocorrem (ordem de gates preservada):**
  - **Pré-condição:** `compose_execution_record` devolve
    `instrucoes_obrigatorias_carregadas: False` (simula steering ausente).
  - **Resultado esperado:** `call_agent` retorna antes de chamar
    `_admit_circuit_break` **e** antes de `_dispatch_with_recovery`/
    `_write_execution_record` — nem o limitador conta a tentativa, nem o
    registro de execução é gravado. Confirma a ordem de gates do bloco:
    composição (#308) → limitador (#306) → dispatch → registro (#307), cada um
    estritamente anterior ao próximo, sem sobreposição.
- **CT-04d — Resultado classificado (#307) reflete fielmente o desfecho mesmo
  com o limitador ativo e dentro do limite (uma entrega não distorce a
  outra):**
  - **Pré-condição:** limitador ativo e dentro do limite; espião de dispatch
    devolve, em sub-execuções sucessivas, `SUCEDIDO`, depois
    `UNKNOWN_OUTCOME`, depois `FALHA`.
  - **Resultado esperado:** cada chamada produz um registro de execução cujo
    `resultado` corresponde à classificação do `ExecutionResult` daquela
    chamada (`CONCLUIDA`, `INTERROMPIDA`/`DESCONHECIDA`, `FALHA_TERMINAL`
    respectivamente) — a presença do limitador ativo **não** altera nem
    atrasa a classificação gravada por #307; e cada uma dessas três entregas
    (todas dentro do limite) é contada normalmente pelo limitador.
- **Resultado esperado (consolidado):** existe **evidência automatizada e
  executável** de que a admissão do limitador (#306) e a gravação do registro
  de execução (#307) **co-existem** no mesmo ponto de decisão (`call_agent`)
  sem que uma mascare o efeito da outra: bloqueio real impede dispatch e
  registro; admissão real permite ambos; a ordem de gates com a composição
  (#308) é preservada. Se a convergência regredir (ex.: um registro de execução
  sendo gravado para uma tentativa bloqueada pelo limitador, ou o limitador
  deixando de contar uma entrega por causa do registro), o teste falha.
- **Observações:**
  - **Isolamento (lição #106):** proibido `monkeypatch` dos símbolos sob teste
    (`_admit_circuit_break`, `_write_execution_record`, o núcleo de
    `CircuitBreaker.admit` ou de `record_from_execution_result`). Patches
    permitidos **apenas** nas fronteiras reais de ambiente/execução
    (`KiroCliAgent`, `ensure_steering_integrity`, `compose_execution_record`
    como pré-condição de #308 já coberta por seus próprios testes,
    `_dispatch_with_recovery` como espião do subprocesso).
  - Este é o **único** caso desta entrega que adiciona código de teste; é um
    teste de **regressão da verificação**, dentro do escopo (o CA de
    convergência já existe na issue #315), **sem** ampliar o escopo de #306 ou
    #307. Fecha uma lacuna de cobertura de um critério já aceito — não corrige
    comportamento do produto —, logo acompanha o relatório; o bump de versão só
    se aplica se, ao escrevê-lo, uma **divergência de comportamento** real for
    revelada (então vira CT-03/CA-4).

## CT-05 — Verificação sem divergência (relatório, sem código, sem bump)

- **CA de origem:** CA-3 — "Dado que nenhuma divergência é encontrada entre o
  declarado e o comportamento na linha principal, quando a verificação encerra,
  então o relatório registra o resultado 'sem divergência' e a entrega é válida
  sem alteração de código-fonte e, portanto, sem incremento de versão." Cenário
  obrigatório CT-05.
- **Tipo:** manual/revisão (fecho da verificação) + guarda objetiva.
- **Arquivo/alvo:** o **relatório de verificação** (entregável da etapa de
  execução de testes, em `doc/quality/verificacao-bloco-2/`); coerência de
  versão e CHANGELOG: `src/core/version.py` (`VERSION`) e `CHANGELOG.md`.
- **Pré-condição:** CT-01 verde (suíte completa passa, descontadas as falhas de
  baseline alheias ao bloco), CT-02 sem lacuna não tratada, CT-03 sem
  divergência de comportamento, CT-04 verde.
- **Passos:**
  1. Confirmar que todos os vereditos são "atendido" (ou "não verificável" com
     razão), sem nenhum "não atendido" pendente.
  2. Confirmar coerência versão↔CHANGELOG↔entregue: `VERSION` e o
     `CHANGELOG.md` refletem #305 (1.17.0), #308 (1.18.0), #306 (1.19.0) e #307
     (1.20.0), **sem** entrada nova inventada para esta verificação.
  3. Registrar no relatório o desfecho **"sem divergência"**.
  4. **Garantir que não há alteração de código-fonte de produto** atribuível a
     esta verificação: `git diff --stat origin/main...HEAD` **não** mostra
     mudanças em `src/` (apenas documentação em `doc/quality/…` e, se CT-04
     adicionou o teste de convergência, o arquivo de teste em `tests/`).
- **Resultado esperado:** o relatório registra "sem divergência"; **`VERSION`
  inalterada** e **nenhuma entrada nova** no `CHANGELOG.md`; o `diff` contra
  `origin/main` restringe-se a `doc/quality/verificacao-bloco-2/` (relatório +
  estes casos) e, no máximo, ao teste de convergência de CT-04 em `tests/`.
  Nenhuma mudança em `src/`.
- **Observações:** a adição do teste de CT-04 em `tests/` **não** é "alteração
  de código-fonte do produto" (não toca `src/`) e **não** exige bump: fecha
  cobertura de um critério já aceito. O bump/CHANGELOG ficam **estritamente**
  condicionados ao ramo "divergência corrigível" de CT-03/CA-4. Inventar
  mudança para justificar a entrega é **proibido** pelo escopo (seção "Fora de
  escopo" e "Riscos e pontos de atenção" do corpo da issue).

---

## Notas de execução para a etapa `execucao-testes`

- **Suíte completa:** `python -m pytest -q` a partir de `/app/repo/main`;
  registrar sumário e qualquer falha com causa-raiz (CT-01). Comparar o
  **conjunto de nomes** de testes falhos contra o baseline conhecido
  (`test_agent_log_descritivo.py` + 1 caso de `test_agent_failure_detection.py`
  + `test_dockerfile.py`/`test_docker_compose.py`) para provar **zero
  regressão nova** (mesma técnica usada na verificação do bloco 1: comparação
  via worktree limpo de `origin/main`, se necessário).
- **Foco adicional** nos arquivos de #305/#306/#307/#308 listados na tabela de
  "Avaliação da suíte existente" e no novo
  `tests/test_convergencia_bloco2_execucao.py` (CT-04).
- **Offline:** nenhum teste pode depender de rede, `gh` real ou subprocesso
  real; usar fakes/mocks e `tmp_path` (padrão já adotado em toda a suíte das
  quatro entregas).
- **Relógio controlável:** onde pertinente (janela do limitador, retenção do
  registro de execução), `time.time`/relógio sempre mockado — nunca `sleep`
  real.
- **Veredito por critério:** o relatório final (`test-results.md` / relatório
  de verificação) deve conter **CA-1..CA-7** com veredito **e evidência** (nome
  do teste executado ou observação estrutural). Critério sem meio de
  verificação → **"não verificável" com razão**.
- **Precedência do desfecho:** se CT-01..CT-04 passam e CT-03 não revela
  divergência, o desfecho é CT-05 ("sem divergência", sem bump). Divergência
  corrigível → CT-03/CA-4 (regressão + bump + CHANGELOG). Divergência que
  amplia escopo → CA-5 (demanda separada).

## Devolução ao planejamento (quando aplicável)

Não aplicável: o escopo da issue #315 está completo e internamente consistente
para derivar os casos. As quatro entregas auditadas (#305, #306, #307, #308)
estão identificadas, versionadas e com `test-cases.md`/`test-results.md`
próprios já publicados; a leitura do código confirmou os pontos de ancoragem
citados (núcleos em `src/core/column_withdrawal.py`,
`src/core/agent_circuit_break.py`, `src/core/execution_record.py`,
`src/core/composition.py`, e o ponto de convergência único em
`src/__main__.py::call_agent`). Nenhuma decisão de negócio em aberto impede a
especificação. Avançar para `desenvolvimento`.
