# Casos de Teste — Adicionar gate de `participation_intent` em `keep_task` com evento deduplicado

- **Task:** #258 — Adicionar gate de `participation_intent` em `keep_task` com evento deduplicado
- **User Story:** #245 — Gate de elegibilidade por intenção confirmada em `keep_task`
- **Arquivo de teste alvo:** `tests/test_participation_intent_gate.py` (novo) e/ou
  reuso da fixture de `tests/test_auto_advance_enqueue.py`
- **Autor:** Camila Rocha - Engenheira de Qualidade (QA)

## Rastreamento de critérios de aceitação

Critérios de aceite da task #258:
- **CA1** — Implementação segue arquitetura (gate lê exclusivamente o campo
  `participation_intent` já cacheado no snapshot local; **nenhuma** chamada de
  rede; nenhum uso de `BoardPort`/adapter dentro do gate).
- **CA2** — Código cobre o cenário descrito (gate nos dois pontos do laço de
  `keep_task`: auto-advance do `todo` e seleção para execução; evento
  `dispatch_blocked_unconfirmed_intent` deduplicado).
- **CA3** — Testes unitários criados.
- **CA4** — Sem quebra de funcionalidades existentes (suíte completa sem
  regressão; regressão do comportamento atual com o campo presente e válido).

Critérios de aceitação da story #245 (âncoras de negócio):
- **CA-Story-2** — Toda entrada sem intenção confirmada falha fechada (sem
  auto-advance, sem seleção, sem execução) e gera o evento
  `dispatch_blocked_unconfirmed_intent` de forma **deduplicada**.
- **CA-Story-7** — O código do gate **não** realiza nenhuma chamada de rede,
  verificável por inspeção/teste com fake `BoardPort` que falha se chamado.

Regras/decisões de referência:
- **RN-B01** — participação sem prova de intenção nunca é executável
  (falha fechada).
- **ADR-001** — "`keep_task` exige um desses valores [`origin`/`authorized`]
  além dos filtros atuais. Campo ausente, valor pendente ou conflito bloqueia
  auto-advance e despacho."
- **Overview / Constraints** — o gate acrescenta a condição
  `participation_intent in {origin, authorized}`; entradas sem o campo,
  pendentes ou conflitantes são ignoradas e geram o evento deduplicado; o gate
  não chama a API.

## Pré-condições comuns

- Ambiente isolado: `tmp_path` como cwd (`monkeypatch.chdir(tmp_path)`), snapshot
  local montado sem rede — mesmo padrão da fixture `task_board` de
  `tests/test_auto_advance_enqueue.py` e do `board_doing` de
  `tests/test_rerun_cooldown.py`.
- `config` mínimo com `boards.<board_id>.columns`, uma coluna elegível (com
  `agent` e `change.advance`) e, quando o caso exigir, `todo` apontando para a
  coluna de backlog com `change.advance`.
- Cada issue no snapshot é um `dict` livre (sem dataclass nova). O campo
  `participation_intent` é adicionado/omitido conforme o caso. `status == "ok"`
  e `id` presentes (pré-requisito já existente de `keep_task`).
- **Isolamento de caches de módulo entre testes** (fixture `autouse`):
  limpar `src.__main__._rerun_cache` **e** `src.__main__._unconfirmed_intent_logged`
  antes e depois de cada teste — mesmo padrão da fixture `cache_limpo` de
  `tests/test_rerun_cooldown.py`. Sem isso, a dedução em memória vaza entre
  testes e o caso CT-09 (dedup) fica flaky.
- Os arquivos `-body.md` das issues elegíveis **não** contêm bloco `@---` com
  `/need_human` nem `/blocked_by` (para que `_is_blocked` não interfira e o
  gate seja o único responsável pelo bloqueio no cenário testado).

---

## CT-01 — Issue com `participation_intent = "origin"` em coluna elegível é selecionada

- **Critério:** CA2, CA4 (regressão do comportamento atual, agora com o campo)
- **Tipo:** unitário
- **Pré-condição:** snapshot com uma issue em coluna elegível (com `agent` e
  `change.advance`), fora do `todo`, `status == "ok"`,
  `participation_intent == "origin"`, sem `/need_human`/`/blocked_by`, sem
  cooldown ativo.
- **Passos:**
  1. Montar snapshot e `config`.
  2. Chamar `keep_task(board_id, config)`.
- **Resultado esperado:** retorna o `dict` da tarefa (não `None`, não
  `AUTO_ADVANCED`); `result["issue"]["id"]` é o id da issue e
  `result["col_id"]` é a coluna elegível.

## CT-02 — Issue com `participation_intent = "authorized"` em coluna elegível é selecionada

