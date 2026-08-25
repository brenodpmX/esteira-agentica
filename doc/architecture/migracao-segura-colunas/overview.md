# Architecture Overview — Migração segura de colunas de boards

Status: approved
Owner: architecture
Last updated: 2026-08-25

## Inputs

- `/app/.pipe/boards/epic/arquitetura/91-migracao_de_boards-body.md`
- `/app/.pipe/boards/epic/arquitetura/91-migracao_de_boards-history.md`
- `/app/contexts/templates/docs/architecture-overview.md`
- `doc/product/migracao-de-boards/diligencia-negocio.md`
- `doc/requirements/migracao-de-boards/functional-requirements.md`
- `doc/requirements/migracao-de-boards/business-rules.md`
- `doc/requirements/migracao-de-boards/non-functional-requirements.md`
- `doc/requirements/migracao-de-boards/glossary.md`
- `CONTEXT.md`
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md`
- `src/__main__.py` (`board_full_sync`)
- `src/core/config.py` (`_validate_boards`)
- `src/core/board.py` (`BoardPort`, `Board.sync_boards`, `list_issues`, `move_issue`)
- `src/adapters/github_board.py` (`sync_boards`, `list_issues`, `move_issue`, `_update_status_options`)

Não foi encontrado artefato de prototipação específico deste épico no
repositório. A inspeção do fluxo atual e dos testes existentes foi usada como
spike técnico: ela confirmou que `_update_status_options` recebe hoje apenas a
lista desejada e substitui as opções do campo `Status` antes de verificar os
itens que ainda usam opções retiradas.

## Visão geral

A retirada de coluna passa a ser uma reconciliação estrutural segura em três
fases: **expandir, migrar e contrair**.

1. **Expandir:** garantir boards, campo `Status` e novas colunas desejadas,
   preservando todas as opções remotas existentes.
2. **Migrar:** para cada opção remota ausente da configuração resultante,
   verificar as issues atuais, validar um destino explícito quando a origem
   estiver ocupada e mover somente os itens que ainda estão na origem.
3. **Contrair:** retirar uma opção de `Status` somente depois de uma nova
   leitura remota confirmar que a origem está vazia.

O estado remoto do board é a fonte de verdade para retomada. Se uma execução
falhar depois de mover parte das issues, as já movidas permanecem no destino e
a origem continua disponível. A tentativa seguinte lista novamente o board e
atua somente sobre o que ainda estiver na origem. Não é necessário criar banco,
broker, workflow distribuído ou estado persistente de progresso por item.

A intenção de destino é declarativa e local ao board:

```yaml
boards:
  epic:
    name: Epic
    columns:
      backlog:
        name: Backlog
      validacao-arquitetura:
        name: Validação de Arquitetura
    column-migrations:
      arquitetura: validacao-arquitetura
```

As chaves e valores de `column-migrations` são IDs de coluna, isto é, as mesmas
chaves usadas em `boards.<board>.columns`. O mapa pode ser declarado antes da
retirada e permanecer depois dela. Ele só é acionado quando a origem existe
remotamente e não pertence mais à configuração desejada.

## Estilo arquitetural

A solução preserva a arquitetura hexagonal e o processo sequencial existentes:

- a **política** de validar, drenar e somente então retirar fica no core;
- o **port** expõe preparação e alteração da estrutura remota, além das
  primitivas já existentes de listar e mover issues;
- o adapter GitHub continua responsável apenas por GraphQL, paginação,
  identificação de options/items e tradução de erros;
- o loop principal continua síncrono e sob o `InstanceLock` existente; e
- logs estruturados continuam sendo a evidência operacional acessível.

O padrão adotado é uma combinação simples de **expand-and-contract** com
**reconciliação idempotente**. Não se adota uma saga genérica: não há transação
entre serviços nem necessidade de compensar conteúdo de issue. A única mutação
por item é a troca do valor de `Status`, e o próprio estado remoto permite
retomada.

## Diagnóstico do fluxo atual

```text
board_full_sync
  -> grava no snapshot apenas as colunas da nova configuração
  -> Board.sync_boards
     -> GitHubBoardAdapter.sync_boards
        -> _update_status_options(lista desejada)
           -> remove a option antiga mesmo que ainda esteja ocupada
  -> detecta issues remotas já sem Status
