# Requisitos Funcionais — Otimizar prompts, contextos e comandos

Status: approved · Owner: requirements · Updated: 2026-08-25
Inputs: `doc/product/otimizar-prompts-contextos-comandos/analise-negocio.md`;
código-fonte (`src/core/agent.py`, `src/core/commands.py`,
`src/core/context_generator.py`, `src/core/config.py`,
`src/adapters/kiro_cli_agent.py`); histórico da issue #92 (respostas do dono
em 22 e 25/08/2026); `business-rules.md` e `glossary.md` deste mesmo diretório.

> Nenhum requisito abaixo define arquitetura, tecnologia ou nome de arquivo de
> implementação. Onde o "como" é decisão técnica, o requisito descreve apenas
> o comportamento observável exigido.

## Atores

- **Agente executor (adapter Kiro):** recebe o prompt dinâmico e o contexto
  persistente/operador antes de agir sobre a issue. Não decide o que é
  obrigatório — apenas executa com o que recebeu.
- **Esteira (núcleo `build_prompt`/`generate_context`):** compõe o prompt
  dinâmico e o contexto persistente a cada execução, a partir de `pipe.yml` e
  da task corrente (issue/coluna/board).
- **Operador da esteira:** mantém `pipe.yml` e os contextos em
  `contexts/<plataforma>/<agente>.md`; consome o benchmark e o inventário
  para decidir configuração, mas não é o dono do conteúdo deste épico quanto
  a `contexts/`.
- **Arquitetura/engenharia (consumidor deste baseline):** implementa a
  composição em camadas e o contrato de prova de carregamento a partir destes
  requisitos, sem redefini-los.
- **QA (consumidor deste baseline):** valida os gates de redução e os
  cenários de não regressão usando a matriz fixa (RF-006) e os critérios de
  aceitação abaixo.

## Dados

- **Prompt dinâmico:** string composta por `build_prompt()`; hoje contém
  cabeçalho da tarefa, regras de workdir, Git Setup, instruções de execução,
  Commit/Push, Pull Request, Cleanup, manual de anotações `@---` e transição
  de coluna. Ver glossário.
- **Contexto persistente (contexto do sistema):** conteúdo de
  `.pipe/CONTEXT.md` / `.kiro/agents/pipe_context.json`, gerado por
  `generate_context()` a partir de `pipe.yml` (restrições de sistema,
  nomeação de issues, boards/colunas, git flow/branches).
- **Contexto do operador:** conteúdo de `contexts/<plataforma>/<agente>.md`
  — fora de escopo quanto ao conteúdo (RN-003), mas dentro de escopo quanto a
  **como** é combinado com as outras camadas (duplicidade, RN-005).
- **Configuração de coluna (`pipe.yml`):** `target-prompt`, `gitevents`,
  `change`, `agent`/`agent-hub` — candidatos a revisão apenas se ligados à
  composição (RN-006). O dono já indicou intenção concreta de dividir
  `target-prompt` em objetivo (`target-prompt`) e passo a passo opcional
  (`steps-prompt`), e de expor duas granularidades de contexto —
  principal (`/context`) e secundário/sob demanda (`/knowledge`).
- **Inventário de instruções:** artefato a produzir (RF-001) que classifica
  cada trecho hoje presente no prompt/contexto por camada (política
  invariável, contexto do operador, workflow da etapa, dado da tarefa) e por
  obrigatoriedade (sempre carregada vs. sob demanda).
- **Benchmark antes/depois:** conjunto de medições (caracteres, palavras,
  tokens quando disponíveis) por cenário da matriz fixa (RF-006), na versão
  atual e na versão proposta.

## Fluxo principal (composição de uma execução)

1. A esteira seleciona uma task (`keep_task`) e chama `build_prompt` +
   `generate_context` (ou equivalente na versão simplificada).
2. A esteira classifica cada instrução candidata como obrigatória (sempre
   carregada) ou sob demanda, conforme o inventário (RF-001) e a coluna/task
   corrente.
3. A esteira monta o prompt dinâmico contendo apenas: dados da tarefa
   corrente, workflow da etapa aplicável à coluna, e — quando aplicável pelos
   critérios de RF-002 — a indicação de como acessar referências sob demanda.
4. A esteira monta o contexto persistente contendo as políticas invariáveis e
   instruções obrigatórias que não variam por tarefa.
5. O adapter recebe prompt dinâmico + contexto persistente + contexto do
   operador e os entrega ao agente executor, registrando prova de
   carregamento das instruções obrigatórias (RF-004).
6. O log de execução continua registrando `## Parâmetros`, `## Prompt` e
   `## Chat` de forma que cada bloco seja identificável sem ambiguidade
   (RF-005).

