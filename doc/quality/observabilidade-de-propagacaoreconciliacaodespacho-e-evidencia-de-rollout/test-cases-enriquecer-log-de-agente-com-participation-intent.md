# Casos de Teste — Enriquecer log de execução do agente com `participation_intent` e board de origem

Status: draft
Owner: quality
Last updated: 2026-08-28

## Inputs
- Task #262 — Enriquecer log de execução do agente com `participation_intent` e board de origem
- User Story #246 — Observabilidade de propagação/reconciliação/despacho e evidência de rollout
- RF-07 e RN-B09 (`doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md` e `business-rules.md`)
- Código de referência: `src/core/agent.py` (`AgentParams`), `src/__main__.py` (`call_agent`),
  `src/adapters/kiro_cli_agent.py` (`KiroCliAgent._build_log`)

## CT-001 — `AgentParams` aceita `participation_intent` com default `None`

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 1 — campo opcional novo com default, para não quebrar chamadas posicionais existentes.

**Pré-condição:**
- Nenhuma (construção direta da dataclass).

**Passos:**
1. Construir `AgentParams(...)` informando apenas os campos obrigatórios já existentes hoje (sem `participation_intent`), como já é feito nos testes atuais (ex.: `tests/test_agent_log_descritivo.py::_make_params`).

**Resultado esperado:**
- Construção não lança `TypeError`.
- `params.participation_intent is None`.

## CT-002 — `AgentParams` aceita `participation_intent` preenchido

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 1.

**Pré-condição:**
- Nenhuma.

**Passos:**
1. Construir `AgentParams(...)` informando `participation_intent="origin"`.

**Resultado esperado:**
- `params.participation_intent == "origin"`.

## CT-003 — Campo `participation_intent` existe na dataclass `AgentParams`

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 1.

**Pré-condição:**
- Nenhuma.

**Passos:**
1. Inspecionar `dataclasses.fields(AgentParams)`.

**Resultado esperado:**
- Existe um campo de nome `participation_intent` na lista de campos.

## CT-004 — `call_agent` propaga `participation_intent` do dict da issue quando presente

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 2 — `participation_intent=issue.get("participation_intent")`.

**Pré-condição:**
- Task simulada (padrão de `TestCallAgentPopulaNovosCampos` em `tests/test_agent_log_descritivo.py`) cuja `issue` (dict) contém a chave `"participation_intent": "origin"`.
- `AgentPort` (adapter) mockado para capturar o `AgentParams` recebido em `execute`.

**Passos:**
1. Chamar `call_agent(config, task)`.

**Resultado esperado:**
- O `AgentParams` capturado tem `participation_intent == "origin"`.

