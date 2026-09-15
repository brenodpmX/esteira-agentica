# Resultados de Execução — Migrar snapshots legados sem `participation_intent` no full sync de startup

- **Task:** #257 — Migrar snapshots legados sem `participation_intent` no full sync de startup
- **User Story:** #245 — Gate de elegibilidade por intenção confirmada em `keep_task`
- **Etapa:** Execução de Testes
- **Branch:** `task/257-migrar-snapshots-legados-sem-participation-intent`
- **Commit sob teste:** `c30dbaa` — Migrar snapshots legados sem participation_intent no full sync (#257)
- **Arquivo de teste:** `tests/test_participation_intent_migration.py`
- **Casos de teste:** `doc/quality/integridade-de-issues-entre-boards/casos-de-teste/test-cases-migrar-snapshots-legados-participation-intent.md`
- **Autor:** Camila Rocha - Engenheira de Qualidade (QA)

## Veredito

**APROVADO.** Todos os 7 casos de teste (CT-01..CT-07) passam. A aderência
arquitetural (CA1) foi validada. Nenhuma regressão foi introduzida por esta task
(as 22 falhas remanescentes da suíte completa são pré-existentes e sem relação
com este escopo — comprovado abaixo).

## Resumo

| Métrica | Valor |
|---------|-------|
| Total de casos | 7 (8 testes; CT-03 com 2 subcasos) |
| Passou | 7 (8 testes) |
| Falhou | 0 |
| Bloqueado | 0 |

## Resultado por caso

| Caso | Descrição | Critério | Teste | Status |
|------|-----------|----------|-------|--------|
| CT-01 | Issue em board único legado recebe `origin` | CA2, CA-Story, ADR-001 | `test_ct01_single_board_legacy_becomes_origin` | ✅ pass |
| CT-02 | Mesma issue em 2 boards configurados legados → `unresolved` em ambos | CA2, CA-Story, ADR-001, RN-B01 | `test_ct02_duplicate_across_configured_boards_becomes_unresolved` | ✅ pass |
| CT-03a | Entrada com `"authorized"` não é sobrescrita; par não migrado → `unresolved` | CA2, RN-B01 | `test_ct03_existing_value_not_overwritten_authorized` | ✅ pass |
| CT-03b | Entrada com `None` explícito não é sobrescrita (`not in` vs `.get`) | CA2, RN-B01 | `test_ct03_existing_none_not_overwritten` | ✅ pass |
| CT-04 | Entrada em board NÃO configurado não conta como duplicidade → `origin` | CA2 | `test_ct04_unconfigured_board_not_counted` | ✅ pass |
| CT-05 | Idempotência: 2ª execução não altera nada | CA2 | `test_ct05_idempotent` | ✅ pass |
| CT-06 | Salva apenas snapshots efetivamente alterados | CA1/CA2 | `test_ct06_saves_only_changed_snapshots` | ✅ pass |
| CT-07 | `board_full_sync` chama a migração após sync/detecção e antes de retornar | CA1, CA2, CA-Story | `test_ct07_board_full_sync_calls_migration_in_order` | ✅ pass |

## Comando de verificação e saída

### Arquivo de teste alvo

```
python -m pytest tests/test_participation_intent_migration.py -v
→ 8 passed in 1.57s
```

### Suíte filtrada (conforme especificado nos casos de teste)

```
python -m pytest tests/ -k "participation_intent or migration or full_sync" -v
→ 8 passed, 1164 deselected in 2.33s
```

### Suíte completa (CA4 — sem regressão)

```
python -m pytest
→ 22 failed, 1115 passed, 34 skipped, 1 xpassed in 35.28s
```

## Validação de aderência arquitetural (CA1)

- A função `migrate_legacy_participation_intent` reside no core em
  `src/core/participation_migration.py`.
- Imports do módulo: **apenas** `src.core.log` e `src.core.snapshot`.
  Nenhum import de adapter, `Board` ou `BoardPort` — **sem violação de
  camada**. Nenhum bug crítico de arquitetura registrado.
- A função é pura em I/O de rede: lê/escreve apenas os `snapshot.json` locais.
- Ponto de integração (`src/__main__.py`, `board_full_sync`): a chamada é a
  última instrução da função, **após** `board.sync_boards(config)` e o laço de
  `board.detect_board_changes(...)` — confirmado por leitura de código e pelo
  CT-07 (spy de ordem, sem rede).

## Análise das 22 falhas da suíte completa (pré-existentes)

As 22 falhas concentram-se em três arquivos sem qualquer relação com o escopo
desta task (migração de snapshots / `participation_intent`):

- `tests/test_dockerfile.py` — pinagem de versão / verificação SHA-256 do
  kiro-cli no Dockerfile;
- `tests/test_agent_log_descritivo.py` — formatação do log descritivo de agente;
- `tests/test_agent_failure_detection.py` — detecção de falha / formato da linha
  de início.

**Prova de pré-existência:** executando esses três arquivos no commit
`f86a786` (imediatamente anterior aos commits desta task, `12187c9` e
`c30dbaa`), o resultado é idêntico:

```
git checkout f86a786
python -m pytest tests/test_dockerfile.py tests/test_agent_log_descritivo.py tests/test_agent_failure_detection.py
→ 22 failed, 99 passed, 13 skipped
```

Portanto, as falhas **antecedem** esta entrega e **não** constituem regressão
introduzida pela task #257. CA4 satisfeito.

## Cobertura dos critérios de aceite

| Critério | Situação |
|----------|----------|
| CA1 — Implementação segue arquitetura | ✅ função pura no core, sem import de adapter (verificado + CT-01..CT-07) |
| CA2 — Código cobre o cenário descrito | ✅ `origin`/`unresolved`, não sobrescrita, board não configurado, integração (CT-01..CT-07) |
| CA3 — Testes unitários criados | ✅ `tests/test_participation_intent_migration.py` (8 testes) |
| CA4 — Sem quebra de funcionalidades | ✅ 22 falhas pré-existentes comprovadas em `f86a786`; nenhuma nova |
| CA-Story #245 — campo migrado antes do 1º `keep_task` | ✅ migração roda em `board_full_sync` (antes do loop), validado por CT-07 |

## Observações

- **CT-06 (otimização de escrita):** a implementação salva **apenas** os
  snapshots alterados (`changed_boards`), conforme a instrução explícita do
  escopo — não há desvio a reavaliar com o desenvolvedor.
- **CT-03 (ausente vs `None`):** ponto de maior risco de regressão silenciosa;
  a implementação usa `"participation_intent" in issue` (não `.get(...)`),
  cobrindo corretamente ambos os subcasos.
- Escopo mantido: não há teste extrapolando para política completa
  `origin/authorized/propagated`, gate em `keep_task`, label
  `board-intent-<board_id>` nem limpeza de resíduo — todos fora do escopo.

— Camila Rocha - Engenheira de Qualidade (QA)