## Fluxos alternativos / exceções

- **Coluna sem nenhum comando `@---` aplicável:** a esteira não inclui o
  manual de anotações completo no prompt dinâmico (ver RF-002); a referência
  fica disponível sob demanda.
- **Adapter sem suporte a prova de carregamento:** fora de escopo — este
  épico define o contrato apenas para o adapter Kiro atual (RN-004).
- **`pipe.yml` sem os novos campos opcionais (se introduzidos):** a esteira
  mantém o comportamento equivalente ao atual (fallback), sem quebrar
  configurações existentes.

## Requisitos

### RF-001 — Inventário auditável de instruções por camada
- Descrição: o sistema deve produzir um inventário que liste cada instrução
  hoje presente no prompt dinâmico e no contexto persistente, classificada
  por: (a) camada de responsabilidade (política invariável / contexto do
  operador / workflow da etapa / dado da tarefa) e (b) obrigatoriedade
  (sempre carregada / sob demanda), com a origem no código (arquivo/função) e
  a contagem de palavras.
- Ator: Esteira (produzido por arquitetura/engenharia a partir deste
  requisito); consumido por QA e pelo próprio time de requisitos para
  validar RN-005.
- Pré-condição: acesso ao código atual de `build_prompt`,
  `generate_context` e `annotations_doc`.
- Fluxo principal: listar cada bloco (Diretório de trabalho, Git Setup,
  Executar tarefa, Commit e Push, Pull Request, Cleanup, Manual `@---`,
  Transição de coluna, Restrições de sistema, Criação de issues, Boards e
  colunas, Git flow e branches) → classificar → contar palavras → registrar
  duplicidade entre camadas sempre carregadas.
- Alternativos/exceções: bloco condicional (ex.: Git Setup só aparece para
  certos `gitevents`) é inventariado uma vez por variante relevante.
- Critérios de aceitação:
  - Dado o código atual de `build_prompt` e `generate_context`, quando o
    inventário é gerado, então todo bloco de texto hoje concatenado ao
    prompt ou ao contexto persistente aparece no inventário com camada,
    obrigatoriedade e contagem de palavras.
  - Dado o inventário completo, quando duas entradas descrevem a mesma regra
    em camadas sempre carregadas distintas, então isso é sinalizado
    explicitamente como duplicidade (insumo direto para RN-005).
- Fonte: análise de negócio, escopo aprovado "inventariar as instruções
  atuais por responsabilidade e camada" · Regras: RN-005.

### RF-002 — Manual de anotações `@---` deixa de ser sempre concatenado ao prompt
- Descrição: o sistema deve deixar de incluir incondicionalmente o manual de
  anotações completo (`annotations_doc()`, 281 palavras) no prompt dinâmico de
  toda execução; ele passa a ser disponibilizado como referência sob demanda,
  acessível ao agente quando a coluna corrente permite pelo menos um comando
  `@---` relevante à etapa.
- Ator: Esteira.
- Pré-condição: coluna e task corrente resolvidas por `keep_task`.
- Fluxo principal: esteira verifica se a coluna corrente permite algum
  comando `@---` (ex.: existe `change` configurado, ou a coluna não é
  terminal) → se sim, inclui referência/indicação de como acessar o manual
  completo, sem necessariamente concatenar o texto completo → se não, omite
  qualquer menção ao manual.
- Alternativos/exceções: se a etapa de arquitetura decidir que uma versão
  resumida (não as 281 palavras completas) deve permanecer sempre carregada
  como lembrete mínimo, essa versão resumida conta como conteúdo obrigatório
  e deve ser inventariada (RF-001) e medida (RF-006) como tal — não pode ser
  contada como "removida" se ainda for sempre carregada.
- Critérios de aceitação:
  - Dado uma coluna terminal sem `change` configurado e sem necessidade de
    `@---`, quando o prompt é composto, então o texto completo do manual de
    anotações (281 palavras) não está presente no prompt dinâmico.
  - Dado uma coluna com `change` configurado, quando o prompt é composto,
    então o agente tem acesso, direto ou por referência, aos comandos `@---`
    relevantes para reportar transição/relações — sem perda de capacidade
    frente ao comportamento atual.
  - Dado o mesmo cenário nas versões antes/depois, quando medido o total de
    palavras do manual sempre carregado, então o resultado da versão depois é
    menor que 281 palavras por execução comparável (ou zero, se movido
    inteiramente para sob demanda).
- Fonte: resposta do dono, item 1 (25/08/2026): "todas as colunas podem ter
  algum evento de comando (...) existe um gerador de contexto (...)
  introduzir lá alguns conceitos poderia ajudar a reduzir no prompt" ·
  Regras: RN-001, RN-002, RN-005.

