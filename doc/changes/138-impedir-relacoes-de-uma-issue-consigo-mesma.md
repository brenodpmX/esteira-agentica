# Change #138 — Impedir relações de uma issue consigo mesma

- **Tipo:** correção de bug / hardening preventivo
- **Versão-alvo:** 1.8.3 (já presente em `main`)
- **Plataforma afetada:** todas (validação independe de board provider)
- **Compatibilidade:** sem mudança de schema ou de `pipe.yml`
- **Implementação:** commit `8f63809` (merge do PR #156, task #143), já em `main`
- **Story:** #138, épico #104 (post-mortem do incidente #97)

## Problema

No incidente #97, a esteira tentou aplicar `set_parent(76, 76)` — uma issue
sendo registrada como pai de si mesma — o que resultou em HTTP 422 e travou a
fila global de sincronismo por 2h37, pois o evento inválido permaneceu na
cabeça da fila. Não havia validação de auto-referência antes da primeira
chamada ao board, para nenhuma das quatro relações suportadas (`parent`,
`children`, `blocked_by`, `blocks`).

## Mudanças implementadas

- Nova função pura `sanitize_relations(issue_id, cmds)` em
  `src/core/commands.py`, que remove auto-referências de `parent`, `children`,
  `blocked_by` e `blocks` antes de qualquer chamada ao board:
  - `parent` autorreferente é descartado (`None`);
  - em `children`/`blocked_by`/`blocks`, somente o próprio ID é removido da
    lista — os demais IDs válidos continuam sendo processados;
  - normaliza os IDs para `str` antes de comparar;
  - função pura: não muta a instância de `IssueCommands` recebida (usa
    `dataclasses.replace`), não recebe `board_id` e não faz chamadas de rede.
  - função auxiliar `_sanitize_relations_with_discards` retorna também a lista
    de atributos onde houve descarte, para fins de log.
- Cada descarte gera um `log.warning` identificando board (quando aplicável),
  issue, relação e o ID descartado — sem exigir leitura de estado interno.
- Dois pontos de chamada em `src/core/sync.py`:
  - `_apply_create_up` — sanitiza os comandos da issue recém-criada antes de
    aplicar relações;
  - `_apply_change_up` — sanitiza os comandos antes de propagar mudanças
    locais para o board.
- Defesa em profundidade em `Board.apply_commands` (`src/core/board.py`):
  chama `_sanitize_relations_with_discards` novamente antes de aplicar
  labels/relações, garantindo que nenhuma auto-referência alcance o adapter
  mesmo que um caminho de código futuro esqueça de sanitizar antes.

## Validação

- `tests/test_sanitize_relations.py` — 29 testes cobrindo as quatro relações
  isoladas e combinadas no mesmo body, listas mistas (só o próprio ID é
  descartado, IDs válidos permanecem), não-mutação da entrada original,
  normalização de tipos (`int` vs `str`) e o cenário de regressão do
  incidente #97 (`set_parent(76, 76)`).
- Suíte completa executada nesta etapa: `989 passed, 28 skipped, 1 xfailed`.
  As 4 falhas observadas em `tests/test_version_bump.py` são pré-existentes e
  não relacionadas a esta story (checam um número de versão-alvo antigo,
  "1.6.0", desatualizado em relação à `VERSION` atual do projeto).

## Fora de escopo (conforme a story)

Classificação de erros da API, política de tentativas, dead-letter e
resolução da identidade de arquivos — cobertos por outras stories do épico
#104 (#139, #140, #141, #142).

## Observação sobre dependência

A task técnica #143 (`Validar auto-referência em relações
parent/children/blocked_by/blocks`), sub-issue desta story (`/children #143`
no body), foi concluída e mergeada (PR #156, commit `8f63809`), entregando
integralmente o escopo desta story.
