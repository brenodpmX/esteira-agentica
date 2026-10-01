# Casos de Teste — Composição em camadas do prompt e do contexto entregues ao agente

- **Issue:** #308
- **Story relacionada:** Composição em camadas do prompt e do contexto (board `entrega`, flow `feature`)
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-01
- **Branch:** `feature/308-composicao-em-camadas-do-prompt-e-contexto`

> Todo caso de teste é vinculado a um critério de aceitação (CA). Nenhum caso
> existe sem CA de origem. Cada caso tem resultado esperado explícito e
> verificável. A suíte é Python/pytest em `tests/`.

## Convenções e grounding (leitura obrigatória pelo desenvolvimento)

Os casos abaixo foram derivados do escopo e dos 17 critérios de aceitação da
issue, cruzados com a arquitetura atual do motor. Parte das capacidades **já
existe parcialmente** (ver "Riscos" no corpo da issue); esses casos **reusam ou
estendem** testes já na suíte e estão marcados como `[existente]` ou
`[estende]`. Os demais são `[novo]` (greenfield que o desenvolvimento
implementa).

Pontos de ancoragem no código atual:

- `src/core/agent.py` — `build_prompt(config, task)` concatena hoje todas as
  camadas num único prompt; `annotations_doc()` (manual `@---`) é SEMPRE
  incluído; `target-prompt` (objetivo) e `step-prompt` (passo a passo) já são
  campos separados, mas o passo a passo só é renderizado quando não-vazio;
  `PROTECTED_PATHS` + `_assert_no_protected` já protegem o estado interno;
  `build_continuation_prompt(config, task)` já existe. **Não há** resolução
  única do nome da branch (hoje o padrão é passado como instrução e o agente
  cria a branch).
- `src/core/context_generator.py` — contexto persistente = steering
  `.kiro/steering/esteira.md`, gerado na raiz onde vive o `pipe.yml`;
  `_section_project` já injeta nome/resumo/humanos; `ensure_steering_integrity`
  reescreve o steering se divergir; `_PROTECTED_FILES` inclui
  `.kiro/steering/**/*.md`.
- `src/core/config.py` — `_validate_project` (name/summary obrigatórios, humans
  opcional) e `_validate_git` (exige `branch_pattern` por flow como string
  não-vazia) já existem.
- `src/adapters/kiro_cli_agent.py` — `_compose_input` escolhe
  continuação/full/remediação; `_run` usa `KIRO_HOME` para o steering. **Não
  há** registro de medição por execução nem gate de instruções obrigatórias.
- `src/__main__.py` — `call_agent()` monta prompt/continuação/persona, chama
  `ensure_steering_integrity` e despacha via `_dispatch_with_recovery`.

### Contrato do registro de medição (referência dos casos de CA-1/2/4/5/15/17)

A implementação fixa a sintaxe final; os casos verificam a PRESENÇA e os TIPOS
dos campos, não nomes literais obrigatórios além dos citados nos critérios
(`tokens_entrada`, `instrucoes_obrigatorias_carregadas`,
`referencias_sob_demanda_incluidas`). Estrutura esperada por execução:

```
{
  "execucao": <str>,
  "adapter": <str>,
  "prompt_dinamico": { "caracteres": <int>, "palavras": <int>, "linhas": <int> },
  "contexto_sempre_carregado": { "caracteres": <int>, "palavras": <int>, "linhas": <int> },
  "total_sempre_carregado": { "caracteres": <int>, "palavras": <int> },
  "tokens_entrada": <int|null>,
  "referencias_sob_demanda_incluidas": [<str>, ...],
  "instrucoes_obrigatorias_carregadas": <bool>
}
```

> **Nota de implementação (não normativa):** sugere-se uma função pura de
> composição/medição em `src/core/` (ex.: `compose_measurement(config, task,
> adapter_caps)` ou equivalente) que o adapter e o orquestrador consomem, para
> que os casos unitários meçam sem acionar `kiro-cli`. O desenvolvimento decide
> a arquitetura; os casos abaixo descrevem o comportamento observável.

---

## Rastreabilidade (CA → casos)

