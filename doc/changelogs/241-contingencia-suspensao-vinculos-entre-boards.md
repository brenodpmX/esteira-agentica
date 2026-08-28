# Change File — Contingência de suspensão de vínculos entre boards #241

**Data:** 2026-08-28
**Issue:** #241 — Contingência de suspensão de vínculos entre boards
**Branch do épico:** `epic241-241-contingencia_de_suspensao_de_vinculos_entre_boards`
**Issue pai:** #230 — Integridade de issues entre boards (1 de 6)
**Status:** desenvolvimento e testes concluídos nas duas tasks filhas; integrado em `epic`

## Resumo

Story decomposta em duas tasks técnicas (#255 e #256), ambas encerradas, que
juntas disponibilizam uma contingência reversível para suspender apenas a
**criação de novos** vínculos pai/filho entre issues de boards distintos, sem
afetar relações já existentes, remoções ou vínculos dentro do mesmo board.

## Escopo entregue

### Task #255 — chave de configuração `safety.cross_board_parent_links`

PR #283 (commit `ad1da07`, merge em `epic`), em `src/core/config.py`:

- `CROSS_BOARD_LINKS_VALUES = {"enabled", "suspended"}`;
- `validate_cross_board_parent_links(config)` — valida a chave opcional
  `safety.cross_board_parent_links`, seguindo o padrão já existente de
  `validate_max_attempts`;
- `resolve_cross_board_parent_links(config)` — retorna o valor efetivo
  (default `"enabled"` quando a chave está ausente);
- `load_current_config()` — releitura do `pipe.yml` do disco sem cache em
  memória, condição necessária para a suspensão valer sem restart;
- integração da validação em `check_config()`.
- Testes: `tests/test_config_cross_board_parent_links.py`.

### Task #256 — gate de bloqueio em `Board.apply_commands`

PR #285 (commit `cdf79cf`, merge em `epic`), em `src/core/board.py` e
`src/core/sync.py`:

- `_is_cross_board_link_blocked(board_id, target_issue_id, resolve_board_fn)` —
  bloqueia apenas quando `cross_board_parent_links` resolve para `"suspended"`
  **e** o board do alvo é conhecido (via `resolve_board_fn`) **e** é diferente
  do board de origem. Issue não rastreada (`resolve_board_fn` retorna `None`)
  não é bloqueada nesta camada — sem prova de "outro board", não há decisão
  segura a tomar aqui;
- `Board.apply_commands` recebe o parâmetro opcional `resolve_board_fn`; sem
  ele, o gate é ignorado (comportamento anterior preservado);
- vínculo de `parent` bloqueado: não aplica `set_parent`, não entra nos
  deltas do gatilho de par recíproco, registra warning estruturado
  (`event_type="cross_board_link_blocked"`);
- vínculo de `children` bloqueado por item: como `children` é um conjunto,
  cada id novo é avaliado individualmente — parte pode ser aplicada e parte
  bloqueada na mesma chamada; remoções nunca são bloqueadas;
- `_apply_change_up` (`src/core/sync.py`) passa
  `resolve_board_fn=lambda tid: (_find_snapshot_issue(tid) or (None, None))[0]`,
  resolvendo o board da issue alvo a partir do snapshot já conhecido pelo
  core, sem criar ciclo de import entre `board.py` e `sync.py`.
- Testes: `tests/test_cross_board_contingency.py`.

### Débito #273 (resolvido durante a execução)

A primeira passagem de Casos de Teste da task #256 foi corretamente
interrompida por depender do contrato de configuração da task #255, ainda
não disponível em `epic`. A decisão de produto manteve a sequência
obrigatória #255 → #256 (sem placeholder nem contrato alternativo); resolvida
com o merge do PR #283, #256 retomou a partir do commit `ad1da07`. Documentado
em `doc/product/integridade-de-issues-entre-boards/273-resolucao-dependencia-255-256.md`.

## Comportamento resultante

- `cross_board_parent_links` ausente ou `"enabled"` → comportamento idêntico
  ao anterior, sem qualquer bloqueio.
- `cross_board_parent_links: "suspended"` → toda tentativa de criar um vínculo
  `parent`/`children` novo apontando para um board distinto (conhecido no
  snapshot) é recusada e registrada via log estruturado; vínculos existentes,
  remoções e relações dentro do mesmo board permanecem intactos.
- A releitura via `load_current_config()` (sem cache) permite ativar/desativar
  a suspensão editando `pipe.yml`, sem restart nem novo deploy.

## Não escopo (confirmado nas duas tasks)

- Classificação de intenção (`origin`/`authorized`/`propagated`/`unresolved`)
  e gate de `keep_task` — stories #242/#245, não tocadas.
- Reconciliação de participação já propagada — stories #243/#244, não
  tocadas.
- Reprodução automática, após reativação, de vínculos recusados durante a
  suspensão — não implementada, por não ser objetivo da story.
- `_add_sub_issue`/`ParticipationIntegrity` (adapter) — fora do único call
  site coberto (`Board.apply_commands`, via bloco `@---`).

## Verificação dos bloqueios do épico #230

Levantamento das 6 stories filhas de #230 (`/blocked_by #243, #244, #241,
#245, #246, #242`):

| Story | Situação |
|-------|----------|
| #241 — Contingência de suspensão de vínculos entre boards | tasks #255/#256 encerradas; este change file |
| #243 — Reconciliação imediata após vínculo pai/filho | em `change-file`, porém **ainda `/blocked_by #249, #250`** (tasks filhas próprias não concluídas) |
| #242 — Classificação de intenção de participação em board | em `aguardando-tasks` (planejamento técnico não concluído) |
| #244 — Reconciliação na descoberta remota com retentativa sem bloqueio | em `aguardando-tasks` |
| #245 — Gate de elegibilidade por intenção confirmada em `keep_task` | em `aguardando-tasks` |
| #246 — Observabilidade de propagação/reconciliação/despacho e evidência de rollout | em `aguardando-tasks` |

**Conclusão:** nem todos os bloqueios do épico #230 estão concluídos — apenas
#241 está de facto pronto nesta verificação; #243 continua bloqueada por suas
próprias tasks, e #242/#244/#245/#246 ainda não saíram da etapa de
planejamento técnico. O épico #230 **não** avança nesta execução; permanece em
sua coluna atual até que as 6 stories estejam efetivamente concluídas.

## Referências

- `doc/product/integridade-de-issues-entre-boards/273-resolucao-dependencia-255-256.md`
- `doc/quality/integridade-de-issues-entre-boards/test-cases-adicionar-e-validar-chave-safety-cross-board-parent-links.md`
- `doc/quality/integridade-de-issues-entre-boards/test-results-adicionar-e-validar-chave-safety-cross-board-parent-links.md`
- PR #283 (task #255) / PR #285 (task #256)

— Isabela Gomes - Tech Lead
