# Casos de Teste — Execução autônoma confiável (detecção de falha fiel + recuperação segura)

- **Issue:** #303
- **Story relacionada:** #303 — "Tornar a execução autônoma de agentes confiável, com detecção de falha fiel e recuperação segura de interrupções"
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/303-execucao-autonoma-confiavel`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da issue
> #303. Cada caso tem resultado esperado explícito e verificável. Os testes são
> da suíte Python do motor (pytest, em `tests/`), salvo os marcados como
> **manual/revisão** (documentação).

---

## 🔁 Escopo reconciliado (revisar-escopo, 2026-10-01) — base desta especificação

Esta especificação foi **reescrita** após a reconciliação de escopo feita pelo
planejamento (Tech Lead, Isabela Gomes), que fechou os dois conflitos de contrato
que a QA havia escalado na iteração anterior. As duas decisões já estão
**incorporadas aos critérios de aceitação do corpo da issue**; os casos abaixo as
refletem (não há mais tensão em aberto a sinalizar):

1. **Grupo D (recuperação de interrupção) × ADR #217 — resolvido.** O eixo de
   recuperação foi **reduzido ao que a ADR aceita permite sem a fronteira
   idempotente da seção 4** (que ficou **fora de escopo**, para entrega dedicada
   futura). O escopo agora é:
   - `UNKNOWN_OUTCOME` **fail-closed**: `dispatch failure` / `InternalServerError`
     após output parcial / timeout são classificados como **resultado ambíguo**
     (não sucesso); o subprocesso é invocado **no máximo uma vez** por entrega
     (sem backoff seguido de nova chamada); output / request ID / causa /
     `session_id` são **preservados** para auditoria e continuidade; a
     reconciliação e a eventual retomada ficam a cargo do **loop normal**.
   - Retry inline com backoff **apenas** para `DEFINITE_NOT_STARTED`:
     não-inicialização **comprovada mecanicamente** (ex.: `kiro-cli` ausente no
     PATH). Ausência de tool call em output parcial **não** é evidência de
     não-inicialização.
   - Parâmetros `retry.*` **aplicáveis só ao caso seguro** `DEFINITE_NOT_STARTED`:
     `max_tentativas` (int, > 0, default 3), `backoff_inicial_seg` (int, >= 0,
     default 30), `backoff_fator` (número, >= 1.0, default 2.0). Os parâmetros
     `retry.retomar_sessao` e `retry.idempotencia_ativa` da versão anterior
     foram **removidos do escopo**.
   - **Consequência nos casos:** os antigos CT-10 (retry inline genérico até
     sucesso), CT-11 (idempotência: não repetir commit/push/movimento) e CT-12
     (limite de tentativas para interrupção transitória genérica) foram
     **redesenhados**. CT-11 (idempotência de efeitos parciais) foi **removido**
     — depende da fronteira da seção 4, fora de escopo. O eixo de recuperação é
     agora coberto por: CT-10 (`UNKNOWN_OUTCOME` fail-closed — uma única
     invocação, preservação, sem retry inline), CT-11 (`DEFINITE_NOT_STARTED` —
     retry com backoff até sucesso ou limite, falha persistente ao esgotar),
     CT-12 (`UNKNOWN_OUTCOME` não dispara retry/backoff), CT-13 (observabilidade:
     causa real + origem do canal), CT-14 (validação/defaults de `retry.*`).

2. **Grupo A (ausência de resumo ⇒ falha) × suíte congelada — resolvido.**
   - O canal **"ausência do bloco final de resumo normal ⇒ falha"** foi
     **removido do escopo** (o antigo CT-06 foi **eliminado**). O kiro-cli não
     emite reconhecedor estrutural estável de "resumo normal"; inferir falha pela
     ausência dele reintroduziria o falso positivo oposto e colidiria com os
     testes de **sucesso** da suíte congelada (output vazio/curto = sucesso), que
     são legítimos. **Falha só é afirmada por sinal estruturado presente**
     (exit-code, timeout, erro interno, saída de erro estruturada); a ausência de
     sinal é **sucesso**.
   - **Precedência de contrato fixada (Grupo A):** nos casos em que a suíte
     congelada `tests/test_agent_failure_detection.py` codifica o **próprio falso
     positivo** a eliminar (classificar falha a partir de termo de erro citado na
     narrativa), **#303 prevalece** — esses testes são **atualizados/reescritos**
     nesta entrega (ver CT-05b). Os testes de **sucesso** da suíte congelada
     (output vazio/normal sem marcador = sucesso) **continuam válidos** e viram
     garantia conjunta com #303.

> Esta reconciliação **não é** decisão unilateral da QA: ela apenas transcreve,
> em casos de teste, as decisões de escopo já tomadas pelo planejamento e já
> presentes nos critérios de aceitação do corpo da issue. Nenhum critério de
> aceitação foi alterado nesta etapa.

---

## Rastreabilidade (CA → casos)

| Grupo | Critério de aceitação | Caso(s) |
|-------|-----------------------|---------|
| Detecção de falha | Narrativa com frase de erro, sem sinal estruturado → **sucesso** | CT-01 |
| Detecção de falha | Exit-code ≠ 0 → **falha** com causa dos canais estruturados | CT-02 |
| Detecção de falha | Marcador de timeout → **falha** | CT-03 |
| Detecção de falha | Erro de transporte nos canais estruturados → **falha** | CT-04 |
| Detecção de falha | Output vazio/normal sem marcador → **sucesso** | CT-04b |
| Detecção de falha | Regressão do falso positivo histórico não recorre | CT-05 |
| Detecção de falha | Suíte congelada que codifica o falso positivo é reescrita (precedência #303) | CT-05b |
| Caminhos de apoio | Caminho inexistente no lote não cancela as ferramentas válidas | CT-07 |
| Caminhos de apoio | Config e código apontam para a mesma fonte válida (todos existem) | CT-08 |
| Contexto | Contexto injetado contém tabelas preenchidas, sem aviso de conflito | CT-09 |
| Contexto | Artefato congelado (tabelas vazias) não tem precedência | CT-09b |
| Recuperação | `UNKNOWN_OUTCOME` → fail-closed: 1 invocação, preserva evidências, sem retry inline | CT-10 |
| Recuperação | `DEFINITE_NOT_STARTED` → retry com backoff até sucesso/limite; esgotado = falha persistente | CT-11 |
| Recuperação | `UNKNOWN_OUTCOME` não dispara retry inline nem backoff | CT-12 |
| Recuperação | Toda classificação/retry registra causa real + origem (canal) no log | CT-13 |
| Recuperação (config) | Validação/defaults dos parâmetros `retry.*` | CT-14 |
| Documentação | Nenhuma referência a identificador de modelo inválido permanece | CT-15 |

---

## Grupo A — Detecção de falha por canais estruturados

> Alvo principal: `src/adapters/kiro_cli_agent.py::KiroCliAgent._detect_failure`.
> Regra central (alinhada ao precedente de rate limit): a classificação
> considera **apenas** canais estruturados — código de saída ≠ 0
> (`[exit-code: N]`), marcador de timeout (`[TIMEOUT]`), marcador de erro interno
> (`[ERRO]`) e saída de erro estruturada reconhecível por marcador. A narrativa
> (texto livre) do agente **nunca** classifica. **Ausência de sinal estruturado
> = sucesso** (não existe mais o canal "ausência de resumo ⇒ falha").

### CT-01 — Narrativa cita frase de erro, sem sinal estruturado → sucesso

- **CA de origem:** "Dado um output de execução sem código de saída de erro e sem
  marcador estruturado de falha, mas cuja narrativa do agente cita uma frase de
  erro conhecida (ex.: 'Kiro is having trouble responding'), … então o resultado
  é **sucesso**."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`
  (`TestDeteccaoFalhaCanaisEstruturados`).
