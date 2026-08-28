# Casos de Teste — Adicionar e validar a chave `safety.cross_board_parent_links` no `pipe.yml`

Status: draft
Owner: quality
Last updated: 2026-08-28

## Inputs
- Task #255 — Adicionar e validar a chave `safety.cross_board_parent_links` no `pipe.yml`
- User Story #241 — Contingência de suspensão de vínculos entre boards
- `src/core/config.py` (`validate_max_attempts`, `resolve_max_attempts`,
  `DEFAULT_MAX_ATTEMPTS`, `check_config`, `ConfigError`, `PIPE_FILE`) — padrão
  de referência replicado por esta task
- Seção "Como testar" da issue #255 (lista de casos exigidos)

## CT01 — `validate_cross_board_parent_links` sem seção `safety` não levanta erro

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 2 ("Ausência da chave ou de toda a seção `safety` é permitida")

**Pré-condição:**
- `config = {}`

**Passos:**
1. Chamar `validate_cross_board_parent_links({})`.

**Resultado esperado:**
- Nenhuma exceção levantada.

## CT02 — `validate_cross_board_parent_links` com seção `safety` presente e chave ausente não levanta erro

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 2

**Pré-condição:**
- `config = {"safety": {}}`

**Passos:**
1. Chamar `validate_cross_board_parent_links({"safety": {}})`.

**Resultado esperado:**
- Nenhuma exceção levantada.

## CT03 — `validate_cross_board_parent_links` aceita `"enabled"`

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 2 (`CROSS_BOARD_LINKS_VALUES`)

**Pré-condição:**
- `config = {"safety": {"cross_board_parent_links": "enabled"}}`

**Passos:**
1. Chamar `validate_cross_board_parent_links(config)`.

**Resultado esperado:**
- Nenhuma exceção levantada.

## CT04 — `validate_cross_board_parent_links` aceita `"suspended"`

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 2 (`CROSS_BOARD_LINKS_VALUES`)

**Pré-condição:**
- `config = {"safety": {"cross_board_parent_links": "suspended"}}`

**Passos:**
1. Chamar `validate_cross_board_parent_links(config)`.

**Resultado esperado:**
- Nenhuma exceção levantada.

## CT05 — `validate_cross_board_parent_links` rejeita variação de caixa (`"Enabled"`)

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 2 ("comparação exata, sem normalizar caixa/espaços") e critério de aceite da story #241 ("mensagem acionável")

**Pré-condição:**
- `config = {"safety": {"cross_board_parent_links": "Enabled"}}`

**Passos:**
1. Chamar `validate_cross_board_parent_links(config)`.

**Resultado esperado:**
- Levanta `ConfigError`.
- A mensagem da exceção contém a chave `safety.cross_board_parent_links`.

## CT06 — `validate_cross_board_parent_links` rejeita valor string inválido (`"off"`)

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 2

**Pré-condição:**
- `config = {"safety": {"cross_board_parent_links": "off"}}`

**Passos:**
1. Chamar `validate_cross_board_parent_links(config)`.

**Resultado esperado:**
- Levanta `ConfigError`.
- A mensagem da exceção contém a chave `safety.cross_board_parent_links`.

## CT07 — `validate_cross_board_parent_links` rejeita valor não-string (`True`)

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 2 ("inclusive tipos não-string, vazio ou variações de caixa")

**Pré-condição:**
- `config = {"safety": {"cross_board_parent_links": True}}`

**Passos:**
1. Chamar `validate_cross_board_parent_links(config)`.

**Resultado esperado:**
- Levanta `ConfigError`.
- A mensagem da exceção contém a chave `safety.cross_board_parent_links`.

## CT08 — `resolve_cross_board_parent_links` retorna `"enabled"` por default

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 3 ("Default 'enabled' quando a chave ou a seção `safety` estão ausentes")

**Pré-condição:**
- `config = {}`

**Passos:**
1. Chamar `resolve_cross_board_parent_links({})`.

