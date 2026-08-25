# Resultados de Teste — Corrigir `model` de exemplo inválido no `README.md`

Status: approved
Owner: quality
Last updated: 2026-08-25

## Inputs

- `doc/quality/problemas-execucao-kiro/test-cases-corrigir-model-exemplo-invalido-readme.md`
- Task #207 — Corrigir `model` de exemplo inválido no `README.md` (board Task)
- Ambiente: `kiro-cli 2.18.1` (pinado em `docker/versions.env`: `KIRO_CLI_VERSION=2.18.0`)

## CT-001 — Identificador de modelo escolhido é válido na versão pinada do `kiro-cli`

**Resultado:** failed

**Observações:**
- `kiro-cli --version` → `2.18.1`, mesma linha minor da versão pinada
  (`2.18.0`); considerado equivalente para este teste.
- `kiro-cli chat --model claude-sonnet-4-5 "oi" --no-interactive
  --trust-all-tools` → **falhou**: `error: Model 'claude-sonnet-4-5' does not
  exist. Available models: auto, claude-opus-5, claude-sonnet-5,
  claude-opus-4.8, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna, claude-opus-4.7,
  claude-opus-4.6, claude-sonnet-4.6, claude-opus-4.5, claude-sonnet-4.5,
  claude-sonnet-4, claude-haiku-4.5, deepseek-3.2, minimax-m2.5,
  minimax-m2.1, glm-5, qwen3-coder-next`.
- O identificador escolhido pela etapa de Desenvolvimento (`claude-sonnet-4-5`,
  com hífen) **não está** na lista de modelos disponíveis. O separador correto
  é ponto: `claude-sonnet-4.5` (confirmado na própria lista de erro retornada
  pelo CLI).
- Reconfirmação do defeito original: `kiro-cli chat --model
  claude-sonnet-4-20250514 ...` → `error: Model 'claude-sonnet-4-20250514'
  does not exist` (mesma lista de modelos disponíveis acima). Defeito original
  reproduzido como esperado.
- Testes adicionais de diagnóstico (fora do CT, para isolar a causa):
  `claude-sonnet-4.5`, `claude-sonnet-4` e `claude-sonnet-5` executam sem erro
  de modelo inexistente. Ou seja, a string trocada pela etapa de
  Desenvolvimento reproduz **o mesmo tipo de erro** que a issue pedia para
  corrigir — apenas com um identificador diferente, igualmente inválido.

## CT-002 — `README.md` usa o identificador válido no exemplo de `pipe.yml`

**Resultado:** failed

**Observações:**
- `README.md:50` contém `model: claude-sonnet-4-5`, exatamente como descrito
  no histórico de Desenvolvimento — nenhuma outra linha do bloco de exemplo
  foi alterada (diff isolado às commits da task, `git diff ad6e9bd HEAD --
  README.md`, mostra apenas essa linha).
- Reprovado por dependência do CT-001: a string presente é a que falhou na
  validação de existência do modelo. A parte textual/estrutural do critério
  (linha correta, formatação, isolamento do diff) está correta, mas o valor
  em si não é um identificador válido.

## CT-003 — Nenhuma ocorrência remanescente do identificador inválido no repositório

**Resultado:** passed

**Observações:**
- `grep -rn "claude-sonnet-4-20250514"` na raiz do repositório não retorna
  nenhuma ocorrência (nem prescritiva, nem histórica) na branch da task.
- Este teste valida apenas a ausência da string **antiga**; não cobre a
  validade da string nova (isso é CT-001/CT-002). O critério de aceite quanto
  a essa string específica está atendido.

## CT-004 — Nenhuma mudança fora do escopo documental

**Resultado:** passed

**Observações:**
- `git diff ad6e9bd HEAD --stat` (commits exclusivos desta task, isolando o
  branch base do PR anterior) mostra apenas dois arquivos alterados:
  `README.md` (1 linha) e o novo
  `doc/quality/problemas-execucao-kiro/test-cases-corrigir-model-exemplo-invalido-readme.md`.
- Nenhuma alteração em `src/`, `tests/`, `docker/`, `docker-compose.yml`,
  `compose.dev.yml` ou `pipe.yml` real.
- `docker/versions.env` não foi modificado por esta task (`KIRO_CLI_VERSION`
  permanece `2.18.0`).

## Resumo

- Total: 4
- Passou: 2 (CT-003, CT-004)
- Falhou: 2 (CT-001, CT-002)
- Bloqueado: 0

**Veredito:** reprovado. A troca de `claude-sonnet-4-20250514` para
`claude-sonnet-4-5` não corrige o defeito relatado na issue — o novo
identificador também não existe na versão de `kiro-cli` pinada (nem na
2.18.1 instalada neste ambiente), pelo mesmo motivo da string original: `kiro-cli chat --model claude-sonnet-4-5 ...` retorna `error: Model
'claude-sonnet-4-5' does not exist`. O identificador válido mais próximo é
`claude-sonnet-4.5` (separador ponto, não hífen). Devolvendo para
Desenvolvimento com essa observação.

— Camila Rocha - Engenheira de Qualidade (QA)
