# Casos de Teste — Retirada segura de colunas de board com migração de issues, bloqueio, retomada e evidência

- **Issue:** #305
- **Story relacionada:** proteção de retirada estrutural de coluna (confiabilidade); bloqueia #315
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/305-retirada-segura-colunas-migracao`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da issue
> #305 e de seus cenários obrigatórios (CT-01 a CT-17). Cada caso tem resultado
> esperado explícito e verificável. Os testes são da suíte Python do motor
> (pytest, em `tests/`), salvo os marcados como **varredura/revisão** (guarda
> estática de código/logs).

---

## Contexto de arquitetura (baseline do código atual)

A reconciliação estrutural de boards existe hoje e é **destrutiva** no ponto que
esta issue protege:

- `src/core/board.py::Board.sync_boards(config)` extrai, de cada board do
  `pipe.yml`, `{id, name, columns}` onde `columns = list(board_cfg["columns"].keys())`,
  ordena por `priority` e delega ao port.
- `src/adapters/github_board.py::GitHubBoard.sync_boards(boards)` compara a ordem
  de opções publicadas do campo `Status` com a lista de colunas desejada e, se
  diferirem, chama `_update_status_options(field_id, columns, existing, name)`.
- `src/adapters/github_board.py::_update_status_options` monta a lista **exata**
  de opções e chama `updateProjectV2Field(... singleSelectOptions: [...] ...)`.
  Essa substituição exata é o que **remove a opção da coluna retirada mesmo com
  issues ainda classificadas nela** — a causa das "issues órfãs de classificação".
  Opções ausentes da nova lista desaparecem; não há drenagem nem confirmação.
- `src/adapters/github_board.py::_create_status_field` cria o campo `Status` com
  a lista de opções quando o campo não existe.
- `BoardPort` (`src/core/board.py`) já oferece as primitivas necessárias:
  `list_issues(board_id)`, `get_issue(board_id, issue_id, fullsync)`,
  `move_issue(board_id, issue_id, column, from_column=None)`. A camada de acesso
  passa por throttle/penalidade (`PenaltyException`) no adapter real.
- **Não existe** hoje: noção de "destino de migração" na configuração; operação
  de preparação não destrutiva separada da contração; núcleo de decisão que
  valide/drene/confirme antes de contrair; evento de evidência por tentativa.

Ordenação do full sync hoje (`src/__main__.py::board_startup_sync`):

1. cria diretórios locais `.pipe/boards/<board>/<col>` e **grava o snapshot
   local** (`snap.board = {col_id: name}`; `snap.save()`);
2. **depois** chama `board.sync_boards(config)` (reconciliação remota);
3. **depois** roda `sync_remote(board_id, board, queue)` por board.

Ou seja, o snapshot da estrutura é gravado **antes** da reconciliação remota.
CA-13 / RF-17 exigem inverter: reconciliar o remoto **primeiro** e gravar o
snapshot **com a estrutura remota efetiva** (incluindo origens retidas por
bloqueio), preservando os diretórios locais dessas origens; uma falha de
reconciliação **não** pode sobrescrever o snapshot anterior.

Validação de configuração (`src/core/config.py`):

- `ConfigError` é a exceção única; o padrão é `validate_*`/`resolve_*` com a
  mensagem **citando o caminho da chave** (ex.: `validate_retry` cita
  `retry.max_tentativas`, rejeita `bool` **antes** de `int`, e aceita ausência
  aplicando defaults). `_validate_boards` já itera `boards.<id>` (dicts), pulando
  chaves escalares como `platform`/`rerun_cooldown`.
- CA-11 / RF-18 encaixam nesse padrão: `boards.<board>.column-migrations` como
  mapa opcional `string → string`, validado por forma, com `ConfigError` citando
  o caminho e a entrada que falhou.

Observabilidade (`src/core/log.py`):

- `log.info(module, msg, **extra)` e `log.warning(module, msg, **extra)` gravam
  no arquivo diário `logs/<AAAA-MM-DD>.json` a linha
  `"<ts> - <LEVEL> - <module> - <msg> | {extra}"`. Os campos estruturados
  (`**extra`) são o veículo da evidência consultável; não exigem abrir arquivos
  internos protegidos (`.pipe/...`).

> **Decisão de design NÃO fixada pela QA (é do desenvolvimento):** o nome e a
> localização do núcleo de decisão (política de validar/drenar/confirmar/contrair),
> a assinatura de `preparar(...)`/`contrair(...)` e onde a reconciliação de
> estrutura passa a ser chamada. Os casos abaixo testam **comportamento e
> invariantes observáveis**, não assinaturas. Onde um caso precisa de um símbolo
> concreto, indica o alvo provável e deixa a ancoragem exata ao desenvolvimento
> (test-first). O que a QA fixa é: a política pertence ao **núcleo de decisão**,
> não à camada de acesso ao provedor (ver "Riscos" da issue).

---

## Rastreabilidade (CA → casos)

| CA / Cenário | Requisito | Regra | Caso(s) |
|--------------|-----------|-------|---------|
| CA-1 / CT-01 — retirada de coluna vazia | RF-01, RF-02, RF-03 | RN-01 | CT-01, CT-01b |
| CA-2 / CT-02 — migração de coluna ocupada com destino válido | RF-04, RF-05, RF-07, RF-10, RF-11 | RN-02, RN-04 | CT-02, CT-02b |
| CA-3 / CT-03 — preservação de atributos | RF-08 | RN-07 | CT-03 |
| CA-4 / CT-04 — destino ausente | RF-04, RF-06 | RN-03 | CT-04 |
| CA-4 / CT-05 — destino inválido | RF-05, RF-06 | RN-03, RN-10 | CT-05a, CT-05b, CT-05c |
| CA-4 / CT-06 — destinos em ciclo | RF-05, RF-06 | RN-03 | CT-06 |
| CA-5 / CT-07 — issue chega durante a drenagem | RF-09, RF-10 | RN-04 | CT-07 |
| CA-6 / CT-08 — falha parcial e retomada | RF-07, RF-14 | RN-05, RN-12 | CT-08 |
| CA-7 / CT-09 — falhas sucessivas (não perda/duplicação) | RF-07, RF-14 | RN-06 | CT-09 |
| CA-8 / CT-10 — sem progresso | RF-13 | RN-05 | CT-10 |
| CA-9 / CT-11 — isolamento entre origens | RF-15 | RN-03 | CT-11 |
| CA-10 / CT-13 — preparação não destrutiva | RF-12 | — | CT-13a, CT-13b |
| CA-11 / CT-12 — validação de forma da configuração | RF-18 | — | CT-12a, CT-12b, CT-12c |
| CA-12 / — evidência por tentativa (campos/níveis) | RF-16 | RN-08 | CT-OBS-01, CT-OBS-02 |
| CA-13 / CT-14 — ordem do full sync e snapshot efetivo | RF-17 | — | CT-14a, CT-14b, CT-14c |
| CA-14 / CT-15 — contagem de chamadas | — | RNF-07 | CT-15 |
| CA-2,6 / CT-16 — idempotência | RF-14 | RN-06, RNF-06 | CT-16 |
| CA-12 / CT-17 — evidência coerente por execução | RF-16 | RN-08, RNF-05 | CT-17 |
| — / rate limit respeitado na drenagem | — | RNF-08 | CT-RL-01 |
| — / segurança da evidência | — | RNF-10 | CT-SEC-01 |

> Observação de cobertura: o escopo da issue está completo e internamente
> consistente — os 14 CAs mapeiam limpo sobre a arquitetura core/adapters
> existente, sem lacuna que exigisse devolver ao planejamento (`revisar-escopo`).
> Os casos abaixo cobrem os 17 CTs obrigatórios mais os invariantes
> não-funcionais testáveis sem rede (RNF-05/06/07/08/10).

---

## Convenções para o desenvolvimento (todos os casos automatizados)

- **Offline, sem rede:** usar um `BoardPort` fake (padrão de
  `tests/test_incremental_absent_delete_down.py` e `tests/test_sync_optimization.py`).
  O fake deve ser **espião controlável**: `list_issues(board_id)` devolve a lista
  corrente de issues por coluna (o teste pode **mutá-la** entre leituras para
  simular drenagem/chegada), `move_issue(...)` registra a chamada e aplica a
  mudança de coluna no estado interno do fake, e um contador separa chamadas de
  `move_issue` de chamadas de leitura de conteúdo (`get_issue`/`update_issue`).
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` por teste (fixture
  `autouse`), para que `.pipe/` e `logs/` sejam isolados — mesmo padrão dos
  testes existentes.