- **Critério:** CA2, CA4
- **Tipo:** unitário
- **Pré-condição:** idêntica a CT-01, porém
  `participation_intent == "authorized"`.
- **Passos:**
  1. Montar snapshot e `config`.
  2. Chamar `keep_task(board_id, config)`.
- **Resultado esperado:** retorna o `dict` da tarefa correspondente à issue
  (mesma asserção de CT-01).

## CT-03 — Issue com `participation_intent = "propagated"` é ignorada na seleção

- **Critério:** CA2, CA-Story-2, RN-B01, ADR-001 (falha fechada)
- **Tipo:** unitário
- **Pré-condição:** única issue elegível na coluna, porém
  `participation_intent == "propagated"`.
- **Passos:**
  1. Montar snapshot e `config`.
  2. Chamar `keep_task(board_id, config)`.
- **Resultado esperado:** `keep_task` **não** seleciona a issue; como é a única,
  retorna `None`. A issue nunca vira `result["issue"]`.

## CT-04 — Issue com `participation_intent = "unresolved"` é ignorada na seleção

- **Critério:** CA2, CA-Story-2, RN-B01, ADR-001
- **Tipo:** unitário
- **Pré-condição:** idêntica a CT-03, porém
  `participation_intent == "unresolved"`.
- **Passos:**
  1. Montar snapshot e `config`.
  2. Chamar `keep_task(board_id, config)`.
- **Resultado esperado:** `keep_task` retorna `None` (issue ignorada).

## CT-05 — Issue **sem** o campo `participation_intent` é ignorada (falha fechada)

- **Critério:** CA2, CA-Story-2, RN-B01, ADR-001 ("campo ausente ... bloqueia")
- **Tipo:** unitário
- **Pré-condição:** única issue elegível na coluna, **sem** a chave
  `participation_intent` no dict do snapshot.
- **Passos:**
  1. Montar snapshot (dict da issue sem a chave) e `config`.
  2. Chamar `keep_task(board_id, config)`.
- **Resultado esperado:** `keep_task` retorna `None` — campo ausente é tratado
  como não confirmado (`_has_confirmed_intent` retorna `False`).
- **Observação:** este é o caso-guarda de falha fechada. Vale complementar com
  subcasos de valor `None` explícito e string vazia (`""`) — ambos devem
  retornar `None`, pois `_has_confirmed_intent` só aceita `"origin"`/`"authorized"`.

## CT-06 — `_has_confirmed_intent` (helper puro) — tabela-verdade

- **Critério:** CA1 (helper puro, sem I/O), CA2
- **Tipo:** unitário (direto no helper)
- **Pré-condição:** import de `_has_confirmed_intent` de `src.__main__`.
- **Passos:** chamar `_has_confirmed_intent({...})` para cada entrada abaixo.
- **Resultado esperado:**

  | `issue` | esperado |
  |---------|----------|
  | `{"participation_intent": "origin"}` | `True` |
  | `{"participation_intent": "authorized"}` | `True` |
  | `{"participation_intent": "propagated"}` | `False` |
  | `{"participation_intent": "unresolved"}` | `False` |
  | `{"participation_intent": None}` | `False` |
  | `{"participation_intent": ""}` | `False` |
  | `{}` (chave ausente) | `False` |
  | `{"participation_intent": "ORIGIN"}` (case) | `False` |
- **Observação:** confirma que o helper não faz I/O — recebe um `dict` puro e
  retorna `bool`, sem tocar disco/rede.

## CT-07 — Issue sem intenção confirmada na coluna `todo` NÃO sofre auto-advance

- **Critério:** CA2, CA-Story-2, RN-B01 (bloqueio de auto-advance)
- **Tipo:** unitário
- **Pré-condição:** `config` com `todo` apontando para a coluna de backlog (com
  `change.advance`). Única issue no `todo`, `status == "ok"`, sem intenção
  confirmada (ex.: `participation_intent == "propagated"` **ou** campo ausente).
- **Passos:**
  1. Montar snapshot e `config`.
  2. Espionar/patchar `src.__main__._auto_advance` (spy) para detectar chamada.
  3. Capturar estado inicial dos arquivos da issue e do snapshot.
  4. Chamar `keep_task(board_id, config)`.
- **Resultado esperado:**
  - `_auto_advance` **não** é chamado (spy sem chamadas).
  - Nenhum arquivo `-body.md`/`-history.md`/`-addcomment.md` é movido de coluna.
  - O snapshot **não** é alterado (mesma coluna, mesmo `status`).
  - `keep_task` **não** retorna `AUTO_ADVANCED` para essa issue nesse ciclo
    (como é a única issue, retorna `None`).

