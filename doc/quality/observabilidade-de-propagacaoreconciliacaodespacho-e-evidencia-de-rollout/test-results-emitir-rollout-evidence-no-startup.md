# Resultados de Teste — Emitir evento `rollout_evidence` (version/commit/environment) no startup

Status: approved
Owner: quality
Last updated: 2026-08-28

## Inputs

- `doc/quality/observabilidade-de-propagacaoreconciliacaodespacho-e-evidencia-de-rollout/test-cases-emitir-rollout-evidence-no-startup.md`
- Task #259 — Emitir evento `rollout_evidence` (version/commit/environment) no
  startup (board Task, story pai #246)

## CT-001 — `resolve_commit()` resolve via `git rev-parse HEAD` em checkout local

**Resultado:** passed

**Observações:**
- `test_ct001_resolve_via_git_rev_parse_em_checkout_local` passou: repo git
  real criado em `tmp_path`, `HEAD` resolvido via `resolve_commit()` é
  idêntico ao `git rev-parse HEAD` de referência, 40 caracteres hexadecimais.
- Leitura de `src/core/version.py` confirma `resolve_commit()` chamando
  `subprocess.run(["git", "rev-parse", "HEAD"], ...)` como fonte 1 e
  retornando `result.stdout.strip()` quando `returncode == 0` e não vazio.

## CT-002 — `resolve_commit()` cai para `BUILD_COMMIT_FILE` quando `git` não está instalado

**Resultado:** passed

**Observações:**
- `test_ct002_git_ausente_e_arquivo_inexistente_retorna_none` passou:
  `subprocess.run` mockado levantando `FileNotFoundError` e
  `BUILD_COMMIT_FILE` apontando para caminho inexistente → `None`, sem
  exceção propagada.
- Código confirma o `try/except Exception` em torno do `subprocess.run`,
  tratando qualquer falha (incluindo `FileNotFoundError`) como "fonte 1
  indisponível" e caindo para a verificação de `BUILD_COMMIT_FILE.exists()`.

## CT-003 — `resolve_commit()` cai para `BUILD_COMMIT_FILE` quando diretório não é repositório git

**Resultado:** passed

**Observações:**
- `test_ct003_nao_e_repo_git_cai_para_arquivo_de_build` passou: `returncode=128`
  simulado, arquivo de build com conteúdo `"abc123\n"` → retorno `"abc123"`
  (sem quebra de linha, via `.strip()`).
- Teste de reforço `test_timeout_do_git_cai_para_arquivo` (não listado no
  documento de casos de teste, mas coerente com a docstring — "Falhas do
  subprocess git (não é repo, git não instalado, **timeout**)") também
  passou: `subprocess.TimeoutExpired` cai para a fonte 2 corretamente.

## CT-004 — `resolve_environment()` retorna `None` quando `PIPE_ENVIRONMENT` está ausente

**Resultado:** passed

**Observações:**
- `test_ct004_ausente_retorna_none` passou com
  `monkeypatch.delenv("PIPE_ENVIRONMENT", raising=False)` → `None`.

## CT-005 — `resolve_environment()` retorna o valor quando definido e normaliza espaços em branco para `None`

**Resultado:** passed

**Observações:**
- `test_ct005_a_valor_definido` (`PIPE_ENVIRONMENT="production"` →
  `"production"`) e `test_ct005_b_apenas_espacos_normaliza_para_none`
  (`"   "` → `None`) passaram, cobrindo os dois casos (A e B) do CT-005.

## CT-006 — `emit_rollout_evidence()` emite evento completo quando commit e environment estão disponíveis

**Resultado:** passed

**Observações:**
- `test_ct006_evento_completo` passou: com `resolve_commit`/
  `resolve_environment` mockados retornando valores não vazios,
  `log.info` é chamado exatamente uma vez com `event_type="rollout_evidence"`
  e `rollout_evidence_complete=True`; campos `version`, `commit`,
  `environment`, `started_at` presentes e não vazios; `log.warning` não é
  chamado.

## CT-007 — `emit_rollout_evidence()` registra ausência explícita quando falta apenas o commit

**Resultado:** passed

**Observações:**
- `test_ct007_falta_apenas_commit` passou: `log.warning` chamado com
  `rollout_evidence_complete=False` e `missing_fields=["commit"]`; nenhuma
  chamada a `log.info` com `event_type="rollout_evidence"` no cenário
  incompleto (confirma que o evento não é emitido como completo por engano).

## CT-008 — `emit_rollout_evidence()` registra ausência explícita quando faltam commit e environment

**Resultado:** passed

**Observações:**
- `test_ct008_falta_commit_e_environment` passou:
  `missing_fields=["commit", "environment"]` e `rollout_evidence_complete=False`
  via `log.warning`.

## CT-009 — `emit_rollout_evidence()` nunca levanta exceção e não interrompe o startup

**Resultado:** passed

**Observações:**
- `test_ct009_nunca_levanta_excecao` passou: chamada com ambas as fontes
  retornando `None` completa normalmente (retorno `None`), sem exceção
  propagada — startup pode continuar mesmo sem evidência completa.

## CT-010 — Evento `rollout_evidence` não expõe dados sensíveis

**Resultado:** passed

**Observações:**
- Verificado por asserção em `test_ct006_evento_completo`: o conjunto exato
  de chaves emitidas no evento completo é
  `{event_type, version, commit, environment, started_at, rollout_evidence_complete}`
  — nenhum token, chave SSH, body de issue ou conteúdo de arquivo protegido.
- Leitura de `emit_rollout_evidence()` em `src/__main__.py` confirma que os
  únicos dados coletados são `VERSION` (constante de módulo),
  `resolve_commit()` e `resolve_environment()` — nenhuma outra fonte de dado
  é lida ou logada, tanto no ramo completo quanto no incompleto
  (`missing_fields` só nomeia `"commit"`/`"environment"`, nunca conteúdo).
- Conforme o próprio critério de aceite do CT-010, essa constatação é
  documentada em comentário no teste (`tests/test_rollout_evidence.py`,
  docstring do módulo e comentário no corpo de
  `test_ct006_evento_completo`), sem necessidade de asserção adicional.

## Resumo

- Total: 10
- Passou: 10
- Falhou: 0
- Bloqueado: 0

## Verificação de código e não regressão

- `python -m pytest tests/test_rollout_evidence.py -v` → 11 passed (os 10 CTs
  mais o teste de reforço de timeout do git).
- Suíte completa `python -m pytest tests/` → **1231 passed, 28 skipped, 1
  xpassed, 21 failed**. As 21 falhas pertencem exclusivamente a
  `tests/test_agent_log_descritivo.py` (formato de log de agente) e
  `tests/test_dockerfile.py` (ARGs de SHA256 do Dockerfile) — sem qualquer
  relação com `rollout_evidence`, `resolve_commit`, `resolve_environment` ou
  `src/__main__.py::main`. Confirmado com `git status` (working tree limpa
  nesta branch, sem diffs pendentes) executando a mesma suíte: as mesmas 21
  falhas ocorrem de forma independente das alterações desta task — são
  pré-existentes na branch, não introduzidas por ela.
- Leitura de `src/core/version.py` e `src/__main__.py` confirma a
  implementação fiel ao escopo técnico da issue: `BUILD_COMMIT_FILE`
  constante de módulo, `resolve_commit()` com ordem de fallback git → arquivo
  → `None`, `resolve_environment()` normalizando vazio/espaços para `None`,
  `emit_rollout_evidence()` chamada em `main()` imediatamente após o
  `log.info("Pipe", ...)` inicial e antes de `check_config()`, independente do
  resultado da validação de configuração.

## Conclusão

Nenhuma dúvida ou ambiguidade encontrada nos casos de teste: todos objetivos,
verificáveis por execução direta de `pytest` e leitura do código-fonte
alterado. Escopo respeitado — nenhuma alteração de código de produção, teste
ou caso de teste foi feita nesta etapa; apenas execução e registro. Critério
de aceite da issue #259 atendido: implementação segue a arquitetura descrita,
código cobre os cenários descritos (evento completo, ausência parcial e
total, nunca propaga exceção, sem dados sensíveis), testes unitários existem
e passam (11/11), e não há quebra de funcionalidades existentes (21 falhas
pré-existentes e sem relação com esta task).

Aprovado — avançar para **advance** (merge-request).

— Camila Rocha - Engenheira de Qualidade (QA)
