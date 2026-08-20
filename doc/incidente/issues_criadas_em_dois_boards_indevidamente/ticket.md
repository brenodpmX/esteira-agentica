# Incidente — Issues criadas em dois boards indevidamente

Status: Fenômeno 1 implementado e homologado — veículo único #88 / PR #102; merge e deploy pendentes
Owner: engineering
Last updated: 2026-08-19

## Registro

> Contém informações preliminares do incidente/problema

### Descrição:
- Data: 2026-07-07
- Reportado por: observação de log (operação interna)

É fato que podemos permitir a criação de issue e vinculá-la a mais de um board, mas se olhar o log de hoje 07/07/2026, verá que diversos ids aparecerão em boards diferentes, mas sem um motivo real. Pode ser o agente que alucinou, a própria esteira que duplicou, ou até mesmo o GitHub criando um novo item ao identificar uma issue como filho. Precisamos identificar e impedir isto.

Uma issue pode estar em dois boards ao mesmo tempo, mas não temos hoje nenhum cenário onde isso se encaixaria corretamente — e quando tiver, tem que ser uma decisão consciente do próprio agente.

### Evidências

- Issues #20 e #21 presentes simultaneamente em `Pipe - User Stories` e `Pipe - Epics` (confirmado via GraphQL em 07/07/2026).
- Diretório `.pipe/boards/feature/` com snapshot rastreando #1 e #4, board `feature` removido do `pipe.yml` e project node ID `PVT_kwHOEY5qBc4BcHfF` retornando `NOT_FOUND` no GitHub.
- Log `2026-07-06.json`: `[epic] #16..#21 create-down` no mesmo ciclo em que `set_parent` foi chamado para stories do épico #1.
- Log `2026-07-07.json`: `[epic] #20 change-down` e `[epic] #21 change-down` (4x cada); `[feature] #1 down full` e `[feature] change-down #1 -> aguardando-stories`.

### Impacto:
- Execuções duplicadas de agente no board `epic` para issues que pertencem ao board `story` — custo direto de tokens.
- Agentes do fluxo de épicos podem ver e tentar trabalhar em stories que não pertencem ao fluxo.
- Erros `NOT_FOUND` recorrentes contra o project ID obsoleto do board `feature`.
- Risco crescente: escala com o número de novos épicos com sub-issues.

## Triagem

### Classificação:
Dois bugs de software distintos:
1. **Fenômeno 1** — Comportamento implícito do GitHub Projects V2: `set_parent` via `POST /repos/.../issues/:parent/sub_issues` adiciona automaticamente a sub-issue a todos os projetos onde o pai está presente. A esteira não trata esse efeito colateral e não possui primitiva de remoção de item de projeto.
2. **Fenômeno 2** — Snapshot órfão de board removido do `pipe.yml`: `_find_snapshot_issue` (sync.py) varre todos os diretórios físicos em `.pipe/boards/` sem filtrar pelos boards configurados, ativando o gatilho de par recíproco contra boards inexistentes.

### Severidade:
**P2 — Média** (problema com workaround disponível; sem perda de dados; impacto financeiro direto e recorrente, mas funcionalidade principal intacta)

### Prioridade:
Alta — o dano escala com o uso normal da esteira (criação de épicos com sub-issues).

### Workaround:
1. Remover #20 e #21 do projeto `Pipe - Epics` manualmente no GitHub (UI/Projects).
2. Remover as tags `/blocks #1` do body do épico nas issues #20 e #21 (o vínculo ativo que as mantém sincronizadas).
3. Apagar o diretório `.pipe/boards/feature/` localmente.

Atenção: o workaround mitiga o sintoma atual, mas **não impede recorrência** — qualquer novo épico com sub-issues reabre o Fenômeno 1.

## Análise Técnica

**Data:** 2026-07-07
**Responsável:** Bruno Ferreira - Engenheiro de Software SR.

### Causa raiz (nível de código)

