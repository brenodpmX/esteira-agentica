# Casos de Teste — Testes de conformidade: eventos estruturados nunca expõem segredo, body ou arquivo protegido

Status: draft
Owner: quality
Last updated: 2026-08-28

## Inputs
- Task #263 — Testes de conformidade: eventos estruturados nunca expõem segredo, body ou arquivo protegido
- User Story #246 — Observabilidade de propagação/reconciliação/despacho e evidência de rollout
- RN-B09, último item (`doc/requirements/integridade-de-issues-entre-boards/business-rules.md`)
- Constraints (`doc/architecture/integridade-de-issues-entre-boards/constraints.md`)
- Critério de aceitação final da story #246

## CT-001 — `assert_no_sensitive_kwargs` não levanta erro para kwargs neutros

**Tipo:** unitário
**Critério de aceitação:** docstring de `assert_no_sensitive_kwargs` — "Levanta ValueError se `extra` contiver alguma chave proibida."

**Pré-condição:**
- Nenhuma.

**Passos:**
1. Chamar `assert_no_sensitive_kwargs({"issue_id": "1", "board_id": "task"})`.

**Resultado esperado:**
- A chamada retorna normalmente (`None`), sem exceção propagada.

## CT-002 — `assert_no_sensitive_kwargs` levanta `ValueError` quando a chave `token` está presente

**Tipo:** unitário
**Critério de aceitação:** docstring de `assert_no_sensitive_kwargs`; RN-B09 último item — "Logs não podem conter token [...]".

**Pré-condição:**
- Nenhuma.

**Passos:**
1. Chamar `assert_no_sensitive_kwargs({"issue_id": "1", "token": "ghp_x"})`.

**Resultado esperado:**
- É levantado `ValueError`.
- A mensagem da exceção menciona `"token"`.

## CT-003 — `assert_no_sensitive_kwargs` é case-insensitive na comparação de chaves

**Tipo:** unitário
**Critério de aceitação:** docstring de `assert_no_sensitive_kwargs` — "comparação exata, case-insensitive".

**Pré-condição:**
- Nenhuma.

**Passos:**
1. Chamar `assert_no_sensitive_kwargs({"BODY": "..."})`.

**Resultado esperado:**
- É levantado `ValueError`.

## CT-004 — `assert_no_sensitive_kwargs` detecta cada uma das demais chaves proibidas (`ssh_key`, `gh_token`, `kiro_api_key`)

**Tipo:** unitário
**Critério de aceitação:** docstring de `assert_no_sensitive_kwargs` — conjunto `FORBIDDEN_LOG_KWARGS = {"token", "ssh_key", "body", "gh_token", "kiro_api_key"}`.

**Pré-condição:**
- Nenhuma.

**Passos:**
1. Para cada chave em `ssh_key`, `gh_token`, `kiro_api_key`: chamar `assert_no_sensitive_kwargs({<chave>: "valor"})` isoladamente.

**Resultado esperado:**
- Cada chamada levanta `ValueError` mencionando a respectiva chave.

## CT-005 — `assert_no_sensitive_kwargs` reporta todas as chaves proibidas presentes, não apenas a primeira

**Tipo:** unitário
**Critério de aceitação:** docstring de `assert_no_sensitive_kwargs` — `hit = lower_keys & FORBIDDEN_LOG_KWARGS`.

**Pré-condição:**
- Nenhuma.

**Passos:**
1. Chamar `assert_no_sensitive_kwargs({"token": "x", "body": "y", "issue_id": "1"})`.

**Resultado esperado:**
- É levantado `ValueError`.
- A mensagem da exceção menciona tanto `"token"` quanto `"body"` (não apenas uma delas).

## CT-006 — Inspeção estática: chamadas de log dos `event_type` da story não contêm campos proibidos

**Tipo:** integração (inspeção estática de código-fonte)
**Critério de aceitação:** critério de aceitação final da story #246 — "Nenhum evento acima contém token, chave SSH, body completo da issue ou conteúdo de arquivos protegidos."

**Pré-condição:**
- Nenhuma (o teste lê o texto-fonte diretamente do repositório).