- **Nunca** fazer `monkeypatch` do próprio símbolo sob teste (lição do incidente
  #106 — mascarava ausência de cobertura real). A política de decisão é
  exercitada de verdade; só o **provedor** (port) é fake.
- **Evidência:** ler o arquivo de log do dia (`logs/<data>.json`) e localizar a
  linha do evento `column_migration_attempt`, verificando os campos
  estruturados. **Não** inspecionar arquivos internos protegidos
  (`.pipe/boards/*/snapshot.json`, `.pipe/changeQueue.json`) para auditar
  evidência — isso é exatamente o que RN-08 proíbe.
- **Contração** é a única operação que remove opção; preparação nunca remove.
  Os testes de política verificam **se** e **quando** a contração é acionada,
  não o detalhe GraphQL (que é coberto pelos testes de adapter).
- Onde um caso cita um símbolo (`sync_boards`, núcleo de decisão, `preparar`,
  `contrair`), o alvo é **provável**; se o desenvolvimento adotar outro nome, o
  caso vale sobre o comportamento equivalente.

---

## Grupo A — Decisão e drenagem (núcleo de política)

> Alvo principal: o núcleo de decisão que detecta colunas retiradas, classifica
> origem, valida destino, drena e confirma antes de contrair. Exercitado sobre
> um `FakePort` controlável, sem rede.

### CT-01 — Retirada de coluna vazia (`completed`, `initial_count=0`)

- **CA de origem (CA-1 / CT-01):** "Dado um board com uma coluna sem issues
  ausente da configuração, quando a reconciliação roda, então a opção é retirada
  do board remoto sem exigir destino, após uma leitura remota imediatamente
  anterior confirmar zero issues; a tentativa é registrada como `completed` com
  `initial_count=0`."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py` (novo), exercitando o
  núcleo de decisão sobre `FakePort`.
- **Pré-condição:** board remoto publica a opção de `Status` `revisao` (entre
  outras); a config desejada **não** contém `revisao`; `list_issues` não devolve
  nenhuma issue classificada em `revisao`. Nenhum destino declarado.
- **Passos:**
  1. Montar board remoto (via fake) com opções `[backlog, revisao, done]` e zero
     issues em `revisao`.
  2. Config desejada: `[backlog, done]` (sem `column-migrations`).
  3. Rodar a reconciliação estrutural uma vez.
- **Resultado esperado:** uma leitura remota de `revisao` ocorre imediatamente
  antes da retirada e confirma zero issues; a opção `revisao` é **contraída**
  (deixa de existir no `Status` final `[backlog, done]`); nenhuma issue é movida;
  é emitido exatamente um evento `column_migration_attempt` com
  `result=completed`, `source=revisao`, `initial_count=0`, `moved_count=0`,
  `remaining_count=0`, em nível informativo.
- **Observações:** cobre RN-01 (coluna vazia não exige destino) e RF-02/RF-03.

### CT-01b — Coluna vazia não contrai sem leitura de confirmação imediata

- **CA de origem (CA-1 / RF-03, RF-10):** "...após uma leitura remota
  imediatamente anterior confirmar zero issues."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** mesma de CT-01, mas o fake registra a ordem das chamadas
  (leitura vs. contração).
- **Passos:**
  1. Reconciliar como em CT-01.
  2. Inspecionar a sequência de chamadas registradas pelo fake.
- **Resultado esperado:** há **uma** leitura de issues da origem `revisao`
  **imediatamente antes** da chamada de contração (ordem: ler → confirmar vazio →
  contrair). Nunca contrai sem a leitura imediatamente anterior.
- **Observações:** guarda contra "contrair com base em contagem antiga" (RN-04).

### CT-02 — Migração de coluna ocupada com destino válido

- **CA de origem (CA-2 / CT-02):** "Dado um board com uma coluna de N issues
  (N > 0) e destino válido no mesmo board, ... então as N issues são movidas ao
  destino e a opção só é retirada após uma leitura remota confirmar a origem
  vazia; `moved_count=N` e `remaining_count=0`."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** board com opções `[backlog, revisao, done]`; `revisao` tem
  N=3 issues (`#10, #11, #12`); config desejada `[backlog, done]` com
  `column-migrations: {revisao: done}`. `move_issue` do fake move a issue para a
  coluna alvo no estado interno; `list_issues` reflete o estado após cada move.
- **Passos:**
  1. Reconciliar uma vez.
  2. Drenar e inspecionar as chamadas de `move_issue` e a estrutura final.
- **Resultado esperado:** as 3 issues são movidas para `done` (3 chamadas de
  `move_issue` com `column=done`); após drenar, uma leitura confirma `revisao`
  vazia e **só então** a opção `revisao` é contraída (final `[backlog, done]`);
  evento `column_migration_attempt` com `result=completed`, `source=revisao`,
  `destination=done`, `initial_count=3`, `moved_count=3`, `remaining_count=0`.
- **Observações:** cobre RF-04/RF-05/RF-07/RF-10/RF-11 e RN-02.

### CT-02b — Contração preserva as demais opções (por origem)

- **CA de origem (CA-2 / RF-11):** "Ao remover uma opção, preservar todas as
  demais opções configuradas ou retidas do board."
- **Tipo:** unitário (política) + adapter
- **Arquivo/alvo:** `tests/test_column_withdrawal.py` (política) e
  `tests/test_github_board_contract.py` (novo, adapter).
- **Pré-condição:** board com opções `[backlog, revisao, done, arquivo]`; só
  `revisao` sai da config; `arquivo` permanece publicada mas também fora da
  config desejada e **retida** (ocupada sem destino) no mesmo ciclo.
- **Passos:**
  1. Reconciliar uma vez.
  2. Verificar a lista de opções após a contração de `revisao`.
- **Resultado esperado:** a contração remove **apenas** `revisao`; `backlog`,
  `done` e a retida `arquivo` permanecem com seus identificadores originais
  preservados. No adapter: a mutação de `Status` mantém os `id`s das opções que
  continuam (não recria opções preservadas).
- **Observações:** garante que contrair uma origem não derruba outra origem
  retida no mesmo ciclo (interação com CT-11).

### CT-03 — Preservação de atributos na migração

- **CA de origem (CA-3 / CT-03):** "...então apenas o `Status` muda; título,
  corpo, rótulos, relações e estado aberto/fechado permanecem idênticos."
- **Tipo:** unitário (política) + varredura
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** cenário de CT-02 (N issues migrando de `revisao` para `done`).
- **Passos:**
  1. Reconciliar uma vez.
  2. Inspecionar, no fake, quais métodos de escrita foram chamados por issue.
- **Resultado esperado:** para cada issue migrada, **só** `move_issue` é chamado
  (mudança de coluna/`Status`). **Nenhuma** chamada a `update_issue`,
  `set_labels`/`add_label`/`remove_label`, `set_parent`/`set_children`,
  `set_blocked_by`/`set_blocks`, `close_issue`/`reopen_issue` para efetuar a
  migração. Título, corpo, labels, relações e estado aberto/fechado permanecem
  intactos no estado do fake.
- **Observações:** cobre RF-08/RN-07 e sustenta RNF-07 (sem releitura de
  conteúdo por issue — ver CT-15).

### CT-04 — Destino ausente (`blocked`, `reason=destino_ausente`)

- **CA de origem (CA-4 / CT-04):** "Dado uma coluna ocupada sem destino
  declarado... então nenhuma issue é movida, a opção não é retirada e a tentativa
  é `blocked` com `reason=destino_ausente`."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` com N=2 issues, fora da config desejada, **sem**
  entrada em `column-migrations`.
- **Passos:**
  1. Reconciliar uma vez.
  2. Verificar movimentações, opções finais e evento.
- **Resultado esperado:** zero chamadas de `move_issue`; a opção `revisao`
  **permanece** publicada; evento `column_migration_attempt` com
  `result=blocked`, `source=revisao`, `destination` vazio,
  `reason=destino_ausente`, `initial_count=2`, `moved_count=0`,
  `remaining_count=2`, em nível de **aviso**; a própria mensagem textual
  identifica board, coluna de origem e motivo (sem exigir correlação entre
  registros).
- **Observações:** cobre RN-03; mensagem auto-contida exigida por CA-12.

### CT-05a — Destino inexistente (`reason=destino_inexistente`)

- **CA de origem (CA-4 / CT-05 / RF-05):** destino declarado que **não existe**
  na configuração resultante do mesmo board.
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` ocupada; `column-migrations: {revisao: naoexiste}`
  onde `naoexiste` **não** está nas colunas resultantes do board.
- **Passos:** reconciliar uma vez; inspecionar.
- **Resultado esperado:** nenhuma movimentação; `revisao` não é retirada; evento
  `blocked` com `reason=destino_inexistente` e a origem/motivo na mensagem.
- **Observações:** cobre RN-03 e a validação semântica "existir na config
  resultante".

### CT-05b — Destino em outro board (`reason=destino_mesmo_board_invalido`)

- **CA de origem (CA-4 / CT-05 / RN-10):** destino que é coluna de **outro**
  board (cross-board é inválido por construção).
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** dois boards configurados; `boards.A.column-migrations`
  aponta `revisao` para uma coluna que só existe no board B.
- **Passos:** reconciliar; inspecionar o board A.
- **Resultado esperado:** nenhuma movimentação; a opção não é retirada; evento
  `blocked` com `reason=destino_mesmo_board_invalido`.
- **Observações:** cobre RN-10 e o escopo "um único board por operação". (A
  validação de **forma** aceita qualquer string; a invalidez cross-board é
  **semântica**, detectada na reconciliação — ver CT-12.)

### CT-05c — Destino igual à origem (`reason=destino_e_origem`)

- **CA de origem (CA-4 / CT-05 / RF-05):** destino igual à própria origem.
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` ocupada; `column-migrations: {revisao: revisao}`.
- **Passos:** reconciliar; inspecionar.
- **Resultado esperado:** nenhuma movimentação; opção não retirada; evento
  `blocked` com `reason=destino_e_origem`.
- **Observações:** destino deve ser diferente da origem (RF-05).

### CT-06 — Destinos em ciclo / destino também em retirada (`reason=destino_tambem_retirado`)

- **CA de origem (CA-4 / CT-06):** "Duas colunas ocupadas apontando uma para a
  outra, ambas em retirada → ambas bloqueadas sem nenhuma movimentação."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` e `espera` ambas ocupadas, ambas **fora** da config
  desejada; `column-migrations: {revisao: espera, espera: revisao}`.
- **Passos:** reconciliar; inspecionar ambas as origens.
- **Resultado esperado:** nenhuma movimentação em nenhuma das duas; nenhuma opção
  retirada; **dois** eventos `blocked`, cada um com `reason=destino_tambem_retirado`
  (o destino é outra coluna também em retirada no mesmo ciclo).
- **Observações:** cobre a validação semântica "não ser outra coluna também em
  retirada no mesmo ciclo" (RF-05). Testar também o caso assimétrico (apenas um
  destino está em retirada) deve bloquear essa origem com o mesmo motivo.

