# Casos de Teste — Verificação do bloco 4 (limite de consumo de IA e vitrine de exemplos)

- **Issue:** #317
- **Story relacionada:** #317 — "Verificação do bloco 4 — limite de consumo de
  IA e vitrine de exemplos" (auditoria integrada das entregas #311 e #312)
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA) SR
- **Data:** 2026-11-11
- **Branch:** `feature/317-verificacao_do_bloco_4_limite_de_consumo_de_ia_e_vitrine_de_exemplos`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da
> issue #317. Cada caso tem resultado esperado explícito e verificável. Os
> testes são da suíte Python do motor (pytest, em `tests/`), salvo os
> marcados como **manual/revisão** (auditoria documental/estrutural).

---

## Natureza desta entrega (ler antes de implementar os casos)

Esta **não** é uma entrega de funcionalidade: é uma **verificação de bloco**.
O produto é um **relatório de verificação** com um **veredito por critério de
aceitação** (atendido / não atendido / não verificável) de cada uma das duas
entregas auditadas, apoiado em **comportamento observado ou teste
executado** — nunca em releitura de texto.

As duas entregas já estão na linha principal (`origin/main` @ `e7ba768`):

- **#311** — Limitador opcional de consumo de IA por plataforma. Núcleo
  `src/core/consumption_limit.py` (validação, política resolvida, acumulador
  por instância/período, reset por calendário/fuso, persistência em
  `.pipe/consumptionLimit.json`), integrado ao caminho real em
  `src/__main__.py::_consumption_allows` (chamado antes do despacho do agente,
  nos dois pontos de chamada — linhas 580 e 749 do arquivo atual) e
  `_record_consumption` (acumula após a execução). Chave de configuração
  `agents.<plataforma>.limits`, validada em
  `src/core/config.py::_validate_agents`/`check_config` (exceção explícita
  para não tratar a chave `limits` como agente — CT-A3 do `test-cases.md` de
  origem). Estado listado em `PROTECTED_PATHS` (`src/core/agent.py`).
  Registrada no `CHANGELOG.md` seção **1.28.0**.
- **#312** — Primeira vitrine de exemplos executáveis da Esteira com
  validação interna e governança. Dois pacotes de exemplo
  (`exemplos/minimalista/`, `exemplos/referencia-hipotetica/`), documentação
  de processo e governança (`doc/exemplos/`), link no `README.md` e suíte
  própria (`tests/test_vitrine_*.py`). **Não há entrada no `CHANGELOG.md`
  nem incremento de `VERSION` para #312** — ponto que esta verificação
  precisa confirmar como correto ou como divergência (ver CT-03/CT-05).

Consequências para a implementação dos casos:

1. **Desfecho "sem divergência" é válido.** Se a verificação confirmar as
   duas entregas efetivas, a suíte verde (descontado o baseline alheio) e a
   ausência de bump de #312 como coerente (não como omissão), o único
   artefato é o **relatório**: **sem alteração de código-fonte e sem
   incremento de versão** (CA-3/CT-05 da issue).
2. **Diferente dos blocos 1–3, as duas entregas deste bloco NÃO compartilham
   um ponto de decisão do produto.** #311 modifica exclusivamente o caminho
   de despacho de agente (`src/__main__.py`, `src/core/consumption_limit.py`,
   `src/core/config.py`, `src/core/agent.py`). #312 **não altera nenhum
   arquivo em `src/`** (confirmado por `git show 0d2b2d6 --stat` — commit
   `feat(312)`: só `exemplos/`, `doc/exemplos/`, `tests/test_vitrine_*.py`,
   `.gitignore`; e `f16af24` — só `README.md`). Os dois pacotes de exemplo
   (`exemplos/minimalista/pipe.yml`, `exemplos/referencia-hipotetica/pipe.yml`)
   também **não configuram** `agents.<plataforma>.limits`. Logo a
   pré-condição de CA-6 ("duas entregas que atuam no mesmo ponto de decisão")
   **não se verifica neste bloco** — CT-04 existe para **confirmar essa
   ausência com evidência**, não para criar um teste de convergência (ao
   contrário do bloco 3, onde a convergência existia e exigia teste novo).
