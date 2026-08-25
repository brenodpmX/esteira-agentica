# ADR-001 — Expandir, migrar e contrair colunas no core

Status: accepted
Owner: architecture
Last updated: 2026-08-25

## Inputs

- `/app/contexts/templates/docs/adr.md`
- `doc/architecture/migracao-segura-colunas/overview.md`
- `doc/architecture/migracao-segura-colunas/constraints.md`
- `doc/requirements/migracao-de-boards/functional-requirements.md`
- `doc/requirements/migracao-de-boards/business-rules.md`
- `src/core/board.py`
- `src/adapters/github_board.py`

## Contexto

O adapter atual recebe a lista final de colunas e a publica integralmente com
`updateProjectV2Field`. Quando uma option removida ainda é usada, a decisão
destrutiva ocorre antes de o sistema listar e reclassificar as issues.

A arquitetura precisa garantir que novas colunas existam antes dos movimentos,
que origens antigas permaneçam ativas durante falhas e que somente o core
decida quando uma opção pode ser retirada. Ao mesmo tempo, a solução deve
continuar simples, síncrona e compatível com os ports existentes.

## Decisão

Adotar reconciliação estrutural em três fases:

1. **expandir:** o adapter cria/resove boards e campo `Status`, adiciona opções
   desejadas ausentes e preserva todas as opções remotas atuais;
2. **migrar:** o core lista issues, valida o destino e move os itens ainda
   presentes na origem, relendo até confirmar drenagem ou ausência de
   progresso; e
3. **contrair:** o core autoriza a substituição exata das options somente após
   uma leitura remota imediatamente anterior confirmar origem vazia.

`Board.sync_boards(config)` permanece como fachada. `BoardPort` separa uma
operação de preparação não destrutiva de uma operação de substituição exata de
colunas. As primitivas `list_issues` e `move_issue` são reutilizadas.

A contração é feita por origem, preservando no payload todas as demais opções
configuradas ou temporariamente retidas. Isso permite que uma origem bloqueada
não impeça outra origem vazia ou migrada de concluir.

`board_full_sync` passa a gravar diretórios e mapa de colunas do snapshot depois
da reconciliação, usando a estrutura remota efetiva retornada pelo core.

## Justificativa

- É o menor desenho que impede a mutação destrutiva prematura.
- Mantém regra de negócio no domínio e GraphQL no adapter, coerente com a
  arquitetura hexagonal do projeto.
- Reutiliza listagem, movimentação, throttle, erros tipados e logging já
  existentes.
- A origem funciona como proteção natural contra falha parcial; não é preciso
  implementar rollback.
- O padrão expand-and-contract é adequado a mudança de schema com consumidores
  ainda ativos e é mais simples que uma saga ou workflow persistente.

Alternativas rejeitadas:

- **Migrar dentro do adapter:** mistura regra de negócio com GitHub e dificulta
  um futuro adapter de board.
- **Remover e reparar issues sem Status:** viola a invariável principal e perde
  a informação de origem.
- **Usar ChangeQueue para a estrutura:** mistura eventos de issue com schema,
  exige novo protocolo de dependência e não melhora a retomada.
- **Rollback de itens já movidos:** acrescenta chamadas e novos modos de falha;
  o estado parcial já é consistente e retomável.
- **Serviço/banco/workflow separado:** custo operacional sem necessidade para
  um loop sequencial e uma fonte remota de verdade.

## Consequências

- Positivas: a option da origem permanece durante migração/falha; execução é
  idempotente; adapters continuam substituíveis; bloqueios são isoláveis por
  origem; atributos das issues não são reenviados.
- Negativas: `BoardPort` ganha duas capacidades estruturais e os ports fake dos
  testes precisam ser atualizados; a listagem remota ocorre mais de uma vez por
  origem; o full sync muda de ordem.
- Riscos: uma origem sob fluxo contínuo pode não esvaziar; ausência de progresso
  deve interromper a tentativa sem retirar a option. O GitHub não oferece
  compare-and-swap da option contra contagem zero, deixando a janela externa
  descrita em `constraints.md`.