**Fenômeno 1 — efeito colateral do GitHub não tratado.**
`github_board._add_sub_issue()` chama `POST /repos/.../issues/{parent}/sub_issues` (`replace_parent=True`). O GitHub Projects V2 propaga a sub-issue para todos os projetos onde o pai está (sem status). No ciclo seguinte, `detect_board_changes` (board.py) vê a issue como nova no board `epic` e enfileira `create-down` (`fullsync`). A esteira **não possui** primitiva de remoção de item de projeto (`removeProjectV2Item`/`deleteProjectV2Item` = 0 ocorrências no `src/`). Comportamento latente desde o 1º commit — só se manifestou quando passamos a criar épicos com sub-issues.

**Fenômeno 2 — snapshot órfão amplificado via gatilho recíproco.**
`_find_snapshot_issue` (sync.py:151) faz `BOARDS_DIR.glob("*/snapshot.json")` sem cruzar com `board.board_ids(config)`. Quando `_trigger_reciprocal_downs` processa o par `blocks/blocked_by` de #20/#21↔#1, encontra #1 no snapshot do board `feature` e enfileira `change-down` para `feature`. O `apply_changes` chama `get_issue(board_id='feature', …)` com project ID obsoleto → `NOT_FOUND`. Ativado na v1.3.0 (`5e1f07b`). O `board_full_sync` já usa `board.board_ids(config)` e não itera boards órfãos — a única porta de entrada do órfão é o `glob` sem filtro do `_find_snapshot_issue`.

### Risco da correção

O principal risco de regressão está no Fenômeno 1: um `deleteProjectV2Item` mal direcionado removeria a issue (e seu status) de um board legítimo. A guarda "só remover quando a issue chega a um segundo board sem status/coluna, e board ≠ board de origem" é o controle crítico.

### Custo estimado de correção

- **Fenômeno 2** (~0,5 dia): filtro em `_find_snapshot_issue` + limpeza de órfãos no `board_full_sync` + teste de regressão.
- **Fenômeno 1** (~1,5–2 dias): nova primitiva `deleteProjectV2Item` + guarda no `_apply_create_down` + testes cobrindo chegada por efeito colateral (remove), multi-board consciente (preserva) e issue de origem (nunca remove).

## Decisão de tratamento

**Opção escolhida: Opção 2 — Tasks de correção no board Task.**

### Motivos

O incidente tem severidade **P2 (média)**: a funcionalidade principal está intacta, não há perda de dados, há workaround disponível e o custo de correção é estimado em 2–3 dias/dev. Esses fatores não justificam tratamento como incidente produtivo (P1) com mobilização de guerra.

Os dois fenômenos têm causas raiz independentes e soluções cirúrgicas bem delimitadas. O caminho correto é criar uma task por fenômeno, priorizá-las no board Task e executar em sequência (Fenômeno 2 primeiro, por ser mais barato e de menor risco; Fenômeno 1 em seguida).

A ausência de cobertura de testes nesses caminhos de código é um risco adicional que as tasks devem endereçar.

## Tarefas de correção

- **Task — Fenômeno 2:** Filtrar `_find_snapshot_issue` por boards configurados + limpeza de diretórios órfãos no `board_full_sync` + testes de regressão.
- **Task — Fenômeno 1:** Implementar `deleteProjectV2Item` + guarda no `_apply_create_down` para remover issues adicionadas por efeito colateral do GitHub + testes cobrindo os três cenários (efeito colateral, multi-board consciente, board de origem).

## Ação proposta

**Decisão:** Opção 2 — Problema intermediário tratado via tasks de correção no board `task`.

Serão criadas **duas issues no board `task`**, uma por fenômeno, a serem executadas em sequência:

---

### Task 1 — Filtrar boards configurados em `_find_snapshot_issue` e limpar snapshots órfãos

**Board:** task | **Coluna:** backlog

