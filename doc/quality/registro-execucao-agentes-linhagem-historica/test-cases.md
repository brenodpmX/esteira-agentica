# Casos de Teste — Registro de execução de agentes com consolidação por linhagem histórica

- **Issue:** #307
- **Story relacionada:** registro de negócio por execução de agente + consulta/exportação de linhagem histórica (confiabilidade/custos); `/blocks #315`
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-02
- **Branch:** `feature/307-registro-execucao-agentes-linhagem-historica`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA-1 a
> CA-18) da issue #307, de suas regras de negócio (RN-01 a RN-14), requisitos
> não funcionais (RNF-01 a RNF-10), tabela de comportamento em falha e
> cenários obrigatórios (CT-01 a CT-17). Cada caso tem resultado esperado
> explícito e verificável. Os testes são da suíte Python do motor (pytest, em
> `tests/`), salvo os marcados como **varredura/revisão** (guarda estática de
> estrutura/superfície). Os testes de tempo (retenção, duração, janela) usam
> **relógio controlável** (`monkeypatch` de `time.time`/`datetime`), nunca
> `sleep` real.

---

## Contexto de arquitetura (baseline do código atual)

A capacidade **não existe hoje**. A leitura do motor confirmou os pontos de
ancoragem e as restrições que os casos exercitam:

- **Ponto de execução (onde o registro nasce)** —
  `src/__main__.py::call_agent(config, task, …)` entrega a issue ao agente e
  despacha via `_dispatch_with_recovery(...)`, que devolve um `ExecutionResult`
  (`src/core/execution.py`) com `classe` (`SUCEDIDO` / `FALHA` /
  `UNKNOWN_OUTCOME` / `DEFINITE_NOT_STARTED` / `falha persistente`), `causa`,
  `origem`, `session_id`, `request_id`, `tentativas`. **Hoje não há criação de
  nenhum registro de negócio ao fim da execução** — o único artefato por
  execução é o log detalhado em Markdown escrito pelo adapter. O registro desta
  entrega deve ser gravado **ao final de cada execução e em qualquer desfecho**
  (CA-1), no core, a partir do que `call_agent`/`ExecutionResult` já conhecem.
- **Avanço da issue (dimensão independente do resultado)** — a mudança de etapa
  é observável no motor: `src/__main__.py::_auto_advance(board_id, issue,
  target_col, snap)` move os 3 arquivos da issue para a coluna seguinte,
  atualiza o snapshot e enfileira o `change-up`; o `change.advance` da coluna é
  a transição configurada. O indicador `avancou` do registro deriva dessa
  observação, **não** do `resultado` técnico (RN-01).