| Critério de aceitação | Caso(s) de teste |
|-----------------------|------------------|
| CA-1 — estático do prompt dinâmico ≥ 40% menor | CT-01 |
| CA-2 — total sempre carregado ≥ 20% menor (real, não transferência) | CT-02, CT-03 |
| CA-3 — nenhuma regra em mais de uma camada (inventário) | CT-04 |
| CA-4 — registro `instrucoes_obrigatorias_carregadas: true` | CT-05 |
| CA-5 — sem instruções obrigatórias → não aciona + sinaliza falha + motivo | CT-06, CT-07 |
| CA-6 — cenários de referência (dir/branch/proteção/arquivos/finalização/transição) sem regressão | CT-08, CT-09, CT-10, CT-11, CT-12 |
| CA-7 — sem acesso indevido a estado protegido nem regressão de isolamento | CT-13, CT-14 |
| CA-8 — manual `@---` sob demanda (gate por comandos permitidos na etapa) | CT-15, CT-16, CT-17 |
| CA-9 — objetivo + passo a passo em campos próprios; passo a passo ausente é válido | CT-18, CT-19 |
| CA-10 — nome de branch resolvido idêntico em todos os blocos | CT-20 |
| CA-11 — marcador não resolvível → erro de config, sem nome inconsistente | CT-21, CT-22 |
| CA-12 — metadados de projeto (nome, descrição, humanos) no contexto persistente | CT-23 |
| CA-13 — prompt de continuidade, não maior em palavras, instrui continuar | CT-24, CT-25 |
| CA-14 — contexto persistente na raiz protegido contra escrita indevida | CT-26, CT-27 |
| CA-15 — matriz fixa (5 fluxos × transição × agente auxiliar) com medição p/ todas | CT-28, CT-29 |
| CA-16 — commit/PR refletem a mudança; versionamento não é pulado quando o fluxo exige | CT-30, CT-31 |
| CA-17 — adapter sem tokens → `tokens_entrada: null`, sem falhar | CT-32 |
| RN-04 — regra com origem única (reforço de CA-3) | CT-04 |
| RN-05 — branch única por execução (reforço de CA-10) | CT-20 |
| RN-08 — mover texto de camada não conta como redução | CT-03 |

---

## Casos de teste

### CT-01 — Estático do prompt dinâmico reduz ≥ 40% vs. base `[novo]`

- **CA de origem:** CA-1
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_medicao.py::TestReducaoEstatico`
- **Pré-condição:** Um `task`/`config` fixo (fixture canônica reutilizada pelos
  casos de medição). A "versão-base" é a composição que inclui todo o material
  invariável no prompt dinâmico (comportamento atual de `build_prompt`); a
  "versão entregue" é a composição em camadas.
- **Passos:**
  1. Compor o prompt dinâmico da versão entregue para a fixture canônica.
  2. Obter o tamanho do conteúdo ESTÁTICO (invariável) do prompt dinâmico
     base e entregue — medir caracteres (a métrica estática exclui os dados
     variáveis da tarefa: título, paths, ids).
  3. Calcular a razão `entregue_estatico / base_estatico`.
- **Resultado esperado:** `entregue_estatico <= 0.60 * base_estatico` (redução
  de pelo menos 40% do conteúdo estático). O valor-base é fixado por uma
  constante/fixture congelada no teste para a medição ser determinística e não
  depender de execução real do agente.
- **Observações:** A fronteira "estático vs. variável" deve ser explícita na
  fixture (ver "Riscos" da issue). Caso o desenvolvimento exponha uma função de
  medição, o teste chama-a diretamente; não deve acionar `kiro-cli`.

### CT-02 — Total sempre carregado reduz ≥ 20% no adapter suportado `[novo]`

- **CA de origem:** CA-2
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_medicao.py::TestReducaoTotal`
- **Pré-condição:** Fixture canônica + o contexto sempre carregado (steering
  gerado por `context_generator`) para o mesmo cenário, nas duas versões.
- **Passos:**
  1. Medir `total_sempre_carregado` (prompt dinâmico + contextos automáticos)
     da versão-base (congelada na fixture) e da versão entregue.
  2. Calcular a razão `entregue_total / base_total` (em caracteres).
- **Resultado esperado:** `entregue_total <= 0.80 * base_total` (redução de pelo
  menos 20% do total sempre carregado).
- **Observações:** Mede o AGREGADO das camadas sempre carregadas, não só o
  prompt. Complementa CT-01 (que isola o prompt dinâmico).

### CT-03 — Redução é real, não transferência entre camadas (RN-08) `[novo]`