```

Há três lacunas arquiteturais:

1. o adapter recebe uma decisão estrutural pronta e não consegue aplicar a
   regra de negócio “origem vazia antes da retirada”;
2. o snapshot local é atualizado antes de a estrutura remota ser reconciliada;
3. a operação atual não produz uma tentativa de migração com contagens e
   resultado próprios.

## Componentes

| Componente | Responsabilidade |
|-----------|------------------|
| `config.py` | Validar que `column-migrations`, quando presente, é um mapa de IDs de coluna não vazios. A validade semântica do destino é verificada durante a reconciliação, para que uma tentativa inválida seja bloqueada com contagens sem impedir os demais boards. |
| `Board.sync_boards` | Orquestrar expandir → migrar → contrair, validar destinos, detectar ausência de progresso e devolver a estrutura remota efetiva por board. |
| `BoardPort` | Separar a preparação não destrutiva da estrutura da substituição exata das opções. Continuar expondo `list_issues` e `move_issue`. |
| `GitHubBoardAdapter` | Criar/resolver project e campo, preservar IDs de options existentes, executar mutations GraphQL e retornar a estrutura observada. Não decidir destino nem política de retirada. |
| `board_full_sync` | Executar primeiro a reconciliação remota; depois criar diretórios e atualizar o mapa de colunas do snapshot com a estrutura efetiva, inclusive origens retidas. |
| Sync incremental existente | Detectar as mudanças de coluna como `change-down`, atualizar arquivos/snapshot e aplicar `on_out`/`on_in` pelo fluxo já vigente, sem disparo especial ou duplicado pela migração. |
| Logging existente | Registrar uma evidência estruturada por tentativa e por coluna retirada, sem exigir acesso a snapshot ou fila protegida. |

### Evolução mínima do port

O método público `Board.sync_boards(config)` permanece. No limite entre core e
adapter, a operação monolítica atual é separada em duas capacidades:

```text
prepare_boards(boards) -> {board_id: [colunas_remotas_efetivas]}
set_board_columns(board_id, columns) -> [colunas_remotas_efetivas]
```

`prepare_boards` cria o que estiver ausente e acrescenta novas colunas
desejadas, mas nunca remove opções existentes. `set_board_columns` substitui a
lista de options somente quando o core já autorizou a contração. Os nomes
podem ser ajustados na implementação, mas a separação entre preparação não
destrutiva e contração autorizada é obrigatória.

`list_issues` e `move_issue` continuam sendo as primitivas de itens. Uma issue
só conta como movida quando uma leitura posterior não a encontra mais na
origem; warning ou retorno silencioso do adapter nunca autorizam retirar a
coluna.

## Fluxo principal

```text
configuração desejada
  -> prepare_boards (adiciona destino, preserva origens antigas)
  -> para cada coluna remota ausente da configuração:
       listar issues remotas
       contar issues na origem
       origem vazia?
         sim -> reler imediatamente -> retirar somente essa origem
         não -> validar column-migrations[origem]
                ausente/inválido -> manter origem + registrar blocked
                válido -> mover lote atual para o destino
                          reler origem
                          ainda há itens e houve progresso -> repetir drenagem
                          ainda há itens sem progresso/falha -> manter origem
                          vazia -> reler imediatamente -> retirar origem
  -> retornar colunas efetivas
  -> atualizar diretórios/snapshot local
  -> detecção remota normal gera change-down para os itens movidos