- **Fonte única de contagem** — `src/core/agent_circuit_break.py` **declara-se**
  (docstring e nota de integração #307/#315) a **única fonte de verdade** para
  "quantas execuções houve neste contexto `(board, coluna, issue)`". A entrega é
  contabilizada ali, no instante da entrega, independente do resultado
  (`CircuitBreaker.admit` → `occurrences` por contexto ativo
  `(board, issue)` + `column`). Esta capacidade **adere** a essa fonte (CA-18 /
  CT-17) — **não** cria contador paralelo de "execuções por contexto".
- **Efemeridade da rastreabilidade local (o problema que a linhagem resolve)** —
  ao arquivar/deletar uma issue, `src/core/sync.py::_apply_delete_down(...)`
  **apaga** os arquivos locais da issue (`-body.md` / `-history.md` /
  `-addcomment.md`) e remove a entrada do snapshot; e o log detalhado é
  **expurgado por TTL** por `src/core/log.py::Log.cleanup()` (remove arquivos
  com idade `> log.ttl` dias). Logo, a linhagem **não pode** depender de
  arquivos locais nem de logs — tem de ser reconstruída dos **registros
  próprios** (RN-06 / CA-9 / CT-07), que capturam de forma durável a
  **existência** da issue (`issue_id`) e o **parentesco observado na execução**
  (`issue_parent`).
- **Consumo sem tokens no adapter atual** — o `kiro-cli` não expõe contagem de
  tokens de entrada (em `compose_execution_record`, `tokens_entrada` já é
  `None`). Para o consumo do registro, isso significa `disponibilidade =
  indisponível` — comportamento **correto**, não falha (CA-5 / CT-03).
- **Validação de config segue o padrão da casa** — `src/core/config.py`:
  `ConfigError` é a exceção única; blocos opcionais de raiz (`retry`, `sync`,
  `project`, `agent_circuit_break`) são validados em `check_config()` com
  mensagem **citando o caminho do campo**, e **`bool` é rejeitado ANTES de
  `int`** (`True/False` são `int` em Python). `check_config()` roda **antes** de
  qualquer alteração de estado. A nova chave `registro.retencao_dias` (ou o
  caminho concreto escolhido pelo desenvolvimento) segue esse mesmo padrão.
- **Estado interno protegido** — `src/core/agent.py::PROTECTED_PATHS` lista os
  caminhos `.pipe/*` que o agente nunca acessa; o novo armazenamento durável dos
  registros (seja qual for o arquivo/estrutura) **deve** entrar nessa lista, e
  seu conteúdo nunca é exposto a agente/comentário/prompt.

> **Decisão de etapa técnica — NÃO fixada pela QA (é do desenvolvimento):**
> tecnologia de armazenamento, estrutura de dados concreta, protocolo da
> consulta/exportação, algoritmo de travessia da linhagem, e o **mapeamento
> concreto** entre as classes de `ExecutionResult`
> (`SUCEDIDO`/`FALHA`/`UNKNOWN_OUTCOME`/`DEFINITE_NOT_STARTED`/`falha
> persistente`) e a taxonomia de `resultado` deste registro
> (`concluída`/`falha terminal`/`timeout`/`interrompida`/`desconhecida`). Os
> casos abaixo testam **comportamento e invariantes observáveis**, não
> assinaturas nem o formato de armazenamento. Onde um caso cita um símbolo
> concreto (`call_agent`, `_auto_advance`, `agent_circuit_break`,
> `PROTECTED_PATHS`), o alvo é **provável**; se o desenvolvimento adotar outro
> nome/local, o caso vale sobre o **comportamento equivalente**.

### Nota de mapeamento resultado → taxonomia (restrição, não escolha do "como")

O desenvolvimento escolhe o mapeamento concreto, mas ele é **restringido** pelos
CAs e RNs e deve ser **total e determinístico** (nunca `resultado` vazio/nulo —
RN-02). Os casos CT-01/CT-02/CT-18/CT-19/CT-20 fixam âncoras observáveis que o
mapeamento tem de respeitar:

- execução que concluiu sem sinal estruturado de falha → `resultado = concluída`
  (CT-01, CA-2);
- interrupção transitória / resultado ambíguo (`UNKNOWN_OUTCOME`) → `resultado`
  **não** `concluída` e **não** vazio — é `interrompida` ou `desconhecida`
  conforme a evidência (CT-02/CT-18/CT-19, comportamento em falha);
- desfecho impossível de classificar com segurança → `resultado = desconhecida`,
  nunca vazio (CT-19, RN-02);
- o mapeamento cobre **todas** as classes de `ExecutionResult` sem deixar
  nenhuma sem destino (CT-20 — guarda de totalidade).

---

## Convenções para o desenvolvimento (todos os casos automatizados)

- **Offline, sem rede:** usar fakes controláveis no padrão de
  `tests/test_rerun_cooldown.py`, `tests/test_agent_circuit_break.py` e
  `tests/test_column_withdrawal.py`. Um **dispatch espião** substitui
  `_dispatch_with_recovery` para devolver um `ExecutionResult` controlado
  (classe/causa/origem) e registrar **se** foi chamado — assim o teste exercita
  a gravação do registro sem executar `kiro-cli`. Um `BoardPort` **fake**
  fornece parentesco/coluna quando o caso precisar.
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` por teste (fixture
  `autouse`), para que `.pipe/` e `logs/` sejam isolados — mesmo padrão da suíte
  existente. Qualquer cache de módulo relevante deve ser limpo em fixture
  `autouse`.
- **Relógio controlável:** nos casos de duração (CT-02), retenção
  (CT-11/CT-12) e qualquer janela temporal, controlar o tempo via `monkeypatch`
  de `time.time`/`datetime` — **nunca** `sleep` real. Início/fim/idade são
  derivados do relógio injetado, deterministicamente.
- **Nunca** fazer `monkeypatch` do próprio símbolo sob teste (lição do incidente
  #106 — mascarava ausência de cobertura real). O núcleo (gravação do registro,
  resolução de linhagem, agregação, expurgo por retenção) é exercitado **de
  verdade**; só o **dispatch**, o **board/parentesco** e o **relógio** são
  controlados.
- **Exercitar a capacidade pela API pública que o desenvolvimento expuser**
  (gravação no fim de `call_agent`; consulta por raiz; expurgo por retenção). O
  teste **não** inspeciona o arquivo de estado interno protegido (`.pipe/...`)
  como fonte de evidência de negócio — a evidência vem da **consulta/exportação**
  (a saída lógica contratada). A leitura direta do armazenamento só é admitida
  nos casos que **explicitam** ser verificação de persistência/durabilidade
  (CT-07, CT-16), nunca como prova de regra de negócio consultável.
- **Fixtures de linhagem:** montar árvores raiz→descendentes semeando execuções
  reais (cada execução captura `issue_id` + `issue_parent`), e então simular
  arquivamento (apagar arquivos locais via o caminho real de
  `_apply_delete_down` ou equivalente) e expurgo de logs (`Log.cleanup()` com
  TTL vencido) **sem** tocar nos registros próprios — para provar resiliência.

---

## Rastreabilidade (CA / cenário → casos)

| CA / Cenário obrigatório | Regra(s) | Caso(s) neste documento |
|--------------------------|----------|-------------------------|
| CA-1 — registro sempre criado | RN-02, RN-11 | CT-20, CT-21 |
| CA-2 / CT-01 — concluída sem avanço | RN-01 | CT-01 |
| CA-3 / CT-02 — interrompida com avanço prévio | RN-01 | CT-02 |
| CA-5 / CT-03 — consumo indisponível | RN-04 | CT-03 |
| CA-6 / CT-04 — consumo zero reportado | RN-04 | CT-04 |
| CA-4 — consumo reportado (disponível) | RN-04, RN-05 | CT-04b |
| CA-8 / CT-05 — repetição sem avanço (mesma etapa) | RN-03 | CT-05 |
| CA-8 / CT-06 — não repetição após mudança de etapa | RN-03 | CT-06 |
| CA-9 / CT-07 — linhagem resiliente à limpeza local | RN-06 | CT-07 |
| CA-10 / CT-08 — descendente sem registro | RN-08 | CT-08 |
| CA-11 / CT-09 — ciclo na linhagem | RN-07 | CT-09 |
| CA-7 / CT-10 — agregado com unidades diferentes | RN-05 | CT-10 |
| CA-12 / CT-11 — retenção configurada expira | RN-09 | CT-11 |
| CA-12 / CT-12 — retenção não configurada | RN-09 | CT-12 |
| CA-13 / CT-13 — exclusão de issue preserva registros | RN-10 | CT-13 |
| CA-14 / CT-14 — ausência de exclusão manual | RN-11 | CT-14 (varredura) |
| CA-15 / CT-15 — resposta da raiz sem abrir logs | RN-13 | CT-15 |
| CA-17 / CT-16 — isolamento de conteúdo | RN-13 | CT-16 (+ varredura) |
| CA-18 / CT-17 — fonte única de contagem | RN-01 | CT-17 (varredura + comportamental) |
| Comportamento em falha — interrompida/parcial | RN-02 | CT-18 |
| Comportamento em falha — desfecho inclassificável → desconhecida | RN-02 | CT-19 |
| CA-1 / RN-02 — taxonomia fechada, total e não-vazia | RN-02 | CT-20 (varredura) |
| CA-16 — baseline de 30 dias | RN-01, RN-04 | CT-21 |
| CA-11 / RN-07 — dupla contagem por múltiplos caminhos | RN-07 | CT-09b |
| CA-9 / RNF-09 — preservação após exclusão por consulta de linhagem | RN-10 | CT-13b |

> **Observação de cobertura (decisão de não devolver ao planejamento):** o
> escopo da issue está **completo e internamente consistente** após a resolução
> do dono (histórico de 02/10): a RN-06/CA-9/CT-07 foi fixada como preservação
> durável de existência + parentesco por execução, resiliente a arquivamento e
> expurgo de logs. Os 18 CAs mapeiam limpo sobre a arquitetura real
> (`call_agent`/`ExecutionResult`, `_auto_advance`, `agent_circuit_break` como
> fonte única, `_apply_delete_down`/`Log.cleanup` como as ferramentas de limpeza
> a resistir). Não há lacuna nem contradição que exija `revisar-escopo`. O que é
> "como" (armazenamento, travessia, mapeamento concreto de classes) está
> explicitamente fora e **não** bloqueia a especificação dos casos
> comportamentais.

---

## Grupo A — Registro por execução: identidade, resultado, avanço, repetição

> Alvo principal: a gravação do registro ao fim de `call_agent`/
> `_dispatch_with_recovery`, com dispatch espião e relógio controlável. O
> registro é lido de volta pela consulta/exportação pública (não pelo arquivo
> protegido).

### CT-01 — Execução concluída sem avanço

- **CA de origem (CA-2 / CT-01):** "Dada uma execução que concluiu sem mover a
  issue de etapa, quando o registro é criado, então `resultado = concluída` e
  `avancou = não`."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py` (novo).
- **Pré-condição:** dispatch espião devolve `ExecutionResult(classe=SUCEDIDO)`;
  a issue sinaliza intervenção humana (`/need_human`) e **permanece** na mesma
  coluna após a execução (sem `_auto_advance`, sem `change.advance`).
- **Passos:**
  1. Entregar a issue ao agente (uma execução).
  2. Consultar o registro criado para essa execução.
- **Resultado esperado:** existe **exatamente um** registro para a execução;
  `resultado = concluída`; `avancou = não` (booleano/`não`). O avanço é derivado
  da **não**-mudança de etapa, independente de o resultado ser sucesso.
- **Observações:** cobre CA-1 (existe registro), CA-2, RN-01 (independência das
  duas dimensões). Âncora do mapeamento: sucesso sem sinal de falha → `concluída`.

### CT-02 — Interrompida com avanço prévio

- **CA de origem (CA-3 / CT-02):** "Dada uma execução interrompida cuja issue já
  havia avançado de etapa antes da interrupção, quando o registro é criado,
  então `resultado = interrompida` e `avancou = sim`."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** a issue **avança de etapa** durante a execução (observável
  via `_auto_advance`/`change.advance` — simulado pelo fake de board/coluna);
  depois o dispatch devolve um desfecho de **interrupção** (ex.:
  `ExecutionResult(classe=UNKNOWN_OUTCOME, origem="timeout"|"dispatch failure")`
  — a classe que o mapeamento associa a `interrompida`). Relógio controlável
  para início/fim parciais.
