# Change File — Unificar a sincronização de boards em um único modelo

**Data:** 2026-10-01
**Issue:** #304 — Unificar a sincronização de boards em um único modelo que
sincroniza tudo
**Branch:** `feature/304-unificar-sincronizacao-boards` (cortada de `origin/main`)
**Versão:** 1.15.0

## Resumo

A descoberta remota (down) do motor tinha dois caminhos distintos:

- **Completo** (`Board.detect_board_changes`) — reconciliava o board inteiro
  (propriedades, dependências de bloqueio e poda por ausência), mas rodava só na
  inicialização e uma vez por dia de calendário (controlado por `last_full_sync`
  em `__main__`).
- **Reduzido/incremental** (`sync_remote`) — rodava a cada ciclo, já buscava o
  board inteiro e já fazia poda por ausência, porém usava `last_board_update`
  como corte para decidir **quais** issues reconciliar e emitia `change-down`
  com `fullsync=False`, deixando as dependências de bloqueio sem reconciliar na
  maioria dos itens.

Essa entrega consolida tudo em **um único caminho** (`sync_remote`) que, a cada
acionamento, reconcilia o board inteiro contra o estado local — sem corte por
data e sem acionamento diário separado —, e elimina do produto a existência de
dois modos: comportamento, código, logs e vocabulário.

## O que muda para quem opera/usa a esteira

- Um item novo no board passa a existir localmente **na sincronização
  seguinte**, sem esperar o antigo evento diário.
- Um item removido/arquivado no board é podado do estado local na sincronização
  seguinte.
- Dependências de bloqueio alteradas no board são reconciliadas em **toda**
  sincronização, não só na diária.
- Não há mais opção, nome, flag ou log que ofereça escolha entre "completo" e
  "reduzido/incremental" — resta apenas "sincronização".

## Alterações entregues

### `src/core/sync.py`

- `sync_remote` passa a ser o ponto de entrada único da descoberta remota: a
  cada acionamento reconcilia o board inteiro — `create-down` para novas,
  `change-down` **sempre `fullsync=True`** (propriedades **+** dependências de
  bloqueio) para divergentes (`updated_at` maior **ou** coluna diferente) e
  `delete-down` por ausência.
- Removido o uso de `last_board_update` como corte (`since`): a detecção não
  depende mais da data da última atualização.
- O fetch do board (`list_issues`) é a primeira operação; `PenaltyException`
  propaga antes de qualquer decisão de poda — uma leitura interrompida por
  limite de requisições nunca é interpretada como ausência de itens.
- Log de sincronização padronizado ao contrato mínimo:
  `sincronizacao board=<id> criados=<n> atualizados=<n> removidos=<n> resultado=<ok|limite|erro>`.

### `src/core/board.py`

- Removido `Board.detect_board_changes` (o antigo caminho "completo").
- Removido `list_issues_since` do `BoardPort` e do `Board`.

### `src/adapters/github_board.py`

- Removido `list_issues_since` do adapter GitHub.

### `src/__main__.py`

- Removido o ramo de acionamento diário (`last_full_sync`) do loop.
- A função de setup (estrutura local + primeira sincronização por board) foi
  renomeada de `board_full_sync` para `board_startup_sync`.

### `src/core/snapshot.py`

- Campo `last_board_update` descontinuado (property/setter removidos). Snapshots
  legados que ainda o contenham carregam sem erro — a chave é ignorada e
  removida na reescrita.

### `src/core/version.py`

- Bump `1.14.1` → `1.15.0` (minor; mudança de comportamento sem quebra de
  configuração).

### Documentação

- `CHANGELOG.md` — seção `[1.15.0]`.
- `README.md` — seção "Loop Principal" (`board_startup_sync`), callout
  "Sincronização única" e seção "Otimização de Sincronização"/`fullsync`
  atualizados para o modelo único.

### Testes

- Novos: `tests/test_sync_unico.py`, `tests/test_sync_unico_deps.py`,
  `tests/test_sync_unico_sem_segundo_modo.py`,
  `tests/test_sync_unico_nomenclatura.py`, `tests/test_snapshot_legacy.py`,
  `tests/test_sync_unico_log.py`.
- Migrados ao modelo único: `tests/test_incremental_absent_delete_down.py`,
  `tests/test_remedios_bloqueio.py`, `tests/test_sub_issue_propagation_fix.py`.
- Renomeação `board_full_sync` → `board_startup_sync` propagada nos helpers e
  testes afetados.

## Fora de escopo (mantido)

- Política de erros/retry/dead-letter da fila (`sync.max_attempts` intacto).
- Cache, nova paginação ou otimização de volume de requisições.
- Periodicidade do loop e teto de requisições para boards grandes (ponto de
  atenção para tratamento posterior).

## Verificação

- Testes do #304 (novos + migrados): **73 passed** na execução de testes
  (etapa QA, veredito APROVADO).
- Regressão geral: as 26 falhas remanescentes são **pré-existentes e
  ambientais** (singleton de log, ambiente Docker ausente, SHA/versão pinada),
  confirmadas no baseline limpo de `origin/main` — nenhuma regressão atribuível
  ao #304.
- Documentação de qualidade:
  [casos de teste](../quality/unificar-sincronizacao-boards/test-cases.md) e
  [resultados](../quality/unificar-sincronizacao-boards/test-results.md).

— Isabela Gomes - Tech Lead
