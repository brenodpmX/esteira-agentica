# Resultados de Teste — Corrigir `model` de exemplo inválido no `README.md`

Status: approved
Owner: quality
Last updated: 2026-08-25

## Inputs

- `doc/quality/problemas-execucao-kiro/test-cases-corrigir-model-exemplo-invalido-readme.md`
- Task #207 — Corrigir `model` de exemplo inválido no `README.md` (board Task)
- Ambiente: `kiro-cli 2.18.1` (pinado em `docker/versions.env`: `KIRO_CLI_VERSION=2.18.0`)
- Iteração 2 de Desenvolvimento (commit `3d407b6`), após reprovação registrada
  na iteração 1 (commit `12f2954`)

## CT-001 — Identificador de modelo escolhido é válido na versão pinada do `kiro-cli`

**Resultado:** passed

**Observações:**
- `kiro-cli --version` → `2.18.1`, mesma linha minor da versão pinada
  (`2.18.0`); considerado equivalente para este teste.
- `kiro-cli chat --model claude-sonnet-4.5 "oi" --no-interactive
  --trust-all-tools` → executa com sucesso (exit-code 0), sem erro de modelo
  inexistente.
- Reconfirmação do defeito original: `kiro-cli chat --model
  claude-sonnet-4-20250514 "oi" --no-interactive --trust-all-tools` →
  `error: Model 'claude-sonnet-4-20250514' does not exist. Available models:
  auto, claude-opus-5, claude-sonnet-5, claude-opus-4.8, gpt-5.6-sol,
  gpt-5.6-terra, gpt-5.6-luna, claude-opus-4.7, claude-opus-4.6,
  claude-sonnet-4.6, claude-opus-4.5, claude-sonnet-4.5, claude-sonnet-4,
  claude-haiku-4.5, deepseek-3.2, minimax-m2.5, minimax-m2.1, glm-5,
  qwen3-coder-next` — defeito original reproduzido como esperado, e
  `claude-sonnet-4.5` (ponto) está listado entre os modelos disponíveis.

## CT-002 — `README.md` usa o identificador válido no exemplo de `pipe.yml`

**Resultado:** passed

**Observações:**
- `README.md:50` contém `model: claude-sonnet-4.5` (separador ponto),
  identificador confirmado válido em CT-001.
- `git diff ad6e9bd HEAD -- README.md` mostra diff de exatamente uma linha
  nesse arquivo; nenhuma outra chave/indentação do bloco de exemplo
  (`name: engineering`, demais linhas) foi alterada.

## CT-003 — Nenhuma ocorrência remanescente do identificador inválido no repositório

**Resultado:** passed

**Observações:**
- `grep -rn "claude-sonnet-4-20250514" .` na raiz do repositório retorna
  apenas ocorrências dentro de
  `doc/quality/problemas-execucao-kiro/test-cases-corrigir-model-exemplo-invalido-readme.md`
  e deste próprio documento de resultados — registros factuais/históricos que
  descrevem o defeito original, não exemplo prescritivo de configuração.
- `README.md` e demais arquivos de setup (`.env.example`, `doc/**` de
  tutoriais) não contêm a string antiga.

## CT-004 — Nenhuma mudança fora do escopo documental

**Resultado:** passed

**Observações:**
- `git diff ad6e9bd HEAD --stat` (commits exclusivos desta task, isolando o
  branch base) mostra três arquivos alterados: `README.md` (1 linha) e os
  dois documentos de qualidade (casos de teste e este resultado).
- Nenhuma alteração em `src/`, `tests/`, `docker/`, `docker-compose.yml`,
  `compose.dev.yml` ou `pipe.yml` real.
- `docker/versions.env` não foi modificado por esta task (`KIRO_CLI_VERSION`
  permanece `2.18.0`).

## Resumo

- Total: 4
- Passou: 4 (CT-001, CT-002, CT-003, CT-004)
- Falhou: 0
- Bloqueado: 0

**Veredito:** aprovado. A correção da iteração 2 (`claude-sonnet-4.5`, com
ponto) substitui corretamente o identificador inválido original
(`claude-sonnet-4-20250514`) e o identificador intermediário também inválido
(`claude-sonnet-4-5`, com hífen, reprovado na iteração anterior). Todos os
critérios de aceite da issue #207 estão atendidos. Task avança para
**Merge Request**.

— Camila Rocha - Engenheira de Qualidade (QA)
