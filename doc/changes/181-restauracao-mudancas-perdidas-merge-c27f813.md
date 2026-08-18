# Change #181 — Restauração das mudanças perdidas no merge `c27f813`

- **Tipo:** correção de regressão (perda de código em merge)
- **Versão-alvo:** 1.9.0
- **Branch:** `fix/restaurar-mudancas-perdidas-merge-c27f813`
- **Base:** `origin/main` em `e106af3`
- **Compatibilidade:** sem mudança de schema; `boards.rerun_cooldown` volta a
  ter efeito (a validação já existia, o comportamento não)

## Problema

O merge `c27f813` ("Merge: integrar epic em main", 12/08/2026 22:24) integrou a
branch `epic` em `main`. Os dois lados eram legítimos:

- **Parent 1 — `45c8b14`** (`main`): commits manuais com `rerun_cooldown`,
  banner ASCII da locomotiva, descoberta local global e refactor dos logs de
  agente.
- **Parent 2 — `87037f9`** (`epic`): refatoração ampla (`SnapshotGuard`,
  `AgentGuard`, `preflight`, `migrate_agent_level_labels`, `agent_level` por
  label, criação atômica de branch).

A `merge-base` das duas pontas é `26d863e` — bem anterior aos commits manuais.
Na resolução de conflitos de `src/__main__.py`, `src/core/agent.py`,
`src/adapters/kiro_cli_agent.py` e `tests/`, o lado `epic` foi adotado por
inteiro, descartando o trabalho que existia apenas em `main`.

### Commits de `main` cujo conteúdo foi perdido

| Commit | Assunto | Perda |
|--------|---------|-------|
| `7ed7bf0` | `style(banner)` | banner substituído |
| `45c8b14` | `corrigindo a locomotiva` | banner substituído |
| `28fea7e` | `feat(keep-task): boards.rerun_cooldown` | comportamento removido |
| `d8d85d9` | `feat(loop): descoberta local global` | revertido para acoplado |
| `2ea665e` | `refactor(agent-logs)` | logs de agente empobrecidos |
| `3a1196a` | `fix(agent-logs): erro real do kiro-cli` | detecção de falha removida |
| `6176819` | `test(sync): create-up slug underscore` | teste deletado |

### Efeito colateral do conflito mal resolvido

`AgentParams` (`src/core/agent.py`) ficou com `col_name` declarado **duas
vezes** e com `issue_title` órfão (nenhum consumidor). Funciona por acidente da
semântica de `__annotations__` em dataclass, mas é código morto e armadilha.

## Objetivo

Estado final em que **todas** as mudanças — as manuais de `main` e as da branch
`epic` — coexistem e funcionam. Nenhum dos dois lados é descartado; onde havia
conflito real, as duas intenções são reconciliadas.

## Plano de execução

Cada passo é um commit isolado, verificado antes de seguir para o próximo.

### P1 — Sanear `AgentParams` (pré-requisito)

Remover `issue_title` e a declaração duplicada de `col_name`. Campos finais
para log de terminal: `col_name: str = ""` e `title: str = ""`.

- Arquivo: `src/core/agent.py`
- Verificação: `grep` por `issue_title` em `src/` e `tests/`; suíte de
  `test_agent*`.

### P2 — Restaurar o log rico de execução do agente

Reintroduzir `_detect_failure` e `_last_meaningful_line` em
`src/adapters/kiro_cli_agent.py`, **reconciliando** com o formato do `epic`
(que já traz `title`, `col_name` e o caminho do log).

Resultado desejado:
- início: `[board] #id "título" @ coluna agent='nome' log='caminho'`
- sucesso: `execução concluída: <última linha significativa>`
- falha: `falhou: <erro real do kiro-cli>` em nível `error`

Não voltar ao formato antigo de `main` — o do `epic` é mais informativo. O que
`main` tinha de único é a **detecção da falha real**, e é isso que retorna.

