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

## 🔁 Reconciliação QA (revisar-caso-de-teste → revisar-escopo) — 2026-10-01

O desenvolvimento (Sofia Carvalho, PL) devolveu a #303 a esta coluna
(`revisar-caso-de-teste`) com **dois conflitos de contrato confirmados por
código**. A QA, ao reconciliar, confirmou ambos e decidiu encaminhar a issue ao
**planejamento (`revisar-escopo`)**, por serem contradições do **escopo em si**
contra artefatos que a QA não pode alterar (uma ADR aceita e uma suíte de
regressão congelada de outra entrega) — não dúvidas que a QA resolve com os
critérios de aceitação e a suíte existente.

### Conflito 1 — Grupo D (retry idempotente, CT-10..CT-13) × ADR #217 (aceita)

A ADR `doc/architecture/retry-kiro-cli/idempotencia.md` (**aceita**) rejeita
retry inline para `dispatch failure` / `InternalServerError` / timeout
(`UNKNOWN_OUTCOME`, *fail-closed*) e só o admite após a **fronteira idempotente
da seção 4**, cujo item 4.3 exige **interposição real** de commit/push/movimento
("não podem contornar a fronteira por shell ou CLI arbitrários; observar texto
de saída não satisfaz"). A arquitetura vigente **não** interpõe esses efeitos: o
adapter roda `kiro-cli` com `--trust-all-tools`
(`src/adapters/kiro_cli_agent.py`) e o core apenas **instrui em prosa** o agente
a rodar git e mover arquivos (`src/core/agent.py`). Logo, satisfazer CT-11 ("não
repetir operações já efetivadas" + journal/outbox + verificação de pós-condição)
exige **redefinir o modelo de execução e o mecanismo de auto-aprovação** —
ambos **fora de escopo** de #303. Esse é exatamente o cenário que esta QA
pré-declarou abaixo: fronteira idempotente fora do orçamento ⇒ o escopo da
recuperação torna-se contraditório com a ADR ⇒ **revisar-escopo**.

### Conflito 2 — Grupo A (CT-06: ausência de resumo ⇒ falha) × suíte congelada

A regra central ("classificar só por canais estruturados, ignorando a
narrativa") é **correta e implementável** (CT-01/CT-05 viram XPASS). O problema é
só o canal **"ausência do bloco final de resumo normal ⇒ falha"** (CT-06): ele
contradiz diretamente a suíte de regressão congelada
`tests/test_agent_failure_detection.py` (restaurada em `c27f813`), que afirma o
oposto — `test_output_vazio_nao_e_falha`, `test_output_normal_nao_e_falha`,
`test_palavra_error_sem_marcador_nao_e_falha`,
`TestExecuteUsaDeteccao::test_sucesso_loga_info_com_resumo` tratam output sem
bloco de resumo como **sucesso**. Não há interpretação em que "ausência de
resumo ⇒ falha" e "output vazio/curto ⇒ sucesso" sejam ambos verdadeiros.

**Por que isto também é `revisar-escopo` e não decisão QA isolada:** reconciliar
exige **precedência entre duas entregas** — ou #303 prevalece (e a suíte
congelada de uma entrega anterior é reescrita/invalidada, mudando os critérios
de aceite daquela entrega), ou a suíte prevalece (e o canal CT-06 de #303 é
afrouxado/removido, mudando o critério de aceite de #303). Qualquer das saídas
**altera requisitos** — vedado à QA. A QA não reescreve a suíte de regressão de
outra entrega nem enfraquece o critério de #303 sem decisão de escopo.

**Questões que o planejamento deve resolver (revisar-escopo):**

1. **Grupo D:** reconciliar o eixo "Recuperação de interrupção transitória" de
   #303 com a ADR #217. Opções: (a) incluir no escopo de #303 a fronteira
   idempotente da seção 4 (chave estável, journal/outbox, interposição real,
   pós-condição, operações declarativas) — reconhecendo que isso implica tocar o
   modelo de execução/auto-aprovação hoje fora de escopo; (b) reduzir #303 ao que
   a ADR permite sem a fronteira (`UNKNOWN_OUTCOME` *fail-closed* + preservação
   de sessão + observabilidade, retry inline **apenas** para
   `DEFINITE_NOT_STARTED` comprovado mecanicamente) e reescrever CT-10..CT-13
   conforme; ou (c) abrir uma entrega dedicada para a fronteira idempotente e
   deixar #303 só com os eixos A/B/C/E + a parte segura de recuperação.
2. **Grupo A/CT-06:** decidir a **precedência de contrato** entre #303 e a suíte
   congelada `test_agent_failure_detection.py`, e **fixar o formato real do
   "bloco final de resumo normal" do kiro-cli** (o reconhecedor estrutural). Sem
   esse formato, CT-06 não é implementável sem ambiguidade. Decidido isso, a QA
   atualiza CT-06 e a suíte afetada de forma consistente.

**O que permanece válido e pronto (sem conflito), para quando o escopo voltar:**

- **A (parte não-conflitante):** classificação só-por-canais ignorando a
  narrativa — CT-01/CT-05 (XPASS sinaliza entrega), CT-02/CT-03/CT-04 (já fixam a
  fronteira sobre o código atual).
- **B — Caminhos de apoio:** CT-07 (resolução por item, não cancelar o lote) +
  CT-08 (fonte única `contexts/templates/`).
- **C — Contexto:** CT-09/CT-09b (tabelas preenchidas; congelado sem precedência;
  `pipe_context.json` legado não sombreia o steering).
- **E — Documentação:** CT-15 (`README.md` ainda traz `model:
  claude-sonnet-4-20250514`; corrigir para identificador válido + guarda
  `MODELOS_VALIDOS`).
- **D (config):** CT-14 (validação/defaults de `retry.*`) é implementável
  independentemente da fronteira — a decisão do planejamento sobre o Grupo D pode
  mantê-la ou ajustá-la.

> Esta reconciliação **não altera** nenhum critério de aceitação nem a
> arquitetura: apenas registra os dois conflitos verificados e os encaminha ao
> fórum competente (planejamento). O esqueleto de testes e a rastreabilidade
> abaixo permanecem como especificados.

---

## ⚠️ Conflito de arquitetura a resolver antes/durante o desenvolvimento

A issue #303 pede, no eixo "Recuperação de interrupção transitória", **retry
inline com backoff + retomada de sessão** condicionado a idempotência
(parâmetros `retry.*`). Existe uma decisão arquitetural **aceita** em
`doc/architecture/retry-kiro-cli/idempotencia.md` (ADR #217/#208) que **rejeitou
retry inline** para `dispatch failure` / `InternalServerError` / timeout,
classificando-os como `UNKNOWN_OUTCOME` e adotando política *fail-closed* (uma
única invocação por entrega; reconciliação pelo loop normal).

A ADR, porém, admite retry automático futuro **desde que** exista uma fronteira
idempotente (seção 4): chave estável de operação, journal/outbox durável,
interposição real dos efeitos (commit/push/movimento de coluna), verificação de
pós-condição e operações declarativas. A issue #303 pede exatamente essa
garantia de idempotência ("o retry só reexecuta operações de escrita que ainda
não foram efetivadas; operações já aplicadas não são repetidas").

**Implicação para os testes:** os casos do grupo "Recuperação de interrupção"
(CT-10 a CT-13) assumem que o desenvolvimento **implementa a fronteira
idempotente da seção 4 da ADR** antes de habilitar o retry — caso contrário o
retry inline viola a ADR vigente. Se o desenvolvimento concluir que a fronteira
idempotente está fora do orçamento desta entrega, o escopo da recuperação é
**contraditório com a arquitetura aceita** e a issue deve voltar ao
planejamento (coluna `planejamento`, via `revisar-escopo`) para reconciliar
#303 com a ADR #217 — não cabe à QA alterar requisito nem arquitetura.
Documento esta tensão aqui e sigo especificando os casos conforme o escopo
escrito, com a garantia de idempotência como invariante central e testável.

---

## Rastreabilidade (CA → casos)

| Grupo | Critério de aceitação | Caso(s) |
|-------|-----------------------|---------|
| Detecção de falha | Narrativa com frase de erro + resumo normal → **sucesso** | CT-01 |
| Detecção de falha | Exit-code ≠ 0 → **falha** com causa dos canais estruturados | CT-02 |
| Detecção de falha | Marcador de timeout → **falha** | CT-03 |
| Detecção de falha | Erro de transporte nos canais estruturados → **falha** | CT-04 |
| Detecção de falha | Regressão do falso positivo histórico não recorre | CT-05 |
| Detecção de falha | Ausência do bloco final de resumo normal → **falha** | CT-06 |
| Caminhos de apoio | Caminho inexistente no lote não cancela as ferramentas válidas | CT-07 |
| Caminhos de apoio | Config e código apontam para a mesma fonte válida (todos existem) | CT-08 |
| Contexto | Contexto injetado contém tabelas preenchidas, sem aviso de conflito | CT-09 |
| Contexto | Artefato congelado (tabelas vazias) não tem precedência | CT-09b |
| Recuperação | Interrupção sem efeito aplicado → retoma com backoff + sessão até sucesso/limite | CT-10 |
| Recuperação | Interrupção após efeito aplicado → não repete; log indica puladas | CT-11 |
| Recuperação | Interrupção persistente → encerra em `max_tentativas`, falha persistente | CT-12 |
| Recuperação | Todo retry/classificação registra causa real + origem (canal) no log | CT-13 |
| Recuperação (config) | Validação/defaults dos parâmetros `retry.*` | CT-14 |
| Documentação | Nenhuma referência a identificador de modelo inválido permanece | CT-15 |

---

## Grupo A — Detecção de falha por canais estruturados

> Alvo principal: `src/adapters/kiro_cli_agent.py::KiroCliAgent._detect_failure`.
> Regra central (alinhada ao precedente de rate limit): a classificação
> considera **apenas** canais estruturados (exit-code, marcador de timeout,
> marcador de erro interno, ausência do bloco final de resumo normal, saída de
> erro estruturada). A narrativa (texto livre) do agente **nunca** classifica.

### CT-01 — Narrativa cita frase de erro, mas o resumo final é normal → sucesso

- **CA de origem:** "Dado um output cujo bloco final de resumo é normal e sem
  código de saída de erro, mas cuja narrativa cita uma frase de erro conhecida,
  … então o resultado é **sucesso**."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_agent_failure_detection.py` (novos testes na
  classe `TestDetectFailureSucesso`) ou novo
  `tests/test_deteccao_falha_canais_estruturados.py`.
- **Pré-condição:** adapter `KiroCliAgent` instanciado; output simula execução
  bem-sucedida cuja narrativa menciona termos hoje em `_FAILURE_MARKERS`/
  `_ERROR_HINTS` (ex.: `Kiro is having trouble responding`, `InternalServerError`,
  `error:`), mas termina com o bloco de resumo normal (crédito/tempo) e sem
  `[exit-code: N≠0]`.
- **Passos:**
  1. Montar `output` contendo, no corpo narrativo, uma frase de erro conhecida
     (ex.: `"Implementei o tratamento para 'Kiro is having trouble responding'"`).
  2. Acrescentar ao final um bloco de resumo normal (ex.: linha de crédito/tempo
     que a ferramenta emite em execução bem-sucedida) e exit-code 0.
  3. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna `None` (sucesso). A frase de erro na narrativa
  **não** dispara falha. Em `execute()`, loga `info … execução concluída`.
- **Observações:** este é o coração da correção — hoje `"Kiro is having trouble
  responding"` em `_FAILURE_MARKERS` dispara falso positivo mesmo quando citado
  pela narrativa. O desenvolvimento deve parar de escanear texto livre.

### CT-02 — Exit-code ≠ 0 → falha com causa dos canais estruturados

- **CA de origem:** "Dado um output com código de saída diferente de zero, …
  então o resultado é **falha** com a causa real extraída dos canais
  estruturados."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_agent_failure_detection.py::TestDetectFailureFalha`.
- **Pré-condição:** output com marcador estruturado `[exit-code: N]`, N ≠ 0.
- **Passos:**
  1. Montar `output` com `"[exit-code: 2]"` e uma linha de erro estruturada.
  2. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna string não-vazia (falha); a causa provém do
  canal estruturado (exit-code / saída de erro), não da narrativa; mensagem em
  uma única linha.
- **Observações:** preservar a extração de causa já coberta pelos testes atuais.

### CT-03 — Marcador de timeout → falha

- **CA de origem:** "Dado um output com marcador de timeout, … então o resultado
  é **falha**."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_agent_failure_detection.py::TestDetectFailureFalha`.
- **Pré-condição:** `_run` retorna o marcador `"[TIMEOUT] Agente excedeu …s"`.
- **Passos:**
  1. Montar `output` contendo o marcador de timeout.
  2. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna falha (string não-vazia). Timeout é tratado
  como falha (coerente com a ADR, que o classifica como `UNKNOWN_OUTCOME` —
  resultado não-sucesso).
- **Observações:** o timeout é canal estruturado, não narrativa.

### CT-04 — Erro de transporte nos canais estruturados → falha

- **CA de origem:** "Dado um output com erro de transporte reportado nos canais
  estruturados, … então o resultado é **falha**."
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_agent_failure_detection.py::TestDetectFailureFalha`.
- **Pré-condição:** output que simula erro de transporte emitido como canal
  estruturado da ferramenta (ex.: marcador de erro interno/`[ERRO]`, saída de
  erro estruturada de dispatch), não como mera narrativa.
- **Passos:**
  1. Montar `output` com o marcador estruturado de erro de transporte.
  2. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna falha, com a causa real extraída do canal
  estruturado.
- **Observações:** diferenciar do CT-01 — aqui o sinal é **estruturado**
  (marcador/seção de erro), não texto livre do agente. O desenvolvimento deve
  definir claramente que marcadores são "canal estruturado" vs. "narrativa".

### CT-05 — Regressão do falso positivo histórico (anti-recorrência)

- **CA de origem:** "Dado o histórico do falso positivo (narrativa com termo de
  erro em execução bem-sucedida), … então existe um teste que o reproduz e
  comprova que não recorre."
- **Tipo:** unitário (regressão)
- **Arquivo/alvo:** novo teste nomeado explicitamente como regressão, ex.:
  `tests/test_deteccao_falha_canais_estruturados.py::test_regressao_falso_positivo_narrativa`.
- **Pré-condição:** reproduzir o caso real do incidente — execução bem-sucedida
  cujo texto do agente contém `"Kiro is having trouble responding"` (ou outro
  termo de erro) no meio da narrativa, com resumo final normal.
- **Passos:**
  1. Reconstruir o output do incidente (narrativa com o termo + resumo normal).
  2. Chamar `_detect_failure(output)`.
  3. Documentar no docstring do teste o vínculo com o incidente/CA.
- **Resultado esperado:** retorna `None` (sucesso). O teste falha com a
  implementação antiga (que escaneava texto) e passa com a nova (só canais
  estruturados).
- **Observações:** este teste é o "trava" anti-regressão exigido pelo CA.

### CT-06 — Ausência do bloco final de resumo normal → falha

- **CA de origem:** escopo "Canais a considerar: … ausência do bloco final de
  resumo normal (crédito/tempo)".
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_deteccao_falha_canais_estruturados.py`.
- **Pré-condição:** output que **não** contém o bloco final de resumo normal
  (execução cortada no meio sem exit-code explícito), simulando interrupção de
  streaming.
- **Passos:**
  1. Montar `output` sem o bloco de resumo final e sem marcadores óbvios.
  2. Chamar `_detect_failure(output)`.
- **Resultado esperado:** retorna falha (string não-vazia): a ausência do
  resumo normal é, por si, canal estruturado de falha.
- **Observações:** o desenvolvimento deve definir o reconhecedor do "bloco final
  de resumo normal" (crédito/tempo) de forma estrutural, não por texto livre.
  **Atenção à regressão:** CT-01 (narrativa com termo de erro **mas com** resumo
  normal) deve continuar sucesso; CT-06 (sem resumo normal) deve ser falha —
  os dois juntos fixam a fronteira.

---

## Grupo B — Resolução dos caminhos de apoio

> Alvo: resolução dos caminhos de modelo (templates de doc/issue) referenciados
> por configuração e pelos contextos de agente; tratamento isolado de ausência
> sem cancelar o lote de ferramentas. A fonte válida de templates é
> `contexts/templates/` (ex.: `contexts/templates/docs/test-cases.md`).

### CT-07 — Caminho de apoio inexistente não cancela o lote de ferramentas

- **CA de origem:** "Dada uma referência a um caminho de apoio inexistente em um
  lote de chamadas de ferramenta, … então as ferramentas válidas do lote
  executam e a ausência é sinalizada isoladamente, sem cancelar o lote."
- **Tipo:** unitário/integração
- **Arquivo/alvo:** novo `tests/test_caminhos_de_apoio.py` (função a definir
  pela implementação — ex.: `resolve_support_paths` / validador por item).
- **Pré-condição:** um lote contendo N referências a caminhos de apoio, das
  quais ao menos uma é inexistente e as demais válidas.
- **Passos:**
  1. Montar o lote com caminhos válidos + um ausente.
  2. Acionar a validação/resolução de caminhos de apoio.
- **Resultado esperado:** os itens válidos são resolvidos/executados; o ausente
  é sinalizado isoladamente (ex.: warning/retorno por item), **sem** levantar
  exceção que cancele todo o lote. A granularidade é por item, não por lote.
- **Observações:** o escopo explicita que o motor valida o lote "em bloco" hoje
  — o desenvolvimento deve trocar para validação por item (isolar a ausência).
  O desenvolvimento define o ponto exato de interceptação; o teste fixa a
  invariante (um caminho ausente ≠ cancelar os válidos).

### CT-08 — Config e código apontam para a mesma fonte válida (todos existem)

- **CA de origem:** "Dado o ambiente de execução no início de uma execução,
  quando os caminhos de apoio referenciados pela configuração e pelos contextos
  são resolvidos, então todos existem (configuração e código apontam para a
  mesma fonte válida)."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_caminhos_de_apoio.py`.
- **Pré-condição:** ambiente com `contexts/templates/` presente (fonte válida);
  caminhos dirigidos por configuração e os gerados por código.
- **Passos:**
  1. Resolver os caminhos de apoio referenciados por configuração.
  2. Resolver os caminhos de apoio referenciados por código (gerados).
  3. Comparar as duas fontes.
- **Resultado esperado:** todos os caminhos existem no ambiente e as duas fontes
  (config e código) apontam para o mesmo diretório-fonte válido
  (`contexts/templates/…`). Nenhuma divergência config↔código.
- **Observações:** este caso detecta o anti-padrão de config e código apontando
  para pastas diferentes. O desenvolvimento deve centralizar a constante da
  fonte de templates.

---

## Grupo C — Contexto derivado da configuração vigente

> Alvo: `src/core/context_generator.py` (`generate_context`,
> `ensure_steering_integrity`, `_build_content`) e o despacho em
> `src/__main__.py::call_agent`. O contexto efetivo deve ser sempre o derivado
> da config vigente, com tabelas preenchidas, sem "aviso de conflito de
> contexto" e sem precedência de artefato congelado.

### CT-09 — Contexto injetado contém tabelas preenchidas, sem aviso de conflito

- **CA de origem:** "Dada a configuração vigente de boards, colunas e fluxo de
  branches, … então ele contém as tabelas de boards/colunas e de fluxo de
  branches **preenchidas**, sem aviso de conflito de contexto."
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_context_generator.py` (novos testes) e/ou
  `tests/test_steering_integrity.py`.
- **Pré-condição:** `config` vigente com ≥1 board com colunas e ≥1 flow com
  prefixo/base.
- **Passos:**
  1. Gerar o contexto a partir da config vigente (`generate_context` /
     `_build_content`).
  2. Inspecionar o conteúdo gerado.
  3. Capturar logs de warning durante o despacho (`call_agent`).
- **Resultado esperado:** o conteúdo contém a tabela de boards/colunas com ao
  menos uma linha de dados (coluna/nome/agente reais, não cabeçalho vazio) e a
  tabela de flow/branches preenchida (prefixo/origem/merge/base). **Nenhum**
  log de "conflito de contexto"/"steering divergente" é emitido no caminho feliz.
- **Observações:** reforça que `ensure_steering_integrity` não deve acusar
  divergência quando o steering já reflete a config vigente (hoje retorna
  `False` nesse caso — manter).

### CT-09b — Artefato congelado (tabelas vazias) não tem precedência

- **CA de origem:** "Dado um artefato de contexto congelado com tabelas vazias
  presente no ambiente, … então o contexto efetivo é o derivado da configuração
  vigente (o congelado não tem precedência)."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_context_generator.py` /
  `tests/test_steering_integrity.py`.
- **Pré-condição:** existe um artefato de contexto congelado com tabelas vazias
  (ex.: `.kiro/steering/esteira.md` ou `.kiro/agents/pipe_context.json` antigo
  com tabelas vazias) no ambiente, **divergente** da config vigente.
- **Passos:**
  1. Colocar no ambiente o artefato congelado com tabelas vazias.
  2. Iniciar o fluxo que injeta o contexto (`ensure_steering_integrity` antes de
     `call_agent`).
  3. Inspecionar o contexto efetivo entregue ao agente.
- **Resultado esperado:** o contexto efetivo é o **regenerado** a partir da
  config vigente (tabelas preenchidas); o artefato congelado é sobrescrito e não
  prevalece. Se houver um `pipe_context.json` legado capaz de "sombrear" o
  steering, o desenvolvimento garante que ele não tenha precedência (ou é
  removido/regenerado).
- **Observações:** o docstring de `context_generator.py` indica que o
  `pipe_context.json` deixou de ser gerado (Caminho B). O desenvolvimento deve
  garantir que nenhum artefato congelado remanescente sombreie o steering
  vigente — e o teste prova a precedência do gerado.

---

## Grupo D — Recuperação de interrupção transitória com retry idempotente

> Alvo: `src/__main__.py::call_agent` (hoje chama `adapter.execute` sem retry) e
> o adapter `KiroCliAgent`. **Pré-requisito arquitetural:** a fronteira
> idempotente da seção 4 da ADR `retry-kiro-cli/idempotencia.md` (chave estável,
> journal/outbox, interposição real de commit/push/movimento de coluna,
> verificação de pós-condição, operações declarativas). Sem ela, o retry inline
> viola a ADR — ver o aviso no topo deste documento.
>
> Observabilidade exigida em todos os casos deste grupo: cada retry e cada
> classificação de falha registra no log a **causa real** e a **origem (canal
> estruturado)**; o retry registra **quais operações foram puladas** por já
> estarem aplicadas.

### CT-10 — Interrupção sem efeito aplicado → retoma com backoff e sessão até sucesso/limite

- **CA de origem:** "Dada uma interrupção transitória sem efeito colateral já
  aplicado, … então a execução é retomada com backoff e com a sessão anterior,
  sem intervenção humana, até sucesso ou até o limite de tentativas."
- **Tipo:** integração
- **Arquivo/alvo:** novo `tests/test_retry_recuperacao.py`.
- **Pré-condição:** `retry` ativo (`max_tentativas=3`, `backoff_inicial_seg`,
  `backoff_fator`, `retomar_sessao=True`, `idempotencia_ativa=True`); fronteira
  idempotente registrando que **nenhuma** operação de escrita foi efetivada; o
  adapter sinaliza interrupção transitória na 1ª tentativa e sucesso na 2ª.
  `time.sleep` mockado (sem espera real).
- **Passos:**
  1. Configurar o adapter para falhar transitoriamente uma vez e depois ter
     sucesso.
  2. Chamar o orquestrador de execução (`call_agent` com retry).
  3. Observar número de tentativas, uso de backoff e retomada de sessão.
- **Resultado esperado:** a execução é retomada automaticamente (sem
  intervenção humana); o backoff cresce por `backoff_fator` a partir de
  `backoff_inicial_seg`; a sessão anterior é retomada (`--resume-id`); conclui em
  sucesso dentro do limite. `time.sleep` chamado com os valores de backoff
  esperados.
- **Observações:** o teste deve mockar o sleep e asserir os **argumentos** do
  backoff, não esperar tempo real.

### CT-11 — Interrupção após efeito aplicado → não repete; log indica puladas

- **CA de origem:** "Dada uma interrupção após push, commit ou movimento de
  coluna já efetivado, … então nenhuma dessas operações é repetida e o log
  indica quais foram puladas por já estarem aplicadas."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_retry_recuperacao.py`.
- **Pré-condição:** fronteira idempotente registra que `commit`, `push` e/ou
  `movimento de coluna` já foram **efetivados** (estado `applied`/`verified`);
  interrupção ocorre após esses efeitos; `idempotencia_ativa=True`.
- **Passos:**
  1. Marcar no journal/outbox as operações de escrita como já aplicadas.
  2. Disparar interrupção transitória e o retry.
  3. Inspecionar que as operações aplicadas NÃO foram reexecutadas e o log.
- **Resultado esperado:** nenhuma das operações já efetivadas (commit/push/
  movimento de coluna) é repetida; a verificação de pós-condição confirma o
  estado desejado; o log lista explicitamente as operações **puladas por já
  estarem aplicadas**.
- **Observações:** invariante central da entrega. Casar com a seção 4 da ADR
  (operações declarativas: reaplicar = no-op). Testar as três operações.

### CT-12 — Interrupção persistente → encerra em `max_tentativas` (falha persistente)

- **CA de origem:** "Dada uma interrupção que persiste, quando o número de
  tentativas atinge `retry.max_tentativas`, então a recuperação encerra, a
  execução é classificada como falha persistente e o reprocessamento para (o log
  registra o total de tentativas e a última causa)."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_retry_recuperacao.py`.
- **Pré-condição:** adapter sinaliza interrupção transitória em **todas** as
  tentativas; `max_tentativas=3`; `time.sleep` mockado.
- **Passos:**
  1. Configurar o adapter para falhar transitoriamente sempre.
  2. Chamar o orquestrador com retry.
  3. Contar invocações e observar a classificação final e os logs.
- **Resultado esperado:** exatamente `max_tentativas` invocações (sem laço
  infinito); a execução é classificada como **falha persistente**; o
  reprocessamento para; o log registra o total de tentativas e a última causa.
- **Observações:** fixa o limite superior e a ausência de laço infinito.
  `max_tentativas` tentativas totais (confirmar com o desenvolvimento se o
  default 3 significa 3 execuções ou 1 + 3 retries — ver CT-14; o teste deve
  travar a semântica escolhida).

### CT-13 — Observabilidade: causa real + origem do canal em todo retry/classificação

- **CA de origem:** "Dado qualquer retry ou classificação de falha, … então o
  log registra a causa real e a origem no canal estruturado, permitindo
  auditoria."
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_retry_recuperacao.py` e
  `tests/test_deteccao_falha_canais_estruturados.py`.
- **Pré-condição:** execução que falha/retenta, com causa conhecida vinda de um
  canal estruturado identificável (ex.: exit-code, timeout, erro de transporte).
- **Passos:**
  1. Disparar uma classificação de falha e um retry.
  2. Capturar os registros de log emitidos.
- **Resultado esperado:** cada registro de retry e de classificação contém (a) a
  causa real e (b) a origem/canal estruturado (ex.: campo que diferencie
  `exit-code` de `timeout` de `transporte`), permitindo auditoria. A narrativa do
  agente nunca é a origem registrada.
- **Observações:** o desenvolvimento define a chave/campo de origem no log; o
  teste assegura que causa e origem coexistem no registro.

### CT-14 — Validação e defaults dos parâmetros `retry.*`

- **CA de origem:** escopo "Parâmetros de configuração a suportar: `retry.*`"
  (obrigatórios, com defaults e restrições).
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_project_config.py` ou novo
  `tests/test_retry_config.py` (validação em `src/core/config.py`).
- **Pré-condição:** função de validação de `retry` em `config.py` (a implementar,
  no padrão de `validate_max_attempts`/`resolve_max_attempts`).
- **Passos / sub-casos:**
  1. Ausência de `retry` → aplica defaults: `max_tentativas=3`,
     `backoff_inicial_seg=30`, `backoff_fator=2.0`, `retomar_sessao=True`,
     `idempotencia_ativa=True`.
  2. `max_tentativas` inválido (0, negativo, `True`/bool, float, string) →
     `ConfigError` identificando a chave.
  3. `backoff_inicial_seg` < 0 → `ConfigError`.
  4. `backoff_fator` < 1.0 → `ConfigError`.
  5. `retomar_sessao` / `idempotencia_ativa` não-booleanos → `ConfigError`.
  6. Valores válidos → aceitos e resolvidos corretamente.
- **Resultado esperado:** validação rejeita cada valor inválido com `ConfigError`
  nomeando a chave; resolve defaults quando ausentes; aceita válidos.
- **Observações:** espelhar o estilo já existente (bool rejeitado antes de int,
  mensagem identifica a chave). Confirmar com o desenvolvimento a semântica de
  "tentativas" (ver CT-12).

---

## Grupo E — Higiene de documentação

### CT-15 — Nenhuma referência a identificador de modelo inválido na doc de exemplo

- **CA de origem:** "Dada a documentação de exemplo do produto, quando ela é
  revisada, então nenhuma referência a identificador de modelo inválido ou
  inexistente permanece."
- **Tipo:** manual/revisão + unitário de guarda (opcional)
- **Arquivo/alvo:** revisão de `README.md` (hoje `model: claude-sonnet-4-20250514`
  na seção de exemplo do `pipe.yml`, linha ~50); opcionalmente um teste de
  guarda em `tests/` que varre a doc de exemplo por identificadores inválidos.
- **Pré-condição:** lista dos identificadores de modelo **válidos** vigentes
  (definida pelo desenvolvimento/produto; o histórico do planejamento cita
  `claude-sonnet-5` / `auto` / `claude-haiku-4.5` como vigentes).
- **Passos:**
  1. Levantar todas as referências a `model:` / identificadores de modelo na
     documentação de exemplo do produto (ex.: `README.md`).
  2. Comparar com a lista de identificadores válidos.
  3. Corrigir as inválidas (desenvolvimento) e revalidar.
- **Resultado esperado:** nenhuma referência a identificador de modelo inválido/
  inexistente permanece na doc de exemplo. Se houver teste de guarda, ele falha
  enquanto houver identificador inválido e passa após a correção.
- **Observações:** QA valida a ausência; a correção textual é do desenvolvimento.
  Recomendo um teste de guarda simples (grep estruturado) para evitar
  reintrodução. **Fora de escopo:** não alterar o mecanismo de resolução de
  model, apenas a doc de exemplo.

---

## Notas de execução para o desenvolvimento

- **Isolamento:** usar `monkeypatch`/`tmp_path` e **nunca** fazer `monkeypatch`
  do próprio método sob teste (lição do incidente #106 — mascarava ausência de
  cobertura).
- **Sem espera real:** mockar `time.sleep` nos casos de backoff (CT-10, CT-12),
  asserindo os argumentos de backoff.
- **Sem rede/subprocesso real:** `_run`, `subprocess.run`, listagem de sessões e
  chamadas de board devem ser fakes/mocks; os testes rodam offline.
- **Baseline:** no momento da escrita destes casos, o retry (`retry.*`), a
  resolução de caminhos de apoio e a validação `retry` **não existem** no
  repositório — os testes correspondentes devem falhar antes da implementação e
  passar depois (mesmo padrão test-first de `test_error_classification.py` e
  `test_sanitize_relations.py`).
- **ADR:** antes de implementar o Grupo D, confirmar a reconciliação com a ADR
  `retry-kiro-cli/idempotencia.md` (ver aviso no topo). A idempotência não é
  opcional: é a condição que torna o retry compatível com a arquitetura aceita.