- **Passos:**
  1. Entregar a issue; durante a execução, registrar o avanço de etapa.
  2. Fazer o dispatch devolver o desfecho de interrupção.
  3. Consultar o registro.
- **Resultado esperado:** `resultado = interrompida`; `avancou = sim`; início
  preservado e `fim`/`duracao` preenchidos com o que se conhece (parciais
  aceitos, nunca vazios por obrigação). As duas dimensões são independentes: a
  interrupção técnica **não** apaga o fato de a issue ter avançado.
- **Observações:** cobre CA-3, RN-01, e a 1ª linha de "comportamento em falha".

### CT-03 — Consumo indisponível (plataforma não reporta)

- **CA de origem (CA-5 / CT-03):** "Dado que a plataforma não reportou consumo,
  quando o registro é criado, então `disponibilidade = indisponível` e `valor`
  **não** é preenchido (nunca com zero)."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** adapter/execução **não** expõe consumo (cenário real do
  `kiro-cli`: sem contagem de tokens). Dispatch espião sem dado de consumo.
- **Passos:**
  1. Entregar a issue com a execução sem reporte de consumo.
  2. Consultar o bloco `consumo` do registro.
- **Resultado esperado:** `consumo.disponibilidade = indisponível`; `consumo.
  valor` **ausente/indefinido** (nunca `0`); `unidade`/`origem` coerentes com a
  ausência (não inventam valor). Invariante RNF-02: `disponibilidade =
  indisponível` ⇒ `valor` não definido.
- **Observações:** cobre CA-5, RN-04, RNF-02 e a 3ª linha de "comportamento em
  falha". É o comportamento **correto** para o adapter atual, não uma falha.

### CT-04 — Consumo zero reportado

- **CA de origem (CA-6 / CT-04):** "Dado um consumo efetivamente zero reportado
  pela plataforma, quando o registro é criado, então `valor = 0` e
  `disponibilidade = disponível`."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** a execução reporta consumo **explicitamente zero** (fake de
  consumo = 0, com unidade/origem).
- **Passos:**
  1. Entregar a issue com consumo reportado = 0.
  2. Consultar o bloco `consumo`.
- **Resultado esperado:** `consumo.valor = 0`; `consumo.disponibilidade =
  disponível`; `unidade` e `origem` preenchidas. **Zero reportado** e **não
  informado** (CT-03) são estados **distintos** e não compartilham representação
  (RN-04).
- **Observações:** cobre CA-6, RN-04. Contrasta diretamente com CT-03.

### CT-04b — Consumo reportado disponível (valor, unidade, origem)

- **CA de origem (CA-4):** "Dado que a plataforma reportou consumo, quando o
  registro é criado, então `valor`, `unidade`, `origem` e `disponibilidade =
  disponível` estão preenchidos."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** execução de uma plataforma hipotética que reporta consumo
  positivo com unidade nativa (ex.: `valor=1234`, `unidade="créditos"`,
  `origem="<adapter>"`).
- **Passos:**
  1. Entregar a issue com consumo reportado positivo.
  2. Consultar o bloco `consumo`.
- **Resultado esperado:** `valor` numérico preenchido; `unidade` = unidade
  nativa; `origem` = plataforma/adapter que reportou; `disponibilidade =
  disponível`. O rótulo geral é "Tokens", mas a **unidade nativa** é preservada
  sem conversão (RN-05).
- **Observações:** cobre CA-4, RN-04, RN-05, RNF-08. Base para a segmentação de
  CT-10.

### CT-05 — Repetição sem avanço na mesma etapa

- **CA de origem (CA-8 / CT-05):** "Dado que a execução anterior da issue na
  mesma etapa (mesmo board e mesma coluna) não avançou a issue, quando uma nova
  execução ocorre na mesma etapa, então ela é marcada como repetição sem avanço."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** issue `#42` em `(entrega, desenvolvimento)`; execução 1
  conclui **sem** avançar (mesma coluna depois). Execução 2 ocorre no **mesmo**
  `(board, coluna, issue)`.
- **Passos:**
  1. Entregar a issue (execução 1, sem avanço).
  2. Entregar de novo no mesmo contexto (execução 2).
  3. Consultar o registro da execução 2.
- **Resultado esperado:** o registro da execução 2 tem `repeticao_sem_avanco =
  verdadeiro`; o da execução 1 **não** (não há anterior sem avanço). A marcação
  deriva de RN-03 (nova execução, mesma etapa, após anterior naquela etapa que
  não progrediu).