- **CA de origem:** CA-2 / RN-08
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_medicao.py::TestReducaoNaoEhTransferencia`
- **Pré-condição:** Medições por camada (prompt dinâmico e contexto sempre
  carregado) nas versões base e entregue.
- **Passos:**
  1. Medir caracteres do prompt dinâmico e do contexto sempre carregado em cada
     versão.
  2. Verificar que a soma `total_sempre_carregado` entregue é ≤ 80% da base
     (CT-02) **e** que a redução do prompt dinâmico NÃO foi integralmente
     absorvida pelo contexto sempre carregado (i.e. o contexto sempre carregado
     entregue não cresceu o suficiente para anular a economia do prompt).
- **Resultado esperado:** `contexto_entregue - contexto_base <
  (prompt_base - prompt_entregue)` — ou seja, o aumento (se houver) de uma
  camada sempre carregada é estritamente menor que a redução da outra, provando
  economia líquida real do total.
- **Observações:** Formaliza RN-08 como asserção. Protege contra a "redução
  fantasma" (mover texto de camada).

### CT-04 — Inventário auditável sem regra duplicada entre camadas sempre carregadas `[novo]`

- **CA de origem:** CA-3 / RN-04
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_inventario.py::TestInventarioSemDuplicidade`
- **Pré-condição:** Existe um inventário auditável das regras/instruções
  classificadas por responsabilidade (política invariável, contexto do projeto,
  workflow da etapa, dados da tarefa) e por camada (prompt dinâmico vs. contexto
  sempre carregado). O inventário deve ser derivável por código (ex.: estrutura
  de dados ou função que lista as regras por camada).
- **Passos:**
  1. Obter o inventário das camadas SEMPRE carregadas (prompt dinâmico estático
     + contexto sempre carregado).
  2. Para cada regra identificada por uma chave estável (id/slug da regra),
     contar em quantas camadas sempre carregadas ela aparece.
- **Resultado esperado:** Nenhuma regra aparece em mais de uma camada sempre
  carregada (cada regra tem origem única — RN-04). O teste falha listando a
  regra duplicada e as camadas em que aparece.
- **Observações:** A classificação por responsabilidade também é verificada: o
  teste assegura que o inventário cobre as quatro classes. Esse caso é a prova
  do "inventário auditável" do escopo.

### CT-05 — Registro de carregamento das instruções obrigatórias = true `[novo]`

- **CA de origem:** CA-4
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_composicao_camadas_medicao.py::TestInstrucoesObrigatorias::test_carregadas_true`
- **Pré-condição:** Adapter suportado (`kiro-cli`) com o steering/contexto
  obrigatório presente e íntegro; execução mockada (sem acionar `kiro-cli`
  real).
- **Passos:**
  1. Compor a execução para a fixture canônica com as instruções obrigatórias
     disponíveis.
  2. Capturar o registro de medição emitido por execução, antes de acionar o
     agente.
- **Resultado esperado:** O registro contém
  `instrucoes_obrigatorias_carregadas == True`. O agente é acionado normalmente.
- **Observações:** O registro deve ser emitido ANTES do acionamento do agente
  (contrato "registrado por execução antes de acionar o agente").

### CT-06 — Sem instruções obrigatórias → agente NÃO é acionado `[novo]`

- **CA de origem:** CA-5
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_composicao_camadas_medicao.py::TestInstrucoesObrigatorias::test_ausentes_nao_aciona`
- **Pré-condição:** Adapter suportado com as instruções obrigatórias
  AUSENTES/não carregáveis (ex.: steering inexistente/vazio no `KIRO_HOME`
  simulado). Execução mockada: um espião no ponto de acionamento do agente
  (`adapter.execute` / `subprocess.run`).
- **Passos:**
  1. Compor a execução com as instruções obrigatórias ausentes.
  2. Observar se o agente foi acionado.
- **Resultado esperado:** O agente NÃO é acionado (o espião registra zero
  chamadas); a composição é recusada/sinalizada como falha.
- **Observações:** Fail-closed: a ausência das instruções obrigatórias bloqueia
  o acionamento. Não deve lançar exceção não tratada que derrube o loop — a
  falha é sinalizada (ver CT-07).

### CT-07 — Falha de composição sinalizada com `false` + motivo `[novo]`

- **CA de origem:** CA-5
- **Tipo:** integração
- **Arquivo/alvo:** `tests/test_composicao_camadas_medicao.py::TestInstrucoesObrigatorias::test_ausentes_registra_motivo`
- **Pré-condição:** Mesma de CT-06 (instruções obrigatórias ausentes).
- **Passos:**
  1. Compor a execução com as instruções obrigatórias ausentes.
  2. Capturar o registro de medição e/ou o log estruturado da falha de
     composição.
