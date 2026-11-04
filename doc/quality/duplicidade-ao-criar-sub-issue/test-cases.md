# Casos de Teste — Duplicidade ao criar sub-issue

- **Issue:** #339
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-11-04
- **Branch:** `feature/339-duplicidade_ao_criar_sub_issue`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da
> issue #339. Cada caso tem resultado esperado explícito e verificável. Os
> testes são da suíte Python do motor (pytest, em `tests/`).

---

## Natureza desta etapa (importante)

A issue #339, conforme o corpo e o histórico de Planejamento, tem escopo de
**investigação e documentação da causa raiz** — não de correção de código
(a correção é "entrega futura", explicitamente fora de escopo). Os 3 CAs
pedem que a investigação **reproduza, documente e confirme** fatos sobre o
comportamento atual do motor, com evidência de log real.

Isso não dispensa esta etapa: cada CA é verificável por um teste automatizado
que reproduz o comportamento descrito **de forma determinística e offline**
(sem depender do log externo do `br.com.escrevas`, que é evidência histórica,
não reprodutível neste ambiente). Os casos abaixo são a tradução executável
dos 3 CAs — e, apontando o `pytest` para o código atual, documentam de forma
viva (RED hoje, por serem bugs confirmados; ficam VERDE quando a correção
futura for implementada) exatamente o comportamento que a issue pede para
confirmar.

**Verificação feita nesta etapa, antes de especificar os casos** (obrigação
desta etapa: avaliar os testes já existentes antes de criar novos):

- Reproduzi o bug isoladamente contra o código atual
  (`src/core/sync.py::_apply_create_up`, linha 1160): ao criar uma issue local
  cujo `-body.md` declara **qualquer comando não vazio** no bloco `@---`
  (`/parent`, mas também `/labels`, `/need_human` etc. — ver "Achado adicional"
  abaixo), a chamada `_filter_suspended_cross_board_parent(board_id,
  created.id, cmds, config)` lança `NameError: name 'config' is not defined`,
  pois `_apply_create_up` não recebe `config` como parâmetro nem o define
  localmente. `classify_error` classifica a exceção como `"transitorio"`, e
  `apply_changes` reenfileira o item — repetindo `create_issue` a cada
  tentativa. Rodei o ciclo completo (3 tentativas, `sync.max_attempts=3`) e
  confirmei 3 issues criadas (`#101`, `#102`, `#103`) a partir do mesmo
  `-body.md`, com as mensagens de log idênticas às citadas na issue
  (`erro transitório em create-up (tentativa N/3) - reenfileirando: name
  'config' is not defined` / `esgotou tentativas (3) em create-up - removendo
  da fila`).
- Busquei por testes existentes que exercitem `_apply_create_up` com algum
  comando declarado: existe exatamente um,
  `tests/test_sanitize_relations.py::test_apply_create_up_self_reference_not_sent_to_adapter`.
  Ele **não exercita o bug nem o código de aplicação de comandos**: constrói
  `ChangeItem.of(SyncEvent.CREATE_UP, id=str(body_path), ...)` passando o
  caminho do body como `id=`, não como `identifier=`. Como `_apply_create_up`
  busca `issue_data` por `item.identifier` (não por `item.id`), `item.identifier`
  fica `None`, a busca falha e a função retorna na primeira guarda (`if not
  issue_data: return`) — **antes** de qualquer chamada a `create_issue` ou
  `apply_commands`. Confirmei isso instrumentando `FakePort`: `port.calls`
  permanece `[]` após a chamada. As asserções do teste (`for call in
  blocked_by_calls: ...`) iteram sobre uma lista vazia e passam trivialmente,
  sem nunca ter testado a sanitização de auto-referência que o teste afirma
  cobrir. **Nenhum teste existente cobre o bug desta issue** — os casos novos
  abaixo são, portanto, justificados (não há duplicação) e o achado sobre o
  teste quebrado é registrado como débito para o desenvolvimento corrigir
  junto da correção do bug principal (mesmo arquivo).

### Achado adicional (relevante para o desenvolvimento da correção futura)

