# Contexto e Decisões — Esteira Agêntica v2

Data: 2026-07-02

## Versionamento

A versão do projeto é definida em `src/core/version.py` (variável `VERSION`).
Segue semântico: `MAJOR.MINOR.PATCH`.

**Regra: toda alteração no código deve incrementar a versão antes do commit.**

- PATCH: correções de bugs, ajustes menores
- MINOR: funcionalidades novas, melhorias compatíveis
- MAJOR: mudanças incompatíveis (breaking changes)

A versão é exibida no log ao iniciar a esteira.

## Changelog

### Restauração das mudanças perdidas no merge `c27f813` (v1.9.0 — #181)

Recupera funcionalidade que existia apenas em `main` e foi descartada na
resolução de conflitos do merge `c27f813` (integração de `epic` em `main`). Os
dois lados do merge eram legítimos; o conflito foi resolvido adotando `epic` por
inteiro nos arquivos em disputa, sem reconciliar o que era exclusivo de `main`.

A `merge-base` das pontas era `26d863e`, muito anterior aos commits manuais de
`main` — por isso o three-way não tinha como preservá-los automaticamente.

- Bump: `1.8.3` → `1.9.0` (MINOR — retorno de comportamento ausente, sem
  breaking change; `pipe.yml` e schema inalterados)

**Perdas restauradas:**

| Origem | Perda | Gravidade |
|--------|-------|-----------|
| `28fea7e` | `boards.rerun_cooldown` sem efeito | alta — issue que falha reexecuta em loop apertado |
| `6176819` | `create-up` de body com slug em underscore | alta — falha silenciosa |
| `d8d85d9` | descoberta local presa à rotação de boards | média — inanição de boards de baixa prioridade |
| `3a1196a` | falha do kiro-cli logada como sucesso | média — diagnóstico cego |
| `7ed7bf0`/`45c8b14` | banner da locomotiva substituído | cosmética — mas foi o que revelou o incidente |

**Detalhamento:**

- **`boards.rerun_cooldown` voltou a funcionar** (`src/__main__.py`). A validação
  em `config.py` sobreviveu ao merge, mas o comportamento não: `pipe.yml` aceitava
  a chave sem erro e ela não tinha efeito nenhum. Restaurados `_rerun_cache`,
  `_cooldown_seconds`, `_in_rerun_cooldown`, `_mark_rerun`, `_purge_expired_rerun`
  e os pontos de chamada em `keep_task`.
- **`create-up` de slug em underscore** (`src/core/sync.py`). O merge reintroduziu
  a heurística `elif body_file.name.count("-") >= 2` em `detect_local_changes`.
  Como `_slugify` converte hífens e espaços em underscore, **todo** arquivo
  nomeado pelo próprio sistema tem exatamente um hífen (o de `-body`) e era
  descartado em silêncio — a issue criada localmente nunca subia ao board. Voltou
  a ser `else`: todo `*-body.md` sem prefixo numérico é issue local nova.
- **Descoberta local global** (`src/__main__.py`). Restaurados `detect_local_all`
  (varre todos os boards; barato, só filesystem) e `sync_remote_board` (um board,
  consome API do provider). `sync_board` permanece como wrapper de
  compatibilidade. Motivo: efeitos colaterais de agente são cross-board.
- **Detecção da falha real do kiro-cli** (`src/adapters/kiro_cli_agent.py`).
  Restaurados `_detect_failure` e `_last_meaningful_line`. O exit-code não reflete
  toda falha: erros de modelo/servidor voltam como texto com exit 0. A linha de
  **início** do log mantém o formato do `epic` (mais informativo, com `title`,
  `col_name` e path do log); as linhas de **conclusão/erro** recuperam a
  classificação e a causa real.
- **Banner da locomotiva** (`src/__main__.py`) restaurado byte a byte.
- **`AgentParams` saneado** (`src/core/agent.py`). O merge manteve campos dos dois
  lados, deixando `col_name` declarado duas vezes e `issue_title` sem consumidor.

**Testes:**

- Restaurados (deletados pelo merge): `tests/test_detect_local_all.py`,
  `tests/test_create_up_underscore_slug.py`.
- Novos: `tests/test_rerun_cooldown.py` (32), `tests/test_agent_failure_detection.py`,
  `tests/test_banner.py`.
- `tests/test_sigterm_shutdown.py` corrigido: amarrava o stop do loop em
  `sync_board` e, quando o loop deixou de chamá-lo, `main()` passou a rodar
  indefinidamente (o `except Exception` dorme e continua) — **travando** a suíte
  em vez de falhar. O stop passou a cobrir as três funções de descoberta.