- **Pré-condição:** adapter `KiroCliAgent` instanciado; `output` simula execução
  bem-sucedida cuja narrativa menciona termos hoje em `_FAILURE_MARKERS`/
  `_ERROR_HINTS` (ex.: `Kiro is having trouble responding`, `InternalServerError`,
  `error:`), **sem** `[exit-code: N≠0]`, **sem** `[TIMEOUT]`, **sem** `[ERRO]`.
- **Passos:**
  1. Montar `output` contendo, no corpo narrativo, uma ou mais frases de erro
     conhecidas, sem qualquer marcador estruturado.
  2. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna `None` (sucesso). A frase de erro na narrativa
  **não** dispara falha.
- **Observações:** este é o coração da correção — hoje `"Kiro is having trouble
  responding"` consta em `_FAILURE_MARKERS` e dispara falso positivo mesmo citado
  pela narrativa. O desenvolvimento deve parar de escanear texto livre e remover
  esse termo (e demais termos de prosa) dos marcadores de classificação.
- **Convenção test-first:** `xfail(strict=True)` enquanto a detecção escaneia a
  narrativa → vira **XPASS** com a correção (sinaliza a entrega).

### CT-02 — Exit-code ≠ 0 → falha com causa dos canais estruturados

- **CA de origem:** "Dado um output com código de saída diferente de zero, …
  então o resultado é **falha** com a causa real extraída dos canais
  estruturados."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** output com marcador estruturado `[exit-code: N]`, N ≠ 0.