A hipótese registrada no corpo da issue (critério de aceitação 2) descreve o
disparo como ocorrendo "quando o arquivo `-body.md` que está sendo criado
declara `/parent #N`". A reprodução mostra que a condição real de disparo é
mais ampla: a chamada a `_filter_suspended_cross_board_parent(...)` ocorre
**incondicionalmente** dentro do bloco `if not cmds.is_empty()` (linha 1158),
ou seja, **antes** de a própria `_filter_suspended_cross_board_parent`
verificar `if not getattr(cmds, "parent", None): return cmds`. Como a
avaliação dos argumentos de uma chamada Python ocorre antes de entrar na
função chamada, o `NameError` dispara ao montar os argumentos da chamada —
portanto para **qualquer** `-body.md` novo que declare pelo menos um comando
no bloco `@---` (`/parent`, `/labels`, `/need_human`, `/children`,
`/blocked_by`, `/blocks`, `/agent-hub-*` ou `/archive`), não apenas `/parent`.
Um `-body.md` sem bloco de comandos (`cmds.is_empty() == True`) não dispara o
bug. Isso **não contradiz** a reprodução do cenário real do `br.com.escrevas`
(a Story usava `/parent`, que é um caso do conjunto mais amplo) — apenas
amplia a superfície de disparo que o desenvolvimento da correção futura
precisa cobrir. Registrado como nota de rastreabilidade; não é uma
divergência que justifique devolver ao planejamento (não contradiz nem deixa
incompleto nenhum CA — apenas precisa, nos testes abaixo, cobrir o gatilho
real, mais amplo que o exemplo citado no corpo).

---

## Rastreabilidade (CA → casos)

