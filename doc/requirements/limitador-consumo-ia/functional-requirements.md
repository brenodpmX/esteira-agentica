# Requisitos Funcionais — Limitador de consumo de IA

Status: draft — RF-006 pendente de confirmação (ver `need_human` na issue #177)
Owner: requirements · Updated: 2026-08-25
Inputs: issue #177 e histórico completo da entrevista com o dono (rodadas 1–5),
`doc/product/limitador-consumo-ia/{vision,problem-space,epicos}.md`,
`doc/requirements/limitador-consumo-ia/{business-rules,glossary}.md`,
`src/core/config.py`, `src/adapters/kiro_cli_agent.py`

## Atores

- **Cliente/implantador**: configura limites opcionais por combinação
  pipe/plataforma no `pipe.yml` (RF-001), escolhe fuso (RF-004) e designa o
  responsável pela aferição do primeiro ciclo (RN-011). Não opera o sistema em
  tempo real — define política antes da ativação.
- **Esteira (núcleo de seleção de tarefa)**: antes de cada tentativa de
  acionamento de agente, avalia se a combinação pipe/plataforma está bloqueada
  (RF-002) e decide acionar ou impedir.
- **Adapter de plataforma** (ex.: `kiro_cli_agent`): ao final de cada execução,
  captura o consumo reportado pela plataforma e o traduz para a terminologia
  interna ("tokens"), sem presumir equivalência de valor com outra plataforma
  (RF-003; RN-001).
- **Responsável pela aferição** (designado pelo implantador, RN-011): consome
  o baseline do primeiro ciclo (RF-008) para decidir manter, ajustar ou
  retirar o controle. Não é um ator do fluxo de bloqueio em si.

## Dados

- **Política de consumo**: conjunto de até três limites (diário, semanal,
  mensal) configurados para uma combinação pipe/plataforma; cada limite tem um
  valor numérico na unidade autoritativa da plataforma e, quando aplicável, o
  dia de reset (semanal/mensal). Opcional — pode estar total ou parcialmente
  ausente (RN-005).
- **Consumo reconhecido**: valor acumulado, por período e por combinação
  pipe/plataforma, a partir do consumo capturado ao final de cada execução
  concluída. Estado normal: número >= 0. Estado alternativo: indisponível
  (distinto de zero — RN-007).
- **Registro de tentativa impedida**: entrada gerada a cada bloqueio, contendo
  pipe, plataforma, unidade, consumo reconhecido, limite configurado,
  período(s) que motivaram o bloqueio e a condição de retomada (RN-008).
- **Configuração de fuso**: valor opcional por instalação (ver RF-004) usado
  para calcular a fronteira de todos os períodos configurados.

## Requisitos

### RF-001 — Configurar limites opcionais por combinação pipe/plataforma

- Descrição: o sistema deve permitir que o cliente configure, para uma
  combinação pipe/plataforma, até três limites de consumo independentes
  (diário, semanal, mensal), cada um opcional.
- Ator: Cliente/implantador (declara), Esteira (lê na inicialização/reload de
  configuração).
- Pré-condição: a plataforma referenciada existe em `agents.<plataforma>` no
  `pipe.yml`.
- Fluxo principal:
  1. O cliente declara um ou mais limites (diário/semanal/mensal) para uma
     plataforma no `pipe.yml`.
  2. A esteira valida a configuração na inicialização.
  3. A partir da próxima seleção de tarefa, a combinação passa a ser avaliada
     contra os limites declarados (RF-002).
- Alternativos/exceções:
  - Nenhum limite declarado para a combinação → comportamento atual,
    sem qualquer avaliação de consumo (RN-005).
  - Valor de limite inválido (negativo, não numérico, zero) → configuração
    inválida; a esteira deve rejeitar na validação, no mesmo padrão de erro já
    usado por `check_config()` (mensagem explícita identificando a chave;
    comportamento de "startup falha com erro claro", já estabelecido em
    RF-05 de `doc/requirements/rodar-no-docker/requisitos.md`).
- Critérios de aceitação:
  - Dado um `pipe.yml` sem nenhum limite declarado para uma plataforma,
    quando o agente daquela plataforma for selecionado para execução, então a
    esteira aciona o agente normalmente, sem checagem de consumo.
  - Dado um `pipe.yml` com limite diário declarado para uma plataforma,
    quando apenas esse valor estiver presente (sem semanal/mensal), então a
    esteira aplica somente a checagem diária para essa combinação.
  - Dado um valor de limite negativo ou não numérico no `pipe.yml`, quando a
    esteira inicializar, então a inicialização falha com erro explícito
    identificando a chave inválida (mesmo padrão de `ConfigError`).
- Fonte: issue #177, "Resultado esperado" (1º e 2º itens); histórico, rodada
  3, respostas 3–4 · Regras: RN-002, RN-003, RN-005.

### RF-002 — Impedir a próxima tentativa quando o consumo reconhecido atinge o limite

- Descrição: o sistema deve impedir o próximo acionamento de agente em uma
  combinação pipe/plataforma sempre que o consumo reconhecido em qualquer
  período configurado for maior ou igual ao limite daquele período.
- Ator: Esteira (avalia e decide, no momento da seleção de tarefa, antes de
  chamar o adapter de agente).
- Pré-condição: a combinação pipe/plataforma tem ao menos um limite
  configurado (RF-001) e ao menos uma medição de consumo reconhecido para o
  período correspondente (ainda que zero).
- Fluxo principal:
  1. A esteira seleciona uma tarefa cujo agente pertence a uma combinação
     pipe/plataforma com política configurada.
  2. Para cada período configurado dessa combinação, a esteira compara o
     consumo reconhecido acumulado no período com o limite.
  3. Se qualquer período estiver com consumo reconhecido >= limite, a esteira
     não aciona o agente; gera o registro de tentativa impedida (RF-005) e
     segue para a próxima tarefa elegível, sem interromper outras combinações.
  4. Se nenhum período estiver em condição de bloqueio, a esteira aciona o
     agente normalmente.
- Alternativos/exceções:
  - Mais de um período em condição de bloqueio simultaneamente → um único
    registro de tentativa impedida, citando todos os períodos que motivaram o
    bloqueio (RN-008).
  - Consumo reconhecido indisponível para o período → não conta como
    bloqueio; ver RF-007 (falha aberta).
  - Execução já em andamento no momento em que o limite é atingido → não é
    interrompida; apenas a tentativa seguinte é afetada (RN-006).
- Critérios de aceitação:
  - Dado consumo reconhecido igual ao limite diário configurado, quando a
    esteira for selecionar a próxima tarefa daquela combinação, então o
    acionamento é impedido.
  - Dado consumo reconhecido menor que todos os limites configurados, quando
    a esteira selecionar a tarefa, então o agente é acionado normalmente.
  - Dado consumo reconhecido acima do limite semanal e dentro do limite
    diário, quando a esteira avaliar a combinação, então o acionamento é
    impedido (basta um período em condição de bloqueio).
  - Dado um bloqueio ativo em uma combinação pipe/plataforma, quando outra
    combinação (outra plataforma na mesma pipe, ou a mesma plataforma em
    outra pipe) estiver elegível, então essa outra combinação continua sendo
    processada no mesmo ciclo.
- Fonte: issue #177, "Descrição" e "Critérios de negócio"; histórico, rodada
  3, resposta 2; rodada 4 (validado) · Regras: RN-002, RN-003, RN-004, RN-006.

### RF-003 — Capturar e traduzir o consumo reportado pela plataforma

- Descrição: o sistema deve capturar, ao final de cada execução concluída
  (com sucesso ou falha, desde que a plataforma reporte consumo), o valor de
  consumo na unidade autoritativa da plataforma e atribuí-lo à combinação
  pipe/plataforma e ao instante da execução, para acumulação nos períodos
  vigentes.
- Ator: Adapter de plataforma (captura e traduz), Esteira (acumula por
  período).
- Pré-condição: a execução do agente terminou (a plataforma emitiu algum
  retorno, ainda que de erro).
- Fluxo principal:
  1. A execução do agente termina.
  2. O adapter da plataforma extrai o valor de consumo do retorno da
     plataforma (ex.: hoje o `kiro-cli` reporta tempo e consumo na última
     linha significativa do output).
  3. O adapter atribui esse valor à combinação pipe/plataforma, na
     terminologia interna ("tokens"), sem conversão de valor entre unidades
     de plataformas diferentes (RN-001).
  4. A esteira soma o valor a cada período (diário/semanal/mensal) vigente e
     configurado para aquela combinação.
- Alternativos/exceções:
  - Plataforma não reporta consumo, ou a captura falha → RF-007 (falha
    aberta); nenhum valor é somado, e a indisponibilidade é registrada
    distinta de zero.
  - Combinação sem nenhum período configurado → o valor pode ser descartado
    ou não acumulado (não há política a manter atualizada); este RF não exige
    acumulação para combinações sem RF-001 configurado.
- Critérios de aceitação:
  - Dado que uma execução concluída reporta consumo mensurável, quando o
    adapter processar o retorno, então o valor é atribuído à combinação
    pipe/plataforma correta e à unidade autoritativa daquela plataforma.
  - Dado que duas plataformas diferentes reportam consumo no mesmo ciclo,
    quando a esteira acumular os períodos, então os valores nunca são somados
    ou comparados entre si.
- Fonte: histórico, rodada 4, resposta 4 ("o adapter deve buscar em sua
  plataforma uma medida de consumo... traduzir para a nossa terminologia");
  `src/adapters/kiro_cli_agent.py` (`_last_meaningful_line`, comentário sobre
  tempo/tokens reportados) · Regras: RN-001.

### RF-004 — Fuso configurável para as fronteiras de período

- Descrição: o sistema deve permitir que o cliente configure um fuso horário
  usado para determinar a virada do dia (reset diário), o início da semana
  (reset semanal) e o dia de reset mensal; na ausência de configuração, usa o
  fuso local da máquina onde o processo executa.
- Ator: Cliente/implantador (configura, opcionalmente), Esteira (aplica no
  cálculo de fronteiras).
- Pré-condição: nenhuma — este requisito vale mesmo sem nenhum limite
  configurado (a fronteira só é relevante quando há período configurado, mas
  o fuso pode ser definido de forma independente).
- Fluxo principal:
  1. O cliente opcionalmente declara um fuso horário na configuração.
  2. A esteira usa esse fuso para calcular quando cada período configurado
     reinicia.
  3. Se o cliente não declarar fuso, a esteira usa o fuso local da máquina.
- Alternativos/exceções:
  - Fuso declarado com valor inválido (não reconhecível) → configuração
    inválida; falha na inicialização com erro explícito (mesmo padrão de
    RF-001).
- Critérios de aceitação:
  - Dado um fuso configurado, quando o dia mudar naquele fuso, então o
    período diário de todas as combinações reinicia nesse instante.
  - Dado nenhum fuso configurado, quando o dia mudar no fuso local da
    máquina, então o período diário reinicia nesse instante.
- Fonte: histórico, rodada 5 ("podemos permitir fuso e se não for escolhido,
  usamos o local da máquina") · Regras: RN-010.

### RF-005 — Registrar e explicar toda tentativa impedida

- Descrição: o sistema deve gerar, para cada tentativa impedida por RF-002,
  um warning em terminal e arquivo de log, e um registro no controle de
  execuções, ambos com pipe, plataforma, unidade, consumo reconhecido, limite
  configurado, período(s) que motivaram o bloqueio e a condição de retomada.
- Ator: Esteira.
- Pré-condição: uma tentativa foi impedida por RF-002.
- Fluxo principal:
  1. A esteira decide impedir o acionamento (RF-002).
  2. A esteira monta a explicação com os campos mínimos exigidos.
  3. A esteira emite o warning (terminal e arquivo) e grava o registro no
     controle de execuções, antes de seguir para a próxima tarefa elegível.
- Alternativos/exceções:
  - Mais de um período em condição de bloqueio → todos os períodos
    relevantes aparecem no mesmo registro (não um registro por período).
- Critérios de aceitação:
  - Dado uma tentativa impedida, quando o registro for gerado, então ele
    contém pipe, plataforma, unidade, consumo reconhecido, limite, período(s)
    e condição de retomada — nenhum campo ausente.
  - Dado uma tentativa impedida, quando ela ocorrer, então o warning aparece
    tanto no terminal quanto no arquivo de log daquele ciclo.
- Fonte: issue #177, "Resultado esperado" (item de warning); vision.md,
  "Métricas de sucesso" · Regras: RN-008.

### RF-006 — Declarar a política na configuração por plataforma

- Descrição: o sistema deve permitir declarar os limites de RF-001 na
  hierarquia de chaves `agents.<plataforma>.<limites de consumo>` do
  `pipe.yml`, como decidido pelo dono na entrevista (rodada 3, resposta 4).
- Ator: Cliente/implantador.
- Pré-condição: a plataforma existe em `agents.<plataforma>`.
- Fluxo principal: ver RF-001.
- **Pendência de confirmação (bloqueia o fechamento deste RF):** a
  documentação de negócio descreve o escopo como "por combinação
  pipe/plataforma", mas o `pipe.yml` hoje não tem nenhum campo que identifique
  a pipe — um arquivo de configuração corresponde a exatamente uma
  instância/processo da esteira. Perguntei ao dono (rodada 1 desta etapa,
  `need_human` ativo) se a "pipe" do escopo é sempre a própria instância que
  lê aquele `pipe.yml` (tornando `agents.<plataforma>.<limites>` suficiente,
  sem novo campo de identificação) e qual identificador de pipe deve aparecer
  no registro exigido por RF-005/RN-008. Este RF permanece em draft até a
  resposta; os critérios de aceitação abaixo cobrem apenas o que já está
  validado (a chave é por plataforma) e evitam prescrever a resolução da
  pendência.
- Critérios de aceitação (parciais, não fecham o RF):
  - Dado uma chave de limite declarada sob `agents.<plataforma>` para uma
    plataforma existente, quando a esteira inicializar, então a política é
    aplicada a todas as execuções daquela plataforma.
  - Dado uma chave de limite declarada sob uma plataforma inexistente em
    `agents`, quando a esteira inicializar, então a inicialização falha com
    erro explícito (mesmo padrão de validação de `agent-hub`/`agent` em
    `config.py`).
- Fonte: histórico, rodada 3, resposta 4 · Regras: RN-002 (parcialmente
  pendente — ver observação acima).

### RF-007 — Continuar em falha aberta quando o consumo é indisponível

- Descrição: o sistema deve continuar acionando a combinação pipe/plataforma
  normalmente quando o consumo de uma ou mais execuções não puder ser medido,
  sem tratar a indisponibilidade como consumo zero.
- Ator: Adapter de plataforma (detecta a falha de captura), Esteira (decide
  não bloquear e registra a indisponibilidade).
- Pré-condição: uma execução concluiu sem que o consumo pudesse ser
  determinado a partir do retorno da plataforma.
- Fluxo principal:
  1. O adapter tenta capturar o consumo reportado (RF-003) e não obtém valor.
  2. A esteira marca aquele período/execução como "consumo indisponível" (não
     soma ao acumulado, não trata como zero).
  3. A combinação permanece elegível para a próxima tentativa, salvo se outro
     período/medição já a colocar em bloqueio por RF-002.
  4. A indisponibilidade é registrada de forma distinguível de zero em toda
     evidência (log, controle de execuções, baseline).
- Alternativos/exceções: nenhuma — esta é a decisão explícita do dono
  ("se não conseguimos medir o consumo, continuamos").
- Critérios de aceitação:
  - Dado que uma execução concluída não reporta consumo, quando a esteira
    processar o retorno, então nenhum valor é somado ao consumo reconhecido e
    a combinação não é bloqueada por causa dessa execução.
  - Dado consumo indisponível registrado, quando a evidência for consultada
    (log ou controle de execuções), então o registro distingue
    explicitamente "indisponível" de "zero".
- Fonte: histórico, rodada 4, resposta 1; rodada 5 (fechamento) · Regras:
  RN-007.

### RF-008 — Publicar baseline do primeiro ciclo

- Descrição: o sistema deve acumular e expor, por combinação pipe/plataforma,
  as métricas necessárias para o responsável designado (RN-011) publicar um
  baseline ao final do primeiro ciclo completo de operação da política.
- Ator: Esteira (acumula as métricas), Responsável pela aferição (publica e
  decide, fora do sistema).
- Pré-condição: a política está ativa em ao menos uma combinação
  pipe/plataforma desde o início do ciclo medido.
- Fluxo principal:
  1. Durante o ciclo, a esteira acumula: tentativas impedidas e motivos,
     excedente da última execução iniciada antes do limite, ocorrências de
     consumo indisponível, falsos bloqueios (quando identificáveis), tempo até
     retomada e impacto observável em trabalho prioritário.
  2. Ao fim do primeiro ciclo completo, essas métricas ficam disponíveis para
     o responsável designado consolidar o baseline.
- Alternativos/exceções:
  - Nenhuma combinação com política ativa → não há baseline a publicar
    (este RF não se aplica).
- Critérios de aceitação:
  - Dado um ciclo completo com ao menos uma tentativa impedida, quando o
    baseline for consultado, então tentativas impedidas, excedente e
    indisponibilidade aparecem discriminados por combinação pipe/plataforma.
  - Dado um relatório ou métrica derivada deste baseline, quando apresentado,
    então nenhuma tentativa impedida é apresentada como economia ou consumo
    evitado (RN-012).
- Fonte: issue #177, "Resultado esperado" (medição de excedente/baseline);
  vision.md, "Métricas de sucesso" · Regras: RN-011, RN-012.

## Fora de escopo (herdado de `epicos.md`, não redefinido aqui)

Gestão de orçamento/overage/compra de capacidade; interrupção de execução em
andamento; recomendação automática de cotas; dashboard; garantia de que as
cotas cabem no contrato; coordenação entre instalações que não compartilham o
mesmo controle; decisão de tecnologia/arquitetura; quebra em stories nesta
etapa.
