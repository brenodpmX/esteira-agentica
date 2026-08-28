# Resultados de Teste — Adicionar e validar a chave `safety.cross_board_parent_links` no `pipe.yml`

Status: approved
Owner: quality
Last updated: 2026-08-28

## Inputs

- `doc/quality/integridade-de-issues-entre-boards/test-cases-adicionar-e-validar-chave-safety-cross-board-parent-links.md`
- Issue #255 — Adicionar e validar a chave `safety.cross_board_parent_links` no
  `pipe.yml` (board Task, story pai #241)
- `tests/test_config_cross_board_parent_links.py`
- `src/core/config.py`

## CT01 — `validate_cross_board_parent_links` sem seção `safety` não levanta erro

**Resultado:** passed

**Observações:**
- `test_ct01_no_safety_section` passou. Leitura de
  `validate_cross_board_parent_links` em `src/core/config.py` confirma
  `safety_cfg = config.get("safety") or {}` seguido de retorno antecipado
  quando a chave está ausente.

## CT02 — `validate_cross_board_parent_links` com seção `safety` presente e chave ausente não levanta erro

**Resultado:** passed

**Observações:**
- `test_ct02_safety_present_key_absent` passou, confirmando que o retorno
  antecipado cobre tanto seção ausente quanto seção vazia.

## CT03 — `validate_cross_board_parent_links` aceita `"enabled"`

**Resultado:** passed

**Observações:**
- `test_ct03_accepts_enabled` passou. `"enabled" in CROSS_BOARD_LINKS_VALUES`.

## CT04 — `validate_cross_board_parent_links` aceita `"suspended"`

**Resultado:** passed

**Observações:**
- `test_ct04_accepts_suspended` passou. `"suspended" in CROSS_BOARD_LINKS_VALUES`.

## CT05 — `validate_cross_board_parent_links` rejeita variação de caixa (`"Enabled"`)

**Resultado:** passed

**Observações:**
- `test_ct05_rejects_case_variation` passou. A comparação `value not in
  CROSS_BOARD_LINKS_VALUES` é exata (sem `.lower()`/`.strip()`), rejeitando
  `"Enabled"`. Mensagem contém `safety.cross_board_parent_links` e o valor
  recebido via `{value!r}`.

## CT06 — `validate_cross_board_parent_links` rejeita valor string inválido (`"off"`)

**Resultado:** passed

**Observações:**
- `test_ct06_rejects_invalid_string` passou, mesma validação do CT05.

## CT07 — `validate_cross_board_parent_links` rejeita valor não-string (`True`)

**Resultado:** passed

**Observações:**
- `test_ct07_rejects_non_string` passou. `True not in {"enabled", "suspended"}`
  é `True` em Python (bool não colide com as strings do set), então o valor é
  rejeitado corretamente.

## CT08 — `resolve_cross_board_parent_links` retorna `"enabled"` por default

**Resultado:** passed

**Observações:**
- `test_ct08_default_enabled` passou. `(config.get("safety") or
  {}).get("cross_board_parent_links", "enabled")` com `config = {}` retorna
  `"enabled"`.

## CT09 — `resolve_cross_board_parent_links` retorna o valor configurado (`"suspended"`)

**Resultado:** passed

**Observações:**
- `test_ct09_returns_configured_value` passou. Teste adicional
  `test_safety_section_present_key_absent_defaults_enabled` (seção presente,
  chave ausente) também passou, reforçando a cobertura do default.

## CT10 — `load_current_config` reflete alteração em disco sem cache em memória

**Resultado:** passed

**Observações:**
- `test_ct10_reflects_disk_change_without_cache` passou: duas chamadas
  sucessivas em `tmp_path` isolado (`monkeypatch.chdir`), com o `pipe.yml`
  reescrito entre elas, retornam `"enabled"` e depois `"suspended"`,
  confirmando ausência de cache em memória — cada chamada abre e faz
  `yaml.safe_load` do arquivo novamente.

## CT11 — `load_current_config` sem `pipe.yml` no diretório atual levanta erro

**Resultado:** passed

**Observações:**
- `test_ct11_missing_pipe_raises` passou (`ConfigError` para arquivo
  ausente). Teste adicional `test_empty_pipe_raises` (arquivo vazio) também
  passou, cobrindo o segundo caso mencionado na issue ("Levanta ConfigError
  se o arquivo não existir **ou estiver vazio**").

## CT12 — `check_config()` rejeita `safety.cross_board_parent_links` inválido (integração)

**Resultado:** passed

**Observações:**
- `test_ct12_rejects_invalid_cross_board_value` passou. Confirma a chamada de
  `validate_cross_board_parent_links(config)` dentro de `check_config()`,
  logo após `validate_max_attempts(config)` e antes da validação de `git`
  (conferido por leitura direta do código-fonte).

## CT13 — `check_config()` sem a seção `safety` continua funcionando (regressão)

**Resultado:** passed

**Observações:**
- `test_ct13_without_safety_section_still_works` passou: `check_config()`
  retorna o dict de configuração normalmente, sem `safety` no resultado.
  Teste adicional `test_valid_suspended_passes_check_config` (valor válido
  `"suspended"` chega intacto ao dict retornado) também passou.

## CT14 — Não regressão da suíte existente

**Resultado:** passed

**Observações:**
- `python -m pytest tests/test_config_cross_board_parent_links.py -v` → 16
  passed (13 casos citados na issue + 3 casos extras de robustez: seção
  presente/chave ausente em `resolve`, arquivo vazio em `load_current_config`,
  valor válido `"suspended"` de ponta a ponta em `check_config`).
- `python -m pytest tests/ -k "config" -v` → 63 passed, 11 skipped. Nenhuma
  falha relacionada a `config.py`.
- Suíte completa (`python -m pytest tests/`) → **21 failed, 1271 passed, 29
  skipped, 1 xpassed**. As 21 falhas pertencem exclusivamente a
  `tests/test_agent_log_descritivo.py` (formato de log descritivo do agente)
  e `tests/test_dockerfile.py` (pinagem de versão/SHA256 do `kiro-cli` no
  Dockerfile) — sem qualquer relação com `safety.cross_board_parent_links`,
  `config.py` ou os arquivos alterados nesta task. `git status --short` na
  branch confirma árvore de trabalho limpa (nenhuma alteração de código de
  produção fora dos commits já registrados de Casos de Teste e
  Desenvolvimento), portanto as 21 falhas são pré-existentes na branch, não
  introduzidas por esta entrega.

## Resumo

- Total: 14
- Passou: 14
- Falhou: 0
- Bloqueado: 0

## Conclusão

Nenhuma dúvida ou ambiguidade encontrada nos casos de teste do documento de
qualidade: todos objetivos, com pré-condições, passos e resultados esperados
verificáveis diretamente por execução de `pytest` e leitura do código-fonte
alterado (`src/core/config.py`). Escopo respeitado nesta etapa — nenhum código
de produção, teste automatizado ou caso de teste foi criado ou alterado; apenas
execução e registro de resultado.

Critério de aceite da issue #255 atendido: a implementação segue exatamente o
padrão de referência (`validate_max_attempts`/`resolve_max_attempts`/
`DEFAULT_MAX_ATTEMPTS`) replicado para `safety.cross_board_parent_links`; o
código cobre os cenários descritos (ausência de chave/seção, valores válidos,
variação de caixa, valor inválido, tipo não-string, leitura sem cache,
arquivo ausente/vazio, integração com `check_config()`); os testes unitários
existem e passam (16/16); e não há quebra de funcionalidades existentes (as
21 falhas da suíte completa são pré-existentes e não relacionadas).

Aprovado — avançar para **advance** (merge-request).

— Camila Rocha - Engenheira de Qualidade (QA)