### CT-07 — Issue que chega durante a drenagem

- **CA de origem (CA-5 / CT-07):** "Dado que todas as N issues iniciais já foram
  movidas, quando uma issue passa a estar na origem antes da retirada efetiva,
  então ela também é migrada e a retirada só ocorre com a origem de fato vazia."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` com N=2 issues (`#10, #11`), destino válido `done`.
  O fake é configurado para, **na releitura após drenar as 2 iniciais**, injetar
  uma issue extra `#12` em `revisao` (simula item que chega durante a drenagem);
  na leitura seguinte, `revisao` fica vazia.
- **Passos:**
  1. Reconciliar uma vez (política drena em laço até confirmar vazio).
  2. Inspecionar movimentações e opções finais.
- **Resultado esperado:** `#10`, `#11` e `#12` são movidas para `done` (3
  `move_issue`); a contração só ocorre **após** a leitura que confirma `revisao`
  vazia (depois de migrar `#12`); evento `completed` com `moved_count=3`,
  `remaining_count=0`. Nunca contrai com `#12` ainda presente.
- **Observações:** cobre RF-09/RF-10 e RN-04. `initial_count` reflete a leitura
  inicial (2); `moved_count` reflete o total efetivamente movido (3) — a
  especificação de qual contagem o `initial_count` fixa é a leitura inicial da
  tentativa; o invariante forte é `remaining_count=0` e origem comprovadamente
  vazia antes de contrair.

