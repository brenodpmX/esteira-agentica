# Casos de Teste — Emitir evento `rollout_evidence` (version/commit/environment) no startup

Status: draft
Owner: quality
Last updated: 2026-08-28

## Inputs
- Task #259 — Emitir evento `rollout_evidence` (version/commit/environment) no startup
- User Story #246 — Observabilidade de propagação/reconciliação/despacho e evidência de rollout
- ADR-003 (`doc/architecture/integridade-de-issues-entre-boards/decisions/adr-003-operacao-observavel-sem-nova-stack.md`)
- RN-B08 e RF-06 (`doc/requirements/integridade-de-issues-entre-boards/business-rules.md` e `functional-requirements.md`)

## CT-001 — `resolve_commit()` resolve via `git rev-parse HEAD` em checkout local

**Tipo:** unitário
**Critério de aceitação:** ADR-003 — "o commit vem do checkout [...]"; docstring de `resolve_commit()`, fonte 1.

**Pré-condição:**
- Diretório de trabalho é um repositório git válido com ao menos um commit (o próprio checkout de teste, ou repo git inicializado em `tmp_path` via `monkeypatch.chdir`).

**Passos:**
1. Chamar `resolve_commit()`.

**Resultado esperado:**
- Retorna string de 40 caracteres hexadecimais correspondente ao SHA do `HEAD` atual (idêntico ao resultado de `git rev-parse HEAD` executado no mesmo diretório).

## CT-002 — `resolve_commit()` cai para `BUILD_COMMIT_FILE` quando `git` não está instalado

**Tipo:** unitário
**Critério de aceitação:** docstring de `resolve_commit()`, fonte 1 indisponível → fonte 2; ADR-003 "Riscos: checkout sem `.git` não fornece commit [...] o build grava o hash em arquivo somente leitura".

**Pré-condição:**
- `subprocess.run` mockado para levantar `FileNotFoundError` (simula ausência do binário `git` no PATH).
- `BUILD_COMMIT_FILE` apontando (via monkeypatch) para um caminho inexistente (ex.: `tmp_path/inexistente`).

**Passos:**
1. Chamar `resolve_commit()`.

**Resultado esperado:**
- Retorna `None` (nenhuma exceção propagada).

## CT-003 — `resolve_commit()` cai para `BUILD_COMMIT_FILE` quando diretório não é repositório git

**Tipo:** unitário
**Critério de aceitação:** docstring de `resolve_commit()`, `returncode != 0` cai para fonte 2; ADR-003.

**Pré-condição:**
- `subprocess.run` mockado retornando `returncode=128` (equivalente a "não é um repositório git").
- `BUILD_COMMIT_FILE` (via monkeypatch) apontando para um arquivo existente com conteúdo `"abc123\n"`.

**Passos:**
1. Chamar `resolve_commit()`.

**Resultado esperado:**
- Retorna `"abc123"` (conteúdo do arquivo após `.strip()`, sem quebra de linha à direita).

## CT-004 — `resolve_environment()` retorna `None` quando `PIPE_ENVIRONMENT` está ausente

**Tipo:** unitário
**Critério de aceitação:** docstring de `resolve_environment()` — "None se ausente/vazia".

**Pré-condição:**
- Variável de ambiente `PIPE_ENVIRONMENT` removida (`monkeypatch.delenv("PIPE_ENVIRONMENT", raising=False)`).

**Passos:**
1. Chamar `resolve_environment()`.

**Resultado esperado:**
- Retorna `None`.

## CT-005 — `resolve_environment()` retorna o valor quando definido e normaliza espaços em branco para `None`

**Tipo:** unitário
**Critério de aceitação:** docstring de `resolve_environment()` — leitura e normalização de vazio.

**Pré-condição:**
- Caso A: `PIPE_ENVIRONMENT="production"`.
- Caso B: `PIPE_ENVIRONMENT="   "` (somente espaços).

