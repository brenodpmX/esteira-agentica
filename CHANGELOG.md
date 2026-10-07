# Changelog

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

## [1.25.0] - 2026-10-06

### Corrigido

- **Mudança de relação (bloqueio/sub-issue/parent) agora é percebida na
  sincronização, mesmo sem alterar `updatedAt`.** Operações de dependência
  nativa (`blocked_by`/`blocking`) e de vínculo de sub-issue no GitHub NÃO movem
  o `updatedAt` da issue nem o Status/coluna do item no ProjectV2. Como
  `sync_remote` só divergia por `updatedAt` ou coluna, uma troca de bloqueio
  feita no board nunca era reconciliada localmente: um `/blocked_by` obsoleto
  persistia no body local e congelava a fila (`_is_blocked` segue considerando a
  issue bloqueada por um bloqueador já concluído). Caso real: épico #1 do
  escrevas parado atrás de um bloqueio fantasma `#73 /blocked_by #226` com #226
  já concluída e a dependência já removida no GitHub.

### Adicionado

- **`list_issues` dobra `blockedBy`/`blocking`/`parent`/`subIssues`/`state` na
  MESMA query GraphQL do ProjectV2** (antes só `number/title/body/updatedAt/
  labels`). Custo medido via `rateLimit{cost}`: 1 ponto por página (`first:5`),
  inalterado — as relações vêm sem request adicional. Cada `Issue` listada passa
  a carregar as relações e o `state`, com warning quando `totalCount` excede a
  página (`first:50`), sinalizando mudança possivelmente não detectável sem
  paginação adicional.
- **`sync_remote` compara as relações contra o snapshot** (`blocked_by`,
  `blocks`, `children`, `parent`), por comparação direta e insensível à ordem,
  independente de qualquer timestamp. Qualquer divergência enfileira o mesmo
  `change-down` (fullsync) já existente, que reconcilia o body local. Elimina a
  dependência do `updatedAt` como relógio para relações — a causa-raiz do freeze.
  `get_issue(fullsync=True)` segue usando REST para as dependências na
  reconciliação (acurado e só chamado quando há mudança), sem custo por ciclo.



### Adicionado

- **Socket Docker Unix no container do agente (`/var/run/docker.sock`) via
  sidecar `sockbridge`.** Completa o ambiente DinD (Opção B, v1.13.0): o
  container `pipe` compartilha o NETWORK namespace do `dind` (alcança o daemon
  em `tcp://127.0.0.1:2375`) mas NÃO o filesystem, então nunca enxergou o socket
  unix do dind. Ferramentas que assumem o socket unix padrão falhavam dentro do
  pipe — notavelmente **Testcontainers** (ex.: `IntegracaoBase`/`mvn verify` do
  escrevas, que fixa `UnixSocketClientProviderStrategy` + `/var/run/docker.sock`),
  reportando "sem Docker Unix socket". Novo serviço `sockbridge` (reusa a imagem
  do pipe, que agora traz `socat`) roda como root e encaminha
  `UNIX-LISTEN:/var/run/docker.sock` → `TCP:127.0.0.1:2375`; o socket vive num
  named volume `docker-sock` montado em `/var/run` tanto no bridge quanto no
  pipe. O `pipe` ganha `depends_on: sockbridge (service_healthy)`. Resultado:
  Testcontainers e o `docker` CLI sem `DOCKER_HOST` passam a funcionar dentro do
  pipe **sem alterar o produto**. É capacidade da ferramenta (qualquer produto
  com ITs Testcontainers se beneficia), não específica do escrevas. ADR-05
  preservado: a imagem e o `USER pipe` do serviço `pipe` não mudam; só o
  `sockbridge` efêmero usa root. `TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE=
  /var/run/docker.sock` continua coerente: o path é resolvido pelo daemon do
  dind (que tem o socket real) ao montar no Ryuk.



### Corrigido

- **Subida idempotente quando `.pipe/` (ou outro diretório de estado) não existe
  no `up` — fim do `PermissionError` em `.pipe/pipe.lock`.** Com os bind mounts
  de estado do `compose.dev.yml`, se o diretório do host não existir no momento
  do `docker compose up`, o daemon Docker cria o mountpoint como **root**; o
  serviço `pipe` roda como usuário não-root `pipe` (uid 1000, ADR-05) e falhava
  com `PermissionError: [Errno 13] Permission denied: '.pipe/pipe.lock'` em
  `lock.acquire`, entrando em crash-loop. Acontecia ao remover `.pipe` (unblock
  manual) ou ao matar/subir o pod sem passar pelo `make` (que faz `mkdir -p`).
  Correção: novo serviço efêmero `init-perms` no `docker-compose.yml` que roda
  como root APENAS para `mkdir -p` + `chown pipe:pipe` dos pontos de montagem de
  estado (`/app/.pipe`, `/app/logs`, `/app/repo`, `/home/pipe/.kiro`,
  `/home/pipe/.local/share/kiro-cli`) e encerra; o serviço `pipe` ganha
  `depends_on: init-perms (service_completed_successfully)`. O `compose.dev.yml`
  espelha os três bind mounts de estado no `init-perms` para que ele corrija a
  posse do diretório do host. ADR-05 preservado: a imagem e o `USER pipe` do
  serviço `pipe` não mudam — apenas este init efêmero usa root. Com named
  volumes (base) o passo é inócuo (reafirma pipe:pipe). Torna `rm -rf .pipe` +
  subida (ou pod morto) recuperável sem intervenção manual de permissão.



### Corrigido

- **Presença única de uma issue deixa de travar em `unresolved` por ter pai
  cross-board (fim do loop eterno na reconstrução de snapshot).**
  `classify_participation` (`src/core/participation.py`) classificava como
  `unresolved` toda issue com relação pai/filho ligando-a a outro quadro quando
  não havia prova de propagação, mesmo quando a issue existia em UM ÚNICO
  quadro. Numa hierarquia (epic->story->task) isso é o estado normal de todo
  filho, não propagação: a propagação da plataforma sempre se materializa como
  uma SEGUNDA presença, nunca como uma só. O efeito era um deadlock permanente —
  a presença nunca entrava no snapshot (create-down adiado, sem gravar arquivos),
  então cada ciclo de sync a redescobria como nova, re-despachava create-down,
  refazia o `get_issue(fullsync)` e readiava: a esteira girava a cada ciclo sem
  nunca dormir nem progredir. Sintoma visto no escrevas quando o `.pipe` foi
  apagado e o motor subiu num snapshot vazio: stories #73/#79/#80/#81 (filhas do
  epic #1) em loop eterno. Correção: presença ÚNICA (nenhuma outra presença em
  quadro configurado) é sempre `origin`, mesmo com pai cross-board — não há cópia
  a remover nem impasse que o tempo resolva. A adjudicação de propagação/
  duplicidade passa a depender exclusivamente de haver presença em OUTRO quadro
  configurado (duplicidade real), não do sinal `has_cross_board_parent`. O sinal
  só diferencia o motivo em `evidence` (`sole_presence_cross_board_parent` vs
  `first_presence`). Torna a classificação idempotente: snapshot vazio ou cheio,
  mesmo resultado — matar o pod e subir reconstrói o estado como estava.

