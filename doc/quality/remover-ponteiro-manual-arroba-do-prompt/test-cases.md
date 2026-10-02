# Casos de Teste — Remover do prompt o ponteiro do manual `@---` (manter apenas no steering)

- **Issue:** #325
- **Story relacionada:** composição em camadas do prompt e do contexto (#308) —
  esta entrega retira a referência sob demanda (ponteiro) que #308 havia
  reintroduzido no prompt dinâmico.
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-02
- **Branch:** `feature/325-remover-do-prompt-o-ponteiro-do-manual-manter-apenas-no-steering`

> Todo caso de teste é vinculado a um critério de aceitação (CA) da issue #325.
> Nenhum caso existe sem CA de origem. Cada caso tem resultado esperado
> explícito e verificável. A suíte é Python/pytest em `tests/`.

## Contexto de arquitetura (baseline do código atual — v1.20.1)

Pontos de ancoragem confirmados na leitura do código:

- `src/core/agent.py::build_prompt` (linhas ~381-394): bloco que injeta a seção
  `## Anotações no body (comandos \`@---\`)` sob o gate
  `composition.REF_MANUAL_ARROBA in composition.on_demand_references(col)`.
  É o bloco a **remover por completo** (CA-1).
- `src/core/composition.py`: constante `REF_MANUAL_ARROBA`, conjunto
  `_ANNOTATION_COMMANDS`, função `allowed_commands(col)` (lê a chave de coluna
  `allowed-commands`) e função `on_demand_references(col)` (gate que inclui o
  manual no prompt). O escopo permite remover ou esvaziar — os casos abaixo
  testam o **comportamento observável** (a referência nunca é incluída), não a
  forma de implementação; se as funções forem mantidas, `on_demand_references`
  deve retornar sempre `[]` e `REF_MANUAL_ARROBA` deixa de ser usada por
  `build_prompt`.
- `src/core/config.py` (linhas ~169-179): validação da chave `allowed-commands`
  por coluna, hoje aceitando lista de strings. A remoção retira essa validação
  do schema — a chave deixa de ser reconhecida (CA-3).
- `src/__main__.py::compose_execution_record` (linha ~862): usa
  `composition.on_demand_references(col)` para preencher
  `referencias_sob_demanda_incluidas` no registro de `composicao_medicao`
  (CA-4).
- Testes existentes que **exercitam diretamente** a feature a remover e que
  ficam **invertidos/substituídos** por esta entrega:
  - `tests/test_composicao_camadas_sob_demanda.py` — toda a suíte (CT-15/16/17
    da entrega #308) afirma que o manual aparece sob demanda; passa a afirmar o
    contrário (ausência incondicional).
  - `tests/test_build_prompt_protected_paths.py::TestBuildPromptRegressao::test_prompt_contem_secao_anotacoes_body`
    — afirma que a seção **existe** no prompt; precisa ser removido/invertido.
  - `tests/test_composicao_camadas_matriz.py` — usa
    `referencias_sob_demanda_incluidas` como campo presente (tipo lista); o
    contrato de tipo não muda (continua lista), mas o **conteúdo** passa a ser
    sempre vazio; os testes de tipo continuam válidos sem alteração.
- Testes de medição por comparação a baseline congelado
  (`tests/_composicao_helpers.py::BASELINE`,
  `tests/test_composicao_camadas_medicao.py::TestReducaoEstatico` /
  `TestReducaoTotal` / `TestReducaoNaoEhTransferencia`) comparam o prompt
  **entregue** contra uma constante da versão **pré-#308**. Removendo a seção
  do manual, o prompt entregue fica ainda menor — essas asserções (`<=`)
  permanecem válidas sem qualquer ajuste de baseline.

## Escopo coberto pelos casos

- `src/core/agent.py` (`build_prompt`): ausência incondicional de qualquer
  menção ao manual `@---`.
- `src/core/composition.py`: `on_demand_references` nunca inclui o manual (se
  mantida); gate removido do prompt dinâmico.
- `src/core/config.py`: `allowed-commands` não é mais reconhecida pela
  validação.
- `src/__main__.py` / `compose_execution_record`: `referencias_sob_demanda_incluidas`
  sempre vazia (ou campo ausente).
- Permanência do manual completo no steering (sem alteração).
- Documentação pública (README, contrato de arquitetura, CHANGELOG) e bump de
  versão — fora do escopo de teste automatizado desta QA (verificação textual
  manual na etapa de Documentação); citados aqui apenas para rastreabilidade.

## Fora de escopo dos casos (alinhado à issue)

- Parsing/aplicação dos comandos `@---` pelo motor (continuam inalterados).
- Qualquer alteração do manual no steering (deve permanecer bit-a-bit
  equivalente, exceto pela ausência de uso de `allowed-commands`).
- Demais camadas da composição (política invariável, workflow da etapa, dados
  da tarefa) além do ponto específico do ponteiro.

---

## Rastreabilidade (CA → casos)

| Critério de aceitação | Caso(s) de teste |
|------------------------|-------------------|
| CA-1 — prompt dinâmico nunca contém a seção/ponteiro do manual `@---`, em qualquer coluna com agente | CT-01, CT-02, CT-03 |
| CA-2 — steering continua com o manual completo, inalterado (origem única) | CT-04 |
| CA-3 — `allowed-commands` não é reconhecida pelo schema validado e não afeta o prompt | CT-05, CT-06 |
| CA-4 — `composicao_medicao` nunca reporta referência ao manual `@---` incluída | CT-07, CT-08 |
| CA-5 — suíte cobre tanto a ausência no prompt quanto a permanência no steering | CT-01–CT-04 (conjunto) |

---

## Casos de teste

### CT-01 — Prompt dinâmico nunca contém a seção do manual `@---`, com `allowed-commands` presente `[estende]`

- **CA de origem:** CA-1
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_sob_demanda.py::TestManualArrobaRemovido::test_etapa_com_allowed_commands_nao_carrega`
- **Pré-condição:** Coluna com `allowed-commands` declarando comandos de
  anotação que, na versão anterior (#308), abririam o gate (ex.:
  `["labels", "blocked_by", "need_human"]`).
- **Passos:**
  1. Compor o prompt dinâmico (`build_prompt`) para essa coluna.
  2. Verificar a ausência do cabeçalho `## Anotações no body (comandos
     \`@---\`)` e de qualquer menção ao manual `@---` no prompt.
- **Resultado esperado:** O prompt **não** contém o cabeçalho da seção nem
  qualquer ponteiro/texto referenciando o manual `@---`, independentemente do
  valor de `allowed-commands`.
- **Observações:** Substitui `test_etapa_com_comando_carrega` (que afirmava o
  oposto). Prova que a presença da chave não reativa o ponteiro.

### CT-02 — Prompt dinâmico nunca contém a seção do manual `@---`, sem `allowed-commands` (default) `[estende]`

- **CA de origem:** CA-1
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_sob_demanda.py::TestManualArrobaRemovido::test_etapa_sem_allowed_commands_nao_carrega`
- **Pré-condição:** Coluna sem a chave `allowed-commands` (comportamento
  default, que na versão anterior assumia o conjunto completo de comandos e
  incluía o manual).
- **Passos:**
  1. Compor o prompt dinâmico para essa coluna.
  2. Verificar a ausência do cabeçalho da seção e de qualquer ponteiro ao
     manual.
- **Resultado esperado:** O prompt não contém a seção, mesmo no caso default
  (ausência da chave) que antes garantia a inclusão.
- **Observações:** Substitui `test_etapa_default_carrega_sob_demanda`. Cobre a
  variação de configuração "ausência de allowed-commands" exigida por CA-1
  ("qualquer coluna com agente").

### CT-03 — Prompt dinâmico nunca contém a seção do manual `@---`, com `allowed-commands: []` `[estende]`

- **CA de origem:** CA-1
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_sob_demanda.py::TestManualArrobaRemovido::test_etapa_allowed_commands_vazio_nao_carrega`
- **Pré-condição:** Coluna com `allowed-commands: []` (caso que já não incluía
  o manual antes da entrega).
- **Passos:**
  1. Compor o prompt dinâmico para essa coluna.
  2. Verificar a ausência do cabeçalho e de qualquer menção ao manual.
- **Resultado esperado:** O prompt não contém a seção (comportamento preservado
  neste sub-caso, agora por remoção incondicional em vez de gate).
- **Observações:** Fecha a cobertura das três variações de configuração de
  `allowed-commands` (presente-com-comando, ausente, presente-vazio) exigidas
  pela redação "qualquer coluna com agente" de CA-1.

### CT-04 — Steering mantém o manual `@---` completo e inalterado `[estende]`

- **CA de origem:** CA-2
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_context_generator.py` (estender) /
  `tests/test_composicao_camadas_sob_demanda.py::TestManualArrobaRemovido::test_steering_mantem_manual_completo`
- **Pré-condição:** `context_generator._build_content(config)` (ou função
  equivalente de geração do steering) para uma config canônica.
- **Passos:**
  1. Gerar o conteúdo do steering.
  2. Verificar a presença de todas as seções do manual `@---` hoje documentadas
     no steering (ex.: "Comandos", lista de comandos `/parent`, `/children`,
     `/blocked_by`, `/blocks`, `/labels`, `/agent-hub-<valor>`, `/need_human`,
     `/archive`, regras de bloqueio).
  3. Comparar o conteúdo gerado antes e depois da remoção do ponteiro no prompt
     dinâmico (mesma config): deve ser **idêntico** (a mudança não toca
     `context_generator`).
- **Resultado esperado:** O manual completo permanece no steering, bit-a-bit
  igual ao gerado antes desta entrega. Nenhuma seção do manual é removida do
  steering.
- **Observações:** Garante a premissa "fora de escopo: não alterar o manual no
  steering". Serve como prova de não-regressão da origem única (RN-04 de
  #308).

### CT-05 — `allowed-commands` deixa de ser reconhecida pelo schema validado `[novo]`

- **CA de origem:** CA-3
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_config.py` (estender) ou
  `tests/test_composicao_camadas_sob_demanda.py::TestAllowedCommandsRemovida::test_chave_nao_reconhecida`
- **Pré-condição:** `pipe.yml` válido cuja coluna declara
  `allowed-commands: ["labels"]` (valor que antes era aceito pela validação).
- **Passos:**
  1. Chamar a validação de configuração (`check_config`/`validate_columns` ou
     equivalente) com essa coluna.
- **Resultado esperado:** A validação **não** trata `allowed-commands` como
  chave especial — ou (a) é silenciosamente ignorada por não constar no
  schema de chaves conhecidas da coluna sem causar erro algum relacionado a
  ela, ou (b), se o schema da coluna for de chaves fechadas, rejeita como
  "chave desconhecida" (`ConfigError`). O comportamento exato (ignorar vs.
  rejeitar) depende da política geral de chaves desconhecidas do projeto — o
  caso verifica que **nenhuma validação específica de `allowed-commands`**
  (ex.: "deve ser uma lista de strings") permanece ativa. Em qualquer dos dois
  casos, a validação não levanta o erro específico de forma antigo
  (`"deve ser uma lista de strings (nomes de comando)"`).
- **Observações:** Alinhar com a política de chaves desconhecidas vigente no
  projeto (`src/core/config.py`); se o projeto aceitar chaves desconhecidas em
  colunas, o sub-caso (a) é o esperado.

### CT-06 — `allowed-commands` declarada não produz efeito no prompt `[novo]`

- **CA de origem:** CA-3
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_sob_demanda.py::TestAllowedCommandsRemovida::test_chave_sem_efeito_no_prompt`
- **Pré-condição:** Duas colunas idênticas exceto por `allowed-commands`: uma
  sem a chave, outra com `allowed-commands: ["blocked_by", "need_human"]`.
- **Passos:**
  1. Compor o prompt dinâmico para as duas colunas.
  2. Comparar os dois prompts.
- **Resultado esperado:** Os dois prompts são idênticos em tudo que depende de
  `allowed-commands` — em particular, nenhum deles contém a seção do manual
  `@---`; a chave não produz qualquer diferença observável no prompt
  dinâmico.
- **Observações:** Prova diretamente a frase da CA-3 "não produz efeito algum
  sobre o prompt dinâmico gerado", independentemente de a chave ser aceita ou
  rejeitada na validação (CT-05).

### CT-07 — `composicao_medicao` nunca reporta o manual `@---` como incluído `[estende]`

- **CA de origem:** CA-4
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_composicao_camadas_medicao.py` (estender) /
  `tests/test_composicao_camadas_matriz.py::TestMatrizMedicao` (reexecutar)
- **Pré-condição:** Fixture canônica de `compose_execution_record` (steering
  presente, adapter sem tokens), coluna com `allowed-commands` configurada de
  forma que, na versão anterior, incluiria o manual (ex.: `["labels"]`) e,
  variação, sem a chave.
- **Passos:**
  1. Capturar o registro de medição (`compose_execution_record`) para ambas as
     variações de coluna.
  2. Inspecionar o campo `referencias_sob_demanda_incluidas`.
- **Resultado esperado:** Em ambas as variações, `referencias_sob_demanda_incluidas`
  é uma lista vazia (`[]`) — ou o campo não existe no registro, caso o
  desenvolvimento opte por removê-lo. Em nenhum caso a string correspondente
  ao manual `@---` (`"manual_comandos_arroba"` ou equivalente) aparece no
  registro.
- **Observações:** Cobre as 20 combinações já parametrizadas em
  `test_composicao_camadas_matriz.py` (`TestMatrizMedicao`/`TestMatrizTipos`),
  que continuam exigindo o campo como lista (tipo) — este caso adiciona a
  verificação de **conteúdo sempre vazio**, não coberta antes.

### CT-08 — Medição permanece íntegra nos demais campos após a remoção `[estende]`

- **CA de origem:** CA-4
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_composicao_camadas_matriz.py::TestMatrizTipos` (reexecutar sem alteração)
- **Pré-condição:** Mesma matriz fixa de 20 combinações (5 fluxos de Git ×
  transição × agente auxiliar) já existente.
- **Passos:**
  1. Para cada combinação, capturar o registro de medição.
  2. Verificar que os demais campos (`prompt_dinamico`,
     `contexto_sempre_carregado`, `total_sempre_carregado`, `tokens_entrada`,
     `instrucoes_obrigatorias_carregadas`, `execucao`, `adapter`) continuam
     presentes com os tipos corretos.
- **Resultado esperado:** 20/20 combinações continuam produzindo registro
  completo e tipado corretamente; a única mudança de conteúdo é
  `referencias_sob_demanda_incluidas` sempre vazia (CT-07). Nenhuma regressão
  nos demais campos do contrato de medição.
- **Observações:** Não exige nova implementação de teste — é a suíte existente
  de `test_composicao_camadas_matriz.py` rodando sem alteração; citada aqui
  para fechar a rastreabilidade de CA-4/CA-5 (suíte cobre o contrato
  integralmente).

---

## Ajustes necessários na suíte existente (não são casos novos de CA, mas decorrência da remoção)

Estes ajustes são parte do trabalho de teste desta entrega — sem eles a suíte
fica inconsistente com o novo comportamento especificado:

1. **`tests/test_composicao_camadas_sob_demanda.py`** — As classes
   `TestManualArroba` e `TestGateDerivado` afirmam o comportamento **anterior**
   (manual aparece sob demanda) e devem ser **substituídas** pelos casos CT-01,
   CT-02, CT-03 (classe `TestManualArrobaRemovido`) e CT-05, CT-06 (classe
   `TestAllowedCommandsRemovida`), descritos acima. Não há mais cenário em que
   o manual deva aparecer no prompt dinâmico — portanto nenhum teste deve
   afirmar sua presença.
2. **`tests/test_build_prompt_protected_paths.py`** — O teste
   `TestBuildPromptRegressao::test_prompt_contem_secao_anotacoes_body` afirma
   `assert "Anotações no body" in prompt`, o que contradiz CA-1. Deve ser
   **removido ou invertido** para `assert "Anotações no body" not in prompt`
   (coberto por CT-01/CT-02/CT-03 com a fixture mínima desse arquivo).
3. **`tests/test_composicao_camadas_matriz.py`** — Nenhuma alteração estrutural
   necessária (os testes de tipo continuam válidos); CT-07/CT-08 formalizam a
   verificação de conteúdo vazio que esta suíte já teria capacidade de
   expressar.
4. **`doc/architecture/composicao-camadas-prompt-contexto/contrato.md`** e
   **README.md** — a seção "Referência sob demanda (CA-8)" / "Chave opcional
   por coluna para o gate do manual `@---`" descreve a feature removida; a
   atualização textual é tarefa da etapa de Documentação (fora do escopo desta
   QA), mas fica registrada aqui para rastreabilidade e para a próxima etapa
   não reintroduzir a referência por engano.

---

## Devolução ao planejamento (quando aplicável)

Não aplicável: o escopo está completo e não-contraditório para derivar os
casos. Os pontos de alteração em código já foram confirmados concretamente
pelo planejamento (Isabela Gomes — Tech Lead) e verificados nesta etapa; os
critérios de aceitação mapeiam limpo sobre os quatro arquivos citados
(`agent.py`, `composition.py`, `config.py`, `__main__.py`) e sobre a suíte de
testes já existente da entrega #308, que é a mesma a ajustar. Nenhuma decisão
de negócio em aberto impede a especificação. Avançar para `desenvolvimento`.

## Notas de execução para a etapa `execucao-testes`

- A suíte completa deve ser executada com foco nos arquivos:
  `tests/test_composicao_camadas_sob_demanda.py` (reescrito nesta entrega),
  `tests/test_build_prompt_protected_paths.py` (um assert invertido),
  `tests/test_composicao_camadas_matriz.py` (sem alteração — valida não
  regressão), `tests/test_composicao_camadas_medicao.py` (sem alteração —
  valida não regressão dos baselines CT-01/02/03 de #308) e
  `tests/test_config.py` (CT-05, se o desenvolvimento adicionar/remover
  validação).
- Antes desta entrega, `test_composicao_camadas_sob_demanda.py` existente
  **passa** sob o comportamento antigo — ao reescrevê-lo para afirmar a
  ausência incondicional, os novos testes devem **falhar contra o código
  atual** (pré-desenvolvimento) e **passar** após a implementação. Se os
  testes novos passarem antes da implementação, é sinal de caso mal formulado
  (não está exercitando o comportamento antigo que deveria ser removido).
- Isolar qualquer ruído de ambiente pré-existente (ex.: falhas de
  `test_docker_compose`/`test_dockerfile` por binário/daemon ausente no
  ambiente de CI) do veredito desta issue — essas falhas são independentes do
  escopo de #325.
