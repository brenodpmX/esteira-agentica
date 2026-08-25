# Casos de Teste — `_detect_failure` não deve avaliar a narrativa do agente, só os canais estruturados do kiro-cli

Status: draft
Owner: quality
Last updated: 2026-08-24

## Inputs

- Task #206 — `_detect_failure` não deve avaliar a narrativa do agente, só os
  canais estruturados do kiro-cli (board `task`, etapa Casos de Teste)
- Incidente de origem: #203 — Problemas na execução do kiro (defeito **D5** /
  correção **C3**), `doc/incidente/problemas-execucao-kiro/ticket.md`
  (branch `hotfix203-203-problemas_na_execucao_do_kiro`, ainda não mesclada em
  `epic`/`main` no momento desta escrita — conteúdo consistente com o body da
  issue #206, que é autocontido)
- Precedente de design citado na issue: `README.md`, seção "Rate Limit
  (GitHub)" — decisão de não escanear o corpo da resposta em busca de texto,
  para evitar falso positivo quando o próprio conteúdo (issue/narrativa) cita a
  expressão monitorada
- Código sob teste: `KiroCliAgent._detect_failure` e `KiroCliAgent._run`
  (`src/adapters/kiro_cli_agent.py`)
- Suítes existentes a não regredir: `tests/test_agent_failure_detection.py`,
  `tests/test_error_classification.py`

## Contexto da verificação

**Estado do código no momento desta etapa:** `_detect_failure(self, output:
str)` recebe hoje apenas a string combinada de `stdout`+`stderr` (com
`[exit-code: N]` já concatenado por `_run` quando `returncode != 0`) e decide
se houve falha varrendo o **texto inteiro** em busca de `_FAILURE_MARKERS`
(`"[exit-code:"`, `"[TIMEOUT]"`, `"[ERRO]"`, `"Kiro is having trouble
responding"`). Não há, hoje, nenhuma distinção entre "essa frase apareceu no
bloco de encerramento estruturado do próprio `kiro-cli`" e "essa frase foi
citada pelo agente ao escrever sua resposta/narrativa" — os dois casos usam a
mesma correspondência de substring sobre o mesmo texto.

Isso é exatamente o defeito **D5**: a execução real da triagem da issue #203
(`logs/203/2026-08-24_21-39-38.md`) terminou com sucesso (`▸ Credits: 4.52 •
Time: 4m 2s`, sem `[exit-code:` no fim) e foi classificada como falha porque o
agente, ao **analisar** o incidente, citou literalmente a frase `"Kiro is
having trouble responding right now"` presente no log que estava lendo.

Esta é a etapa de Casos de Teste, anterior à implementação da correção. Os
casos abaixo foram escritos test-first: os que exercitam o comportamento
**ainda não implementado** (recebimento do `returncode`/canal estruturado por
`_detect_failure`, distinção narrativa vs. estruturado) devem falhar no estado
atual do código e passar após a implementação (mesmo padrão de
`tests/test_sanitize_relations.py`, citado na issue #143). Os casos que
exercitam comportamento **já existente e que não pode regredir** (marcadores
reais de falha, extração de causa) já passam hoje e devem continuar passando
depois.

Verificado nesta etapa (sem alterar código, apenas leitura):

```
python -m pytest tests/test_agent_failure_detection.py tests/test_error_classification.py -q
```

Ambas as suítes passam integralmente no estado atual de `epic` — são a
linha de base de não-regressão para esta task.

## CT-001 — Marcador de falha citado só na narrativa do agente não é falha

**Tipo:** unitário
**Critério de aceitação:** AC4 do body (regressão do caso de
`logs/203/2026-08-24_21-39-38.md`)

**Pré-condição:**
- Execução do `kiro-cli` bem-sucedida: `returncode == 0`.
- Output não contém o bloco de encerramento estruturado de erro do
  `kiro-cli`, apenas texto do agente citando a frase de falha ao narrar/citar
  um log analisado.

**Passos:**
1. Montar um output que reproduza a forma real do caso #203: linhas de
   trabalho do agente, uma citação literal de `"Kiro is having trouble
   responding right now"` (como parte da análise do agente, não como bloco de
   erro do processo), e a linha final de sucesso do próprio `kiro-cli`
   (`▸ Credits: 4.52 • Time: 4m 2s`), sem `[exit-code:`.
2. Chamar `_detect_failure` (ou o novo ponto de entrada que recebe o canal
   estruturado, ex. `returncode`) com esse output e `returncode=0`.

**Resultado esperado:**
- Retorno `None` — a execução é tratada como sucesso.
- Este teste deve **falhar no código atual** (a implementação vigente
  retorna erro, pois `_FAILURE_MARKERS` casa em qualquer lugar do texto) e
  **passar após a correção**.

---

## CT-002 — Múltiplas citações da narrativa a marcadores diferentes, ainda sucesso

**Tipo:** unitário
**Critério de aceitação:** AC4 (generalização do CT-001 para os demais
`_FAILURE_MARKERS`)

**Pré-condição:**
- `returncode == 0`, sem bloco de erro estruturado do `kiro-cli`.

**Passos:**
1. Para cada marcador em `_FAILURE_MARKERS` (`"[exit-code:"`, `"[TIMEOUT]"`,
   `"[ERRO]"`, `"Kiro is having trouble responding"`), montar um output de
   sucesso cuja narrativa do agente cite o marcador entre aspas ou como parte
   de uma explicação (ex.: `'O log antigo mostrava "[TIMEOUT]" antes da
   correção do agente X.'`).
2. Chamar a detecção de falha para cada caso.

**Resultado esperado:**
- Retorno `None` em todos os casos — nenhum marcador citado apenas na
  narrativa dispara falha.
- Deve falhar no código atual para os marcadores textuais (`"[TIMEOUT]"`,
  `"[ERRO]"`, `"Kiro is having trouble responding"`) e passar após a correção.

---

## CT-003 — `returncode != 0` real continua detectado como falha (não regressão)

**Tipo:** unitário
**Critério de aceitação:** AC3 (preservar detecção de falha real por
exit-code)

**Pré-condição:**
- Execução do subprocesso com `returncode != 0` (ex.: `1`).

**Passos:**
1. Simular `_run` retornando um output cujo `[exit-code: 1]` foi apendado
   pelo próprio adapter (comportamento atual de `_run` quando
   `result.returncode != 0`), sem qualquer citação narrativa adicional.
2. Chamar a detecção de falha.

**Resultado esperado:**
- Retorno não-`None`, com mensagem de uma linha identificando a falha (mesmo
  contrato hoje coberto por
  `TestDetectFailureFalha.test_cada_marcador_dispara_falha` em
  `tests/test_agent_failure_detection.py`).
- Já passa hoje; não pode regredir após a correção.

---

## CT-004 — Bloco real de erro do kiro-cli (`Kiro is having trouble responding...`) no encerramento continua detectado

**Tipo:** unitário
**Critério de aceitação:** AC3 (caso real do defeito D1/D2 do incidente
#203 — `dispatch failure`, `Tool approval required`)

**Pré-condição:**
- Output reproduzindo literalmente o padrão real de abort do `kiro-cli`
  documentado no incidente #203:
  ```
  Kiro is having trouble responding right now:
     0: Failed to receive the next message: request_id: <id>,
        error: dispatch failure (io error): request or response body error
  Location:
     crates/chat-cli/src/cli/chat/mod.rs:2213
  error: Tool approval required but --no-interactive was specified.
         Use --trust-all-tools to automatically approve tools.
  [exit-code: 1]
  ```
  — ou seja, o bloco aparece como **encerramento estruturado do processo**
  (seguido de `[exit-code: 1]`), não como citação do agente.

**Passos:**
1. Chamar a detecção de falha com esse output e `returncode=1`.

**Resultado esperado:**
- Retorno não-`None`, com a causa real extraída (`dispatch failure`/`Tool
  approval required`), preservando o comportamento coberto por
  `TestDetectFailureFalha.test_extrai_erro_de_modelo_indisponivel` e
  `test_nao_reduz_a_ultima_linha`.
- Já passa hoje (o exit-code real já classifica como falha); a correção não
  pode alterar esse resultado.

---

## CT-005 — Menção a "error"/"Error:" na narrativa sem canal estruturado não é falha

**Tipo:** unitário
**Critério de aceitação:** AC3/AC4 (não regressão do caso já cabido em
`test_palavra_error_sem_marcador_nao_e_falha`, generalizado ao novo contrato)

**Pré-condição:**
- `returncode == 0`, narrativa do agente descrevendo trabalho sobre tratamento
  de erros (ex.: "Implementando o tratamento de error handling do adapter.
  Error: era a mensagem antiga; agora usamos ConfigError. Concluído.").

**Passos:**
1. Chamar a detecção de falha com esse output.

**Resultado esperado:**
- Retorno `None`.
- Já passa hoje e deve continuar passando — este caso não depende do
  `returncode`, apenas confirma que a mudança não introduz sensibilidade nova
  à palavra "error" isolada.

---

## CT-006 — Timeout e erro de `kiro-cli` não encontrado no PATH continuam detectados

**Tipo:** unitário
**Critério de aceitação:** AC3 (canais estruturados sintéticos gerados pelo
próprio adapter em `_run`, não pelo `kiro-cli`)

**Pré-condição:**
- `_run` captura `subprocess.TimeoutExpired` e retorna
  `"[TIMEOUT] Agente excedeu {N}s"`; ou captura `FileNotFoundError` e retorna
  `"[ERRO] kiro-cli não encontrado no PATH"`. Em ambos, não há processo
  finalizado (não há `returncode` do `kiro-cli` a considerar) — o próprio
  adapter sintetiza o marcador.

**Passos:**
1. Chamar a detecção de falha com cada uma dessas duas strings, isoladamente
   (sem `returncode` associado, ou com um valor sentinela definido pela
   implementação para esse caso).

**Resultado esperado:**
- Retorno não-`None` em ambos os casos — são canais estruturados do próprio
  adapter (não narrativa do agente, que nem chega a ser produzida nesses
  caminhos), e continuam sinalizando falha.
- Já passa hoje; a implementação da correção deve manter uma forma explícita
  de tratar esses dois casos como "canal estruturado", já que eles não têm um
  `subprocess.CompletedProcess.returncode` real disponível.

---

## CT-007 — Assinatura/contrato: `_detect_failure` recebe o canal estruturado, não decide só pelo texto completo

**Tipo:** unitário
**Critério de aceitação:** AC2/AC3 do body ("usar, como primeiro critério, o
`returncode` do subprocesso... não no corpo inteiro do output")

**Pré-condição:**
- Implementação concluída da correção.

**Passos:**
1. Inspecionar a assinatura do método responsável pela decisão de falha (via
   `inspect.signature` ou chamada direta) e confirmar que ela recebe
   informação do canal estruturado (`returncode` e/ou o(s) bloco(s)
   reconhecíveis de encerramento do `kiro-cli`), e não apenas o texto
   integral do output como único parâmetro de decisão.
2. Chamar a função duas vezes com o **mesmo texto de narrativa** citando um
   marcador, variando apenas o canal estruturado (`returncode=0` sem bloco de
   erro vs. `returncode=1`/bloco de erro real presente).

**Resultado esperado:**
- Os dois resultados diferem (`None` vs. mensagem de erro) apesar do texto de
  narrativa ser idêntico nos dois casos — prova de que a decisão não depende
  mais só de correspondência textual sobre o corpo inteiro.
- Deve falhar no código atual (hoje a assinatura é `_detect_failure(self,
  output: str)`, sem canal estruturado, e o resultado seria idêntico nos dois
  casos) e passar após a correção.

---

## CT-008 — Não regressão da integração em `execute()`

**Tipo:** integração
**Critério de aceitação:** AC5 (suíte existente permanece verde)

**Pré-condição:**
- Implementação concluída da correção, incluindo o ponto de chamada em
  `execute`/`_run` que agora precisa repassar o `returncode` (ou equivalente)
  para a função de detecção.

**Passos:**
1. Executar a suíte completa de `tests/test_agent_failure_detection.py`
   (inclui `TestExecuteUsaDeteccao`, que já cobre `execute()` fim a fim via
   monkeypatch de `_run`) e `tests/test_error_classification.py`.

**Resultado esperado:**
- Todos os testes pré-existentes continuam passando, sem alteração de
  expectativa nos casos de falha real (D1/D2 — `dispatch failure`, `Tool
  approval required`) nem no formato de log de conclusão/erro
  (`test_sucesso_loga_info_com_resumo`, `test_falha_loga_error_com_causa`,
  `test_linha_de_inicio_preserva_formato_do_epic`).
- A ser reexecutado após a implementação; nesta etapa (Casos de Teste), a
  suíte já passa integralmente contra o código atual (linha de base).

---

## Resultado da execução (nesta etapa)

Nesta etapa (Casos de Teste, anterior à implementação), foram definidos 8
casos de teste (CT-001 a CT-008) cobrindo:

- o falso positivo relatado (CT-001, CT-002) — devem falhar hoje;
- a não regressão dos casos de falha real já cobertos (CT-003, CT-004, CT-006)
  e do caso de "error" sem marcador (CT-005) — já passam hoje;
- o contrato de que a decisão passa a depender do canal estruturado, não do
  texto completo (CT-007) — deve falhar hoje;
- a suíte de integração/regressão completa (CT-008) — já passa hoje.

Confirmado nesta etapa, sem alterar código:

```
python -m pytest tests/test_agent_failure_detection.py tests/test_error_classification.py -q
```

Resultado: ambas as suítes passam integralmente contra `src/adapters/
kiro_cli_agent.py` no estado atual de `epic` — linha de base de não-regressão
para a implementação subsequente (etapa Desenvolvimento).

Os testes automatizados correspondentes a CT-001/CT-002/CT-007 (os que devem
falhar no estado atual) não foram adicionados ao código de produção/testes
nesta etapa — a criação do arquivo `tests/test_detect_failure_canais_
estruturados.py` (ou extensão de `tests/test_agent_failure_detection.py`) e a
alteração de `_detect_failure`/`_run` pertencem à etapa de Desenvolvimento,
conforme o objetivo desta task ser exclusivamente a definição dos casos de
teste.

Nenhuma dúvida bloqueante ou débito a registrar: a issue é autocontida e o
comportamento a corrigir é determinístico e reproduzível a partir do log real
citado (`logs/203/2026-08-24_21-39-38.md`).