- **Backoff de participações não resolvidas agora é respeitado no enfileiramento
  (`src/core/sync.py`).** `sync_remote` reenfileirava `create-down` para toda
  issue ausente do snapshot a cada ciclo, sem consultar o adiamento gravado em
  `.pipe/participationPending.json` (`next_attempt_at`). Uma presença genuinamente
  `unresolved` (duplicidade ambígua ou falha de consulta) nunca persiste, então
  era redescoberta e re-despachada a cada ciclo — o mesmo loop sem throttle,
  gastando API/créditos. O backoff existia (`defer_pending`/`is_due`) mas nenhum
  ponto o consultava fora de `detect_external_removal`. Agora `sync_remote` pula
  o reenfileiramento enquanto a pendência não vence o prazo, limitando a
  reavaliação a uma vez por intervalo (`rerun_cooldown` ou 300s) em vez de a cada
  ciclo.



### Corrigido

- **Erros determinísticos de argumento da CLI gh agora falham rápido
  (fail-fast) em vez de retry cego.** `classify_error` (`src/core/sync.py`)
  passou a reconhecer os erros de uso do parser cobra do gh (flag/argumento/
  subcomando inválido) e classificá-los na nova categoria `definitivo_cli`,
  tratada no mesmo caminho fail-fast do `definitivo`: o item é isolado em
  dead-letter já na primeira falha, sem consumir `max_attempts`. Antes esses
  erros caíam no default `transitorio` e eram re-enfileirados até esgotar as
  tentativas — desperdício garantido, pois reprocessar um comando malformado
  produz exatamente o mesmo erro. É a classe do incidente not_planned
  (`invalid argument "not_planned" for "-r, --reason" flag`), cujo sintoma
  pontual já fora corrigido na fronteira do gh, mas cuja classe genérica
  seguia como transitória. Assinaturas reconhecidas: `unknown flag:`,
  `unknown shorthand flag:`, `flag needs an argument:`, `arg(s), received `
  (cobre `accepts N`/`requires ... N`), `unknown command "` e
  `invalid argument "X" for "..."`. Novo `next_step` orienta corrigir a
  construção do comando no engine (reprocessar não resolve). Erros de
  transporte/rede permanecem `transitorio`.

### Alterado

- **Resumo de sincronização por ciclo rebaixado para TRACE.** A linha
  `sincronizacao board=<id> criados=<n> atualizados=<n> removidos=<n>
  resultado=ok` (`sync_remote`) era emitida em INFO a cada ciclo de cada
  board, poluindo o terminal com ruído de rotina. Agora sai em TRACE (vai só
  para o arquivo, não para o terminal). Os casos `resultado=limite` e
  `resultado=erro` seguem em INFO.

## [1.23.1] - 2026-10-05

### Corrigido