- **Passos:**
  1. Montar `output` com `"[exit-code: 2]"` e uma linha de erro estruturada.
  2. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna string não-vazia (falha); a causa provém do
  canal estruturado (exit-code / saída de erro); mensagem em uma única linha.
- **Observações:** preservar a extração de causa já coberta hoje. Passa sobre o
  código atual (fixa a fronteira correta).

### CT-03 — Marcador de timeout → falha

- **CA de origem:** "Dado um output com marcador de timeout, … então o resultado
  é **falha**."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** output contém o marcador `"[TIMEOUT] Agente excedeu …s"`.
- **Passos:**
  1. Montar `output` com o marcador de timeout.
  2. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna falha (string não-vazia). Timeout é canal
  estruturado, não narrativa.
- **Observações:** no eixo de recuperação, o timeout após output parcial é tratado
  como `UNKNOWN_OUTCOME` (fail-closed) — ver Grupo D. Aqui o foco é só a
  classificação sucesso×falha de `_detect_failure`.

### CT-04 — Erro de transporte nos canais estruturados → falha

- **CA de origem:** "Dado um output com erro de transporte reportado como canal
  estruturado (marcador de erro interno / saída de erro estruturada), … então o
  resultado é **falha** com a causa extraída do canal estruturado."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** output que simula erro de transporte emitido como canal
  estruturado da ferramenta (ex.: marcador de erro interno `[ERRO]`), não como
  mera narrativa.
- **Passos:**
  1. Montar `output` com o marcador estruturado de erro de transporte.
  2. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna falha, com a causa real extraída do canal
  estruturado.
- **Observações:** diferenciar do CT-01 — aqui o sinal é **estruturado**
  (marcador/seção de erro), não texto livre. O desenvolvimento deve definir
  claramente que marcadores constituem "canal estruturado".

### CT-04b — Output vazio ou normal sem marcador → sucesso

- **CA de origem:** "Dado um output vazio ou normal sem marcador estruturado, …
  então o resultado é **sucesso** (a ausência de sinal estruturado não é falha)."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** `output` vazio, ou com texto normal de conclusão, **sem**
  qualquer marcador estruturado.
- **Passos:**
  1. Chamar `_detect_failure("")`.
  2. Chamar `_detect_failure("Pronto. 3 arquivos alterados.\n")`.
- **Resultado esperado:** retorna `None` (sucesso) em ambos. A ausência de sinal
  estruturado **nunca** é falha.
- **Observações:** este caso **fixa a decisão de escopo** de que o canal
  "ausência de resumo normal ⇒ falha" foi removido. É coerente com os testes de
  sucesso da suíte congelada (`test_output_vazio_nao_e_falha`,
  `test_output_normal_nao_e_falha`), que **continuam válidos**. Passa sobre o
  código atual.

### CT-05 — Regressão do falso positivo histórico (anti-recorrência)

- **CA de origem:** "Dado o histórico do falso positivo (narrativa com termo de
  erro em execução bem-sucedida), … então existe um teste que o reproduz e
  comprova que não recorre."
