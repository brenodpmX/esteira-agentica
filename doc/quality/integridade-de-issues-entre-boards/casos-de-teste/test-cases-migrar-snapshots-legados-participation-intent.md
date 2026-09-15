# Casos de Teste — Migrar snapshots legados sem `participation_intent` no full sync de startup

- **Task:** #257 — Migrar snapshots legados sem `participation_intent` no full sync de startup
- **User Story:** #245 — Gate de elegibilidade por intenção confirmada em `keep_task`
- **Arquivo de teste alvo:** `tests/test_participation_intent_migration.py`
- **Autor:** Camila Rocha - Engenheira de Qualidade (QA)

## Rastreamento de critérios de aceitação

Critérios de aceite da task #257:
- **CA1** — Implementação segue arquitetura (função pura no core, sem import de
  adapter; sem chamada de rede; só I/O de snapshot local).
- **CA2** — Código cobre o cenário descrito (migração `origin`/`unresolved`,
  não sobrescrita, board não configurado, integração em `board_full_sync`).
- **CA3** — Testes unitários criados.
- **CA4** — Sem quebra de funcionalidades existentes (suíte completa sem
  regressão).

Critério de aceitação da story #245 (âncora de negócio):
- **CA-Story** — "Dado um snapshot legado sem `participation_intent`, quando o
  full sync de startup roda antes do primeiro `keep_task`, então o campo é
  migrado conforme a regra de unicidade/duplicidade descrita, e nenhuma issue
  chega a `keep_task` sem o campo preenchido."

