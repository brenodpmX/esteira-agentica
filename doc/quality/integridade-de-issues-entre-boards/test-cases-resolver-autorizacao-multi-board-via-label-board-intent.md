# Test Cases — Resolver autorização multi-board via label `board-intent-<board_id>`

**Issue:** #264
**Arquivo de Testes:** `tests/test_participation_policy.py`
**Função testada:** `src.core.participation_policy.authorized_boards(labels, config)`

## Resumo

12 testes unitários cobrindo:
1. Label válida com um único board
2. Sufixo inválido (board não configurado) com warning
3. Chave `platform` sempre inválida
4. Labels sem prefixo ignoradas silenciosamente
5. Múltiplas autorizações simultâneas
6. Lista vazia
7. Determinismo (ordem não importa)
8. Pureza: `labels` não é mutado
9. Pureza: `config` não é mutado
10. Mistura de labels válidas/inválidas
11. Config vazia (sem boards)
12. Case-sensitivity do prefixo

## Matriz de Cobertura

| Caso | Entrada | Resultado Esperado | Status |
|------|---------|-------------------|--------|
| CT01 | `["board-intent-epic"]` + `{"epic": {}}` | `{"epic"}` | ✓ |
| CT02 | `["board-intent-inexistente"]` + `{"epic": {}}` | `set()` + warning | ✓ |
| CT03 | `["board-intent-platform"]` + `{"platform": {...}, "epic": {}}` | `set()` + warning | ✓ |
| CT04 | `["backend", "agent-hub-high"]` + `{"epic": {}}` | `set()` (sem warning) | ✓ |
| CT05 | `["board-intent-epic", "board-intent-story"]` + `{epic, story}` | `{"epic", "story"}` | ✓ |
| CT06 | `[]` + `{"epic": {}}` | `set()` | ✓ |
| CT07 | Múltiplas ordens | Resultado idêntico | ✓ |
| CT08 | Mutação de `labels` | Não mutado | ✓ |
| CT09 | Mutação de `config` | Não mutado | ✓ |
| CT10 | Mistura válida/inválida | Apenas válidas | ✓ |
| CT11 | Config vazia | `set()` | ✓ |
| CT12 | Case-sensitive | Falso-positivo rejected | ✓ |

## Verificação de Pureza

- **CT08:** `labels` é lista; verificado que permanece igual pós-chamada.
- **CT09:** `config` é dict; verificado que não é modificado.
- Implementação: função **nunca modifica** argumentos (sem `labels.append()`, sem `config[...]  =`).

## Verificação de Warnings

- **CT02:** label `board-intent-inexistente` com sufixo inválido → `log.warning` chamado.
- **CT03:** label `board-intent-platform` (platform sempre excluída) → `log.warning` chamado.
- **CT04:** labels sem prefixo → **sem warning** (fora do escopo da função).

## Execução

```bash
cd /app/repo/main
python -m pytest tests/test_participation_policy.py -v
```

**Resultado esperado:** `12 passed`

## Regressão

Suíte completa antes desta issue: 1255 passed, 29 skipped, 1 xpassed, 21 failed.
Suíte após adição de `test_participation_policy.py`: 1267 passed, 29 skipped, 1 xpassed, 21 failed.
Delta: +12 passed (novos testes), 0 regressões.

---

## Rastreabilidade

- **RN-B04:** "Ausência de autorização é o padrão... board inexistente gera warning, sem conceder autorização."
- **ADR-001:** "`authorized`: board atual aparece na label reservada `board-intent-<board_id>` da issue."

---

**Status:** Homologado e aprovado (19/08/2026)
