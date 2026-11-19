# Casos de Teste — Documentação pública de avaliação e governança editorial do produto

- **Issue:** #313
- **Story relacionada:** n/a (issue única, planejamento já fechado o escopo)
- **Autor(a):** Camila Rocha — Engenheira de Qualidade SR (QA)
- **Data:** 2026-11-11
- **Branch:** `feature/313-documentacao_publica_de_avaliacao_e_governanca_editorial_do_produto`

> Todo caso de teste é vinculado a um critério de aceitação (CA, 1–12 do corpo da
> issue) e, quando aplicável, ao cenário obrigatório correspondente (`CT-0X do
> corpo`). Nenhum caso existe sem CA de origem. Os testes automatizados são da
> suíte Python do motor (pytest, em `tests/`); os marcados **manual** dependem
> de um avaliador humano ou de participantes reais e são evidenciados por
> registro, não por pytest — a esteira não tem como simular a leitura humana do
> README nem a execução por um avaliador externo.
>
> Numeração: os casos deste documento usam `CT-NN`. Isso reaproveita o prefixo
> já usado pelo corpo da issue para os cenários obrigatórios (CT-01..CT-12) —
> quando a referência for a um cenário da issue, o texto diz explicitamente
> "CT-0X **do corpo**"; sem essa marcação, `CT-NN` refere-se sempre a este
> documento.

---

## 1. Baseline da suíte existente (avaliado antes de criar casos)

- Não existe hoje nenhum teste sobre a estrutura editorial do `README.md`, nem
  sobre catálogo de configuração, inventário de conteúdo público, manual de
  padrões, gate de revisão ou comunicação de versão. É escopo 100% novo.
- Precedente direto de **estilo de teste estático sobre documentação Markdown**,
  a reaproveitar sem reescrever o padrão:
  - `tests/test_docker_runbook.py` — asserções por regex sobre conteúdo de
    Markdown, com `pytest.mark.skipif` quando o artefato ainda não existe,
    mensagens de falha citando o critério de aceitação de origem, e checagem de
    consistência entre o documento e os artefatos reais (compose, `.env.example`).
  - `tests/test_vitrine_estrutura.py`, `test_vitrine_governanca.py`,
    `test_vitrine_registros.py`, `test_vitrine_config.py` e o helper
    `tests/_vitrine_helpers.py` — padrão de **validador puro** (`validar_registro_*`,
    função de teste que recebe um `dict` e devolve lista de erros) usado para
    testar tanto registros reais quanto casos sintéticos de regra de negócio
    documental (ex.: `h.validar_registro_impacto`, `h.validar_registro_apresentacao`).
    Esta issue trata de **governança documental equivalente** (gate, catálogo,
    inventário, nota de versão) e reaproveita exatamente este padrão — a função
    validadora aplica o contrato de comportamento definido no corpo da issue
    ("Detalhamento → Configuração e contratos"), não implementa o mecanismo de
    produção do gate (que está fora de escopo, conforme a própria issue).
  - `tests/test_version_bump.py` — fonte única da versão corrente:
    `src.core.version.VERSION` (hoje `1.29.0`), e o hábito de testar
    `CONTEXT.md`/changelog em conjunto com a versão.
  - `tests/test_versions_env.py` — padrão de lista `REQUIRED_KEYS` fixa,
    comparada contra um arquivo de configuração, para garantir cobertura
    completa de campos obrigatórios. Reaproveitado para a cobertura de 100% das
    chaves do catálogo (CA-9).
- `src/core/config.py` (mais os módulos que ele delega:
  `src/core/consumption_limit.py`, `src/core/agent_circuit_break.py`,
  `src/core/sync_circuit_breaker.py`) é a **fonte de verdade mecânica** de quais
  chaves de `pipe.yml` o motor conhece — os nomes de chave aparecem literalmente
  nas mensagens de `ConfigError` e nos argumentos de `_require`. A lista
  canônica da §2.3 foi extraída de lá (mais `src/core/log.py` para `log.dir`/
  `log.level`, e `src/__main__.py` para `boards.<board_id>.parallel`), não do
  `README.md` atual — o `README.md` atual **já está incompleto** (ex.:
  `sync.max_attempts` não aparece em nenhuma documentação hoje), o que é
  exatamente o gap que o catálogo (RF-08/RNF-06) precisa fechar.
- `README.md` tem hoje 1415 linhas. A ordem "execução local antes do container"
  (RN-08) **já está correta** na seção `## Uso` (`### Execução local (Python)`
  antes de `### Execução via Docker Compose`) — é regressão a proteger, não
  reescrita a exigir.

## 2. Decisões de especificação (ambiguidades fechadas aqui, sem reabrir escopo)

O corpo da issue já fixa, em "Detalhamento → Configuração e contratos", os
campos mínimos de quatro artefatos (catálogo de chave, inventário, nota de
versão, gate). Os testes abaixo usam esses campos **literalmente**, sem
alteração. O que faltava para os casos serem implementáveis sem ambiguidade era
somente **onde** cada artefato vive e **qual conjunto exato** de chaves/itens
ele precisa cobrir — fixado abaixo.

### 2.1 Caminhos dos artefatos (a criar pelo desenvolvimento)

```
README.md                                          — porta de entrada (reescrito)
doc/configuracao/referencia.md                     — catálogo de chaves (RF-08)
doc/governanca-editorial/inventario-conteudo-publico.md   — inventário (RF-07)
doc/governanca-editorial/manual-padroes-documentacao.md   — manual de padrões (RF-11)
doc/governanca-editorial/gate-revisao.md                  — contrato do gate (RF-12)
doc/governanca-editorial/comunicacao-versao.md             — processo de nota de versão (RF-09/RF-10)
doc/governanca-editorial/baseline-avaliacao.md             — decisão de baseline (RF-13/RN-11)
NOVIDADES.md                                        — canal único de nota pública de versão (RF-09)
CHANGELOG.md                                        — mantido; passa a ser classificado
                                                      como registro técnico complementar
                                                      (interno/detalhado), não mais a porta
                                                      pública de comunicação de versão
tests/_editorial_helpers.py                         — helpers/validadores puros desta suíte
```