**Conteúdo:**
```
# Filtrar boards configurados em _find_snapshot_issue e limpar snapshots órfãos

effort: low

## User Story
N/A — Correção de bug interno da esteira (Incidente #24).

## Descrição
A função `_find_snapshot_issue` em `sync.py` varre todos os diretórios físicos em
`.pipe/boards/` (glob sem filtro), incluindo diretórios de boards que foram removidos
do `pipe.yml`. Quando o gatilho de par recíproco (`_trigger_reciprocal_downs`) aciona
essa função, encontra snapshots de boards inexistentes e enfileira `change-down` contra
project IDs obsoletos, resultando em erros `NOT_FOUND` recorrentes.

Adicionalmente, o `board_full_sync` não limpa diretórios de boards removidos do
`pipe.yml`, deixando acúmulo de lixo ao longo do tempo.

## Escopo técnico
- Modificar `_find_snapshot_issue` para aceitar a lista de board IDs configurados e
  ignorar diretórios não presentes nessa lista.
- Propagar `board_ids` (ou `config`) até `_trigger_reciprocal_downs` para que o filtro
  seja aplicado.
- Adicionar limpeza de diretórios órfãos no `board_full_sync`: diretório presente em
  `.pipe/boards/` mas ausente no `pipe.yml` deve ser movido para lixeira (ex.:
  `.pipe/boards/.orphaned/<board_id>_<timestamp>/`) em vez de deletado diretamente.
- Aplicar o workaround imediato: deletar `.pipe/boards/feature/` (diretório órfão ativo).

## Fora de escopo
- Não alterar o comportamento de boards configurados.
- Não tratar o Fenômeno 1 (efeito colateral do GitHub em `sub_issues`) — escopo da
  próxima task.

## Critério de aceite
- `_find_snapshot_issue` não enfileira `change-down` para boards ausentes no `pipe.yml`.
- Diretórios órfãos em `.pipe/boards/` são movidos para lixeira no `board_full_sync`.
- Testes unitários cobrindo: (a) board configurado é processado; (b) board órfão é
  ignorado; (c) limpeza de diretório órfão no `board_full_sync`.
- Sem quebra de funcionalidades existentes.
```

---

### Task 2 — Tratar efeito colateral do GitHub em `sub_issues`: remover issues adicionadas indevidamente a boards

**Board:** task | **Coluna:** backlog

**Conteúdo:**
```
# Tratar efeito colateral do GitHub em sub_issues: remover issues adicionadas indevidamente a boards

effort: medium

## User Story
N/A — Correção de bug interno da esteira (Incidente #24).

## Descrição
Quando a esteira chama `set_parent` (via `POST /repos/.../issues/:parent/sub_issues`),
o GitHub Projects V2 adiciona automaticamente a sub-issue a todos os projetos onde o
pai está presente, sem status/coluna. No ciclo seguinte, `detect_board_changes` vê
essas issues como novas nos boards adicionais e enfileira `create-down`, fazendo a
esteira materializar e sincronizar issues em boards indevidos.

A esteira não possui hoje primitiva de remoção de item de projeto
(`removeProjectV2Item`/`deleteProjectV2Item` = 0 ocorrências no `src/`).

## Escopo técnico
- Implementar `remove_from_project(issue_id, project_id)` no adapter
  `github_board.py`, usando a mutation GraphQL `deleteProjectV2Item`. Requer
  resolução do `item id` do projeto via `content.projectItems`.
- Implementar guarda no `_apply_create_down`: ao receber um `create-down` para uma
  issue em um determinado board, verificar se a issue já existe em outro board
  configurado **com coluna/status definido** (board de origem legítimo). Se a issue
  chegou ao board atual **sem status** (efeito colateral), chamar `remove_from_project`
  para removê-la do board atual e interromper o processamento do `create-down`.
- A guarda deve preservar o cenário legítimo de multi-board (issue presente em dois
  boards por decisão consciente do agente, ambos com coluna definida).
- Aplicar workaround imediato: remover #20 e #21 do projeto `Pipe - Epics` no GitHub
  e retirar os vínculos `/blocks #1` do body do épico nessas issues.

## Fora de escopo
- Não interceptar `set_parent` ou `set_children` diretamente — a guarda fica
  centralizada no `_apply_create_down`.
- Não alterar o comportamento de issues legitimamente em múltiplos boards.

## Critério de aceite
- Issues adicionadas como efeito colateral de `sub_issues` são detectadas e removidas
  do board indevido antes de criar arquivos locais.
