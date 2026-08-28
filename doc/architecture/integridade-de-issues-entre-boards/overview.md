# Architecture Overview — Integridade de issues entre boards

Status: draft
Owner: architecture
Last updated: 2026-08-27

## Inputs
- `doc/product/integridade-de-issues-entre-boards/vision.md`
- `doc/product/integridade-de-issues-entre-boards/problem-space.md`
- `doc/product/integridade-de-issues-entre-boards/epicos.md`
- `doc/requirements/integridade-de-issues-entre-boards/glossary.md`
- `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`
- `doc/requirements/integridade-de-issues-entre-boards/business-rules.md`
- `doc/requirements/integridade-de-issues-entre-boards/non-functional-requirements.md`
- `doc/incidente/sub-issues-propagadas/ticket.md`
- `doc/changes/88-sub-issues-propagadas-entre-boards.md`
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md`
- `CONTEXT.md`, `README.md`
- Implementação/protótipo vigente em `src/core/sync.py`, `src/core/board.py`, `src/core/commands.py`, `src/__main__.py`, `src/adapters/github_board.py` e `tests/test_sub_issue_propagation_fix.py`

## Visão geral

A solução adiciona uma fronteira de integridade entre a descoberta remota e o
despacho de agentes. Uma participação em GitHub Project V2 somente é
materializada como issue executável depois de ser classificada como origem
intencional ou como participação adicional explicitamente autorizada. Na
ausência de prova, o comportamento é *fail-closed*: o evento permanece pendente,
a issue não entra no conjunto elegível de `keep_task` e as demais issues
continuam a avançar.

A correção anterior é mantida como protótipo e evidência do comportamento da
API, mas deixa de definir a política. Hoje ela usa `Status` vazio como proxy de
propagação, preserva automaticamente qualquer item que já tenha `Status`,
engole falhas do pós-hook e não valida intenção em `keep_task`. Isso explica
como uma propagação pode atravessar as duas proteções existentes e receber um
agente do board errado.

A arquitetura proposta usa defesa em profundidade em três pontos:

1. reconciliação imediata, após criar uma relação pai/filho;
2. classificação obrigatória de toda participação nova no `create-down`, com ou
   sem `Status`; e
3. gate final em `keep_task`, que exige intenção confirmada no snapshot.

Não são introduzidos banco de dados, broker, worker, webhook ou novo serviço. O
loop sequencial, a fila persistente, os snapshots e os logs JSON existentes são
reutilizados.

## Estilo arquitetural

Permanece a arquitetura hexagonal atual. Regras de intenção, autorização,
contingência e elegibilidade ficam no core; o adapter GitHub apenas traduz
GraphQL/REST para contratos normalizados do `BoardPort`.

O padrão principal é **Policy + Gate fail-closed**:

- uma política pura classifica uma participação em `origin`, `authorized`,
  `propagated` ou `unresolved`;
- um gate impede materialização e despacho quando o resultado não é seguro; e
- a fila existente retenta casos não resolvidos sem bloquear outros itens.

Esse desenho é deliberadamente mais simples que event sourcing, saga ou
serviço de consistência separado. A operação é sequencial e o volume observado
não justifica infraestrutura adicional.

## Componentes

| Componente | Responsabilidade |
|-----------|------------------|
| `Participation` (modelo do core) | Representar `issue_id`, board, item remoto, `Status` e arquivamento sem expor GraphQL ao domínio. |
| `ParticipationPolicy` (core) | Classificar intenção usando autorização explícita, boards configurados e participações já confirmadas. Não faz I/O. |
| `ParticipationIntegrity` (core) | Orquestrar consulta, classificação, remoção e auditoria após vínculo e no fluxo down. |
| `BoardPort` | Expor `list_participations(issue_id)` e a remoção já existente `remove_from_board`; adapters não decidem intenção. |
| `GitHubBoardAdapter` | Consultar `projectItems` por GraphQL e executar `deleteProjectV2Item`; propagar erros tipados. |
| `ChangeQueue` | Manter o evento não resolvido, com `next_attempt_at`, e rotacioná-lo sem head-of-line blocking. |
| `Snapshot` | Cachear `participation_intent=origin|authorized` nas issues materializadas; nunca é a fonte da autorização explícita. |
| `keep_task` | Aplicar o gate final: somente `status == ok` e intenção confirmada podem avançar ou receber agente. |
| `IssueCommands`/labels | Reutilizar `/labels` e a label reservada `board-intent-<board_id>` para autorizar participação adicional. |
| Configuração de segurança | Ler `safety.cross_board_parent_links: enabled|suspended` antes de aplicar novos vínculos. |
| Logging existente | Emitir eventos estruturados de classificação, reconciliação, bloqueio, remoção externa e rollout. |

## Modelo de intenção

A autorização adicional é declarada pela label reservada
`board-intent-<board_id>`, usando o mecanismo de labels já sincronizado por
`IssueCommands`. O sufixo deve corresponder exatamente a um board configurado.
A label autoriza somente o board citado; não autoriza todos os boards e não é
necessária para o board de origem.

| Estado | Como é provado | Pode materializar/despachar? |
|---|---|---|
| `origin` | Primeira participação observada, sem outra participação confirmada em board configurado | Sim |
| `authorized` | Label `board-intent-<board_id>` presente e válida | Sim |
| `propagated` | Issue já confirmada em outro board configurado, sem autorização para o board atual | Não; remover a participação atual |
| `unresolved` | Consulta falhou, evidência é ambígua ou migração encontrou duplicidade anterior sem autorização | Não; manter pendente e auditar |

`Status` preenchido não é evidência de intenção. `parent` isolado também não é
prova de propagação. A classificação vale para qualquer par de boards e não
codifica Epics, User Stories ou Tasks.

O snapshot guarda apenas o resultado confirmado para que o gate seja barato.
Labels continuam sendo a fonte verificável da autorização multi-board. Entradas
legadas sem `participation_intent` são migradas no startup: uma ocorrência única
em boards configurados vira `origin`; duplicidades sem autorização ficam
`unresolved`, bloqueadas e visíveis para tratamento, sem remoção automática de
resíduo histórico.

## Fluxo principal

```text
GitHub list_issues / relação criada
              |
              v
      list_participations
              |
              v
     ParticipationPolicy
       /       |        \
 origin/   propagated   unresolved
 authorized     |           |
    |           v           v
 materializa  remove      requeue com
 + marca      item        next_attempt_at
 intenção       |           |
    +-----------+-----------+
                |
                v
      log estruturado/auditoria
                |
                v
 keep_task exige intention in {origin, authorized}
                |
                v
             agente