## CT-005 — `call_agent` resulta em `participation_intent=None` quando a chave está ausente na issue

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 2 — comportamento aceito no período de transição (campo ainda não escrito pela story #245).

**Pré-condição:**
- Task simulada cuja `issue` (dict) **não** contém a chave `"participation_intent"`.
- `AgentPort` mockado para capturar o `AgentParams` recebido em `execute`.

**Passos:**
1. Chamar `call_agent(config, task)`.

**Resultado esperado:**
- O `AgentParams` capturado tem `participation_intent is None`.
- Nenhuma exceção é lançada (`issue.get(...)` não deve quebrar por ausência de chave).

## CT-006 — `_build_log` inclui a linha `participation_intent` com valor preenchido

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 3.

**Pré-condição:**
- `AgentParams` construído com `participation_intent="authorized"`.

**Passos:**
1. Chamar `KiroCliAgent()._build_log(params)`.

**Resultado esperado:**
- O markdown resultante contém a linha `- **participation_intent**: authorized`.

## CT-007 — `_build_log` usa o placeholder `(ausente)` quando `participation_intent` é `None`

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 3 — placeholder explícito, linha nunca omitida.

**Pré-condição:**
- `AgentParams` construído sem informar `participation_intent` (ou explicitamente `None`).

**Passos:**
1. Chamar `KiroCliAgent()._build_log(params)`.

**Resultado esperado:**
- O markdown resultante contém a linha `- **participation_intent**: (ausente)`.
- A linha não é omitida (está presente mesmo com valor ausente).

## CT-008 — `_build_log` mantém a posição da linha `participation_intent` entre `coluna` e `issue`

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 3 — "imediatamente após a linha `coluna` e antes de `issue`".

**Pré-condição:**
- `AgentParams` construído com `col_id`, `issue_id` e `participation_intent` preenchidos.

**Passos:**
1. Chamar `KiroCliAgent()._build_log(params)`.
2. Localizar os índices das linhas `- **coluna**: ...`, `- **participation_intent**: ...` e `- **issue**: ...` no markdown resultante.

**Resultado esperado:**
- A ordem das linhas é exatamente: `coluna` → `participation_intent` → `issue` (índice da linha `coluna` < índice da linha `participation_intent` < índice da linha `issue`).

## CT-009 — Regressão: demais linhas do bloco `## Parâmetros` continuam presentes e na mesma ordem relativa

**Tipo:** unitário
**Critério de aceitação:** Seção "Como testar" da issue — "as demais linhas [...] continuam presentes e na mesma ordem relativa entre si".

**Pré-condição:**
- `AgentParams` construído com todos os campos do bloco `## Parâmetros` preenchidos (`platform`, `agent_name`, `model`, `board_id`, `col_id`, `issue_id`, `repo_id`, `work_dir`) e `participation_intent` preenchido.

**Passos:**
1. Chamar `KiroCliAgent()._build_log(params)`.

**Resultado esperado:**
- As linhas `plataforma`, `agente`, `model`, `board`, `coluna`, `issue`, `repo` e `work_dir` continuam presentes no markdown.
- A ordem relativa entre essas oito linhas permanece a mesma de antes da mudança (a nova linha `participation_intent` é uma inserção entre `coluna` e `issue`, não uma reordenação das demais).

## CT-010 — Regressão: `_build_log` sem `repo_id`/`work_dir` continua omitindo essas linhas condicionalmente

**Tipo:** unitário
**Critério de aceitação:** Regressão de comportamento existente (`if params.repo_id` / `if params.work_dir`), não deve ser afetado pela mudança.

**Pré-condição:**
- `AgentParams` construído com `repo_id=None` e `work_dir=""`, e `participation_intent` preenchido.

**Passos:**
1. Chamar `KiroCliAgent()._build_log(params)`.

**Resultado esperado:**
- As linhas `- **repo**: ...` e `- **work_dir**: ...` não aparecem no markdown (comportamento condicional preexistente preservado).
- A linha `- **participation_intent**: ...` aparece normalmente.

## CT-011 — Board de origem é o `board_id` já existente, sem campo novo

**Tipo:** unitário
**Critério de aceitação:** Escopo técnico item 1 — "o próprio `board_id` já existente em `AgentParams` é o board de origem da execução".

**Pré-condição:**
- `AgentParams` construído com `board_id="task"`.

**Passos:**
1. Chamar `KiroCliAgent()._build_log(params)`.

**Resultado esperado:**
- O markdown resultante contém a linha `- **board**: task` (comportamento já existente, não alterado por esta task).
- Não é necessário nem esperado nenhum campo adicional de "board de origem" em `AgentParams` — `board_id` cobre esse requisito integralmente.

## CT-012 — Regressão de compatibilidade: chamadas existentes de `AgentParams` (posicionais e nomeadas) continuam funcionando

**Tipo:** unitário
**Critério de aceitação:** Seção "Como testar" da issue — "continua funcionando sem erro, com `participation_intent is None` por default".

**Pré-condição:**
- Reexecutar as construções de `AgentParams` já cobertas pelos testes existentes em `tests/test_agent_log_descritivo.py` (ex.: `_make_params`, construção "antiga" sem os campos novos em `test_codigo_existente_sem_novos_campos_nao_quebra`).

**Passos:**
1. Rodar a suíte existente `tests/test_agent_log_descritivo.py` sem alteração.

**Resultado esperado:**
- Todos os testes existentes continuam passando (nenhuma regressão introduzida pelo novo campo opcional).

## CT-013 — Sem chamada de rede na leitura de `participation_intent`

**Tipo:** unitário
**Critério de aceitação:** Descrição da issue — "sem nenhuma chamada de rede adicional, mesmo espírito de 'gate não chama rede'".

**Pré-condição:**
- Mesmo cenário de CT-004/CT-005, com qualquer cliente de rede/API do board (ex.: adapter GitHub) mockado ou ausente do caminho de código exercitado.

**Passos:**
1. Chamar `call_agent(config, task)` com a issue já carregada localmente (dict em memória, sem I/O de rede).

**Resultado esperado:**
- Nenhuma chamada a métodos de rede/API (`gh api`, GraphQL, etc.) ocorre como efeito da leitura de `participation_intent` — a leitura é apenas `issue.get("participation_intent")` sobre o dict já em memória.
