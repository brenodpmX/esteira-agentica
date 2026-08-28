# Casos de Teste — Resolver autorização multi-board via label `board-intent-<board_id>`

**Issue:** #264
**Função:** `authorized_boards(labels: list[str], config: dict) -> set[str]`
**Especificação:** RN-B04, ADR-001

## CT01: Label válida — autorização simples

**Entrada:**
```python
labels = ["board-intent-epic"]
config = {"boards": {"epic": {}, "story": {}}}
```

**Resultado esperado:**
```python
{"epic"}
```

**Justificativa:** label com prefixo `board-intent-` cuja sufixo `epic` existe em `config["boards"]` → board_id é autorizado.

---

## CT02: Sufixo inválido — board não configurado

**Entrada:**
```python
labels = ["board-intent-inexistente"]
config = {"boards": {"epic": {}}}
```

**Resultado esperado:**
```python
set()  # retorna vazio
# log.warning("Participation", "label 'board-intent-inexistente' ignorada - board 'inexistente' não configurado em pipe.yml")
```

**Justificativa:** sufixo `inexistente` não está em `config["boards"]` → ignorado com warning, sem levantar exceção.

---

## CT03: Chave `platform` nunca é válida

**Entrada:**
```python
labels = ["board-intent-platform"]
config = {"boards": {"platform": {...}, "epic": {}}}
```

**Resultado esperado:**
```python
set()  # retorna vazio
# log.warning("Participation", "label 'board-intent-platform' ignorada - board 'platform' não configurado em pipe.yml")
```

**Justificativa:** a chave `platform` em `config["boards"]` é sempre excluída da validação (não é um board, é metadata de plataforma). Mesmo que presente, nunca autoriza.

---

## CT04: Labels sem prefixo — ignoradas silenciosamente

**Entrada:**
```python
labels = ["backend", "agent-hub-high", "security"]
config = {"boards": {"epic": {}}}
```

**Resultado esperado:**
```python
set()  # retorna vazio, sem warnings
```

**Justificativa:** labels sem o prefixo `board-intent-` não são alvo da função. Ignoradas sem log (escopo diferente).

---

## CT05: Múltiplas autorizações simultâneas

**Entrada:**
```python
labels = ["board-intent-epic", "board-intent-story"]
config = {"boards": {"epic": {}, "story": {}}}
```

**Resultado esperado:**
```python
{"epic", "story"}
```

**Justificativa:** todas as labels com prefixo válido são processadas. Múltiplas labels válidas produzem conjunto com múltiplos elementos.

---

## CT06: Lista vazia

**Entrada:**
```python
labels = []
config = {"boards": {"epic": {}}}
```

**Resultado esperado:**
```python
set()
```

**Justificativa:** nenhuma label → conjunto vazio.

---

## CT07: Determinismo — ordem não importa

**Entrada (ordem 1):**
```python
labels = ["board-intent-epic", "board-intent-story", "board-intent-task"]
```

**Entrada (ordem 2):**
```python
labels = ["board-intent-task", "board-intent-epic", "board-intent-story"]
```

**Entrada (ordem 3):**
```python
labels = ["board-intent-story", "board-intent-task", "board-intent-epic"]
```

**Config (igual em todas):**
```python
config = {"boards": {"epic": {}, "story": {}, "task": {}}}
```

**Resultado esperado (em todas as ordens):**
```python
{"epic", "story", "task"}
```

**Justificativa:** `set` é não-ordenado. Resultado é idêntico independentemente da ordem de `labels`. Determinismo garantido por comparação de `set`.

---

## CT08: Pureza — `labels` não é mutado

**Entrada:**
```python
labels = ["board-intent-epic", "backend"]
labels_original = list(labels)
config = {"boards": {"epic": {}}}

result = authorized_boards(labels, config)

assert labels == labels_original  # lista não foi modificada
```

**Justificativa:** função não deve ter efeito colateral sobre argumentos.

---

## CT09: Pureza — `config` não é mutado

**Entrada:**
```python
config = {"boards": {"epic": {}, "story": {}}}
config_original = {"boards": {"epic": {}, "story": {}}}

result = authorized_boards(["board-intent-epic"], config)

assert config == config_original  # dict não foi modificado
```

**Justificativa:** função não deve ter efeito colateral sobre argumentos.

---

## Critério de Aceite (Validação)

- ✓ Todos os 9 casos acima passam com assertions exatas.
- ✓ Nenhuma exceção é levantada em cenários esperados (inclusive sufixo inválido).
- ✓ `log.warning` é chamado exatamente quando sufixo não existe em `config["boards"]` (não em outros casos).
- ✓ Função é pura (não mutaa `labels` nem `config`).
- ✓ Resultado é sempre um `set[str]` (conjunto de board_ids válidos).
