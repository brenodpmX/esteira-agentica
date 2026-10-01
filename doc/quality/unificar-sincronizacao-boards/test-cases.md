# Casos de Teste — Unificar a sincronização de boards em um único modelo que sincroniza tudo

- **Issue:** #304
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/304-unificar-sincronizacao-boards`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da issue
> #304 e de seus cenários obrigatórios (CT-01 a CT-08). Cada caso tem resultado
> esperado explícito e verificável. Os testes são da suíte Python do motor
> (pytest, em `tests/`), salvo os marcados como **varredura/revisão** (guarda
> estática de código/logs).

---

## Contexto de arquitetura (baseline do código atual)

Dois caminhos de descoberta remota (down) coexistem hoje — a distinção vive em
**código e estado local**, não em configuração:

- `src/core/board.py::Board.detect_board_changes` — reconciliação **completa**:
  create-down / change-down (com `fullsync=True`, logo reconcilia dependências) /
  delete-down por ausência. Hoje roda **só** na inicialização e **uma vez por dia
  de calendário** (controlada por `last_full_sync` em `src/__main__.py`,
  comparando `datetime.now().date()`).
- `src/core/sync.py::sync_remote` — caminho **por ciclo**. Já busca o board
  inteiro via `board_obj.list_issues` e já faz delete-down por ausência, mas:
  (a) usa `snap.last_board_update` como **corte incremental** (`since`) para
  decidir **quais** issues reconciliar; (b) emite change-down com
  `fullsync=False`, logo **não reconcilia dependências** da maioria dos itens
  (ver `ChangeItem.of(SyncEvent.CHANGE_DOWN, ...)` sem `fullsync=True`);
  (c) quando `since` é vazio, delega a `detect_board_changes`.
- A flag `fullsync` do `ChangeItem` é o que decide se as dependências
  (`blocked_by`/`blocks`) são reconciliadas — ver
  `src/core/sync.py::_write_state_from_issue` e `_apply_change_down`
  (passa `fullsync=item.fullsync` a `get_issue`).
- O corte incremental é persistido em `Snapshot.last_board_update`
  (`src/core/snapshot.py`), inclusive com `setdefault("last_board_update", None)`
  no `load()`.
- A busca do board é **atômica**: o adapter levanta `PenaltyException` em vez de
  devolver página parcial (`src/adapters/github_board.py`), então leitura
  truncada por limite nunca vira ausência/poda.

A unificação, portanto, deve: (1) fazer o caminho por ciclo reconciliar o board
inteiro **sempre**, incluindo dependências; (2) eliminar o corte por
`last_board_update` como critério e descontinuar o campo no snapshot (com
leitura retrocompatível); (3) remover o acionamento diário do caminho completo
como evento separado; (4) apagar a nomenclatura de modo
("full/completo/completa/reduzido/incremental") de nomes, logs e mensagens;
(5) padronizar o log ao contrato mínimo.

> **Decisão de design NÃO fixada pela QA (é do desenvolvimento):** qual função
> "sobrevive" como a sincronização única (fundir `sync_remote` e
> `detect_board_changes`), e o nome único adotado. Os casos abaixo testam o
> **comportamento e os invariantes**, não a assinatura escolhida. Onde um caso
> precisa de um símbolo concreto, ele indica o alvo provável e deixa a
> ancoragem exata a cargo do desenvolvimento (test-first: o teste é escrito
> contra o comportamento esperado e deve passar após a implementação).

---

## Rastreabilidade (CA → casos)

| CA / Cenário | Requisito | Caso(s) |
|--------------|-----------|---------|
| CA-1 / CT-01 — criação em execução única | RF-01, RF-02, RN-01 | CT-01, CT-01b |
| CA-3 / CT-02 — modificação + dependências em execução única | RF-03, RF-05, RN-01 | CT-02, CT-02b |
| CA-2 / CT-03 — poda por ausência | RF-04, RN-03 | CT-03, CT-03b |
| CA-6 / CT-04 — leitura parcial não poda | RN-02, RNF-01 | CT-04 |
| CA-4 / CT-05 — ausência de segundo modo | RF-06, RN-04 | CT-05 |
| CA-5 / CT-06 — nomenclatura única | RF-07, RNF-02 | CT-06, CT-06b |
| CA-7 / CT-07 — snapshot legado | RN-05 | CT-07, CT-07b |
| — / observabilidade | RF-08 | CT-OBS-01, CT-OBS-02 |
| CA-8 / CT-08 — regressão geral | RNF-03 | CT-08 |

---

## Convenções para o desenvolvimento (todos os casos)

- **Offline, sem rede:** usar um `BoardPort` fake (padrão de
  `tests/test_incremental_absent_delete_down.py` e `tests/test_sync_optimization.py`)
  cujo `list_issues` devolve uma lista pré-configurada e cujo `get_issue`
  devolve uma `Issue` com `blocked_by`/`blocks` controlados.
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` por teste (fixture
  autouse), para que `.pipe/` seja isolado — mesmo padrão dos testes existentes.