Documentação: [change #181](doc/changes/181-restauracao-mudancas-perdidas-merge-c27f813.md)
e [changelog](doc/changelogs/181-restauracao-mudancas-perdidas-merge-c27f813.md).

### compose.dev.yml — estado/logs em bind mount no host (v1.8.3 — US-04)

Cria o override `compose.dev.yml` (previsto na US-04, até então inexistente — os
testes ficavam em `skip`). Substitui os named volumes de estado por bind mounts
configuráveis, dando acesso a logs/estado pelo host. Como o container roda como
uid 1000, os arquivos criados no host pertencem ao usuário de mesmo uid (não ao
root), ficando fáceis de inspecionar e apagar.

- Bump: `1.8.2` → `1.8.3` (PATCH — adição de override de dev, sem breaking change
  no compose base de produção)
- `compose.dev.yml`: `${PIPE_STATE_DIR:-./.pipe}:/app/.pipe`,
  `${PIPE_REPO_DIR:-./repo}:/app/repo`, `${PIPE_LOGS_DIR:-./logs}:/app/logs`;
  merge por destino substitui os named volumes do base; `init: true` herdado.
- Uso: `docker compose -f docker-compose.yml -f compose.dev.yml up` ou
  `COMPOSE_FILE=docker-compose.yml:compose.dev.yml` no `.env`.
- **Operação:** os diretórios do host (`.pipe`, `repo`, `logs`) devem existir com
  posse do usuário antes do `up` — se não existirem, o Docker os cria como root.
- Testes US-04 (`TestBindMountsEstado`, `TestDefaultsInline`) saíram do `skip`;
  `tests/test_docker_compose.py` passa 107/107.

### Fix: posse dos named volumes com usuário não-root (v1.8.2)

Correção de `PermissionError` no arranque em Docker: o container roda como `pipe`
(uid 1000), mas os mountpoints dos named volumes (`/app/logs`, `/app/.pipe`,
`/app/repo`, `/home/pipe/.kiro`) não existiam na imagem — o Docker os criava como
`root`, impedindo a escrita (ex.: `logs/<data>.json`).

- Bump: `1.8.1` → `1.8.2` (PATCH — correção de bug)
- `Dockerfile`: pré-cria esses diretórios como `pipe` (`mkdir -p` após `USER pipe`),
  para que cada volume — vazio na primeira criação — herde a posse `pipe:pipe`.
- **Operação:** volumes já criados com posse `root` precisam ser recriados
  (`docker compose down -v`) para a correção surtir efeito.

### Correções: get_board_ids + build Docker canônico (v1.8.1)

Bump PATCH consolidando correção de bug de arranque e ajustes no build Docker.

- Bump: `1.8.0` → `1.8.1` (PATCH — correção de bug + ajustes de build)
- **Fix `get_board_ids`** (`src/__main__.py`): passou a ignorar chaves escalares
  dentro de `boards` (ex.: `rerun_cooldown`) via `isinstance(cfg, dict)`,
  corrigindo `AttributeError: 'int' object has no attribute 'get'` no arranque.
  Alinha o comportamento com `board.board_ids` e a validação de `config.py`.
- **`docker-compose.yml`**: `build` na forma longa com `build.secrets: [ssh_key]`,
  para que `docker compose build` injete a chave SSH como secret de build (usado
  pelo `git clone` da última camada do Dockerfile). Alinha com o runbook.
- **`docker/versions.env` + `Dockerfile`**: pins atualizados para desbloquear o
  build — `gh 2.96.0 → 2.97.0` e `kiro-cli 2.13.1 → 2.18.0` (SHA-256 repinado).
  Build canônico validado ponta a ponta (`docker build` completo). A fragilidade
  recorrente desses pins ficou registrada em **Pendências**.

### Preflight de Credenciais (v1.6.0 — US-02)

Adição de comportamento novo: verificação de credenciais antes do startup
principal (preflight). Implementado nas tasks #34 (kiro_cli_agent) e #35
(startup), consolidado nesta task #36 com o bump MINOR correspondente.

- Bump: `1.5.0` → `1.6.0` (MINOR — adição de comportamento, sem breaking change)
- Funcionalidade: `preflight()` verifica SSH, GitHub CLI e permissões do repo
  antes de qualquer operação destrutiva
- Referências: ADR-04, `doc/arch/rodar-no-docker/us-02-autenticacao-headless.md`

## Visão Geral

Esteira automatizada de agentes de IA com arquitetura hexagonal. Reescrita do projeto `oldversion/` para suportar múltiplas plataformas de board (GitHub Projects, ClickUp, etc) e múltiplos adapters de agente (kiro-cli, etc).

## Arquitetura Hexagonal

```
src/
├── core/               # Domínio - regras de negócio
│   ├── log.py          # Logging dual (terminal resumo + arquivo detalhe)
│   ├── config.py       # Validação do pipe.yml + contexts
│   ├── agent.py        # AgentPort + AgentParams + build_prompt
│   ├── board.py        # Board core + BoardPort + ChangeItem + SyncEvent
│   ├── commands.py     # Comandos @--- no body (IssueCommands, parse/serialize)
│   ├── change_queue.py # Fila persistente de sincronismo (at-least-once)
│   ├── snapshot.py     # Snapshot por board
│   ├── session.py      # Índice de sessões do agente (.pipe/sessions.json)
│   └── sync.py         # Sincronização local ↔ board (detect + apply)
├── adapters/           # Implementações de ports
│   ├── github_board.py # Adapter para GitHub Projects V2
│   └── kiro_cli_agent.py # Adapter para execução via kiro-cli
└── __main__.py         # Orquestração
```

### Ports e Adapters

- **BoardPort** — interface abstrata para operações de board
- **Board** — core que usa o port para operações
- **AgentPort** — interface abstrata para execução de agentes
- **KiroCliAgent** — adapter que executa via kiro-cli

## Fluxo Principal

```
main()
├── check_config()         # Valida pipe.yml, SSH, contexts
├── startup()              # Configura SSH, clona repos, limpa fila anterior
├── board_full_sync()      # Sync completo
│   ├── Cria .pipe/boards/<board_id>/<col_id>/
│   ├── Sincroniza snapshot local (mapa de colunas)
│   ├── sync_boards() remoto (com retry de penalty)
│   ├── Recupera issues com status pendente (crash recovery)
│   └── detect_board_changes() por board
│
└── while running:
    ├── board_full_sync()          # Re-executa se mudou o dia (daily full sync)
    ├── detect_local_all() → bool  # Descoberta local (up) em TODOS os boards
    ├── sync_remote_board() → bool # Descoberta remota (down) no board atual
    ├── process_queue()            # Aplica a fila global de mudanças
    ├── keep_task() → task | AUTO_ADVANCED | None
    ├── call_agent()               # Resolve adapter, build_prompt, executa
    └── sleep_time()               # Dorme se !had_changes AND task==None
```

> **Descoberta desacoplada:** a detecção local (`up`) é **global** — roda em
> todos os boards a cada ciclo, pois um agente atuando em um board pode criar
> artefatos (ex.: issue bloqueante) em outro. O sync remoto (`down`) permanece
> **por board**, na rotação priorizada, por ser o lado caro (API do provider,
> sujeito a rate limit). `had_changes = local (qualquer board) OR remoto (board atual)`.

### sleep_time

Controle de ociosidade condicional:
- Se a descoberta não movimentou nada (`detect_local_all()` + `sync_remote_board()` → `False`) **E** `keep_task()` retornou `None` (nenhuma tarefa elegível) → dorme `config["sleep"]` segundos.
- Se houve qualquer atividade → prossegue imediatamente.

O campo `sleep` é obrigatório no `pipe.yml` (número > 0, em segundos).

## Sincronização

### Eventos (SyncEvent)

| Evento | Direção | Significado |
|--------|---------|-------------|
| `create-up` | local → board | Issue criada localmente |
| `create-down` | board → local | Issue criada no board |
| `change-up` | local → board | Issue modificada localmente |
| `change-down` | board → local | Issue modificada no board |
| `delete-up` | local → board | Issue deletada localmente |
| `delete-down` | board → local | Issue deletada no board |

### Regra de conflito

Quando há `change-up` e `change-down` simultâneos, o **board (remoto) vence**. O `detect_local_changes` não enfileira `change-up` se a issue já está com status `change-down`.

### Detecção de mudanças remotas

Gatilhos para `change-down`:
- `updated_at` no board > `updated_at` no snapshot
- Coluna no board ≠ coluna no snapshot

### Fila de mudanças (ChangeQueue)

- Modelo at-least-once: `getNext()` espia sem remover, `remove(uuid)` confirma
- Persistida em `.pipe/changeQueue.json`
- Deduplicação por `event + id + identifier + board`
- Limpa no startup (issues com status pendente são re-enfileiradas do snapshot)

#### Flag `fullsync`

Cada `ChangeItem` tem um booleano `fullsync` (default `False`):
- `fullsync=True` → reconcilia **todas** as propriedades + dependências
  (blocked_by/blocks, que só existem via REST). Usado em todo create, no
  full sync diário e na **recuperação de pendências no startup** (toda
  mudança detectada/recuperada em `board_full_sync` sobe como fullsync).
- `fullsync=False` → apenas a chamada única de propriedades (sem deps). Usado
  em `change-down` incremental.
- **Upgrade (superset)**: se um item equivalente já está na fila sem fullsync
  e um novo full chega, o existente é promovido a `fullsync=True` (não
  duplica). `same_target` ignora `fullsync` na deduplicação.

## Otimização de Sincronização (v1.3.0)

Objetivo: minimizar chamadas ao GitHub por issue. Duas estratégias combinadas.

### Down — chamada única enriquecida

`get_issue(board_id, issue_id, fullsync=False)` traz, numa **única query
GraphQL**: title, body, state, updatedAt, labels, parent, children (subIssues),
coluna (Status) e isArchived (via `projectItems`). As dependências
(blocked_by/blocks) **não existem no GraphQL** (só REST) e só são buscadas
quando `fullsync=True` (2 chamadas REST via `_get_dependencies`).

Em cada evento down, o estado real do board é gravado no snapshot
(`_write_state_from_issue`). Sem fullsync, `blocked_by`/`blocks` são
**preservados** do snapshot (não vêm na chamada única) para não apagar o bloco
`@---` de deps ao reescrever o `-body.md`. A coluna também vem do `get_issue`,
eliminando o `list_issues` (paginação completa) que era feito antes.

### Up — comparar antes de escrever

`Board.apply_commands(board_id, issue_id, cmds, known=None)` compara o estado
desejado (comandos do arquivo) contra o estado conhecido (`known`, do
snapshot) e **só chama o setter do atributo que realmente mudou**. Os setters
(`set_parent/children/blocked_by/blocks`) recebem `known_current`, evitando os
GETs internos de leitura-antes-de-escrita. Retorna deltas
`{rel: {added, removed}}` das relações para o gatilho recíproco.

Sem `known` (reconciliação completa), comporta-se como antes (chama todos os
setters, que descobrem o estado atual sozinhos).

### Gatilho de par recíproco (dependências)

Relações são bidirecionais no GitHub:

| Relação em X | Par recíproco em Y |
|--------------|--------------------|
| `X.parent = Y` | `Y.children ∋ X` |
| `X.children ∋ Y` | `Y.parent = X` |
| `X.blocked_by ∋ Y` | `Y.blocks ∋ X` |
| `X.blocks ∋ Y` | `Y.blocked_by ∋ X` |

Ao detectar relação **adicionada/removida** em X (up ou down),
`_trigger_reciprocal_downs` enfileira um `change-down fullsync` do alvo Y
**apenas se o snapshot de Y estiver inconsistente** com o par recíproco:
- adicionada: enfileira se Y **ainda não** reciproca X;
- removida: enfileira se Y **ainda** reciproca X.

Essa checagem de par (`_reciprocates`) é a **condição de parada**: quando o
alvo já está coerente, nada é enfileirado — evitando reação em cadeia infinita.
O estado desejado/real é sempre gravado no snapshot **antes** de disparar o
gatilho. Alvos não rastreados no snapshot são ignorados.

### Resolução automática de bloqueios (blocked_by/blocks)

Uma issue com `/blocked_by` ou `/blocks` no body é tratada como bloqueada por
`keep_task` (não avança). Como o GitHub **mantém a dependência mesmo com a
issue bloqueadora fechada** e **remover a dependência não altera o
`updated_at`** da issue (logo não é detectada como `change-down`), três
mecanismos garantem que bloqueios obsoletos sejam limpos:

1. **Ao arquivar** (`/archive` no body **ou** coluna de destino com
   `on_in:[archive]`): antes de arquivar, `_apply_change_up` **zera**
   `blocked_by`/`blocks` da issue. A remoção gera deltas que disparam o
   gatilho recíproco → cada issue vinculada recebe um `change-down fullsync` e
   reconcilia seu estado (desbloqueando-se).

2. **Ao deletar** (`delete-up` **ou** `delete-down`):
   `_cleanup_block_relations_on_delete` percorre as issues apontadas pela
   deletada (via `blocks`/`blocked_by`), remove o vínculo recíproco no board
   (`set_blocked_by`/`set_blocks`), atualiza o snapshot do alvo e enfileira um
   `change-down fullsync` para ele.

3. **Na inicialização**: toda mudança detectada/recuperada em
   `board_full_sync` é `fullsync=True`, reconciliando as dependências (ver
   flag `fullsync`).

### Throttle

Toda requisição respeita o throttle. `_get_rate_limit_info` chama
`self._throttle()` diretamente (não pode rotear por `_gh`, pois é invocado de
dentro de `_handle_rate_limit`, que já roda dentro de `_gh`/`_gql` — causaria
recursão). As demais chamadas `subprocess.run` ficam dentro de `_gh`/`_gql`,
sempre após `_throttle()`.

Escala do valor (segundos): `0, 1, 2, 4, ... 64`.
- **Aumento** (`_throttle_hit`, secondary rate limit): dobra até o teto `64`;
  se estiver em `0`, sobe para `1`. Em `64` e ainda falhando → `penalty`.
- **Redução** (`_throttle`, cooldown de 1h sem problemas): divide por 2; ao
  chegar em `1`, cai para `0` (sem espera). Em `0` permanece `0`.
- `_load_throttle` só restaura o valor persistido quando ele é **maior** que o
  atual (não rebaixa após reinício).

### Detecção de rate limit por transporte (não pelo corpo)

`_handle_rate_limit` decide **exclusivamente** por sinais de transporte:

- `headers["__status__"]` (linha de status HTTP parseada em `_parse_headers`)
  igual a `403`/`429`;
- `stderr` do `gh` mencionando "rate limit";
- `_graphql_rate_limited(output)`, que parseia o JSON e olha apenas
  `data.errors[].type` (`RATE_LIMITED`/`FORBIDDEN`) — a seção estruturada de
  erros da API.

O corpo (`output`/stdout) **nunca** é escaneado por substring. Regressão
corrigida: a versão anterior fazia `combined = f"{output} {error}"` e buscava
"rate limit" no corpo. Uma issue cujo título/body continha "Rate Limit" (ex.:
issue de análise de custo de API) fazia toda `list_issues` (HTTP 200,
`remaining` ~5000) ser classificada como *secondary rate limit*, escalando
throttle até 64s e ativando penalty por horas sem nenhum limite real.
Cobertura em `tests/test_rate_limit_detection.py`.

## Seleção de Tarefas (keep_task)

- Boards ordenados por prioridade (menor = mais prioritário)
- Dentro do board, varredura coluna a coluna: da última coluna para a primeira (`backlog`/`todo` por último)
- Dentro de cada coluna, seleciona a mais antiga elegível (`created_at` / `updated_at`)
- Retorno tri-estado:
  - `dict` → tarefa elegível para execução imediata (`call_agent`)
  - `AUTO_ADVANCED` → nenhuma tarefa pronta, mas uma issue do `todo` foi avançada; o loop **mantém o board atual** e força uma nova descoberta (`detect_local_all` + `sync_remote_board`) + `process_queue` (não avança de board nem reinicia em 0)
  - `None` → nada a fazer neste board; o loop avança para o próximo
- Auto-advance: coluna `todo` → próxima coluna; só dispara se nenhuma coluna posterior tiver tarefa elegível. Move os 3 arquivos, atualiza o snapshot (marca `status=change-up`, `body_path` na nova coluna, `column` permanece a de origem) e **enfileira o `change-up`** na ChangeQueue para o sync propagar ao board
- `parallel: false` → bloqueia auto-advance se issue ativa fora de terminais
- Elegível: `status == "ok"` + coluna com `agent` + coluna com `change.advance`
- Bloqueada: `/need_human` ou `/blocked_by` no body (bloqueios obsoletos são
  limpos automaticamente ao arquivar/deletar — ver *Resolução automática de
  bloqueios*)

## Execução de Agentes

### gitevents

| Valor | Blocos no prompt |
|-------|------------------|
| `create` | Git Setup (criar branch) + Commit & Push + Cleanup |
| `use` | Git Setup (checkout existente) + Commit & Push + Cleanup |
| `merge` | Git Setup (checkout existente) + Commit & Push + PR + Cleanup |
| `create-merge` | Git Setup (criar) + Commit & Push + PR + Cleanup |
| `no-branch` | Nenhum bloco de git |

### Substituição de agente por nível (`override-agent`)

A coluna tem um `agent` default. O nível de execução de uma issue é armazenado
como label `agent-level-<nível>` no GitHub (ex.: `agent-level-low`,
`agent-level-medium`, `agent-level-high`). Essa label é sincronizada
nativamente pelo board, eliminando a dependência de estado local.

Se a issue possuir uma label `agent-level-<nível>` e `<nível>` for chave de
`override-agent`, usa o agente do valor; senão, o `agent` default. Como cada
agente carrega o próprio `model`, a troca de agente também troca o model.

Resolvido em `agent.py` (`agent_level` lê `issue["labels"]` diretamente +
`resolve_agent_id`), validado em `config.py`.

No fluxo do planning-poker, o agente escreve `/agent_level <nível>` no bloco
`@---` do body. O sync-up chama `all_labels()` (em `commands.py`), que emite
`agent-level-<nível>` no conjunto de labels efetivas, gravando a label no board
via `apply_commands`. A label `agent-level-*` é tratada como campo especial
(análogo a `need_human`): extraída em `from_issue`, reemitida em `all_labels`,
nunca sobrescrita pelo comando `/labels` do usuário.

Migração de issues legadas: o `board_full_sync` chama
`migrate_agent_level_labels` (em `sync.py`) que, para cada issue com
`/agent_level` no body mas sem label `agent-level-*` no snapshot, enfileira um
`change-up` para que o sync-up grave a label no board.

### Contexto do agente

Cada agente tem um arquivo em `contexts/<plataforma>/<agente>.md` que é enviado
como contexto na execução. Validado no `check_config` (deve existir e não
estar vazio).

O contexto é entregue **concatenado no início do input** do `kiro-cli chat`
(via `_compose_input`: `contexto + "---" + prompt`), não via `--agent`. A
execução usa o `~/.kiro` padrão do kiro-cli — não há `KIRO_HOME` isolado nem
geração de configs de agente nativos.

### Sessão do agente (continuidade entre execuções)

Módulo `src/core/session.py` (`SessionIndex`), índice em `.pipe/sessions.json`.

Objetivo: preservar o raciocínio do agente entre execuções da mesma issue —
quando um agente pausa (ex.: `need_human`/`blocked_by`) e retoma depois, ele
continua de onde parou em vez de recomeçar do zero.

- **Chave por agente**: `<board>/<issue>/<agente>`. O mesmo agente atuando em
  colunas diferentes retoma o próprio raciocínio; agentes distintos nunca
  herdam a sessão um do outro. O agente da chave é o **resolvido**
  (`resolve_agent_id`, considera override por `/agent_level`).
- **Retomar**: antes de executar, se há `session_id` conhecido e ele **ainda
  existe** no kiro-cli (`--list-sessions` do cwd), passa `--resume-id <id>`.
- **Capturar**: após executar, pega o id da sessão mais recente do cwd
  (topo de `--list-sessions`) e grava no índice. Cobre a primeira execução e o
  caso de sessão descartada pelo kiro (que vira sessão nova). O loop é
  sequencial, então a sessão do topo é seguramente a desta execução.
- **Ciclo de vida**: a esteira **não** gerencia as sessões do kiro-cli (não
  apaga, não limpa) — apenas aponta enquanto existirem. Se o `--resume-id`
  referencia uma sessão inexistente, o kiro cria uma nova silenciosamente (sem
  erro) e o índice é atualizado.

Detalhes técnicos verificados no kiro-cli:
- Sessões ficam em `~/.kiro/sessions/cli/{uuid}.json/.jsonl`; o índice é um
  SQLite global (`~/.local/share/kiro-cli/`), **keyed por cwd**. Como cada repo
  tem seu cwd (`repo/<repo_id>`), `--list-sessions` só enxerga as sessões
  daquele repo — pipes diferentes não colidem.
- O `session_id` **não** aparece no stdout headless; só é obtido via
  `--list-sessions`.
- `.pipe/sessions.json` sobrevive a reinícios (o `startup` só limpa a fila de
  mudanças, não o índice de sessões).

### Log de execução

Gerado em `<log.dir>/<issue_id>/<timestamp>.md` com 3 seções:
- **Parâmetros**: plataforma, agente, model, agent_level, board, coluna, issue, context
- **Prompt**: prompt completo montado por `build_prompt`
- **Chat**: diálogo (preenchido durante execução)

Em caso de erro, o log registra o erro na seção Chat antes de propagar a exceção.

## Configuração (pipe.yml)

```yaml
sleep: 60

log:
  dir: logs
  ttl: 10
  level: INFO

git:
  repo:
    <id>: <url-ssh>
  flow:
    base: main
    <id-flow>:
      prefix: <prefix>/
      create: <branch-origem>
      merge: <branch-destino>

agents:
  <id-platform>:
    <id-agent>:
      name: <nome>
      model: <modelo>

boards:
  platform: github
  <id-board>:
    name: <nome>
    todo: <coluna-inicial>
    priority: <n>
    flow: <id-flow>
    parallel: true|false
    columns:
      <id-column>:
        name: <nome>
        agent: <id-agent>
        override-agent: {<nível>: <id-agent>}
        gitevents: create|use|merge|create-merge|no-branch
        prompt: <objetivo da etapa>
        archive: true|false
        on_in: [<token>, ...]
        on_out: [<token>, ...]
        change:
          advance: <id-column>
          <condition>: <id-column>
```

## Arquivos por Issue

| Arquivo | Função |
|---------|--------|
| `<id>-<slug>-body.md` | `# Título\n\n<body>` — leitura e escrita |
| `<id>-<slug>-history.md` | Histórico de comentários — somente leitura |
| `<id>-<slug>-addcomment.md` | Escrever aqui → vira comentário na issue |

### Formato do history

```markdown
## <autor> - <yyyy-MM-dd HH:mm:ss>

<texto do comentário>
---
```

## Comandos no body (`@---`)

Módulo `src/core/commands.py`. O body de uma issue pode terminar com um bloco
de comandos separado por uma linha `@---`.

- `IssueCommands`: dataclass com parent, children[], blocked_by[], blocks[],
  labels[], agent_level, close, archive, need_human.
- `split_body(raw)` → `(body_limpo, IssueCommands)`. Múltiplos `@---`: o último
  vence, anteriores removidos.
- `compose_body(body, cmds)` → body completo com bloco.
- `from_issue(issue)` → IssueCommands (extrai `need_human` e `agent_level` das labels; ambos tratados como campos especiais — não aparecem em `cmds.labels`).
- `annotations_doc()` → documentação compartilhada por prompts e contexts.

Filosofia presença/ausência: o estado escrito é o estado final (SET). Sem
comandos de "remover".

### Fluxo

- **Down** (`_compose_down_body` em sync.py): escreve `# título\n\n{body_limpo}`
  + bloco `@---` reconstruído do estado real da issue (relações via `get_issue`,
  labels, need_human). Limpa qualquer `@---` pré-existente no body remoto.
- **Up** (`_apply_create_up` / `_apply_change_up`): `split_body` separa o body
  limpo (enviado ao board) dos comandos, que são aplicados via
  `Board.apply_commands` (set_labels com all_labels, set_parent, set_children,
  set_blocked_by, set_blocks, archive/unarchive, close).

### Adapter GitHub

- Sub-issues (parent/children): REST `/issues/{n}/sub_issues` (usa
  `fullDatabaseId` no corpo, number no path), `replace_parent=true`.
- Dependências (blocked_by/blocks): REST `/issues/{n}/dependencies/blocked_by`
  e `/blocking`. `set_blocks` escreve no lado blocked_by de cada alvo.
- Labels: PUT `/issues/{n}/labels` (SET); add/remove unitário via POST/DELETE.
- Arquivamento: GraphQL `archiveProjectV2Item` / `unarchiveProjectV2Item`.
- `need_human` é label comum no GitHub, tratada em campo próprio no domínio.

## Proteção contra propagação de sub-issues entre boards (v1.6.1)

O GitHub Projects V2 possui um efeito colateral ao registrar relações de
sub-issue: ao executar `POST /repos/{owner}/{repo}/issues/{parent}/sub_issues`,
o filho pode ser propagado para todos os projects do parent sem valor no campo
`Status`. Antes da v1.6.1, o sync interpretava esse item sem coluna como uma
issue nova no board e materializava arquivos locais duplicados.

A correção usa defesa em profundidade:

1. **Primitiva da porta:** `BoardPort.remove_from_board` e
   `Board.remove_from_board` expõem a remoção de item do project. O adapter
   GitHub resolve o item e executa a mutation `deleteProjectV2Item`.
2. **Pós-hook do vínculo:** `_add_sub_issue` recebe o board de origem e chama
   `_remove_propagated_items_without_status`. Dados de Projects V2 (inclusive
   `Status`) só existem no GraphQL — não há endpoint REST equivalente —, então o
   pós-hook consulta `projectItems`/`fieldValues` no mesmo padrão de `get_issue`
   e `_belongs_to_board` e remove por `deleteProjectV2Item` usando o
   `project_id`/`item_id` retornados pela própria query. Ignora o project
   informado e remove somente itens de **outros** projects com `Status` vazio; um
   item com coluna definida é considerado intencional e é preservado. Se o
   project informado não puder ser resolvido, nada é removido (sem a exclusão
   garantida, o item de origem entraria na lista de candidatos).
   Assimetria deliberada: `set_parent` informa o board do filho (o item
   propagado, que aparece no project do pai, é removido aqui), enquanto
   `set_children` informa o board do pai — nesse caminho o item propagado está
   justamente no project excluído e a limpeza fica com o guard do `create-down`,
   que possui a prova de presença no snapshot.
3. **Guard no `create-down`:** `_apply_create_down` só descarta um item sem
   coluna quando há **prova** de propagação automática: a própria issue já
   registrada em outro board **configurado** no `pipe.yml`, com coluna conhecida
   naquele board. `parent` isolado é apenas contexto de log — uma sub-issue nova
   e legítima do board atual também pode chegar sem coluna, e removê-la seria
   perda de dado. Snapshots de diretórios fora da configuração não contam como
   prova (`_find_snapshot_issue` aceita um filtro opcional de boards). A remoção
   precisa concluir antes do descarte: falha propaga e a fila reprocessa,
   preservando a garantia *at-least-once*.
4. **Reconciliação:** `detect_board_changes` considera `Status` vazio diferente
   da coluna conhecida. `_apply_change_down` reaplica no board a coluna do
   snapshot antes de decidir sobre os arquivos locais — se dependesse da
   movimentação local, o caso comum (arquivo já na coluna certa) deixaria o item
   remoto sem `Status` e a divergência voltaria em todo full sync. Movimentação
   remota legítima não escreve de volta no board. Issues realmente novas, sem
   prova de presença em outro board, continuam usando a primeira coluna
   configurada como fallback local, e `create_issue` também aplica fallback para
   a primeira opção do project (com warning) quando a coluna pedida não existe —
   antes o `Status` era pulado em silêncio, criando a própria "issue sem coluna".

O discriminador crítico é a ausência de `Status`: a correção não remove
sub-issues legitimamente mantidas em múltiplos boards quando cada item possui
coluna própria. Resíduos já materializados antes da v1.6.1 não são limpos
automaticamente e exigem operação manual com a esteira parada.

Cobertura de regressão: `tests/test_sub_issue_propagation_fix.py` exercita a
implementação real (sem substituir o método sob teste por fake) — pós-hook em
GraphQL com `_gh`/`_api` proibidos, preservação do project de origem e de itens
com `Status`, fail-safe de project não resolvido, fallback de `create_issue`,
prova exigida pelo guard do `create-down`, falha de remoção que não consome o
evento, reconciliação do `change-down` e detecção de coluna vazia.

## Eventos de coluna (`on_in` / `on_out`)

Cada coluna pode declarar `on_in` e `on_out` (listas). Em uma mudança de
coluna, dispara o `on_out` da origem e o `on_in` do destino.

Tokens: `close`, `open` (reopen + unarchive), `archive`, `-archive`,
`need_human`, `-need_human`, `<label>` (add), `-<label>` (remove).

Validação em `config.py`: `on_in`/`on_out` devem ser listas se presentes.

### Movimentação local (change-up)

`_apply_change_up` → `_fire_column_events` aplica os eventos diretamente no
board via `Board.apply_column_events`.

### Movimentação manual no board (change-down)

Quando o usuário move a issue manualmente no GitHub, o `_apply_change_down`
detecta a mudança de coluna e, **após salvar o snapshot** (com o `body_mtime`
já registrado), chama `_bake_column_events`: reescreve o arquivo `-body.md`
aplicando `on_out`/`on_in` no bloco `@---` (via `apply_events_to_commands`).

O snapshot **não é alterado** nesse momento. Como a reescrita deixa o arquivo
mais novo que o `body_mtime` salvo, o próximo `sync` detecta modificação local
e dispara um `change-up`, que sobe os status/labels resultantes para o board.
Isso garante que tags e status fiquem sempre sincronizados, mesmo em
movimentações manuais.

## Snapshot por Board

`.pipe/boards/<board_id>/snapshot.json`:
```json
{
  "board": {"<col_id>": "<col_name>"},
  "issues": [
    {
      "id": "1", "column": "...", "body_path": "...", "body_mtime": "...",
      "updated_at": "...", "status": "ok",
      "labels": [], "parent": null, "children": [],
      "blocked_by": [], "blocks": [], "archived": false, "state": "open"
    }
  ],
  "last_sync": null,
  "last_board_update": "..."
}
```

Os campos de estado (`labels`, `parent`, `children`, `blocked_by`, `blocks`,
`archived`, `state`) guardam o **estado conhecido** da issue, usado para o diff
no fluxo up e para a checagem de par recíproco. São gravados em todo evento
up (estado desejado) e down (estado real do board). `status` é o campo de
sincronismo (crash recovery), distinto de `state` (open/closed da issue).

## Post mortem: sub-issues propagadas entre boards (documentação v1.6.1 — #99)

O GitHub Projects V2 propaga uma sub-issue para os projects do parent quando o
vínculo hierárquico é criado, mas esses itens podem nascer sem `Status`. O core
atual interpreta um `create-down` sem coluna como issue nova e pode materializar
uma cópia local no board errado.

A primeira tentativa de correção (issue #98, PR #103, commit `01f9e83`) foi
homologada com 208 testes aprovados, mas cancelada pela decisão do débito
#110, que definiu #88/PR #102 como veículo único da correção — o PR #103 foi
fechado sem merge. A implementação efetivamente entregue é a do #106/PR #102
(commit `a00ba7c`), com cinco camadas: `remove_from_board` via
`deleteProjectV2Item`, pós-hook de limpeza pós-vínculo
(`_remove_propagated_items_without_status`, via GraphQL real), guard no
`create-down` com prova de propagação, fallback de coluna e reconciliação de
coluna vazia. A suíte terminou com 221 testes aprovados e 3 ignorados, sem
`monkeypatch` do código sob teste. Essa correção está integrada a esta branch.

### Regra de acesso à API de GitHub Projects V2

Operações sobre projects, `projectItems`, campos de project e remoção de item
devem usar GraphQL via `self._gql`. REST via `self._gh` fica restrito às APIs
tradicionais de issues e pull requests. Um endpoint REST de `projectitems` foi
inventado na primeira tentativa de correção (PR #102 original, reprovada em
code review sob #106) e passou pelos mocks; qualquer exceção a essa regra
exige validação contra a documentação oficial e teste de integração gated.

O registro completo, os fatores de reincidência e as ações preventivas estão em
`doc/incidente/sub-issues-propagadas/ticket.md`. O conteúdo funcional planejado
e o estado de integração estão em
`doc/changes/98-sub-issues-propagadas-entre-boards.md`; a entrega documental
v1.6.1 está em `doc/changelogs/99-post_mortem_sub_issues_propagadas.md`.

## Robustez e Segurança do Estado (v1.5.0 — Incidente "Issue Fantasma")

Pacote de correções derivado do incidente "Issue Fantasma" (registro completo
em `doc/incidente/issue-fantasma/ticket.md`). O incidente teve causa raiz
tripla: (1) agente com escrita irrestrita ao estado interno; (2) prefixo
numérico no nome de arquivo interpretado como ID de issue real; (3) ausência de
tratamento para "issue inexistente" combinada com fila *at-least-once*. As
issues reais #1, #2, #3 (épicos) foram fechadas indevidamente por colisão de
número no espaço compartilhado de IDs do repositório.

Quatro correções foram entregues nesta release. A Correção 4 (validação
pós-agente por comparação de mtime) **não** foi implementada.

### Correção 2 — CONTEXT.md gerado no startup (`context_generator.py`)

`generate_context(config)` roda em `startup()` (`src/__main__.py`) e gera dois
arquivos a partir do `pipe.yml`:

- `.pipe/CONTEXT.md` — instruções em Markdown.
- `.kiro/agents/pipe_context.json` — agente kiro-cli (`tools: ["*"]`,
  `allowedTools: ["@builtin"]`) com o mesmo conteúdo no campo `prompt`.

Regeneração: recria se o arquivo não existir OU se `pipe.yml.mtime >
CONTEXT.md.mtime`. O conteúdo tem quatro blocos: restrições de sistema (arquivos
protegidos), regras de nomeação de issue (`<slug>-body.md` sem prefixo
numérico), tabela de boards/colunas e git flow/branches.

Injeção: o adapter `kiro_cli_agent.py` passa `--agent pipe_context` (nunca
inline no prompt) e exporta `KIRO_HOME=<esteira>/.kiro` para o kiro-cli localizar
o agente gerado (o cwd do processo é `repo/<repo_id>`, então sem `KIRO_HOME` o
kiro-cli buscaria agentes no diretório errado).

> Distinto do `CONTEXT.md` da raiz (este arquivo, técnico e manual). O gerado
> fica em `.pipe/` e é sobrescrito a cada restart.

### Correção 1 — Estado interno read-only para o agente (`agent.py`)

`PROTECTED_PATHS` (glob) centraliza os arquivos de estado interno:
`.pipe/boards/*/snapshot.json`, `.pipe/changeQueue.json`, `.pipe/throttle.json`,
`.pipe/throttle-*.json`. `build_prompt` chama `_assert_no_protected(prompt)`,
que tokeniza o prompt e casa cada token contra os padrões (fnmatch + match de
sufixo para paths absolutos). Se algum padrão aparecer, levanta `ValueError` —
o path do snapshot nunca chega ao agente. O `CONTEXT.md` gerado reforça a regra
em linguagem natural.

### Correção 3 — Tratamento de erro irrecuperável no sync (`sync.py`)

`_apply_change_up` e `_apply_delete_up` capturam a exceção cujo texto contém
`Could not resolve to an issue or pull request` (issue inexistente no GitHub):
logam warning `removendo do snapshot (issue fantasma)`, removem a entrada do
snapshot e **retornam** (descartam o evento) em vez de propagá-lo. Sem esse
tratamento, a fila *at-least-once* re-enfileirava o evento a cada ciclo
(loop na v1.4.2; crash-loop na base atual, sem o `except Exception` amplo).
Qualquer outra exceção continua propagando.

### Correção 5 — Isolamento de IDs entre boards (`github_board.py`)

Antes de `update_issue` e `close_issue`, `_assert_belongs_to_board` chama
`_belongs_to_board`, que consulta via GraphQL os `projectItems` da issue e
confirma que o `project_id` do board alvo está entre eles. Se não pertencer, a
operação é abortada com warning `não pertence a este board — operação abortada`
e o método retorna sem efeito. Custo: +1 chamada GraphQL por operação
destrutiva (dentro da quota de 5000 pontos/hora).

## Pendências

- [ ] Implementar adapter ClickUp
- [ ] **Fragilidade dos pins Docker — tratar na próxima intervenção nas
  configurações Docker.** O `gh` é instalado do canal `stable` do repo APT, que
  serve **apenas a última versão** publicada; e o `kiro-cli` é baixado de uma URL
  `/latest/` com `KIRO_CLI_SHA256` pinado. Como consequência, a cada novo release
  upstream o build canônico quebra (`gh=X.Y.Z was not found` ou
  `sha256 did NOT match`), exigindo bump manual em `docker/versions.env` + o
  `Dockerfile`. Em 2026-08-14 foram repinados `gh 2.96.0 → 2.97.0` e
  `kiro-cli 2.13.1 → 2.18.0` só para desbloquear. Avaliar como resolver de forma
  durável: usar o `gh` empacotado no Debian (`2.46.0-3`, estável no `trixie`) e/ou
  uma URL versionada do kiro-cli (em vez de `/latest/`), fixando também o digest da
  imagem base.

## Distribuição Docker (v1.6.0; build canônico revisado em v1.8.1)

O build canônico usa `Dockerfile` e `docker-compose.yml` na raiz. O `kiro-cli`
**não** é copiado do host: ele é baixado no build a partir de `KIRO_CLI_URL`
(versão em `docker/versions.env`, validada por `KIRO_CLI_SHA256`). O `gh` é
instalado via APT na versão pinada (`GH_VERSION`), e o código-fonte é clonado no
build (última camada) usando a chave SSH como **secret do BuildKit** — a chave
nunca persiste em nenhuma camada da imagem. A imagem roda como usuário não-root
`pipe` (uid 1000). `prepare-docker.sh` é legado do modelo antigo (COPY do host) e
não faz parte do build canônico.

Credenciais e configuração entram via `.env` (`env_file`): `GH_TOKEN` e
`KIRO_API_KEY` como variáveis, e a chave SSH como Docker secret alimentado por
`SSH_KEY_FILE_HOST` (caminho absoluto no host), montada em `/run/secrets/ssh_key`
— `PIPE_SSH_KEY_FILE` é fixado pelo compose nesse caminho. O `pipe.yml` e os
`contexts/` entram como bind read-only. O estado é persistido nos volumes
`pipe-state`, `pipe-repo`, `pipe-logs`, `kiro-home` e `kiro-local`.

`docker compose build` ativa o BuildKit e passa o secret de build via
`build.secrets` (ver v1.8.1). A operação usa `PYTHONUNBUFFERED=1` para logs em
tempo real, `init: true` para repassar sinais e handler de `SIGTERM` para
shutdown limpo. O serviço usa `restart: unless-stopped`. A arquitetura, limitações
e evidências de homologação estão em
`doc/architecture/rodar-no-docker/arquitetura.md`; o guia operacional está no
`README.md` e no `doc/runbook/docker.md`.


## Fluxo de Integração: Feature → Epic → Main (Débito #165)

**Correção em: v1.8.0 — #165. Estado: Implementado.**

### Problema Original

O fluxo de integração de branches estava incompleto:
- Features (`feature/*`) eram mergeadas em `epic` via PR.
- PRs eram marcadas como "closed" no board quando o merge em `epic` era feito.
- A branch `epic` **nunca era mergeada em `main`**, deixando funcionalidade completada "offline".

Consequências:
- Testes e planejamento subsequentes operavam sobre `main` que **não tinha** o código "fechado".
- Dependências entre tasks (Planning Poker #148 depends-on #146 e #147) partiam de premissa falsa: código estava apenas em `epic`, não em `main`.
- Risco composto: cada PR adicional em `epic` aumentava o diff a resolver.

### Solução

1. **Merge de `epic` em `main` (#165)**
   - Merge realizado em dois estágios: commit `c27f813` (merge inicial de 133
     commits com resolução de 8 conflitos conforme arquitetura Docker não-root)
     e merge complementar dos commits pós-merge (v1.8.1, v1.8.2, v1.8.3, PR #178).
   - Todos os commits de `epic` são agora ancestrais de `main`.
   - ⚠️ **Perda colateral, corrigida em v1.9.0 (#181):** a resolução dos
     conflitos adotou o lado `epic` por inteiro em `src/__main__.py`,
     `src/core/agent.py`, `src/core/sync.py`, `src/adapters/kiro_cli_agent.py` e
     `tests/`, descartando trabalho que existia **apenas** em `main`
     (`rerun_cooldown`, `create-up` de slug em underscore, descoberta local
     global, detecção de falha do kiro-cli, banner). Os commits perdidos
     permaneciam ancestrais de `main` — logo `git log` e `--is-ancestor` não
     denunciavam nada — mas seu **conteúdo** havia sido revertido pela árvore do
     merge. Ver o changelog da v1.9.0.

   **Lição para merges futuros de branch longa:** commit ancestral não garante
   conteúdo presente. Após integrar uma branch com `merge-base` antiga, verificar
   cada arquivo em conflito com `git diff <parent-main> <merge> -- <arquivo>` e
   confirmar que nenhum hunk reverte trabalho exclusivo do lado `main`.

2. **Fluxo Corrigido (permanente)**
   - Feature branches (`feature/*`) continuam apontando para origem definida em `pipe.yml`.
   - Padrão esperado (conforme `README.md`):
     - Para flows de integração simples: `feature/* → main` direto (gitevents: `create-merge`).
     - Para flows multi-tier (se necessário): `feature/* → epic → main` (gitevents: `create-merge` em ambos os estágios, com base diferente).
   - **Regra crítica**: Toda branch de integração intermediária (ex.: `epic`) deve ser **explicitamente mergeada em `main`** antes de ser considerada completa.

3. **Salvaguardas**
   - Validação em `config.py` pode ser estendida (sugestão da Camila Rocha, TC-04):
     verificar que toda cadeia `flow → ... → base` termina em `main`.
   - Testes de regressão em `tests/test_epic_merge_ausente_146_147.py` (TC-04)
     validam que nenhuma cadeia de flow fica "presa" sem alcançar `base`.

### Validação Pós-Merge

```bash
# Critério 1: Ancestralidade
git merge-base --is-ancestor 498674b main  # is ancestor ✓
git merge-base --is-ancestor 9572409 main  # is ancestor ✓

# Critério 2: Sem divergência material de código
git diff main epic -- src/                 # sem diffs relevantes

# Critério 3: Testes passam
python -m pytest tests/ -q

# Critério 4: Documentação disponível
grep -i "epic\|fluxo de branch" CONTEXT.md  # Seção presente
```

### Referências

- **Débito**: Issue #165
- **Issues Desbloqueadas**: #148 (Planning Poker pode retomar)
- **Commits Críticos**:
  - `498674b` — Resolução determinística do body da issue (#146)
  - `9572409` — Detecção de arquivos órfãos (#147)
  - `c27f813` — Merge inicial (débito #165)
