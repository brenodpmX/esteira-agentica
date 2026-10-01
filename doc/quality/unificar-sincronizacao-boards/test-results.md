# Resultados de Teste — Unificar a sincronização de boards em um único modelo que sincroniza tudo

- **Issue:** #304
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Etapa:** Execução de Testes
- **Data:** 2026-10-01
- **Branch:** `feature/304-unificar-sincronizacao-boards`
- **Commit sob teste:** `f4e6541` (desenvolvimento) sobre `80ac89b` (especificação de casos)

---

## Veredito

**APROVADO.** Todos os casos de teste derivados dos critérios de aceitação
(CT-01 a CT-08, incluindo os desdobramentos `b`, de dependências e de
observabilidade) passam. O comportamento especificado foi implementado sem gaps
e sem violação de arquitetura. As 26 falhas remanescentes na suíte completa são
**pré-existentes e ambientais** — comprovadamente idênticas no baseline
`origin/main` sem as mudanças do #304 —, portanto **não constituem regressão**
desta entrega.

---

## Ambiente de execução

- `python -m pytest` — pytest 9.1.1, Python 3.12.14, Linux.
- Sem rede/subprocesso real nos casos do #304: `BoardPort` fake
  (`list_issues`/`get_issue`), `monkeypatch.chdir(tmp_path)` por teste.
- Baseline de comparação: worktree destacado em `origin/main` (`bd88e7d`),
  usado para isolar falhas pré-existentes das introduzidas pela mudança.

---

## 1. Execução dos testes pertinentes à mudança (#304)

Comando:

```
python -m pytest \
  tests/test_sync_unico.py tests/test_sync_unico_deps.py \
  tests/test_sync_unico_log.py tests/test_sync_unico_nomenclatura.py \
  tests/test_sync_unico_sem_segundo_modo.py tests/test_snapshot_legacy.py \
  tests/test_incremental_absent_delete_down.py tests/test_remedios_bloqueio.py \
  tests/test_sub_issue_propagation_fix.py tests/test_sync_optimization.py -v
```

Resultado: **73 passed in 1.69s** (0 falhas, 0 erros).

### Mapeamento CA/CT → caso pytest → resultado

| CA / CT | Caso pytest | Resultado |
|---------|-------------|-----------|
| CA-1 / CT-01 | `test_sync_unico.py::test_ct01_create_detected_single_run` | PASS |
| CA-1 / CT-01b (RN-01) | `test_sync_unico.py::test_ct01b_create_detected_even_with_hot_snapshot_and_old_updated_at` | PASS |
| CA-3 / CT-02 | `test_sync_unico.py::test_ct02_modification_detected_single_run` | PASS |
| CA-3 / CT-02b (RF-05) | `test_sync_unico_deps.py::test_ct02b_change_down_is_fullsync` | PASS |
| CA-3 / CT-02b (RF-05) | `test_sync_unico_deps.py::test_ct02b_dependencies_reconciled_after_apply` | PASS |
| CA-2 / CT-03 | `test_sync_unico.py::test_ct03_prune_absent_single_run` | PASS |
| CA-2 / CT-03b (RN-03) | `test_sync_unico.py::test_ct03b_prune_only_items_with_board_identity` | PASS |
| CA-6 / CT-04 (RN-02) | `test_sync_unico.py::test_ct04_penalty_during_read_does_not_prune_and_preserves_snapshot` | PASS |
| CA-4 / CT-05 (RF-06/RN-04) | `test_sync_unico_sem_segundo_modo.py::test_fullsync_not_used_as_down_scope_selector` | PASS |
| CA-4 / CT-05 | `test_sync_unico_sem_segundo_modo.py::test_no_last_board_update_cut_in_src` | PASS |
| CA-4 / CT-05 | `test_sync_unico_sem_segundo_modo.py::test_no_separate_full_sync_function_or_daily_trigger` | PASS |
| CA-5 / CT-06 (RF-07) | `test_sync_unico_nomenclatura.py::test_no_mode_qualifier_in_symbol_names` | PASS |
| CA-5 / CT-06 | `test_sync_unico_nomenclatura.py::test_no_mode_qualifier_in_log_literals` | PASS |
| CA-5 / CT-06 | `test_sync_unico_nomenclatura.py::test_sync_log_uses_single_name_contract` | PASS |
| CA-5 / CT-06b | `test_sync_unico_nomenclatura.py::test_config_has_no_sync_mode_key` | PASS |
| CA-5 / CT-06b | `test_sync_unico_nomenclatura.py::test_config_sync_max_attempts_still_valid` | PASS |
| CA-7 / CT-07 (RN-05) | `test_snapshot_legacy.py::test_ct07_legacy_snapshot_loads_without_error` | PASS |
| CA-7 / CT-07 | `test_snapshot_legacy.py::test_ct07_sync_runs_normally_over_legacy_snapshot` | PASS |
| CA-7 / CT-07b | `test_snapshot_legacy.py::test_ct07b_rewritten_snapshot_drops_legacy_cut_field` | PASS |
| CA-7 / CT-07b | `test_snapshot_legacy.py::test_ct07b_fresh_snapshot_has_no_cut_field` | PASS |
| RF-08 / CT-OBS-01 | `test_sync_unico_log.py::test_ct_obs01_success_log_contract` | PASS |
| RF-08 / CT-OBS-02 | `test_sync_unico_log.py::test_ct_obs02_penalty_log_limite_and_no_prune` | PASS |