---

## Grupo B — Falha, retomada e idempotência

### CT-08 — Falha parcial e retomada

- **CA de origem (CA-6 / CT-08):** "Dado uma migração que falha após M de N
  issues (0 ≤ M < N)... as M permanecem no destino, as N−M permanecem na origem,
  a opção não foi retirada, e a nova execução migra apenas as N−M restantes."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` com N=3 issues, destino `done`. O fake levanta uma
  exceção de transporte (ou `PenaltyException`) ao mover a 2ª issue (M=1 já
  movida). Estado remoto do fake persiste entre as duas execuções.
- **Passos:**
  1. **Execução 1:** reconciliar; a falha interrompe após mover `#10`.
  2. Verificar estado intermediário.
  3. **Execução 2:** reconciliar de novo (sem a falha configurada).
  4. Verificar estado final.
- **Resultado esperado:** após a execução 1: `#10` está em `done`, `#11`/`#12`
  seguem em `revisao`, `revisao` **não** foi contraída; evento `interrupted` com
  `moved_count` e `remaining_count` coerentes com o momento (1 e 2). Após a
  execução 2: `#11` e `#12` migram (apenas as restantes), `revisao` é contraída;
  o conjunto final em `done` é exatamente `{#10, #11, #12}`.
- **Observações:** cobre RF-07/RF-14, RN-05/RN-12 e RNF-04. A retomada deriva o
  trabalho restante **do estado remoto** (não de estado persistente novo).

### CT-09 — Falhas sucessivas: não perda / não duplicação

