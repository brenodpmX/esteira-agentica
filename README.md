# Esteira Agêntica

Esteira automatizada de agentes de IA com arquitetura hexagonal.

## Requisitos

- Python 3.12+
- Git
- GitHub CLI (`gh`) autenticado
- Chave SSH configurada no GitHub

## Instalação

```bash
pip install pyyaml
```

## Configuração

### 1. Variável de ambiente SSH

```bash
export PIPE_SSH_KEY_FILE=~/.ssh/id_ed25519
```

### 2. Arquivo pipe.yml

```yaml
sleep: 60

log:
  dir: logs
  ttl: 10
  level: INFO

git:
  repo:
    main: git@github.com:user/repo.git
  flow:
    base: main
    feature:
      prefix: feature/
      create: main
      merge: main

agents:
  kiro-cli:
    dev:
      name: engineering
      model: claude-sonnet-4.5

boards:
  platform: github
  rerun_cooldown: 300   # opcional: tempo mínimo (segundos) para reexecutar a
                        # mesma issue (mesmo board + coluna + id). 0/ausente
                        # desabilita. Se a issue muda de coluna, fica elegível
                        # imediatamente.
  backlog:
    name: Backlog
    priority: 0
    flow: feature
    columns:
      todo:
        name: To Do
      doing:
        name: Doing
        agent: dev
        gitevents: create
        target-prompt: Execute a tarefa
        change:
          advance: done
      done:
        name: Done
        archive: true
```

### 3. Contextos de agentes

Cada agente precisa de um arquivo de contexto em `contexts/<plataforma>/<agente>.md`.
Ao executar, o sistema cria arquivos vazios automaticamente e exige preenchimento.

## Uso

### Execução local (Python)

```bash
python -m src
```

### Execução via Docker Compose (recomendado para produção)

A distribuição Docker executa o loop da esteira sem prompts no container;
intervenções de negócio continuam sendo feitas no board do GitHub e são
capturadas pelo sincronismo seguinte. O passo a passo detalhado (verificação de
saúde e gestão do container) está em
[`doc/runbook/docker.md`](doc/runbook/docker.md).

**Pré-requisitos no host:**
- Docker Engine com Docker Compose V2 (`docker compose`);
- chave SSH registrada no GitHub (usada como Docker secret no build e no runtime);
- token do GitHub com escopos `repo` e `project`;
- API key do Kiro (plano Pro/Pro+ ou superior), gerada em
  https://app.kiro.dev → **API Keys**.

O `kiro-cli` **não** precisa estar instalado no host: o build o baixa na versão
pinada em `docker/versions.env` (validada por SHA-256). O login local do `gh`
também não é necessário — a autenticação usa `GH_TOKEN`.

**1. Configurar credenciais:**

```bash
cp .env.example .env
```

Preencha no `.env`:

```env
GH_TOKEN=ghp_seu_token
KIRO_API_KEY=kiro_sua_api_key
SSH_KEY_FILE_HOST=/caminho/absoluto/para/id_ed25519   # alimenta o Docker secret
```

`PIPE_SSH_KEY_FILE` é fixado pelo compose como `/run/secrets/ssh_key` — não o
defina no `.env`. Use caminho **absoluto** em `SSH_KEY_FILE_HOST` (o compose não
expande `~` em `secrets.file`). Não versione o `.env`. Para rotacionar a API key,
atualize `KIRO_API_KEY` e recrie o serviço com
`docker compose up -d --force-recreate`.

**2. Criar a configuração da esteira:**

