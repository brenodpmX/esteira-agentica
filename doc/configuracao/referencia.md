# Referência de configuração do `pipe.yml`

Esta é a fonte canônica de todas as chaves do `pipe.yml`, o arquivo que define
a esteira. Cada chave aparece uma vez, com o mesmo conjunto de campos:

- `descricao`: o que a chave controla.
- `tipo`: `string`, `inteiro`, `booleano`, `lista` ou `mapa`.
- `obrigatoriedade`: `obrigatória` ou `opcional`.
- `default`: valor assumido quando a chave falta.
- `valores_aceitos`: faixa ou lista de valores válidos.
- `efeito_ausencia`: o que acontece quando a chave não é informada.
- `exemplo`: o valor num uso mínimo.

Trechos entre `<` e `>` no nome da chave são escolhidos por você: `<board_id>`,
`<column_id>`, `<flow_id>`, `<repo_id>`, `<platform_id>` e `<agent_id>` são ids
livres; `<valor>`, `<condicao>` e `<origem>` estão explicados na própria chave.
Uma chave opcional só vale quando o bloco que a contém existe.

A validação roda na inicialização. Valor fora do aceito encerra a esteira com
uma mensagem que cita o caminho da chave, antes de qualquer alteração no board.

Um `pipe.yml` mínimo e válido está na seção Configuração do
[`README.md`](../../README.md#configuração); exemplos completos estão em
[`exemplos/`](../../exemplos/minimalista/pipe.yml).

## Geral

### `sleep`

```text
chave: sleep
descricao: Pausa, em segundos, entre dois ciclos da esteira quando não há nada para sincronizar nem tarefa para executar. Havendo trabalho, o ciclo seguinte começa sem pausa.
tipo: inteiro
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: número > 0; aceita decimal (ex.: 0.5)
efeito_ausencia: a validação falha com 'pipe.yml: campo sleep é obrigatório'
exemplo: 60
```

### `agent_timeout_seg`

```text
chave: agent_timeout_seg
descricao: Tempo máximo, em segundos, de uma única execução do agente. Estourado o tempo, a execução é encerrada e registrada como timeout.
tipo: inteiro
obrigatoriedade: opcional
default: 3600
valores_aceitos: inteiro > 0; vale para todas as colunas e boards
efeito_ausencia: cada execução pode durar até 3600 segundos (1 hora)
exemplo: 1800
```

## Logs e registros

### `log.dir`

```text
chave: log.dir
descricao: Diretório dos logs diários da esteira e dos logs de cada execução de agente.
tipo: string
obrigatoriedade: opcional
default: logs
valores_aceitos: caminho relativo à raiz da instalação ou absoluto
efeito_ausencia: os logs são gravados em logs/
exemplo: logs
```

### `log.ttl`

```text
chave: log.ttl
descricao: Por quantos dias um arquivo de log é mantido; arquivos mais antigos são apagados na inicialização.
tipo: inteiro
obrigatoriedade: opcional
default: 10
valores_aceitos: inteiro >= 1
efeito_ausencia: logs com mais de 10 dias são apagados
exemplo: 30
```

### `log.level`

```text
chave: log.level
descricao: Nível mínimo das mensagens registradas no log.
tipo: string
obrigatoriedade: opcional
default: INFO
valores_aceitos: TRACE, DEBUG, INFO, WARNING, ERROR (sem diferença de maiúsculas); valor desconhecido vira INFO
efeito_ausencia: o log registra a partir de INFO
exemplo: DEBUG
```

### `registro.retencao_dias`

```text
chave: registro.retencao_dias
descricao: Por quantos dias o registro estruturado de cada execução de agente é mantido. Independe de log.ttl; o expurgo roda na inicialização.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: inteiro > 0; outro campo dentro de registro é rejeitado
efeito_ausencia: nenhum registro de execução é apagado automaticamente
exemplo: 90
```

## Tentativas e sincronização

### `retry.max_tentativas`

```text
chave: retry.max_tentativas
descricao: Quantas vezes a esteira tenta acionar o agente quando há prova de que ele nem começou (ex.: kiro-cli ausente no PATH). Resultado ambíguo nunca é repetido automaticamente.
tipo: inteiro
obrigatoriedade: opcional
default: 3
valores_aceitos: inteiro > 0
efeito_ausencia: até 3 tentativas
exemplo: 5
```

### `retry.backoff_inicial_seg`

```text
chave: retry.backoff_inicial_seg
descricao: Espera, em segundos, antes da segunda tentativa de acionar o agente.
tipo: inteiro
obrigatoriedade: opcional
default: 30
valores_aceitos: inteiro >= 0
efeito_ausencia: espera de 30 segundos antes da segunda tentativa
exemplo: 10
```

### `retry.backoff_fator`

```text
chave: retry.backoff_fator
descricao: Multiplicador aplicado à espera a cada nova tentativa de acionar o agente.
tipo: inteiro
obrigatoriedade: opcional
default: 2.0
valores_aceitos: número >= 1.0; aceita decimal (ex.: 1.5)
efeito_ausencia: a espera dobra a cada tentativa
exemplo: 2
```

### `sync.max_attempts`

```text
chave: sync.max_attempts
descricao: Quantas vezes uma mudança que falhou por erro transitório volta para a fila de sincronização antes de ser separada como falha definitiva.
tipo: inteiro
obrigatoriedade: opcional
default: 3
valores_aceitos: inteiro >= 1
efeito_ausencia: até 3 tentativas por mudança
exemplo: 5
```

## Proteção contra falha repetida de sincronização (sync.circuit_breaker)

### `sync.circuit_breaker.persistence`

```text
chave: sync.circuit_breaker.persistence
descricao: Onde o estado das proteções contra falha repetida de sincronização é guardado.
tipo: string
obrigatoriedade: opcional
default: file
valores_aceitos: file (sobrevive a reinício) | memory (zera a cada reinício)
efeito_ausencia: o estado é guardado em arquivo e sobrevive a reinícios
exemplo: file
```

### `sync.circuit_breaker.escalation_agent`

```text
chave: sync.circuit_breaker.escalation_agent
descricao: Agente acionado uma única vez quando uma issue continua falhando na sincronização depois dos bloqueios previstos, com o erro completo e a instrução de corrigir a issue.
tipo: string
obrigatoriedade: opcional
default: correcao-esteira
valores_aceitos: id de um agente declarado em agents (com contexto preenchido)
efeito_ausencia: a escalação procura o agente correcao-esteira; se ele não existir, a esteira encerra na escalação
exemplo: correcao-esteira
```

### `sync.circuit_breaker.issue.max_failures`

```text
chave: sync.circuit_breaker.issue.max_failures
descricao: Falhas consecutivas de sincronização de uma issue que a bloqueiam temporariamente.
tipo: inteiro
obrigatoriedade: opcional
default: 3
valores_aceitos: inteiro >= 1
efeito_ausencia: a issue é bloqueada após 3 falhas seguidas
exemplo: 3
```

### `sync.circuit_breaker.issue.block_duration`

```text
chave: sync.circuit_breaker.issue.block_duration
descricao: Duração, em segundos, do bloqueio temporário de uma issue.
tipo: inteiro
obrigatoriedade: opcional
default: 300
valores_aceitos: inteiro >= 1
efeito_ausencia: o bloqueio dura 300 segundos
exemplo: 300
```

### `sync.circuit_breaker.issue.max_blocks`

```text
chave: sync.circuit_breaker.issue.max_blocks
descricao: Bloqueios consecutivos de uma issue antes de acionar o agente de escalação.
tipo: inteiro
obrigatoriedade: opcional
default: 3
valores_aceitos: inteiro >= 1
efeito_ausencia: a escalação ocorre no terceiro bloqueio seguido
exemplo: 3
```

### `sync.circuit_breaker.platform.max_blocked_issues`

```text
chave: sync.circuit_breaker.platform.max_blocked_issues
descricao: Quantas issues distintas bloqueadas dentro da janela bloqueiam toda a sincronização com a plataforma.
tipo: inteiro
obrigatoriedade: opcional
default: 5
valores_aceitos: inteiro >= 1
efeito_ausencia: a plataforma é bloqueada com 5 issues bloqueadas na janela
exemplo: 5
```

### `sync.circuit_breaker.platform.block_window`

```text
chave: sync.circuit_breaker.platform.block_window
descricao: Janela, em segundos, usada para contar as issues bloqueadas.
tipo: inteiro
obrigatoriedade: opcional
default: 600
valores_aceitos: inteiro >= 1
efeito_ausencia: janela de 600 segundos
exemplo: 600
```

### `sync.circuit_breaker.platform.block_duration`

```text
chave: sync.circuit_breaker.platform.block_duration
descricao: Duração, em segundos, do bloqueio da plataforma. A esteira continua rodando; só a sincronização com a plataforma é pulada.
tipo: inteiro
obrigatoriedade: opcional
default: 900
valores_aceitos: inteiro >= 1
efeito_ausencia: o bloqueio da plataforma dura 900 segundos
exemplo: 900
```

### `sync.circuit_breaker.half_open.success_threshold`

```text
chave: sync.circuit_breaker.half_open.success_threshold
descricao: Sincronizações bem-sucedidas, após o fim de um bloqueio, para voltar ao funcionamento normal. Uma falha nesse período bloqueia de novo.
tipo: inteiro
obrigatoriedade: opcional
default: 2
valores_aceitos: inteiro >= 1
efeito_ausencia: 2 sucessos encerram o período de teste
exemplo: 2
```

## Limitador de reexecuções (agent_circuit_break)

### `agent_circuit_break.executions`

```text
chave: agent_circuit_break.executions
descricao: Máximo de execuções do agente para a mesma issue na mesma coluna dentro da janela. A execução excedente não começa: a issue recebe need_human e um comentário explicando o bloqueio.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: inteiro >= 1; obrigatória quando o bloco agent_circuit_break existe
efeito_ausencia: sem o bloco, nenhuma execução é bloqueada por repetição
exemplo: 5
```

### `agent_circuit_break.window`

```text
chave: agent_circuit_break.window
descricao: Janela, em segundos, em que as execuções da mesma issue na mesma coluna são contadas.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: inteiro >= 1; obrigatória quando o bloco agent_circuit_break existe
efeito_ausencia: sem o bloco, nenhuma execução é bloqueada por repetição
exemplo: 3600
```

## Segurança

### `safety.cross_board_parent_links`

```text
chave: safety.cross_board_parent_links
descricao: Permite suspender a criação de novos vínculos mãe/filha entre issues de boards diferentes, sem reiniciar a esteira. A chave é relida do arquivo a cada vínculo.
tipo: string
obrigatoriedade: opcional
default: enabled
valores_aceitos: enabled | suspended (exatamente assim)
efeito_ausencia: novos vínculos entre boards são permitidos
exemplo: suspended
```

## Projeto

### `project.name`

```text
chave: project.name
descricao: Nome do projeto, repassado aos agentes como contexto.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: texto não vazio
efeito_ausencia: a validação falha
exemplo: Meu projeto
```

### `project.summary`

```text
chave: project.summary
descricao: Resumo do projeto em uma ou duas frases, repassado aos agentes como contexto.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: texto não vazio
efeito_ausencia: a validação falha
exemplo: Esteira de entrega do produto X.
```

### `project.humans.name`

```text
chave: project.humans.name
descricao: Nome de uma pessoa com papel no fluxo, informado aos agentes. Cada item da lista project.humans tem name e role.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: texto não vazio; obrigatória em cada item de project.humans
efeito_ausencia: os agentes não recebem a lista de papéis humanos
exemplo: Ana
```

### `project.humans.role`

```text
chave: project.humans.role
descricao: Papel da pessoa no fluxo (ex.: quem aprova escopo).
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: texto não vazio; obrigatória em cada item de project.humans
efeito_ausencia: os agentes não recebem a lista de papéis humanos
exemplo: Aprova o escopo das entregas
```

## Git

### `git.repo.main`

```text
chave: git.repo.main
descricao: Endereço SSH do repositório principal, clonado em repo/main. É o repositório usado pelos boards que não declaram repo.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: URL SSH do GitHub (git@github.com:org/repo.git); git.repo precisa de ao menos uma entrada
efeito_ausencia: sem nenhuma entrada em git.repo a validação falha
exemplo: git@github.com:minha-org/meu-repo.git
```

### `git.repo.<repo_id>`

```text
chave: git.repo.<repo_id>
descricao: Repositório adicional, clonado em repo/<repo_id>. Um board passa a usá-lo com boards.<board_id>.repo.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: URL SSH do GitHub; <repo_id> é livre
efeito_ausencia: só os repositórios declarados são clonados; diretórios de repositórios removidos da lista são apagados de repo/
exemplo: git@github.com:minha-org/outro-repo.git
```

### `git.flow.base`

```text
chave: git.flow.base
descricao: Branch base do repositório, usada quando um flow não declara create ou merge.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: nome de branch existente
efeito_ausencia: a validação falha
exemplo: main
```

### `git.flow.<flow_id>.prefix`

```text
chave: git.flow.<flow_id>.prefix
descricao: Prefixo das branches do flow, exibido aos agentes no contexto do sistema.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: texto; cada flow precisa de prefix ou name
efeito_ausencia: sem prefix e sem name, a validação falha
exemplo: feature/
```

### `git.flow.<flow_id>.name`

```text
chave: git.flow.<flow_id>.name
descricao: Nome legível do flow. Atende à exigência de prefix ou name.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: texto; cada flow precisa de prefix ou name
efeito_ausencia: sem prefix e sem name, a validação falha
exemplo: Funcionalidade
```

### `git.flow.<flow_id>.branch_pattern`

```text
chave: git.flow.<flow_id>.branch_pattern
descricao: Modelo do nome da branch de trabalho de cada issue do flow.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: texto não vazio; marcadores {id} e {slug} da issue
efeito_ausencia: a validação falha
exemplo: feature/{id}-{slug}
```

### `git.flow.<flow_id>.create`

```text
chave: git.flow.<flow_id>.create
descricao: Branch de onde as branches do flow nascem.
tipo: string
obrigatoriedade: opcional
default: valor de git.flow.base
valores_aceitos: nome de branch existente
efeito_ausencia: as branches nascem de git.flow.base
exemplo: main
```

### `git.flow.<flow_id>.merge`

```text
chave: git.flow.<flow_id>.merge
descricao: Branch de destino dos pull requests do flow.
tipo: string
obrigatoriedade: opcional
default: valor de git.flow.base
valores_aceitos: nome de branch existente
efeito_ausencia: os pull requests apontam para git.flow.base
exemplo: main
```

## Agentes

### `agents.<platform_id>.<agent_id>.name`

```text
chave: agents.<platform_id>.<agent_id>.name
descricao: Nome de apresentação do agente, usado no prompt e nas assinaturas. Cada agente exige o contexto contexts/<platform_id>/<agent_id>.md preenchido.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: texto não vazio; <platform_id> suportado: kiro-cli
efeito_ausencia: a validação falha
exemplo: Assistente
```

### `agents.<platform_id>.<agent_id>.model`

```text
chave: agents.<platform_id>.<agent_id>.model
descricao: Modelo de IA usado pelo agente, repassado à plataforma.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: identificador aceito pela plataforma (ex.: claude-sonnet-5, claude-haiku-4.5, auto)
efeito_ausencia: a plataforma usa o próprio modelo padrão
exemplo: claude-sonnet-5
```

### `agents.<platform_id>.limits.timezone`

```text
chave: agents.<platform_id>.limits.timezone
descricao: Fuso usado para virar os períodos do limite de consumo.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: nome de fuso IANA (ex.: America/Sao_Paulo)
efeito_ausencia: os períodos viram no fuso local da máquina
exemplo: America/Sao_Paulo
```

### `agents.<platform_id>.limits.daily.limit`

```text
chave: agents.<platform_id>.limits.daily.limit
descricao: Consumo máximo da plataforma por dia, na unidade que ela reporta. Atingido o teto, a próxima execução não começa até o período virar.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: inteiro >= 1; obrigatória quando daily existe
efeito_ausencia: sem limite diário
exemplo: 50000
```

### `agents.<platform_id>.limits.weekly.limit`

```text
chave: agents.<platform_id>.limits.weekly.limit
descricao: Consumo máximo da plataforma por semana.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: inteiro >= 1; obrigatória quando weekly existe
efeito_ausencia: sem limite semanal
exemplo: 300000
```

### `agents.<platform_id>.limits.weekly.reset_weekday`

```text
chave: agents.<platform_id>.limits.weekly.reset_weekday
descricao: Dia da semana em que o período semanal recomeça.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: 0 (segunda) a 6 (domingo); obrigatória quando weekly existe
efeito_ausencia: sem limite semanal
exemplo: 0
```

### `agents.<platform_id>.limits.monthly.limit`

```text
chave: agents.<platform_id>.limits.monthly.limit
descricao: Consumo máximo da plataforma por mês.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: inteiro >= 1; obrigatória quando monthly existe
efeito_ausencia: sem limite mensal
exemplo: 1200000
```

### `agents.<platform_id>.limits.monthly.reset_day`

```text
chave: agents.<platform_id>.limits.monthly.reset_day
descricao: Dia do mês em que o período mensal recomeça.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: 1 a 28, ou o texto last para o último dia do mês; obrigatória quando monthly existe
efeito_ausencia: sem limite mensal
exemplo: 1
```

## Boards

### `boards.platform`

```text
chave: boards.platform
descricao: Plataforma de board usada por todos os boards.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: github
efeito_ausencia: a validação falha; valor diferente de github encerra a inicialização
exemplo: github
```

### `boards.rerun_cooldown`

```text
chave: boards.rerun_cooldown
descricao: Tempo mínimo, em segundos, para entregar de novo a mesma issue, na mesma coluna, ao agente. Mudar de coluna libera a issue na hora. O controle zera a cada reinício.
tipo: inteiro
obrigatoriedade: opcional
default: 0
valores_aceitos: inteiro >= 0; 0 desliga
efeito_ausencia: a issue pode ser reexecutada no ciclo seguinte
exemplo: 300
```

### `boards.<board_id>.name`

```text
chave: boards.<board_id>.name
descricao: Nome do board. A esteira procura o GitHub Project com esse título e o cria se não existir.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: texto não vazio
efeito_ausencia: a validação falha
exemplo: Entrega
```

### `boards.<board_id>.priority`

```text
chave: boards.<board_id>.priority
descricao: Ordem de atendimento entre boards; o menor número é atendido primeiro.
tipo: inteiro
obrigatoriedade: opcional
default: 999
valores_aceitos: inteiro
efeito_ausencia: o board vai para o fim da ordem
exemplo: 0
```

### `boards.<board_id>.flow`

```text
chave: boards.<board_id>.flow
descricao: Flow de git (git.flow.<flow_id>) usado pelas issues do board.
tipo: string
obrigatoriedade: opcional
default: feature
valores_aceitos: id de um flow declarado em git.flow
efeito_ausencia: o board usa o flow feature
exemplo: feature
```

### `boards.<board_id>.repo`

```text
chave: boards.<board_id>.repo
descricao: Repositório (id em git.repo) em que os agentes do board trabalham.
tipo: string
obrigatoriedade: opcional
default: primeiro repositório de git.repo
valores_aceitos: id declarado em git.repo
efeito_ausencia: o board usa o primeiro repositório de git.repo
exemplo: main
```

### `boards.<board_id>.todo`

```text
chave: boards.<board_id>.todo
descricao: Coluna de entrada do board. Uma issue nessa coluna avança sozinha para o destino de change.advance da coluna quando nenhuma coluna posterior tem trabalho pronto.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: id de uma coluna do board
efeito_ausencia: nenhuma issue avança sozinha; a movimentação começa pelo board
exemplo: backlog
```

### `boards.<board_id>.parallel`

```text
chave: boards.<board_id>.parallel
descricao: Com false, uma issue só avança sozinha da coluna de entrada quando nenhuma outra issue está em andamento (fora da entrada e das colunas com archive).
tipo: booleano
obrigatoriedade: opcional
default: true
valores_aceitos: true | false
efeito_ausencia: várias issues podem andar ao mesmo tempo
exemplo: false
```

### `boards.<board_id>.column-migrations.<origem>`

```text
chave: boards.<board_id>.column-migrations.<origem>
descricao: Coluna de destino das issues de uma coluna retirada do board. A esteira move as issues, confirma a origem vazia e só então remove a coluna do GitHub Project.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: id de uma coluna do mesmo board, diferente da origem e que não esteja sendo retirada
efeito_ausencia: coluna retirada e vazia é removida; coluna retirada com issues fica bloqueada até o destino ser declarado
exemplo: concluido
```

### `boards.<board_id>.file-sync.allowed-types`

```text
chave: boards.<board_id>.file-sync.allowed-types
descricao: Extensões de arquivo anexado ou embutido nas issues que a esteira aceita baixar. Substitui a lista padrão.
tipo: lista
obrigatoriedade: opcional
default: png, jpg, jpeg, gif, webp, pdf, txt, md, csv, json, log, zip
valores_aceitos: lista não vazia de extensões
efeito_ausencia: vale a lista padrão
exemplo: [png, jpg, pdf]
```

### `boards.<board_id>.file-sync.max-size`

```text
chave: boards.<board_id>.file-sync.max-size
descricao: Tamanho máximo, em bytes, de cada arquivo baixado.
tipo: inteiro
obrigatoriedade: opcional
default: sem default
valores_aceitos: inteiro > 0
efeito_ausencia: sem limite de tamanho
exemplo: 5000000
```

### `boards.<board_id>.file-sync.on-reject`

```text
chave: boards.<board_id>.file-sync.on-reject
descricao: O que acontece quando um arquivo é recusado. O texto da issue sempre sincroniza.
tipo: string
obrigatoriedade: opcional
default: aviso
valores_aceitos: silencioso (só log) | aviso (um comentário na issue) | bloqueante (comentário e need_human)
efeito_ausencia: a issue recebe um comentário único listando os arquivos recusados
exemplo: aviso
```

## Colunas

### `boards.<board_id>.columns.<column_id>.name`

```text
chave: boards.<board_id>.columns.<column_id>.name
descricao: Nome da coluna, igual à opção de Status no GitHub Project. A ordem das colunas no pipe.yml é a ordem no board.
tipo: string
obrigatoriedade: obrigatória
default: sem default
valores_aceitos: texto não vazio
efeito_ausencia: a validação falha
exemplo: Desenvolvimento
```

### `boards.<board_id>.columns.<column_id>.agent`

```text
chave: boards.<board_id>.columns.<column_id>.agent
descricao: Agente padrão da coluna. Uma issue só é executada numa coluna que tem agent e change.advance.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: id de agente declarado em agents
efeito_ausencia: a coluna não executa agente
exemplo: dev
```

### `boards.<board_id>.columns.<column_id>.agent-hub.<valor>`

```text
chave: boards.<board_id>.columns.<column_id>.agent-hub.<valor>
descricao: Agente usado quando a issue tem a label agent-hub-<valor>. Exige agent na coluna.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: id de agente declarado em agents; <valor> é livre (ex.: low, high)
efeito_ausencia: a coluna sempre usa o agente de agent
exemplo: senior
```

### `boards.<board_id>.columns.<column_id>.on_in`

```text
chave: boards.<board_id>.columns.<column_id>.on_in
descricao: Ações aplicadas quando uma issue entra na coluna.
tipo: lista
obrigatoriedade: opcional
default: sem default
valores_aceitos: close, open, archive, -archive, need_human, -need_human, <label> (adiciona), -<label> (remove)
efeito_ausencia: nenhuma ação na entrada
exemplo: [close, done]
```

### `boards.<board_id>.columns.<column_id>.on_out`

```text
chave: boards.<board_id>.columns.<column_id>.on_out
descricao: Ações aplicadas quando uma issue sai da coluna.
tipo: lista
obrigatoriedade: opcional
default: sem default
valores_aceitos: mesmos valores de on_in
efeito_ausencia: nenhuma ação na saída
exemplo: [-done]
```

### `boards.<board_id>.columns.<column_id>.gitevents`

```text
chave: boards.<board_id>.columns.<column_id>.gitevents
descricao: O que o agente faz com branches nesta coluna.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: create (cria a branch) | use (usa a branch existente) | merge (usa a existente e abre pull request) | create-merge (cria e abre pull request) | no-branch (sem git)
efeito_ausencia: nenhuma instrução de git é dada ao agente
exemplo: create
```

### `boards.<board_id>.columns.<column_id>.target-prompt`

```text
chave: boards.<board_id>.columns.<column_id>.target-prompt
descricao: Objetivo da etapa, entregue ao agente em toda execução na coluna.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: texto livre
efeito_ausencia: o agente recebe o objetivo vazio
exemplo: Implemente a issue com testes.
```

### `boards.<board_id>.columns.<column_id>.step-prompt`

```text
chave: boards.<board_id>.columns.<column_id>.step-prompt
descricao: Passos da etapa, entregues ao agente logo após o objetivo.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: texto livre, pode ter várias linhas
efeito_ausencia: o prompt não traz a seção de passos
exemplo: Leia a issue, implemente e rode os testes.
```

### `boards.<board_id>.columns.<column_id>.change.advance`

```text
chave: boards.<board_id>.columns.<column_id>.change.advance
descricao: Coluna para onde o agente move a issue ao concluir a etapa. Sem ela, a coluna não é executada.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: id de uma coluna do mesmo board
efeito_ausencia: a coluna não executa agente
exemplo: revisao
```

### `boards.<board_id>.columns.<column_id>.change.<condicao>`

```text
chave: boards.<board_id>.columns.<column_id>.change.<condicao>
descricao: Transição adicional que o agente pode escolher (ex.: devolver a issue). Cada condição vira uma opção de destino no prompt.
tipo: string
obrigatoriedade: opcional
default: sem default
valores_aceitos: id de uma coluna do mesmo board; <condicao> é livre
efeito_ausencia: o agente só conhece a transição advance
exemplo: planejamento
```

### `boards.<board_id>.columns.<column_id>.archive`

```text
chave: boards.<board_id>.columns.<column_id>.archive
descricao: Marca a coluna como final. Issues nela não contam como em andamento para parallel: false. Para arquivar a issue no board, use on_in com archive.
tipo: booleano
obrigatoriedade: opcional
default: false
valores_aceitos: true | false
efeito_ausencia: a coluna conta como em andamento
exemplo: true
```
