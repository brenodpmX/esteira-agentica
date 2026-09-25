# Changelog

Todas as mudanças relevantes deste projeto serão registradas neste arquivo.

## [1.14.0] - 2026-09-24

### Corrigido

- O sync incremental por-ciclo (`sync_remote`) agora detecta issues presentes no
  snapshot mas AUSENTES do fetch atual e enfileira `delete-down` para elas —
  arquivadas (o GitHub ProjectV2 remove itens arquivados da connection `items`,
  eles não voltam com `isArchived=true`) ou deletadas no board. Antes, essa
  detecção de ausência só existia na varredura completa (`detect_board_changes`,
  startup/diária); por isso uma issue arquivada permanecia no snapshot até o full
  sync do dia seguinte, congelando boards `parallel:false` (uma issue terminal
  parada era contada como ocupante ativo, bloqueando o auto-advance do backlog).
  Agora a poda ocorre no ciclo seguinte ao arquivamento.

### Detalhes

- Custo de API zero: o fetch completo (`list_issues`) já era feito a cada ciclo
  por dentro de `list_issues_since`; `sync_remote` passa a usá-lo diretamente,
  derivando o subconjunto modificado (`updated_at > since`) para create/change e
  o conjunto completo para a detecção de ausência.
- O fetch é atômico (rate limit levanta `PenaltyException` em vez de devolver
  página parcial), então uma leitura truncada não gera falso-positivo de
  deleção — mesmo risco/garantia da varredura completa.

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