- **Tipo:** unitário (regressão)
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`
  (teste nomeado explicitamente como regressão).
- **Pré-condição:** reproduzir o caso real do incidente — execução bem-sucedida
  cujo texto do agente contém `"Kiro is having trouble responding"` (e outros
  termos) no meio da narrativa, **sem** sinal estruturado.
- **Passos:**
  1. Reconstruir o output do incidente (narrativa com o(s) termo(s), sem
     marcador).
  2. Chamar `_detect_failure(output)`.
  3. Documentar no docstring do teste o vínculo com o incidente/CA.
- **Resultado esperado:** retorna `None` (sucesso). Falha com a implementação
  antiga (que escaneava texto) e passa com a nova (só canais estruturados).
- **Observações:** é o "trava" anti-regressão exigido pelo CA.
- **Convenção test-first:** `xfail(strict=True)` → **XPASS** com a correção.

### CT-05b — Suíte congelada que codifica o falso positivo é reescrita (precedência #303)

- **CA de origem:** "… os testes anteriores que afirmavam o oposto (falha a
  partir de narrativa) foram atualizados para a classificação por canal
  estruturado."
- **Tipo:** unitário (atualização de suíte de regressão existente)
- **Arquivo/alvo:** `tests/test_agent_failure_detection.py` (suíte congelada,
  restaurada no merge `c27f813`).
- **Pré-condição:** a suíte congelada afirma, hoje, falha a partir de termo de
  erro **citado na narrativa** — exatamente o falso positivo que #303 elimina.
- **Testes a reescrever/remover (codificam o falso positivo):**
  - `TestDetectFailureFalha::test_cada_marcador_dispara_falha[Kiro is having trouble responding]`
    — remover o parâmetro `"Kiro is having trouble responding"` do conjunto (os
    marcadores **estruturais** `[exit-code: 1]`, `[TIMEOUT]`, `[ERRO]`
    permanecem).
  - `TestDetectFailureFalha::test_extrai_erro_de_modelo_indisponivel` — reescrever
    para que a falha seja afirmada por **canal estruturado** (ex.: anexar
    `[exit-code: N]` ou `[ERRO]`), não pela mera presença de "Kiro is having
    trouble responding" na prosa.
  - `TestDetectFailureFalha::test_nao_reduz_a_ultima_linha` — idem: a causa real
    deve ser extraída de um output que contenha sinal estruturado.
  - `TestDetectFailureFalha::test_une_linhas_relevantes_com_pipe` — idem.
  - `TestExecuteUsaDeteccao::test_falha_loga_error_com_causa` — reescrever o
    `output` para conter sinal estruturado (ex.: `[ERRO]`/`[exit-code: N]`) além
    da causa, de modo que a classificação de falha venha do canal, não da
    narrativa.
- **Testes a PRESERVAR (legítimos — classificam sucesso):**
  - `TestDetectFailureSucesso::test_output_vazio_nao_e_falha`
  - `TestDetectFailureSucesso::test_output_normal_nao_e_falha`
  - `TestDetectFailureSucesso::test_palavra_error_sem_marcador_nao_e_falha`
  - `TestExecuteUsaDeteccao::test_sucesso_loga_info_com_resumo`
  - toda a classe `TestLastMeaningfulLine` (não trata de classificação).
- **Resultado esperado:** após a reescrita, a suíte congelada e a suíte de #303
  são **mutuamente consistentes**: falha só por sinal estruturado; narrativa
  nunca classifica; output sem sinal = sucesso.
- **Observações:** esta é a **ação concreta** da decisão de precedência fixada no
  escopo. O desenvolvimento executa a reescrita; a QA, na etapa de execução de
  testes, valida que nenhum teste remanescente classifica falha a partir de
  narrativa. Não enfraquecer as asserções de sucesso.

---

## Grupo B — Resolução dos caminhos de apoio

> Alvo: resolução dos caminhos de modelo (templates de doc/issue) referenciados
> por configuração e pelos contextos de agente; tratamento isolado de ausência
> sem cancelar o lote de ferramentas. A fonte válida de templates é
> `contexts/templates/` (confirmado no repo: `contexts/templates/docs/test-cases.md`).

### CT-07 — Caminho de apoio inexistente não cancela o lote de ferramentas

- **CA de origem:** "Dada uma referência a um caminho de apoio inexistente em um
  lote de chamadas de ferramenta, … então as ferramentas válidas do lote
  executam e a ausência é sinalizada isoladamente, sem cancelar o lote."
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`
  (`TestCaminhosDeApoio`); função a definir pela implementação (ex.:
  `resolve_support_paths` / validador por item).
- **Pré-condição:** um lote contendo N referências a caminhos de apoio, das quais
  ao menos uma é inexistente e as demais válidas.
- **Passos:**
  1. Montar o lote com caminhos válidos + um ausente.
  2. Acionar a validação/resolução de caminhos de apoio.