```

### Relação pai/filho

1. O core identifica os boards confirmados de pai e filha.
2. Se a contingência estiver suspensa e os boards forem distintos, não envia a
   relação ao adapter; registra `cross_board_link_blocked`. Relações no mesmo
   board continuam permitidas.
3. Se habilitada, aplica a relação pela API nativa.
4. Consulta as participações da filha e reconcilia toda participação não
   autorizada. A relação pai/filho não é removida.
5. Falha na consulta/remoção é propagada como erro tipado. A reconciliação
   assíncrona do fluxo down continua sendo a barreira definitiva caso o GitHub
   materialize o item depois da consulta imediata.

A lógica deixa de ter a assimetria atual entre `set_parent` e `set_children`:
o serviço recebe a filha e seus boards confirmados, não um `exclude_board_id`
cujo significado muda conforme o call site.

### Descoberta remota (`create-down`)

1. Toda issue nova no board passa pela política, mesmo que já tenha `Status`.
2. `origin` ou `authorized`: cria os três arquivos locais e grava a intenção no
   snapshot.
3. `propagated`: chama `remove_from_board`, registra a reconciliação e somente
   então consome o evento.
4. `unresolved` ou falha transitória: não cria arquivos nem snapshot executável;
   mantém o item na fila com `next_attempt_at = now + sleep` e o rotaciona para
   que outros itens sejam processados.
5. Se a participação desaparecer sem evento de reconciliação automática bem
   sucedido, registra `participation_removed_externally`, permitindo apurar
   intervenção manual.

### Gate de despacho

`keep_task` mantém os filtros atuais e acrescenta a condição:

```text
participation_intent in {origin, authorized}
```

Entradas sem o campo, pendentes ou conflitantes são ignoradas e geram
`dispatch_blocked_unconfirmed_intent` de forma deduplicada. Esse gate não chama
a API e também protege contra resíduos ou regressões que escapem da camada de
reconciliação.

### Retentativa sem bloqueio global

Casos `unresolved` usam a própria `ChangeQueue`. `next_attempt_at` evita loop
apertado; itens ainda não vencidos são rotacionados. Esse tipo de pendência não
vai para dead-letter apenas por quantidade de tentativas, pois a participação
continua segura e precisa ser reconciliada em ciclos subsequentes. Erros
definitivos de contrato continuam seguindo a política de dead-letter vigente.

### Contingência operacional

A chave abaixo é validada e relida por mtime antes de aplicar uma nova relação;
não exige restart ou deploy:

```yaml
safety:
  cross_board_parent_links: enabled  # enabled | suspended