- **Resultado esperado:** O registro contém
  `instrucoes_obrigatorias_carregadas == False` e um motivo não-vazio
  (mensagem/campo) descrevendo por que as instruções não foram carregadas.
- **Observações:** O motivo é texto humano-legível; o teste verifica presença e
  não-vazio, não o literal exato.

### CT-08 — Regressão: diretório de trabalho obrigatório no prompt `[estende]`

- **CA de origem:** CA-6
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_build_prompt_git_setup.py` (estender) /
  `tests/test_composicao_camadas_regressao.py::TestDiretorioTrabalho`
- **Pré-condição:** `build_prompt` com `task` padrão (board/coluna/issue).
- **Passos:**
  1. Compor o prompt na versão entregue.
  2. Verificar a presença da seção de diretório de trabalho e da regra `cd
     <work_dir>` / operar apenas no clone.
- **Resultado esperado:** O prompt entregue mantém a instrução de diretório de
  trabalho obrigatório e a proibição de operar fora dele (sem regressão vs.
  base).
- **Observações:** Reusar os asserts já existentes em
  `test_build_prompt_git_setup.py` adaptando ao novo formato de camadas.

### CT-09 — Regressão: preparação de branch (reutilizar vs. criar atômica) `[estende]`

- **CA de origem:** CA-6
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_build_prompt_git_setup.py` (estender) /
  `tests/test_composicao_camadas_regressao.py::TestBranch`
- **Pré-condição:** `task` com `gitevents` em `{create, create-merge}` e, em
  variação, `{use, merge}`.