## CT-08 — Auto-advance do `todo` continua ocorrendo para issue COM intenção confirmada

- **Critério:** CA2, CA4 (regressão: auto-advance preservado quando confirmado)
- **Tipo:** unitário
- **Pré-condição:** `config` com `todo` (backlog com `change.advance`). Única
  issue no `todo`, `status == "ok"`, `participation_intent == "origin"`.
- **Passos:**
  1. Montar snapshot e `config`.
  2. Chamar `keep_task(board_id, config)`.
- **Resultado esperado:** `keep_task` retorna `AUTO_ADVANCED`; os arquivos são
  movidos para a coluna de destino e o snapshot é atualizado (comportamento
  histórico de `test_keep_task_returns_auto_advanced_for_todo`, agora
  condicionado à intenção confirmada).

## CT-09 — Duas issues na mesma coluna elegível: só a confirmada é candidata

- **Critério:** CA2, CA-Story-2 (bloqueada não afeta as demais elegíveis)
- **Tipo:** unitário
- **Pré-condição:** duas issues na mesma coluna elegível, ambas `status == "ok"`:
  - issue A com `participation_intent == "propagated"` (ou ausente) e
    `created_at` mais antigo;
  - issue B com `participation_intent == "origin"` e `created_at` mais recente.
- **Passos:**
  1. Montar snapshot e `config`.
  2. Chamar `keep_task(board_id, config)`.
- **Resultado esperado:** `keep_task` retorna a issue **B** (a confirmada),
  ignorando A mesmo sendo mais antiga. A presença da issue A bloqueada **não**
  altera a ordem/seleção entre as demais issues elegíveis.
- **Observação:** valida que o gate age como um `continue` no laço (mesma
  granularidade de `_is_blocked`/cooldown), sem interromper a varredura.

## CT-10 — Evento `dispatch_blocked_unconfirmed_intent` é deduplicado por (board, coluna, issue)

- **Critério:** CA2, CA-Story-2 (evento deduplicado)
- **Tipo:** unitário (com spy em `src.core.log.log.warning`)
- **Pré-condição:** única issue em coluna elegível, sem intenção confirmada
  (ex.: `participation_intent == "propagated"`). Cache
  `_unconfirmed_intent_logged` limpo (fixture `autouse`).
- **Passos:**
  1. Instalar spy/mock em `src.core.log.log.warning` (mesmo alvo importado por
     `src.__main__`), capturando chamadas e seus `kwargs`.
  2. Chamar `keep_task(board_id, config)` (1ª vez).
  3. Chamar `keep_task(board_id, config)` (2ª vez) **sem** mudar a issue de
     coluna.
- **Resultado esperado:**
  - O evento `dispatch_blocked_unconfirmed_intent` é emitido **exatamente uma
    vez** (apenas na 1ª chamada). Filtrar as chamadas do spy por
    `event_type == "dispatch_blocked_unconfirmed_intent"` e contar 1.
  - A chamada carrega os campos estruturados: `board_id`, `issue_id`, `col_id`
    e `participation_intent` (valor efetivo da issue, ex.: `"propagated"`).
  - Ambas as chamadas de `keep_task` retornam `None` (issue nunca despachada).

## CT-11 — Evento é re-emitido quando a issue muda de coluna (nova chave)

- **Critério:** CA2, CA-Story-2 (dedup expira por mudança de coluna)
- **Tipo:** unitário (spy em `log.warning`)
- **Pré-condição:** issue sem intenção confirmada, começando na coluna
  elegível X.
- **Passos:**
  1. Spy em `src.core.log.log.warning`.
  2. Chamar `keep_task` (emite evento para chave `(board, X, id)`).
  3. Mover a issue no snapshot para outra coluna elegível Y
     (novo `col_id`) e persistir.
  4. Chamar `keep_task` novamente.
- **Resultado esperado:** o evento `dispatch_blocked_unconfirmed_intent` é
  emitido **de novo** (total 2), pois a chave `(board, col_id, id)` mudou —
  confirma que a dedup é por coluna, não global.
- **Observação:** caso opcional/complementar; reforça a semântica de chave
  idêntica ao cache de cooldown. Se o desenvolvedor considerar fora do escopo
  mínimo, registrar como cobertura extra (não é violação de CA).

## CT-12 — Gate NÃO consome/reinicia o cooldown de reexecução

- **Critério:** CA2 (ordem: gate **antes** de `_in_rerun_cooldown`)
- **Tipo:** unitário
- **Pré-condição:** `config` com `boards.rerun_cooldown > 0`. Única issue em
  coluna elegível, sem intenção confirmada.
- **Passos:**
  1. Montar snapshot e `config` com cooldown ativo.
  2. Limpar `_rerun_cache`.
  3. Chamar `keep_task(board_id, config)`.
  4. Inspecionar `src.__main__._rerun_cache`.
