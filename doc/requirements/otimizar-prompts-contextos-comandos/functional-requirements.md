# Requisitos Funcionais — Otimizar prompts, contextos e comandos

Status: approved (exceto RF-007, RF-008 e RF-009 — ver bloqueios) · Owner: requirements
Updated: 2026-08-26
Inputs: `doc/product/otimizar-prompts-contextos-comandos/analise-negocio.md`;
código-fonte (`src/core/agent.py`, `src/core/commands.py`,
`src/core/context_generator.py`, `src/core/config.py`, `src/core/session.py`,
`src/adapters/kiro_cli_agent.py`); histórico da issue #92 (respostas do dono
em 22, 25 e 26/08/2026); `business-rules.md` e `glossary.md` deste mesmo
diretório.

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
- **Configuração de flow (`git.flow.<id>`):** hoje fixa implicitamente o
  formato de nome de branch em `{prefix}{issue_id}-{slug}` dentro de
  `build_prompt` (`src/core/agent.py`); passa a ser candidata a um template
  configurável (RF-008).
- **Metadados de projeto (`pipe.yml`):** nova hierarquia de chaves,
  ainda a nomear pela arquitetura, para nome do projeto, descrição breve e
  humanos envolvidos (nome/função) — candidata a entrar no contexto
  persistente (RF-009).
- **Estado de sessão (`.pipe/sessions.json` via `SessionIndex`):** já indica,
  antes da execução, se a issue está sendo retomada (`session_id` conhecido)
  ou iniciada pela primeira vez. `build_prompt` hoje não consome esse sinal —
  passa a ser entrada de composição do prompt (RF-010).
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