**Resultado esperado:**
- Retorno `"enabled"`.

## CT09 — `resolve_cross_board_parent_links` retorna o valor configurado (`"suspended"`)

**Tipo:** unitário
**Critério de aceitação:** issue #255, item 3

**Pré-condição:**
- `config = {"safety": {"cross_board_parent_links": "suspended"}}`

**Passos:**
1. Chamar `resolve_cross_board_parent_links(config)`.

**Resultado esperado:**
- Retorno `"suspended"`.

## CT10 — `load_current_config` reflete alteração em disco sem cache em memória

**Tipo:** integração (I/O de arquivo)
**Critério de aceitação:** issue #255, item 4 ("sem cache em memória do processo")

**Pré-condição:**
- Diretório temporário isolado (`monkeypatch.chdir(tmp_path)`, mesmo padrão de
  `tests/test_sync_optimization.py`).
- Um `pipe.yml` válido escrito nesse diretório.

**Passos:**
1. Chamar `load_current_config()` e capturar o retorno.
2. Sobrescrever o `pipe.yml` em disco com conteúdo diferente (ex.: outro
   valor de `safety.cross_board_parent_links`).
3. Chamar `load_current_config()` novamente.

**Resultado esperado:**
- O primeiro retorno reflete o conteúdo original do arquivo.
- O segundo retorno reflete o novo conteúdo escrito no passo 2 (confirma
  ausência de cache em memória entre chamadas).

## CT11 — `load_current_config` sem `pipe.yml` no diretório atual levanta erro

**Tipo:** integração (I/O de arquivo)
**Critério de aceitação:** issue #255, item 4 ("Levanta ConfigError se o arquivo não existir")

**Pré-condição:**
- Diretório temporário isolado, sem nenhum arquivo `pipe.yml`.

**Passos:**
1. Chamar `load_current_config()`.

**Resultado esperado:**
- Levanta `ConfigError`, com a mesma mensagem já usada em `check_config()`
  para arquivo ausente.

## CT12 — `check_config()` rejeita `safety.cross_board_parent_links` inválido (integração)

**Tipo:** integração
**Critério de aceitação:** critério de aceite da story #241 ("Dado um valor inválido [...] quando o `check_config` valida a configuração, então a validação rejeita com mensagem acionável") e issue #255, item 5

**Pré-condição:**
- `pipe.yml` de teste válido (demais seções obrigatórias presentes), exceto
  `safety.cross_board_parent_links: "invalido"`.

**Passos:**
1. Chamar `check_config()` nesse ambiente.

**Resultado esperado:**
- Levanta `ConfigError`.

## CT13 — `check_config()` sem a seção `safety` continua funcionando (regressão)

**Tipo:** integração
**Critério de aceitação:** issue #255, item 2 ("a chave é opcional") — regressão

**Pré-condição:**
- `pipe.yml` de teste válido, sem a seção `safety`.

**Passos:**
1. Chamar `check_config()` nesse ambiente.

**Resultado esperado:**
- Não levanta exceção relacionada a `safety`/`cross_board_parent_links`.
- Retorna o dict de configuração normalmente.

## CT14 — Não regressão da suíte existente

**Tipo:** integração (execução de suíte)
**Critério de aceitação:** "Sem quebra de funcionalidades existentes" (issue #255)

**Pré-condição:**
- Suíte de testes completa do repositório.

**Passos:**
```bash
python -m pytest tests/ -k "config" -v
python -m pytest
```

**Resultado esperado:**
- Todos os testes pré-existentes continuam passando.
- Os novos testes de `validate_cross_board_parent_links`,
  `resolve_cross_board_parent_links` e `load_current_config` passam.

## Fora de escopo (não testar nesta task)

- Bloqueio real de `set_parent`/`set_children` entre boards distintos
  (`src/core/board.py`/`src/core/sync.py`) — task subsequente (#256).
- Emissão do evento `cross_board_link_blocked` ou qualquer log estruturado
  associado — task subsequente (#256).