Justificativa de `NOVIDADES.md` separado do `CHANGELOG.md`: o `CHANGELOG.md`
existente é tecnicista (listas de "Adicionado"/"Corrigido" com detalhe de
implementação) — o oposto do que RN-07 exige para a nota pública ("nunca uma
lista tecnicista"). Reescrever o `CHANGELOG.md` para benefício destruiria seu
valor como registro técnico (ele é citado por outros documentos, ex. runbooks).
Criar um canal novo e único resolve a fragmentação apontada no problema (CA-6)
sem apagar histórico nem reabrir escopo de migração de conteúdo não pedido.

### 2.2 Contratos de campo (citados verbatim do corpo da issue — não são decisão nova)

Catálogo de chave (`chave`, `descricao`, `tipo`, `obrigatoriedade`, `default`,
`valores_aceitos`, `efeito_ausencia`, `exemplo`), inventário (`documento`,
`audiencia`, `sensibilidade`, `fonte_canonica`, `responsavel`,
`gatilho_atualizacao`), nota de versão (`versao`, `data`, `destaques`, `acao`)
e gate (`entrada`, `criterios`, `saida_aprovado`, `saida_reprovado`) — ver seção
"Configuração e contratos" do corpo da issue. Formato de registro: linhas
`chave: valor` (uma por linha), parseável por `^([a-z_]+):\s*(.*)$`, igual ao
padrão já usado em `doc/exemplos/` (ver `tests/_vitrine_helpers.py`).

### 2.3 Lista canônica de chaves de `pipe.yml` (fecha CA-9 / RNF-06 "100%")

Extraída mecanicamente de `src/core/config.py`, `src/core/consumption_limit.py`,
`src/core/agent_circuit_break.py`, `src/core/sync_circuit_breaker.py`,
`src/core/log.py` e `src/__main__.py` (não do `README.md`, que está incompleto
hoje). Segmentos variáveis (id de board/coluna/agente/plataforma/flow/valor de
hub) usam `<...>` e são descritos no catálogo **uma vez**, pela chave
estrutural — não por instância:

```
sleep
log.dir
log.ttl
log.level
registro.retencao_dias
agent_timeout_seg
retry.max_tentativas
retry.backoff_inicial_seg
retry.backoff_fator
safety.cross_board_parent_links
sync.max_attempts
sync.circuit_breaker.persistence
sync.circuit_breaker.escalation_agent
sync.circuit_breaker.issue.max_failures
sync.circuit_breaker.issue.block_duration
sync.circuit_breaker.issue.max_blocks
sync.circuit_breaker.platform.max_blocked_issues
sync.circuit_breaker.platform.block_window
sync.circuit_breaker.platform.block_duration
sync.circuit_breaker.half_open.success_threshold
agent_circuit_break.executions
agent_circuit_break.window
project.name
project.summary
project.humans.name
project.humans.role
git.repo.main
git.flow.base
git.flow.<flow_id>.prefix
git.flow.<flow_id>.name
git.flow.<flow_id>.branch_pattern
git.flow.<flow_id>.create
git.flow.<flow_id>.merge
agents.<platform_id>.<agent_id>.name
agents.<platform_id>.<agent_id>.model
agents.<platform_id>.limits.timezone
agents.<platform_id>.limits.daily.limit
agents.<platform_id>.limits.weekly.limit
agents.<platform_id>.limits.weekly.reset_weekday
agents.<platform_id>.limits.monthly.limit
agents.<platform_id>.limits.monthly.reset_day
boards.platform
boards.rerun_cooldown
boards.<board_id>.name
boards.<board_id>.priority
boards.<board_id>.flow
boards.<board_id>.parallel
boards.<board_id>.column-migrations.<origem>
boards.<board_id>.file-sync.allowed-types
boards.<board_id>.file-sync.max-size
boards.<board_id>.file-sync.on-reject
boards.<board_id>.columns.<column_id>.name
boards.<board_id>.columns.<column_id>.agent
boards.<board_id>.columns.<column_id>.agent-hub.<valor>
boards.<board_id>.columns.<column_id>.on_in
boards.<board_id>.columns.<column_id>.on_out
boards.<board_id>.columns.<column_id>.gitevents
boards.<board_id>.columns.<column_id>.target-prompt
boards.<board_id>.columns.<column_id>.change.advance
boards.<board_id>.columns.<column_id>.archive
```

60 chaves estruturais. Esta lista é o `CHAVES_CONFIGURACAO_CONHECIDAS` fixo de
`tests/test_catalogo_configuracao.py` (padrão `REQUIRED_KEYS` de
`test_versions_env.py`). Se uma chave nova for adicionada ao motor no futuro
sem entrar nesta lista e no catálogo, isso é exatamente a divergência que
RN-09 (gatilho de atualização) deve capturar — manutenção da lista é
responsabilidade de quem altera `config.py` dali em diante, não desta issue.

### 2.4 Classificação do que sai do `README.md` (fecha CA-5 / RF-06, sem reabrir RN-01)

O próprio corpo da issue, em "Contexto e problema", já nomeia os seis blocos de
mecânica interna que poluem a porta de entrada hoje: **laço principal de
execução**, **seleção e reexecução de tarefas**, **otimização de
sincronização**, **limites de taxa**, **proteção de estado interno** e
**relatos de incidentes passados**. Mapeados às seções atuais do `README.md`
(nomes de heading podem mudar na reescrita; o teste usa padrão, não heading
fixo):

| Bloco citado na issue | Seção(ões) atuais |
|---|---|
| Laço principal de execução | `## Loop Principal`, `### sleep_time` |
| Seleção e reexecução de tarefas | `## Seleção de Tarefas (keep_task)` e subseções (cooldown, limitador de reexecuções, resolução automática de bloqueios) |
| Otimização de sincronização | `## Otimização de Sincronização` e subseções (fullsync, gatilho de par recíproco, sub-issues sem coluna, isolamento de IDs) |
| Limites de taxa | `## Rate Limit (GitHub)` e subseções (Detecção, Throttle, Penalty) |
| Proteção de estado interno | `### Proteção de estado interno` |
| Relatos de incidentes passados | qualquer heading "Incidente:"/"Incidente resolvido:" e menções a "post-mortem" |

Este é o **deny-list mínimo e não-ambíguo** verificado em CT-08/CT-09: tudo que
já era nomeado como mecânica interna pelo próprio autor do escopo. O restante
do `README.md` (ex.: `## Execução de Agentes` — `gitevents`, `agent-hub`,
`agent_timeout_seg`, limitador de consumo — ou `## Anotações no body`) é
conteúdo "misto" na forma de RN-01 e a classificação fina de cada subseção é
decisão do desenvolvimento/tech lead no inventário (RF-07), não deste teste —
evita-se aqui reabrir uma decisão editorial que a issue não fechou.

### 2.5 CT-06/CT-11 do corpo (comunicação de versão): o que é automatizável e o que não é

"Auditar as dez mudanças mais recentes na linha principal" depende de
julgamento humano sobre elegibilidade (RN-05, "mudança com efeito de produto")
e de histórico real do git no momento em que o teste roda — não é uma
asserção estável para pytest (o próprio corpo da issue identifica o
versionamento histórico inconsistente como risco à "aplicação retroativa").
Fica dividido em:

- **Automatizável e exigido por este documento:** o *processo* existe e tem
  formato correto (CT-20/21); um *validador* aplica a regra de estilo/fronteira
  a uma nota candidata (CT-22/23, sintético + notas reais já publicadas em
  `NOVIDADES.md`); a versão corrente do motor tem nota correspondente em
  `NOVIDADES.md` (CT-24 — fecha o "marca de versão defasada" do risco listado,
  de forma determinística, sem depender de `git log`); um validador de
  auditoria (`auditar_mudancas_elegiveis`) é testado com uma lista sintética de
  mudanças e notas (CT-39).
- **Não automatizável em pytest, fica para evidência de processo:** aplicar de
  fato a auditoria às dez mudanças reais mais recentes do repositório
  (CT-25, marcado **manual/processo** — evidência fica registrada pela própria
  prática do processo documentado, não por uma asserção de teste que seria
  instável no tempo).

---

## 3. Rastreabilidade (CA → casos)

| Critério de aceitação | Caso(s) de teste |
|---|---|
| CA-1 (entende valor/capacidades/limites/pré-requisitos) | CT-01, CT-02, CT-11 |
| CA-2 (execução local sem ajuda, antes do container) | CT-03, CT-04 |
| CA-3 (container como alternativa, link ao runbook) | CT-03, CT-05 |
| CA-4 (localiza configuração e exemplos) | CT-06, CT-07 |
| CA-5 (README auditado sem conteúdo de desenvolvimento) | CT-08, CT-09, CT-10 |
| CA-6 (nota pública curada no mesmo momento, sem artefato interno) | CT-20, CT-21, CT-23, CT-24, CT-25, CT-39 |
| CA-7 (nota curta/informal/informativa/de benefício) | CT-20, CT-22 |
| CA-8 (inventário com fonte canônica/responsável/gatilho) | CT-16, CT-17, CT-18, CT-19, CT-37 |
| CA-9 (100% das chaves descritas) | CT-12, CT-13, CT-14, CT-15 |
| CA-10 (manual verificável objetivamente) | CT-31, CT-32, CT-33, CT-38 |
| CA-11 (gate reprova com motivo registrado) | CT-26, CT-27, CT-28, CT-29, CT-30 |
| CA-12 (baseline condicionado a RN-11, decisão registrada) | CT-34, CT-35, CT-36 |

Cenários obrigatórios do corpo (CT-01..CT-12 do corpo) → casos deste documento:
corpo CT-01→CT-01/02/11; corpo CT-02→CT-03/04; corpo CT-03→CT-03/05; corpo
CT-04→CT-06/07; corpo CT-05→CT-08/09/10; corpo CT-06→CT-20/21/24; corpo
CT-07→CT-27; corpo CT-08→CT-28; corpo CT-09→CT-12/13; corpo CT-10→CT-16/17;
corpo CT-11→CT-25/39; corpo CT-12→CT-34/35/36.

---

## 4. Arquivos de teste previstos (a criar pelo desenvolvimento)

- `tests/test_readme_porta_entrada.py` — CT-01..CT-10
- `tests/test_catalogo_configuracao.py` — CT-12..CT-15
- `tests/test_inventario_editorial.py` — CT-16..CT-19, CT-37
- `tests/test_comunicacao_versao.py` — CT-20..CT-25, CT-39
- `tests/test_gate_revisao.py` — CT-26..CT-30
- `tests/test_manual_padroes.py` — CT-31..CT-33, CT-38
- `tests/test_baseline_avaliacao.py` — CT-34..CT-36
- `tests/_editorial_helpers.py` — helpers compartilhados (parse de registros
  `chave: valor`, extração de seções Markdown por heading, validadores puros)

Convenções reaproveitadas de `tests/_vitrine_helpers.py`: `secao(texto, titulo)`
retorna o corpo de uma seção Markdown pelo título do heading (ou `None`);
`linhas_nao_vazias(texto)`; `tokens_em_crase(texto)`. Reutilizar, não duplicar
— import de `tests._vitrine_helpers` onde já servir, novo helper só para o que
for específico de governança editorial.

---

## 5. Casos de teste

### CT-01 — README comunica valor, capacidades e pré-requisitos sem exigir o código

- **CA de origem:** CA-1 (RF-01)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_intro_comunica_valor_e_capacidades`
- **Pré-condição:** `README.md` reescrito.
- **Passos:**
  1. Extrair o bloco entre o título `# Esteira Agêntica` e o primeiro `## `.
  2. Verificar presença da seção `## Requisitos` (ou `## Pré-requisitos`) e que
     ela tem ao menos 3 itens.
- **Resultado esperado:** o bloco de abertura tem ≥ 40 palavras; cita, em
  linguagem natural (case-insensitive), ao menos um termo de capacidade
  (`orquestr|automatiz|executa agentes|board`) e nenhum termo de mecânica
  interna da §2.4; a seção de pré-requisitos existe e não está vazia.
- **Observações:** não exige heading literal "Valor"/"Capacidades" — testa o
  conteúdo, não o rótulo exato do heading, para não prescrever redação.

### CT-02 — README tem seção explícita de limites

- **CA de origem:** CA-1 (RF-01)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_secao_limites_presente`
- **Pré-condição:** idem CT-01.
- **Passos:**
  1. Buscar heading que corresponda a `limit|limitaç|fora do escopo|não faz`
     (case-insensitive) em qualquer nível (`##`/`###`).
- **Resultado esperado:** existe ao menos uma seção dedicada a limites/escopo,
  com ≥ 2 itens de lista, visível a partir do README sem navegar para outro
  documento.
- **Observações:** pode reaproveitar/linkar o "Fora de escopo" desta issue
  como fonte de conteúdo, mas o teste verifica a seção no README, não a fonte.

### CT-03 — Execução local é apresentada antes do container (RN-08, regressão)

- **CA de origem:** CA-2, CA-3 (RN-08; corpo CT-02/CT-03)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_execucao_local_antes_do_container`
- **Pré-condição:** seção `## Uso` do README.
- **Passos:**
  1. Localizar o índice de caractere de uma subseção de execução local
     (`execução local|rodar localmente|python -m src` como heading) e de uma
     subseção de container/Docker.
- **Resultado esperado:** o índice da subseção local é menor que o da subseção
  de container; ambas existem.
- **Observações:** hoje já é verdade (`### Execução local (Python)` antes de
  `### Execução via Docker Compose`) — este caso é guarda de regressão.

### CT-04 — Jornada de execução local é autossuficiente

- **CA de origem:** CA-2 (RF-02)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_execucao_local_autossuficiente`
- **Pré-condição:** subseção de execução local.
- **Passos:**
  1. Verificar presença, em ordem, de: instalação de dependência
     (`pip install`), criação/uso do `pipe.yml` (referência, não exemplo
     completo — ver CT-07), variável `PIPE_SSH_KEY_FILE`, e o comando de
     execução (`python -m src`).
- **Resultado esperado:** os 4 elementos presentes na subseção local, sem
  nenhum deles remeter a "ver código-fonte" ou a um arquivo fora de
  `README.md`/`doc/configuracao/referencia.md`/`exemplos/`.
- **Observações:** replica o espírito de `TestAC03PassoAPasso` de
  `test_docker_runbook.py`, mas para a jornada local.

### CT-05 — Container aparece como alternativa suportada com link ao runbook

- **CA de origem:** CA-3 (RF-03)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_container_alternativa_com_link_runbook`
- **Pré-condição:** subseção de container.
- **Passos:**
  1. Verificar que a subseção cita a palavra "alternativa" (ou equivalente) e
     contém um link Markdown para `doc/runbook/docker.md`.
- **Resultado esperado:** link presente e resolve a arquivo existente
  (`(doc/runbook/docker.md)` ⇒ `Path("doc/runbook/docker.md").exists()`).
- **Observações:** reaproveita o link já existente hoje
  (`[`doc/runbook/docker.md`](doc/runbook/docker.md)`); apenas protege contra
  regressão e checa a existência real do arquivo (link não quebrado).

### CT-06 — README localiza configuração e exemplos

- **CA de origem:** CA-4 (RF-04)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_links_configuracao_e_exemplos`
- **Pré-condição:** README reescrito.
- **Passos:**
  1. Buscar link Markdown para `doc/configuracao/referencia.md`.
  2. Buscar link Markdown para `exemplos/` (ou para os pacotes individuais).
- **Resultado esperado:** ambos os links existem e resolvem a caminhos reais.
- **Observações:** a seção "Exemplos" já existe e já linka `exemplos/*/USO.md`
  — preservar; o novo é o link ao catálogo.

### CT-07 — Seção Configuração do README é enxuta e remete ao catálogo (fonte única)

- **CA de origem:** CA-4 (RNF-05; RN-09 — fonte canônica única)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_secao_configuracao_enxuta`
- **Pré-condição:** seção `## Configuração` do README.
- **Passos:**
  1. Medir o número de linhas da seção (do heading até o próximo `## `).
  2. Verificar link para `doc/configuracao/referencia.md`.
- **Resultado esperado:** seção ≤ 60 linhas (hoje tem ~106, cheia de
  comentário por chave — o detalhe item a item migra para o catálogo); contém
  o link ao catálogo; mantém só um exemplo mínimo de `pipe.yml` (não um
  exemplo com todas as chaves comentadas).
- **Observações:** fecha a duplicação de fonte apontada pelo risco de
  manutenção (RN-09) — hoje o exemplo comentado no README e o futuro catálogo
  seriam duas fontes do mesmo fato.

### CT-08 — README não contém as seções de mecânica interna nomeadas pela issue

- **CA de origem:** CA-5 (RF-06, RN-04)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_sem_mecanica_interna`
- **Pré-condição:** README reescrito.
- **Passos:**
  1. Para cada termo do deny-list da §2.4 (`Loop Principal`, `sleep_time`,
     `keep_task`, `Otimização de Sincronização`, `Rate Limit`, `Proteção de
     estado interno`), buscar heading ou menção textual destacada
     (case-insensitive).
- **Resultado esperado:** zero ocorrências como heading; o termo pode aparecer
  apenas dentro de um link para o documento interno de destino (ex.: texto de
  um link "ver CONTEXT.md"), nunca como conteúdo explicativo próprio.
- **Observações:** teste negativo simétrico ao de `test_vitrine_estrutura.py
  ::test_nenhum_tema_extra`. Não força remoção de `## Execução de Agentes` nem
  de `## Anotações no body` (conteúdo misto — decisão do inventário, §2.4).

### CT-09 — README não contém relato de incidente nem identificador de trabalho

- **CA de origem:** CA-5 (RF-06; aplicação da lógica de RN-03/RN-04 ao README)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_sem_incidentes_e_identificadores`
- **Pré-condição:** README reescrito.
- **Passos:**
  1. Buscar heading contendo "incidente" (case-insensitive) em qualquer nível.
  2. Buscar "post-mortem"/"post mortem" em qualquer lugar do texto.
  3. Buscar padrão `#\d{2,4}` (identificador de issue) fora de blocos de código.
- **Resultado esperado:** zero ocorrências nos três casos.
- **Observações:** o README atual tem `### Incidente: sub-issues propagadas
  entre boards (#88/#98/#99/#106)` e referências a outros `#NNN` espalhadas —
  este teste falha hoje de propósito (é o estado "antes"; passa só após a
  reescrita).

### CT-10 — README é enxuto (RNF-05)

- **CA de origem:** CA-5 (RNF-05)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_readme_porta_entrada.py::test_readme_enxuto`
- **Pré-condição:** README reescrito.
- **Passos:**
  1. Contar linhas totais de `README.md`.
- **Resultado esperado:** ≤ 600 linhas (hoje 1415; a remoção dos 6 blocos da
  §2.4 mais a redução da seção Configuração — CT-07 — já cobrem a maior parte
  da diferença).
- **Observações:** número fixado para dar um alvo objetivo e verificável a
  "enxuta" (RNF-05), sem prescrever exatamente o que fica — só o resultado.

### CT-11 — Avaliador externo real lê o README sem ajuda (manual)

- **CA de origem:** CA-1 (corpo CT-01; RF-13 quando há baseline — RN-11)
- **Tipo:** manual
- **Arquivo/alvo:** registro de baseline/pós-teste (`doc/governanca-editorial/baseline-avaliacao.md`
  ou registros individuais) quando há participantes confirmados; caso
  contrário, evidenciado apenas pela revisão do gate de conteúdo (RF-12) sobre
  o próprio README.
- **Pré-condição:** README publicado; participante real (se houver, RN-11).
- **Passos:**
  1. Participante lê somente o README.
  2. Relata, sem consultar código, valor/capacidades/limites/pré-requisitos.
- **Resultado esperado:** relato correto nos 4 pontos, sem ajuda.
- **Observações:** não bloqueia o pytest; ver CT-34/35/36 para a condicional
  de RN-11.

### CT-12 — Catálogo de configuração: toda entrada tem os 8 campos do contrato

- **CA de origem:** CA-9 (RF-08)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_catalogo_configuracao.py::test_entradas_tem_oito_campos`
- **Pré-condição:** `doc/configuracao/referencia.md` existe.
- **Passos:**
  1. Parsear o documento em blocos por entrada (um bloco por `chave:`).
  2. Para cada bloco, verificar `chave`, `descricao`, `tipo`, `obrigatoriedade`,
     `default`, `valores_aceitos`, `efeito_ausencia`, `exemplo`.
- **Resultado esperado:** os 8 campos presentes e não vazios em toda entrada;
  `tipo` ∈ `{string, inteiro, booleano, lista, mapa}`; `obrigatoriedade` ∈
  `{obrigatória, opcional}`.

### CT-13 — Catálogo cobre 100% das chaves conhecidas do motor

- **CA de origem:** CA-9 (RNF-06)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_catalogo_configuracao.py::test_cobertura_completa`
- **Pré-condição:** lista `CHAVES_CONFIGURACAO_CONHECIDAS` (§2.3, 60 itens) no
  próprio arquivo de teste; catálogo parseado.
- **Passos:**
  1. Extrair o conjunto de valores de `chave:` do catálogo.
  2. Comparar com `CHAVES_CONFIGURACAO_CONHECIDAS`.
- **Resultado esperado:** toda chave da lista canônica tem entrada no catálogo
  (subconjunto ⊆ catálogo); nenhuma chave da lista está ausente — reportar
  exatamente as ausentes na mensagem de falha (padrão `assert not ausentes, ...`
  de `test_versions_env.py::test_chaves_obrigatorias_presentes`).
- **Observações:** teste **determinístico**, não precisa reler `config.py` em
  runtime — a lista é fixa e versionada com o teste; manutenção futura da
  lista é responsabilidade de quem adicionar chave nova (nota da §2.3).

### CT-14 — Catálogo não duplica chave e não lista chave fora da lista canônica sem marcação

- **CA de origem:** CA-9 (RF-08, consistência)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_catalogo_configuracao.py::test_sem_duplicatas_e_sem_chave_estranha`
- **Pré-condição:** idem CT-13.
- **Passos:**
  1. Verificar que não há dois blocos com o mesmo valor de `chave:`.
  2. Para toda `chave:` do catálogo fora de `CHAVES_CONFIGURACAO_CONHECIDAS`,
     verificar que o bloco tem marcação explícita `status: obsoleta` ou
     `status: experimental`.
- **Resultado esperado:** zero duplicatas; toda chave extra justificada.

### CT-15 — Exemplo de cada entrada do catálogo é YAML válido e compatível com o tipo declarado

- **CA de origem:** CA-9 (RNF-03 — correção do conteúdo)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_catalogo_configuracao.py::test_exemplo_valido_por_tipo`
- **Pré-condição:** idem CT-13.
- **Passos:**
  1. Parsear o campo `exemplo` de cada bloco com `yaml.safe_load`.
  2. Conferir o tipo Python resultante contra `tipo` declarado
     (`string→str`, `inteiro→int` não-bool, `booleano→bool`, `lista→list`,
     `mapa→dict`).
- **Resultado esperado:** parse sem erro; tipo resultante compatível.
- **Observações:** não exige que o exemplo seja aceito por `config.check_config()`
  isoladamente (a chave sozinha não forma um `pipe.yml` válido) — só a forma.

### CT-16 — Inventário existe com os 6 campos por item

- **CA de origem:** CA-8 (RF-07)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_inventario_editorial.py::test_itens_tem_seis_campos`
- **Pré-condição:** `doc/governanca-editorial/inventario-conteudo-publico.md`.
- **Passos:**
  1. Parsear por item (`documento:` inicia bloco).
  2. Verificar `documento`, `audiencia`, `sensibilidade`, `fonte_canonica`,
     `responsavel`, `gatilho_atualizacao`.
- **Resultado esperado:** os 6 campos presentes e não vazios; `audiencia` ∈
  `{publico, interno, misto}`; `sensibilidade` ∈ `{baixa, media, alta}`.

### CT-17 — Todo documento público priorizado está no inventário

- **CA de origem:** CA-8 (RN-09)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_inventario_editorial.py::test_cobertura_documentos_publicos`
- **Pré-condição:** inventário parseado.
- **Passos:**
  1. Verificar presença de `documento:` para cada um de: `README.md`,
     `doc/configuracao/referencia.md`, `doc/governanca-editorial/manual-padroes-documentacao.md`,
     `doc/governanca-editorial/gate-revisao.md`, `NOVIDADES.md`,
     `doc/runbook/docker.md`, `exemplos/minimalista/USO.md`,
     `exemplos/referencia-hipotetica/USO.md`.
- **Resultado esperado:** todos presentes no inventário, com `audiencia:
  publico` (exceto se houver decisão registrada em contrário).

### CT-18 — Item incompleto é detectado (comportamento em falha)

- **CA de origem:** CA-8 (RN-09; tabela "Comportamento em falha")
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_inventario_editorial.py::test_item_sem_fonte_responsavel_gatilho_e_reportado`
- **Pré-condição:** validador `validar_item_inventario(dict)` em
  `tests/_editorial_helpers.py`.
- **Passos:**
  1. Sintético: item completo → `[]` (válido).
  2. Remover `fonte_canonica` → erro citando o campo.
  3. Remover `responsavel` → erro citando o campo.
  4. Remover `gatilho_atualizacao` → erro citando o campo.
  5. Rodar o validador sobre todo item real do inventário.
- **Resultado esperado:** (1) válido; (2)-(4) cada reporta exatamente o campo
  ausente; itens reais do inventário passam.

### CT-19 — Audiência "misto" exige decisão registrada

- **CA de origem:** CA-8 (RF-05, RN-01 — "conteúdo misto é decidido caso a caso")
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_inventario_editorial.py::test_misto_exige_decisao`
- **Pré-condição:** validador `validar_item_inventario`.
- **Passos:**
  1. Sintético: `audiencia: misto` sem campo `decisao` → inválido.
  2. `audiencia: misto` com `decisao` preenchida (≥ 20 caracteres,
     justificando a finalidade) → válido.
- **Resultado esperado:** (1) reporta "misto" exige `decisao`; (2) válido.

### CT-20 — Processo de comunicação de versão documentado com os 4 campos

- **CA de origem:** CA-6, CA-7 (RF-09)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_comunicacao_versao.py::test_processo_documenta_campos`
- **Pré-condição:** `doc/governanca-editorial/comunicacao-versao.md`.
- **Passos:**
  1. Verificar bloco de formato com `versao`, `data`, `destaques`, `acao`.
  2. Verificar que o documento declara `NOVIDADES.md` como canal único.
  3. Verificar que o documento declara explicitamente que a nota é escrita em
     linguagem de benefício e nunca uma lista tecnicista (RN-07, citado).
- **Resultado esperado:** campos presentes; canal único nomeado; regra de
  estilo declarada.

### CT-21 — Processo declara publicação na mesma mudança (RF-10)

- **CA de origem:** CA-6 (RF-10)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_comunicacao_versao.py::test_publicacao_mesmo_momento_declarada`
- **Pré-condição:** idem CT-20.
- **Passos:**
  1. Buscar declaração de que a nota é preparada/commitada junto com a
     mudança que ela comunica (mesmo commit/PR/merge na linha principal).
- **Resultado esperado:** declaração presente e inequívoca (não "depois",
  não "periodicamente").

### CT-22 — Validador de nota aplica a regra de estilo (RN-07)

- **CA de origem:** CA-7 (RN-07; corpo CT-08)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_comunicacao_versao.py::test_validador_estilo_nota`
- **Pré-condição:** `avaliar_gate_revisao(texto, tipo="nota_versao")` em
  `tests/_editorial_helpers.py` (ver §2.2 do gate).
- **Passos:**
  1. Nota curta (≤ 500 caracteres), em prosa, com linguagem de benefício →
     `[]` (aprovada).
  2. Nota com lista de bullets técnicos (`- Corrigido: NullPointerException em
     ...`) → reprovada citando "registro editorial inadequado" / "lista
     tecnicista".
  3. Nota com > 800 caracteres → reprovada citando "longa demais".
  4. Rodar sobre toda entrada real de `NOVIDADES.md` → todas aprovadas.
- **Resultado esperado:** (1) e (4) aprovadas; (2) e (3) reprovadas com motivo.

### CT-23 — Validador de nota rejeita artefato de processo interno (RN-03)

- **CA de origem:** CA-6 (RN-03)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_comunicacao_versao.py::test_validador_rejeita_artefato_interno`
- **Pré-condição:** idem CT-22.
- **Passos:**
  1. Nota citando `#313`, `épico`, `história #N` → reprovada citando o
     artefato.
  2. Nota sem nenhum identificador → aprovada (quanto a este critério).
  3. Rodar sobre `NOVIDADES.md` real → nenhuma entrada cita identificador.
- **Resultado esperado:** (1) reprovada apontando o artefato citado; (2)
  aprovada; (3) suíte real limpa.

### CT-24 — Versão corrente do motor tem nota pública correspondente

- **CA de origem:** CA-6 (RNF-04; fecha o risco "marca de versão defasada")
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_comunicacao_versao.py::test_versao_corrente_tem_nota`
- **Pré-condição:** `src.core.version.VERSION`; `NOVIDADES.md` parseado.
- **Passos:**
  1. Buscar entrada com `versao: <VERSION>` em `NOVIDADES.md`.
- **Resultado esperado:** entrada existe.
- **Observações:** determinístico e local — não depende de `git log`; é o
  equivalente, para a nota pública, do que `test_version_bump.py` já faz para
  `CONTEXT.md`.

### CT-25 — Auditoria das mudanças elegíveis recentes (manual/processo)

- **CA de origem:** CA-6 (corpo CT-11; RNF-04)
- **Tipo:** manual/processo
- **Arquivo/alvo:** processo descrito em `doc/governanca-editorial/comunicacao-versao.md`;
  evidência é a prática (toda mudança elegível desde a adoção do processo tem
  nota em `NOVIDADES.md`), não uma asserção pytest.
- **Pré-condição:** processo em vigor a partir desta entrega.
- **Passos:**
  1. A cada merge elegível na linha principal, confirmar nota publicada no
     mesmo momento.
- **Resultado esperado:** 100% das mudanças elegíveis desde a adoção do
  processo têm nota; aplicação é prospectiva (ver §2.5 — não retroage sobre o
  histórico anterior a esta issue).

### CT-26 — Contrato do gate documentado com os 4 campos

- **CA de origem:** CA-11 (RF-12)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_gate_revisao.py::test_contrato_tem_quatro_campos`
- **Pré-condição:** `doc/governanca-editorial/gate-revisao.md`.
- **Passos:**
  1. Verificar `entrada`, `criterios`, `saida_aprovado`, `saida_reprovado`.
  2. Verificar que `criterios` enumera, no mínimo, os 5 critérios do corpo da
     issue (fronteira público/interno, ausência de artefato interno, ausência
     de promessa de retorno financeiro, instruções corretas/seguras, registro
     editorial adequado).
- **Resultado esperado:** campos presentes; os 5 critérios citados.

### CT-27 — Gate reprova conteúdo que cita artefato interno, com motivo

- **CA de origem:** CA-11 (corpo CT-07; comportamento em falha, linha 1)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_gate_revisao.py::test_reprova_artefato_interno`
- **Pré-condição:** `avaliar_gate_revisao(texto, tipo)`.
- **Passos:**
  1. Conteúdo citando identificador de issue/épico/história → reprovado,
     motivo aponta exatamente o artefato citado (não uma mensagem genérica).
- **Resultado esperado:** `saida_reprovado` com motivo acionável.

### CT-28 — Gate reprova registro tecnicista ou longo demais, com motivo

- **CA de origem:** CA-11 (corpo CT-08)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_gate_revisao.py::test_reprova_registro_tecnicista`
- **Pré-condição:** idem CT-27; reaproveita CT-22 (mesma função, `tipo="nota_versao"`).
- **Passos:** idênticos a CT-22 (2) e (3), verificando aqui o motivo registrado
  pelo gate, não só a reprovação.
- **Resultado esperado:** motivo cita a regra de estilo violada.

### CT-29 — Gate reprova promessa de retorno financeiro

- **CA de origem:** CA-11 (critério "ausência de promessa de retorno
  financeiro"; fora de escopo "prometer retorno financeiro... antes do
  baseline")
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_gate_revisao.py::test_reprova_promessa_financeira`
- **Pré-condição:** idem CT-27.
- **Passos:**
  1. Conteúdo com "economize X% em suporte"/"retorno garantido"/"reduza custos
     em Y" → reprovado citando a promessa.
  2. Conteúdo descrevendo capacidade sem number de economia/retorno →
     aprovado quanto a este critério.
- **Resultado esperado:** (1) reprovado; (2) aprovado.

### CT-30 — Gate aprova conteúdo que respeita todos os critérios

- **CA de origem:** CA-11 (comportamento no caminho feliz)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_gate_revisao.py::test_aprova_conteudo_conforme`
- **Pré-condição:** idem CT-27.
- **Passos:**
  1. Rodar `avaliar_gate_revisao` sobre o `README.md` final, `NOVIDADES.md`
     (cada entrada) e `doc/configuracao/referencia.md`.
- **Resultado esperado:** `[]` (aprovado) para todos — fecha o laço: os
  próprios artefatos públicos desta issue passam pelo gate que esta issue
  define.

### CT-31 — Manual de padrões é verificável objetivamente

- **CA de origem:** CA-10 (RF-11)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_manual_padroes.py::test_regras_tem_criterio_verificavel`
- **Pré-condição:** `doc/governanca-editorial/manual-padroes-documentacao.md`.
- **Passos:**
  1. Parsear a lista de regras do manual (cada regra como item numerado ou
     bullet de nível 1 dentro de uma seção "## Regras").
  2. Para cada regra, verificar que ela contém um critério de aceite/rejeição
     objetivo (padrão: a frase contém "deve"/"não deve"/"sempre"/"nunca" +
     uma condição checável, não apenas uma preferência de estilo vaga).
- **Resultado esperado:** toda regra tem critério objetivo; zero regras
  redigidas como sugestão (sem "deve"/"nunca"/equivalente).

### CT-32 — Manual não contradiz as decisões já fixadas nesta issue

- **CA de origem:** CA-10 (RN-08, RN-07, RNF-05 — coerência)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_manual_padroes.py::test_coerente_com_regras_de_negocio_da_issue`
- **Pré-condição:** idem CT-31.
- **Passos:**
  1. Verificar que o manual declara: execução local antes do container
     (RN-08); nota de versão nunca lista tecnicista (RN-07); porta de entrada
     concisa, sem conteúdo de desenvolvimento (RNF-05/RN-04); fonte canônica
     única por documento (RN-09).
- **Resultado esperado:** as 4 regras presentes e sem contradição textual.

### CT-33 — Checklist do manual aplicado ao README final não aponta divergência

- **CA de origem:** CA-10 (RF-11, aplicação prática)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_manual_padroes.py::test_checklist_aplicado_ao_readme`
- **Pré-condição:** manual parseado; `README.md` final.
- **Passos:**
  1. Para cada regra objetiva extraída em CT-31 que seja mecanicamente
     checável sobre Markdown (ex.: "não deve conter heading de incidente"),
     aplicar ao `README.md`.
- **Resultado esperado:** zero divergências — o manual e o README resultante
  desta própria issue são o primeiro caso de conformidade.

### CT-34 — Sem participantes confirmados: decisão "sem baseline disponível" registrada

- **CA de origem:** CA-12 (RN-11, ramo sem confirmação)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_baseline_avaliacao.py::test_decisao_sem_participantes`
- **Pré-condição:** `doc/governanca-editorial/baseline-avaliacao.md`.
- **Passos:**
  1. Ler o campo de decisão de continuidade.
- **Resultado esperado:** quando não há registro de participantes confirmados
  antes do início desta etapa, o campo contém exatamente
  `decisao_continuidade: sem baseline disponível`; o documento declara
  explicitamente que os demais entregáveis constituem a entrega mínima
  completa (RN-11).
- **Observações:** este é o ramo esperado nesta execução, salvo confirmação
  explícita de participantes antes do início da etapa de Desenvolvimento —
  ver anotação na issue.

### CT-35 — Com participantes confirmados: registro de baseline/pós-teste completo

- **CA de origem:** CA-12 (RF-13, RNF-01, RNF-02 — ramo condicional)
- **Tipo:** unitário (condicional — `pytest.skip` se o ramo não se aplica)
- **Arquivo/alvo:** `tests/test_baseline_avaliacao.py::test_registro_baseline_pos_teste`
- **Pré-condição:** só roda (não faz `skip`) se
  `doc/governanca-editorial/baseline-avaliacao.md` declarar participantes
  confirmados.
- **Passos:**
  1. Verificar campos de baseline (taxa de sucesso sem ajuda, tempo mediano)
     e de pós-teste nos mesmos termos.
  2. Verificar regra de decisão: ≥ 4 de 5 concluem as três jornadas sem ajuda;
     comparação com baseline (melhora de sucesso e redução de tempo mediano,
     sem regressão quando o baseline já está no teto).
- **Resultado esperado:** campos completos; regra de decisão aplicada e
  resultado (`continuar`/`interromper`) registrado com base nela.
- **Observações:** espelha o padrão de `pytest.skip` de
  `test_vitrine_governanca.py::test_registro_real_de_reavaliacao_apos_producao`
  para condição que só vale após um gatilho específico.

### CT-36 — Execução do teste com participantes reais (manual)

- **CA de origem:** CA-12 (corpo CT-12)
- **Tipo:** manual
- **Arquivo/alvo:** registros individuais referenciados por
  `doc/governanca-editorial/baseline-avaliacao.md`.
- **Pré-condição:** participantes confirmados antes do início da etapa de
  Documentação (RN-11).
- **Passos:**
  1. Cada participante percorre as três jornadas (CT-01/02/03 do corpo) a
     partir do README, sem ajuda.
  2. Registrar sucesso/falha e tempo por participante.
- **Resultado esperado:** dados brutos por participante, usados para compor o
  registro agregado de CT-35.

### CT-37 — Reclassificação por finalidade, não por localização (RN-02)

- **CA de origem:** CA-8 (RN-02; comportamento em falha, linha 4)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_inventario_editorial.py::test_classificacao_por_finalidade_nao_localizacao`
- **Pré-condição:** inventário parseado.
- **Passos:**
  1. Para cada item cujo `documento` esteja sob `doc/runbook/` ou `exemplos/`
     (pastas já públicas) mas cuja finalidade seja de desenvolvimento (se
     houver algum caso assim no inventário), confirmar `audiencia: interno`
     ou `misto` com decisão — nunca herdado automaticamente de estar em pasta
     pública.
  2. Caso simétrico: item sob `doc/architecture/`, `doc/incidente/`,
     `doc/product/` ou `doc/quality/` (pastas majoritariamente internas) não
     pode estar marcado `audiencia: publico` sem `decisao` registrada
     justificando a excecão.
- **Resultado esperado:** nenhuma classificação herdada só da pasta; toda
  exceção (pasta pública com item interno, ou vice-versa) tem `decisao`
  registrada.

### CT-38 — Alteração de documentação fora do manual é recusada até adequar-se

- **CA de origem:** CA-10 (comportamento em falha, linha 6)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_manual_padroes.py::test_alteracao_fora_do_padrao_e_recusada`
- **Pré-condição:** validador `avaliar_conformidade_manual(texto_alterado) ->
  list[str]` construído a partir das regras extraídas em CT-31 que forem
  mecanicamente checáveis.
- **Passos:**
  1. Texto sintético de `README.md` alterado que reintroduz uma seção de
     mecânica interna (ex.: heading "Loop Principal") → reprovado, motivo
     aponta o ponto de divergência frente ao manual.
  2. Texto sintético conforme → aprovado.
- **Resultado esperado:** (1) reprovado com ponto de divergência citado; (2)
  aprovado.

### CT-39 — Validador de auditoria de mudanças elegíveis (sintético)

- **CA de origem:** CA-6 (corpo CT-11; comportamento em falha, linha 3)
- **Tipo:** unitário
- **Arquivo/alvo:** `tests/test_comunicacao_versao.py::test_auditoria_mudancas_sintetica`
- **Pré-condição:** `auditar_mudancas_elegiveis(mudancas: list[dict], notas:
  list[dict]) -> list[str]` em `tests/_editorial_helpers.py`; `mudancas`:
  `[{"versao", "data", "elegivel": bool}]`; `notas`: `[{"versao", "data"}]`.
- **Passos:**
  1. Mudança elegível sem nota correspondente → reportada ("mudança elegível
     sem nota correspondente", citando a versão).
  2. Mudança elegível com nota de mesma versão e mesma data → sem relato.
  3. Mudança não elegível sem nota → sem relato (RN-05 — não elegível não
     exige nota).
  4. Mudança elegível com nota de versão correta mas data posterior → relato
     ("publicação fora do mesmo momento").
- **Resultado esperado:** (1) e (4) relatadas; (2) e (3) silenciosas.
- **Observações:** esta função é o mecanismo que, aplicado ao histórico real,
  executaria CT-25 — aqui testada apenas com dados sintéticos, por ser a parte
  determinística e estável no tempo.