> **Bloqueio (persiste após a rodada de 26/08/2026):** a rodada de 23/08/2026
> perguntou se "sem copy mecânico" significa apenas liberdade de composição
> de texto, mantendo a obrigação de commitar/dar push/abrir PR sempre que
> `gitevents` exigir. O dono respondeu em 25/08/2026 devolvendo a pergunta
> ("quais são os caminhos aceitáveis? o que ganhamos ao mudar? quais são os
> limites de mudanças?") em vez de decidir. Em 26/08/2026 o dono trouxe uma
> dor concreta relacionada — o core erra o nome de branch a criar/mergear —
> e propôs comandos genéricos ("faça o merge request na branch da issue
> pai"), o que amplia o RF de "texto da mensagem" para "quem resolve o nome
> da branch e o comando exato" (ver RF-008, que fecha a parte de nomenclatura
> configurável). Mas a pergunta original de risco — se o agente pode também
> decidir *não* commitar/pular a etapa quando julgar não haver mudança
> relevante — continua sem resposta explícita. Este RF permanece bloqueado
> até essa escolha existir; é risco de negócio (consistência de workflow),
> não inferência que o Analista deva fazer sozinho. Pergunta objetiva
> reencaminhada no addcomment desta rodada, restrita a uma escolha binária
> (ou uma terceira opção, se nenhuma capturar a intenção).

### RF-008 — Formato de nome de branch configurável por flow
- Descrição: o sistema deve permitir configurar, em `git.flow.<flow_id>`, o
  formato/template do nome de branch usado por `build_prompt` ao instruir
  criação/uso de branch, em vez de um formato fixo embutido no código
  (`{prefix}{issue_id}-{slug}`). O operador deve poder ler no próprio
  `pipe.yml` qual é o padrão vigente sem precisar inspecionar o código-fonte.
- Ator: Operador (configura `git.flow.<flow_id>` em `pipe.yml`); Esteira
  (resolve o nome de branch a partir do template configurado).
- Pré-condição: flow configurado em `pipe.yml` (`git.flow.<flow_id>`).
- Fluxo principal: operador define o template de nome de branch para um flow
  (ex.: variáveis disponíveis como id da issue, slug, prefixo) → esteira
  resolve o nome efetivo da branch a partir do template ao montar o prompt →
  o prompt exibe o nome já resolvido (não o template) ao agente.
- Alternativos/exceções: flow sem template explícito mantém o comportamento
  atual (`{prefix}{issue_id}-{slug}`) como default — configuração existente
  não quebra.
- Critérios de aceitação:
  - Dado um `git.flow.<flow_id>` sem o novo campo de template, quando o
    prompt é composto, então o nome de branch resolvido é idêntico ao
    comportamento atual (`{prefix}{issue_id}-{slug}`).
  - Dado um `git.flow.<flow_id>` com um template customizado válido, quando
    o prompt é composto, então o nome de branch usado em todos os blocos de
    Git (Setup, Commit/Push, PR, Cleanup) é o resultado da resolução do
    template — sem divergência entre blocos.
  - Dado um template inválido (referencia variável inexistente ou sintaxe
    malformada), quando `pipe.yml` é validado, então a validação falha com
    erro identificando o flow e o problema — não falha silenciosamente em
    tempo de execução do agente.
- Fonte: resposta do dono (26/08/2026): "o core erra muito o nome da branch
  a se criada, a ser mergeada (...) me incomoda não poder colocar no gitflow
  no arquivo pipe.yml o formato que quero que as branchs sejam criadas" ·
  Regras: RN-006, RN-010.

### RF-009 — Metadados de projeto no `pipe.yml` incluídos no contexto persistente
- Descrição: o sistema deve permitir configurar, em uma nova seção de
  `pipe.yml`, metadados do projeto — nome do projeto, descrição breve, e
  humanos envolvidos (nome e função/papel) — e incluir esse conteúdo no
  contexto persistente gerado (`generate_context`), tornando-o disponível ao
  agente sem exigir que o operador o repita no prompt dinâmico ou no contexto
  do operador (`contexts/<plataforma>/<agente>.md`).
- Ator: Operador (preenche os metadados em `pipe.yml`); Esteira (inclui os
  metadados na seção apropriada do contexto persistente gerado).
- Pré-condição: nenhuma — seção é opcional.
- Fluxo principal: operador preenche nome, descrição e lista de humanos
  (nome + função) em `pipe.yml` → `generate_context` inclui uma seção com
  esse conteúdo no `.pipe/CONTEXT.md`/agente gerado → o agente passa a ter
  acesso a "quem é o dono", "qual é o projeto" sem essa informação estar
  duplicada em cada `target-prompt`.
- Alternativos/exceções: `pipe.yml` sem a seção de metadados mantém o
  contexto persistente sem essa seção (comportamento atual, sem quebra).
- Critérios de aceitação:
  - Dado um `pipe.yml` sem a nova seção de metadados, quando o contexto
    persistente é gerado, então o resultado é idêntico ao comportamento
    atual (sem a seção).
  - Dado um `pipe.yml` com nome, descrição e ao menos um humano (nome +
    função) preenchidos, quando o contexto persistente é gerado, então essas
    três informações aparecem em uma seção identificável do contexto
    persistente.
  - Dado que o conteúdo de metadados muda no `pipe.yml`, quando o próximo
    startup ocorre, então a regeneração do contexto persistente (regra já
    existente de "pipe.yml mais novo que CONTEXT.md") reflete o novo
    conteúdo.
- Fonte: resposta do dono (26/08/2026): "me incomoda não ter uma hierarquia
  de chaves no pipe.yml para falar do projeto (...) informar o nome do
  projeto, uma breve descrição, nome e função dos humanos envolvidos" ·
  Regras: RN-003 (não se aplica — é metadado da esteira, não conteúdo do
  operador), RN-006.

### RF-010 — Prompt alternativo de continuidade em reexecução de issue
- Descrição: quando a esteira detecta, antes de montar o prompt, que a issue
  corrente está sendo retomada (já existe `session_id` conhecido em
  `SessionIndex` para o par board/issue/agente — ver glossário "sessão
  retomada"), o prompt dinâmico deve refletir esse fato — instruindo o
  agente a continuar o trabalho em andamento a partir do contexto retomado —
  em vez de repetir a montagem completa como se fosse a primeira execução.
- Ator: Esteira (detecta reexecução via `SessionIndex.get`; compõe o prompt
  de continuidade).
- Pré-condição: `SessionIndex.get(board_id, issue_id, agent_id)` retorna um
  `session_id` não nulo para a task corrente.
- Fluxo principal: esteira resolve a task (`keep_task`) → antes de montar o
  prompt, verifica se há sessão conhecida para board/issue/agente → se sim,
  compõe o prompt no formato de continuidade (referencia o trabalho já
  iniciado, sem repetir instruções redundantes já entregues na execução
  anterior) → se não, compõe o prompt completo (comportamento atual).
- Alternativos/exceções: se a sessão indicada pelo índice não existir mais no
  kiro-cli (foi descartada), o comportamento de fallback para sessão nova
  já é responsabilidade do adapter (comportamento preexistente, não alterado
  por este RF); o prompt de continuidade não pode assumir que o histórico
  de raciocínio sempre estará disponível.
- Critérios de aceitação:
  - Dado que não existe `session_id` registrado para board/issue/agente,
    quando o prompt é composto, então o resultado é equivalente ao
    comportamento atual (prompt completo de primeira execução).
  - Dado que existe `session_id` registrado para board/issue/agente, quando
    o prompt é composto, então o texto instrui explicitamente o agente a
    retomar o trabalho em andamento, sem reconstruir do zero as seções cujo
    conteúdo não muda entre a execução anterior e esta.
  - Dado o cenário de continuidade, quando medido o total de palavras do
    prompt de continuidade, então ele não é maior que o prompt de primeira
    execução para a mesma coluna/tarefa (a continuidade deve reduzir, nunca
    aumentar, o texto).
- Fonte: resposta do dono (26/08/2026): "sobre a reexecução da issue pelo
  agente, faz falta um prompt alternativo como 'continue o que estava
  fazendo' obviamente que mantendo o contexto" · Regras: RN-001 (continuidade
  não pode omitir guardrails), RN-005.

### RF-011 — Contexto persistente gerado fora de `.pipe/`, na raiz do projeto [BLOQUEADO — aguarda decisão de nomenclatura/arquitetura]
- Descrição: o arquivo de contexto persistente gerado pela esteira
  (atualmente `.pipe/CONTEXT.md`) deve nascer no mesmo diretório do
  `pipe.yml` ("raiz do projeto", conforme definido pelo dono — não a raiz de
  cada repositório clonado em `repo/`), e não dentro de `.pipe/`.
- Ator: Esteira (`generate_context`, `_needs_regeneration`).
- Pré-condição: nenhuma.
- Fluxo principal: no startup, a esteira gera o contexto persistente em um
  caminho na raiz do projeto (ao lado de `pipe.yml`), não em `.pipe/`.
- Alternativos/exceções: **não definido** — ver bloqueio.
- Critérios de aceitação: **pendentes.**
- Fonte: resposta do dono (26/08/2026): "sobre o arquivo de contexto, me
  incomoda ele nascer no `.pipe/` (...) o arquivo de contexto tem que nascer
  na raiz do projeto (...) no mesmo diretório do arquivo pipe.yml" ·
  Regras: RN-006.

> **Bloqueio:** este requisito é observável e não depende de arquitetura para
> ser *descrito* (onde o arquivo nasce), mas colide com uma garantia de
> segurança que este mesmo épico não pode regredir (RN-001): hoje
> `PROTECTED_PATHS` e a lista de "Restrições de sistema" do contexto gerado
> cobrem exclusivamente caminhos dentro de `.pipe/`; o próprio arquivo de
> contexto gerado (`.pipe/CONTEXT.md`) é hoje implicitamente protegido por
> estar fora do que o agente lista como escopo de escrita permitido (o
> workdir é `repo/<repo_id>`, não a raiz do projeto). Mover o contexto
> gerado para a raiz do projeto expõe, na mesma árvore de diretórios, o
> `pipe.yml`, o próprio contexto gerado e potencialmente outros arquivos de
> estado — nenhum dos quais o agente deveria escrever, já que o agente opera
> confinado a `repo/<repo_id>` (RN-001, `_assert_no_protected`).
> Preciso de decisão do dono sobre **um** destes pontos antes de escrever
> critério de aceitação testável: (a) o novo arquivo na raiz do projeto
> entra em `PROTECTED_PATHS` com o mesmo nível de proteção do que hoje tem
> dentro de `.pipe/`, ou (b) existe alguma razão para ele precisar ser
> gravável/acessível de outro modo que hoje não se aplica a `.pipe/CONTEXT.md`.
> Sem essa resposta, o requisito ficaria ambíguo sobre se a mudança de local
> é puramente de conveniência de leitura humana ou se implica mudança de
> superfície de proteção. Pergunta reencaminhada no addcomment desta rodada.