### RF-003 — Separação de objetivo e passo a passo da etapa
- Descrição: o sistema deve permitir configurar, por coluna, o objetivo da
  tarefa (`target-prompt`) separadamente do passo a passo procedimental
  (novo campo opcional, ex.: `steps-prompt`), de forma que o texto de
  procedimento longo não infle o campo de objetivo.
- Ator: Operador (configura `pipe.yml`); Esteira (compõe o prompt a partir
  dos dois campos).
- Pré-condição: coluna configurada em `pipe.yml`.
- Fluxo principal: operador define `target-prompt` curto (objetivo) e,
  quando necessário, `steps-prompt` (passo a passo) → esteira compõe o
  prompt dinâmico usando ambos, mantendo a distinção visível para o agente.
- Alternativos/exceções: coluna sem `steps-prompt` definido mantém
  comportamento atual (apenas objetivo, sem passo a passo adicional).
- Critérios de aceitação:
  - Dado uma coluna com `target-prompt` e `steps-prompt` definidos, quando o
    prompt é composto, então ambos aparecem no prompt em seções
    distinguíveis (objetivo vs. procedimento).
  - Dado uma coluna sem `steps-prompt`, quando o prompt é composto, então o
    comportamento é equivalente ao atual (apenas objetivo).
  - Dado uma configuração de coluna existente sem o novo campo, quando o
    `pipe.yml` é validado, então a validação não falha por ausência do campo
    opcional.
- Fonte: resposta do dono, item 5 (25/08/2026) · Regras: RN-006.

### RF-004 — Contrato de prova de carregamento das instruções obrigatórias
- Descrição: o sistema deve expor uma verificação determinística, executável
  no fluxo de execução do agente, de que as instruções classificadas como
  obrigatórias (RF-001) foram de fato compostas e passadas ao processo do
  adapter Kiro antes do disparo — não apenas que o arquivo-fonte existe em
  disco.
- Ator: Esteira / Adapter Kiro.
- Pré-condição: inventário de instruções obrigatórias (RF-001) e mecanismo de
  injeção do adapter definidos.
- Fluxo principal: antes (ou imediatamente após) o disparo do processo do
  agente, a esteira verifica que o conteúdo obrigatório corrente está
  presente no argumento/entrada efetivamente passado ao adapter → registra
  essa verificação de forma consultável (log ou equivalente).
- Alternativos/exceções: se a verificação falhar, a execução não deve
  proceder silenciosamente como se as instruções tivessem sido entregues —
  o comportamento exato de falha (abortar vs. registrar e seguir) é decisão
  de arquitetura, mas deve haver visibilidade equivalente ao guard atual de
  `_assert_no_protected`.
- Critérios de aceitação:
  - Dado um conjunto de instruções obrigatórias vigente, quando uma execução
    do agente Kiro é disparada, então existe um registro (auditável sem
    acesso a estado protegido) de que essas instruções foram compostas e
    entregues ao processo do adapter nessa execução.
  - Dado que o conteúdo obrigatório muda (ex.: `pipe.yml` é atualizado),
    quando a próxima execução ocorre, então a prova de carregamento reflete o
    conteúdo atualizado, não uma versão em cache desatualizada.
  - Dado o mesmo mecanismo, quando perguntado "o adapter recebeu X
    instrução nesta execução", então a resposta pode ser obtida sem inspecionar
    manualmente o binário/processo do adapter.
- Fonte: análise de negócio, gate de sucesso 4 · Regras: RN-004.

### RF-005 — Blocos do log de execução permanecem distinguíveis sem ambiguidade
- Descrição: o sistema deve manter (ou tornar mais explícita) a separação
  entre os três blocos do log de execução (`## Parâmetros`, `## Prompt`,
  `## Chat`), de forma que não seja possível confundir onde termina o
  manual/prompt e onde começa o diálogo capturado — a ambiguidade relatada em
  23/08/2026 não pode se repetir.
- Ator: Esteira / Adapter (produz o log).
- Pré-condição: execução de agente concluída, log gravado.
- Fluxo principal: log grava `## Parâmetros`, depois `## Prompt` com o texto
  exato enviado (já reduzido pelas demais RFs), depois `## Chat` com o
  diálogo — sem texto de um bloco vazar visualmente para outro.
- Alternativos/exceções: nenhuma.
- Critérios de aceitação:
  - Dado um log de execução gerado após a simplificação do prompt, quando o
    arquivo é lido, então é possível identificar, sem ambiguidade textual,
    onde termina `## Prompt` e começa `## Chat`.
  - Dado o mesmo log, quando o bloco `## Prompt` é inspecionado, então ele
    contém exatamente o texto passado ao adapter nessa execução (sem
    reconstrução ou resumo divergente do que foi realmente enviado).