- **Observações:** cobre CA-8 (ramo "é repetição"), RN-03. `repeticao_sem_avanco`
  é **derivado**, não derivado do `resultado`.

### CT-06 — Não repetição após mudança de etapa

- **CA de origem (CA-8 / CT-06):** "Dado que a etapa mudou entre as execuções,
  então **não** é marcada [como repetição]."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** execução 1 em `(entrega, desenvolvimento, #42)` sem avanço;
  depois a issue **muda de etapa** para `(entrega, execucao-testes, #42)`;
  execução 2 ocorre já na nova etapa.
- **Passos:**
  1. Entregar na etapa `desenvolvimento` (execução 1).
  2. Mudar a etapa para `execucao-testes`.
  3. Entregar na nova etapa (execução 2).
  4. Consultar o registro da execução 2.
- **Resultado esperado:** o registro da execução 2 tem `repeticao_sem_avanco =
  falso` — a mudança de etapa **descaracteriza** a repetição (RN-03), ainda que
  seja a mesma issue. A etapa é parte da identidade (board + coluna).
- **Observações:** cobre CA-8 (ramo "não é repetição"), RN-03. Par
  complementar de CT-05.

---

## Grupo B — Linhagem histórica: resiliência, descendentes, ciclo, agregação

> Alvo: a consulta/exportação por issue raiz, reconstruída dos registros
> próprios (`issue_id` + `issue_parent` por execução), resiliente a arquivamento
> (arquivos locais apagados) e expurgo de logs por TTL, sem ciclo nem dupla
> contagem.

### CT-07 — Linhagem resiliente à limpeza local

- **CA de origem (CA-9 / CT-07):** "Dado um épico com descendentes que
  executaram, quando a esteira posteriormente arquiva issues da linhagem
  (apagando seus arquivos locais) e/ou expurga os logs por TTL, então a consulta
  de linhagem continua retornando todos os descendentes **conhecidos**, mesmo
  que não restem arquivos locais nem logs daquelas issues."
- **Tipo:** integração (registro + linhagem + limpeza)
- **Arquivo/alvo:** `tests/test_execution_lineage.py` (novo).
- **Pré-condição:** raiz `#100` com descendentes `#101` (filho) e `#102`
  (neto, filho de `#101`). Cada um executou ao menos uma vez — cada execução
  gravou `issue_id` + `issue_parent` observado. Em seguida:
  (a) arquivar/deletar `#101` e `#102` pelo caminho real que apaga os arquivos
  locais (`_apply_delete_down` ou equivalente) e remove do snapshot;
  (b) rodar `Log.cleanup()` com TTL vencido para expurgar os logs daquelas
  issues. Os **registros próprios** não são tocados.
- **Passos:**
  1. Semear execuções de `#100`, `#101`, `#102` (parentesco capturado).
  2. Confirmar que os arquivos locais e os logs de `#101`/`#102` **não** existem
     mais após (a) e (b).
  3. Consultar a linhagem de `#100`.
- **Resultado esperado:** a consulta retorna `#100`, `#101` e `#102` — todos os
  descendentes **conhecidos** — com existência e parentesco preservados, mesmo
  sem arquivos locais nem logs. A reconstrução usa **somente** os registros
  próprios (`issue_id` + `issue_parent`), nunca o snapshot/arquivos/logs
  apagados.
- **Observações:** cobre CA-9, RN-06, RNF-03 e a última linha de "comportamento
  em falha". É o caso central da entrega. A verificação da ausência de arquivos
  locais/logs é parte do caso (prova a resiliência).

### CT-08 — Descendente conhecido sem registro

- **CA de origem (CA-10 / CT-08):** "Dado um descendente conhecido que nunca
  produziu registro, quando a linhagem é consultada, então ele aparece
  sinalizado como 'sem registro', nunca omitido."
- **Tipo:** integração (linhagem)
- **Arquivo/alvo:** `tests/test_execution_lineage.py`
- **Pré-condição:** raiz `#100` com execução; descendente `#103` cuja
  **existência e parentesco** foram capturados por um registro (ex.: outro
  descendente `#101` executou declarando `issue_parent=#100`, e `#103` é
  conhecido como filho de `#101` por um registro que o referencia) **mas** `#103`
  em si **nunca** produziu um registro de execução próprio. (O caso respeita a
  definição fixada: "descendente conhecido" = existência + vínculo capturados
  por ao menos um registro.)
- **Passos:**
  1. Montar a linhagem onde `#103` é conhecido porém sem execução própria.
  2. Consultar a linhagem de `#100`.
- **Resultado esperado:** `#103` aparece no resultado com `sem_registro =
  verdadeiro` e `execucoes = 0`; **nunca** é omitido nem tratado como ausente.
  Os demais itens com registro aparecem com `sem_registro = falso` e sua
  contagem real.
- **Observações:** cobre CA-10, RN-08, RNF-04. "Sem registro" é **sinalizado**,
  distinto de "zero execuções" silencioso.

### CT-09 — Linhagem com ciclo: cada issue/execução conta uma vez

- **CA de origem (CA-11 / CT-09):** "Dada uma linhagem com ciclo de vínculos,
  quando é consultada, então nenhuma issue ou execução é contada mais de uma vez."
- **Tipo:** integração (linhagem)
- **Arquivo/alvo:** `tests/test_execution_lineage.py`
- **Pré-condição:** registros que, pelos `issue_parent` capturados, formam um
  **ciclo** (ex.: `#100 → #101 → #102 → #100`), induzido por vínculos observados
  em execuções distintas. Cada issue tem uma quantidade conhecida de execuções.
- **Passos:**
  1. Semear os registros que induzem o ciclo.
  2. Consultar a linhagem de `#100`.
- **Resultado esperado:** a consulta **neutraliza** o ciclo e retorna um
  resultado consistente: cada issue aparece **uma única vez** e cada execução é
  contada **exatamente uma vez** — `quantidade_execucoes` agregada = soma simples
  das execuções distintas, sem inflar. Resultado determinístico/reprodutível.
- **Observações:** cobre CA-11, RN-07, RNF-03 e a linha de ciclo em
  "comportamento em falha".

### CT-09b — Dupla contagem por múltiplos caminhos (grafo, não só ciclo)

- **CA de origem (CA-11 / RN-07):** "...cada issue e cada execução conta
  exatamente uma vez, mesmo alcançável por mais de um caminho."
- **Tipo:** integração (linhagem)
- **Arquivo/alvo:** `tests/test_execution_lineage.py`
- **Pré-condição:** linhagem em que um descendente é alcançável por **dois
  caminhos** distintos a partir da raiz (sem ciclo), por vínculos capturados em
  execuções diferentes (ex.: `#104` observado como filho de `#101` numa execução
  e de `#102` noutra, ambos descendentes de `#100`).