Regras de referência: **RN-B01** (participação sem prova de intenção nunca é
executável) e **ADR-001** ("Na migração, uma issue presente em um único board
configurado recebe `origin`. Duplicidades legadas sem label permanecem
bloqueadas... não se escolhe uma origem por ordem de filesystem ou
prioridade").

## Pré-condições comuns

- Ambiente isolado: `tmp_path` como cwd; `BOARDS_DIR` de `src.core.snapshot`
  (e do módulo que hospedar a função, se importar `Snapshot`) apontando para
  `tmp_path/.pipe/boards` via `monkeypatch` — padrão já usado em
  `tests/test_orphan_detection.py`.
- `config` mínimo com `boards.platform` + N boards configurados, cada um com
  `columns`. A chave `platform` deve ser ignorada pela iteração de boards
  (mesmo padrão de `get_board_ids`/`Board.board_ids`, que ignoram `platform` e
  entradas que não são `dict`).
- Snapshots criados manualmente via `Snapshot(board_id)` com `issues` como
  `list[dict]` livre (sem dataclass nova), gravados com `save()`.
- Nenhum mock de `Board`/`BoardPort` é necessário nos casos CT-01..CT-06
  (função pura em rede). O caso CT-07 usa um `Board`/port fake e spy.

---

## CT-01 — Issue em board único legado recebe `origin`

- **Critério:** CA2, CA-Story, ADR-001 (unicidade → `origin`)
- **Tipo:** unitário
- **Pré-condição:** `config` com 1+ boards configurados. Snapshot do board
  `task` contém uma issue `{"id": "100"}` **sem** a chave
  `participation_intent`. Nenhum outro board contém entrada com `id == "100"`.
- **Passos:**
  1. Persistir o snapshot legado.
  2. Chamar `migrate_legacy_participation_intent(config)`.
  3. Recarregar `Snapshot("task").load()` e localizar a entrada `id == "100"`.
- **Resultado esperado:** a entrada passa a ter
  `participation_intent == "origin"`. Nenhuma outra chave da entrada é
  removida/alterada.

## CT-02 — Mesma issue em dois boards configurados legados recebe `unresolved` em ambos

- **Critério:** CA2, CA-Story, ADR-001 (duplicidade legada → `unresolved`),
  RN-B01
- **Tipo:** unitário
- **Pré-condição:** `config` com pelo menos 2 boards configurados (ex.: `task`
  e `bug`). Ambos os snapshots contêm uma entrada com o **mesmo** `id`
  (ex.: `"200"`), ambas **sem** `participation_intent`.
- **Passos:**
  1. Persistir os dois snapshots legados.
  2. Chamar `migrate_legacy_participation_intent(config)`.
  3. Recarregar ambos os snapshots e localizar a entrada `id == "200"` em cada.
- **Resultado esperado:** **ambas** as entradas passam a ter
  `participation_intent == "unresolved"`. Nenhuma escolha automática de origem
  por ordem de filesystem/prioridade.

## CT-03 — Entrada já com `participation_intent` não é sobrescrita (mesmo em duplicidade)

- **Critério:** CA2, "roda uma única vez por issue", RN-B01
- **Tipo:** unitário
- **Pré-condição:** issue `id == "300"` presente em 2 boards configurados:
  - board A: entrada com `participation_intent` **já preenchido** (testar
    dois subcasos: valor `"authorized"` e valor `None` explícito no dict);
  - board B: entrada **sem** o campo.
- **Passos:**
  1. Persistir os snapshots.
  2. Chamar `migrate_legacy_participation_intent(config)`.
  3. Recarregar ambos.
- **Resultado esperado:**
  - A entrada do board A **permanece inalterada** (mantém `"authorized"` no
    subcaso 1; mantém `None` no subcaso 2 — a distinção entre chave ausente e
    chave com `None` deve ser respeitada via `"participation_intent" not in
    issue_dict`, nunca `.get(...)`).
  - A entrada do board B (não migrada) recebe `"unresolved"` (a contagem de
    "2+ boards" considera a entrada já preenchida do board A como presença).

## CT-04 — Entrada em board NÃO configurado não conta como duplicidade → `origin`

- **Critério:** CA2, iteração restrita a `config["boards"]`
- **Tipo:** unitário
- **Pré-condição:** issue `id == "400"` presente em:
  - board `task` (configurado em `config["boards"]`) — sem o campo;
  - board `removido` — diretório de snapshot existe em disco (`.pipe/boards/
    removido/snapshot.json`) mas **não** está listado em `config["boards"]`
    (resíduo de board removido do `pipe.yml`) — também sem o campo.
- **Passos:**
  1. Persistir ambos os snapshots.
  2. Chamar `migrate_legacy_participation_intent(config)`.
  3. Recarregar o snapshot do board `task` e do board `removido`.
- **Resultado esperado:**
  - A entrada em `task` recebe `participation_intent == "origin"` (contada como
    presença em **um único** board configurado).
  - A entrada no board `removido` **não** é alterada (board não configurado não
    é iterado/gravado pela migração).

## CT-05 — Idempotência: segunda execução não altera nada

- **Critério:** CA2, "roda uma única vez por issue", idempotência
- **Tipo:** unitário
- **Pré-condição:** cenário misto com issues de CT-01 (`origin`), CT-02
  (`unresolved` em 2 boards) e CT-04 (board não configurado).
- **Passos:**
  1. Chamar `migrate_legacy_participation_intent(config)` (1ª vez).
  2. Capturar o conteúdo em bytes/JSON de cada `snapshot.json` afetado
     (ou o mtime, se preferir; mas comparação por conteúdo é mais robusta).
  3. Chamar `migrate_legacy_participation_intent(config)` (2ª vez).
  4. Recapturar o conteúdo de cada `snapshot.json`.
- **Resultado esperado:** o conteúdo dos snapshots após a 2ª chamada é
  **idêntico** ao capturado após a 1ª — a segunda chamada não altera nenhuma
  entrada já migrada (todos os campos já existem, logo nenhuma escrita). Idem
  para o board não configurado (permanece intocado).

## CT-06 — Salva apenas snapshots efetivamente alterados

- **Critério:** CA1/CA2 ("Salve apenas os snapshots que tiveram ao menos uma
  entrada alterada")
- **Tipo:** unitário
- **Pré-condição:** `config` com 2 boards configurados:
  - board `task`: issue legada `id == "500"` sem o campo (será alterada);
  - board `bug`: apenas issues **já** com `participation_intent` (nenhuma
    alteração devida).
- **Passos:**
  1. Persistir os snapshots.
  2. Espionar `Snapshot.save` (spy/monkeypatch) OU comparar mtime/conteúdo
     antes e depois por board.
  3. Chamar `migrate_legacy_participation_intent(config)`.
- **Resultado esperado:** `save()` é chamado (ou o arquivo muda) apenas para o
  board `task`; o snapshot de `bug` **não** é reescrito (nenhuma entrada
  alterada). Observação: este caso valida a otimização de escrita; se a
  implementação optar por salvar sempre, registrar como observação e reavaliar
  com o desenvolvedor (não é violação de CA-Story, mas contraria a instrução
  explícita do escopo).

## CT-07 — `board_full_sync` chama a migração após sincronizar snapshots e antes de retornar

- **Critério:** CA1, CA2, CA-Story (migração roda no full sync de startup,
  antes do primeiro `keep_task`)
- **Tipo:** integração (com `Board`/port fake + spy de ordem)
- **Pré-condição:**
  - `config` válido mínimo.
  - `board` (global de `src/__main__.py`) substituído por um fake cujo
    `sync_boards`, `board_ids`, `detect_board_changes` são no-ops observáveis
    (sem rede).
  - `migrate_legacy_participation_intent` substituída por um spy que registra
    o instante/ordem da chamada (ex.: `append` numa lista de eventos
    compartilhada; `sync_boards` e `detect_board_changes` também registram seus
    eventos na mesma lista).
- **Passos:**
  1. Chamar `board_full_sync(config)`.
  2. Inspecionar a lista de eventos registrada.
- **Resultado esperado:**
  - A migração é chamada **exatamente uma vez**.
  - A ordem registrada é: `sync_boards` → detecção de mudanças remotas
    (`detect_board_changes`) → `migrate_legacy_participation_intent` → retorno
    de `board_full_sync`. Ou seja, a migração ocorre **depois** do bloco que
    sincroniza a estrutura local e de `sync_boards`/detecção remota
    bem-sucedidos e **antes** do fim da função.
  - A migração recebe o `config` (não depende de rede).

---

## Observações

- **Aderência arquitetural (validada na etapa de execução):** a função deve
  residir no core (`src/core/sync.py` ou `src/core/participation_migration.py`)
  e **não** pode importar adapter nem `Board`/`BoardPort`; só pode tocar
  `Snapshot` e I/O local. Import de adapter no core = **bug crítico**
  (violação de camada).
- **Fora de escopo (não testar aqui):** política completa
  `origin`/`authorized`/`propagated` de criação/reconciliação; gate em
  `keep_task`; label `board-intent-<board_id>`; limpeza de resíduo
  materializado. Estes pertencem a outras tasks/stories do épico.
- **Distinção ausente vs `None`:** CT-03 é o caso-guarda que garante o uso de
  `"participation_intent" not in issue_dict` em vez de `.get(...)`. É o ponto
  de maior risco de regressão silenciosa.
- **Comando de verificação:**
  `python -m pytest tests/ -k "participation_intent or migration or full_sync" -v`
  e a suíte completa `python -m pytest` sem regressão (CA4).