- **Nunca** fazer `monkeypatch` do próprio símbolo sob teste (lição do incidente
  #106 — mascarava ausência de cobertura real).
- **Drenar a fila** lendo `ChangeQueue.getNext()`/`remove(uuid)` e comparando a
  lista de `(event, id)` resultante, como em `_drain` do teste de delete-down.
- Onde o caso fala em "sincronização única", refira-se ao caminho unificado
  resultante — a função pública que sobreviver. Se o desenvolvimento mantiver o
  nome `sync_remote` como ponto de entrada único, os casos valem diretamente
  sobre ele; se renomear, os casos valem sobre o novo nome (ver CT-06).

---

## Grupo A — Reconciliação completa em execução única

> Alvo principal: o caminho único de descoberta remota resultante
> (`src/core/sync.py`, ex-`sync_remote` + fusão de `detect_board_changes`).

### CT-01 — Criação detectada em execução única (sem evento diário)

- **CA de origem (CA-1 / CT-01):** "Dado um board com issues novas no board
  remoto e ausentes do estado local, quando a sincronização roda uma vez, então
  todas as novas passam a existir localmente na mesma execução, sem depender de
  um evento diário."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_sync_unico.py` (novo), exercitando o caminho
  único sobre um `FakePort`.
- **Pré-condição:** snapshot do board **sem** a issue `#50`; `FakePort.list_issues`
  devolve `#50` (nova). **Nenhum** `last_board_update` previamente gravado
  (snapshot "zerado"/novo).
- **Passos:**
  1. Semear snapshot vazio do board (sem issues, sem corte incremental).
  2. `FakePort` lista `#50` (nova no board).
  3. Rodar a sincronização única **uma vez**.
  4. Drenar a fila.
- **Resultado esperado:** exatamente um evento `create-down` para `#50` é
  enfileirado **nesta única execução** — sem exigir inicialização nem o
  acionamento diário. O item de criação é `fullsync=True` (criação precisa montar
  o body com dependências, pois não há baseline no snapshot).
- **Observações:** hoje, com snapshot novo (`since` vazio), `sync_remote` delega a
  `detect_board_changes`; o comportamento externo (create-down na 1ª passada) já
  deve existir. O caso **fixa a invariante** de que, após a unificação, a criação
  é detectada em execução única **independentemente de haver ou não corte** — ver
  CT-01b, que remove a dependência de "snapshot novo".

### CT-01b — Criação detectada mesmo com snapshot já "quente" (sem corte temporal)

- **CA de origem (CA-1 / RN-01):** a criação não pode depender do corte por data.
- **Tipo:** unitário (regressão do corte incremental)
- **Arquivo/alvo:** `tests/test_sync_unico.py`.
- **Pré-condição:** snapshot já contém `#40` (antiga) **e** — se o campo ainda
  existir no estado legado — um `last_board_update` recente (ex.: data **maior**
  que o `updated_at` da nova issue). `FakePort` lista `#40` e `#51` (nova), onde
  `#51.updated_at` é **anterior** ao `last_board_update` legado (simula uma issue
  cuja data não cruzaria o corte incremental).
- **Passos:**
  1. Semear snapshot com `#40` e um corte incremental recente (estado legado).
  2. `FakePort` lista `#40` (inalterada) e `#51` (nova, `updated_at < corte`).
  3. Rodar a sincronização única **uma vez**.
  4. Drenar a fila.
- **Resultado esperado:** `create-down` para `#51` **é** enfileirado, mesmo com
  `updated_at` abaixo do antigo corte. Isso prova que o corte por
  `last_board_update` deixou de decidir o que reconciliar (RN-01). `#40`, sem
  divergência, não gera evento.
- **Observações:** este é o caso que **falha** no comportamento atual
  (`sync_remote` ignoraria `#51` por `updated_at <= since`) e deve **passar**
  após a unificação. É a prova central da eliminação do corte incremental.

---

## Grupo B — Modificação com reconciliação de dependências

### CT-02 — Modificação de propriedade em execução única

- **CA de origem (CA-3 / CT-02):** "Dada uma issue cujas dependências de bloqueio
  mudaram no board remoto, quando a sincronização roda uma vez, então as
  dependências locais são reconciliadas na mesma execução, sem depender de um
  evento diário." (parte: detecção da modificação)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_sync_unico.py`.
- **Pré-condição:** snapshot contém `#60` (coluna `backlog`); `FakePort` lista
  `#60` com coluna/propriedade divergente (ex.: coluna `desenvolvimento` **ou**
  `updated_at` maior que o do snapshot).
- **Passos:**
  1. Semear snapshot com `#60` em `backlog`.
  2. `FakePort` lista `#60` divergente.
  3. Rodar a sincronização única **uma vez**.
  4. Drenar a fila.
- **Resultado esperado:** um evento `change-down` para `#60` é enfileirado na
  única execução.
- **Observações:** garante a detecção de modificação sem depender da varredura
  diária.

### CT-02b — Modificação reconcilia dependências de bloqueio (fullsync sempre)

- **CA de origem (CA-3 / CT-02 / RF-05):** toda sincronização reconcilia as
  dependências de bloqueio, não apenas propriedades. "Deixa de existir
  reconciliação só-propriedades."
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_sync_unico.py` (detecção) +
  `tests/test_sync_unico_deps.py` (aplicação do change-down).
- **Pré-condição:**
  - snapshot contém `#70` com `blocked_by=["80"]` (estado antigo);
  - `FakePort.list_issues` lista `#70` modificada;
  - `FakePort.get_issue("...","70", fullsync=True)` devolve `Issue` com
    `blocked_by=["90"]` (dependência mudou no board: `80`→`90`).
- **Passos:**
  1. Semear snapshot com `#70` e `blocked_by=["80"]`.
  2. `FakePort` lista `#70` modificada e, no `get_issue`, devolve
     `blocked_by=["90"]`.
  3. Rodar a sincronização única e **processar** o change-down resultante
     (aplicar o down: `_apply_change_down`/equivalente) ou, no mínimo, asserir
     que o `change-down` enfileirado é `fullsync=True`.
  4. Inspecionar: (a) a flag do item e (b) o estado reconciliado das deps.
- **Resultado esperado:**
  - **(a) obrigatório:** o `change-down` de `#70` é `fullsync=True` (o item
    carrega a reconciliação de dependências). Isso é o inverso do baseline, onde
    `sync_remote` emite `fullsync=False` para change-down.
  - **(b) se o caso processar o down:** após aplicar, `get_issue` foi chamado com
    `fullsync=True` e o snapshot/body de `#70` reflete `blocked_by=["90"]`
    (reconciliado), não mais `["80"]`. Em `_write_state_from_issue`, só com
    `fullsync=True` as deps são sobrescritas.
- **Observações:** **caso central do RF-05.** No baseline, `sync_remote` enfileira
  change-down `fullsync=False`, então `get_issue` é chamado sem deps e
  `_write_state_from_issue` **preserva** `["80"]` — a mudança de dependência
  **não** seria reconciliada por ciclo (só na diária). Após a unificação, deve
  ser reconciliada em execução única. Verificar também que o **gatilho de par
  recíproco** (`_trigger_reciprocal_downs`) continua com sua condição de parada
  (não entrar em cadeia infinita) — reaproveitar as asserções de
  `tests/test_sync_optimization.py::test_pair_trigger_*` como referência de
  invariante.

---

## Grupo C — Poda por ausência

### CT-03 — Poda por ausência em execução única

- **CA de origem (CA-2 / CT-03):** "Dado um item removido ou arquivado no board
  remoto, quando a sincronização roda uma vez, então ele é podado do estado local
  na mesma execução."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_sync_unico.py`.
- **Pré-condição:** snapshot contém `#69` (com `id` definido) e `#70`; `FakePort`
  lista **apenas** `#70` (`#69` arquivada/removida sumiu da connection).
- **Passos:**
  1. Semear snapshot com `#69` e `#70`.
  2. `FakePort` lista apenas `#70`.
  3. Rodar a sincronização única **uma vez**.
  4. Drenar a fila.
- **Resultado esperado:** exatamente um evento `delete-down` para `#69`; `#70`
  presente e inalterada **não** gera evento. (Mesma invariante já coberta por
  `tests/test_incremental_absent_delete_down.py`, agora exigida no caminho único
  e **sem** depender de `last_board_update` preexistente.)
- **Observações:** reaproveitar o `FakePort` e `_drain` do teste existente.
  Diferencial: no baseline esse delete-down só ocorre quando `since` já existe;
  após a unificação deve ocorrer na execução única mesmo com snapshot "zerado"
  (ver CT-03b).

### CT-03b — Poda só atinge itens com identidade definida no board (RN-03)

- **CA de origem (RN-03):** "A poda por ausência só se aplica a itens que o estado
  local já conhecia com identidade definida no board."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_sync_unico.py`.
- **Pré-condição:** snapshot contém `#71` (com `id`) **e** um item local
  **sem id** (`id: None`, criado localmente via create-up, ainda sem
  correspondência remota). `FakePort.list_issues` **não** lista nenhum dos dois,
  mas lista ao menos uma issue real diferente (fetch completo e não-vazio).
- **Passos:**
  1. Semear snapshot com `#71` (id definido) e um item `id=None`.
  2. `FakePort` lista uma issue diferente (fetch completo, não truncado).
  3. Rodar a sincronização única **uma vez**.
  4. Drenar a fila.
- **Resultado esperado:** `delete-down` é emitido **apenas** para `#71` (id
  definido e ausente do board). O item `id=None` **nunca** gera delete-down (não
  tem identidade no board) — espelha o filtro `if i.get("id")` já presente em
  `sync_remote`/`detect_board_changes` (`snapshot_by_id` só inclui ids não-nulos).
- **Observações:** evita remoção incorreta de item local ainda sem id. Para não
  colidir com CT-04 (atomicidade), o `FakePort` deve listar ao menos uma issue
  **real e não-vazia** diferente das do snapshot, deixando claro que o fetch foi
  completo (não truncado).

---

## Grupo D — Robustez a limite de requisições (atomicidade)

### CT-04 — Leitura parcial por limite não poda e preserva o estado

- **CA de origem (CA-6 / CT-04 / RN-02 / RNF-01):** "Dada a sinalização de limite
  de requisições durante a leitura do board, quando a sincronização é interrompida
  antes de ler o board por inteiro, então nenhum item é podado, nenhum evento de
  remoção é emitido e o estado local permanece íntegro."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_sync_unico.py`.
- **Pré-condição:** snapshot contém `#69` e `#70`; `FakePort.list_issues`
  **levanta `PenaltyException`** (simula limite durante a leitura — leitura
  atômica, nunca página parcial).
- **Passos:**
  1. Semear snapshot com `#69` e `#70`.
  2. `FakePort.list_issues` levanta `PenaltyException`.
  3. Rodar a sincronização única e **capturar** a `PenaltyException` (ou verificar
     que o caminho a propaga para o nível superior, que já a trata com backoff).
  4. Drenar a fila e reler o snapshot do disco.
- **Resultado esperado:**
  - **nenhum** evento `delete-down` (nem qualquer outro) é enfileirado;
  - o snapshot persistido permanece **idêntico** ao estado anterior (nem `#69`
    nem `#70` marcados como `delete-down`/alterados);
  - a interrupção é sinalizada como limite (`PenaltyException`), não como fetch
    vazio.
- **Observações:** **invariante de segurança (RN-02).** A `PenaltyException` deve
  propagar/ser capturada **antes** de qualquer decisão de poda — o caso falha se
  a implementação interpretar a interrupção como "board vazio" e podar. Testar
  que o fetch é a **primeira** operação e que a ausência de itens só é avaliada
  sobre um fetch bem-sucedido. Ver também CT-OBS-02 (log `resultado=limite`).

---

## Grupo E — Ausência de segundo modo (código)

### CT-05 — Não existe caminho/flag/parâmetro que selecione um segundo escopo

- **CA de origem (CA-4 / CT-05 / RF-06 / RN-04):** "Dado o produto após a mudança,
  quando se procura por um parâmetro, flag, nome de função pública ou caminho de
  código que selecione um escopo de dados de sincronização diferente do modelo
  único, então nenhum é encontrado."
- **Tipo:** varredura estática (teste de guarda) + revisão
- **Arquivo/alvo:** `tests/test_sync_unico_sem_segundo_modo.py` (novo teste de
  guarda que varre `src/`).
- **Pré-condição:** o código-fonte após a implementação.
- **Passos / asserções:**
  1. **Ausência da flag `fullsync` como seletor de escopo:** varrer `src/` por
     ocorrências de `fullsync`. Resultado esperado: a flag não é mais usada para
     **escolher** entre reconciliar "só propriedades" vs. "propriedades + deps"
     no caminho down — ou foi removida, ou toda reconciliação down é sempre
     completa. O desenvolvimento define a forma; o teste assegura que **não há
     dois comportamentos** de down selecionáveis por essa flag. (Se `fullsync`
     sobreviver em outro papel — ex.: no fluxo up — documentar e restringir a
     varredura ao fluxo down.)
  2. **Ausência de `last_board_update` como critério:** varrer `src/` — nenhuma
     leitura de `last_board_update` decide **o que** reconciliar (ver CT-07 para
     a descontinuação do campo).
  3. **Ausência de função pública de "full sync" separada:** não existe mais um
     símbolo público cuja razão de existir seja "o caminho completo" paralelo ao
     "reduzido" (ex.: `detect_board_changes` não é mais acionado como evento
     diário distinto; se o nome sobreviver fundido, não há um **segundo** ponto
     de entrada de escopo menor).
  4. **Ausência do acionamento diário distinto:** varrer `src/__main__.py` —
     não há mais o ramo `if today != last_full_sync: board_full_sync(...)` que
     dispare um caminho de escopo diferente do ciclo normal.
- **Resultado esperado:** todas as asserções acima passam — nenhum seletor de
  "segundo escopo" de sincronização permanece (RN-04). A única opção é a
  sincronização única.
- **Observações:** este caso é a prova anti-regressão de RN-04 ("não reintroduzir,
  sob outro nome ou como otimização interna, um segundo caminho de escopo
  menor"). O desenvolvimento deve confirmar o conjunto exato de símbolos
  (`fullsync`, `last_board_update`, `last_full_sync`, `detect_board_changes`,
  `list_issues_since`) e o teste trava a ausência de seleção de escopo. A
  varredura deve ignorar `tests/` e docs (apenas `src/`).

---

## Grupo F — Nomenclatura única (código, config, logs e mensagens)

### CT-06 — Varredura por qualificadores de modo não encontra uso comportamental

- **CA de origem (CA-5 / CT-06 / RF-07 / RNF-02):** "Dado o produto após a
  mudança, quando se faz uma varredura por termos que qualificam a sincronização
  como 'completo/full/completa' ou 'reduzido/incremental' em código, configuração,
  logs e mensagens, então nenhum uso comportamental permanece — apenas, se houver,
  o nome único de sincronização."
- **Tipo:** varredura estática (teste de guarda)
- **Arquivo/alvo:** `tests/test_sync_unico_nomenclatura.py` (novo).
- **Pré-condição:** código-fonte (`src/`) após a implementação.
- **Passos / asserções:**
  1. Varrer `src/` (code + strings de log/mensagem) por tokens de modo, case-insensitive:
     `full sync`, `fullsync`, `full_sync`, `last_full_sync`, `completo`,
     `completa`, `reduzido`, `reduzida`, `incremental`, `since`/`last_board_update`
     **quando usados como qualificador de sincronização**.
  2. Para cada ocorrência remanescente, exigir que **não** seja um qualificador
     comportamental de sincronização (ex.: `incremental` num comentário sobre
     outro assunto é aceitável; `log.info("Sync", "... full ...")` não é).
- **Resultado esperado:** nenhuma string de log, mensagem ou identificador em
  `src/` qualifica a sincronização como "full/completo/completa" ou
  "reduzido/incremental". Se o nome único for, por ex., "sincronização"/`sync`,
  apenas ele permanece.
- **Observações:** docstrings e comentários **históricos** que apenas narram a
  mudança (ex.: "antes havia dois caminhos") podem permanecer se não forem
  identificadores nem mensagens de runtime — o foco de RNF-02 é
  **comportamento/config/logs/mensagens**. O teste deve ser preciso para não
  gerar falso-positivo em docstring explicativa; recomendo restringir a asserção
  a: (a) nomes de símbolos (def/var), (b) literais passados a `log.*`, e (c)
  chaves de config. O desenvolvimento alinha a lista final de tokens proibidos.

### CT-06b — Nenhuma chave de configuração seleciona escopo de sincronização

- **CA de origem (CA-5 / "Configuração e contratos" / RN-04):** nenhuma chave de
  config seleciona, liga ou dimensiona modo reduzido vs. completo; se existir, é
  removida e sua ausência não quebra a leitura da config.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_project_config.py` (acrescentar) ou
  `tests/test_sync_unico_nomenclatura.py`.
- **Pré-condição:** validador de config em `src/core/config.py`. Hoje a única
  chave sob `sync` é `sync.max_attempts` (fora de escopo).
- **Passos / asserções:**
  1. Afirmar que **não** existe validação/leitura de nenhuma chave de config que
     selecione escopo de sincronização (varredura por chaves tipo
     `sync.mode`, `sync.full`, `sync.incremental`, `full_sync`, etc. em
     `config.py`).
  2. Config contendo **apenas** `sync.max_attempts` continua válida (não quebra).
  3. (Retrocompatibilidade) uma config que, hipoteticamente, trouxesse uma chave
     desconhecida de modo **não** deve quebrar a leitura — chave desconhecida é
     ignorada, não rejeitada (coerente com o contrato da entrega).
- **Resultado esperado:** nenhuma chave de seleção de modo existe no validador;
  `sync.max_attempts` permanece funcionando; config legada carrega sem erro.
- **Observações:** confirma a afirmação do planejamento (nenhuma chave nova é
  necessária e nenhuma de seleção de escopo existe). `sync.max_attempts` está
  **fora de escopo** e não deve ser tocada.

---

## Grupo G — Retrocompatibilidade do snapshot legado

### CT-07 — Leitura de snapshot que ainda contém o campo de corte não falha

- **CA de origem (CA-7 / CT-07 / RN-05):** "Dado um snapshot persistido por uma
  versão anterior que ainda contém o campo do corte incremental, quando a
  sincronização o lê após a mudança, então a leitura não falha e a sincronização
  ocorre normalmente."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_snapshot_legacy.py` (novo) ou acrescentar a um
  teste de snapshot existente.
- **Pré-condição:** escrever manualmente no disco um `snapshot.json` legado
  contendo `last_board_update` (ex.: `"2026-09-01T00:00:00Z"`) **além** dos
  campos atuais (`board`, `issues`, `last_sync`).
- **Passos:**
  1. Gravar `snapshot.json` com o campo legado presente.
  2. `Snapshot(board_id).load()` — não deve levantar exceção.
  3. Rodar a sincronização única sobre esse board (com um `FakePort` simples).
- **Resultado esperado:** `load()` lê sem erro (campo desconhecido/legado é
  **ignorado**, não rejeitado); a sincronização ocorre normalmente e os eventos
  esperados (create/change/delete-down) são produzidos **sem** usar o valor
  legado como corte.
- **Observações:** **prova central de RN-05.** Após a descontinuação, o
  `setdefault("last_board_update", None)` e o par getter/setter em
  `snapshot.py` devem ser removidos **sem** quebrar a leitura de arquivos antigos
  que ainda tenham a chave. Com `json.loads` + acesso por chaves conhecidas, uma
  chave extra no dict é naturalmente ignorada — o teste **trava** essa garantia
  contra uma implementação que valide o schema estritamente.

### CT-07b — Campo de corte é descontinuado na escrita (não reintroduzido)

- **CA de origem (CA-7 / "Estado local (snapshot)"):** o campo que marca a última
  atualização considerada para o corte incremental **deve ser descontinuado**.
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_snapshot_legacy.py`.
- **Pré-condição:** snapshot novo criado pelo código após a mudança.
- **Passos:**
  1. Criar e salvar um snapshot via API corrente (`Snapshot(...).save()`), após
     uma sincronização.
  2. Reler o JSON salvo do disco.
- **Resultado esperado:** o snapshot **recém-escrito** não contém mais a chave de
  corte incremental (`last_board_update`), ou — se o desenvolvimento optar por
  mantê-la inerte por ultra-compatibilidade — ela **não** é lida como critério em
  nenhum ponto do sync (coberto por CT-05/CT-06). A decisão preferencial do
  escopo é **descontinuar** o campo.
- **Observações:** garante que a descontinuação é efetiva (não só "parou de ler",
  mas "parou de escrever/decidir por ele"). Alinhar com o desenvolvimento se o
  campo é removido fisicamente ou apenas deixa de existir no payload novo.

---

## Grupo H — Observabilidade padronizada (contrato mínimo de log)

> **Alvo:** RF-08 e seção "Formato de log de sincronização". Contrato mínimo:
> `sincronizacao board=<board_id> criados=<n> atualizados=<n> removidos=<n> resultado=<ok|limite|erro>`.
> O log **não** deve conter qualificador de modo, nem corpo de issue, arquivo
> protegido ou credencial.

### CT-OBS-01 — Sincronização bem-sucedida emite log no contrato mínimo

- **CA de origem (RF-08 / "Configuração e contratos"):** toda sincronização de
  board emite um log no contrato mínimo definido.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_sync_unico_log.py` (novo), capturando os
  registros emitidos pelo `log` do core (padrão dos testes que capturam
  `log.warning`/`log.info`).
- **Pré-condição:** sincronização única com `FakePort` que produz, numa execução,
  N criados, M atualizados e K removidos conhecidos (ex.: 1 create-down,
  1 change-down, 1 delete-down).
- **Passos:**
  1. Preparar `FakePort`/snapshot para 1 criação, 1 modificação e 1 ausência.
  2. Rodar a sincronização única e capturar os logs.
- **Resultado esperado:** há **um** registro de sincronização por board contendo,
  de forma estruturada/parseável: `board=<id>`, `criados=1`, `atualizados=1`,
  `removidos=1`, `resultado=ok`. O registro **não** contém "full/completo/
  completa/reduzido/incremental", nem corpo de issue, nem caminho de arquivo
  protegido, nem credencial.
- **Observações:** o desenvolvimento define o `component`/formato exato
  (prefixo `sincronizacao`), mas os **campos e contadores** são obrigatórios e
  testáveis. Os contadores devem refletir os eventos realmente enfileirados na
  execução.

### CT-OBS-02 — Interrupção por limite emite log com `resultado=limite` e não poda

- **CA de origem (RF-08 / "Comportamento em falha"):** board sinaliza limite →
  log com `resultado=limite` e identificação do board; nenhum evento de remoção.
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_sync_unico_log.py`.
- **Pré-condição:** `FakePort.list_issues` levanta `PenaltyException` (mesma
  pré-condição de CT-04).
- **Passos:**
  1. Rodar a sincronização única com fetch que levanta `PenaltyException`.
  2. Capturar os logs e drenar a fila.
- **Resultado esperado:** há um registro com `board=<id>` e `resultado=limite`;
  **nenhum** `delete-down` é enfileirado (reforça CT-04 pelo ângulo do log). O
  registro não vaza corpo/credencial.
- **Observações:** par de CT-04 pela observabilidade. Se o tratamento de
  `PenaltyException` ocorrer num nível acima do caminho único, o caso pode
  asserir o log no ponto onde o limite é capturado (`sync_remote_board`/loop) —
  o desenvolvimento indica o ponto; o teste trava `resultado=limite` + ausência
  de poda.

---

## Grupo I — Regressão geral

### CT-08 — Suíte completa passa após a mudança

- **CA de origem (CA-8 / CT-08 / RNF-03):** "Dado o conjunto de testes
  automatizados do projeto, quando ele é executado após a mudança, então passa
  integralmente."
- **Tipo:** regressão (suíte inteira)
- **Arquivo/alvo:** toda a suíte `tests/` via `python -m pytest`.
- **Pré-condição:** implementação concluída na branch.
- **Passos:**
  1. Rodar `python -m pytest` na raiz do repositório.
- **Resultado esperado:** todos os testes passam (0 falhas, 0 erros). Em
  particular, os testes que hoje fixam o comportamento **do caminho incremental**
  — notadamente `tests/test_incremental_absent_delete_down.py` e os
  `test_pair_trigger_*`/`test_queue_*` de `tests/test_sync_optimization.py` —
  devem ser **reconciliados** pelo desenvolvimento com o modelo único:
  - os invariantes ainda válidos (delete-down por ausência; condição de parada do
    par recíproco; upgrade de fullsync na fila) **permanecem** cobertos;
  - testes cujo propósito era especificamente o **corte incremental**
    (`since`/`last_board_update`) devem ser **atualizados** para o modelo único
    (não apenas apagados — o comportamento equivalente no caminho único deve
    continuar coberto pelos casos deste documento).
- **Observações:** **ponto de atenção para o desenvolvimento:**
  `test_incremental_absent_delete_down.py` instancia o comportamento com
  `last_board_update` e espera a semântica do corte. Ao unificar, esse arquivo
  precisa ser migrado para o caminho único (os casos CT-01b, CT-02b, CT-03,
  CT-03b, CT-04 deste documento cobrem o comportamento equivalente). Não deixar a
  suíte vermelha nem deletar cobertura real — migrar.

---

## Notas de execução para o desenvolvimento

- **Test-first:** CT-01b, CT-02b (flag `fullsync=True` no change-down),
  CT-04/CT-OBS-02 (atomicidade), CT-05, CT-06/CT-06b, CT-07/CT-07b e os de log
  devem **falhar** contra o baseline atual (que ainda tem o corte incremental, o
  change-down `fullsync=False`, o acionamento diário e o campo
  `last_board_update`) e **passar** após a unificação.
- **Reaproveitar fakes:** `FakePort` de
  `tests/test_incremental_absent_delete_down.py` e `tests/test_sync_optimization.py`
  são a base; estender `get_issue` para devolver `blocked_by`/`blocks` nos casos
  de dependência (CT-02b).
- **Sem rede/subprocesso:** nenhum teste bate em GitHub real; `list_issues`/
  `get_issue` são fakes. A atomicidade (CT-04) é simulada levantando
  `PenaltyException` no fake.
- **Isolamento:** `monkeypatch.chdir(tmp_path)` por teste; nunca `monkeypatch` do
  símbolo sob teste (lição #106).
- **Fronteira QA↔Dev:** a QA fixa comportamento e invariantes. A escolha de qual
  função sobrevive como "a sincronização" e o nome único são do desenvolvimento;
  onde um caso cita um símbolo (`sync_remote`, `detect_board_changes`,
  `fullsync`, `last_board_update`), ele indica o alvo provável e deve ser
  reancorado ao símbolo final mantendo a asserção de comportamento.