- Arquivos: `src/adapters/kiro_cli_agent.py`
- Verificação: `tests/test_agent_log_descritivo.py` e suíte de agente.

### P3 — Restaurar o cooldown de reexecução (`boards.rerun_cooldown`)

Reintroduzir em `src/__main__.py`: `_rerun_cache`, `_cooldown_seconds`,
`_in_rerun_cooldown`, `_mark_rerun`, `_purge_expired_rerun`, e os respectivos
pontos de chamada em `keep_task`.

Já presentes e intactos (não mexer):
- validação em `src/core/config.py` (`rerun_cooldown` inteiro `>= 0`);
- guards `isinstance(cfg, dict)` em `src/core/board.py` e em `get_board_ids`.

- Arquivos: `src/__main__.py`
- Verificação: teste novo de cooldown (skip por cooldown, elegibilidade
  imediata ao trocar de coluna, purga de expirados, `cooldown<=0` esvazia).

### P4 — Restaurar a descoberta local global por ciclo

Reintroduzir `detect_local_all(config)` (varre **todos** os boards) e
`sync_remote_board(board_id)` (apenas o board da rotação), mantendo
`sync_board` como wrapper de compatibilidade. O loop principal volta a usar as
duas fases separadas.

Motivo original: efeitos colaterais de agente são cross-board — uma execução em
um board pode criar artefatos em outro; presa à rotação, a descoberta atrasaria
indefinidamente boards de baixa prioridade.

- Arquivos: `src/__main__.py`
- Verificação: restaurar `tests/test_detect_local_all.py`.

### P5 — Restaurar o banner da locomotiva

Repor o `_BANNER` de `45c8b14`.

- Arquivos: `src/__main__.py`
- Verificação: teste que garante o banner e impede regressão silenciosa.

### P6 — Restaurar os testes deletados

- `tests/test_detect_local_all.py` (de `d8d85d9`)
- `tests/test_create_up_underscore_slug.py` (de `6176819`)

Ambos precisam ser reavaliados contra o `src/core/sync.py` atual, que o `epic`
alterou substancialmente (+524 linhas). Se um teste falhar por mudança
**legítima** de contrato do `epic`, o teste é adaptado ao novo contrato — nunca
o contrário.

### P7 — `test_sigterm_shutdown.py`: sem ação

O `epic` reescreveu o arquivo e removeu a cobertura de `PYTHONUNBUFFERED` e
`init: true`, mas ela foi **relocada** para `tests/test_dockerfile.py` e
`tests/test_docker_compose.py`. Verificado: não há perda de cobertura.

### P8 — Versão e documentação

- `src/core/version.py`: `1.8.3` → `1.9.0` (restauração de comportamento
  ausente de `main`, sem quebra de compatibilidade).
- `CONTEXT.md`: registrar o incidente de merge e o estado reconciliado.
- `README.md`: confirmar a documentação de `rerun_cooldown` e da descoberta
  desacoplada.
- `doc/changelogs/`: entrada da versão.

### P9 — Verificação final e MR

- Suíte completa comparada ao baseline.
- Merge request para `main`.

## Baseline de testes (antes das mudanças)

```
4 failed, 1015 passed, 10 skipped, 1 xfailed, 13 errors
```

Todas as falhas e erros são **ambientais**, não de código:

- `tests/test_docker_compose.py` (4 falhas): `docker compose config` exige o
  arquivo `.env`, que não é versionado.
- `tests/test_dockerfile.py` (13 erros): testes de integração que exigem a
  imagem Docker construída.

O critério de aceite é: nenhuma falha nova além dessas, e os testes novos
passando.

## Registro de execução

| Passo | Estado | Commit | Observações |
|-------|--------|--------|-------------|
| P1 | pendente | — | |
| P2 | pendente | — | |
| P3 | pendente | — | |
| P4 | pendente | — | |
| P5 | pendente | — | |
| P6 | pendente | — | |
| P7 | concluído | — | sem ação: cobertura relocada, verificada |
| P8 | pendente | — | |
| P9 | pendente | — | |
