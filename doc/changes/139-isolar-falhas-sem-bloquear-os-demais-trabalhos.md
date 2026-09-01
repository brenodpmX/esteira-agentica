# Change File — Story #139: Isolar falhas sem bloquear os demais trabalhos

## Status

Encerrada por decisão humana em 2026-08-20 (comentários de 01:46 e 01:48 no
histórico da issue), após 12 verificações técnicas independentes ao longo do
dia confirmarem que os critérios de aceite já estavam satisfeitos por código
mergeado em `main`.

## O que foi entregue

A implementação dos 7 critérios de aceite da story **não ocorreu na branch
desta story** (`story139-139-isolar_falhas_sem_bloquear_os_demais_trabalhos`,
que permanece com 0 commits próprios). Ela foi feita e mergeada em `main`
por outra linhagem de branch, sob os ids das tasks originalmente planejadas
(#144 e #145), via:

- **PR #157** (branch `feature144-144-classificar_erros_de_sincronismo_e_impedir_head_of_line_blocking_na_fila`,
  merge commit `6168c68`) — commit `d7b69be`:
  - Classificador de erro estável (`classify_error` em `src/core/sync.py`):
    `rate_limit` (via `PenaltyException`), `definitivo` (mensagens estáveis
    de alvo inexistente) e `transitorio` (default seguro).
  - Contador de tentativas por item em `ChangeItem` (`change_queue.py`).
  - Limite de tentativas configurável em `pipe.yml`
    (`sync.max_attempts`), com `DEFAULT_MAX_ATTEMPTS = 3` e
    `validate_max_attempts` em `config.py` rejeitando valores não inteiros
    ou menores que 1.
  - `apply_changes()` em `sync.py` ajustado para nunca propagar exceção de
    um item e travar o ciclo inteiro: cada item é tentado no máximo uma vez
    por passagem (`tried_targets`); falhas transitórias voltam ao fim da
    fila via `queue.requeue`; os demais itens (mesmo board e outros boards)
    continuam a ser processados na mesma passagem.
  - Arquivos alterados: `board.py`, `change_queue.py`, `config.py`,
    `sync.py` (+127/-2).

- **PR #158** (branch `feature145-145-persistir_dead_letter_e_registrar_evidencia_acionavel_ao_isolar_item_da_fila`,
  merge commit `8a5678d`) — commit `b902239`:
  - Novo módulo `src/core/dead_letter.py` (157 linhas): `DeadLetterEntry` e
    `DeadLetterQueue`, persistência idempotente (por board+id+event) em
    `.pipe/deadLetter.json`, sobrevivente a reinício.
  - `sanitize_reason()` mascara `PROTECTED_PATHS` e tokens/credenciais
    antes de logar ou persistir o motivo do isolamento.
  - Log de isolamento em `sync.py` (`_isolate_in_dead_letter`) registra
    item, board, evento, motivo, tentativas, categoria e próximo passo.
  - `.pipe/deadLetter.json` adicionado a `PROTECTED_PATHS`
    (`src/core/agent.py`) e ao contexto gerado
    (`context_generator.py` / `.kiro/agents/pipe_context.json`).
  - Arquivos alterados: `agent.py`, `context_generator.py`, `dead_letter.py`
    (novo), `sync.py`, `pipe_context.json` (+200/-3).

- Suíte de teste dedicada: `tests/test_dead_letter.py` (600 linhas, 30+
  casos), já presente em `main`.

## Verificação dos critérios de aceite

| Critério de aceite | Status | Onde |
|---|---|---|
| Classificação estável de erro (definitivo/transitório/rate limit) | ✅ | `classify_error`, `sync.py` |
| Limite de tentativas configurável, default seguro, inteiro ≥ 1 | ✅ | `resolve_max_attempts`/`validate_max_attempts`, `config.py` |
| Tentativa única por item por passagem; demais itens continuam | ✅ | `apply_changes`, `sync.py` |
| Dead-letter persistente e idempotente, sobrevive a reinício | ✅ | `dead_letter.py` |
| Log de isolamento completo, sem expor segredos/paths protegidos | ✅ | `sanitize_reason`, `_isolate_in_dead_letter`, `sync.py` |
| Itens saudáveis (mesmo board e outros boards) avançam na mesma passagem | ✅ | `apply_changes`, `sync.py` |
| Erros definitivos não são retentados | ✅ | `classify_error` + `_isolate_in_dead_letter`, `sync.py` |

Todos os 7 critérios foram confirmados por leitura direta do código em
`main` (`git show origin/main:...`) em múltiplos ciclos de verificação
independentes (13:57 a 01:29 de 2026-08-19/20).

## Pendência conhecida, não bloqueante para o encerramento

A branch `story139-139-isolar_falhas_sem_bloquear_os_demais_trabalhos`
nunca recebeu o merge/rebase de `main` e permanece divergente (200+ commits
atrás, 0 commits próprios) — o código relevante chegou a `main` por outra
linhagem (tasks #144/#145 → PRs #157/#158), não por esta branch. Como não
há trabalho de código para publicar a partir desta branch, não é gerado
diff/PR de código para esta story; este arquivo documenta a entrega já
existente em `main` para efeito de rastreabilidade da story #139.

## Verificação do épico #104 (bloqueios)

Épico #104 (`/children #138, #139, #140, #141, #142`) declara
`/blocked_by #139` no body atual. Nenhuma outra story-filha do épico possui
arquivo ativo em `.pipe/boards/story/` nesta verificação (apenas #139 está
presente), e o único bloqueio declarado no épico é a própria #139.

Com a implementação dos critérios de aceite de #139 confirmada em `main` e
o encerramento desta story, **não há mais bloqueio pendente do lado desta
story para o épico #104**. O `/blocked_by #139` deve ser removido do body
do épico na próxima sincronização/reconciliação para permitir seu avanço,
condicionado à confirmação de que as demais filhas (#138, #140, #141, #142)
também estão concluídas — o que está fora do escopo de verificação desta
issue individual.

— Isabela Gomes - Tech Lead