Invariantes migrados/preservados (não deletados), também verdes:

- `test_incremental_absent_delete_down.py` (5) — poda por ausência, criação,
  modificação e delete+change combinados no caminho único.
- `test_sync_optimization.py` (16) — upgrade de `fullsync` na fila e **condição
  de parada** do gatilho de par recíproco (`test_pair_trigger_*`), garantindo
  que a reconciliação de deps em toda sincronização **não** gera reação em
  cadeia.
- `test_remedios_bloqueio.py` (10) e `test_sub_issue_propagation_fix.py` (23) —
  migrados de `detect_board_changes`→`sync_remote` sem perda de cobertura.

---

## 2. Validação independente de arquitetura (varredura estática, além dos testes de guarda)

Para não depender apenas dos testes de guarda do próprio desenvolvimento,
executei varredura direta em `src/` (CT-05/CT-06, RF-06/RF-07/RN-04/RNF-02):

- **`detect_board_changes`, `last_full_sync`, `list_issues_since`:** ausentes do
  código-fonte `.py` (só restam em artefatos `.pyc` de cache, irrelevantes).
  Caminho "completo" paralelo e acionamento diário **removidos**.
- **`last_board_update`:** única ocorrência em `src/core/snapshot.py:47`
  (`self._data.pop("last_board_update", None)`), que é exatamente a
  descontinuação retrocompatível (CT-07). **Não** é lido como critério de corte
  em nenhum ponto.
- **`fullsync` como seletor de escopo no down:** em `sync_remote`
  (`src/core/sync.py`), `create-down` e `change-down` são emitidos com
  `fullsync=True` **literal e incondicional** (linhas 689 e 701). Não há
  bifurcação "só propriedades" vs. "propriedades+deps". `fullsync` sobrevive
  apenas como atributo do mecanismo (buscar deps via REST) e no fluxo
  up/recíproco — papel explicitamente permitido pela QA em CT-05. **RN-04
  respeitado.**
- **Qualificadores de modo (`completo/completa/reduzido/incremental`):** as
  ocorrências restantes em `src/` são todas não-comportamentais e alheias à
  sincronização ("prompt completo", "throttle reduzido", "SET completo",
  "resumo completo"). Nenhuma qualifica a sincronização.
- **Contrato de log:** `sync_remote` emite
  `sincronizacao board=<id> criados=<n> atualizados=<n> removidos=<n> resultado=<ok|limite|erro>`,
  sem qualificador de modo e sem vazar corpo/credencial. Confere com RF-08 e com
  CT-OBS-01/02.
- **Atomicidade (RN-02):** `list_issues` é a primeira operação de `sync_remote`;
  `PenaltyException` propaga **antes** de qualquer avaliação de ausência/poda,
  logando `resultado=limite`.

---

## 3. Regressão geral (CT-08 / RNF-03)

Comando: `python -m pytest -q` (suíte inteira).

Resultado: **26 failed, 1273 passed, 17 skipped, 1 xpassed**.

### Análise de causa-raiz das 26 falhas

Comparei a suíte completa contra o baseline limpo `origin/main` (`bd88e7d`),
rodando os mesmos quatro arquivos num worktree destacado **sem** as mudanças do
#304:

```
# em worktree de origin/main:
python -m pytest tests/test_agent_log_descritivo.py \
  tests/test_agent_failure_detection.py \
  tests/test_docker_compose.py tests/test_dockerfile.py -q
# -> 26 failed, 222 passed, 6 skipped
```

O baseline reproduz **o mesmo conjunto de 26 falhas**. Classificação:

| Grupo | Qtd | Causa | Relação com #304 |
|-------|-----|-------|------------------|
| `test_agent_log_descritivo.py` | 18 | Estado global do singleton de log (ordem de testes) | Nenhuma |
| `test_agent_failure_detection.py::test_linha_de_inicio_preserva_formato_do_epic` | 1 | Falha isolada já presente no baseline | Nenhuma |
| `test_docker_compose.py` | 4 | Ambiente Docker ausente no container de teste | Nenhuma |
| `test_dockerfile.py` | 3 | SHA/versão pinada do ambiente (Dockerfile de teste simplificado) | Nenhuma |

Nenhuma dessas falhas toca os módulos alterados pelo #304
(`sync.py`, `board.py`, `snapshot.py`, `github_board.py`, `__main__.py`).
**Zero regressão introduzida pela entrega.** Essas falhas são de ambiente/escopo
alheio a esta issue (ponto de atenção para o time, fora do escopo do #304).

---

## 4. Conclusão e classificação

- **Comportamento especificado:** implementado integralmente (CT-01 a CT-08 e
  desdobramentos verdes).
- **Aderência à arquitetura:** verificada por testes de guarda **e** por
  varredura estática independente — modelo único, sem seletor de escopo, sem
  nomenclatura de modo, log no contrato mínimo, atomicidade preservada.
- **Regressão:** nenhuma atribuível ao #304; as 26 falhas são pré-existentes e
  ambientais, idênticas no baseline.

**Veredito final: APROVADO — avançar para Documentação.**

— Camila Rocha - Engenheira de Qualidade (QA)