**Passos:**
1. Ler o texto-fonte de `src/__main__.py`, `src/core/board.py`, `src/core/sync.py` e `src/core/log.py`.
2. Para cada um dos sete literais `event_type="..."` listados abaixo, localizar suas ocorrências nos quatro arquivos:
   - `rollout_evidence`
   - `participation_classified`
   - `participation_reconciled`
   - `participation_reconcile_failed`
   - `participation_removed_externally`
   - `dispatch_blocked_unconfirmed_intent`
   - `cross_board_link_blocked`
3. Para cada ocorrência encontrada, extrair a chamada completa de `log.info(...)`/`log.warning(...)`/`log.error(...)` (do início da chamada até o fechamento do parêntese correspondente).
4. Verificar, por busca textual simples, se alguma das substrings `body=`, `token=`, `ssh_key=`, `gh_token=`, `kiro_api_key=` aparece dentro do trecho extraído.

**Resultado esperado:**
- Nenhuma das substrings proibidas aparece em nenhum trecho extraído.
- `event_type="rollout_evidence"` é encontrado (já implementado) e validado positivamente.
- Os demais seis `event_type` (ainda não implementados no momento da criação desta suíte) não fazem o teste falhar por ausência — a verificação é apenas pulada para o `event_type` não encontrado.

## CT-007 — Inspeção estática não falha quando um `event_type` da lista ainda não existe no código

**Tipo:** integração (inspeção estática de código-fonte)
**Critério de aceitação:** "Como testar" da task — "Se algum dos sete `event_type` listados não for encontrado [...] pule a verificação apenas para esse `event_type` — não falhe o teste por ausência".

**Pré-condição:**
- Estado atual da base: apenas `rollout_evidence` está implementado; os demais seis `event_type` (`participation_classified`, `participation_reconciled`, `participation_reconcile_failed`, `participation_removed_externally`, `dispatch_blocked_unconfirmed_intent`, `cross_board_link_blocked`) ainda não existem em `src/__main__.py`, `src/core/board.py`, `src/core/sync.py` nem `src/core/log.py`.

**Passos:**
1. Executar o teste de inspeção estática (CT-006) no estado atual da base.

**Resultado esperado:**
- O teste passa (não há falha por ausência dos seis `event_type` não implementados).
- Nenhuma asserção de "presença obrigatória" é feita para `event_type` ausente.

## CT-008 — Inspeção estática: evento `participation_classified` não expõe `.body` nem lista completa de labels em `evidence=`

**Tipo:** integração (inspeção estática de código-fonte)
**Critério de aceitação:** item 5 de "Como testar" da task — segunda linha de defesa textual específica para `participation_classified`.

**Pré-condição:**
- Aplica-se apenas quando `event_type="participation_classified"` for encontrado no código (conforme CT-006/CT-007). Enquanto não implementado, este caso é pulado, sem falha.

**Passos:**
1. Localizar a(s) ocorrência(s) de `event_type="participation_classified"` nos quatro arquivos listados em CT-006.
2. Extrair a chamada de log completa correspondente.
3. Se a chave `evidence=` estiver presente no trecho extraído, verificar por busca textual se a substring `.body` aparece dentro do valor de `evidence=`.
4. Verificar se `labels=` aparece no trecho extraído referenciando a lista completa de labels da issue (heurística textual simples, não reimplementação da lógica de classificação).

**Resultado esperado:**
- Quando `participation_classified` existir: nem `.body` nem `labels=` (lista completa) aparecem no trecho de `evidence=`.
- Quando `participation_classified` não existir na base: caso pulado, sem falha do teste.

## CT-009 — Suíte completa de testes não sofre regressão

**Tipo:** integração
**Critério de aceitação:** "Como testar" da task — "Rode [...] a suíte completa `python -m pytest` sem regressão."

**Pré-condição:**
- `assert_no_sensitive_kwargs` e a suíte `tests/test_observability_compliance.py` implementadas.

**Passos:**
1. Executar `python -m pytest tests/test_observability_compliance.py -v`.
2. Executar `python -m pytest`.

**Resultado esperado:**
- Todos os testes da suíte `test_observability_compliance.py` passam.
- A suíte completa do projeto passa sem falhas novas introduzidas por esta task.