- **Passos:**
  1. Semear a estrutura com caminho duplo até `#104`.
  2. Consultar a linhagem de `#100`.
- **Resultado esperado:** `#104` e suas execuções são contados **uma única vez**,
  apesar de alcançáveis por dois caminhos; os agregados não duplicam.
- **Observações:** cobre RN-07 no cenário de grafo com confluência (distinto do
  ciclo de CT-09). Guarda contra dupla contagem silenciosa.

### CT-10 — Agregado com unidades diferentes (sem soma cruzada)

- **CA de origem (CA-7 / CT-10):** "Dado um agregado de linhagem com execuções
  em unidades distintas, quando é consultado, então os totais aparecem
  segmentados por unidade/origem e **nunca** somados entre unidades distintas."
- **Tipo:** integração (linhagem + consumo)
- **Arquivo/alvo:** `tests/test_execution_lineage.py`
- **Pré-condição:** linhagem com execuções de **duas** origens/unidades distintas
  (ex.: `créditos` da origem A e outra unidade da origem B), além de ao menos uma
  execução com consumo **indisponível**.
- **Passos:**
  1. Semear execuções com unidades/origens diferentes e uma indisponível.
  2. Consultar os agregados da raiz.
- **Resultado esperado:** `consumo_por_unidade_origem` traz **uma entrada por
  `{unidade, origem}`**, com `total` por segmento e `ha_indisponivel`
  sinalizando a presença de execução sem consumo; **não** há um total único
  somando unidades distintas. A segmentação é explícita (RN-05, RNF-08).
- **Observações:** cobre CA-7, RN-05, RNF-08. Reaproveita CT-04b/CT-03 na mesma
  linhagem.

### CT-15 — Resposta da raiz sem abrir nenhum log

- **CA de origem (CA-15 / CT-15):** "Dada uma issue raiz com histórico, quando
  consultada, então quantidade, duração, consumo, resultados e repetições
  retornam sem que qualquer log individual precise ser aberto."
- **Tipo:** integração (linhagem + isolamento de I/O)
- **Arquivo/alvo:** `tests/test_execution_lineage.py`
- **Pré-condição:** raiz com histórico conhecido (várias execuções em
  descendentes). Instrumentar/espiar o acesso ao diretório de logs
  (`logs/<issue_id>/*.md`) — ex.: monkeypatch de `open`/leitura do diretório de
  logs para **registrar** qualquer abertura; ou garantir que os logs **nem
  existem** (expurgados) e a consulta ainda responde.
- **Passos:**
  1. Semear a linhagem com registros; (opcional) expurgar os logs.
  2. Consultar os agregados da raiz com o espião de I/O de log armado.
- **Resultado esperado:** a consulta devolve `quantidade_execucoes`,
  `duracao_total`, `consumo_por_unidade_origem`, `distribuicao_resultados` e
  `repeticoes_sem_avanco` **sem** nenhuma abertura de arquivo de log individual
  (zero leituras no diretório de logs); funciona inclusive com os logs
  **ausentes**.
- **Observações:** cobre CA-15, RN-13, RNF-05 (parte técnica: resposta sem abrir
  logs; a meta de 5 min é de experiência do operador, não SLA — não testada como
  latência). Reforça CT-07 (independência de logs).

---

## Grupo C — Retenção própria, preservação e isolamento de conteúdo

### CT-11 — Retenção configurada torna o registro elegível a expurgo

- **CA de origem (CA-12 / CT-11):** "Dada retenção configurada em N dias, quando
  um registro atinge N dias de idade, então ele se torna elegível a expurgo."
- **Tipo:** unitário (retenção), relógio controlável
- **Arquivo/alvo:** `tests/test_execution_record_retention.py` (novo).
- **Pré-condição:** `registro.retencao_dias = N` (ex.: `N=7`); um registro criado
  em `t0`. Relógio controlável avançando a idade para `N-1`, `N` e `N+1` dias
  (sub-casos de borda).
- **Passos:**
  1. Criar o registro em `t0`.
  2. Avançar o relógio e acionar o expurgo condicional para cada idade de borda.
  3. Consultar se o registro permanece.
- **Resultado esperado:** idade `< N` dias → registro **permanece** (não
  elegível); idade `>= N` dias (idade `== N` e `> N`) → registro **elegível a
  expurgo** e removido pelo expurgo. A idade é `(agora - criacao)` conforme o
  contrato (`>= retencao_dias` ⇒ elegível). A retenção é **própria**, independente
  do `log.ttl`.
- **Observações:** cobre CA-12 (ramo configurado), RN-09, RNF-06. A borda segue
  o contrato `>= retencao_dias`. Independência do TTL do log é parte do caso
  (ter `log.ttl` diferente não altera a retenção do registro).

### CT-12 — Retenção não configurada: nenhum expurgo automático

- **CA de origem (CA-12 / CT-12):** "Dado retenção não configurada, então nenhum
  registro é expurgado automaticamente."
- **Tipo:** unitário (retenção)
- **Arquivo/alvo:** `tests/test_execution_record_retention.py`
- **Pré-condição:** config **sem** `registro.retencao_dias`; registros antigos
  (idade arbitrariamente grande via relógio controlável).
- **Passos:**
  1. Criar registros e avançar o relógio muito além de qualquer idade razoável.
  2. Acionar o ciclo de expurgo.
  3. Consultar os registros.
- **Resultado esperado:** **nenhum** registro é removido automaticamente —
  estado seguro por padrão (ausente ⇒ sem expurgo). Os registros seguem
  consultáveis.
- **Observações:** cobre CA-12 (ramo ausente), RN-09, RNF-06 e a linha "retenção
  não configurada com o tempo passando" de "comportamento em falha".

### CT-11b — Validação da configuração de retenção (forma, na inicialização)

- **CA de origem (contrato de configuração + padrão da casa):**
  "`registro.retencao_dias`: opcional; quando presente, inteiro > 0."
- **Tipo:** unitário (config), **parametrizado**
- **Arquivo/alvo:** `tests/test_execution_record_config.py` (novo) ou extensão de
  `tests/test_config*`.
- **Pré-condição:** sub-casos de `registro.retencao_dias`:
  1. ausente → aceito (política de expurgo inativa);
  2. inteiro `> 0` (ex.: `7`) → aceito;
  3. `0` → `ConfigError` citando o caminho;
  4. negativo (ex.: `-1`) → `ConfigError` citando o caminho;
  5. booleano (`true`/`false`) → `ConfigError` citando o caminho (bool rejeitado
     **antes** de int);
  6. float não-int (ex.: `7.5`) → `ConfigError` citando o caminho;
  7. string (ex.: `"7"`) → `ConfigError` citando o caminho.