**Passos:**
1. Chamar `resolve_environment()` em cada caso.

**Resultado esperado:**
- Caso A: retorna `"production"`.
- Caso B: retorna `None`.

## CT-006 — `emit_rollout_evidence()` emite evento completo quando commit e environment estão disponíveis

**Tipo:** unitário
**Critério de aceitação:** Critério de aceitação da story #246 — "um evento `rollout_evidence` é emitido com `version`, `commit`, `environment` e `started_at`".

**Pré-condição:**
- `resolve_commit()` e `resolve_environment()` mockados retornando valores não vazios.
- Spy/mock em `src.core.log.log.info`.

**Passos:**
1. Chamar `emit_rollout_evidence()`.

**Resultado esperado:**
- `log.info` é chamado exatamente uma vez com `event_type="rollout_evidence"` e `rollout_evidence_complete=True`.
- Os campos `version`, `commit`, `environment` e `started_at` estão presentes na chamada e nenhum deles é vazio.

## CT-007 — `emit_rollout_evidence()` registra ausência explícita quando falta apenas o commit

**Tipo:** unitário
**Critério de aceitação:** RN-B08 — "Ausência ou perda da evidência bloqueia o fechamento, não é aprovada por omissão."; docstring de `emit_rollout_evidence()`.

**Pré-condição:**
- `resolve_commit()` mockado retornando `None`.
- `resolve_environment()` mockado retornando um valor disponível.
- Spy/mock em `src.core.log.log.warning` e em `src.core.log.log.info`.

**Passos:**
1. Chamar `emit_rollout_evidence()`.

**Resultado esperado:**
- `log.warning` é chamado com `event_type="rollout_evidence"`, `rollout_evidence_complete=False` e `missing_fields=["commit"]`.
- `log.info` **não** é chamado com `event_type="rollout_evidence"` neste cenário (o evento não é emitido como completo por engano).

## CT-008 — `emit_rollout_evidence()` registra ausência explícita quando faltam commit e environment

**Tipo:** unitário
**Critério de aceitação:** RN-B08; docstring de `emit_rollout_evidence()`.

**Pré-condição:**
- `resolve_commit()` e `resolve_environment()` mockados, ambos retornando `None`.
- Spy/mock em `src.core.log.log.warning`.

**Passos:**
1. Chamar `emit_rollout_evidence()`.

**Resultado esperado:**
- `log.warning` é chamado com `rollout_evidence_complete=False` e `missing_fields=["commit", "environment"]`.

## CT-009 — `emit_rollout_evidence()` nunca levanta excecão e não interrompe o startup

**Tipo:** unitário
**Critério de aceitação:** docstring de `emit_rollout_evidence()` — "NUNCA levanta excecão nem impede o startup de continuar".

**Pré-condição:**
- `resolve_commit()` e `resolve_environment()` mockados retornando `None`.

**Passos:**
1. Chamar `emit_rollout_evidence()` dentro de um bloco que falharia o teste caso qualquer exceção fosse propagada.

**Resultado esperado:**
- A chamada retorna normalmente (`None`), sem exceção propagada.

## CT-010 — Evento `rollout_evidence` não expõe dados sensíveis

**Tipo:** unitário
**Critério de aceitação:** Critério de aceitação da story #246 — "Nenhum evento acima contém token, chave SSH, body completo de issue ou conteúdo de arquivo protegido".

**Pré-condição:**
- Mesmos mocks de CT-006 (cenário completo).

**Resultado esperado:**
- Os únicos campos de dados emitidos no evento são `version`, `commit`, `environment` e `started_at` (mais o marcador `rollout_evidence_complete`/`missing_fields`, quando aplicável) — nenhum token, chave SSH, body de issue ou conteúdo de arquivo protegido é incluído. Caso não se aplique ao payload real do evento, documentar essa constatação como comentário no teste, não sendo necessária asserção adicional além da verificação dos campos esperados em CT-006/CT-007/CT-008.