- **CA de origem (CA-7 / CT-09):** "Falha após 1 movimento por execução,
  repetido → conjunto final = N originais, sem duplicata; total de movimentações
  = N."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` com N=3 issues. O fake é configurado para mover
  exatamente **uma** issue por execução e então falhar, por 3 execuções; na 4ª,
  confirma vazio e contrai.
- **Passos:**
  1. Rodar 4 execuções sequenciais sobre o mesmo estado remoto do fake.
  2. Somar as chamadas de `move_issue` e comparar o conjunto de ids em `done`.
- **Resultado esperado:** o total de chamadas de `move_issue` é **exatamente 3**
  (nenhuma issue já no destino é removida/recontada/reprocessada); o conjunto de
  identificadores final em `done` é exatamente `{#10, #11, #12}` (sem faltar nem
  duplicar); `revisao` contraída só na execução que confirma vazio.
- **Observações:** cobre RN-06, RNF-03 e RNF-06 (idempotência por conjunto de
  ids; a ordem de processamento não afeta o resultado).

### CT-10 — Interrupção por ausência de progresso (`reason=sem_progresso`)

- **CA de origem (CA-8 / CT-10):** "Duas leituras consecutivas com a mesma
  contagem (> 0) → `interrupted`, `reason=sem_progresso`, sem contrair, sem laço
  infinito."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` com N=2 issues, destino válido `done`, mas o fake
  faz `move_issue` ser **no-op** (a issue permanece na origem — simula provedor
  que aceita a mutação mas a releitura não reduz a contagem).
- **Passos:**
  1. Reconciliar uma vez.
  2. Verificar número de passagens/leituras e o evento.
- **Resultado esperado:** a política detecta que uma passagem completa **não
  reduziu** a contagem da origem e **encerra** a tentativa daquela origem;
  `revisao` **não** é contraída; evento `interrupted` com `reason=sem_progresso`,
  `moved_count` e `remaining_count` do momento; o teste **termina** (sem laço
  infinito) — reforçado por um limite de iterações/timeout defensivo no teste
  que, se atingido, falha o caso.
- **Observações:** cobre RF-13 e RN-05. Chave para a coluna sob fluxo contínuo
  (risco citado na issue).

### CT-16 — Idempotência: reexecução no mesmo estado

- **CA de origem (CA-2/CA-6 / CT-16 / RNF-06):** "Reexecução no mesmo estado, com
  issues já no destino → nenhuma movimentação extra; mesmo resultado final."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** estado já convergido — `revisao` **já** contraída e as issues
  já em `done` (resultado de uma migração anterior bem-sucedida); config desejada
  estável.
- **Passos:**
  1. Reconciliar novamente sobre o estado já convergido.
  2. Verificar movimentações e estrutura.
- **Resultado esperado:** zero `move_issue`; nenhuma contração extra (não há mais
  opção `revisao` publicada, logo não há origem retirada a tratar); estrutura
  final idêntica. Nenhum evento `column_migration_attempt` para `revisao` (não é
  mais uma coluna publicada fora da config).
- **Observações:** cobre RNF-06. Garante convergência estável.

---

## Grupo C — Isolamento, preparação e contagem

### CT-11 — Isolamento entre origens

- **CA de origem (CA-9 / CT-11):** "Uma origem válida e uma bloqueada no mesmo
  ciclo → válida concluída, bloqueada preservada, sem interferência."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** mesmo board com duas colunas retiradas: `revisao` (ocupada,
  destino válido `done`) e `espera` (ocupada, **sem** destino declarado).
- **Passos:**
  1. Reconciliar uma vez.
  2. Verificar cada origem de forma independente.
- **Resultado esperado:** `revisao` é drenada e contraída (`completed`); `espera`
  é bloqueada e **permanece publicada** com suas issues intactas
  (`blocked`, `reason=destino_ausente`); o bloqueio de `espera` **não** impede o
  processamento de `revisao`. Dois eventos distintos, um por origem.
- **Observações:** cobre RF-15. Testar também isolamento **entre boards** (um
  board bloqueado não impede a reconciliação de outro) como variação do caso.

### CT-13a — Preparação não destrutiva: cria destino, não remove origem retirada

- **CA de origem (CA-10 / CT-13):** "Preparação com uma coluna nova de destino e
  uma coluna em retirada → a coluna de destino é criada e a coluna em retirada
  **não** é removida nessa etapa, preservando os identificadores das opções
  existentes."
- **Tipo:** integração (adapter)
- **Arquivo/alvo:** `tests/test_github_board_contract.py` (novo), com um fake do
  cliente GraphQL (`_gql`) que registra as mutações emitidas — **sem** rede.
- **Pré-condição:** board remoto com opções `[backlog, revisao, done]` (ids
  conhecidos); estrutura desejada acrescenta a coluna nova `entregue` e retira
  `revisao` (ainda ocupada).
- **Passos:**
  1. Chamar a operação de **preparação** (`preparar(estrutura_desejada)` ou
     equivalente).
  2. Inspecionar as mutações emitidas ao provedor.
- **Resultado esperado:** `entregue` é **criada**; `revisao` **não** é removida
  nesta etapa; `backlog`, `revisao`, `done` mantêm seus `id`s de opção
  originais (preparação preserva TODAS as opções existentes, inclusive em vias de
  retirada). Nenhuma mutação de contração é emitida pela preparação.
- **Observações:** cobre RF-12. Preparação e contração são operações distintas; a
  preparação **nunca** remove opção.

### CT-13b — Preparação cria boards/campo Status ausentes preservando opções

- **CA de origem (CA-10 / RF-12):** "Criar boards/campo `Status`/colunas ausentes
  preservando as opções remotas existentes."
- **Tipo:** integração (adapter)
- **Arquivo/alvo:** `tests/test_github_board_contract.py`
- **Pré-condição:** (i) board sem campo `Status` → preparação cria o campo com as
  colunas desejadas; (ii) board com campo `Status` e uma opção extra `legado`
  ausente da config → preparação **mantém** `legado`.