- **Resultado esperado:** os itens válidos são resolvidos/executados; o ausente é
  sinalizado isoladamente (ex.: warning/retorno por item), **sem** exceção que
  cancele todo o lote. Granularidade por item, não por lote.
- **Observações:** o desenvolvimento define o ponto exato de interceptação; o
  teste fixa a invariante (1 caminho ausente ≠ cancelar os válidos).

### CT-08 — Config e código apontam para a mesma fonte válida (todos existem)

- **CA de origem:** "Dado o ambiente de execução no início de uma execução,
  quando os caminhos de apoio referenciados pela configuração e pelos contextos
  são resolvidos, então todos existem e apontam para a mesma fonte válida
  (`contexts/templates/`)."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** ambiente com `contexts/templates/` presente (fonte válida);
  caminhos dirigidos por configuração e os gerados por código.
- **Passos:**
  1. Resolver os caminhos de apoio referenciados por configuração.
  2. Resolver os caminhos de apoio referenciados por código (gerados).
  3. Comparar as duas fontes.
- **Resultado esperado:** todos os caminhos existem e as duas fontes (config e
  código) apontam para o mesmo diretório-fonte válido (`contexts/templates/…`).
  Nenhuma divergência config↔código.
- **Observações:** detecta o anti-padrão de config e código apontando para pastas
  diferentes. O desenvolvimento deve centralizar a constante da fonte de
  templates.

---

## Grupo C — Contexto derivado da configuração vigente

> Alvo: `src/core/context_generator.py` (`generate_context`,
> `ensure_steering_integrity`, `_build_content`) e o despacho em
> `src/__main__.py::call_agent`. O contexto efetivo deve ser sempre o derivado da
> config vigente, com tabelas preenchidas, sem "aviso de conflito de contexto" e
> sem precedência de artefato congelado.

### CT-09 — Contexto injetado contém tabelas preenchidas, sem aviso de conflito

- **CA de origem:** "Dada a configuração vigente de boards, colunas e fluxo de
  branches, … então ele contém as tabelas de boards/colunas e de fluxo de
  branches **preenchidas**, sem aviso de conflito de contexto."
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`
  (`TestContextoDerivadoDaConfig`).
- **Pré-condição:** `config` vigente com ≥1 board com colunas e ≥1 flow com
  prefixo/base.
- **Passos:**
  1. Gerar o contexto a partir da config vigente (`_build_content`).
  2. Inspecionar o conteúdo gerado.
  3. Verificar que `ensure_steering_integrity`, quando o steering já reflete a
     config, não acusa divergência (sem aviso de conflito).
- **Resultado esperado:** o conteúdo contém a tabela de boards/colunas com ao
  menos uma linha de dados reais (coluna/nome/agente) e a tabela de flow/branches
  preenchida (prefixo/origem/merge/base). Nenhum aviso de "conflito de
  contexto"/"steering divergente" no caminho feliz.
- **Observações:** reforça que `ensure_steering_integrity` não acusa divergência
  quando o steering já reflete a config vigente (hoje retorna `False` — manter).

### CT-09b — Artefato congelado (tabelas vazias) não tem precedência

- **CA de origem:** "Dado um artefato de contexto congelado com tabelas vazias
  presente no ambiente, … então o contexto efetivo é o derivado da configuração
  vigente (o congelado não tem precedência)."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** existe um artefato de contexto congelado com tabelas vazias
  (ex.: `.kiro/steering/esteira.md` antigo com tabelas vazias) no ambiente,
  **divergente** da config vigente.
- **Passos:**
  1. Colocar no ambiente o artefato congelado com tabelas vazias.
  2. Rodar `ensure_steering_integrity(config)`.
  3. Inspecionar o contexto efetivo.
- **Resultado esperado:** o contexto efetivo é o **regenerado** a partir da config
  vigente (tabelas preenchidas); o artefato congelado é sobrescrito e não
  prevalece (`ensure_steering_integrity` retorna `True` = divergiu/corrigiu).
- **Observações:** 2ª camada — se houver um `.kiro/agents/pipe_context.json`
  legado capaz de sombrear o steering, o desenvolvimento garante que ele não tenha
  precedência (removido/regenerado). O docstring do `context_generator` indica que
  o `pipe_context.json` deixou de ser gerado (Caminho B).

---

## Grupo D — Tratamento seguro de interrupção transitória (alinhado à ADR #217)

> Alvo: `src/__main__.py::call_agent` (hoje chama `adapter.execute` sem retry) e o
> adapter `KiroCliAgent`. **Sem** fronteira idempotente da seção 4 da ADR (fora de
> escopo). A política é:
> - `UNKNOWN_OUTCOME` (`dispatch failure` / `InternalServerError` após output
>   parcial / timeout): **fail-closed** — uma única invocação por entrega, sem
>   retry inline; preservar evidências; reconciliação pelo loop normal.
> - `DEFINITE_NOT_STARTED` (não-inicialização comprovada mecanicamente, ex.:
>   `kiro-cli` ausente no PATH): retry inline com backoff e limite.
>
> Observabilidade exigida em todos: cada classificação de falha e cada retry
> seguro registra no log a **causa real** e a **origem (canal estruturado)**.
> `time.sleep` SEMPRE mockado nos casos de backoff.

### CT-10 — `UNKNOWN_OUTCOME` → fail-closed (uma invocação, preserva evidências, sem retry inline)

- **CA de origem:** "Dado um aborto transitório classificado como ambíguo
  (`dispatch failure` / `InternalServerError` após output parcial / timeout), …
  então o subprocesso é invocado **no máximo uma vez** naquela entrega (sem
  backoff seguido de nova chamada), o resultado é marcado como ambíguo (não
  sucesso), e output/request ID/causa/`session_id` são preservados para auditoria
  e continuidade."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`
  (`TestRecuperacaoInterrupcao`).
