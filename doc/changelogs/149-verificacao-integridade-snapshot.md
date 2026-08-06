# Change File — Verificação de integridade do snapshot na execução do agente

**Data:** 2026-08-06
**Issue:** #149 — Verificação de integridade do snapshot na execução do agente
**Branch:** `story149-149-verificacao_de_integridade_do_snapshot_na_execucao_do_agente`
**Épico:** #141 — Restaurar alterações indevidas no snapshot após execução do agente (US-04)
**Status:** entregue via tasks filhas #153 e #154 (mergeadas em `epic`)

## Resumo

Implementa a barreira de recuperação prevista em ADR-05: o `snapshot.json` de
cada board passa a ser capturado em memória antes de cada execução de agente
e restaurado atomicamente caso a execução (com sucesso, erro ou timeout) o
tenha alterado, criado ou removido indevidamente. Fecha o item 5 do escopo do
épico #104 ("Estado protegido").

A implementação foi dividida em duas tasks sequenciais, ambas já mergeadas em
`epic`:

- **#153** — `SnapshotGuard`/`SnapshotIntegrityError` em `src/core/snapshot.py`
  (PR #168).
- **#154** — integração da guarda em `call_agent` e encerramento fatal do
  processo em `src/__main__.py` (PR #169).

## Alterações entregues

### `src/core/snapshot.py`

- Nova classe `SnapshotGuard`, usada como context manager em torno da
  execução do adapter do agente:
  - Ao entrar, captura existência, bytes completos e hash SHA-256 do
    `snapshot.json` do `board_id` informado.
  - Ao saída (via `__exit__`, portanto cobrindo sucesso e exceção),
    compara o estado atual por conteúdo/hash — nunca por metadado de
    filesystem (mtime, tamanho).
  - Alteração ou remoção detectada → restaura os bytes capturados por
    escrita atômica (arquivo temporário no mesmo diretório + `os.replace`).
  - Criação indevida (arquivo não existia antes e passou a existir) →
    remove o arquivo.
  - Nenhuma diferença → nenhuma escrita é realizada.
  - Cada violação gera exatamente um `log.warning` com `board_id` e os
    hashes antes/depois — nunca o conteúdo dos bytes.
  - Se a própria restauração falhar (`OSError`), levanta
    `SnapshotIntegrityError(board_id, cause)`, nova exceção que identifica o
    board e a causa original; nunca é engolida silenciosamente.
  - Não faz chamadas de rede nem importa `Board`/adapters.

### `src/__main__.py`

- `call_agent`: a chamada `adapter.execute(params)` passa a ocorrer dentro de
  `with SnapshotGuard(board_id): ...`, cobrindo sucesso, erro (exceção
  relançada por `KiroCliAgent.execute`) e timeout, sem alterar o mecanismo de
  timeout existente.
- `main()` (loop `while running`): novo `except SnapshotIntegrityError`,
  posicionado antes do `except Exception` genérico, registra `log.error` com
  `board_id` e causa e relança a exceção — o processo encerra antes de
  qualquer novo `board_full_sync`/`sync_remote_board`, sem cair no tratamento
  de "erro no ciclo (não fatal)".

### Testes

- `tests/test_snapshot_guard.py` — captura, comparação por bytes/hash
  (incluindo alterações com mesmo tamanho e mtime forjado), restauração
  atômica de alteração/remoção, remoção de criação indevida, log de
  auditoria sem conteúdo, propagação de exceção original do bloco protegido,
  `SnapshotIntegrityError` em falha de restauração, overhead de milissegundos.
- `tests/test_snapshot_guard_call_agent.py` — integração com `call_agent`
  usando fake `AgentPort`: snapshot restaurado após execução normal e após
  exceção do adapter; `SnapshotIntegrityError` propagada por `call_agent` em
  falha de restauração; loop de `main()` não trata essa exceção como não
  fatal; `PenaltyException`/`KeyboardInterrupt` inalterados.
- Suíte completa validada em `epic` (checkout isolado): 28 testes relevantes
  (`test_snapshot_guard.py` + `test_snapshot_guard_call_agent.py`) passam, 1
  skip — sem regressão nos testes pré-existentes de `test_loop_guard.py`,
  `test_sync_optimization.py` e `test_sigterm_shutdown.py`.

## Fora de escopo (mantido)

Extensão da mesma guarda a `changeQueue.json`, `throttle*.json`,
`deadLetter.json` e `sessions.json`; sandbox de filesystem; qualquer mudança
no mecanismo de timeout do `KiroCliAgent`.

## Verificação de bloqueios do épico

Épico #141 está `blocked_by: #149` (esta story). #149, por sua vez, não tem
bloqueadores pendentes — suas tasks filhas #153 e #154 estão **CLOSED** no
GitHub e mergeadas em `epic` (PRs #168 e #169). Com a conclusão desta etapa,
não há bloqueios remanescentes entre #149 e o avanço do épico #141.

— Isabela Gomes - Tech Lead
