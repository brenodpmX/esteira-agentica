# Change #141 — Restaurar alterações indevidas no snapshot após execução do agente

- **Tipo:** funcionalidade (confiabilidade / integridade de estado)
- **Épico:** #104 (post-mortem do incidente #97 — parent recursivo)
- **Story:** #141 (US-04)
- **Task técnica:** #149 — "Verificação de integridade do snapshot na execução
  do agente" (C4)
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`
- **Implementação:** mergeada em `main`

## Problema

A proteção de `snapshot.json` era apenas declarativa: `PROTECTED_PATHS`
(`src/core/agent.py`) e o `CONTEXT.md` gerado instruíam o agente a não tocar
nos arquivos de estado interno, mas nada detectava nem revertia uma escrita
indevida caso ela ocorresse (bug do agente, comando de shell inesperado,
etc.).

## Mudanças implementadas

- **`SnapshotGuard`** (`src/core/snapshot.py`) — gerenciador de contexto que
  envolve a execução do agente por `board_id`:
  - Ao entrar, captura em memória existência, bytes completos e SHA-256 do
    `snapshot.json` do board.
  - Ao sair (sucesso, erro ou timeout — via `try/finally`), compara o estado
    atual ao capturado por conteúdo (nunca por tamanho ou timestamp
    isoladamente, cobrindo o caso de alteração com mesmo tamanho/mtime
    forjado).
  - Restaura alteração ou remoção indevida por escrita atômica (arquivo
    temporário no mesmo diretório + `os.replace`), preservando o modo do
    arquivo.
  - Remove arquivo criado indevidamente durante a execução (inexistente
    antes dela).
  - Cada violação gera exatamente um `log.warning` com `board_id` e hashes
    antes/depois, sem nunca expor o conteúdo dos bytes.
  - Se a própria restauração falhar (ex.: `OSError`), levanta
    `SnapshotIntegrityError`, identificando `board_id` e causa — não é
    engolida silenciosamente.
- **Integração em `call_agent`** (`src/__main__.py`) — a chamada
  `adapter.execute(params)` passou a ser envolvida pelo `SnapshotGuard` do
  `board_id` da issue em execução. A exceção original do agente (erro ou
  timeout) continua se propagando após a restauração; apenas uma falha da
  própria restauração é fatal e prevalece.
- **Encerramento fatal do processo em falha de restauração** — no loop
  principal (`main()`, bloco `while running`), `SnapshotIntegrityError` não é
  tratada como "erro no ciclo (não fatal)": propaga até finalizar o processo
  com mensagem de log fatal e acionável, antes de qualquer novo
  `board_full_sync`/`sync_remote_board`.

## Rastreabilidade (PRs)

- **#168** — `feature153`: implementação inicial do `SnapshotGuard`
  (captura, comparação, restauração atômica).
- **#169** — `feature154`: integração do `SnapshotGuard` ao `call_agent` e
  encerramento fatal do processo em falha de restauração.
- **#194** — `feature149`: correções de QA/Dev sobre a lacuna restante
  (preservação de modo do arquivo, ramos sem teste de falha em remoção,
  diretório removido). Regressão completa sem novas falhas introduzidas
  (baseline vs. branch do PR).

Todos os três PRs estão mergeados em `main` (via `epic`).

## Cobertura de testes

- `tests/test_snapshot_guard.py`
- `tests/test_snapshot_guard_call_agent.py`
- `tests/test_correcao4_validacao_pos_agente.py`

Critérios de aceite do body de #149 (captura/comparação por bytes, casos de
borda de tamanho/mtime idênticos, remoção/recriação, criação indevida, log
único sem expor bytes, propagação de erro sem mascarar, `SnapshotIntegrityError`
sem ser engolida, overhead em milissegundos, sem regressão) cobertos.

## Fora de escopo (mantido)

Extensão da mesma guarda a `changeQueue.json`, `throttle*.json` e
`sessions.json` — continuam protegidos apenas declarativamente até entrega
futura. Sandbox de filesystem não incluído.

## Estado de disponibilidade

Implementação já integrada em `main`. Este change file documenta, para a
etapa de Change File da story #141, as alterações entregues através das
tasks filhas #149 (e seu histórico de #153/#154, absorvidas no mesmo
encadeamento de PRs).