- **Pré-condição:** o adapter sinaliza aborto transitório ambíguo (ex.: output
  parcial seguido de `dispatch failure` / `InternalServerError`, ou `[TIMEOUT]`
  após output parcial); `retry.*` resolvido; `time.sleep` mockado.
- **Passos:**
  1. Configurar o adapter/execução para produzir um resultado ambíguo.
  2. Chamar o orquestrador de execução (`call_agent`).
  3. Observar o número de invocações do subprocesso e o resultado/evidências.
- **Resultado esperado:**
  - o subprocesso é invocado **exatamente uma vez** (nenhum retry inline, nenhum
    `time.sleep` de backoff disparado);
  - o resultado é classificado como `UNKNOWN_OUTCOME` (**não** sucesso, **não**
    falha definitiva);
  - output, request ID (quando disponível), causa e `session_id` são
    **preservados** (acessíveis para auditoria/continuidade).
- **Observações:** este é o cerne do fail-closed. A reconciliação de filesystem,
  git e board e a eventual retomada via `--resume-id` ficam a cargo do **loop
  normal** (não testadas aqui como retry inline).

### CT-11 — `DEFINITE_NOT_STARTED` → retry com backoff até sucesso ou limite (falha persistente)

- **CA de origem:** "Dado um aborto com não-inicialização comprovada
  mecanicamente (`DEFINITE_NOT_STARTED`, ex.: subprocesso ausente no PATH), …
  então a execução é reexecutada com backoff crescente por `backoff_fator` a
  partir de `backoff_inicial_seg`, até o limite `max_tentativas`, sem laço
  infinito; esgotado o limite, o resultado é **falha persistente** e o log
  registra o total de tentativas e a última causa."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** o adapter sinaliza `DEFINITE_NOT_STARTED` (ex.: retorna o
  marcador de `kiro-cli` ausente no PATH — hoje `"[ERRO] kiro-cli não encontrado
  no PATH"`); `retry.max_tentativas=3`, `backoff_inicial_seg`, `backoff_fator`
  resolvidos; `time.sleep` mockado.
- **Sub-casos / passos:**
  1. **Retoma até sucesso:** adapter falha com `DEFINITE_NOT_STARTED` uma vez,
     depois tem sucesso → a execução é reexecutada com backoff e conclui em
     sucesso; `time.sleep` chamado com `backoff_inicial_seg` na 1ª espera.
  2. **Esgota o limite:** adapter falha com `DEFINITE_NOT_STARTED` sempre →
     exatamente `max_tentativas` invocações (sem laço infinito); o backoff cresce
     por `backoff_fator` a partir de `backoff_inicial_seg` (ex.: 30, 60); o
     resultado é **falha persistente**; o log registra o total de tentativas e a
     última causa.