- **Passos:** chamar a validação de config (`check_config`/validador específico)
  para cada sub-caso.
- **Resultado esperado:** sub-casos 1–2 aceitos; 3–7 levantam `ConfigError` cuja
  mensagem **cita o caminho completo** do campo; a falha ocorre na verificação de
  configuração, **antes de qualquer alteração de estado**. Segue o padrão de
  `validate_retry`/`validate_agent_circuit_break` (bool antes de int, mensagem
  acionável).
- **Observações:** cobre a validação de forma do contrato de retenção. O caminho
  concreto (`registro.retencao_dias` ou equivalente) é escolha do
  desenvolvimento; o caso vale sobre o campo que a capacidade expuser.

### CT-13 — Exclusão de issue preserva os registros (consulta direta)

- **CA de origem (CA-13 / CT-13):** "Dada uma issue com registros, quando ela é
  excluída, então os registros continuam existentes e consultáveis, sujeitos
  apenas à retenção própria."
- **Tipo:** integração (registro + exclusão de issue)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** issue `#200` com ≥ 2 registros de execução. Em seguida a
  issue é **excluída** pelo caminho real (`_apply_delete_down` / arquivamento),
  que apaga os arquivos locais e remove do snapshot.
- **Passos:**
  1. Semear registros de `#200`.
  2. Excluir a issue (arquivos locais apagados, snapshot sem `#200`).
  3. Consultar os registros de `#200` **diretamente**.
- **Resultado esperado:** os registros de `#200` **continuam existindo e
  consultáveis** por consulta direta; não são excluídos, anonimizados nem
  rompidos pela exclusão da issue. Ficam sujeitos **apenas** à retenção própria
  (CT-11/CT-12).
- **Observações:** cobre CA-13, RN-10, RNF-09 e a linha "issue com registros é
  excluída" de "comportamento em falha".

### CT-13b — Exclusão de issue preserva os registros também na consulta de linhagem

- **CA de origem (CA-13 / RNF-09 / RN-10):** preservação "por consulta direta e
  por consulta de linhagem".
- **Tipo:** integração (linhagem + exclusão)
- **Arquivo/alvo:** `tests/test_execution_lineage.py`
- **Pré-condição:** raiz `#100` com descendente `#200` (com registros); `#200` é
  excluída (arquivos apagados).
- **Passos:**
  1. Semear a linhagem com `#200` executado como descendente de `#100`.
  2. Excluir `#200`.
  3. Consultar a linhagem de `#100`.
- **Resultado esperado:** `#200` continua presente na linhagem de `#100` com sua
  existência, parentesco e execuções; a exclusão da issue **não** a remove da
  consulta de linhagem.
- **Observações:** cobre RNF-09 na dimensão de linhagem; complementa CT-07
  (arquivamento) com o gatilho de **exclusão**.

### CT-14 — Ausência de superfície de exclusão manual de registro

- **CA de origem (CA-14 / CT-14):** "Dada a superfície exposta pelo sistema,
  quando inspecionada, então não há nenhuma ação de exclusão manual de registro."
- **Tipo:** varredura/revisão (guarda estática de superfície)
- **Arquivo/alvo:** `tests/test_execution_record_surface.py` (novo) ou extensão
  de guarda existente.
- **Pré-condição:** inventário da superfície pública da capacidade (API
  programática exposta pelo módulo, comandos `@---`/CLI, qualquer ponto de
  entrada). O único caminho de remoção legítimo é o **expurgo por retenção**
  (lógica interna, CT-11).
- **Passos:**
  1. Enumerar a superfície pública da capacidade (funções/métodos exportados,
     comandos).
  2. Verificar que nenhuma oferece exclusão/remoção manual de um registro
     específico por qualquer papel (agente ou operador).
- **Resultado esperado:** **nenhuma** operação de exclusão manual de registro é
  exposta; a remoção só existe como **expurgo por retenção** acionado pela lógica
  interna do motor. Registros só nascem na execução e só saem por expurgo (RN-11).
- **Observações:** cobre CA-14, RN-11, RNF-10. É guarda de **superfície** (como
  os testes de `PROTECTED_PATHS`), não de comportamento dinâmico.

### CT-16 — Isolamento de conteúdo: sem prompt nem conversa

- **CA de origem (CA-17 / CT-16):** "Dado qualquer registro, quando inspecionado,
  então ele não contém prompt nem conversa, apenas eventual referência ao log
  detalhado."
- **Tipo:** unitário (registro) + varredura
- **Arquivo/alvo:** `tests/test_execution_record.py` e
  `tests/test_build_prompt_protected_paths.py` (extensão).
- **Pré-condição:** execução cujo prompt e cuja conversa contêm **marcadores
  únicos** (ex.: `PROMPT_SECRETO_123`, `CONVERSA_SECRETA_456`). O log detalhado
  existe e tem um caminho (`log_ref`).
- **Passos:**
  1. Entregar a issue com prompt/conversa marcados.
  2. Inspecionar a estrutura do registro criado (todos os campos).
  3. Verificar que o novo armazenamento durável está em `PROTECTED_PATHS` e que
     `build_prompt` o rejeita se o caminho aparecer no prompt.
- **Resultado esperado:** o registro **não** contém `PROMPT_SECRETO_123` nem
  `CONVERSA_SECRETA_456` em nenhum campo; no máximo um `log_ref` (referência ao
  log detalhado), nunca o conteúdo copiado. O caminho do armazenamento está
  listado em `PROTECTED_PATHS` (`src/core/agent.py`) e `build_prompt` levanta
  `ValueError` se ele aparecer no prompt (mesmo padrão dos demais `.pipe/*`).
- **Observações:** cobre CA-17, RN-13, RNF-07. A verificação do conteúdo do
  armazenamento aqui é explicitamente **verificação de isolamento** (não uso de
  estado interno como fonte de evidência de negócio).

---

## Grupo D — Fonte única, taxonomia total, falhas e baseline

### CT-17 — Fonte única da contagem de execuções (adesão ao `agent_circuit_break`)

- **CA de origem (CA-18 / CT-17):** "Dado que outra entrega do mesmo bloco também
  observa execuções de agente, quando esta capacidade conta execuções por
  contexto, então ela usa a fonte única já existente (`agent_circuit_break`) e
  não mantém contador paralelo."