```

### Validação do destino

Para uma origem ocupada, o destino é válido somente quando:

- há exatamente um valor declarado para a origem;
- o destino é uma coluna da configuração resultante do mesmo board;
- o destino é diferente da origem; e
- o destino não é outra coluna retirada na mesma alteração.

A localidade do mapa dentro de `boards.<board>` impede destino cross-board.
Destino ausente ou inválido não gera nenhum `move_issue` e não autoriza
`set_board_columns` sem a origem. Outras colunas do mesmo ou de outros boards
podem continuar sendo reconciliadas.

### Drenagem e chegada de novas issues

Cada passagem lista novamente o board. Se uma issue chegar à origem durante a
migração, ela aparece na leitura seguinte e é movida para o mesmo destino. A
contração só ocorre após uma leitura imediatamente anterior retornar zero.

Para não prender indefinidamente o startup quando o provider não confirma uma
mutação, a tentativa é interrompida quando uma passagem completa não reduz o
conjunto observado na origem. A origem permanece ativa, o resultado é
`interrupted` com motivo `no_progress`, e uma execução posterior pode tentar de
novo.

### Falha, interrupção e retomada

A ordem das operações fornece a segurança:

- a option da origem permanece no campo durante toda a migração;
- cada mutation altera somente `Status` da issue;
- uma falha antes da contração deixa itens já movidos no destino e os demais na
  origem;
- uma nova tentativa deriva o trabalho restante de `list_issues`, portanto não
  move novamente itens já no destino;
- `PenaltyException` e demais erros continuam usando throttle, retry de startup
  e restart do container existentes; e
- se a confirmação de vazio falhar, a contração não é chamada.

Não há rollback dos itens já movidos: ele criaria mais chamadas e mais pontos de
falha sem melhorar o estado. O estado parcial já é válido e convergente.

### Eventos de coluna e preservação de atributos

A migração chama apenas a primitiva de alteração de `Status`; não atualiza
issue, labels, relações, estado ou arquivamento. Assim, ID e demais atributos
são preservados.

Depois da reconciliação estrutural, a detecção remota existente observa
`origem -> destino` em relação ao snapshot anterior e enfileira `change-down`.
Esse fluxo continua responsável por materializar a mudança local e por aplicar
os eventos `on_out`/`on_in` segundo a configuração vigente. A migração não chama
`apply_column_events` diretamente, evitando evento duplicado em uma repetição.

## Estrutura local e ordem do full sync

A ordem de `board_full_sync` deve mudar para não publicar no snapshot uma
estrutura desejada que ainda não existe remotamente:

```text
antes:  snapshot desejado -> sync remoto -> detecção
novo:   reconciliação remota segura -> snapshot efetivo -> detecção
```

A estrutura efetiva inclui colunas configuradas e qualquer origem retida por
bloqueio, falha ou falta de progresso. Os diretórios locais correspondentes são
mantidos/criados para que issues ainda na origem continuem representáveis. O
contexto e o escalonamento de agentes continuam derivados da configuração; uma
coluna retirada, embora temporariamente preservada no board, não recebe novas
tarefas da esteira.

Se a reconciliação falhar antes de retornar a estrutura efetiva, o snapshot
anterior não é substituído.

## Observabilidade

Cada origem retirada produz um evento final `column_migration_attempt` no log
normal da esteira, com pelo menos:

```text
attempt_id, board, source, destination,
initial_count, moved_count, remaining_count,
result, reason, started_at, finished_at
```

Resultados:

- `completed`: origem confirmada vazia e option retirada;
- `blocked`: origem ocupada e destino ausente ou inválido;
- `interrupted`: falha, penalty, ausência de progresso ou confirmação
  inconclusiva; a origem permanece ativa.

IDs observados/movidos/restantes podem ser emitidos no log detalhado para
rastreabilidade, sem título, body, credenciais ou conteúdo de arquivos
protegidos. As contagens são derivadas das leituras remotas; itens já no destino
antes da tentativa não são contabilizados novamente como movidos.

Esses eventos usam o logging dual já existente e, portanto, são consultáveis em
`logs/`, não em `snapshot.json` ou `changeQueue.json`. A infraestrutura externa
de métricas pode agregá-los durante os 90 dias definidos pelo produto, sem ser
pré-requisito desta entrega.

## Compatibilidade e liberação

- Configurações sem `column-migrations` continuam válidas. Colunas remotas
  vazias podem ser retiradas como hoje; colunas ocupadas passam a ser retidas.
- O mapa pode ser adicionado antes da retirada, permitindo rollout declarativo
  em um ou dois commits sem modo especial.
- Não há migração de arquivo de estado nem nova dependência.
- A estrutura do snapshot passa a refletir as colunas remotas efetivas após a
  reconciliação, preservando campos de issues existentes.
- A implementação deve incrementar a versão MINOR, pois adiciona
  comportamento/configuração compatível.
- O README e o exemplo de `pipe.yml` devem documentar o novo mapa e seu ciclo de
  vida.

## Estratégia de testes

### Core com port fake

- coluna vazia sem destino é retirada;
- coluna ocupada com destino válido é totalmente drenada antes da contração;
- destino ausente, inexistente, igual à origem ou também retirado bloqueia sem
  nenhuma movimentação;
- falha após M movimentos mantém a origem e a repetição move só os restantes;
- issue que chega entre leituras é incluída na drenagem;
- passagem sem progresso interrompe sem loop infinito;
- duas origens na mesma mudança são tratadas independentemente;
- atributos da issue não são enviados a operações de atualização;
- evidência contém todas as contagens e o resultado.

### Adapter GitHub

- preparação mantém option antiga e preserva IDs existentes;
- destino ausente é criado antes do primeiro movimento;
- contração GraphQL só recebe a lista autorizada pelo core;
- paginação de `list_issues` participa da contagem integral;
- todas as chamadas passam por `_gql` e pelo throttle;
- erro REST/GraphQL estruturado propaga sem remover a origem.

### Integração e regressão

- `board_full_sync` grava a estrutura efetiva somente depois da reconciliação;
- `change-down` posterior atualiza arquivos e dispara eventos uma única vez;
- reinício com migração parcial converge sem perda ou duplicação;
- os cenários F-001 a F-006 e RN-001 a RN-010 são exercitados;
- suíte completa, `git diff --check` e smoke de startup/shutdown.

## Rastreabilidade

| Requisito | Decisão arquitetural |
|---|---|
| RF-001, RF-008, RN-001, RN-004 | leituras remotas no início, após cada lote e imediatamente antes da contração |
| RF-003 a RF-005, RN-002, RN-003, RN-010 | mapa local ao board e validação semântica antes do primeiro movimento |
| RF-006, RF-007, RN-007 | uso exclusivo de `move_issue`/Status e fluxo normal de eventos |
| RF-009 a RF-011, RN-005, RN-006 | origem preservada até vazio e retomada derivada do estado remoto |
| RF-012, RN-008 | evento estruturado por tentativa no log operacional |
| RN-009 | reconciliação acionada somente por divergência estrutural de colunas |

## Fora de escopo

- migração entre boards ou destino por issue;
- arquivar ou fechar como destino;
- autorização, janela de mudança ou WIP;
- novo scheduler, banco, broker, fila estrutural ou rollback dos itens já
  movidos;
- alteração das regras gerais de `keep_task`, `on_in` ou `on_out`;
- limpeza automática de issues que já estavam sem `Status` antes da tentativa.