- **Passos:** chamar a preparação nos dois sub-cenários; inspecionar mutações.
- **Resultado esperado:** (i) `createProjectV2Field` (ou equivalente) é emitido
  com as colunas desejadas quando o campo não existe; (ii) a opção extra `legado`
  é preservada (não aparece em nenhuma mutação de remoção), com `id` intacto.
- **Observações:** garante que a preparação é estritamente aditiva.

### CT-15 — Contagem de chamadas (exatamente N mutações de `Status`)

- **CA de origem (CA-14 / CT-15 / RNF-07):** "Origem com N issues e destino
  válido → exatamente N mutações de `Status`; sem releitura de conteúdo por
  issue."
- **Tipo:** unitário (política) com fake instrumentado
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` com N=4 issues, destino válido `done`; o fake conta
  separadamente: (a) chamadas de `move_issue` (mutação de `Status`), (b) chamadas
  de `get_issue`/`update_issue` (leitura/reescrita de conteúdo por issue).
- **Passos:**
  1. Reconciliar uma vez (migração completa).
  2. Ler os contadores do fake.
- **Resultado esperado:** exatamente **N=4** chamadas de `move_issue`; **zero**
  chamadas de `get_issue`/`update_issue` por issue para efeito de migração (a
  migração não relê conteúdo nem relações por issue). As leituras adicionais
  permitidas são as de **listagem/drenagem** da origem (`list_issues`), não por
  issue.
- **Observações:** cobre RNF-07. Interage com CT-03 (só `Status` muda).

### CT-RL-01 — Rate limit respeitado na drenagem (sem retentativa paralela)

- **CA de origem (RNF-08 / comportamento em falha):** "Todas as chamadas ao
  provedor respeitam o throttle e a penalidade existentes; nenhuma retentativa
  paralela. Penalidade durante a drenagem não contrai a origem parcialmente
  drenada."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_column_withdrawal.py`
- **Pré-condição:** `revisao` com N=3 issues; o fake levanta `PenaltyException`
  ao mover a 2ª issue.
- **Passos:**
  1. Reconciliar uma vez.
  2. Verificar tratamento da `PenaltyException` e estado.
- **Resultado esperado:** a `PenaltyException` **propaga** para o laço de
  reconciliação existente (que já a trata com `time.sleep(e.wait_seconds)` no
  `board_startup_sync`), **sem** retentativa paralela dentro da política; a
  origem **não** é contraída (parcialmente drenada); a tentativa registra
  `interrupted` com `moved_count`/`remaining_count` do momento, mantendo a origem
  presente na estrutura efetiva.
- **Observações:** cobre RNF-08 e a linha "penalidade de rate limit durante a
  drenagem" da tabela de falhas. Não deve introduzir throttle paralelo próprio.

---

## Grupo D — Configuração (validação de forma)

> Alvo: `src/core/config.py`, nova função `validate_column_migrations` (ou
> integração em `_validate_boards`), no padrão `ConfigError` que **cita o
> caminho da chave** `boards.<board>.column-migrations` e a entrada que falhou.

### CT-12a — Mapa de destinos válido é aceito

- **CA de origem (CA-11 / CT-12 / RF-18):** "Um mapa de strings não vazias é
  aceito."
- **Tipo:** unitário (config)
- **Arquivo/alvo:** `tests/test_column_migrations_config.py` (novo).
- **Pré-condição:** config com `boards.entrega.column-migrations: {revisao: done}`.
- **Passos:** chamar a validação de forma.
- **Resultado esperado:** nenhuma exceção; a configuração é aceita. (A validação
  de **forma** não exige que `done`/`revisao` existam nas colunas — isso é
  **semântica**, verificada na reconciliação; ver CT-05.)
- **Observações:** cobre RF-18 (aceita mapa de strings não-vazias).

### CT-12b — Ausência do mapa é válida (compatibilidade)

- **CA de origem (CA-11 / CT-12 / RNF-09):** "A ausência do mapa é aceita."
- **Tipo:** unitário (config)
- **Arquivo/alvo:** `tests/test_column_migrations_config.py`
- **Pré-condição:** config de board **sem** `column-migrations`.
- **Passos:** chamar a validação de forma.
- **Resultado esperado:** nenhuma exceção; comportamento estrutural vigente
  preservado (boards sem retirada de coluna não mudam de comportamento).
- **Observações:** cobre RNF-09 (declaração opcional).

### CT-12c — Tipos/valores inválidos são rejeitados com `ConfigError` citando o caminho

- **CA de origem (CA-11 / CT-12 / RF-18):** "Qualquer tipo/valor inválido é
  rejeitado com `ConfigError` citando o caminho `boards.<board>.column-migrations`
  e a entrada que falhou."
- **Tipo:** unitário (config), parametrizado
- **Arquivo/alvo:** `tests/test_column_migrations_config.py`
- **Pré-condição:** cada sub-caso parametrizado com uma config inválida:
  1. `column-migrations` como lista (`[revisao, done]`) — não é mapa;
  2. `column-migrations` como string;
  3. valor vazio após `strip` (`{revisao: "   "}`);
  4. valor nulo (`{revisao: null}`);
  5. valor não-string (`{revisao: 10}`);
  6. chave vazia após `strip` (`{"  ": done}`);
  7. chave não-string, se expressável no YAML carregado.
- **Passos:** chamar a validação de forma para cada sub-caso.
- **Resultado esperado:** cada sub-caso levanta `ConfigError` cuja mensagem
  **cita** `boards.<board>.column-migrations` **e** a entrada específica que
  falhou (chave/valor). Nenhum sub-caso é aceito silenciosamente.