- **Tipo:** varredura/revisão (guarda de integração) + comportamental
- **Arquivo/alvo:** `tests/test_execution_record.py` e/ou
  `tests/test_agent_circuit_break.py` (guarda cruzada).
- **Pré-condição:** `src/core/agent_circuit_break.py` é a fonte declarada de
  "quantas execuções houve neste contexto `(board, coluna, issue)`" (`occurrences`
  por contexto). Entregar a mesma issue algumas vezes no mesmo contexto.
- **Passos:**
  1. Entregar a issue N vezes no mesmo `(board, coluna, id)`.
  2. Verificar que a **contagem por contexto** observada pela consulta de
     linhagem/registro é **a mesma** mantida por `agent_circuit_break` (uma só
     fonte incrementada no instante da entrega), e que a capacidade **não**
     introduz uma segunda estrutura incrementada independentemente para o mesmo
     fato ("execuções por contexto").
  3. Guarda estática: o código da capacidade **lê/adere** à fonte existente, sem
     um contador paralelo próprio de "execuções por contexto".
- **Resultado esperado:** há **uma única** fonte de verdade para a contagem por
  contexto; esta capacidade adere a ela. O **registro por execução** (um por
  execução, CA-1) não constitui contador paralelo da métrica de contexto — é o
  artefato de negócio por execução; a métrica "quantas execuções no contexto"
  continua tendo origem única em `agent_circuit_break`. Não há duas estruturas
  incrementadas de forma independente para o mesmo evento de entrega.
- **Observações:** cobre CA-18, RN-01 (contagem/repetição corretas), e o
  entregável de verificação de bloco (`/blocks #315`). Trava o invariante
  arquitetural. Distinção importante: o registro por execução **existe** por
  execução (não é "contador paralelo"); o que não pode haver é uma **segunda
  contagem por contexto**.

### CT-18 — Interrupção por infraestrutura antes de finalizar

- **CA de origem (comportamento em falha, 1ª linha):** "Execução interrompida por
  falha de infraestrutura antes de finalizar → gravar registro com `resultado =
  interrompida` ou `desconhecida`, preservando início e o que se conhece de
  fim/duração."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** dispatch espião devolve interrupção transitória
  (`ExecutionResult(classe=UNKNOWN_OUTCOME)` com `origem` de dispatch/timeout) e
  o relógio permite início conhecido e fim parcial.
- **Passos:**
  1. Entregar a issue; interromper a execução antes de finalizar.
  2. Consultar o registro.
- **Resultado esperado:** existe registro (CA-1); `resultado ∈ {interrompida,
  desconhecida}` conforme a evidência disponível, **nunca** vazio; `inicio`
  preservado; `fim`/`duracao` preenchidos com o que se conhece (parciais).
- **Observações:** cobre CA-1, RN-02 e a 1ª linha de "comportamento em falha".
  Par de CT-02 (que fixa o caso de interrupção **com** avanço).

### CT-19 — Desfecho inclassificável grava `desconhecida` (nunca vazio)

- **CA de origem (comportamento em falha, 2ª linha / RN-02):** "Desfecho técnico
  impossível de classificar com segurança → gravar `resultado = desconhecida`,
  nunca campo vazio."
- **Tipo:** unitário (registro)
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** dispatch espião devolve um desfecho **ambíguo/sem evidência
  estruturada suficiente** para classificar com segurança (ex.: `UNKNOWN_OUTCOME`
  sem `origem` conclusiva), que o mapeamento associa a `desconhecida`.
- **Passos:**
  1. Entregar a issue com desfecho inclassificável.
  2. Consultar o registro.
- **Resultado esperado:** `resultado = desconhecida` (um valor da taxonomia
  fechada), **nunca** vazio/nulo. O registro existe e é classificável.
- **Observações:** cobre RN-02 e a 2ª linha de "comportamento em falha".

### CT-20 — Taxonomia fechada, total e determinística (nunca vazio)

- **CA de origem (RN-02 / CA-1):** "`resultado` assume exatamente um de:
  `concluída`, `falha terminal`, `timeout`, `interrompida`, `desconhecida`.
  Desfecho indeterminado grava `desconhecida`, nunca vazio/nulo."
- **Tipo:** unitário (registro), **parametrizado** sobre as classes de
  `ExecutionResult`
- **Arquivo/alvo:** `tests/test_execution_record.py`
- **Pré-condição:** uma matriz cobrindo **todas** as classes de `ExecutionResult`
  — `SUCEDIDO`, `FALHA`, `UNKNOWN_OUTCOME`, `DEFINITE_NOT_STARTED`, `falha
  persistente` — e, se aplicável, variações de `origem` (ex.: `timeout` vs.
  `exit-code` vs. `dispatch failure`) que o mapeamento usa para distinguir
  `timeout`/`falha terminal`/`interrompida`.
- **Passos:**
  1. Para cada classe/variação, entregar a issue com o dispatch espião
     devolvendo aquele `ExecutionResult`.
  2. Consultar o `resultado` gravado.
- **Resultado esperado:** **toda** classe/variação mapeia para **exatamente um**
  valor da taxonomia fechada (`concluída` / `falha terminal` / `timeout` /
  `interrompida` / `desconhecida`); **nenhuma** produz `resultado` vazio/nulo ou
  fora da taxonomia; o mapeamento é **total** (sem classe órfã) e
  **determinístico** (mesma entrada → mesmo `resultado`). Âncoras obrigatórias:
  `SUCEDIDO` sem falha → `concluída`; desfecho inclassificável → `desconhecida`.
- **Observações:** cobre RN-02, CA-1. Trava a **totalidade** do mapeamento sem
  fixar a tabela concreta (que é "como"): a QA exige que seja total, fechado e
  nunca vazio.

### CT-21 — Suporte ao baseline de 30 dias (agregados compõem as 4 métricas)

- **CA de origem (CA-16):** "Dados 30 dias de operação com registros, quando o
  operador designado consulta os agregados, então consegue compor falha
  terminal, repetição sem avanço, cobertura de consumo e consumo/duração por
  etapa sem dado ausente não sinalizado."
- **Tipo:** integração (agregação / baseline)
- **Arquivo/alvo:** `tests/test_execution_lineage.py` ou
  `tests/test_execution_record_baseline.py` (novo).
- **Pré-condição:** um conjunto de registros representando ~30 dias de operação
  (semeados com relógio controlável), com variedade de `resultado` (incl. `falha
  terminal`), repetições sem avanço, execuções com consumo disponível,
  indisponível e zero, em diferentes etapas.