| CA | Enunciado resumido | Caso(s) |
|----|---------------------|---------|
| CA-1 | Investigação reproduz e confirma a triplicação de sub-issues via `create-up`, citando o mecanismo | CT-01, CT-02, CT-05 |
| CA-2 | Causa documentada citando arquivo/função/variável/chamada exatos | CT-01, CT-03, CT-06 |
| CA-3 | Confirmação (com evidência) de que `participation_intent` (#310) não participa da causa no cenário mesmo-board | CT-04 |

---

## Convenções para os casos abaixo

- **Offline, sem rede:** usar `BoardPort` fake local (padrão de
  `tests/test_error_classification.py::FakePort` e
  `tests/test_sanitize_relations.py::FakePort`), nunca o adapter real
  (`github_board.py`).
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` por teste (fixture
  `autouse`), igual à suíte existente — `.pipe/` isolado por teste.
- **`ChangeItem` para `create-up` usa `identifier=<caminho do body>`**, nunca
  `id=` (achado desta etapa — ver nota acima; os casos novos usam a chamada
  correta para realmente exercitar `_apply_create_up`).
- **Nunca** fazer `monkeypatch` do próprio símbolo sob teste (lição do
  incidente #106): os testes chamam `sync._apply_create_up` e
  `sync.apply_changes` de verdade; só a **porta** (`BoardPort`) é fake.
- Onde um caso descreve o estado esperado "hoje" (RED, bug presente), isso é
  intencional: a issue pede para **confirmar e documentar** o comportamento
  atual, não para corrigi-lo. O teste deve falhar claramente (ficar vermelho)
  se uma correção futura mudar esse comportamento sem que o caso seja
  revisado deliberadamente — é o contrato executável da investigação.

---

## Grupo A — Reprodução determinística do bug (CA-1, CA-2)

### CT-01 — `NameError` ao criar sub-issue com `/parent` no create-up

- **CA de origem (CA-1, CA-2):** reproduzir a triplicação e documentar a causa
  exata (arquivo, função, variável, chamada).
- **Tipo:** integração (sync + porta fake), unitário na asserção de causa.
- **Arquivo/alvo:** `tests/test_create_up_config_nameerror.py` (novo),
  exercitando `src/core/sync.py::_apply_create_up`.
- **Pré-condição:** board `task` configurado; `-body.md` novo (sem ID) no
  snapshot com `status: pending-create`, conteúdo com `@---\n/parent #81`;
  `BoardPort` fake cujo `create_issue` retorna uma issue com `id` sequencial
  (simula o GitHub atribuindo o número real).
- **Passos:**
  1. Montar `ChangeItem.of(SyncEvent.CREATE_UP, identifier=<caminho do
     body>, board="task")`.
  2. Chamar `sync._apply_create_up("task", item, board_obj, queue=queue)`
     diretamente, dentro de `pytest.raises(NameError)`.
- **Resultado esperado:** a chamada levanta `NameError` cuja mensagem contém
  `"config"` (ex.: `"name 'config' is not defined"`); **antes** da exceção,
  `create_issue` foi chamado exatamente uma vez (a issue já existe no board
  remoto quando o erro ocorre — é o fato que torna o retry perigoso); o
  arquivo local `-body.md` **não** foi renomeado com o ID atribuído (prova de
  que a função foi interrompida antes de concluir a atualização local).
- **Observações:** cobre CA-1 (confirma o mecanismo) e CA-2 (localiza
  exatamente onde ocorre). Documenta o fato central: a issue já foi criada no
  GitHub no momento em que a exceção interrompe a função.

### CT-02 — Ciclo completo de `apply_changes` recria a issue a cada tentativa (triplicação)

- **CA de origem (CA-1):** confirmar que a triplicação observada no log real
  (4 Tasks × 3 tentativas = 12 issues) é reprodução de um padrão determinístico
  N tentativas → N issues criadas, não um acidente de um board específico.
- **Tipo:** integração (sync + fila + porta fake), parametrizado.
- **Arquivo/alvo:** `tests/test_create_up_config_nameerror.py`.
- **Pré-condição:** mesmo cenário de CT-01, mas processado através de
  `sync.apply_changes(board_obj, queue, config={"sync": {"max_attempts": N}})`,
  chamado `N` vezes (cada chamada de `apply_changes` tenta o item uma vez,
  conforme a semântica documentada em `tests/test_error_classification.py`).
  Parametrizado com `N` em `{1, 3, 5}` (cobre o default de `retry`/`sync` e
  valores customizados).
- **Passos:**
  1. Enfileirar um único item `create-up` para o `-body.md` com `/parent #N`.
  2. Chamar `apply_changes` `N` vezes seguidas, com `sync.max_attempts=N`.
  3. Contar quantas vezes `create_issue` foi chamado na porta fake.
- **Resultado esperado:** `create_issue` é chamado exatamente `N` vezes
  (uma issue nova por tentativa); ao final da `N`-ésima chamada, o item sai da
  fila (`queue.getNext() is None`) com log de "esgotou tentativas"; cada
  issue criada recebe um ID distinto da porta fake — reproduzindo, em escala
  menor e determinística, o padrão "4 Tasks × 3 tentativas = 12 issues" do log
  real citado na issue.
- **Observações:** cobre CA-1 com generalização sobre o parâmetro de
  tentativas, evitando acoplar o teste ao valor específico `3` do incidente
  real.

### CT-03 — O gatilho não depende de `/parent`: qualquer comando não vazio dispara o mesmo erro

- **CA de origem (CA-2):** documentar a causa com precisão suficiente para
  sustentar o desenvolvimento futuro sem nova investigação — o que inclui a
  condição de disparo real, não apenas o exemplo observado no log.
- **Tipo:** unitário (sync + porta fake), parametrizado.
- **Arquivo/alvo:** `tests/test_create_up_config_nameerror.py`.
- **Pré-condição:** quatro variações de `-body.md` novo, cada uma com um
  bloco `@---` de um único comando: `/parent #81`, `/labels bug`,
  `/need_human`, `/blocked_by #10`.
- **Passos:**
  1. Para cada variação, chamar `sync._apply_create_up` isoladamente.
- **Resultado esperado:** as quatro variações levantam `NameError` idêntico
  (mesma mensagem, mesma linha de origem via `traceback`); um quinto sub-caso
  de controle, com `-body.md` **sem** bloco `@---` (nenhum comando declarado),
  **não** levanta exceção e completa o fluxo normal (arquivo renomeado, 1
  issue criada, item sai da fila).
- **Observações:** fecha a lacuna entre a redação do corpo da issue (que cita
  apenas `/parent`) e o comportamento real do código (qualquer comando não
  vazio). Evidencia textual: a chamada
  `_filter_suspended_cross_board_parent(board_id, created.id, cmds, config)`
  ocorre dentro de `if not cmds.is_empty()` — a referência a `config`
  é avaliada ao montar os argumentos da chamada, antes de
  `_filter_suspended_cross_board_parent` sequer verificar
  `if not getattr(cmds, "parent", None)`.

---

## Grupo B — Confirmação de que `participation_intent` (#310) não participa (CA-3)

### CT-04 — Vínculo `/parent` no mesmo board não aciona nenhum caminho de `participation_intent`

- **CA de origem (CA-3):** confirmar, com evidência de log, que o mecanismo
  da issue #310 não participa da causa quando Story e Tasks estão no mesmo
  board.
- **Tipo:** integração (sync + porta fake + captura de log).
- **Arquivo/alvo:** `tests/test_create_up_config_nameerror.py`.
- **Pré-condição:** mesmo cenário de CT-01 (Story e Task no mesmo board
  `task`, sem nenhum board configurado adicional que torne o vínculo
  cross-board); captura de `log.info`/`log.warning` via `monkeypatch`
  (padrão de `tests/test_participation_evidence.py`).
- **Passos:**
  1. Executar `_apply_create_up` (ou `apply_changes`) sobre o cenário.
  2. Verificar os eventos emitidos no log capturado.
- **Resultado esperado:** nenhum evento da família `participation_classified`,
  `participation_reconciled`, `participation_reconcile_failed` ou
  `dispatch_blocked_unconfirmed_intent` é emitido; a função
  `_board_of_issue` (usada por `_filter_suspended_cross_board_parent` para
  decidir se o vínculo é cross-board) resolve o board do pai como `None` ou
  igual a `board_id` (mesmo board) — confirmando por asserção direta (chamando
  `sync._board_of_issue` com a config do cenário) que o guard de contingência
  cross-board não altera `cmds.parent` nesse caso; o `NameError` ocorre antes
  dessa decisão (na montagem dos argumentos da chamada), então mesmo esse
  guard nunca é alcançado.
- **Observações:** cobre CA-3 de forma direta e automatizada — evidência
  reproduzível, complementar (não substituta) à leitura do log real do
  `br.com.escrevas` já citada no corpo da issue.

---

## Grupo C — Débito identificado na suíte existente (não é código novo, é correção de teste)

### CT-05 — `test_apply_create_up_self_reference_not_sent_to_adapter` não exercita `_apply_create_up` (teste quebrado)

- **CA de origem:** parte da obrigação desta etapa de "avaliar os testes já
  existentes antes de criar novos" — e insumo necessário para a entrega
  futura de correção não reintroduzir falso positivo.
- **Tipo:** unitário (meta-teste sobre o teste existente).
- **Arquivo/alvo:** `tests/test_create_up_config_nameerror.py` (documenta o
  achado) — a correção do teste em si
  (`tests/test_sanitize_relations.py`, troca de `id=` por `identifier=` na
  construção do `ChangeItem.of`) é **fora de escopo desta etapa** (não é
  código de teste novo para os CAs desta issue, é débito num teste de outra
  issue, #143) e deve ser registrada para o desenvolvimento tratar junto da
  correção do bug principal, no mesmo arquivo.
- **Passos:**
  1. Reconstruir exatamente a chamada feita pelo teste existente
     (`ChangeItem.of(SyncEvent.CREATE_UP, id=str(body_path), board=board_id)`).
  2. Executar `_apply_create_up` com essa construção.
  3. Verificar `port.calls`.
- **Resultado esperado:** `port.calls == []` — nenhuma chamada ao adapter
  ocorre, confirmando que a função retornou na guarda inicial
  (`issue_data` não encontrado porque a busca usa `item.identifier`, que fica
  `None` quando só `id=` é passado) e que o teste original nunca exerceu a
  sanitização de auto-referência que afirma cobrir.
- **Observações:** não é regressão introduzida por esta issue — o teste já
  estava assim. Registrado como achado de qualidade a ser corrigido (trocar
  `id=` por `identifier=`) na mesma entrega que corrigir o bug de `config`,
  para que a suíte passe a oferecer a cobertura que documenta.

---

## Resumo de arquivos de teste propostos

| Arquivo | Cobre |
|---------|-------|
| `tests/test_create_up_config_nameerror.py` | CT-01 a CT-05 (reprodução determinística do bug, condição real de disparo, confirmação de que #310 não participa, achado sobre teste existente quebrado) |

Sem regressão: a suíte existente de sync e sanitização de relações
(`tests/test_sanitize_relations.py`, `tests/test_error_classification.py`,
`tests/test_sync_unico*.py`, `tests/test_participation_*.py`) deve continuar
passando — os casos novos são aditivos e não alteram nenhum código de
produção nesta etapa (issue de investigação; correção é entrega futura).

## Fora de escopo dos casos (alinhado à issue)

- Implementação da correção (propagar `config` a `_apply_create_up`, ou
  qualquer redesenho) — entrega futura, conforme "Fora de escopo" do corpo da
  issue.
- Limpeza das issues duplicadas já materializadas no `br.com.escrevas`.
- Redesenho do mecanismo de `participation_intent` (#310).
- Qualquer alteração na *workflow* do GitHub do repositório
  `br.com.escrevas` (já resolvida, fora do motor).