- **Observações:** cobre RF-18. Seguir o padrão de `validate_retry` (rejeitar
  antes de prosseguir, mensagem acionável). Não validar semântica aqui.

---

## Grupo E — Full sync, snapshot e evidência

### CT-14a — Ordem: reconciliar o remoto ANTES de gravar o snapshot

- **CA de origem (CA-13 / CT-14 / RF-17):** "A estrutura remota é reconciliada
  antes de o snapshot ser gravado."
- **Tipo:** integração (orquestração)
- **Arquivo/alvo:** `tests/test_full_sync_order.py` (novo), exercitando
  `board_startup_sync` (ou o ponto de orquestração do full sync) com `FakePort`
  e um `Board` espião que registra a **ordem** entre "reconciliar estrutura
  remota" e "gravar snapshot".
- **Pré-condição:** config com uma origem retirada; fake registra timestamps/
  ordem das operações.
- **Passos:**
  1. Rodar o full sync uma vez.
  2. Comparar a ordem: reconciliação de estrutura remota vs. `Snapshot.save()`.
- **Resultado esperado:** a reconciliação da estrutura remota ocorre **antes** da
  gravação do snapshot de estrutura (inversão da ordem atual do
  `board_startup_sync`, que hoje grava o snapshot antes de `sync_boards`).
- **Observações:** cobre RF-17. Este caso **falha** no baseline atual (ordem
  invertida) — é test-first.

### CT-14b — Snapshot reflete a estrutura efetiva e preserva diretórios de origens retidas

- **CA de origem (CA-13 / CT-14 / RF-17):** "O snapshot reflete a estrutura
  efetiva (incluindo origens retidas) e os diretórios locais dessas origens são
  preservados."
- **Tipo:** integração (orquestração)
- **Arquivo/alvo:** `tests/test_full_sync_order.py`
- **Pré-condição:** `revisao` está fora da config desejada mas é **retida**
  (ocupada, bloqueada) na reconciliação; existe diretório local
  `.pipe/boards/<board>/revisao/` com um arquivo.
- **Passos:**
  1. Rodar o full sync uma vez.
  2. Ler `snap.board` e verificar o diretório local de `revisao`.
- **Resultado esperado:** `snap.board` **inclui** `revisao` (origem retida que
  permanece publicada remotamente), não apenas as colunas da config; o diretório
  `.pipe/boards/<board>/revisao/` e seu conteúdo são **preservados** (não
  apagados por não estarem na config). *(Leitura de `snap.board` aqui é
  verificação de teste da estrutura resultante, não auditoria de evidência de
  negócio — RN-08 trata de evidência de tentativa, coberta por CT-OBS.)*
- **Observações:** cobre RF-17. O snapshot segue a **estrutura remota efetiva**,
  não a config desejada quando divergem por retenção.

### CT-14c — Falha de reconciliação não sobrescreve o snapshot anterior

- **CA de origem (CA-13 / CT-14 / comportamento em falha):** "Uma falha de
  reconciliação não sobrescreve o snapshot anterior."
- **Tipo:** integração (orquestração)
- **Arquivo/alvo:** `tests/test_full_sync_order.py`
- **Pré-condição:** existe um snapshot anterior com conteúdo conhecido; a
  reconciliação remota levanta uma exceção genérica (não `PenaltyException`)
  antes de retornar a estrutura efetiva.
- **Passos:**
  1. Semear snapshot anterior.
  2. Rodar o full sync; a reconciliação falha.
  3. Ler o snapshot em disco.
- **Resultado esperado:** o snapshot anterior permanece **intacto** (não
  sobrescrito com estrutura parcial); o erro propaga conforme o tratamento
  vigente.
- **Observações:** cobre a linha "falha na reconciliação antes de retornar a
  estrutura efetiva". Distinguir de `PenaltyException`, que é retomável por
  `sleep` (ver CT-RL-01).

### CT-OBS-01 — Evidência por tentativa: campos e níveis

- **CA de origem (CA-12 / RF-16 / RN-08):** "Encontra `board`, `source`,
  `destination` (quando aplicável), `initial_count`, `moved_count`,
  `remaining_count`, `result` e `reason` (quando bloqueada/interrompida), sem
  abrir arquivos internos protegidos, com `blocked`/`interrupted` em nível de
  aviso e `completed` em nível informativo."
- **Tipo:** unitário (observabilidade)
- **Arquivo/alvo:** `tests/test_column_migration_evidence.py` (novo), lendo o
  arquivo de log do dia em `logs/<data>.json`.
- **Pré-condição:** três tentativas provocadas em sequência: uma `completed`
  (CT-02), uma `blocked` (CT-04) e uma `interrupted` (CT-10).
- **Passos:**
  1. Provocar cada tentativa.
  2. Localizar as linhas do evento `column_migration_attempt` no log do dia.
  3. Conferir campos e nível por tentativa.
- **Resultado esperado:**
  - cada tentativa produz **exatamente um** registro `column_migration_attempt`;
  - os campos presentes: `board`, `source`, `initial_count`, `moved_count`,
    `remaining_count`, `result`; `destination` presente quando aplicável
    (vazio/omitido em `completed` de coluna vazia sem destino e aceitável vazio);
    `reason` presente e não-vazio em `blocked`/`interrupted`, vazio/omitido em
    `completed`;
  - `completed` é gravado em nível **INFO**; `blocked` e `interrupted` em nível
    **WARNING** (verificável pela coluna de nível na linha do log);
  - toda a evidência está no log normal da esteira — **nenhuma** leitura de
    `.pipe/boards/*/snapshot.json` nem `.pipe/changeQueue.json` é necessária.
- **Observações:** cobre RF-16/RN-08/RNF-05. O teste asserta sobre o conteúdo
  textual/estruturado da linha de log, não sobre arquivos protegidos.

