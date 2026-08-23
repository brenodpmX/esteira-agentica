# Glossário — Migração Segura de Colunas de Boards

Status: em elaboração
Owner: requirements
Last updated: 2026-08-22

## Inputs
- `/app/.pipe/boards/epic/requisitos/91-migracao_de_boards-body.md`
- `/app/.pipe/boards/epic/requisitos/91-migracao_de_boards-history.md`
- `README.md` (seções "boards", "Rate Limit (GitHub)")
- `src/adapters/github_board.py` (`sync_boards`, `_update_status_options`)

Este glossário fixa os termos usados nos demais artefatos de requisitos deste
épico, para eliminar ambiguidade entre negócio, arquitetura e QA.

## Termos

**Coluna**
Opção do campo `Status` de um board (Projects V2 no GitHub). Corresponde a uma
etapa do fluxo de trabalho (ex.: `todo`, `doing`, `done`) declarada em
`pipe.yml` sob `boards.<board>.columns`.

**Retirada de coluna**
Remoção de uma entrada de `boards.<board>.columns` no `pipe.yml`, detectada
pela esteira ao comparar a lista de colunas configurada com as opções do
campo `Status` existentes no board remoto.

**Coluna vazia**
Coluna que, no momento da avaliação, não possui nenhuma issue classificada
nela, no board em que a retirada foi solicitada.

**Coluna ocupada**
Coluna que possui uma ou mais issues classificadas nela, no board em que a
retirada foi solicitada, no momento da avaliação.

**Destino**
Coluna do **mesmo board** da coluna retirada, ainda presente na configuração
resultante, para a qual as issues de uma coluna ocupada devem ser movidas
antes da retirada se concluir.

**Destino explícito**
Destino declarado de forma inequívoca para a coluna retirada, associando-a a
exatamente uma coluna válida do mesmo board. A forma de declaração
(configuração, comando, parâmetro) é decisão de arquitetura e não é definida
neste baseline.

**Destino válido**
Destino explícito que aponta para uma coluna existente na configuração
resultante do mesmo board (não a própria coluna retirada, não uma coluna que
também está sendo retirada na mesma operação).

**Migração**
Operação de mover, para o destino, todas as issues que estavam classificadas
na coluna retirada, como pré-condição para a retirada.

**Retirada (de coluna)**
Efetivação da remoção da coluna da configuração publicada no board (remoção
da opção correspondente no campo `Status`), permitida apenas quando a coluna
está vazia.

**Issue sem coluna / issue órfã de classificação**
Issue cuja opção de `Status` no board deixou de existir ou não corresponde a
nenhuma coluna válida, ficando sem etapa de fluxo identificável. É o efeito
indesejado que este épico deve impedir (ver `README.md`, seção "boards" e
histórico da issue #91).

**Tentativa (de migração)**
Execução do fluxo de migração para uma retirada de coluna específica, do
início (contagem inicial) até um resultado (concluída, bloqueada ou
interrompida). Uma retirada pode exigir múltiplas tentativas até concluir.

**Contagem inicial**
Número de issues classificadas na coluna retirada no início de uma tentativa
de migração.

**Itens movidos**
Subconjunto das issues da contagem inicial que já foram reclassificadas com
sucesso para o destino durante a tentativa.

**Itens restantes**
Subconjunto das issues da contagem inicial ainda classificadas na coluna de
origem ao final (ou durante) de uma tentativa.

**Resultado da retirada**
Estado final de uma tentativa: concluída (coluna vazia e retirada efetivada),
bloqueada (destino ausente ou inválido) ou interrompida (falha durante a
migração, origem permanece ativa).

**Repetição segura / idempotência da migração**
Propriedade pela qual reexecutar a migração da mesma coluna, no mesmo estado
ou em estado parcialmente avançado, não perde nem duplica issues e chega ao
mesmo resultado final.

**Board**
Quadro de trabalho configurado em `pipe.yml` sob `boards.<board>`, mapeado
para um GitHub Project V2 (ver README, seção "boards").

**Mudança estrutural**
Alteração da lista de colunas configuradas para um board (adicionar,
remover, reordenar), em contraposição à movimentação individual de uma issue
entre colunas no fluxo normal de trabalho (`keep_task`, `on_in`/`on_out`).
Este épico trata exclusivamente da retirada de coluna como mudança
estrutural — não é uma regra geral de movimentação de trabalho (ver body da
issue #91, seção "Resultado a construir").

## Termos explicitamente fora de escopo deste glossário

- **Migração entre boards**: não faz parte deste épico (ver body da issue
  #91, seção "Escopo").
- **Arquivamento** e **encerramento**: não são destinos válidos para a
  migração tratada aqui.
- **WIP (limite de trabalho em progresso)**: não é considerado nesta
  proteção.
