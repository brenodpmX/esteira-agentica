# Requisitos Funcionais — Migração Segura de Colunas de Boards

Status: aprovado
Owner: requirements
Last updated: 2026-08-22

## Inputs
- `/app/.pipe/boards/epic/requisitos/91-migracao_de_boards-body.md`
- `/app/.pipe/boards/epic/requisitos/91-migracao_de_boards-history.md`
- `doc/requirements/migracao-de-boards/glossary.md`
- `doc/requirements/migracao-de-boards/business-rules.md`
- `README.md` (seções "boards", "Loop Principal", "Rate Limit (GitHub)")
- `src/adapters/github_board.py` (`sync_boards`, `_update_status_options`)

Este documento especifica o comportamento funcional observável necessário
para atender ao body da issue #91 e às regras de negócio já acordadas. Não
define solução técnica, componentes, arquivos ou stories — isso é decisão de
arquitetura e de quebra em stories, consumidoras deste baseline.

## Atores

- **Operador da esteira**: pessoa que edita `pipe.yml` e decide retirar uma
  coluna da configuração de um board, com ou sem destino declarado. É quem
  recebe/age sobre o resultado de uma tentativa bloqueada (histórico, resposta
  7: "decisão de quem estiver usando a esteira").
- **Esteira (sistema)**: processo automatizado que detecta a divergência entre
  a configuração declarada e o estado do board remoto, e executa a migração
  e a retirada, com ou sem supervisão humana em tempo real (pode rodar em
  container, configuração em Git).
- **Board remoto (GitHub Projects V2)**: fonte de verdade do campo `Status` e
  da classificação de cada issue em uma coluna.

## Dados envolvidos

- **Configuração de colunas do board** (`pipe.yml`, `boards.<board>.columns`):
  lista ordenada de colunas declaradas para um board. A ausência de uma
  coluna anteriormente presente é o gatilho da retirada.
- **Destino declarado**: associação entre a coluna retirada e a coluna do
  mesmo board para onde suas issues devem ir. A forma de declaração é decisão
  de arquitetura; este requisito trata apenas da existência, validade e
  uso desse dado.
- **Classificação da issue (`Status`)**: coluna atual de cada issue no board
  remoto.
- **Evidência da tentativa**: contagem inicial, itens movidos, itens
  restantes e resultado, por tentativa de migração (ver RN-008).

## Fluxo principal — F-001: Retirada de coluna vazia

**Ator:** Esteira, acionada por uma retirada de coluna feita pelo Operador na
configuração.

1. O Operador remove uma coluna de `boards.<board>.columns` no `pipe.yml`.
2. A Esteira detecta a divergência entre a configuração declarada e as opções
   atuais do campo `Status` do board remoto.
3. A Esteira verifica a contagem de issues classificadas na coluna retirada,
   no board remoto, no momento da avaliação.
4. A contagem é zero.
5. A Esteira retira a opção correspondente do campo `Status` no board remoto.
6. A Esteira registra a evidência da tentativa: contagem inicial (zero),
   itens movidos (nenhum), itens restantes (nenhum), resultado (concluída).

**Critério de aceite (Dado/Quando/Então):**
- Dado um board com uma coluna configurada e sem nenhuma issue classificada
  nela, quando o Operador remove essa coluna da configuração, então a Esteira
  retira a opção correspondente no board remoto sem exigir destino e registra
  o resultado como concluído.

## Fluxo principal — F-002: Retirada de coluna ocupada com destino válido

**Ator:** Esteira.

1. O Operador remove uma coluna de `boards.<board>.columns` e declara um
   destino explícito para as issues dessa coluna, apontando para outra
   coluna do mesmo board presente na configuração resultante.
2. A Esteira detecta a divergência e verifica a contagem de issues
   classificadas na coluna retirada — a contagem é maior que zero.
3. A Esteira valida o destino declarado: existe, é do mesmo board, e não é a
   própria coluna em retirada nem outra coluna também em retirada na mesma
   operação.
4. O destino é válido.
5. A Esteira move cada issue da coluna de origem para o destino, preservando
   id, conteúdo, relações e demais atributos (RN-007).