- **Passos:**
  1. Semear o conjunto de 30 dias.
  2. Consultar os agregados necessários ao baseline.
- **Resultado esperado:** a consulta permite compor as quatro métricas do
  baseline — (i) **falha terminal** (via `distribuicao_resultados`); (ii)
  **repetição sem avanço** (via `repeticoes_sem_avanco`); (iii) **cobertura de
  consumo** (quais execuções têm consumo disponível vs. indisponível, com
  `ha_indisponivel` por segmento); (iv) **consumo/duração por etapa** (segmentos
  por unidade/origem e `duracao_total`, derotuláveis por etapa) — **sem** dado
  ausente **não sinalizado** (toda ausência de consumo aparece marcada, RNF-02).
- **Observações:** cobre CA-16, RN-01, RN-04, RNF-01. Não é teste de volume/SLA;
  é prova de que os agregados **compõem** as métricas, com ausências sempre
  sinalizadas.

---

## Fora de escopo dos casos (alinhado à issue)

Os seguintes **não** são testados aqui por estarem fora de escopo da issue:

- painel visual (dashboard) e alertas;
- avaliação automática de qualidade da execução;
- recomendação automática de agente ou modelo;
- conversão de consumo entre unidades ou para moeda sem fonte auditável
  (RN-05/RN-14) — não há caso que converta grandezas;
- exclusão manual de registro por qualquer papel (ao contrário: CT-14 garante a
  **ausência** dessa superfície);
- duplicação de prompt/conversa no registro (ao contrário: CT-16 garante o
  isolamento);
- a **tecnologia de armazenamento**, a **estrutura de dados concreta**, o
  **protocolo** e o **algoritmo de travessia** da linhagem — "como", testado só
  pelo comportamento observável;
- o **mapeamento concreto** classe→taxonomia (CT-20 fixa que é total, fechado e
  nunca vazio; a tabela exata é do desenvolvimento);
- política de **autorização** de quem consulta/exporta (RN-12): é decisão do
  operador da instância; o produto não impõe segunda política de papéis — não há
  caso que teste controle de acesso;
- a meta de **5 minutos** (RNF-05): experiência do operador, não SLA — CT-15
  testa apenas "responde sem abrir logs", não latência;
- atribuição de **retorno monetário** sem baseline/regra auditável (RN-14).

---

## Resumo de arquivos de teste propostos

| Arquivo | Cobre |
|---------|-------|
| `tests/test_execution_record.py` (novo) | CT-01, CT-02, CT-03, CT-04, CT-04b, CT-05, CT-06, CT-13, CT-16, CT-17 (comportamental), CT-18, CT-19, CT-20 (registro por execução: identidade, resultado/avanço independentes, repetição, consumo, isolamento, taxonomia total) |
| `tests/test_execution_lineage.py` (novo) | CT-07, CT-08, CT-09, CT-09b, CT-10, CT-13b, CT-15, CT-21 (consulta por raiz: resiliência a limpeza local, descendente sem registro, ciclo/dupla contagem, segmentação por unidade/origem, resposta sem abrir logs, baseline) |
| `tests/test_execution_record_retention.py` (novo) | CT-11, CT-12 (retenção própria configurável, borda `>= N`, desligada por padrão) |
| `tests/test_execution_record_config.py` (novo, ou extensão de `tests/test_config*`) | CT-11b (validação de forma de `registro.retencao_dias`, padrão `ConfigError` citando o caminho) |
| `tests/test_execution_record_surface.py` (novo, ou extensão de guarda) | CT-14 (ausência de superfície de exclusão manual) |
| `tests/test_build_prompt_protected_paths.py` (extensão) | CT-16 (novo armazenamento durável em `PROTECTED_PATHS`; `build_prompt` rejeita o caminho) |
| `tests/test_agent_circuit_break.py` (guarda cruzada) | CT-17 (fonte única da contagem por contexto — sem contador paralelo) |

### Mapa cenários obrigatórios da issue (CT-01..CT-17) → casos deste documento

| CT da issue | Caso(s) neste documento |
|-------------|-------------------------|
| CT-01 — Concluída sem avanço | CT-01 |
| CT-02 — Interrompida com avanço prévio | CT-02 (+ CT-18 interrupção genérica) |
| CT-03 — Consumo indisponível | CT-03 |
| CT-04 — Consumo zero reportado | CT-04 (+ CT-04b consumo disponível, CA-4) |
| CT-05 — Repetição sem avanço (mesma etapa) | CT-05 |
| CT-06 — Não repetição após mudança de etapa | CT-06 |
| CT-07 — Linhagem resiliente à limpeza local | CT-07 (+ CT-13b exclusão) |
| CT-08 — Descendente sem registro | CT-08 |
| CT-09 — Linhagem com ciclo | CT-09 (+ CT-09b caminho duplo) |
| CT-10 — Agregado com unidades diferentes | CT-10 |
| CT-11 — Retenção configurada expira | CT-11 (+ CT-11b validação de forma) |
| CT-12 — Retenção não configurada | CT-12 |
| CT-13 — Exclusão de issue preserva registros | CT-13 (+ CT-13b por linhagem) |
| CT-14 — Ausência de exclusão manual | CT-14 |
| CT-15 — Resposta da raiz sem abrir logs | CT-15 |
| CT-16 — Isolamento de conteúdo | CT-16 |
| CT-17 — Fonte única de contagem | CT-17 |

> Os 17 cenários obrigatórios (CT-01..CT-17 da issue) estão integralmente
> cobertos; CA-1 (registro sempre criado) e RN-02 (taxonomia total, não-vazia)
> são travados adicionalmente por CT-18/CT-19/CT-20; CA-16 (baseline de 30 dias)
> por CT-21; e os requisitos não funcionais testáveis sem rede
> (RNF-02/03/04/06/07/08/09) ficam cobertos ao longo dos grupos A–D.

### Não regressão

A suíte existente deve continuar passando. Em especial, a capacidade é
**aditiva** no ponto de execução (`call_agent`) e **não** altera o caminho normal
de despacho/recuperação (`_dispatch_with_recovery`), a classificação de
`ExecutionResult`, nem a fonte única de contagem (`agent_circuit_break`). Devem
permanecer verdes, entre outros: `tests/test_agent_circuit_break.py`,
`tests/test_rerun_cooldown.py`, `tests/test_execucao_autonoma_confiavel.py`,
`tests/test_error_classification.py`, `tests/test_snapshot_guard_call_agent.py` e
`tests/test_build_prompt_protected_paths.py`. Sem `registro.retencao_dias`
configurado, nenhum expurgo ocorre (CT-12) — comportamento seguro por padrão.