Crie `pipe.yml` na raiz (ele não é versionado) usando o exemplo da seção
[Configuração](#configuração). Preencha também os contextos requeridos em
`contexts/<plataforma>/<agente>.md`; o startup cria arquivos ausentes, mas exige
conteúdo antes de executar os agentes.

**3. Construir e iniciar:**

```bash
docker compose build
docker compose up -d
docker compose logs -f
```

O `docker compose build` ativa o BuildKit e injeta a chave SSH como **secret de
build** (`build.secrets`) para o `git clone` do código na última camada do
Dockerfile; a chave nunca persiste em nenhuma camada da imagem. Os logs são
emitidos em tempo real (`PYTHONUNBUFFERED=1`). O Compose usa um processo init e a
aplicação trata `SIGTERM`, portanto `down`/`stop` encerram o loop de forma limpa,
sem aguardar `SIGKILL` (issue #70).

**4. Parar ou reiniciar:**

```bash
docker compose down       # preserva os volumes
docker compose up -d      # reutiliza estado, clones e logs
docker compose down -v    # remove também todo o estado persistido
```

O serviço usa `restart: unless-stopped`, reiniciando após crash ou reboot do
host, mas permanecendo parado após uma interrupção explícita.

**Volumes persistidos entre reinícios:**

| Volume | Caminho no container | Conteúdo |
|--------|---------------------|----------|
| `pipe-state` | `/app/.pipe` | Snapshots, fila de mudanças e índice de sessões |
| `pipe-repo` | `/app/repo` | Clones dos repositórios Git |
| `pipe-logs` | `/app/logs` | Logs da esteira e das execuções de agentes |
| `kiro-home` | `/home/pipe/.kiro` | Configuração do kiro-cli |
| `kiro-local` | `/home/pipe/.local/share/kiro-cli` | Dados locais do kiro-cli |

Por padrão o estado fica em **named volumes** (geridos pelo Docker, em
`/var/lib/docker/volumes/`). Para ter logs e estado **acessíveis no host** — e
com posse do seu usuário, não do root — use o override `compose.dev.yml`, que
troca esses volumes por bind mounts configuráveis:

```bash
docker compose -f docker-compose.yml -f compose.dev.yml up -d
```

Para que o `docker compose up` normal já use os dois arquivos, defina no `.env`:

```env
COMPOSE_FILE=docker-compose.yml:compose.dev.yml
```

Os caminhos no host são configuráveis (`PIPE_STATE_DIR`, `PIPE_REPO_DIR`,
`PIPE_LOGS_DIR`; padrão `./.pipe`, `./repo`, `./logs`). Crie os diretórios com o
seu usuário antes do `up` (`mkdir -p .pipe repo logs`) — se não existirem, o
Docker os cria como root.

### Solução de problemas do Docker

| Sintoma | Verificação / correção |
|---------|------------------------|
| Build falha ao instalar `gh` (`Version 'X.Y.Z' for 'gh' was not found`) | O repo APT do `gh` serve apenas a última versão; atualize `GH_VERSION` em `docker/versions.env` e o `Dockerfile`. |
| Build falha no kiro-cli (`sha256 … did NOT match`) | A URL `/latest/` mudou de build; atualize `KIRO_CLI_VERSION`/`KIRO_CLI_SHA256` em `docker/versions.env` e no `Dockerfile`. |
| Falha de autenticação do agente | Confirme `KIRO_API_KEY` no `.env` e recrie o serviço. |
| Falha de API/projeto do GitHub | Confirme os escopos `repo` e `project` de `GH_TOKEN`. |
| Falha ao clonar via SSH | Confirme `SSH_KEY_FILE_HOST` (caminho absoluto) e o cadastro da chave no GitHub. |
| Configuração ou contexto inválido | Consulte `docker compose logs`; o startup encerra com mensagem explícita. |

> A imagem é construída para Linux `amd64`: o Dockerfile baixa o GitHub CLI e o
> Kiro CLI (binário nativo glibc `x86_64`) para essa arquitetura.

## Estrutura

```
src/
├── core/                   # Domínio
│   ├── log.py              # Logging dual (terminal + arquivo)
│   ├── config.py           # Validação do pipe.yml
│   ├── agent.py            # AgentPort + build_prompt + PROTECTED_PATHS
│   ├── context_generator.py # Gera CONTEXT.md + agente pipe_context no startup
│   ├── board.py            # Board core + BoardPort + ChangeItem
│   ├── commands.py         # Comandos @--- no body (parse/serialize)
│   ├── change_queue.py     # Fila persistente de sincronismo
│   ├── snapshot.py         # Snapshot por board
│   ├── session.py          # Índice de sessões do agente
│   └── sync.py             # Sincronização local ↔ board
├── adapters/               # Implementações
│   ├── github_board.py     # Adapter para GitHub Projects V2
│   └── kiro_cli_agent.py   # Adapter para execução via kiro-cli
└── __main__.py             # Entrada principal (orquestração)

.pipe/boards/<id>/          # Diretórios de boards e snapshots
.pipe/sessions.json         # Índice (board/issue/agente) → session_id
.pipe/CONTEXT.md            # Contexto do sistema gerado no startup (protegido)
.kiro/agents/pipe_context.json  # Agente kiro-cli gerado com o contexto do sistema
contexts/<platform>/<agent>.md  # Contextos dos agentes
repo/                       # Repositórios clonados
logs/                       # Logs diários (JSON) + logs de agente (MD)
pipe.yml                    # Configuração
```

## Loop Principal

```
main()
├── check_config()         # Valida pipe.yml, SSH, contexts
├── startup()              # Configura SSH, gera CONTEXT.md, clona repos
├── board_full_sync()      # Sync completo (estrutura + mudanças remotas)
│
└── while running:
    ├── board_full_sync()   # Re-executa se mudou o dia (daily full sync)
    ├── detect_local_all()  # Descoberta local (up) em TODOS os boards → bool
    ├── sync_remote_board() # Descoberta remota (down) no board atual → bool
    ├── process_queue()     # Aplica a fila global de mudanças
    ├── keep_task()         # Seleciona próxima tarefa → task | AUTO_ADVANCED | None
    ├── call_agent()        # Executa agente com prompt construído
    └── sleep_time()        # Intervalo entre ciclos (condicional)
```

> **Descoberta desacoplada:** a detecção local (`up`) roda em **todos** os
> boards a cada ciclo — barata (varredura de filesystem) e necessária porque um
> agente atuando em um board pode criar artefatos (ex.: issue bloqueante) em
> outro. Já o sync remoto (`down`) permanece **por board**, na rotação
> priorizada, por consumir API do provider (sujeito a rate limit).

### sleep_time (controle de ociosidade)

Ativado apenas quando **ambas** as condições são verdadeiras:
- a descoberta não movimentou nada (`detect_local_all()` e `sync_remote_board()` retornaram `False`)
- `keep_task()` retornou `None` (nenhuma tarefa elegível)

Quando ativado, dorme pelo tempo definido em `sleep` no `pipe.yml` (em segundos).
Se houve qualquer atividade (sync movimentou algo OU existe tarefa para executar), o loop prossegue imediatamente sem pausa.

## Seleção de Tarefas (keep_task)

- Boards ordenados por prioridade (menor = mais prioritário)
- Dentro do board, varre coluna a coluna da última para a primeira (`backlog`/`todo` por último)
- Dentro de cada coluna, pega a issue elegível mais antiga (por data)
- Retorno tri-estado: `task` (executa), `AUTO_ADVANCED` (avançou uma issue do `todo`; loop mantém o board e força novo sync), `None` (nada a fazer; loop avança de board)
- Auto-advance de coluna `todo` para próxima coluna (só ocorre se nenhuma coluna posterior tiver tarefa pronta); move os arquivos, atualiza o snapshot e enfileira o `change-up` para o sync propagar ao board
- `parallel: false` → bloqueia auto-advance se já existe issue ativa
- Issues com `/need_human` ou `/blocked_by` no body são ignoradas
- Issues reexecutadas há menos de `boards.rerun_cooldown` segundos são puladas
  (ver abaixo)

### Cooldown de reexecução (`boards.rerun_cooldown`)

Impede que a mesma issue seja reentregue ao agente em loop apertado quando falha
repetidamente. Sem isso, uma issue que não avança consome quota do modelo a cada
ciclo sem progresso.

- Cache interno em memória: `(board, coluna, id)` → instante da última entrega.
- A chave **inclui a coluna** de propósito: se a issue avança no board, é
  trabalho novo e fica elegível imediatamente, sem esperar o cooldown.
- Entradas expiradas são purgadas a cada acionamento do `keep_task`, para o cache
  não crescer indefinidamente com issues que saíram do board.
- `0` ou ausente desabilita e esvazia o cache.

O cooldown é por processo (não persiste entre reinícios): reiniciar a esteira
libera todas as issues imediatamente.

> **Atenção ao atualizar de 1.8.x:** nas versões 1.8.0–1.8.3 essa chave era
> validada mas **não tinha efeito** (regressão do merge `c27f813`, corrigida na
> 1.9.0). Se o seu `pipe.yml` já a declara, o comportamento muda ao atualizar.
> Para manter o comportamento anterior, remova a chave ou defina `0`.

### Resolução automática de bloqueios

Uma issue com `/blocked_by`/`/blocks` no body não avança. Como o GitHub mantém
a dependência mesmo com a bloqueadora fechada — e removê-la no board não altera
o `updated_at` (logo não vira `change-down`) —, bloqueios obsoletos são limpos
automaticamente em três situações:

1. **Ao arquivar** (`/archive` no body ou coluna com `on_in:[archive]`): os
   bloqueios da issue são removidos antes de arquivar, e cada issue vinculada
   recebe um `change-down fullsync` para reconciliar (desbloquear).
2. **Ao deletar** (up ou down): as issues apontadas pela deletada têm o vínculo
   de bloqueio removido no board e recebem `change-down fullsync`.
3. **Na inicialização**: toda mudança detectada/recuperada sobe como fullsync,
   reconciliando as dependências.

## Execução de Agentes

### gitevents (controle de branches)

| Valor | Comportamento |
|-------|--------------|
| `create` | Cria branch a partir da origem |
| `use` | Usa branch existente |
| `merge` | Usa branch existente + cria PR |
| `create-merge` | Cria branch + cria PR |
| `no-branch` | Sem operações de git |

### Substituição de agente por nível (`override-agent`)

Cada coluna define um agente default no atributo `agent`. O nível de execução
de uma issue é armazenado como label `agent-level-<nível>` no GitHub (ex.:
`agent-level-low`, `agent-level-medium`, `agent-level-high`). Essa label é
sincronizada nativamente pelo board, garantindo que o nível persista entre
ciclos de sync.

Se a issue possuir uma label `agent-level-<nível>` e esse `<nível>` for uma
chave do mapa `override-agent` da coluna, a esteira usa o agente indicado no
valor. Caso contrário, usa o `agent` default.

No fluxo do planning-poker, o agente escreve `/agent_level <nível>` no bloco
`@---` do body. O sync-up lê esse campo via `all_labels()` e grava a label
`agent-level-<nível>` no GitHub automaticamente. A resolução de agente em
`resolve_agent_id()` lê diretamente `issue["labels"]` — sem dependência de
arquivo local.

Como cada agente carrega o próprio `model`, trocar o agente por nível troca
também o model efetivo da execução.

```yaml
columns:
  desenvolvimento:
    agent: engineering          # default
    override-agent:
      low: generic              # agent-level-low  -> generic
      high: senior-engineering  # agent-level-high -> senior-engineering
```

Validação (`config.py`): `override-agent` deve ser um mapa `<nível>: <agente>`,
a coluna precisa ter um `agent` default, e todo agente referenciado deve existir
em `agents`.

### Log de execução

Cada execução gera um arquivo em `logs/<issue_id>/<timestamp>.md` com:
- **Parâmetros**: plataforma, agente, model, agent_level, board, coluna, issue
- **Prompt**: prompt completo enviado ao agente
- **Chat**: diálogo da execução (preenchido pelo adapter)

### Continuidade de sessão

A esteira mantém a continuidade do raciocínio do agente entre execuções da
mesma issue. Quando um agente pausa (ex.: `/need_human` ou `/blocked_by`) e a
tarefa retorna depois, ele retoma de onde parou em vez de recomeçar.

- Índice em `.pipe/sessions.json` mapeia `<board>/<issue>/<agente>` →
  `session_id` do kiro-cli (chave **por agente**: agentes distintos não herdam
  a sessão um do outro; o mesmo agente reusado retoma o próprio raciocínio).
- Antes de executar, se a sessão ainda existir, retoma via `--resume-id`.
- Após executar, captura o id da sessão (mais recente do cwd) e atualiza o
  índice.
- A esteira **não** gerencia o ciclo de vida das sessões do kiro-cli — apenas
  aponta enquanto existirem. Sessão inexistente vira sessão nova sem erro.

### Contexto do sistema (`CONTEXT.md` gerado no startup)

No startup, a esteira gera automaticamente um contexto de sistema a partir do
`pipe.yml` e o injeta em toda execução de agente. O objetivo é dar ao agente
instruções explícitas derivadas da configuração real, em vez de deixá-lo
inferir comportamento (origem do incidente "Issue Fantasma").

- `generate_context(config)` (em `src/core/context_generator.py`) roda no
  `startup()` e escreve dois arquivos:
  - `.pipe/CONTEXT.md` — instruções em Markdown.
  - `.kiro/agents/pipe_context.json` — arquivo de agente do kiro-cli com o
    mesmo conteúdo.
- O conteúdo é injetado via `--agent pipe_context` (argumento de CLI), **nunca
  embutido inline no prompt**. O adapter usa `KIRO_HOME` apontando para o
  `.kiro` da esteira para que o kiro-cli encontre o agente gerado.
- **Regeneração:** recria se o arquivo não existir OU se o `pipe.yml` for mais
  novo que o `CONTEXT.md`. Caso contrário, mantém o arquivo atual.

O `CONTEXT.md` gerado contém quatro blocos derivados do `pipe.yml`:

1. **Restrições de sistema** — lista de arquivos de estado interno que o agente
   nunca deve ler ou escrever (ver "Proteção de estado interno" abaixo).
2. **Criação de issues** — obriga o padrão `<slug>-body.md` **sem prefixo
   numérico**. O ID real é atribuído pelo GitHub no sync; antes disso o arquivo
   não tem (e não deve ter) prefixo numérico. Foi justamente o prefixo numérico
   inventado pelo agente que disparou o incidente "Issue Fantasma".
3. **Boards e colunas** — tabela de boards/colunas/agentes configurados.
4. **Git flow e branches** — prefixos de branch por flow e branch base.

> **Atenção:** o `.pipe/CONTEXT.md` gerado é diferente do `CONTEXT.md` da raiz
> do projeto (documentação técnica escrita à mão). O arquivo gerado é protegido
> e **não deve ser editado manualmente** — será sobrescrito no próximo restart.

### Proteção de estado interno

Os arquivos de estado interno da esteira (`snapshot.json`, `changeQueue.json`,
`throttle`) são memória exclusiva do core. O agente **não pode** acessá-los. A
proteção age em duas frentes:

- **No prompt:** `src/core/agent.py` mantém a lista `PROTECTED_PATHS` e a função
  `build_prompt` valida que nenhum desses padrões aparece no prompt enviado ao
  agente. Se aparecer, levanta `ValueError` identificando o arquivo — o path do
  snapshot nunca é entregue ao agente.
- **No contexto:** o `CONTEXT.md` gerado instrui explicitamente o agente a nunca
  ler, escrever, criar ou modificar esses arquivos.

Padrões protegidos (`PROTECTED_PATHS`):

| Padrão | Conteúdo |
|--------|----------|
| `.pipe/boards/*/snapshot.json` | Snapshot interno de cada board |
| `.pipe/changeQueue.json` | Fila persistente de sincronismo |
| `.pipe/throttle.json` | Estado do throttle de rate limit |
| `.pipe/throttle-*.json` | Estado do throttle por escopo |

## Anotações no body (comandos `@---`)

O body de cada issue pode conter um bloco de comandos no final, separado do
conteúdo real por uma linha contendo apenas `@---`. O core lê esse bloco e
aplica as relações/atributos no board; o body enviado ao board é sempre limpo
(sem o bloco). No fluxo down, o core reescreve o bloco a partir do estado real
da issue no board.

Desambiguação: se houver mais de um `@---`, o último vence e os anteriores são
removidos.

Filosofia presença/ausência: o que estiver escrito é o estado final. Comando
presente garante a relação/atributo; ausente, remove. Não há comandos de
"remover".

| Comando | Efeito |
|---------|--------|
| `/parent #N` | esta issue é sub-issue (filha) de N |
| `/children #N, #M` | N e M são sub-issues desta |
| `/blocked_by #N, #M` | esta issue está bloqueada por N e M |
| `/blocks #N, #M` | esta issue bloqueia N e M |
| `/labels a, b, c` | define (SET) as labels da issue |
| `/agent_level low\|medium\|high` | nível de agente (chave de `override-agent`) |
| `/need_human` | marca intervenção humana (label especial) |
| `/close [completed\|not_planned]` | fecha a issue |
| `/reopen` | reabre a issue |
| `/archive` | arquiva a issue no board |

A label `need_human` é especial: é tratada em campo próprio e não aparece em
`/labels`, embora no board seja uma label comum.

Exemplo de body completo:

```markdown
# Implementar login

Validar credenciais e retornar JWT.

@---
/parent #10
/blocked_by #42, #58
/labels backend, security
/agent_level high
```

### Incidente: sub-issues propagadas entre boards (#88/#98/#99/#106)

Ao vincular uma sub-issue a um parent presente em outro GitHub Project, o
GitHub Projects V2 pode propagar a filha para o project do parent sem
preencher o campo `Status`. O sync então pode interpretar o item sem coluna
como uma issue nova daquele board, criar arquivos locais duplicados e
executar o agente no contexto errado.

A correção é composta por cinco proteções:

1. operação `remove_from_board` via GraphQL `deleteProjectV2Item`;
2. pós-hook de `_add_sub_issue` (`_remove_propagated_items_without_status`)
   que consulta `projectItems`/`fieldValues` via GraphQL (mesmo padrão de
   `_belongs_to_board`/`get_issue`) e remove propagação sem `Status`;
3. guard em `create-down` que exige prova de propagação — a issue já
   registrada em outro board **configurado** com coluna conhecida — antes de
   descartar o evento e remover o item; `parent` isolado, sem essa prova, não
   basta (evita remover sub-issue legítima e nova);
4. fallback de coluna para issues realmente novas ou já rastreadas; e
5. detecção de coluna vazia como divergência a reconciliar.

**Histórico:** a primeira tentativa (PR #102 original) usava endpoints REST
inexistentes para Projects V2 e um teste que fazia `monkeypatch` do próprio
método sob teste, mascarando a ausência de cobertura real — reprovada em code
review (issue #106). Uma segunda tentativa concorrente (sub-issue #98, PR
#103) foi cancelada pela decisão do débito #110, que definiu #88/PR #102 como
veículo único da correção. A implementação corrigida (GraphQL real, guard com
prova de propagação, suíte sem monkeypatch do código sob teste) foi entregue
no commit `a00ba7c` e integrada à branch do PR #102.

**Estado da entrega:** homologação aprovada em 19/08/2026. O merge do PR #102
e o deploy continuam sendo necessários para disponibilizar a correção em
produção. A correção previne novas duplicações, mas não remove resíduos
anteriores (#84/#85/#86), que exigem limpeza manual com a esteira parada.

Documentação: [change #88](doc/changes/88-sub-issues-propagadas-entre-boards.md),
[registro da tentativa cancelada #98](doc/changes/98-sub-issues-propagadas-entre-boards.md)
e [post mortem #99](doc/incidente/sub-issues-propagadas/ticket.md).

## Eventos de coluna (`on_in` / `on_out`)

Cada coluna pode declarar arrays `on_in` (disparado ao entrar) e `on_out`
(disparado ao sair). Quando uma issue muda de coluna, o core dispara o
`on_out` da coluna de origem e o `on_in` da coluna de destino.

```yaml
columns:
  concluido:
    name: Concluído
    on_in:
      - close
      - done
    on_out:
      - -done
```

Tokens suportados:

| Token | Efeito |
|-------|--------|
| `close` | fecha a issue |
| `open` | reabre (se fechada) e desarquiva (se arquivada) |
| `archive` | arquiva o item no board |
| `-archive` | desarquiva o item no board |
| `need_human` | adiciona a label `need_human` |
| `-need_human` | remove a label `need_human` |
| `<label>` | adiciona a label |
| `-<label>` | remove a label |

Os eventos disparam tanto em movimentação local quanto manual no board. Numa
movimentação manual no GitHub, o sync reescreve o `-body.md` aplicando os
eventos no bloco `@---` (sem tocar no snapshot); como o arquivo fica mais novo
que o `body_mtime` salvo, o ciclo seguinte gera um `change-up` que sobe os
status/labels resultantes — mantendo tudo sincronizado.

## Otimização de Sincronização

Para reduzir o número de requisições ao board por issue, o sync combina duas
estratégias:

- **Down (chamada única):** `get_issue` traz numa só query GraphQL título,
  body, estado, labels, parent, filhos, coluna e arquivamento. As dependências
  (`blocked_by`/`blocks`) só existem via REST e são buscadas apenas quando o
  item da fila está marcado como `fullsync`.
- **Up (comparar antes de escrever):** o estado desejado (comandos do arquivo)
  é comparado com o estado conhecido no snapshot; só a diferença gera chamada.
  Um `change-up` de "só body" cai de ~12 requisições para 1.

### fullsync

Cada item da fila tem um booleano `fullsync`. É `True` em todo create e no
full sync diário (reconcilia propriedades + dependências); `False` em
mudanças incrementais. Se um item full e um parcial coincidem no mesmo alvo,
a fila promove o existente para full (sem duplicar).

### Gatilho de par recíproco

Relações são bidirecionais (`parent`↔`children`, `blocked_by`↔`blocks`). Ao
detectar uma relação adicionada/removida numa issue, o sync enfileira um
`change-down fullsync` do alvo **apenas se o snapshot do alvo ainda não
refletir o par recíproco**. Essa checagem é a condição de parada e evita
reação em cadeia infinita.

### Sub-issues propagadas entre boards sem coluna

Ao vincular uma sub-issue a um parent que está em outro GitHub Project, o
GitHub Projects V2 pode adicionar automaticamente a filha aos projects do pai
sem preencher o campo `Status`. Sem tratamento, esse item seria interpretado
como uma nova issue do board e criaria arquivos locais duplicados.

A sincronização trata esse efeito colateral em duas camadas:

1. **Prevenção após o vínculo:** depois de criar a relação parent/child, o
   adapter consulta via GraphQL os `projectItems` da sub-issue (com o `Status`
   de cada item em `fieldValues`) e remove, por `deleteProjectV2Item`, os itens
   de **outros** projects cujo `Status` está vazio. Dados de Projects V2 não
   existem na REST API — a consulta usa o mesmo padrão de `get_issue` e
   `_belongs_to_board`. Itens com coluna definida são preservados, inclusive
   participações multi-board intencionais.
2. **Defesa no `create-down`:** se um item sem coluna já está registrado em
   outro board configurado com coluna conhecida, o core o remove do board atual
   via `deleteProjectV2Item`, descarta o evento e não cria arquivos locais. A
   simples presença de `parent` não basta para remover: sem prova de presença em
   outro board, a issue pode ser uma sub-issue legítima e nova do board atual, e
   segue o fluxo normal com o fallback da primeira coluna.

O project informado ao pós-hook é sempre preservado, mesmo temporariamente sem
`Status`; se esse project não puder ser resolvido, nada é removido. Como
`set_children` informa o project do pai — justamente onde o item propagado
aparece —, esse caminho é coberto deliberadamente pela camada 2, que tem a prova
de presença no snapshot.

A remoção precisa concluir antes de o evento ser descartado; falhas propagam e
são reprocessadas pela fila. Snapshots de boards ausentes do `pipe.yml` não
servem como prova. Além disso, uma coluna remota vazia passa a ser detectada
como divergência: em issues já rastreadas, o `change-down` reaplica no board a
coluna conhecida do snapshot (evitando que a mesma divergência retorne em todo
full sync), e `create_issue` nunca deixa uma issue nascer sem `Status` — coluna
inexistente cai na primeira opção do project com warning.

> A correção previne novas duplicações, mas não remove automaticamente resíduos
> que já haviam sido materializados localmente antes da atualização. Esses itens
> devem ser removidos manualmente do project indevido, com a esteira parada.

### Incidente conhecido: parent recursivo (#97)

Em 01/08/2026, um arquivo órfão com prefixo numérico foi associado à issue
`#76` após o caminho salvo para seu body ficar obsoleto. O sync sobrescreveu o
conteúdo da issue, tentou aplicar `set_parent(76, 76)` e recebeu HTTP 422. Como
o evento inválido permaneceu na cabeça da fila global, todos os boards ficaram
sem processamento por 2h37.

O estado afetado foi reparado operacionalmente (conteúdo da issue restaurado e
arquivos órfãos removidos das colunas ativas), mas as correções preventivas de
código **ainda estão pendentes**. Elas estão divididas em C1–C5: resolução
segura do body, validação de auto-referência, tratamento de mensagem-veneno,
proteção de integridade do estado e lock de instância única.

Até essas correções serem entregues:

- crie issues novas somente como `<slug>-body.md`, sem prefixo numérico;
- não execute duas instâncias da esteira sobre o mesmo estado;
- não altere arquivos internos da `.pipe` manualmente;
- trate repetição contínua de `Erro no ciclo (não fatal)` para o mesmo item
  como incidente: interrompa a instância duplicada, preserve os logs e siga o
  procedimento registrado no ticket antes de reiniciar.

A análise, a mitigação e o plano completo estão em
[`doc/incidente/parent-recursivo/ticket.md`](doc/incidente/parent-recursivo/ticket.md).

### Issues fantasmas (erro irrecuperável)

Quando o sync tenta aplicar uma mudança (`change-up` ou `delete-up`) sobre uma
issue que **não existe** no GitHub, a API responde com
`Could not resolve to an issue or pull request`. Antes, esse erro era tratado
como transitório e, como a fila é *at-least-once*, o evento voltava a cada
ciclo — travando a esteira num loop (ou, na base atual, num crash-loop). Foi a
causa central do incidente "Issue Fantasma".

Agora `_apply_change_up` e `_apply_delete_up` (em `src/core/sync.py`) tratam
esse erro específico: registram um warning
(`removendo do snapshot (issue fantasma)`), removem a entrada correspondente do
snapshot e **descartam** o evento em vez de re-enfileirá-lo. Qualquer outra
exceção continua propagando normalmente.

### Isolamento de IDs entre boards

O espaço de números de issues do GitHub é **compartilhado** entre todos os
boards de um mesmo repositório (epic, story, task…). Sem validação, uma
operação destrutiva num board poderia fechar/alterar uma issue de outro board
que coincidisse no número — foi o que fechou os épicos #1, #2, #3 no incidente.

Antes de qualquer operação destrutiva (`update_issue`, `close_issue`), o adapter
`github_board.py` valida a pertinência via `_belongs_to_board`: uma query
GraphQL lista os `projectItems` da issue e confirma que o projeto do board alvo
está entre eles. Se não pertencer, a operação é **abortada** com um warning
(`não pertence a este board — operação abortada`).

- **Custo:** +1 chamada GraphQL por operação destrutiva. Em um board ativo
  (~10 closes/min) isso adiciona ~10 chamadas/min — dentro da quota padrão de
  5000 pontos/hora do GraphQL do GitHub.

## Rate Limit (GitHub)

Toda requisição respeita o throttle, inclusive dentro de loops de
sincronização.

### Detecção

O rate limit é detectado **apenas por sinais de transporte**, nunca pelo corpo
da resposta:

- **Status HTTP** `403`/`429` (linha de status capturada via `gh api -i`).
- **stderr** do `gh` mencionando rate limit.
- **GraphQL**: resposta `200` com `errors[].type == RATE_LIMITED` (a seção
  estruturada de erros, não o conteúdo das issues).

O corpo da resposta **não** é escaneado em busca da expressão "rate limit". Se
fosse, o título/body de uma issue contendo esse texto (ex.: uma issue sobre
custo de API) provocaria falso-positivo em toda listagem, escalando throttle e
penalty indevidamente.

### Throttle
- Sleep antes de cada chamada (em segundos; escala `0, 1, 2, 4, ... 64`)
- Ao receber secondary rate limit, dobra (até 64s); se estiver em `0`, sobe para `1`
- Regride após 1h sem problemas: divide por 2; ao chegar em `1`, cai para `0` (sem espera)

### Penalty
- Ativado quando throttle atinge 64s e ainda falha
- Bloqueia chamadas por N horas (dobra a cada ativação)
- Regride após 1h sem problemas

## Documentação Técnica

- [Contexto e decisões técnicas](CONTEXT.md)
- [Changelog](CHANGELOG.md)