- **Resultado esperado:** retry inline **apenas** para este caso seguro; backoff
  correto (asserir os **argumentos** de `time.sleep`, não esperar tempo real);
  limite respeitado; falha persistente ao esgotar.
- **Observações:** fixa a semântica de "tentativas" (`max_tentativas=3` ⇒ 3
  invocações do subprocesso) — o desenvolvimento deve travar essa semântica (ver
  CT-14). Ausência de tool call em output parcial **não** é
  `DEFINITE_NOT_STARTED` — é `UNKNOWN_OUTCOME` (CT-10/CT-12).

### CT-12 — `UNKNOWN_OUTCOME` não dispara retry inline nem backoff

- **CA de origem:** "Dado um resultado ambíguo (`UNKNOWN_OUTCOME`), … então
  **não** há retry inline nem backoff na mesma execução; a reconciliação e a
  eventual retomada ficam a cargo do loop normal."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** resultado classificado como `UNKNOWN_OUTCOME`; `retry.*`
  resolvido com `max_tentativas>1`; `time.sleep` mockado.
- **Passos:**
  1. Produzir um `UNKNOWN_OUTCOME`.
  2. Chamar o orquestrador.
  3. Contar invocações do subprocesso e chamadas a `time.sleep`.
- **Resultado esperado:** **uma** invocação do subprocesso; **nenhuma** chamada de
  backoff (`time.sleep` não acionado pelo caminho de retry); o resultado
  permanece `UNKNOWN_OUTCOME`.
- **Observações:** par explícito de CT-11 — garante que o retry inline é
  **exclusivo** de `DEFINITE_NOT_STARTED`. Impede regressão de "retry cego" vedado
  pela ADR.

### CT-13 — Observabilidade: causa real + origem do canal em toda classificação/retry

- **CA de origem:** "Dada qualquer classificação de falha ou retry seguro, …
  então o log registra a causa real e a origem no canal estruturado (ex.: campo
  que diferencie `exit-code` de `timeout` de `erro interno`), permitindo
  auditoria; a narrativa do agente nunca é a origem registrada." + "O resultado
  ambíguo (`UNKNOWN_OUTCOME`) é registrado de forma acionável (causa + evidência
  preservada), distinguindo-o de sucesso e de falha definitiva."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`.
- **Pré-condição:** execuções que produzem (a) falha por canal estruturado, (b)
  `UNKNOWN_OUTCOME` e (c) retry seguro `DEFINITE_NOT_STARTED`.
- **Passos:**
  1. Disparar cada caso e capturar os registros de log.
- **Resultado esperado:** cada registro contém (a) a causa real e (b) a
  origem/canal estruturado (campo que diferencie `exit-code` / `timeout` / `erro
  interno`); o `UNKNOWN_OUTCOME` é registrado de forma distinta de sucesso e de
  falha definitiva, com a evidência preservada; a narrativa do agente nunca é a
  origem registrada.
- **Observações:** o desenvolvimento define a chave/campo de origem no log; o
  teste assegura que causa e origem coexistem e que `UNKNOWN_OUTCOME` é
  distinguível.

### CT-14 — Validação e defaults dos parâmetros `retry.*`

- **CA de origem:** "Dada a ausência da chave `retry` na configuração, … então os
  defaults são aplicados (`max_tentativas=3`, `backoff_inicial_seg=30`,
  `backoff_fator=2.0`); dado qualquer valor fora das restrições
  (`max_tentativas` ≤ 0 ou não-inteiro; `backoff_inicial_seg` < 0;
  `backoff_fator` < 1.0), … então ela rejeita com erro de configuração nomeando a
  chave."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_execucao_autonoma_confiavel.py`
  (`TestRetryConfig`); validação em `src/core/config.py` (padrão
  `validate_max_attempts`/`resolve_max_attempts`).
- **Pré-condição:** função de validação de `retry` em `config.py` (a implementar).
- **Passos / sub-casos:**
  1. Ausência de `retry` → aplica defaults: `max_tentativas=3`,
     `backoff_inicial_seg=30`, `backoff_fator=2.0`.
  2. `max_tentativas` inválido (0, negativo, `True`/bool, float, string) →
     `ConfigError` nomeando `retry.max_tentativas`.
  3. `backoff_inicial_seg` < 0 (ou bool/não-inteiro) → `ConfigError` nomeando
     `retry.backoff_inicial_seg`.
  4. `backoff_fator` < 1.0 (ou bool/não-numérico) → `ConfigError` nomeando
     `retry.backoff_fator`.
  5. Valores válidos → aceitos e resolvidos corretamente.