```

Em `suspended`, uma solicitação nova entre boards distintos é recusada com log
auditável. O pedido recusado não é reproduzido automaticamente: após reativar,
o operador/agente deve submetê-lo novamente. Vínculos existentes e relações no
mesmo board permanecem intactos.

## Observabilidade e rollout

Eventos mínimos, no logger JSON atual:

| Evento | Campos mínimos |
|---|---|
| `participation_classified` | issue, board, classification, evidence, timestamp |
| `participation_reconciled` | issue, origin_board, propagated_board, detected_at, reconciled_at |
| `participation_reconcile_failed` | issue, board, attempt, next_attempt_at, error_kind |
| `participation_removed_externally` | issue, board, first_seen_at, observed_removed_at |
| `dispatch_blocked_unconfirmed_intent` | issue, board, column, classification |
| `cross_board_link_blocked` | parent, child, parent_board, child_board, config_version |
| `rollout_evidence` | version, commit, environment, started_at |

O startup obtém `version` de `src/core/version.py`, `commit` do checkout/arquivo
de build e `environment` de `PIPE_ENVIRONMENT`. O Compose deve definir o
ambiente explicitamente. A data observada é o início daquela instância. Isso
produz evidência de código em execução sem criar stack de métricas. Os logs de
agente passam a incluir `participation_intent` e board de origem, permitindo
correlacionar despachos e créditos.

## Compatibilidade e migração

- Snapshots sem `participation_intent` são aceitos e migrados no full sync de
  startup antes de `keep_task`.
- Itens de fila sem `next_attempt_at` continuam imediatamente elegíveis.
- Adapters sem `list_participations` devem falhar na inicialização quando o
  provider declarar suporte a hierarquia entre boards; não há fallback aberto.
- Labels `board-intent-*` com board inexistente são ignoradas para autorização e
  geram warning.
- A limpeza retroativa de resíduos continua fora de escopo; a migração apenas
  impede despacho de duplicidades ambíguas.

## Estratégia de validação

1. Unitários da política para `origin`, `authorized`, `propagated` e
   `unresolved`, sem dependência da ordem de boards.
2. Regressão Story→Epic e Task→User Story com propagação sem e com `Status`.
3. Caso negativo de multi-board autorizado pela label.
4. Falha transitória de consulta/remoção: nenhum arquivo, nenhum despacho,
   item rotacionado e retentado.
5. Pós-hook sem propagação imediata seguido de chegada tardia no fluxo down.
6. Gate de `keep_task` com entrada legada, pendente e confirmada.
7. Contingência habilitada/desabilitada sem restart, preservando vínculos
   existentes e relações no mesmo board.
8. Migração com issue em um board e duplicidade histórica em dois boards.
9. Teste de integração GraphQL real/gated para `projectItems` e
   `deleteProjectV2Item`, além da suíte com fake port.
10. Homologação em produção por 30 dias e no mínimo 17 novas relações, iniciada
    somente após `rollout_evidence` válido.

## Rastreabilidade

| Requisitos | Elemento arquitetural |
|---|---|
| RF-01, RN-B01 | classificação antes do `create-down` + gate em `keep_task` |
| RF-02, RN-B02 | reconciliação por evento, retentativa pendente e remoção GraphQL |
| RF-03, RN-B03, RN-B11 | remoção apenas do `ProjectV2Item`, nunca da relação |
| RF-04, RN-B04 | label `board-intent-<board_id>` |
| RF-05, RN-B10 | política baseada em board configurado, sem pares hardcoded |
| RF-06, RN-B08 | evento `rollout_evidence` |
| RF-07, RN-B09 | eventos JSON e enriquecimento do log de agente |
| RF-08, RN-B05/RN-B06 | migração bloqueia ambiguidade; resíduos permanecem separados |
| RF-09, RN-B07 | chave de contingência relida sem restart |