### CT-OBS-02 — Mensagem de `blocked` é auto-contida

- **CA de origem (CA-12 / RN-08):** "Para `blocked`, a própria mensagem textual
  identifica board, coluna de origem e motivo específico, sem exigir correlação
  entre registros."
- **Tipo:** unitário (observabilidade)
- **Arquivo/alvo:** `tests/test_column_migration_evidence.py`
- **Pré-condição:** uma tentativa `blocked` (ex.: `destino_inexistente`).
- **Passos:** localizar a linha `blocked`; inspecionar a mensagem textual.
- **Resultado esperado:** a mensagem (não apenas os campos extra) contém board,
  coluna de origem e o motivo específico, legível isoladamente sem juntar com
  outras linhas.
- **Observações:** cobre a exigência de mensagem auto-contida de CA-12.

### CT-17 — Evidência coerente por execução (não acumulada)

- **CA de origem (CA-12 / CT-17 / RNF-05):** "Sequência de execuções parciais →
  cada tentativa reflete o estado real daquela execução, não um acumulado."
- **Tipo:** unitário (observabilidade)
- **Arquivo/alvo:** `tests/test_column_migration_evidence.py`
- **Pré-condição:** cenário de CT-08/CT-09 — execuções parciais sucessivas sobre
  a mesma origem (`N=3`, uma movida por execução).
- **Passos:**
  1. Rodar as execuções parciais em sequência.
  2. Para cada execução, ler o registro `column_migration_attempt` emitido.
- **Resultado esperado:** cada registro reflete o estado **daquela** execução:
  por exemplo, execução 1 → `moved_count=1`, `remaining_count=2`,
  `result=interrupted`; execução 2 → `moved_count=1` (daquela passagem),
  `remaining_count=1`; execução final → `remaining_count=0`, `result=completed`.
  Nenhum `moved_count` é um **acumulado** cross-execução; os contadores são por
  tentativa.
- **Observações:** cobre RNF-05 e a linha "estado remoto é a fonte de verdade;
  tentativas sucessivas com contagens coerentes com o estado real de cada
  execução". Define a semântica de `moved_count` como **por tentativa**.

---

## Grupo F — Segurança da evidência (varredura)

### CT-SEC-01 — Logs não contêm conteúdo sensível

- **CA de origem (RNF-10):** "Logs não contêm credenciais, corpo de issue,
  contexto de agente nem conteúdo de estado protegido."
- **Tipo:** varredura/revisão (guarda estática do evento emitido)
- **Arquivo/alvo:** `tests/test_column_migration_evidence.py`
- **Pré-condição:** issues com corpo não trivial em migração (CT-02), onde o
  corpo contém um marcador único (ex.: `CORPO_SECRETO_123`).
- **Passos:**
  1. Provocar a migração.
  2. Ler todas as linhas `column_migration_attempt` do log.
- **Resultado esperado:** nenhuma linha de evidência contém o marcador do corpo
  da issue, tokens/credenciais, nem caminhos/conteúdo de arquivos de estado
  protegido; os campos são estritamente os de contagem/resultado/identificação
  (board, source, destination, counts, result, reason).
- **Observações:** cobre RNF-10. A evidência é mínima e não vaza conteúdo.

---

## Fora de escopo dos casos (alinhado à issue)

Os seguintes **não** são testados aqui por estarem fora de escopo da issue:

- migração de issues entre boards **diferentes** (apenas o bloqueio cross-board
  é testado — CT-05b);
- destino diferente por issue dentro da mesma coluna (roteamento por issue);
- arquivamento/encerramento como destino;
- limite de WIP por coluna;
- fluxo de autorização/aprovação para retirar coluna;
- SLA/prazo de conclusão da migração;
- alteração das regras gerais de movimentação de issue (eventos `on_in`/`on_out`,
  retenção de tarefa);
- **rollback** dos itens já movidos após falha parcial (o estado parcial é válido
  e convergente — CT-08/CT-09 asseguram convergência, não rollback);
- limpeza automática de issues que já estavam sem `Status` antes da tentativa;
- dashboards/métricas agregadas em observabilidade externa.

A **janela residual** contra escritor externo (RNF-11) é limitação documentada;
os casos exercitam a leitura imediatamente anterior à contração (CT-01b/CT-02) e
a verificação de origem vazia, que é o que a aplicação pode garantir — não há
caso que exija atomicidade impossível no provedor.

---

## Resumo de arquivos de teste propostos

| Arquivo | Cobre |
|---------|-------|
| `tests/test_column_withdrawal.py` | CT-01, CT-01b, CT-02, CT-02b, CT-03, CT-04, CT-05a/b/c, CT-06, CT-07, CT-08, CT-09, CT-10, CT-11, CT-15, CT-16, CT-RL-01 (política de decisão/drenagem) |
| `tests/test_column_migrations_config.py` | CT-12a, CT-12b, CT-12c (validação de forma em `config.py`) |
| `tests/test_github_board_contract.py` | CT-02b (adapter), CT-13a, CT-13b (preparação não destrutiva vs. contração no adapter) |
| `tests/test_full_sync_order.py` | CT-14a, CT-14b, CT-14c (ordem do full sync e snapshot efetivo) |
| `tests/test_column_migration_evidence.py` | CT-OBS-01, CT-OBS-02, CT-17, CT-SEC-01 (evidência e segurança) |

Sem regressão: a suíte existente de reconciliação estrutural e sync
(`tests/test_sync_unico*.py`, `tests/test_incremental_absent_delete_down.py`,
`tests/test_sync_optimization.py`) deve continuar passando — boards **sem**
`column-migrations` mantêm o comportamento estrutural vigente (RNF-09).