- **Resultado esperado:** a issue não é selecionada (retorna `None`) e
  **nenhuma** entrada é gravada em `_rerun_cache` (a chave
  `(board, col_id, id)` não existe). Confirma que o gate roda **antes** de
  `_mark_rerun`/`_in_rerun_cooldown`, evitando consumir cooldown de uma issue
  que nunca é despachada.

## CT-13 — Gate não realiza chamada de rede (fake `BoardPort` que falha se chamado)

- **Critério:** CA1, CA-Story-7 (sem rede, verificável por fake `BoardPort`)
- **Tipo:** unitário (garantia arquitetural)
- **Pré-condição:** montar um fake `BoardPort` cujos métodos levantam
  `AssertionError`/`RuntimeError` se **qualquer** um for chamado. Substituir a
  instância global `src.__main__.board` (usada por `process_queue`/adapters)
  por esse fake durante o teste (monkeypatch). Snapshot local montado em
  `tmp_path`.
- **Passos:**
  1. Instalar o fake `BoardPort` que falha em qualquer método.
  2. Exercitar `keep_task` nos caminhos relevantes: issue confirmada
     (seleção), issue não confirmada (bloqueio + evento) e issue no `todo`
     não confirmada (sem auto-advance).
  3. Verificar que nenhum método do fake foi invocado.
- **Resultado esperado:** `keep_task` completa todos os caminhos **sem** tocar
  o fake `BoardPort` (nenhuma exceção do fake). Prova, por teste, que o gate
  opera apenas sobre `Snapshot`/dados locais — CA1 e CA-Story-7 satisfeitos.
- **Observação:** toda violação de camada (o gate tocar adapter/rede) é **bug
  crítico** na etapa de execução.

---

## Matriz de rastreamento

| Caso | CA1 | CA2 | CA3 | CA4 | CA-Story-2 | CA-Story-7 |
|------|-----|-----|-----|-----|------------|------------|
| CT-01 |  | ✓ | ✓ | ✓ |  |  |
| CT-02 |  | ✓ | ✓ | ✓ |  |  |
| CT-03 |  | ✓ | ✓ |  | ✓ |  |
| CT-04 |  | ✓ | ✓ |  | ✓ |  |
| CT-05 |  | ✓ | ✓ |  | ✓ |  |
| CT-06 | ✓ | ✓ | ✓ |  | ✓ |  |
| CT-07 |  | ✓ | ✓ |  | ✓ |  |
| CT-08 |  | ✓ | ✓ | ✓ |  |  |
| CT-09 |  | ✓ | ✓ |  | ✓ |  |
| CT-10 |  | ✓ | ✓ |  | ✓ |  |
| CT-11 |  | ✓ | ✓ |  | ✓ |  |
| CT-12 |  | ✓ | ✓ |  |  |  |
| CT-13 | ✓ |  | ✓ |  |  | ✓ |

## Observações

- **Aderência arquitetural (validada na execução):** o gate vive em
  `src/__main__.py` (helper `_has_confirmed_intent`, cache
  `_unconfirmed_intent_logged`, `_log_unconfirmed_intent_once`) e lê apenas o
  `dict` da issue já carregado do snapshot local. Nenhum import/uso de adapter
  ou `BoardPort` dentro do gate; nenhuma chamada de rede. Qualquer I/O de rede
  no caminho do gate = **bug crítico** (violação de camada) — coberto por CT-13.
- **Ordem dos filtros (risco de regressão):** o gate de intenção deve vir
  **antes** de `_in_rerun_cooldown` na seleção (CT-12) e **antes** de
  `_auto_advance` no `todo` (CT-07), replicando o early-continue já usado por
  `_is_blocked`/`block_auto_advance`.
- **Dedup em memória:** `_unconfirmed_intent_logged` é `set[tuple[str,str,str]]`
  de processo, sem persistência — mesmo comportamento efêmero do cache de
  cooldown. A dedup expira por mudança de coluna (nova chave, CT-11) ou reinício
  do processo. Não há expiração por tempo (fora de escopo persistir/expirar).
- **Fora de escopo (não testar aqui):** migração de snapshots legados (#257);
  classificação `origin`/`authorized`/`propagated`/`unresolved` na
  criação/reconciliação (outras stories); demais eventos de observabilidade
  além do `dispatch_blocked_unconfirmed_intent` mínimo (#246); persistência do
  cache de dedup.
- **Comando de verificação:**
  `python -m pytest tests/ -k "keep_task or participation_intent or auto_advance" -v`
  e a suíte completa `python -m pytest` sem regressão (CA4).