- **Integração em produção da integridade de participação entre quadros
  (#310).** A entrega 1.23.0 introduziu a política e os efeitos de participação
  (`src/core/participation.py`, `src/core/participation_reconcile.py`) cobertos
  por testes unitários, mas as funções de reconciliação ainda não eram chamadas
  pelo fluxo real do motor — a correção não tinha efeito em produção. Esta
  versão liga cada gatilho ao caminho executado pela esteira e adiciona testes
  de integração que exercitam esses caminhos de ponta a ponta:
  - **RF-07 (reconciliação imediata pós-vínculo):** `sync._apply_change_up`
    passa a chamar `reconcile_after_link` (via `_reconcile_links_after_apply`)
    sempre que um vínculo pai/filho entre quadros distintos é aplicado,
    removendo a presença propagada da filha no quadro do pai — inclusive quando
    a propagação chega com coluna preenchida (CT-03), caso que o pós-hook antigo
    por "Status vazio" não cobria.
  - **RF-08 (reconciliação tardia na descoberta remota):**
    `sync._apply_create_down` substitui o guard por coluna vazia
    (`_propagation_proof`, removido) por `reconcile_remote_presence`, que
    classifica a presença via `classify_participation` e persiste
    `participation_intent` (`origin`/`authorized`) no snapshot da issue nova;
    presença `propagated` é removida e o evento descartado, `unresolved` é
    adiada sem criar arquivos.
  - **RF-12 (contingência):** `_filter_suspended_cross_board_parent` passa a
    delegar a decisão a `guard_cross_board_link` (fonte única da regra), unindo
    as duas implementações antes redundantes.
  - **RF-13 / CT-22 (remoção externa):** o loop principal
    (`__main__.sync_remote_board`) chama `detect_external_removal` a cada
    descoberta remota, registrando `participation_removed_externally` quando uma
    presença pendente some sem reconciliação própria.
  - **RF-15 (correlação de despacho):** o log de execução de agente
    (`kiro_cli_agent._build_log`) passa a registrar `participation_intent` e
    `origin_board`, carregados em `AgentParams`.

## [1.23.0] - 2026-10-05

### Adicionado

- **Integridade de participação de issues entre quadros de trabalho (#310).**
  Quando uma relação pai/filho nativa (sub-issue) liga issues de quadros
  (projects) distintos, o GitHub Projects V2 pode propagar automaticamente a
  issue filha para o quadro do pai — presença que não representa uma decisão
  de quem opera a esteira. Até aqui, essa presença automática (com ou sem
  coluna preenchida) era tratada como issue legítima do quadro, tornando-se
  elegível à seleção de tarefas e podendo disparar um agente no fluxo errado
  (ex.: uma tarefa processada como história). A esteira agora classifica,
  reconcilia e bloqueia essa presença antes que vire trabalho executável, sem
  nunca desfazer a relação pai/filho e sem impedir a participação legítima em
  mais de um quadro quando explicitamente autorizada.
  - **Classificação de intenção** (`src/core/participation.py`): toda presença
    de uma issue em um quadro é classificada, por uma função pura e sem rede,
    em um dos quatro estados — `origin` (presença original), `authorized`
    (participação multi-quadro autorizada pelo rótulo reservado
    `board-intent-<id-do-quadro>`), `propagated` (efeito colateral automático
    da plataforma — some do quadro indevido) ou `unresolved` (evidência
    ambígua ou falha transitória — fica pendente, nunca é removida por
    omissão). A coluna (Status) preenchida ou vazia não influencia o
    resultado, e o mesmo estado de entrada produz sempre a mesma classificação
    independente da ordem de avaliação.
  - **Reconciliação automática** (`src/core/participation_reconcile.py`), em
    dois gatilhos: imediatamente após a criação do vínculo pai/filho e,
    como rede de segurança, na descoberta remota seguinte (para o caso de a
    plataforma materializar a presença depois da primeira consulta). Falhas de
    consulta/remoção são erros tipados — nunca silenciados — e o item fica
    pendente para nova tentativa sem bloquear o restante da fila nem contar
    como tentativa esgotada.
  - **Barreira final na seleção de tarefas** (`keep_task`): nenhuma issue sem
    intenção confirmada (`origin`/`authorized`) é escolhida para execução ou
    avanço automático, mesmo que algo escape das reconciliações anteriores;
    essa verificação não faz nenhuma chamada de rede.
  - **Migração de issues já existentes**: no início do processo, antes da
    primeira seleção de tarefas, toda issue sem o campo de intenção o recebe
    automaticamente — presente em um único quadro vira `origin`; presente em
    mais de um quadro sem autorização vira `unresolved` em todas as entradas;
    um campo já preenchido nunca é sobrescrito.
  - **Contingência operável sem reiniciar a esteira**: a chave opcional
    `safety.cross_board_parent_links` no `pipe.yml` (valores `enabled` —
    padrão — ou `suspended`) permite a um operador recusar temporariamente a
    criação de novos vínculos entre quadros distintos. A chave é relida do
    arquivo a cada vínculo avaliado (sem cache em memória), portanto
    ativar/desativar tem efeito imediato, sem reiniciar o processo. Vínculos
    dentro do mesmo quadro e vínculos já existentes nunca são afetados. Um
    valor diferente de `enabled`/`suspended` é rejeitado na validação do
    `pipe.yml` com mensagem citando a chave e o valor recebido.
  - **Observabilidade**: novos eventos estruturados no log diário —
    `participation_classified`, `participation_reconciled`,
    `participation_reconcile_failed`, `participation_removed_externally`,
    `dispatch_blocked_unconfirmed_intent` (deduplicado por quadro/coluna/issue)
    e `cross_board_link_blocked` — sem segredos, body de issue ou conteúdo
    protegido. No início do processo, a esteira também registra
    `rollout_evidence` (versão, commit, ambiente, instante de início), com
    qualquer campo ausente sinalizado explicitamente em vez de inferir
    sucesso; essa evidência é o pré-requisito para comprovar que a correção
    está de fato em execução no ambiente. O log de execução de agente passa a
    incluir a intenção da participação e o quadro de origem da issue.
  - Novo estado interno protegido (nunca acessível ao agente):
    `.pipe/participationPending.json`, com os itens de participação
    pendentes de reconciliação e seus próximos horários de nova tentativa.
  - A cobertura vale para qualquer par de quadros com relação hierárquica,
    presente ou futuro, sem lista de pares codificada no motor.

## [1.22.0] - 2026-10-05

### Adicionado

- **Captura do consumo real por execução (créditos) a partir do kiro-cli.** O
  registro de negócio de cada execução (`.pipe/executionRecords.json`, #307)
  passa a gravar o consumo **medido** — `valor`/`unidade`/`origem` — em vez do
  `indisponível` fixo. A linha-resumo `▸ Credits: X • Time: Ys` volta a aparecer
  no final do log de chat e no log diário (`execução concluída: ...`).

### Corrigido

- **Consumo sempre `indisponível` / linha de créditos sumindo dos logs.** Desde
  o kiro-cli 2.27.x o modo texto `--no-interactive` deixou de imprimir a
  linha-resumo de créditos/tempo; o consumo passou a ser exposto apenas em
  `--output-format stream-json` (evento `metadata.meteringUsage`, unidade
  `credit`). O adapter rodava em modo texto e o motor fixava
  `Consumo.indisponivel(...)` no registro, então nenhuma execução reportava
  consumo — mesmo com créditos sendo cobrados.
  - Correção: o adapter `kiro_cli_agent` agora executa com
    `--output-format stream-json` e reconstrói um transcript legível a partir
    dos eventos ACP (prosa do agente, linhas `[tool] ...`, erros de
    `runFinished`), somando o `meteringUsage` do metadata final do turno e
    expondo o resultado em `ExecutionResult.consumo`. `_write_execution_record`
    (`__main__`) grava esse consumo, degradando para `indisponível` apenas
    quando o canal não reporta medição (timeout, não-inicialização, result
    `None`). A classificação de falha permanece por canais estruturados
    (`[exit-code]`/`[TIMEOUT]`/`[ERRO]` + trechos preservados crus), sem
    regressão. `turnDurationMs` alimenta a linha-resumo de tempo.

## [1.21.0] - 2026-10-02

### Alterado

- **Ponteiro do manual `@---` removido do prompt dinâmico (#325).** Desde a
  1.18.0 o manual completo dos comandos `@---` vive no steering (contexto sempre
  carregado); a #308, porém, reintroduzira no prompt dinâmico um ponteiro curto
  ao manual (seção "## Anotações no body (comandos `@---`)"), incluído sob
  demanda e controlado pela chave de coluna `allowed-commands`. Agora o prompt
  dinâmico não contém absolutamente nada sobre `@---` — nem o manual, nem o
  ponteiro. O manual passa a existir exclusivamente no steering (origem única).
  - `src/core/agent.py` (`build_prompt`): removido o bloco que injetava a seção
    "## Anotações no body (comandos `@---`)".
  - `src/core/composition.py`: removidos a constante `REF_MANUAL_ARROBA`, o
    conjunto `_ANNOTATION_COMMANDS` e as funções `allowed_commands` e
    `on_demand_references` (gate de referência sob demanda).
  - `src/core/config.py`: removida a validação da chave de coluna
    `allowed-commands`, cujo único propósito era controlar esse ponteiro. A
    chave deixa de ser reconhecida pelo schema (ignorada, sem efeito).
  - `src/__main__.py` (`compose_execution_record`): o campo
    `referencias_sob_demanda_incluidas` do registro `composicao_medicao` passa a
    ser sempre uma lista vazia (contrato de tipo preservado).

## [1.20.1] - 2026-10-02

### Corrigido

- **Falso-positivo de `delete-down` por fetch incompleto, com perda
  irreversível de vínculos de bloqueio.** Em `sync_remote` a poda de issues
  "ausentes do fetch" era disparada apenas por `issue_id not in remote_by_id`,
  sem qualquer confirmação. Quando `list_issues` devolvia um resultado
  **incompleto** (paginação ou consistência eventual do ProjectV2 retornando
  menos itens do que o real), issues ainda vivas pareciam deletadas e geravam
  `DELETE_DOWN`. O tratamento de delete remove, via `set_blocked_by`/
  `set_blocks`, os **vínculos de bloqueio recíprocos** das issues apontadas —
  uma operação **destrutiva e irreversível** no board. Num ciclo seguinte, um
  fetch completo recriava as issues (`create-down`), mas as dependências já
  haviam sido apagadas e não eram restauradas. Resultado observado: cadeia de
  bloqueios inteira de um board apagada por um único fetch truncado.
  - Correção: antes de podar, a ausência é **confirmada** relendo a issue
    diretamente (`_absence_confirmed`). Só há `delete-down` quando a issue
    realmente saiu do board: node nulo (deletada de fato), arquivada, ou sem
    coluna/participação neste board. Issue ainda viva, não arquivada e com
    coluna => ausência tratada como **fetch incompleto** e a poda é
    **suprimida** (log de aviso), preservando o estado. Em erro de releitura o
    comportamento é conservador (não poda).
  - `GithubBoardAdapter.get_issue` passa a devolver `None` quando o node da
    issue é nulo (deletada), distinguindo deleção real de fetch incompleto; os
    aplicadores de `create-down`/`change-down` ignoram com segurança issues
    inexistentes.
  - Testes: `tests/test_incremental_absent_delete_down.py` ganha
    `test_incomplete_fetch_suppresses_delete_down`,
    `test_deleted_issue_confirmed_prunes` e
    `test_archived_issue_confirmed_prunes`. Os invariantes de poda de
    arquivadas/deletadas são preservados.

## [1.20.0] - 2026-10-02

### Adicionado

- **Registro de execução de agentes com consolidação por linhagem histórica**
  (issue #307). Ao final de **cada** execução de agente e em **qualquer**
  desfecho, o motor passa a gravar um **registro de negócio estruturado e
  persistente**, independente do log detalhado em Markdown
  (`logs/<issue_id>/<ts>.md`, sujeito a `log.ttl`). O registro é a base durável
  para responder, em lote e **sem abrir nenhum log individual**: quantas
  execuções uma issue exigiu, quanto tempo/consumo cada etapa demandou, quais
  desfechos ocorreram, quanto esforço foi repetido sem a issue progredir e qual
  o esforço agregado de uma issue principal somada a todos os seus descendentes
  históricos conhecidos.
  - Novo módulo `src/core/execution_record.py` com os campos do registro
    (identidade, tempo, contexto, resultado, avanço, consumo com proveniência e
    `log_ref`), a **taxonomia fechada e total** de `resultado` (`concluída` |
    `falha terminal` | `timeout` | `interrompida` | `desconhecida`, nunca vazio),
    o mapeamento determinístico `ExecutionResult` → `resultado` (`map_resultado`),
    o cálculo de `repeticao_sem_avanco` e a consulta por issue raiz
    (`consulta_linhagem`) com agregação, segmentação de consumo por
    `{unidade, origem}` e sinalização de descendente sem registro.
  - **Resultado técnico e avanço são dimensões independentes** (RN-01):
    `avancou` é observado pela mudança de etapa, não derivado do `resultado`.
    `repeticao_sem_avanco` marca nova execução da **mesma** issue na **mesma**
    etapa após uma anterior que não a fez progredir (mudança de etapa
    descaracteriza).
  - **Consumo com proveniência** (RN-04/RN-05): preserva `valor`, `unidade`,
    `origem` e `disponibilidade`. Consumo **não informado**
    (`disponibilidade = indisponível`, sem valor) e **zero reportado**
    (`disponibilidade = disponível`, `valor = 0`) são estados **distintos** e
    nunca compartilham representação. "Tokens" é apenas o **rótulo geral**
    (`ROTULO_CONSUMO`); cada plataforma preserva sua unidade nativa, sem
    conversão. O adapter `kiro-cli` não expõe tokens ⇒ `indisponível` é o
    comportamento **correto**, não falha.
  - **Linhagem histórica resiliente à limpeza local** (RN-06/RN-07/RN-08): a
    consulta por issue raiz é reconstruída **somente** dos registros próprios
    (`issue_id` + `issue_parent` capturados por execução), nunca dos arquivos
    locais nem dos logs. Arquivar a issue (que apaga `-body/-history/-addcomment`)
    e expurgar logs por TTL **não** removem a existência, o parentesco nem as
    métricas. A travessia neutraliza ciclos e múltiplos caminhos (cada
    issue/execução conta exatamente uma vez) e descendente conhecido sem registro
    aparece sinalizado (`sem_registro`), nunca omitido.
  - **Retenção própria e desacoplada do `log.ttl`:** chave opcional
    `registro.retencao_dias` (raiz do `pipe.yml`, inteiro `> 0`). Ausente ⇒
    nenhum expurgo automático (estado seguro por padrão); presente ⇒ registro com
    idade `>= retencao_dias` fica elegível a expurgo (`purge_expired`), acionado
    pelo motor no startup após `log.cleanup()`. É o **único** caminho de remoção
    — não há exclusão manual de registro por qualquer papel, e excluir uma issue
    **não** remove seus registros.
  - **Fonte única de contagem (CA-18):** a métrica "quantas execuções houve no
    contexto `(board, coluna, issue)`" continua tendo origem única em
    `src/core/agent_circuit_break.py`. Esta capacidade **adere** a essa fonte e
    **não** cria contador paralelo; grava **um registro por execução** (artefato
    de negócio por execução), que não é a métrica de contexto.
  - **Persistência atômica e protegida** em `.pipe/executionRecords.json`
    (temp + `fsync` + `os.replace`, com `version` para integridade); o arquivo
    entra em `PROTECTED_PATHS` (`src/core/agent.py`) — seu conteúdo e caminho
    nunca são expostos a agente/prompt/comentário/log.

### Alterado

- **`src/__main__.py::call_agent`** passa a gravar o registro ao fim do
  dispatch, em qualquer desfecho, de forma **fail-safe** (falha de persistência
  do registro não derruba a esteira — a execução já ocorreu). O `startup`
  executa o expurgo por retenção (`purge_expired`) após `log.cleanup()`,
  desligado por padrão.
- **`src/core/config.py`** ganha `validate_registro`, chamada em `check_config`,
  rejeitando bloco malformado, `retencao_dias` não inteiro/≤ 0 ou campo
  desconhecido, com `ConfigError` citando o caminho, antes de qualquer alteração
  de estado.

### Documentação

- Novo contrato técnico da capacidade
  [`doc/architecture/registro-execucao-agentes-linhagem-historica/contrato.md`](doc/architecture/registro-execucao-agentes-linhagem-historica/contrato.md),
  com os campos do registro, a taxonomia e o mapeamento concreto, a semântica de
  consumo/unidade, a regra de repetição sem avanço, a linhagem resiliente a
  arquivamento/expurgo e a configuração de retenção.
- `README.md` ganhou a seção "Registro de execução de agentes
  (`registro.retencao_dias`)" dentro de "Execução de Agentes", documentou a chave
  opcional no exemplo de `pipe.yml` e registrou `.pipe/executionRecords.json` na
  tabela de arquivos protegidos (`PROTECTED_PATHS`).

## [1.19.0] - 2026-10-01

### Adicionado

- **Limitador de reexecuções de agente por contexto** (issue #306). Mecanismo
  **opt-in** que conta toda execução entregue ao agente por contexto
  `(board, coluna, issue)` — no instante da entrega, independentemente do
  resultado — e, quando o operador configura uma política de limite por janela
  de tempo, **impede a execução excedente antes de ela começar**, marca a issue
  com `need_human`, publica um comentário acionável idempotente e **zera a
  franquia** do contexto. Complementa o cooldown existente
  (`boards.rerun_cooldown`): enquanto o cooldown apenas **espaça** reexecuções
  (sem teto), o limitador impõe um **teto** e **pede intervenção humana**.
  - Novo módulo `src/core/agent_circuit_break.py` como **fonte única** da
    contagem (sem contador paralelo): identidade `(board, coluna, issue)` com
    reinício da contagem ao mudar de coluna; janela deslizante contando apenas
    ocorrências com idade **estritamente menor que `T`** (borda fechada em `T`);
    máquina de estados do bloqueio na ordem obrigatória (persistir evento +
    esvaziar ocorrências → aplicar `need_human` → publicar comentário
    idempotente via marcador oculto `<!-- agent-circuit-break:<event_id> -->` →
    reconciliar); reinício da franquia no bloqueio e retomada humana ao remover
    `need_human`, sem resíduo da janela anterior.
  - **Configuração opcional na raiz** do `pipe.yml` (fora do mapa `boards`):
    `agent_circuit_break.executions` (`N`, inteiro `>= 1`) e
    `agent_circuit_break.window` (`T`, segundos, inteiro `>= 1`), exigidos
    juntos; a ausência do bloco mantém a política inativa **sem** desligar a
    contagem interna. Validada em `src/core/config.py::check_config`
    (`validate_agent_circuit_break`) antes de qualquer alteração de estado,
    rejeitando campo faltante, booleano, valor `< 1`, campo desconhecido ou
    bloco dentro de `boards`, com `ConfigError` citando o caminho do campo.
  - **Persistência atômica e protegida** em `.pipe/agentCircuitBreak.json`
    (`tempfile` + `fsync` + `os.replace`), resistente a reinício;
    **fail-closed** em estado corrompido/ilegível e em falha de escrita com a
    política ativa. O arquivo entra em `PROTECTED_PATHS`
    (`src/core/agent.py`) — seu conteúdo e caminho nunca são expostos ao agente,
    a comentários ou a logs.
  - **Gate de capacidade do adaptador na inicialização**: com a política ativa,
    um adaptador de board sem capacidade real de aplicar label faz a esteira
    **falhar na inicialização**, em vez de aparentar sinalização sem efeito.
  - **Isolamento:** uma issue bloqueada não trava a fila — `keep_task` já pula
    issues com `need_human`, de modo que as demais seguem sendo processadas.

### Alterado

- **`src/__main__.py::call_agent`** passa a admitir a execução pelo limitador
  (`_admit_circuit_break`) **antes** de `_dispatch_with_recovery`, no mesmo
  padrão fail-closed do gate de composição (#308); `main` ganha o gate de
  capacidade de label após `check_access` e antes de `board_startup_sync`.

### Documentação

- Novo runbook do operador
  [`doc/runbook/limitador-reexecucoes-agente.md`](doc/runbook/limitador-reexecucoes-agente.md),
  com a distinção inequívoca **cooldown × limitador**, formato da configuração,
  semântica da janela, o que acontece em um bloqueio, como retomar uma issue e
  os eventos de observabilidade.
- `README.md` ganhou a seção "Limitador de reexecuções por contexto
  (`agent_circuit_break`)" e registrou `.pipe/agentCircuitBreak.json` na tabela
  de arquivos protegidos (`PROTECTED_PATHS`).

## [1.18.0] - 2026-10-01

### Adicionado

- **Composição em camadas do prompt e do contexto entregues ao agente**
  (issue #308). O conteúdo entregue ao agente passa a ser separado em quatro
  camadas por responsabilidade, cada uma com **origem única** (RN-04), e cada
  execução recebe apenas o que é relevante à tarefa corrente — sem repetir
  material invariável e **sem remover nenhum guardrail de segurança nem
  comportamento de workflow**:
  - Novo módulo `src/core/composition.py` com o inventário auditável das regras
    por camada (`layer_inventory`), a prova de ausência de duplicidade entre as
    camadas sempre carregadas (`find_duplicated_rules`), o gate de referência
    sob demanda (`on_demand_references` / `allowed_commands`), a resolução única
    do nome da branch (`resolve_branch_name`), a verificação das instruções
    obrigatórias (`check_required_instructions`) e a medição por execução
    (`compose_measurement`).
  - **Camadas:** política invariável (guardrails, manual `@---`, estrutura do
    `-body.md`, criação de issues, git flow) e contexto do projeto (metadados e
    papéis humanos) vivem **só** no steering `.kiro/steering/esteira.md`
    (sempre carregado); workflow da etapa (objetivo/passos/git/transição) e
    dados da tarefa (título, caminhos, branch resolvido) compõem o **prompt
    dinâmico** enxuto e específico da execução.
- **Referência sob demanda do manual de comandos `@---`.** O manual deixou de
  ser embutido no prompt dinâmico (antes sempre incluído por `annotations_doc()`)
  e passa a entrar na composição **apenas** quando a etapa permite ao menos um
  comando de anotação. O gate é derivado da nova chave opcional
  `allowed-commands` por coluna (ausente ⇒ conjunto completo de comandos,
  comportamento anterior).
- **Contrato observável de carregamento das instruções obrigatórias
  (fail-closed).** Antes de acionar o agente, `call_agent`
  (`src/__main__.py`) verifica o steering obrigatório e emite um **registro de
  medição por execução** (`composicao_medicao`, INFO) com `caracteres`,
  `palavras`, `linhas` por camada, `total_sempre_carregado`,
  `referencias_sob_demanda_incluidas`, `tokens_entrada` e
  `instrucoes_obrigatorias_carregadas`. Sem o contexto obrigatório, o agente
  **não** é acionado (`instrucoes_obrigatorias_carregadas: false` + motivo;
  evento `composicao_fail_closed`). O adapter `kiro-cli` não expõe tokens de
  entrada: `tokens_entrada` é `null`, sem falhar.
- **Resolução única do nome da branch por execução.**
  `composition.resolve_branch_name(branch_pattern, data)` resolve o nome **uma
  única vez** e o reutiliza idêntico em todos os blocos que o citam (criação e
  merge/PR). Marcador não resolvível com os dados da tarefa levanta
  `ConfigError` nomeando o marcador — **nenhum** nome parcialmente resolvido é
  emitido.

### Alterado

- **`build_prompt` (`src/core/agent.py`)** deixou de embutir o manual `@---`
  completo e condensou a prosa invariável do bloco de diretório; a política
  completa fica no steering. A medição determinística na fixture canônica
  (`create-merge`, caminhos normalizados) comprova **redução real** (RN-08): o
  conteúdo estático do prompt dinâmico fica ≥ 40% menor e o total sempre
  carregado (prompt + steering) ≥ 20% menor — não é transferência de texto
  entre camadas.
- **Steering (`src/core/context_generator.py`)** perdeu o exemplo redundante de
  nome de branch (o nome agora é resolvido pelo motor a partir do
  `branch_pattern`), mantendo o manual `@---` e a estrutura do `-body.md` com
  **origem única** no steering.
- **Validação do `pipe.yml` (`src/core/config.py`)** passa a aceitar a chave
  opcional `allowed-commands` por coluna (lista de nomes de comando de
  anotação).

### Detalhes

- **Capacidades consolidadas, não reinventadas:** `target-prompt`/`step-prompt`
  separados, `branch_pattern` por flow, metadados de `project` no steering e o
  prompt de continuidade já existiam parcialmente; a entrega os **formaliza**
  sob o contrato de camadas e medição, sem alterar seu comportamento observável.
- **Contexto persistente protegido:** o steering `.kiro/steering/esteira.md`
  permanece em `PROTECTED_PATHS` e é reescrito em divergência por
  `ensure_steering_integrity` — nunca gravável pelo agente (RN-02/CA-14).
- **Fora de escopo desta entrega:** definição do conteúdo dos contextos de
  responsabilidade do operador, escolha de tecnologia/arquitetura interna ou de
  um arquivo canônico único de instruções, suporte a adapters além do atual,
  múltiplos repositórios por agente, conversão de palavras/tokens em valor
  financeiro e baseline operacional de falhas/tempo (toda meta é de redução
  **estrutural**).
- Contrato técnico e tabela completa de chaves em
  `doc/architecture/composicao-camadas-prompt-contexto/contrato.md`.

## [1.17.0] - 2026-10-01

### Adicionado

- **Retirada segura de colunas de board com migração, bloqueio, retomada e
  evidência** (issue #305). A reconciliação estrutural (startup / full sync)
  passa a tratar a retirada de uma coluna da configuração como operação
  protegida, pelo ciclo **validar → drenar → confirmar vazio → contrair**, para
  nunca deixar issues sem classificação:
  - Novo **núcleo de decisão** `src/core/column_withdrawal.py`: detecta colunas
    publicadas no board remoto ausentes da configuração (candidatas à retirada),
    classifica a origem por leitura remota, valida o destino, drena todas as
    issues ao destino relendo até confirmar origem vazia e só então contrai.
    Coluna vazia é retirada direta (sem destino), confirmada por leitura remota
    imediatamente anterior. A política fica no núcleo, não na camada de acesso
    ao provedor.
  - **Falha e retomada:** indisponibilidade, penalidade de rate limit ou
    encerramento preservam o estado parcial (issues já movidas no destino,
    restantes na origem, origem ainda publicada); a próxima execução deriva o
    trabalho restante **do estado remoto**, sem journal nem estado persistente
    paralelo. Ausência de progresso encerra a tentativa como `interrupted` /
    `sem_progresso`, sem laço infinito.
  - **Isolamento:** cada coluna retirada e cada board é tratado de forma
    independente; bloqueio ou interrupção de uma origem não impede a
    reconciliação das demais.
- **Mapa opcional de destinos por board** `boards.<board>.column-migrations`
  (`src/core/config.py`: `validate_column_migrations`). Associa cada coluna
  retirada a exatamente uma coluna de destino do mesmo board. A validação de
  **forma** exige um mapa de strings não-vazias (origem → destino); tipo
  diferente, chave/valor vazio, nulo ou não-string é rejeitado com `ConfigError`
  citando `boards.<board>.column-migrations` e a entrada que falhou. A ausência
  do mapa é válida (compatibilidade: boards sem retirada de coluna mantêm o
  comportamento estrutural vigente). A validação **semântica** (destino existir
  no mesmo board, ser diferente da origem e não ser outra coluna também em
  retirada no ciclo) ocorre em tempo de reconciliação.
- **Evidência estruturada por tentativa:** cada origem avaliada emite
  exatamente um evento `column_migration_attempt` no log diário
  (`logs/<data>.json`), com os campos `board`, `source`, `destination`,
  `initial_count`, `moved_count`, `remaining_count`, `result` e `reason`.
  `completed` em nível **INFO**; `blocked` e `interrupted` em **WARNING**, com
  mensagem auto-contida (board, origem e motivo). A evidência é consultável
  **sem** abrir arquivos internos protegidos (`.pipe/...`) e não vaza corpo de
  issue, credenciais nem estado protegido. Motivos padronizados de bloqueio:
  `destino_ausente`, `destino_inexistente`, `destino_mesmo_board_invalido`,
  `destino_e_origem`, `destino_tambem_retirado`; de interrupção: `sem_progresso`.
- **Primitivas estruturais no `BoardPort` / `Board`** (`src/core/board.py`):
  `prepare_structure`, `contract_column` e `remote_columns` (com defaults no-op
  no port para não quebrar adapters/fakes existentes); `Board` expõe
  `prepare_boards`, `contract_column`, `remote_columns` e o helper
  `_boards_from_config` (reaproveitado por `sync_boards`).

### Alterado

- **Preparação de estrutura remota agora é estritamente aditiva**
  (`src/adapters/github_board.py`): `prepare_structure` cria boards/campo
  `Status`/colunas ausentes preservando **todas** as opções remotas existentes
  e seus ids (inclusive as em vias de retirada) e **nunca** remove opção. A
  remoção de opção passa a ser uma operação distinta — `contract_column` —, que
  substitui a lista exata preservando os ids que permanecem e faz verificação
  remota logo após a contração (janela residual, RNF-11). `remote_columns` lê as
  opções publicadas do campo `Status`.
- **Ordem do full sync** (`src/__main__.py::board_startup_sync`): a estrutura
  remota passa a ser **reconciliada antes** de o snapshot ser gravado. O
  snapshot reflete a estrutura **efetiva** (inclui origens retidas ainda
  publicadas) e os diretórios locais dessas origens são preservados; uma falha
  genérica de reconciliação **não** sobrescreve o snapshot anterior
  (`PenaltyException` é tratada com `sleep`).

### Detalhes

- **Fora de escopo desta entrega:** migração de issues entre boards diferentes,
  destino diferente por issue, arquivamento/fechamento como destino, limite de
  WIP por coluna, fluxo de autorização/aprovação para retirar coluna, SLA de
  conclusão, rollback dos itens já movidos após falha parcial e limpeza
  automática de issues que já estavam sem `Status` antes da tentativa.
- **Limitação documentada (RNF-11):** o provedor não oferece remoção condicional
  atômica de opção nem trava contra escritor externo; a janela residual entre a
  confirmação de vazio e a contração é mínima e verificada logo após contrair,
  mas não é eliminável apenas pela aplicação. Um item que apareça sem `Status`
  nessa janela é reconciliado para o destino explícito quando inequívoco.
- Documentação pública: nova seção "Retirada segura de colunas
  (`column-migrations`)" no `README.md` e novo runbook
  `doc/runbook/retirada-colunas.md` (declaração do destino, ciclo de vida do
  mapa, evidência nos logs, diagnóstico e garantias/limites).

## [1.16.0] - 2026-10-01

### Adicionado

- **Classificação de resultado de execução por canais estruturados** (issue
  #303). Novo módulo `src/core/execution.py` com `ExecutionResult` e as classes
  de resultado alinhadas à ADR #217 (`doc/architecture/retry-kiro-cli/`):
  `SUCEDIDO`, `FALHA`, `UNKNOWN_OUTCOME`, `DEFINITE_NOT_STARTED` e
  `FALHA_PERSISTENTE`. Cada resultado preserva output, causa, origem do canal,
  `request_id` e `session_id` para auditoria e continuidade.
- **Tratamento seguro de interrupção transitória** no despacho da execução
  (`src/__main__.py::call_agent` via `_dispatch_with_recovery`), conforme a ADR
  #217 (política *fail-closed*, sem a fronteira idempotente da seção 4):
  - `UNKNOWN_OUTCOME` (dispatch failure / `InternalServerError` após output
    parcial / timeout): **uma única invocação por entrega**, sem retry inline
    nem backoff; evidências preservadas; reconciliação e eventual retomada de
    sessão ficam a cargo do loop normal;
  - `DEFINITE_NOT_STARTED` (não-inicialização comprovada mecanicamente, ex.:
    `kiro-cli` ausente no PATH): **único** caso de retry inline, com backoff
    crescente até o limite; esgotado o limite, o resultado é falha persistente,
    sem laço infinito.
- **Parâmetros de configuração `retry.*`** (opcionais) no `pipe.yml`, aplicáveis
  **apenas** ao caso seguro `DEFINITE_NOT_STARTED` (`src/core/config.py`:
  `RetryConfig`, `validate_retry`, `resolve_retry`): `retry.max_tentativas`
  (inteiro > 0, default 3), `retry.backoff_inicial_seg` (inteiro ≥ 0, default
  30) e `retry.backoff_fator` (número ≥ 1.0, default 2.0). Ausência da chave
  aplica os defaults; valores fora das restrições são rejeitados por
  `ConfigError` nomeando a chave.
- **Resolução dos caminhos de apoio por item** (issue #303). Novo módulo
  `src/core/support_paths.py`: `resolve_support_paths` separa caminhos
  existentes de ausentes **sem cancelar o lote** — um template inexistente
  deixa de cancelar as demais chamadas de ferramenta válidas. Config e código
  passam a apontar para a mesma fonte única `contexts/templates/`.

### Alterado

- **Detecção de falha deixa de escanear a narrativa do agente**
  (`src/adapters/kiro_cli_agent.py::_detect_failure`). A classificação de
  sucesso/falha passa a considerar **apenas** canais estruturados da ferramenta
  de execução (`[exit-code: N≠0]`, `[TIMEOUT]`, `[ERRO]`, saída de erro
  estruturada), alinhando-se ao mesmo princípio já adotado na detecção de rate
  limit. Um output cuja prosa cita uma frase de erro (ex.: "Kiro is having
  trouble responding"), mas sem sinal estruturado, agora é classificado como
  **sucesso** — fim do falso positivo histórico que inflava a métrica de falha.
  A ausência de sinal estruturado é sucesso.
- **Contexto do sistema sempre derivado da configuração vigente**
  (`src/core/context_generator.py`). O artefato legado
  `.kiro/agents/pipe_context.json` deixa de ser gerado e é removido em
  `generate_context`/`ensure_steering_integrity`, para que nenhum artefato
  congelado com tabelas vazias tenha precedência sobre o contexto derivado da
  config nem gere aviso de conflito.

### Corrigido

- Referência de exemplo a identificador de modelo inexistente no `README.md`
  (`model: claude-sonnet-4-20250514`) corrigida para o válido
  `claude-sonnet-5`.

### Detalhes

- A fronteira idempotente completa da seção 4 da ADR #217 (chave estável de
  operação, journal/outbox durável, interposição real de commit/push/movimento
  de coluna, verificação de pós-condição) e, por consequência, o retry
  automático de execução possivelmente parcial (`UNKNOWN_OUTCOME`) **não** fazem
  parte desta entrega — ficam para entrega dedicada futura, pois exigiriam
  redefinir o modelo de execução e o mecanismo de auto-aprovação de ferramentas.

## [1.15.0] - 2026-10-01

### Alterado

- **Sincronização única (#304):** a descoberta remota (down) passa a ter um
  único caminho (`sync_remote`) que, a cada acionamento, reconcilia o board
  inteiro contra o estado local — criações (`create-down`), modificações
  (`change-down`), poda por ausência (`delete-down`) e dependências de bloqueio
  —, sem corte por data da última atualização e sem um acionamento diário
  separado. Toda reconciliação vinda do board inclui as dependências
  (`change-down` é sempre `fullsync=True`): deixa de existir reconciliação "só
  propriedades".
- Um item novo no board passa a existir localmente na sincronização seguinte,
  sem esperar o antigo evento diário; dependências alteradas no board são
  reconciliadas em toda sincronização.

### Removido

- Caminho de sincronização reduzida/incremental: eliminado o corte por
  `last_board_update` como critério do que reconciliar.
- `Board.detect_board_changes` (o antigo caminho "completo") e o acionamento
  diário em `__main__` (`last_full_sync`). A função de setup de estrutura +
  primeira sincronização foi renomeada de `board_full_sync` para
  `board_startup_sync`.
- `list_issues_since` do `BoardPort`, do `Board` e do adapter `github_board`.
- O campo `last_board_update` do snapshot: descontinuado. Snapshots legados que
  ainda o contenham carregam sem erro (campo ignorado e removido na reescrita).

### Observabilidade

- Toda sincronização de board emite um log no contrato mínimo:
  `sincronizacao board=<id> criados=<n> atualizados=<n> removidos=<n> resultado=<ok|limite|erro>`,
  sem qualificador de modo e sem vazar corpo de issue, caminho protegido ou
  credencial.

### Robustez

- O fetch do board é atômico: uma leitura interrompida por limite de requisições
  (`PenaltyException`) propaga antes de qualquer decisão de poda — nunca é
  interpretada como ausência de itens (log `resultado=limite`, nenhum
  `delete-down`).

## [1.14.1] - 2026-09-24

### Corrigido

- A abordagem de 1.14.0 (tratar itens arquivados como gatilho de `delete-down`)
  era **inócua**: o GitHub ProjectV2 REMOVE itens arquivados da connection
  `items` — eles não retornam com `isArchived=true` —, então o código que
  "superficializava arquivadas" em `list_issues`/`list_issues_since` nunca era
  exercido. Verificado no board: `items(first:100)` não devolve a issue
  arquivada. Resultado: o sync incremental (`sync_remote`) continuava sem podar
  arquivadas, e boards `parallel:false` seguiam congelando até o full sync
  diário.
- Correção correta: `sync_remote` passa a detectar issues presentes no snapshot
  mas AUSENTES do fetch atual e enfileira `delete-down` (arquivadas ou
  deletadas), mesma lógica que já existia só na varredura completa
  (`detect_board_changes`). Agora a poda ocorre no ciclo seguinte ao
  arquivamento.
- Revertidas as mudanças inócuas de 1.14.0 em
  `GitHubBoardAdapter.list_issues`/`list_issues_since` e
  `Board.detect_board_changes`.

### Detalhes

- Custo de API zero: o fetch completo (`list_issues`) já era feito a cada ciclo
  por dentro de `list_issues_since`; `sync_remote` passa a usá-lo diretamente,
  derivando o subconjunto modificado (`updated_at > since`) para create/change e
  o conjunto completo para a detecção de ausência.
- O fetch é atômico (rate limit levanta `PenaltyException` em vez de devolver
  página parcial), então uma leitura truncada não gera falso-positivo de
  deleção — mesma garantia da varredura completa.

## [1.14.0] - 2026-09-24

### Adicionado

- Itens arquivados no board agora servem como gatilho explícito de `delete-down`
  fora da varredura completa (startup/diária). O adapter do GitHub deixa de
  descartar itens `isArchived` e passa a superficializá-los como uma `Issue`
  leve (`archived=True`, sem coluna/labels/deps — não são reinseridos no board
  local). As camadas de sync (`sync_remote` incremental por-ciclo e
  `detect_board_changes` na varredura completa) enfileiram `delete-down` quando
  o id ainda existe no snapshot, e ignoram quando já não existe (idempotente).

### Alterado

- Para o caso comum de término (issue arquivada), a poda do snapshot deixa de
  depender da heurística frágil "ausente do fetch" (sujeita a falso-positivo de
  deleção sob fetch parcial/paginação truncada) e passa a usar o sinal positivo
  de arquivamento. A detecção por ausência permanece na varredura completa para
  cobrir deleções reais (issue removida do project).

## [1.13.2] - 2026-09-22

### Corrigido

- O auto-advance de uma issue na coluna `todo` (`keep_task`) agora respeita os
  bloqueios. Antes, o guard `_is_blocked` (que verifica `/blocked_by` e
  `/need_human` no body) só era aplicado às colunas com agente; uma issue
  bloqueada parada no `todo` era avançada mesmo assim, ignorando a fila ordenada
  por bloqueios — trazendo a issue bloqueada e deixando a bloqueante no `todo`.
  Agora issues bloqueadas no `todo` são puladas, e o auto-advance segue para a
  próxima issue elegível (tipicamente a bloqueante), preservando a ordem da fila.

## [1.13.1] - 2026-09-21

### Corrigido

- Os logs do sidecar `dind` deixam de poluir a saída do `docker compose up`
  (foreground do `make`). Adicionado `attach: false` ao serviço `dind` no
  `docker-compose.yml`: o daemon continua rodando normalmente e seus logs
  seguem acessíveis sob demanda via `docker compose logs dind`, mas não são mais
  agregados ao log da esteira. Requer Compose v2.20+.

## [1.13.0] - 2026-09-17

### Adicionado

- Toolchain de dev/test para os agentes dentro do container (Opção B —
  Docker-in-Docker). O container do agente agora consegue subir as stacks
  `dev`/`qa` do produto (docker compose) e rodar ITs Testcontainers, que antes
  falhavam com "Could not find a valid Docker environment".
  - Novo sidecar `dind` (`docker:*-dind`, privileged) no `docker-compose.yml`:
    daemon Docker isolado; o serviço `pipe` fala com ele via
    `DOCKER_HOST=tcp://127.0.0.1:2375` compartilhando o network namespace
    (`network_mode: service:dind`), o que também torna as portas das stacks
    aninhadas alcançáveis em `localhost` sem alterar os scripts do produto.
  - Volume `dind-storage` (`/var/lib/docker` do dind) persiste imagens e volumes
    das stacks entre execuções — ambiente de desenvolvimento/teste "real".
  - `compose.dev.yml` compartilha o repo (bind mount) com o `dind` no mesmo
    path, para os bind mounts das stacks aninhadas resolverem.
  - Dockerfile passa a embutir, com versões pinadas em `docker/versions.env`:
    cliente `docker` (estático), plugins `compose` v2 e `buildx`, `jq`, JDK
    Temurin 21 e Apache Maven.

### Segurança

- O daemon Docker fica isolado no sidecar `dind` (privileged) em vez de expor o
  socket do host ao agente — o raio de dano das operações do agente fica contido
  no sidecar. Homologação não é coberta (roda fora de containers, no host).

## [1.11.0] - 2026-08-22

### Alterado

- Renomeado o mecanismo de roteamento de agente de `agent-level` para
  `agent-hub`, com sufixo livre (não mais restrito a níveis `low/medium/high`;
  pode representar função, profundidade ou qualquer critério):
  - Label no board: `agent-level-<nível>` → `agent-hub-<valor>`.
  - Comando no body (bloco `@---`): `/agent_level <nível>` →
    `/agent-hub-<valor>` (token único, no mesmo formato do label, análogo a
    `/need_human`).
  - Chave de configuração da coluna: `override-agent` → `agent-hub`.
  - Identificadores internos: `AGENT_LEVEL_PREFIX` → `AGENT_HUB_PREFIX`,
    `agent_level()` → `agent_hub()`, campo `IssueCommands.agent_level` →
    `agent_hub`.

### Removido

- Removida a migração automática one-shot `migrate_agent_level_labels`
  (renomeada temporariamente para `migrate_agent_hub_labels`) e sua chamada no
  `board_full_sync`. Issues legadas com o comando/label antigo devem ser
  corrigidas manualmente onde necessário.

### Segurança e compatibilidade

- **Breaking change (MINOR):** `pipe.yml` que use `override-agent` deve migrar
  para `agent-hub`; bodies que usem `/agent_level <nível>` devem migrar para
  `/agent-hub-<valor>`. Sem migração automática — correção manual.

## [1.10.1] - 2026-08-20

### Alterado

- Faxina pontual das branches não mergeadas do repositório (#73/#74/#75/#76):
  removidas do remoto as 12 branches de resíduo já integrado a `main`/`epic`,
  8 branches órfãs de tarefas arquivadas, e a branch de nomenclatura antiga
  `feature/1-1-rodar_no_docker`; consolidada a duplicata das issues #46/#47.
  `temp-hotfix23-merge` e `temp-hotfix24-merge` foram preservadas
  deliberadamente, pendentes de decisão sobre manter o histórico de
  incidente em `main`/`epic`.
- Sem mudança de código de produto: a entrega é operação de
  `git branch`/`git push --delete` sobre o remoto, sem alteração de
  comportamento da esteira. Não há mudança de processo nem automação de
  encerramento de branch — a demanda era pontual.
- Adicionado runbook de homologação específico
  (`doc/runbook/homologacao-branches-nao-mergeadas.md`), referenciado no
  README, cobrindo validação do estado das branches e subida do ambiente
  Docker Compose com o código mesclado.

### Segurança e compatibilidade

- Sem mudança de schema, `pipe.yml` ou comportamento em runtime; o bump é
  PATCH.
- Nenhuma branch de tarefa ativa foi removida; a remoção seguiu estritamente
  as regras de negócio confirmadas (resíduo comprovado ou ausência de
  issue/razão que justifique a branch).

## [1.10.0] - 2026-08-20

### Adicionado

- Resolução determinística do body de issues (C1, US-03/#140): o core aceita
  apenas associação inequívoca, recusa zero ou múltiplos candidatos e registra
  artefatos órfãos sem alterar o board (#146/#147).
- Sanitização das quatro formas de auto-referência (C2, US-01/#138) em
  `parent`, `children`, `blocked_by` e `blocks`, antes de qualquer chamada ao
  provider; listas mistas preservam as relações válidas (#143).
- Isolamento de mensagens-veneno (C3, US-02/#139): classificação de erros,
  tentativas limitadas, rotação da fila e dead-letter persistente por item,
  eliminando o bloqueio global por uma única mudança (#144/#145).
- Guarda de integridade do snapshot (C4, US-04/#141): `SnapshotGuard` compara
  o conteúdo antes/depois da execução do agente, restaura atomicamente
  alterações indevidas e preserva as permissões originais (#149).
- Proteção de instância única no ciclo de vida da esteira (C5, US-05/#142).
  `main()` adquire o `InstanceLock` antes de `startup()` e recusa a execução
  concorrente com *fail-fast*, informando os metadados do detentor. A liberação
  em `finally` cobre término normal, sinais e falhas (#150/#151/#152/#196).
- Suítes de regressão do incidente #97, incluindo colisão de body,
  auto-referência, mensagem-veneno, restauração de snapshot e concorrência real
  entre processos.

### Corrigido

- Incidente Parent Recursivo (#97/#104): as cinco lacunas C1–C5 que permitiram
  substituição indevida de conteúdo, 225 repetições e paralisação global por
  2h37 foram corrigidas e homologadas em conjunto. O incidente foi
  reclassificado como **resolvido** em 20/08/2026.
- Preservação do modo do arquivo na restauração do `SnapshotGuard`: a guarda
  não altera mais as permissões do snapshot restaurado (#149/PR #194).
- Reconciliação da defasagem `epic` → `main` (#196): as integrações de
  `InstanceLock`, sua suíte concorrente e `SnapshotGuard`, antes presentes
  apenas na branch agregadora, foram promovidas para a branch executada em
  produção.
- Remoção automática de sub-issues propagadas pelo GitHub Projects V2 para
  boards do parent quando o item chega sem `Status`. O pós-hook consulta
  `projectItems`/`fieldValues` via GraphQL e remove por
  `deleteProjectV2Item`; o project de origem é sempre preservado.
- Proteção no `create-down` contra arquivos e entradas duplicadas para itens
  sem coluna, exigindo prova de presença em outro board configurado.
- Detecção de coluna remota vazia como divergência e reconciliação com a coluna
  conhecida do snapshot.
- `create_issue` passa a aplicar fallback para a primeira coluna do project,
  com warning, quando a coluna solicitada não existe.
- Nova primitiva `remove_from_board` na porta de board, implementada no adapter
  GitHub com `deleteProjectV2Item`.

### Segurança e compatibilidade

- Sem mudança incompatível de schema ou de `pipe.yml`; o bump é MINOR.
- `sync.max_attempts` permanece opcional e assume o valor seguro documentado
  quando ausente.
- O lock é local ao filesystem compartilhado; coordenação entre hosts que não
  compartilham o mesmo estado continua fora de escopo.
- A guarda desta versão cobre snapshots. Sandbox completo do filesystem,
  replay automático de dead-letter e captura parcial de chat em timeout
  permanecem melhorias separadas.
- Itens multi-board com `Status` definido são preservados; a remoção automática
  se restringe a itens propagados sem coluna.
- Resíduos de sub-issues materializados antes da correção não são apagados
  automaticamente e requerem limpeza manual com a esteira parada.

### Validação e disponibilidade

- C1–C5 foram integradas em `main`; as stories #138–#142 foram
  concluídas/encerradas e a homologação do épico #104 foi aprovada em
  20/08/2026.
- A segunda rodada de pré-produção registrou 1121 testes aprovados, 28
  ignorados e 1 xpassed. As 24 falhas observadas eram idênticas em
  `origin/main` e foram classificadas como pré-existentes, fora do escopo.
- A validação estrutural de Docker registrou 213 testes aprovados; build e
  smoke test reais não puderam ser repetidos no sandbox da segunda rodada por
  ausência de Docker. Essa limitação foi explicitada e aceita na homologação.
- A correção de sub-issues propagadas foi homologada separadamente em
  19/08/2026; disponibilidade depende do veículo #88/PR #102 e do deploy.

Detalhes:

- [`doc/changelogs/104-pre-producao-c1-c5-integradas.md`](doc/changelogs/104-pre-producao-c1-c5-integradas.md)
- [`doc/product/confiabilidade-parent-recursivo/post-mortem.md`](doc/product/confiabilidade-parent-recursivo/post-mortem.md)
- [`doc/changes/88-sub-issues-propagadas-entre-boards.md`](doc/changes/88-sub-issues-propagadas-entre-boards.md)