- Issues legitimamente em múltiplos boards (com coluna em ambos) são preservadas.
- A issue de origem (board onde a issue foi criada intencionalmente) nunca é removida.
- Testes unitários cobrindo os três cenários acima.
- Sem quebra de funcionalidades existentes.
- Issues #20 e #21 removidas do `Pipe - Epics` (verificável no GitHub).
```

## Consolidação do veículo de entrega (2026-08-03)

Por decisão humana registrada no débito #110, a correção será consolidada na
issue #88 e no PR #102. A retentativa #98 e o PR #103 foram cancelados para
eliminar duas implementações concorrentes nos mesmos pontos do código. A branch
cancelada permanece apenas como referência técnica; ela não deve ser mesclada
nem combinada integralmente com a branch #88.

O bug #106 concentra a correção do veículo escolhido. O commit `01f9e83`, da
retentativa cancelada, pode servir como fonte seletiva para a query GraphQL e
para testes, mas não deve ser aplicado por cherry-pick cego: além de conflitos
nos mesmos arquivos, seu pós-hook deixou de receber o board de origem e, por
isso, não prova que um item sem `Status` pertence a outro project antes de
removê-lo.

## Definição complementar para a correção #106

A entrega só pode ser considerada concluída quando atender simultaneamente aos
controles abaixo:

1. **API real de Projects V2:** o pós-hook deve consultar `projectItems` e
   `fieldValues` via GraphQL e remover por `deleteProjectV2Item`. Os endpoints
   REST `/issues/{n}/project_items` e `/project_items/{id}` não existem e não
   podem permanecer no caminho produtivo.
2. **Project de origem preservado:** `_add_sub_issue` deve continuar informando
   o board/project de origem. Mesmo se esse item estiver temporariamente sem
   `Status`, o pós-hook nunca pode removê-lo. Somente itens de **outros**
   projects, sem `Status`, são candidatos à limpeza. Item com coluna definida
   também é sempre preservado, inclusive em uso multi-board intencional.
3. **Prova de propagação no `create-down`:** `parent` isolado é contexto, não
   evidência suficiente. Uma issue nova, com parent e coluna vazia, pode ser
   legítima no board atual. O descarte exige evidência de que a própria issue já
   está registrada em outro board configurado com coluna conhecida. Sem essa
   evidência, aplica-se o fallback da primeira coluna e cria-se o estado local.
   Diretórios órfãos de boards fora da configuração não contam como prova.
4. **Falha não pode virar descarte silencioso:** o evento só é descartado depois
   de `remove_from_board` concluir. Falha na remoção deve propagar para a fila
   tentar novamente; registrar warning e retornar perderia a garantia
   *at-least-once* e deixaria o item remoto sem rastreamento local.
5. **Uma única implementação:** o PR #102 deve terminar com um pós-hook, uma
   primitiva de remoção e uma suíte canônica. Não manter os métodos das duas
   branches em paralelo.
6. **Conflito com `main`:** a atualização da branch deve preservar tanto esta
   seção de sub-issues propagadas quanto a documentação de parent recursivo já
   integrada em `main`; resolver o conflito removendo uma das duas análises não
   é aceitável.

### Matriz mínima de regressão

- pós-hook real usa GraphQL e não chama `_gh`/REST;
- item de outro project sem `Status` é removido;
- item do project de origem sem `Status` é preservado;
- item de qualquer project com `Status` é preservado;
- issue nova com parent, sem presença comprovada em outro board, é criada no
  board atual pelo fallback;
- issue sem coluna já registrada em outro board configurado é removida sem
  criar arquivos locais;
- falha de `remove_from_board` não consome silenciosamente o evento;
- fallback de `create_issue`, divergência de coluna vazia e reconciliação de
  `change-down` permanecem cobertos, sem ciclo de reintrodução do item removido.

## Resultado da entrega (2026-08-19)

Os controles acima foram implementados no retrabalho #106 (commit `a00ba7c`),
integrado à branch do veículo #88/PR #102. A implementação usa GraphQL real,
preserva o project de origem, exige prova de propagação no `create-down` e
possui suíte canônica sem `monkeypatch` do método sob teste. A branch foi
atualizada com `main` e a homologação foi aprovada em 19/08/2026.

O Fenômeno 1 está corrigido no veículo de entrega; merge do PR #102 e deploy
continuam necessários para disponibilidade em produção. O Fenômeno 2
(snapshots órfãos de boards removidos da configuração) permanece uma causa
independente e fora desta entrega, exceto por não poder fornecer evidência para
remoção. Resíduos anteriores, como #84/#85/#86, exigem limpeza manual com a
esteira parada.