- **Passos:**
  1. Compor o prompt para gitevents de criação e verificar a instrução de
     criação ATÔMICA a partir de `origin/<origin_branch>` (proteção do bug
     #108) e de gravar o nome real na anotação `branch:`.
  2. Compor para gitevents sem criação e verificar que a etapa opera sobre a
     branch já existente (idempotência) e não cria branch nova.
- **Resultado esperado:** As instruções de branch (criação atômica, proibição
  de HEAD corrente, idempotência) permanecem presentes conforme o `gitevents`,
  sem regressão.
- **Observações:** Alinhado ao texto atual de `build_prompt`.

### CT-10 — Regressão: proteção de estado interno no prompt `[estende]`

- **CA de origem:** CA-6
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_build_prompt_protected_paths.py` (estender)
- **Pré-condição:** Composição em camadas ativa; `PROTECTED_PATHS` definido.
- **Passos:**
  1. Compor o prompt entregue para a fixture canônica e para variações onde um
     path protegido poderia vazar.
  2. Reexecutar os asserts existentes de `_assert_no_protected` sobre o novo
     caminho de composição.
- **Resultado esperado:** `_assert_no_protected` continua levantando
  `ValueError` quando um path protegido aparece e permanece silencioso quando
  não aparece; nenhum path de `PROTECTED_PATHS` vaza no prompt composto em
  camadas.
- **Observações:** Garante que a recomposição não burlou o guard existente.

### CT-11 — Regressão: leitura/escrita dos arquivos da tarefa `[estende]`

- **CA de origem:** CA-6
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_regressao.py::TestArquivosDaTarefa`
- **Pré-condição:** `task` com `body_path` resolvível; derivação de
  `history`/`addcomment` por slug.
- **Passos:**
  1. Compor o prompt entregue.
  2. Verificar que o prompt aponta os caminhos ABSOLUTOS corretos de
     `-body.md`, `-history.md` e `-addcomment.md` e instrui assinar o
     addcomment.
- **Resultado esperado:** Os três caminhos aparecem corretos e a instrução de
  anotar/assinar o addcomment está presente (sem regressão).
- **Observações:** Deriva do bloco "Executar tarefa" atual.

### CT-12 — Regressão: finalização e transição de coluna no prompt `[estende]`

- **CA de origem:** CA-6
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_regressao.py::TestTransicao`
- **Pré-condição:** `task` com `column.change` mapeando condição → coluna
  destino.
- **Passos:**
  1. Compor o prompt entregue.
  2. Verificar a seção "Transição de coluna" e os comandos `mv` para cada
     condição de `change`.
- **Resultado esperado:** Cada condição de transição gera a linha `mv` para o
  diretório da coluna de destino resolvido; a seção permanece presente (sem
  regressão).
- **Observações:** Vale também para `build_continuation_prompt` (ver CT-24).

### CT-13 — Nenhum acesso indevido ao estado protegido em execução `[estende]`

- **CA de origem:** CA-7 / RN-02
- **Tipo:** unitário/integração
- **Arquivo/alvo:** `tests/test_build_prompt_protected_paths.py` (estender) /
  `tests/test_snapshot_guard_call_agent.py` (reusar)
- **Pré-condição:** Fluxo de composição + despacho mockado.
- **Passos:**
  1. Compor e despachar (mock) para a fixture canônica.
  2. Verificar que nenhum path de estado interno protegido aparece no input
     final enviado ao agente (prompt + persona + continuação).
- **Resultado esperado:** Zero ocorrências de paths protegidos no input
  composto; o guard de snapshot permanece ativo durante o despacho (sem
  regressão).
- **Observações:** Cobre o input COMPLETO (não só `build_prompt`).

### CT-14 — Isolamento de repositório/diretório preservado (RN-06) `[estende]`

- **CA de origem:** CA-7 / RN-06
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_regressao.py::TestIsolamentoRepo`
- **Pré-condição:** `config`/`board` resolvendo `work_dir = repo/<repo_id>`.
- **Passos:**
  1. Compor o prompt entregue.
  2. Verificar que o `work_dir` citado é o clone `repo/<repo_id>` resolvido e
     que a instrução de operar apenas nele permanece.
- **Resultado esperado:** O prompt confina o agente ao `work_dir` do repo
  resolvido; nenhuma referência a operar no diretório da esteira. Sem regressão
  de isolamento.
- **Observações:** Complementa CT-08.

### CT-15 — Etapa SEM comando de anotação não carrega o manual `@---` `[novo]`

- **CA de origem:** CA-8
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_sob_demanda.py::TestManualArroba::test_etapa_sem_comando_nao_carrega`
- **Pré-condição:** Uma etapa cujo conjunto de comandos permitidos NÃO inclui
  comandos de anotação `@---` (gate derivado dos comandos permitidos da etapa).
- **Passos:**
  1. Compor o prompt entregue para essa etapa.
  2. Verificar a ausência do conteúdo do manual `@---` (hoje produzido por
     `annotations_doc()`).
- **Resultado esperado:** O manual `@---` NÃO aparece no prompt composto; o
  registro de medição lista `referencias_sob_demanda_incluidas` SEM a
  referência do manual `@---`.
- **Observações:** Hoje `annotations_doc()` é sempre incluído — este caso prova
  a mudança (gate sob demanda).

### CT-16 — Etapa COM comando de anotação disponibiliza o manual `@---` `[novo]`

- **CA de origem:** CA-8
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_sob_demanda.py::TestManualArroba::test_etapa_com_comando_carrega`
- **Pré-condição:** Uma etapa cujo conjunto de comandos permitidos inclui pelo
  menos um comando `@---` que torne o manual necessário.
- **Passos:**
  1. Compor o prompt entregue para essa etapa.
  2. Verificar a presença (sob demanda) do manual `@---`.
- **Resultado esperado:** O manual `@---` fica disponível; o registro lista a
  referência correspondente em `referencias_sob_demanda_incluidas`.
- **Observações:** Par simétrico de CT-15.

### CT-17 — Gate de referência sob demanda é derivado dos comandos permitidos `[novo]`

- **CA de origem:** CA-8
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_sob_demanda.py::TestGateDerivado`
- **Pré-condição:** Duas configurações de etapa que diferem apenas no conjunto
  de comandos permitidos.
- **Passos:**
  1. Compor para ambas as etapas.
  2. Comparar `referencias_sob_demanda_incluidas` das duas composições.
- **Resultado esperado:** A inclusão da referência extensa é função
  determinística do conjunto de comandos permitidos (entra se, e somente se, a
  etapa permite comando que a exige). O teste cobre o critério de derivação, não
  um valor fixo.
- **Observações:** Protege a regra "derivado" da tabela de chaves de config.

### CT-18 — Objetivo e passo a passo em campos próprios `[estende]`

- **CA de origem:** CA-9
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_campos.py::TestObjetivoPasso::test_ambos_presentes`
- **Pré-condição:** Etapa com `target-prompt` (objetivo) e `step-prompt` (passo
  a passo) configurados, ambos não-vazios.
- **Passos:**
  1. Compor o prompt entregue.
  2. Verificar que o objetivo aparece no campo "Objetivo" e o passo a passo no
     campo "Passos", separados.
- **Resultado esperado:** Ambos aparecem em campos próprios e distintos, sem
  mistura.
- **Observações:** Já parcialmente coberto pelo render atual de `build_prompt`;
  estender para o novo formato de camadas.

### CT-19 — Passo a passo ausente mantém a etapa válida `[estende]`

- **CA de origem:** CA-9
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_campos.py::TestObjetivoPasso::test_so_objetivo`
- **Pré-condição:** Etapa com objetivo (`target-prompt`) não-vazio e passo a
  passo (`step-prompt`) AUSENTE ou vazio.
- **Passos:**
  1. Compor o prompt entregue.
  2. Verificar que a composição ocorre sem erro e sem a seção "Passos".
- **Resultado esperado:** A etapa permanece válida; o prompt é composto sem o
  bloco de passos (ausência é configuração válida). Nenhuma exceção.
- **Observações:** Alinhado à tabela de chaves (passo a passo opcional; quando
  presente, não-vazio).

### CT-20 — Nome de branch resolvido uma vez, idêntico em todos os blocos `[novo]`

- **CA de origem:** CA-10 / RN-05
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_branch.py::TestBranchResolvidaUnica`
- **Pré-condição:** Fluxo com `branch_pattern` resolvível (todos os marcadores
  com dados da tarefa), em `gitevents = create-merge` (cita a branch na criação
  e no merge/PR).
- **Passos:**
  1. Compor o prompt entregue com a resolução do nome da branch habilitada.
  2. Extrair TODAS as ocorrências do nome da branch de trabalho no prompt
     (bloco de criação e bloco de merge/PR).
- **Resultado esperado:** Todas as ocorrências do nome de branch de trabalho são
  idênticas (resolvido uma única vez por execução — RN-05); não há duas grafias
  diferentes para a mesma branch.
- **Observações:** Este caso pressupõe que a composição passe a RESOLVER o nome
  (hoje o padrão é instrução para o agente). Se o desenvolvimento mantiver a
  resolução pelo agente, o critério de "idêntico em todos os blocos" ainda deve
  ser verificável no texto composto — o teste exige unicidade do nome citado.

### CT-21 — Marcador de branch não resolvível → ConfigError `[novo]`

- **CA de origem:** CA-11
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_branch.py::TestBranchMarcadorInvalido::test_marcador_nao_resolvivel_erro`
- **Pré-condição:** `branch_pattern` com um marcador que não pode ser resolvido
  com os dados da tarefa (ex.: `{inexistente}`), fluxo com `gitevents` de
  criação.
- **Passos:**
  1. Tentar compor/resolver o nome da branch.
- **Resultado esperado:** Erro de configuração sinalizado (ex.: `ConfigError`)
  nomeando o marcador/dado faltante; a composição não prossegue com nome
  inconsistente.
- **Observações:** Alinha com "Comportamento em falha" → formato de branch com
  marcador não resolvível.

### CT-22 — Nenhum nome de branch inconsistente é emitido na falha `[novo]`

- **CA de origem:** CA-11
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_branch.py::TestBranchMarcadorInvalido::test_nao_emite_nome_parcial`
- **Pré-condição:** Mesma de CT-21.
- **Passos:**
  1. Capturar o resultado da tentativa de composição (erro).
  2. Verificar que nenhum nome de branch parcialmente resolvido (com marcador
     literal remanescente, ex.: `feature/{inexistente}-...`) foi gerado nem
     escrito em nenhum bloco/registro.
- **Resultado esperado:** Não há nome de branch com marcador não resolvido em
  lugar algum da saída/registro; apenas o erro de config é sinalizado.
- **Observações:** Protege contra o nome "meio resolvido" vazar.

### CT-23 — Metadados de projeto no contexto persistente `[estende]`

- **CA de origem:** CA-12
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_context_generator.py` (estender) /
  `tests/test_composicao_camadas_contexto.py::TestMetadadosProjeto`
- **Pré-condição:** `config['project']` com `name`, `summary` (descrição) e
  `humans` (lista de nome+função).
- **Passos:**
  1. Gerar o contexto persistente (steering) para esse config.
  2. Ler o conteúdo gerado.
- **Resultado esperado:** Os três metadados constam do contexto persistente:
  nome, descrição (summary) e cada humano com nome e função. (Hoje
  `_section_project` já cobre isso — o caso congela o comportamento sob o
  contrato da entrega.)
- **Observações:** Reusar/estender asserts de `test_context_generator.py`.

### CT-24 — Prompt de continuidade instrui continuar de onde parou `[estende]`

- **CA de origem:** CA-13
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_session_continuation.py` (estender) /
  `tests/test_composicao_camadas_continuidade.py::TestContinuidadeConteudo`
- **Pré-condição:** Sessão registrada/confirmada para a tarefa;
  `build_continuation_prompt` disponível.
- **Passos:**
  1. Compor o prompt de continuidade para a fixture.
  2. Verificar que instrui retomar (não recomeçar) e aponta
     history/addcomment/body + transição.
- **Resultado esperado:** O prompt contém a instrução de continuar de onde parou
  e os ponteiros aos arquivos e à transição (sem regressão vs. o atual).
- **Observações:** Reusa os asserts já existentes de
  `TestBuildContinuationPrompt`.

### CT-25 — Continuidade não é maior em palavras que a primeira execução `[novo]`

- **CA de origem:** CA-13
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_continuidade.py::TestContinuidadeTamanho`
- **Pré-condição:** Mesma `task` para `build_prompt` (primeira execução) e
  `build_continuation_prompt` (continuidade).
- **Passos:**
  1. Compor ambos os prompts para a MESMA tarefa.
  2. Contar palavras de cada um (mesma função de contagem).
- **Resultado esperado:** `palavras(continuacao) <= palavras(primeira_execucao)`
  para a mesma tarefa.
- **Observações:** Critério comparativo explícito do CA-13.

### CT-26 — Contexto persistente na raiz protegido contra escrita (prompt) `[estende]`

- **CA de origem:** CA-14 / RN-02
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_build_prompt_protected_paths.py` (estender) /
  `tests/test_composicao_camadas_contexto.py::TestContextoProtegidoNoPrompt`
- **Pré-condição:** O contexto persistente é `.kiro/steering/esteira.md` na raiz
  do projeto; `_PROTECTED_FILES`/`PROTECTED_PATHS` cobrem
  `.kiro/steering/**/*.md`.
- **Passos:**
  1. Compor o input completo da execução.
  2. Verificar que o caminho do contexto persistente não aparece como gravável e
     que o steering está listado entre os protegidos.
- **Resultado esperado:** O contexto persistente da raiz é tratado como protegido
  (nunca gravável pelo agente, nunca exposto como estado interno).
- **Observações:** Preserva a premissa fechada (proteção equivalente à atual).

### CT-27 — Integridade do contexto persistente reescrita se divergir `[estende]`

- **CA de origem:** CA-14 / RN-02
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_steering_integrity.py` (reusar/estender)
- **Pré-condição:** `ensure_steering_integrity(config)` disponível.
- **Passos:**
  1. Gerar o contexto persistente.
  2. Corromper o arquivo (simular escrita indevida do agente) e chamar
     `ensure_steering_integrity`.
- **Resultado esperado:** A guarda detecta a divergência e REESCREVE com o
  conteúdo autoritativo (retorna `True`); conteúdo corrompido some. Íntegro →
  `False`.
- **Observações:** Reusa os três casos já existentes de `TestSteeringIntegrity`.

### CT-28 — Medição presente para TODAS as combinações da matriz fixa `[novo]`

- **CA de origem:** CA-15
- **Tipo:** unitário/integração (parametrizado)
- **Arquivo/alvo:** `tests/test_composicao_camadas_matriz.py::TestMatrizMedicao`
- **Pré-condição:** Matriz = 5 fluxos de Git (`create`, `use`, `merge`,
  `create-merge`, `no-branch`) × {com transição de coluna, sem transição} ×
  {com agente auxiliar (agent-hub), sem agente auxiliar} → 20 combinações.
- **Passos:**
  1. Para cada combinação, compor e capturar o registro de medição.
  2. Verificar que existe exatamente um registro por combinação, com os campos
     obrigatórios do contrato preenchidos (`prompt_dinamico`,
     `contexto_sempre_carregado`, `total_sempre_carregado`,
     `referencias_sob_demanda_incluidas`, `instrucoes_obrigatorias_carregadas`).
- **Resultado esperado:** 20/20 combinações produzem registro de medição com os
  campos obrigatórios; nenhuma combinação fica sem medição.
- **Observações:** Usar `pytest.mark.parametrize` sobre as 20 combinações. Mede
  sem acionar `kiro-cli`.

### CT-29 — Campos de medição têm os tipos corretos por combinação `[novo]`

- **CA de origem:** CA-15
- **Tipo:** unitário (parametrizado)
- **Arquivo/alvo:** `tests/test_composicao_camadas_matriz.py::TestMatrizTipos`
- **Pré-condição:** Mesma matriz de CT-28.
- **Passos:**
  1. Para cada combinação, validar os tipos: caracteres/palavras/linhas são
     `int`; `referencias_sob_demanda_incluidas` é lista; `tokens_entrada` é
     `int` ou `None`; `instrucoes_obrigatorias_carregadas` é `bool`.
- **Resultado esperado:** Todos os campos têm os tipos esperados em todas as
  combinações.
- **Observações:** Complementa CT-28 (presença) com validação de tipos.

### CT-30 — Versionamento não é pulado quando o fluxo exige `[estende]`

- **CA de origem:** CA-16
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_versionamento.py::TestVersionamentoObrigatorio`
- **Pré-condição:** `task` com `gitevents` em `{create, use, merge,
  create-merge}` (exigem versionar) e, em variação, `no-branch` (não exige).
- **Passos:**
  1. Compor o prompt para cada `gitevents`.
  2. Verificar presença/ausência da seção "Versionar (commit e push)" conforme o
     fluxo.
- **Resultado esperado:** Para fluxos que exigem Git, a seção de commit/push está
  presente e incondicional (o agente não decide pular); para `no-branch`, não
  há seção de versionamento.
- **Observações:** Alinhado à premissa fechada (liberdade só de TEXTO da
  mensagem; não pular etapa).

### CT-31 — Mensagem de commit/PR reflete a etapa (texto livre) `[estende]`

- **CA de origem:** CA-16
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_versionamento.py::TestMensagemReflecteMudanca`
- **Pré-condição:** `task` com `gitevents` em `{merge, create-merge}` (abre PR).
- **Passos:**
  1. Compor o prompt.
  2. Verificar que o prompt instrui o agente a usar mensagem de commit/PR que
     descreva a etapa/mudança e aponta o alvo de merge correto do fluxo.
- **Resultado esperado:** A instrução de "mensagem que descreva a etapa/mudança"
  está presente e o alvo de merge/PR é o do fluxo; a liberdade do agente é só de
  texto.
- **Observações:** Reusar o bloco "Abrir merge/PR" atual, adaptado ao formato de
  camadas.

### CT-32 — Adapter sem tokens → `tokens_entrada: null`, sem falhar `[novo]`

- **CA de origem:** CA-17
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_composicao_camadas_medicao.py::TestTokensAusentes`
- **Pré-condição:** Adapter (capacidades) que NÃO expõe contagem de tokens.
- **Passos:**
  1. Compor a execução e capturar o registro de medição.
- **Resultado esperado:** O registro usa caracteres/palavras normalmente e
  `tokens_entrada == None` (null), sem lançar exceção.
- **Observações:** Garante o caminho de degradação suave da medição.

---

## Devolução ao planejamento (quando aplicável)

Não aplicável: o escopo está completo e não-contraditório para derivar os casos.
As duas premissas que a abertura sinalizava já vêm fixadas no corpo (liberdade só
de texto no commit/PR; proteção do contexto persistente equivalente à atual), e
as capacidades parciais estão explicitamente marcadas no corpo e nestes casos
(reuso/estensão vs. greenfield). Nenhuma decisão de negócio em aberto impede a
especificação. Avançar para `desenvolvimento`.

## Notas de execução para a etapa `execucao-testes`

- Baseline da suíte em `origin/main` (HEAD `e0304d0`): 1362 passed, 26 failed,
  17 skipped. As 26 falhas são PRÉ-EXISTENTES e independem de #308
  (`test_agent_log_descritivo` — formato de log do ambiente;
  `test_docker_compose`/`test_dockerfile` — docker/binário ausentes no
  ambiente). Ao executar os testes desta issue, isolar esse ruído de ambiente e
  focar nos arquivos `tests/test_composicao_camadas_*.py` e nos testes
  estendidos citados na rastreabilidade.
- Os casos marcados `[novo]` dependem da implementação do contrato de medição e
  do gate sob demanda; naturalmente falham/estão ausentes antes do
  desenvolvimento (escritos antes do código → se reprovarem na `execucao-testes`
  por ausência de implementação, a classificação é de código, não de caso).
