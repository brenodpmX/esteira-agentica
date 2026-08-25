# Constraints — Migração segura de colunas de boards

Status: approved
Owner: architecture
Last updated: 2026-08-25

## Inputs

- `/app/contexts/templates/docs/constraints.md`
- `doc/architecture/migracao-segura-colunas/overview.md`
- `doc/requirements/migracao-de-boards/non-functional-requirements.md`
- `doc/requirements/migracao-de-boards/business-rules.md`
- `CONTEXT.md`
- `README.md`
- `src/__main__.py`
- `src/core/board.py`
- `src/adapters/github_board.py`

## Restrições técnicas

- A solução deve preservar a arquitetura hexagonal: decisão de migrar/reter no
  core; GraphQL, IDs de project/item/option e paginação no adapter.
- Operações de GitHub Projects V2 devem usar GraphQL via `_gql`; não existe
  endpoint REST de `projectitems` aceito neste projeto.
- Toda chamada externa deve continuar passando pelo throttle e penalty
  existentes. Não pode haver `subprocess` ou chamada ao `gh` fora do adapter.
- A option da origem não pode ser omitida de uma mutation estrutural enquanto
  uma leitura remota ainda retornar qualquer issue nela.
- Destino ausente ou inválido deve ser decidido antes do primeiro `move_issue`
  daquela origem.
- Uma mutação de migração só pode alterar o campo `Status`. Título, body,
  labels, relações, estado e arquivamento não podem ser reenviados.
- O core não pode considerar warning/retorno local como confirmação de
  movimento. A confirmação vem de uma nova listagem remota.
- O snapshot deve ser atualizado somente após a reconciliação estrutural e com
  a estrutura remota efetiva, inclusive origens temporariamente retidas.
- Arquivos internos protegidos não podem ser usados como interface de
  observabilidade. A evidência deve ir para os logs normais.
- Não adicionar banco, broker, serviço, thread, worker paralelo ou dependência
  de terceiros. O loop sequencial e o `InstanceLock` existentes são mantidos.
- A mudança não pode transformar a fila at-least-once de issues em coordenador
  de schema; a retomada estrutural deriva do board remoto.

## Premissas

- IDs de coluna configurados são os nomes das options de `Status` publicados
  pelo adapter atual.
- Cada origem possui no máximo um destino, declarado em
  `boards.<board>.column-migrations`.
- O destino pertence ao mesmo board por construção e permanece em
  `boards.<board>.columns` durante a migração.
- O GitHub preserva identidade e atributos quando apenas
  `updateProjectV2ItemFieldValue` altera o `Status`.
- `list_issues` pagina todos os itens não arquivados com conteúdo do tipo Issue;
  drafts e pull requests continuam fora do contrato atual da esteira.
- Há uma única instância da esteira por diretório de estado, garantida pelo
  `InstanceLock`. Usuários ainda podem alterar o board diretamente no GitHub.
- Não há SLA de conclusão. Uma origem pode permanecer ativa por múltiplas
  tentativas sem violar o contrato.
- Logs persistem no diretório configurado e são a fonte para as métricas de 90
  dias solicitadas pelo produto.

## Limite de atomicidade do provider

GitHub Projects V2 não oferece, no contrato atualmente usado, uma operação
atômica do tipo “remova esta option somente se nenhum item a utiliza”, nem um
lock de escrita do project para bloquear usuários externos. Assim, a garantia é
construída por drenagem e leitura imediatamente anterior à mutation.

Uma edição externa exatamente entre a confirmação de vazio e a mutation de
contração é uma janela residual de TOCTOU que a aplicação não consegue eliminar
sem suporte transacional do provider. A implementação deve:

1. manter essa janela restrita à leitura final seguida da mutation;
2. não executar outra operação local entre as duas chamadas;
3. fazer verificação remota logo após a contração e registrar evento crítico se
   surgir item novo sem `Status`;
4. quando houver destino explícito inequívoco, reconciliar o item recém-sem
   status para esse destino; e
5. nunca tratar essa compensação como substituta da pré-condição de origem
   vazia.

A homologação deve incluir chegada de issue antes da leitura final (F-006), que
é plenamente controlada pelo loop de drenagem, e documentar separadamente a
janela residual do provider. Uma garantia estritamente linearizável contra
escritores externos exigiria capacidade nova da API do GitHub e está fora do
controle desta implementação.

## Requisitos não-funcionais

| Atributo | Requisito |
|----------|----------|
| Integridade | Nenhuma contração autorizada enquanto a leitura remota indicar item na origem; destino inválido causa zero mudança de classificação. |
| Idempotência | Repetir a reconciliação no mesmo estado produz o mesmo schema final e move apenas itens ainda observados na origem. |
| Recuperação | Falha antes da contração preserva a origem; restart não requer limpeza manual nem replay de journal. |
| Observabilidade | 100% das tentativas registram board, origem, destino, contagem inicial, movidos, restantes, resultado e motivo. |
| Performance | Uma listagem inicial e uma confirmação por lote/origem; uma mutation por issue ainda na origem; sem releitura de conteúdo detalhado ou relações. |
| Rate limit | Todas as operações usam `_gql`/adapter e respeitam throttle/penalty; nenhuma retentativa paralela. |
| Segurança | Logs não contêm credenciais, body, contexto do agente ou conteúdo de estado protegido. |
| Compatibilidade | `column-migrations` é opcional; boards sem retirada mantêm o comportamento estrutural vigente. |
| Operabilidade | Bloqueio de uma origem não impede a reconciliação segura de outras origens/boards, salvo erro de transporte que já interrompa o full sync. |
| Manutenibilidade | Política coberta por testes do core com port fake; detalhes GraphQL cobertos separadamente no adapter. |

## Guardrails para implementação

- Não mover a política para `GitHubBoardAdapter.sync_boards` apenas porque ele
  já possui os IDs remotos.
- Não remover primeiro para depois procurar issues sem `Status`.
- Não implementar rollback em massa para a origem após falha parcial.
- Não persistir uma lista paralela de IDs já movidos; ela diverge do board e é
  desnecessária para idempotência.
- Não disparar `on_in`/`on_out` diretamente no reconciliador e novamente no
  `change-down`.
- Não usar sleep arbitrário como prova de quiescência.
- Não fazer fallback para a primeira coluna quando o destino da migração é
  inválido; isso esconderia erro de configuração.
- Não apagar diretórios de colunas retidas nem sobrescrever o snapshot antes do
  resultado remoto.

## Critérios de saída da arquitetura

- Contratos do port preservam a separação entre preparação não destrutiva e
  contração exata.
- Todos os fluxos F-001 a F-006 possuem teste automatizado.
- Falhas em cada ponto entre movimentos demonstram que a origem não foi
  retirada.
- Uma repetição após falha demonstra convergência sem duplicação.
- Logs de completed, blocked e interrupted são validados por campos, não por
  texto livre.
- A documentação de configuração e o runbook explicam como declarar e remover
  um mapeamento após a conclusão.