- **Resultado esperado:** validação rejeita cada valor inválido com `ConfigError`
  nomeando a chave; resolve defaults quando ausentes; aceita válidos.
- **Observações:** espelhar o estilo já existente (bool rejeitado antes de int;
  mensagem identifica a chave — ver `validate_max_attempts`). **Não** há mais
  `retry.retomar_sessao` nem `retry.idempotencia_ativa` (removidos do escopo); se
  presentes, ficam a critério do desenvolvimento ignorá-los ou rejeitá-los, mas o
  teste **não** os exige.

---

## Grupo E — Higiene de documentação

### CT-15 — Nenhuma referência a identificador de modelo inválido na doc de exemplo

- **CA de origem:** "Dada a documentação de exemplo do produto, quando ela é
  revisada, então nenhuma referência a identificador de modelo inválido ou
  inexistente permanece (apenas identificadores válidos: `claude-sonnet-5`,
  `auto`, `claude-haiku-4.5`)."
- **Tipo:** manual/revisão + unitário de guarda (opcional)
- **Arquivo/alvo:** revisão de `README.md` (hoje `model: claude-sonnet-4-20250514`
  na seção de exemplo do `pipe.yml`, linha ~50); opcionalmente um teste de guarda
  em `tests/test_execucao_autonoma_confiavel.py` que varre a doc de exemplo por
  identificadores inválidos.
- **Pré-condição:** lista dos identificadores de modelo **válidos** vigentes:
  `claude-sonnet-5`, `auto`, `claude-haiku-4.5`.
- **Passos:**
  1. Levantar todas as referências a `model:` na documentação de exemplo do
     produto (ex.: `README.md`).
  2. Comparar com a lista de identificadores válidos.
  3. Corrigir as inválidas (desenvolvimento) e revalidar.
- **Resultado esperado:** nenhuma referência a identificador de modelo
  inválido/inexistente permanece. Se houver teste de guarda, falha enquanto houver
  identificador inválido e passa após a correção.
- **Observações:** QA valida a ausência; a correção textual é do desenvolvimento.
  Recomendo um teste de guarda simples (regex por `model:`) para evitar
  reintrodução. **Fora de escopo:** não alterar o mecanismo de resolução de model,
  apenas a doc de exemplo.

---

## Notas de execução para o desenvolvimento

- **Isolamento:** usar `monkeypatch`/`tmp_path` e **nunca** fazer `monkeypatch`
  do próprio método sob teste (lição do incidente #106 — mascarava ausência de
  cobertura).
- **Sem espera real:** mockar `time.sleep` nos casos de backoff (CT-11),
  asserindo os argumentos de backoff.
- **Sem rede/subprocesso real:** `_run`, `subprocess.run`, listagem de sessões e
  chamadas de board devem ser fakes/mocks; os testes rodam offline.
- **Baseline:** no momento da escrita destes casos, o retry (`retry.*`), a
  classificação `UNKNOWN_OUTCOME`/`DEFINITE_NOT_STARTED`, a resolução de caminhos
  de apoio e a validação `retry` **não existem** no repositório — os testes
  correspondentes devem falhar antes da implementação e passar depois (padrão
  test-first de `test_error_classification.py` e `test_sanitize_relations.py`).
- **Precedência de contrato (Grupo A):** ao implementar a classificação
  só-por-canais, o desenvolvimento **deve** reescrever os testes da suíte
  congelada listados em CT-05b (que codificam o falso positivo) e **preservar**
  os testes de sucesso. #303 prevalece sobre o falso positivo; os testes de
  sucesso são garantia conjunta.
- **ADR (Grupo D):** a recuperação segue a ADR `retry-kiro-cli/idempotencia.md`
  **sem** a fronteira da seção 4 (fora de escopo): `UNKNOWN_OUTCOME` fail-closed
  (uma invocação, sem retry inline) + retry inline só para
  `DEFINITE_NOT_STARTED`. Não implementar retry inline para `UNKNOWN_OUTCOME` —
  violaria a ADR.
