# US — Declarar destino de migração e preparar a estrutura remota sem remover origens

Status: draft
Owner: product
Last updated: 2026-08-26

## Inputs
- `doc/requirements/migracao-de-boards/functional-requirements.md` (RF-001, RF-004, RF-013)
- `doc/requirements/migracao-de-boards/business-rules.md` (RN-002, RN-003, RN-010)
- `doc/requirements/migracao-de-boards/glossary.md`
- `doc/architecture/migracao-segura-colunas/overview.md`
- `doc/architecture/migracao-segura-colunas/decisions/adr-001-expandir-migrar-contrair-no-core.md`
- `doc/architecture/migracao-segura-colunas/decisions/adr-002-intencao-declarativa-e-retomada-remota.md`
- `doc/architecture/migracao-segura-colunas/constraints.md`

## Descrição

Como operador da esteira,
Quero declarar em `pipe.yml` o destino de uma coluna que estou retirando, e
que a esteira prepare a estrutura remota do board (crie o destino e demais
colunas desejadas) sem nunca remover uma opção de `Status` ainda em uso,
Para que a intenção de migração fique registrada de forma legível e
auditável antes de qualquer movimentação, sem risco de a estrutura remota
ficar inconsistente com o board durante a preparação.

## Regras de negócio

- RN-002: coluna ocupada exige destino único e explícito, do mesmo board,
  antes da retirada — este destino é declarado no mapa
  `boards.<board>.column-migrations` (origem → destino).
- RN-010: a validação de destino não pode aceitar coluna de outro board; a
  localidade do mapa dentro do próprio board impede isso por construção.
- Validação de forma (`config.py`): `column-migrations`, quando presente,
  deve ser um mapa de IDs de coluna não vazios. Validação semântica do
  destino (existência, board, self-reference) é responsabilidade da story de
  migração (não desta).
- A preparação da estrutura remota (`prepare_boards`) nunca remove uma opção
  de `Status` existente — apenas cria boards/campo/colunas ausentes e
  preserva todas as opções remotas atuais, inclusive as que estão em vias de
  retirada.

## Critérios de aceitação

- Dado um `pipe.yml` com `boards.<board>.column-migrations` contendo um mapa
  `<origem>: <destino>`, quando o `check_config` valida a configuração,
  então a validação aceita o mapa quando origem e destino são strings não
  vazias, e rejeita valores vazios ou tipos inválidos com mensagem
  acionável.
- Dado um board cuja configuração desejada inclui uma nova coluna de
  destino ainda não publicada no GitHub Project, quando a reconciliação de
  estrutura é executada, então a coluna de destino é criada no campo
  `Status` remoto antes de qualquer tentativa de migração.
- Dado um board com uma coluna que está sendo retirada da configuração
  (ausente de `boards.<board>.columns` mas presente no `column-migrations`
  como origem), quando a preparação da estrutura remota é executada, então a
  opção correspondente a essa coluna **não é removida** do campo `Status`
  remoto nesta etapa — apenas as fases de migração e contração (stories
  seguintes) podem autorizar a remoção.
- Dado um `BoardPort`, quando a preparação é chamada, então ela expõe uma
  operação de preparação não destrutiva distinta da operação de substituição
  exata de opções (`set_board_columns`), coerente com ADR-001, e o
  `GitHubBoardAdapter` preserva os IDs de options já existentes ao criar
  apenas as ausentes.
- A ausência de `column-migrations` no `pipe.yml` continua sendo uma
  configuração válida e não altera o comportamento vigente de boards sem
  retirada de coluna (compatibilidade retroativa).

## Não objetivos

- Migrar ou mover qualquer issue entre colunas (fica para a story de
  migração de coluna vazia e para a story de migração de coluna ocupada).
- Validar semanticamente se o destino declarado é válido (existe, é do
  mesmo board, não é a própria origem) — a validação de forma nesta story
  cobre apenas estrutura do mapa, não a coerência do valor.
- Retirar qualquer opção de `Status` do board remoto.
- Registrar evidência/observabilidade de tentativa de migração (fica para a
  story de bloqueio, retomada e observabilidade).

## Rastreabilidade

- RF-001, RF-004, RF-013 (functional-requirements.md).
- RN-002, RN-003 (validação de forma), RN-010 (business-rules.md).
- ADR-001 (fase "expandir"), ADR-002 (config declarativa `column-migrations`).
- Constraints: "A option da origem não pode ser omitida... enquanto uma
  leitura remota ainda retornar qualquer issue nela" (aplicada por
  construção: esta story nunca chama a operação de contração).