6. Ao final, a Esteira confirma que a coluna de origem está vazia no board
   remoto.
7. A Esteira retira a opção correspondente do campo `Status` no board remoto.
8. A Esteira registra a evidência da tentativa: contagem inicial, itens
   movidos (igual à contagem inicial), itens restantes (zero), resultado
   (concluída).

**Critério de aceite (Dado/Quando/Então):**
- Dado um board com uma coluna configurada contendo N issues (N > 0) e um
  destino explícito válido para essa coluna, quando o Operador remove a
  coluna da configuração, então a Esteira move as N issues para o destino
  antes de retirar a opção correspondente no board remoto, preserva id,
  conteúdo, relações e demais atributos de cada issue, e registra contagem
  inicial N, itens movidos N, itens restantes 0 e resultado concluído.

## Fluxo alternativo — F-003: Destino ausente para coluna ocupada

**Ator:** Esteira.

1. O Operador remove uma coluna de `boards.<board>.columns`, sem declarar
   destino, e a coluna contém uma ou mais issues.
2. A Esteira detecta a divergência e verifica a contagem — maior que zero.
3. A Esteira verifica a ausência de destino declarado.
4. A Esteira não migra nenhuma issue e não retira a opção do campo `Status`
   no board remoto — a classificação atual de todas as issues da coluna
   permanece inalterada.
5. A Esteira registra a evidência da tentativa: contagem inicial, itens
   movidos (zero), itens restantes (igual à contagem inicial), resultado
   (bloqueada — destino ausente).

**Critério de aceite (Dado/Quando/Então):**
- Dado um board com uma coluna configurada contendo N issues (N > 0) e
  nenhum destino declarado para essa coluna, quando o Operador remove a
  coluna da configuração, então a Esteira não altera a classificação de
  nenhuma das N issues, não retira a opção correspondente no board remoto, e
  registra o resultado como bloqueado com contagem inicial N e itens
  restantes N.

## Fluxo alternativo — F-004: Destino inválido para coluna ocupada

**Ator:** Esteira.

1. O Operador remove uma coluna de `boards.<board>.columns` e declara um
   destino que não é válido — por exemplo, aponta para uma coluna
   inexistente na configuração resultante, para a própria coluna em
   retirada, ou para uma coluna de outro board.
2. A Esteira detecta a divergência e verifica a contagem — maior que zero.
3. A Esteira valida o destino declarado e identifica a invalidez.
4. A Esteira não migra nenhuma issue e não retira a opção do campo `Status`
   no board remoto.
5. A Esteira registra a evidência da tentativa: contagem inicial, itens
   movidos (zero), itens restantes (igual à contagem inicial), resultado
   (bloqueada — destino inválido), com identificação do motivo da
   invalidez.

**Critério de aceite (Dado/Quando/Então):**
- Dado um board com uma coluna configurada contendo N issues (N > 0) e um
  destino declarado que não corresponde a uma coluna válida do mesmo board,
  quando o Operador remove a coluna da configuração, então a Esteira não
  altera a classificação de nenhuma das N issues, não retira a opção
  correspondente no board remoto, e registra o resultado como bloqueado com
  o motivo da invalidez do destino.

## Fluxo alternativo — F-005: Falha ou interrupção durante a migração

**Ator:** Esteira.

1. Uma migração de coluna ocupada com destino válido está em andamento
   (F-002, passo 5).
2. Ocorre uma falha ou interrupção (ex.: indisponibilidade do provedor, rate
   limit, encerramento do processo) antes que todas as issues sejam movidas.
3. A Esteira preserva o estado: as issues já movidas permanecem no destino;
   as issues ainda não movidas permanecem na coluna de origem; a coluna de
   origem permanece ativa no board remoto (opção não é retirada).
4. A Esteira registra a evidência da tentativa: contagem inicial, itens
   movidos (parcial, no momento da interrupção), itens restantes
   (complementar), resultado (interrompida).