3. A suíte já cobre cada entrega isoladamente de forma completa (12/12 CA de
   #311 "Aprovado" em `doc/quality/limitador-opcional-consumo-ia-plataforma/
   test-results.md`; 12/12 CA de #312 "Atendido"/"✅" em
   `doc/quality/primeira-vitrine-exemplos-executaveis/test-results.md`, com
   CT-29 explicitamente `skip` por design até a issue alcançar "Em
   produção"). Os casos abaixo (CT-01..CT-05) são portanto majoritariamente
   **execução e auditoria** dos artefatos já presentes; só geram alteração de
   código se uma **divergência** for encontrada (CT-03), situação em que a
   correção exige teste de regressão + bump de versão + entrada no
   CHANGELOG (CA-4/CA-5 da issue).

---

## Avaliação da suíte existente (base da especificação)

Levantamento feito nesta etapa, sobre a linha principal
(`feature/317-...` criada de `origin/main` @ `e7ba768`), com a suíte completa
executada (`python -m pytest -q`): **2086 passed, 26 failed, 18 skipped,
1 xpassed** (58,69s; 7 subtests passed contados aparte).

| Entrega | Cobertura existente (arquivos) | Veredito preliminar de cobertura |
|---------|--------------------------------|-----------------------------------|
| #311 — limitador de consumo de IA por plataforma | `tests/test_consumption_limit.py`, `tests/test_consumption_limit_config.py`, `tests/test_consumption_limit_integration.py`, `tests/test_consumption_limit_reset.py` (Grupos A–F, CT-A1..CT-F1) | Coberto (validação de config, decisão/acúmulo/isolamento por instância e plataforma/retomada sem reinício/falha aberta, reset diário/semanal/mensal com fuso, observabilidade do bloqueio, integração no gate pré-agente, baseline) |
| #312 — vitrine de exemplos executáveis | `tests/test_vitrine_estrutura.py`, `tests/test_vitrine_config.py`, `tests/test_vitrine_registros.py`, `tests/test_vitrine_governanca.py` (CT-01..CT-29 do `test-cases.md` de origem) | Coberto (estrutura dos 2 pacotes, validação real do motor via `config.check_config`, encadeamento até estado final, ausência de dado sensível, registros de validação/apresentação/impacto/reavaliação). CT-29 (registro de reavaliação pós-"Em produção") é `skip` **por design**, não lacuna. |
| **Convergência #311 × #312 em algum ponto de decisão do produto** | — | **NÃO APLICÁVEL** — ver "Natureza desta entrega" item 2 e CT-04. #312 não toca `src/`; nenhum dos dois pacotes de exemplo configura `limits`. Não há ponto de decisão compartilhado a comprovar nesta verificação. |
| **Coerência versão/CHANGELOG × entregue** | `src/core/version.py` (`VERSION = "1.29.0"`, bump mais recente é de #345, issue fora deste bloco), `CHANGELOG.md` (seção `1.28.0` cita #311; nenhuma seção cita #312) | **A confirmar em CT-03/CT-05** — #311 tem bump+CHANGELOG coerente com a mudança em `src/`; #312 não tem bump nem CHANGELOG, e também não mudou `src/` nem `README.md`'s link de produto pré-existente, então a ausência é candidata a "correta" (regra já estabelecida nas verificações de blocos 1–3: bump só quando `src/` muda), mas precisa ser confirmada como tal, não presumida. |

**Observação da etapa de planejamento (Isabela Gomes, histórico da issue):**
o candidato a divergência levantado — "#312 saiu sem bump/CHANGELOG" — é
exatamente o que CT-03 e CT-05 abaixo são desenhados para confirmar ou
refutar com evidência, não presumir em qualquer direção.

---

## Rastreabilidade (CA → casos)

| # | Critério de aceitação (resumo) | Caso(s) |
|---|--------------------------------|---------|
| CA-1 | Existe relatório que lista **cada critério de #311/#312 e seu veredito** | CT-01 (insumo), CT-02, CT-05 (relatório final consolida CA-1..CA-7) |
| CA-2 | Suíte completa executada; **falha é corrigida ou registrada** com justificativa antes de encerrar | CT-01 |
| CA-3 | **Sem divergência** ⇒ relatório "sem divergência", **sem alteração de código nem bump de versão** | CT-03, CT-05 |
| CA-4 | Divergência **corrigível no escopo** ⇒ teste de regressão + **incremento de versão** + entrada no CHANGELOG | CT-03 |
| CA-5 | Divergência que **exige escopo novo** ⇒ registrada como **demanda separada**, não implementada aqui | CT-03 |
| CA-6 | Duas entregas do bloco no **mesmo ponto de decisão do produto** permanecem efetivas em conjunto, sem uma sombrear a outra | **CT-04** (determinação: pré-condição não se verifica neste bloco) |
| CA-7 | Critério **não verificável** com os meios disponíveis ⇒ veredito "não verificável" com a razão | CT-02 (quando a lacuna/dependência de ambiente impedir verificar), tratamento transversal no relatório |

> Mapeamento dos cenários obrigatórios da issue → casos: CT-01 (suíte
> completa), CT-02 (critério sem cobertura ⇒ lacuna registrada), CT-03
> (comportamento declarado ausente ⇒ "não atendido" + correção/demanda),
> CT-04 (duas entregas no mesmo ponto de decisão), CT-05 (verificação sem
> divergência). Numeração 1:1 com a tabela de "Cenários de teste
> obrigatórios" do corpo da issue #317.

---

## Convenções para o desenvolvimento (quando algum caso exigir código)

- **Nenhum caso desta especificação exige código novo**, salvo se CT-03
  revelar uma divergência corrigível no escopo do bloco (nesse caso, a
  correção segue as convenções já fixadas nos `test-cases.md` de origem de
  #311/#312: relógio e fuso controláveis, `monkeypatch.chdir(tmp_path)`
  autouse, dublês só nas fronteiras externas, nunca `monkeypatch` do símbolo
  sob teste).
- **Evidência:** toda afirmação de "atendido" se apoia em um teste executado
  (nome do teste + resultado) ou em inspeção direta e citável do código/
  artefato (caminho + linha, ou trecho). Nenhum veredito por releitura de
  texto da issue original.
- **Diff como evidência de escopo:** `git diff --stat`/`git diff --name-only
  -- src/` contra `origin/main` (ou contra o commit anterior à entrega
  auditada) é o instrumento usado em CT-03/CT-04/CT-05 para confirmar o que
  cada entrega efetivamente tocou — não presumir pelo texto da issue.

---

## CT-01 — Suíte completa na linha principal

- **CA de origem:** CA-2 — "Dado que a suíte completa é executada, quando há
  falha, então a falha é corrigida ou registrada com justificativa explícita
  antes do encerramento desta issue." (cenário obrigatório CT-01)
- **Tipo:** execução de suíte (verificação) — não é um novo teste de código.
- **Arquivo/alvo:** suíte inteira em `tests/` via `python -m pytest -q` na
  raiz do repositório, na branch da verificação (base `origin/main` @
  `e7ba768`).
- **Pré-condição:** bloco concluído; branch
  `feature/317-verificacao_do_bloco_4_limite_de_consumo_de_ia_e_vitrine_de_exemplos`
  sincronizada com `origin/main`; dependências de teste instaladas (`pytest`,
  `pyyaml`); execução **offline** (sem rede/subprocesso real — os testes já
  mockam board/subprocess/kiro-cli).
- **Passos:**
  1. Executar `python -m pytest -q` a partir de `/app/repo/main`.
  2. Capturar o sumário (total de testes, passados, falhados, pulados) e os
     identificadores de qualquer falha.
  3. Para cada falha: fazer análise de causa-raiz e **classificar** (falha
     de código → divergência CT-03; caso de teste inadequado →
     `revisar-caso-de-teste` na etapa de execução). Nesta etapa de
     **especificação**, apenas registrar o procedimento; a execução
     definitiva ocorre na etapa `execucao-testes`.
- **Resultado esperado:** a suíte completa **passa** (0 falhas atribuíveis
  ao bloco 4). O resultado é **registrado** no relatório (contagem +
  evidência do sumário). Se houver falha, ela é corrigida (quando couber no
  escopo) **ou** registrada com justificativa explícita **antes** do
  encerramento — nunca silenciada.
- **Observações:** levantamento preliminar nesta etapa mostra **2086 passed,
  26 failed, 18 skipped, 1 xpassed** (58,69s; 7 subtests passed). As 26
  falhas, confirmadas por nome de arquivo/teste, são o **mesmo baseline
  pré-existente** já registrado em
  `doc/quality/verificacao-bloco-1/test-results.md`,
  `doc/quality/verificacao-bloco-2/test-results.md`,
  `doc/quality/verificacao-bloco-3/test-results.md` e no `test-results.md` de
  #311 (formato de log diário descritivo —
  `tests/test_agent_log_descritivo.py` (18) + `tests/test_agent_failure_detection.py`
  (1) — e infraestrutura Docker — `tests/test_dockerfile.py` (3) +
  `tests/test_docker_compose.py` (4); 18+1+3+4 = 26), alheias a #311/#312.
  Execução dirigida dos 8 arquivos pertinentes a #311 e #312 nesta etapa:
  **200 passed, 1 skipped** (`test_vitrine_governanca.py::test_registro_real_de_reavaliacao_apos_producao`
  — CT-29, skip por design até "Em produção"). A confirmação definitiva de
  que o baseline da suíte completa é **exatamente** o mesmo (zero regressão
  nova introduzida pelo bloco) é tarefa da etapa `execucao-testes`, pela
  mesma técnica das verificações de bloco anteriores (comparação do
  conjunto de nomes de teste falhos).

## CT-02 — Critério declarado sem cobertura de teste correspondente ⇒ lacuna registrada

- **CA de origem:** CA-1 (veredito por critério com evidência) e CA-7
  (veredito "não verificável" com razão). Cenário obrigatório CT-02.
- **Tipo:** auditoria de cobertura (verificação).
- **Arquivo/alvo:** mapeamento CA (de #311 e #312) → teste existente em
  `tests/`. Fontes:
  `doc/quality/limitador-opcional-consumo-ia-plataforma/test-cases.md` +
  `test-results.md` (#311, CA-1..CA-12) e
  `doc/quality/primeira-vitrine-exemplos-executaveis/test-cases.md` +
  `test-results.md` (#312, CA-1..CA-12), confrontados com os arquivos reais
  em `tests/` e com os respectivos `test-results.md` (vereditos já publicados
  nas etapas de execução de testes de cada entrega).
- **Pré-condição:** lista dos critérios de aceitação de #311 e #312 e dos
  testes que os cobrem (ver tabela "Avaliação da suíte existente").
- **Passos:**
  1. Para cada CA atendido de #311/#312, localizar o(s) teste(s) que o
     cobre(m), usando o mapa de rastreabilidade já publicado nos respectivos
     `test-cases.md`/`test-results.md` de origem.
  2. Marcar cada CA como: **coberto** (teste identificado e verde), **lacuna
     de cobertura** (CA atendido no código mas sem teste que o exercite),
     **coberto com verificação diferida por design** (caso do CT-29 de #312,
     que depende de a issue alcançar a coluna "Em produção" — não é lacuna,
     é condição declarada na própria especificação de origem) ou **não
     verificável** (sem meio disponível para verificar — registrar a razão).
  3. Confirmar explicitamente, nesta etapa, que a ausência de CT-04 "novo"
     (ver item 2 de "Natureza desta entrega") não é uma lacuna de cobertura:
     é a confirmação, com evidência de diff, de que a pré-condição de CA-6
     não se verifica neste bloco.
- **Resultado esperado:** o relatório contém, por critério, o veredito e a
  evidência (nome do teste / observação). O caso CT-29 de #312 é identificado
  e tratado como **diferido por design**, não como lacuna nem como "não
  verificável". Nenhum critério recebe "atendido" por suposição.
- **Observações:** confirmação definitiva de todos os vereditos ocorre na
  etapa `execucao-testes`, pela execução dirigida dos 8 arquivos (resultado
  preliminar nesta etapa: **200 passed, 1 skipped**, ver CT-01).

## CT-03 — Comportamento declarado ausente na linha principal ⇒ veredito "não atendido"

- **CA de origem:** CA-4 (divergência corrigível ⇒ teste de regressão +
  versão + CHANGELOG) e CA-5 (divergência que exige escopo novo ⇒ demanda
  separada). Cenário obrigatório CT-03.
- **Tipo:** verificação de comportamento + (condicional) teste de
  regressão.
- **Arquivo/alvo:** comportamento das duas entregas na linha principal:
  - #311: `src/core/consumption_limit.py` (`validate_consumption_limits`,
    `resolve_policy`/`read_policy_from_disk`, `ConsumptionLimiter.admit`/
    `record`, `period_bounds`, `load_state`/`save_state`),
    `src/__main__.py::_consumption_allows`/`_record_consumption`/
    `_resolve_platform` (gate antes do despacho, nos dois pontos de chamada),
    `src/core/config.py::_validate_agents`/`check_config` (exceção para a
    chave `limits`), `src/core/agent.py::PROTECTED_PATHS`
    (`.pipe/consumptionLimit.json`).
  - #312: os dois pacotes em `exemplos/` (estrutura, `exemplo.yml` com os 8
    campos, `USO.md`/`CUSTOMIZACAO.md`), `doc/exemplos/` (processo de
    validação/apresentação/manutenção por impacto/reavaliação de temas),
    `.gitignore` (exceções para `exemplos/**/pipe.yml`/`contexts/`),
    `README.md` (seção "Exemplos" com os links).
- **Pré-condição:** para cada CA declarado atendido, há um comportamento
  observável correspondente (teste executável ou inspeção estrutural).
- **Passos:**
  1. Para cada CA, confrontar o declarado com o comportamento presente
     (executando o teste correspondente ou inspecionando o código/estrutura).
  2. Se o comportamento declarado **não** estiver presente (teste
     ausente/vermelho que deveria passar, ou código/artefato que contradiz o
     CA), emitir veredito **"não atendido"** com a evidência.
  3. Verificar especificamente a coerência versão/CHANGELOG × entregue (o
     candidato a divergência apontado no planejamento):
     - `git diff --stat <commit-anterior-a-#311>..5116770 -- src/` — deve
       mostrar mudança em `src/` coerente com o bump `1.27.5 → 1.28.0` e com
       o texto da seção `1.28.0` do `CHANGELOG.md`.
     - `git diff --stat a1e3718..e7ba768 -- src/` (intervalo do merge de
       #312) — deve mostrar **nenhuma** mudança em `src/`. Se confirmado
       vazio, a ausência de bump/CHANGELOG para #312 é **coerente** com a
       regra já estabelecida nas verificações de blocos 1–3 ("o bump só é
       disparado quando o código-fonte do produto muda" —
       `doc/quality/verificacao-bloco-3/test-results.md`, seção 8) — **não**
       é uma divergência, e registrar um bump/entrada aqui seria inventar
       mudança para justificar a entrega (vedado pelos "Riscos e pontos de
       atenção" do corpo da issue #317). Se o diff mostrar qualquer mudança
       em `src/` atribuída a #312, a ausência de bump passa a ser
       **divergência** (CA-4/CA-5, conforme couber ou não no escopo).
  4. Classificar toda divergência encontrada:
     - **corrigível no escopo do bloco** → aplicar a correção **com teste
       de regressão** que reproduz a divergência, **incrementar a versão**
       (`src/core/version.py`) e adicionar **entrada no `CHANGELOG.md`**
       (CA-4);
     - **exige escopo novo** → **não** implementar aqui; registrar como
       **demanda separada** no relatório (CA-5).
- **Resultado esperado:** nenhuma divergência silenciosa. Toda ausência vira
  veredito "não atendido" com evidência e um destino explícito (correção com
  regressão + bump + CHANGELOG, **ou** demanda separada). Se **nenhuma**
  divergência for encontrada — incluindo a confirmação de que a ausência de
  bump/CHANGELOG de #312 é coerente (diff de `src/` vazio) —, este caso
  resulta em "não aplicável" e o desfecho é o CT-05.
- **Observações:** o incremento de versão e a entrada no CHANGELOG **só**
  ocorrem no ramo "divergência corrigível" (CA-4). É proibido inventar
  mudança para justificar bump (ver CT-05). A leitura feita nesta etapa (ver
  "Avaliação da suíte existente" e "Natureza desta entrega", item 2) já
  confirma, por `git show --stat` dos commits `5116770` e `0d2b2d6`/`f16af24`,
  que #311 toca `src/` de forma coerente com seu bump e que #312 não toca
  `src/` em nenhum dos seus três commits (`2ffc898`, `0d2b2d6`, `20a4a7f`,
  `f16af24`); a confirmação definitiva (reexecução do `git diff` e checagem
  cruzada com o `CHANGELOG.md`/`VERSION` vigentes) ocorre na etapa
  `execucao-testes`.

## CT-04 — Duas entregas no mesmo ponto de decisão do produto: determinação e evidência

- **CA de origem:** CA-6 — "Dado duas entregas do bloco que atuam no mesmo
  ponto de decisão do produto, quando a verificação ocorre, então há
  evidência registrada de que ambas permanecem efetivas em conjunto, sem que
  uma anule a outra." Cenário obrigatório CT-04.
- **Tipo:** auditoria estrutural (verificação) — determinação da
  pré-condição, não teste de integração novo.
- **Arquivo/alvo:** superfície de código tocada por cada entrega
  (`git diff --name-only -- src/` para os intervalos de merge de #311 e de
  #312) e configuração dos dois pacotes de exemplo de #312
  (`exemplos/minimalista/pipe.yml`, `exemplos/referencia-hipotetica/pipe.yml`).
- **Pré-condição:** nenhuma — este caso **verifica a própria pré-condição**
  do CA-6 antes de decidir se um teste de convergência é necessário.
- **Passos:**
  1. Listar os arquivos de `src/` tocados pelo commit `feat` de #311
     (`5116770`) e confirmar que o único ponto de inserção no caminho de
     despacho de agente é `_consumption_allows`/`_record_consumption` em
     `src/__main__.py`.
  2. Listar os arquivos de `src/` tocados pelos commits de #312 (`2ffc898`,
     `0d2b2d6`, `20a4a7f`, `f16af24`) via `git diff --name-only -- src/`
     contra o commit anterior ao merge de #312.
  3. Verificar se `exemplos/minimalista/pipe.yml` ou
     `exemplos/referencia-hipotetica/pipe.yml` declaram a chave
     `agents.<plataforma>.limits` (grep no YAML de cada pacote).
  4. Com base nos passos 1–3, determinar se existe algum ponto de decisão do
     produto (trecho de código em `src/` executado em runtime) que ambas as
     entregas alcancem.
- **Resultado esperado:** o passo 2 retorna **lista vazia** (#312 não toca
  `src/`) e o passo 3 não encontra a chave `limits` em nenhum dos dois
  pacotes. Logo a pré-condição de CA-6 **não se verifica** neste bloco: não
  há ponto de decisão do produto compartilhado por #311 e #312. O relatório
  registra essa determinação, com a evidência dos três diffs/greps, como o
  desfecho de CA-6 para este bloco — **atendido vacuamente** (o ramo "duas
  entregas no mesmo ponto de decisão" não é acionado, mesmo padrão já usado
  para CA-4 em `doc/quality/verificacao-bloco-1/test-results.md` quando o
  ramo correspondente não se aplica). **Nenhum teste de código novo é
  necessário** para este caso — ao contrário do bloco 3 (onde a convergência
  existia de fato e exigiu `tests/test_convergencia_bloco3_sync.py`).
- **Observações:** se a execução desta etapa encontrar, ao contrário do
  levantamento preliminar, qualquer referência de #312 a `src/` ou qualquer
  pacote de exemplo configurando `limits`, este caso **deixa de ser
  vacuamente atendido**: nesse cenário, a verificação precisa então
  especificar e implementar um teste de convergência real (nos mesmos moldes
  de `tests/test_convergencia_bloco3_sync.py`), e este documento deve ser
  atualizado antes de a etapa `execucao-testes` prosseguir — o que
  configuraria lacuna de escopo desta especificação, não uma decisão da
  execução.

## CT-05 — Verificação sem divergência (relatório, sem código, sem bump)

- **CA de origem:** CA-3 — "Dado que nenhuma divergência é encontrada,
  quando a verificação encerra, então o relatório registra o resultado 'sem
  divergência' e a entrega é válida sem alteração de código-fonte e,
  portanto, sem incremento de versão." Cenário obrigatório CT-05.
- **Tipo:** manual/revisão (fecho da verificação) + guarda objetiva.
- **Arquivo/alvo:** o **relatório de verificação** (entregável da etapa de
  execução de testes, em `doc/quality/verificacao-bloco-4/`); coerência de
  versão e CHANGELOG: `src/core/version.py` (`VERSION`, hoje `1.29.0` — bump
  mais recente é de #345, fora deste bloco) e `CHANGELOG.md`.
- **Pré-condição:** CT-01 verde (suíte completa passa, descontadas as
  falhas de baseline alheias ao bloco), CT-02 sem lacuna não tratada, CT-03
  sem divergência de comportamento (incluindo a ausência de bump de #312
  confirmada como coerente), CT-04 com a determinação registrada (CA-6
  vacuamente atendido).
- **Passos:**
  1. Confirmar que todos os vereditos são "atendido" (inclusive vacuamente,
     onde aplicável) ou "não verificável" com razão, sem nenhum "não
     atendido" pendente.
  2. Confirmar coerência versão↔CHANGELOG↔entregue: `CHANGELOG.md` reflete
     #311 (seção `1.28.0`) e **não** reflete #312 — e essa ausência foi
     confirmada em CT-03 como coerente (sem mudança em `src/`), não como
     omissão.
  3. Registrar no relatório o desfecho **"sem divergência"**.
  4. **Garantir que não há alteração de código-fonte de produto** atribuível
     a esta verificação: `git diff --stat origin/main...HEAD` **não** mostra
     mudanças em `src/` (apenas documentação em `doc/quality/…`).
- **Resultado esperado:** o relatório registra "sem divergência";
  **`VERSION` inalterada** (`1.29.0`) e **nenhuma entrada nova** no
  `CHANGELOG.md`; o `diff` contra `origin/main` restringe-se a
  `doc/quality/verificacao-bloco-4/` (estes casos + o relatório da etapa
  seguinte). Nenhuma mudança em `src/` nem em `tests/` (ao contrário do
  bloco 3, aqui não há teste de convergência a adicionar, pois a
  pré-condição de CA-6 não se verifica — CT-04).
- **Observações:** o bump/CHANGELOG ficam **estritamente** condicionados ao
  ramo "divergência corrigível" de CT-03/CA-4. Inventar mudança para
  justificar a entrega é **proibido** pelo escopo (seção "Fora de escopo" e
  "Riscos e pontos de atenção" do corpo da issue #317).

---

## Cobertura e lacunas declaradas

- Os 7 CAs da issue #317 (CA-1..CA-7) possuem ≥ 1 caso. Nenhum CA sem caso.
- Os 5 cenários obrigatórios do corpo da issue (CT-01..CT-05) mapeiam 1:1
  para os 5 casos deste documento.
- Não há lacuna de escopo que exija devolver à etapa de planejamento: a
  issue #317 está internamente consistente (descrição, escopo, critérios de
  aceitação e cenários obrigatórios se correspondem), e as duas entregas
  auditadas (#311, #312) já estão na linha principal com `test-cases.md` e
  `test-results.md` próprios publicados — insumo suficiente para derivar
  estes casos sem ambiguidade.
- Decisão de especificação registrada nesta etapa (não é lacuna, é
  determinação com evidência, sujeita a confirmação na execução): a
  pré-condição de CA-6 (duas entregas no mesmo ponto de decisão) não se
  verifica neste bloco — ver CT-04. Se a execução encontrar o contrário, o
  caso aponta explicitamente para a necessidade de atualizar esta
  especificação antes de prosseguir.

---

## Notas de execução para a etapa `execucao-testes`

- **Suíte completa:** `python -m pytest -q` a partir de `/app/repo/main`;
  registrar sumário e qualquer falha com causa-raiz (CT-01). Comparar o
  **conjunto de nomes** de testes falhos com o baseline já documentado nas
  verificações de blocos 1–3 e no `test-results.md` de #311, confirmando que
  são os mesmos 4 arquivos / 26 testes (zero regressão nova).
- **Execução dirigida (#311 + #312):**
  `python -m pytest -q tests/test_consumption_limit.py
  tests/test_consumption_limit_config.py
  tests/test_consumption_limit_integration.py
  tests/test_consumption_limit_reset.py tests/test_vitrine_config.py
  tests/test_vitrine_estrutura.py tests/test_vitrine_governanca.py
  tests/test_vitrine_registros.py` — preliminar nesta etapa: **200 passed,
  1 skipped** (CT-29, skip por design).
- **CT-03/CT-04 (diff como evidência):**
  - `git log --oneline origin/main` para localizar os commits de merge de
    #311 (`1996db0`) e #312 (`e7ba768`) e os commits `feat`/`docs`
    individuais (`5116770`; `2ffc898`, `0d2b2d6`, `20a4a7f`, `f16af24`).
  - `git show 5116770 --stat` (confirma `src/` tocado por #311, coerente com
    o bump `1.28.0`).
  - `git show 0d2b2d6 --stat` e `git show f16af24 --stat` (confirma **zero**
    arquivos em `src/` tocados por #312).
  - `grep -n "limits" exemplos/minimalista/pipe.yml
    exemplos/referencia-hipotetica/pipe.yml` (confirma que nenhum pacote
    configura o limitador).
- **CT-05 (guarda de versão):** `cat src/core/version.py`; `head -40
  CHANGELOG.md`; `git diff --stat origin/main...HEAD`; `git status
  --porcelain`.