- Fonte: histórico da issue, comentário de 23/08/2026 (observação sobre a
  leitura equivocada do log) · Regras: nenhuma regra de negócio nova; é
  garantia de rastreabilidade sobre o comportamento já existente.

### RF-006 — Benchmark antes/depois sobre matriz fixa de cenários
- Descrição: o sistema deve ser validado por um benchmark que meça
  caracteres, palavras e, quando disponível, tokens do prompt dinâmico e do
  total sempre carregado, nas versões antes e depois, sobre uma matriz fixa
  de cenários que cubra pelo menos as combinações de `gitevents` (`create`,
  `use`, `merge`, `create-merge`, `no-branch`) cruzadas com presença/ausência
  de `change` (transição configurada) e presença/ausência de `agent-hub` na
  coluna.
- Ator: Arquitetura/Engenharia (executa o benchmark); QA (valida os gates).
- Pré-condição: inventário (RF-001) e composição simplificada implementados.
- Fluxo principal: para cada combinação da matriz, gerar o prompt/contexto
  na versão base e na versão proposta → medir caracteres/palavras/tokens →
  calcular redução percentual → comparar contra os gates de 40%/20%.
- Alternativos/exceções: combinações inválidas (ex.: `no-branch` com `merge`
  simultâneo não existe no domínio — `gitevents` é um valor único por
  coluna) não entram na matriz.
- Critérios de aceitação:
  - Dado as 5 variantes de `gitevents` × 2 variantes de `change` × 2
    variantes de `agent-hub` (20 cenários, descontadas combinações inválidas
    do domínio), quando o benchmark é executado, então existe uma medição
    antes/depois para cada cenário da matriz.
  - Dado o conjunto de medições da matriz, quando agregado, então a redução
    média do prompt dinâmico é ≥ 40% e a redução média do total sempre
    carregado é ≥ 20%, conforme os gates da análise de negócio.
  - Dado qualquer cenário individual da matriz, quando medido isoladamente,
    então nenhum cenário mostra aumento do total sempre carregado em relação
    à versão base.
- Fonte: resolução desta etapa de requisitos (ponto 3 da rodada de dúvidas de
  23/08/2026) — decisão de especificação de teste dentro do escopo já
  aprovado pela análise de negócio, não uma nova decisão de negócio ·
  Regras: RN-008.

### RF-007 — Mensagem de commit e PR compostas pelo agente [BLOQUEADO — aguarda decisão do dono]
- Descrição: o sistema deve deixar de fixar `git commit -m "<coluna>:
  <título>"` e `gh pr create --title "merge: <branch> -> <base>" --body
  "Automated PR from agent"` como literais no prompt; em vez disso, o prompt
  deve instruir o agente a compor mensagem de commit e título/corpo de PR que
  reflitam o que foi efetivamente realizado, preservando a obrigação de
  commitar/dar push/abrir PR quando `gitevents` exigir.
- Ator: Agente executor (compõe a mensagem); Esteira (mantém a obrigação de
  execução do passo conforme `gitevents`).
- Pré-condição: `gitevents` da coluna exige commit/push/PR.
- Fluxo principal: agente realiza a tarefa → agente compõe mensagem de commit
  refletindo a mudança real → agente executa commit/push → (se `merge` ou
  `create-merge`) agente compõe título/corpo de PR refletindo a mudança real
  → agente abre o PR.
- Alternativos/exceções: **não definido.** Ver bloqueio abaixo.
- Critérios de aceitação: **pendentes** — não é possível escrever
  Dado/Quando/Então testável para os limites de liberdade do agente sem a
  resposta do dono descrita no bloqueio.
- Fonte: análise de negócio, escopo aprovado; resposta do dono, item 4
  (25/08/2026) · Regras: RN-007.

> **Bloqueio:** a rodada de 23/08/2026 perguntou se "sem copy mecânico"
> significa apenas liberdade de composição de texto, mantendo a obrigação de
> commitar/dar push/abrir PR sempre que `gitevents` exigir. O dono respondeu
> em 25/08/2026 devolvendo a pergunta ("quais são os caminhos aceitáveis? o
> que ganhamos ao mudar? quais são os limites de mudanças?") em vez de
> decidir. Este RF não pode ser fechado com critérios de aceitação testáveis
> até essa decisão existir, porque o limite de liberdade do agente (por
> exemplo, se ele pode decidir não commitar quando julgar não haver mudança
> relevante) é uma escolha de risco de negócio, não uma inferência que o
> Analista de Requisitos deva fazer sozinho. Ver pedido de esclarecimento
> registrado no addcomment desta rodada.