5. Em uma execução seguinte, a Esteira retoma a migração a partir do estado
   atual (RN-005, RN-006): reconhece os itens já movidos e migra apenas os
   itens restantes.

**Critério de aceite (Dado/Quando/Então):**
- Dado uma migração em andamento de N issues para um destino válido, quando
  ocorre uma falha após M issues terem sido movidas (0 ≤ M < N), então a
  Esteira preserva as M issues no destino, mantém as N-M issues restantes na
  origem, não retira a opção de `Status` da origem, registra o resultado
  como interrompido com itens movidos M e itens restantes N-M, e uma nova
  tentativa migra apenas as N-M issues restantes sem reprocessar as M já
  movidas e sem perder ou duplicar nenhuma das N issues originais.

## Fluxo alternativo — F-006: Issue chega à coluna de origem durante a migração

**Ator:** Esteira.

1. Uma migração de coluna ocupada com destino válido está em andamento.
2. Antes da retirada efetiva da opção de `Status`, uma issue adicional passa
   a ser classificada na coluna de origem (ex.: sincronização concorrente
   detecta uma mudança feita manualmente no board).
3. A Esteira verifica novamente a contagem da coluna de origem antes de
   confirmar a retirada (RN-004) e identifica que a coluna não está vazia.
4. A Esteira migra também a issue recém-chegada para o mesmo destino antes
   de retirar a opção de `Status`.

**Critério de aceite (Dado/Quando/Então):**
- Dado uma migração que já moveu todas as N issues inicialmente contadas,
  quando uma nova issue é classificada na coluna de origem antes da retirada
  efetiva, então a Esteira migra também essa issue para o destino antes de
  retirar a opção de `Status`, e o resultado só é registrado como concluído
  quando a coluna de origem está de fato vazia no momento da retirada.

## Requisitos funcionais consolidados

| ID | Requisito |
|---|---|
| RF-001 | A Esteira deve identificar, para cada coluna retirada da configuração, se ela está vazia ou ocupada no board remoto no momento da avaliação. |
| RF-002 | A Esteira deve concluir a retirada de uma coluna vazia sem exigir destino declarado. |
| RF-003 | A Esteira deve exigir um destino único e explícito, do mesmo board, para retirar uma coluna ocupada. |
| RF-004 | A Esteira deve validar que o destino declarado existe, pertence ao mesmo board e não coincide com a própria coluna em retirada nem com outra coluna também em retirada na mesma operação. |
| RF-005 | A Esteira deve bloquear a retirada e preservar a classificação atual de todas as issues quando o destino for ausente ou inválido. |
| RF-006 | A Esteira deve mover para o destino toda issue classificada na coluna de origem antes de retirar a opção correspondente do campo `Status`. |
| RF-007 | A Esteira deve preservar id, conteúdo, relações e demais atributos de cada issue durante a migração. |
| RF-008 | A Esteira deve confirmar que a coluna de origem está vazia no board remoto imediatamente antes de efetivar a retirada. |
| RF-009 | A Esteira deve preservar o estado (issues já movidas no destino, issues restantes na origem, coluna de origem ativa) quando a migração for interrompida ou falhar. |
| RF-010 | A Esteira deve permitir uma nova tentativa de migração sobre um estado parcialmente avançado, sem reprocessar itens já corretamente movidos. |
| RF-011 | A Esteira não deve perder nem duplicar nenhuma issue em razão de repetição da migração. |
| RF-012 | A Esteira deve registrar, para cada tentativa, contagem inicial, itens movidos, itens restantes e resultado (concluída, bloqueada ou interrompida), acessível sem leitura de arquivos internos protegidos. |
| RF-013 | A Esteira deve restringir a migração a um único board por operação de retirada. |

## Fora de escopo (herdado do body da issue #91)

- Migração entre boards.
- Destino diferente por issue dentro da mesma coluna retirada.
- Arquivamento ou encerramento como destino da migração.
- Limite de WIP.
- Novo fluxo de autorização para quem pode solicitar/aprovar a retirada.
- Formato de configuração, tecnologia ou arquitetura da solução.
- SLA de conclusão da migração.
