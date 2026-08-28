# Requisitos Funcionais — Integridade de issues entre boards

Status: baseline de requisitos
Owner: requirements
Last updated: 2026-08-26

## Inputs
- `doc/product/integridade-de-issues-entre-boards/vision.md`
- `doc/product/integridade-de-issues-entre-boards/problem-space.md`
- `doc/product/integridade-de-issues-entre-boards/epicos.md`
- Histórico de entrevista com o dono (issue #230, 2026-08-26)
- `doc/incidente/sub-issues-propagadas/ticket.md` e `doc/changes/88-sub-issues-propagadas-entre-boards.md` (correção anterior, já em `main`, recorrente)
- `doc/requirements/integridade-de-issues-entre-boards/glossary.md`

Este documento não define arquitetura, tecnologia, classes ou estratégia de
persistência — essas decisões pertencem à etapa técnica. Especifica **o que**
o sistema deve garantir, observável do ponto de vista de negócio e de
operação, para que a etapa de arquitetura e a quebra em stories não precisem
de suposições.

## Atores

| Ator | Papel |
|---|---|
| **Esteira** | O sistema (núcleo de sincronização, seleção de tarefas e execução de agentes) — sujeito principal dos requisitos abaixo. |
| **GitHub Projects V2** | Sistema externo que propaga automaticamente uma sub-issue para o Project do pai ao vincular uma relação pai/filho entre issues de boards distintos. Comportamento da plataforma, não controlável pela esteira. |
| **Agente** | Processo de IA despachado pela esteira para atuar sobre uma issue em um board e coluna específicos. |
| **Dono/Operador** | Pessoa responsável por priorização, custo e decisões de negócio sobre a esteira; interage via comentários na issue e via ações manuais no board. |
| **Issue** | Unidade de trabalho do GitHub (epic, story ou task, dependendo do board), que pode ter relações pai/filho e participar de um ou mais boards. |

## Dados relevantes

- **Issue:** identificador (número GitHub), título, body, `Status` (coluna) por
  participação, labels, relações `parent`/`children`/`blocked_by`/`blocks`,
  estado (aberta/fechada/arquivada).
- **Participação (item de Project V2):** issue, board/project, `Status`
  (pode estar vazio), data de criação da participação.
- **Board configurado:** identificador presente em `pipe.yml`, colunas,
  agente(s) por coluna, `flow`.
- **Evidência de rollout:** commit/versão em execução, ambiente, data do
  último deploy.
- **Registro de despacho:** issue, board, coluna, agente, timestamp, consumo
  (créditos), resultado (concluído/erro).
- **Registro de reconciliação:** issue, board de origem, board propagado,
  timestamp da propagação, timestamp da reconciliação, meio (automática/manual).

## RF-01 — Impedir despacho de agente em board não intencional

**Descrição:** a esteira nunca deve selecionar para execução de agente
(`keep_task`) uma issue cuja participação no board avaliado seja não
intencional (propagada), independentemente de essa participação já ter ou
não recebido `Status`.

**Fluxo principal:**
1. Uma relação pai/filho é criada entre duas issues de boards distintos.
2. O GitHub Projects V2 propaga a filha para o Project do pai.
3. A esteira detecta a participação propagada antes que ela seja avaliada por `keep_task` no board propagado.
4. A issue permanece elegível apenas no seu board intencional.

**Fluxo alternativo — propagação já com `Status`:**
1. A propagação chega ao board indevido já com um `Status` preenchido (por automação nativa do GitHub ou por erro humano).
2. A esteira ainda assim não despacha agente sobre essa participação até que a intencionalidade seja confirmada.

**Critérios de aceite:**
- Dado que uma relação pai/filho foi criada entre issues de boards distintos, quando o GitHub propaga a filha ao Project do pai, então nenhum agente deve ser despachado para essa issue no board do pai antes de a participação ser reconciliada.
- Dado que uma issue tem participação intencional confirmada em dois boards (multi-board autorizado), quando `keep_task` avalia qualquer um dos dois boards, então a issue permanece elegível normalmente em ambos.
- Dado que uma participação propagada já foi reconciliada (removida ou marcada como não executável), quando `keep_task` roda novamente, então essa issue não é mais candidata no board indevido.

## RF-02 — Reconciliar participação não intencional sem intervenção manual

**Descrição:** ao detectar uma participação não intencional, a esteira deve
levá-la a um estado seguro (reconciliação) sem depender de remoção manual pelo
dono, preservando a participação no board intencional.

**Fluxo principal:**
1. A esteira detecta uma participação não intencional em um board.
2. A esteira reconcilia essa participação (remove do board indevido ou impede definitivamente seu despacho) sem intervenção humana.
3. A participação no board intencional permanece intacta, com seu `Status`/coluna preservados.

**Fluxo alternativo — reconciliação falha temporariamente:**
1. A tentativa de reconciliação falha por erro transitório (ex.: indisponibilidade momentânea do GitHub).
2. A esteira preserva o registro da participação não reconciliada e tenta novamente em ciclo posterior, sem descartar o evento e sem despachar agente sobre ela nesse intervalo.

**Critérios de aceite:**
- Dado que uma participação não intencional foi detectada, quando a reconciliação é bem-sucedida, então zero ação manual do dono é necessária para aquele caso.
- Dado que uma issue tem participação intencional em um board e participação não intencional em outro, quando a reconciliação ocorre, então a participação intencional (coluna, `Status`, histórico) permanece inalterada.
- Dado que a tentativa de reconciliação falha por erro transitório, quando o ciclo seguinte roda, então a esteira tenta reconciliar novamente em vez de desistir silenciosamente, e nenhum despacho ocorre sobre a participação não reconciliada nesse intervalo.

## RF-03 — Preservar hierarquia pai/filho

**Descrição:** a reconciliação de participações não intencionais nunca remove
ou invalida a relação pai/filho nativa entre as issues envolvidas.

**Fluxo principal:**
1. Uma relação pai/filho é estabelecida.
2. A participação propagada decorrente é reconciliada.
3. A relação pai/filho entre as duas issues continua visível e íntegra no GitHub e na esteira.

**Critérios de aceite:**
- Dado que uma participação propagada foi reconciliada, quando se consulta a relação pai/filho entre as duas issues, então o vínculo continua presente e correto.
- Dado que uma issue tem múltiplos filhos em boards diferentes do seu, quando cada propagação correspondente é reconciliada, então todas as relações pai/filho permanecem intactas simultaneamente.

## RF-04 — Preservar participação multi-board explicitamente autorizada

**Descrição:** quando uma issue deve legitimamente participar de mais de um
board por decisão deliberada (não por efeito colateral do GitHub), a esteira
não deve tratar nenhuma dessas participações como propagação a ser
reconciliada.

**Fluxo principal:**
1. Uma issue recebe autorização explícita de participação em um segundo board.
2. A esteira registra essa participação como intencional.
3. Ambas as participações permanecem elegíveis para seleção de tarefas em seus respectivos boards.

**Critérios de aceite:**
- Dado que uma participação multi-board foi explicitamente autorizada, quando a detecção de propagação roda, então essa participação não é removida nem impedida de despacho.
- Dado que não existe hoje um caso de uso real de multi-board intencional (conforme resposta do dono em 26/08/2026), quando a solução é entregue, então ela deve, ainda assim, oferecer um meio de declarar essa autorização, verificável pela esteira, para suportar cenários futuros sem exigir nova entrega.

## RF-05 — Cobrir todos os pares de fluxo observados na amostra

**Descrição:** a prevenção e a reconciliação devem cobrir, no mínimo, os três
pares de fluxo comprovados na amostra de negócio: Story propagada para Epics,
Task propagada para User Stories, e qualquer combinação onde uma issue-filha
de um fluxo é propagada para o board do fluxo pai.

**Fluxo principal:**
1. Uma relação pai/filho é criada entre uma story (User Stories) e um épico (Epics), ou entre uma task (Tasks) e uma story (User Stories).
2. A propagação correspondente ao Project do pai é detectada e reconciliada nos mesmos termos do RF-01/RF-02, independentemente do par de fluxos envolvido.

**Critérios de aceite:**
- Dado que uma story é vinculada como filha de um épico em outro board, quando a propagação ocorre, então ela é reconciliada e nenhum agente do fluxo de épicos é despachado sobre a story.
- Dado que uma task é vinculada como filha de uma story em outro board, quando a propagação ocorre, então ela é reconciliada e nenhum agente do fluxo de stories é despachado sobre a task.
- Dado que um novo par de fluxos hierárquico é criado no futuro (ex.: subtask de task), quando uma propagação ocorre entre esses boards, então o mesmo comportamento de prevenção/reconciliação se aplica sem exigir tratamento hardcoded por par específico de board.

## RF-06 — Evidência de rollout distinta de merge

**Descrição:** a entrega deve produzir e expor evidência verificável de que
a correção está de fato em execução no ambiente relevante (commit/versão,
ambiente, data), distinta e adicional à existência do merge em `main`.

**Fluxo principal:**
1. A correção é implantada em um ambiente.
2. A esteira (ou o processo de deploy associado) registra a versão/commit efetivamente em execução, o ambiente e a data.
3. Esse registro é consultável para fins de auditoria e para confirmar o início da janela de validação de 30 dias.

**Critérios de aceite:**
- Dado que a correção foi mesclada em `main`, quando ainda não há evidência de deploy no ambiente observado, então a esteira não deve ser considerada corrigida para fins de contagem da janela de validação.
- Dado que a correção foi implantada, quando se consulta a evidência de rollout, então é possível identificar o commit/versão, o ambiente e a data sem inferência indireta.

## RF-07 — Registrar observabilidade de propagação, reconciliação e despacho

**Descrição:** todo evento relevante para a meta de negócio deve ser
registrável: detecção de participação propagada, reconciliação (automática ou
manual), despacho de agente (indevido ou correto) e consumo associado.

**Fluxo principal:**
1. Uma participação propagada é detectada.
2. O evento de detecção é registrado com issue, board de origem, board propagado e timestamp.
3. A reconciliação (quando ocorre) é registrada com o mesmo nível de detalhe e com o timestamp de conclusão.
4. Caso um despacho indevido ainda ocorra antes da reconciliação, o despacho e seu consumo são registrados.

**Critérios de aceite:**
- Dado que uma propagação foi detectada e reconciliada, quando se consulta o registro, então é possível calcular o tempo entre propagação e reconciliação para aquela issue.
- Dado que 30 dias e ao menos 17 novas relações entre boards se passaram, quando se consulta os registros, então é possível apurar: número de participações propagadas, número de reconciliações automáticas, número de remoções manuais, número de despachos indevidos e créditos consumidos por eles.
- Dado que um despacho indevido ocorre, quando se consulta o registro correspondente, então issue, board indevido, agente, timestamp e resultado (concluído/erro, com consumo se houver) estão disponíveis.

## RF-08 — Tratar resíduos da janela do incidente sem confundir com regressão nova

**Descrição:** as 17 participações e os 7 despachos indevidos já ocorridos em
25–26/08/2026 devem ser tratáveis como resíduo conhecido, distinto de uma
nova ocorrência durante a janela de validação de 30 dias.

**Fluxo principal:**
1. O baseline de resíduos conhecidos (issues #221–#223, #226–#229 e #231–#240) é registrado antes do início da janela de validação.
2. Qualquer nova propagação ou despacho indevido identificado após o início da janela é contado como nova ocorrência, não como resíduo.

**Critérios de aceite:**
- Dado que a janela de validação de 30 dias se inicia, quando um resíduo da janela do incidente é identificado, então ele não é contado como falha da nova entrega.
- Dado que uma nova participação propagada ocorre após o início da janela de validação, quando ela é comparada ao baseline de resíduos, então é corretamente classificada como nova ocorrência sujeita à meta de zero execução indevida.

## RF-09 — Suportar a contingência de suspensão temporária de novos vínculos

**Descrição:** a esteira deve suportar, como contingência temporária já
autorizada pelo dono, um modo em que a criação de novos vínculos pai/filho
entre issues de boards distintos é suspensa, sem remover vínculos já
existentes nem alterar hierarquia previamente estabelecida.

**Fluxo principal:**
1. Um operador ativa a contingência.
2. Uma tentativa de estabelecer um novo vínculo pai/filho entre issues de boards distintos é impedida ou sinalizada para intervenção humana, enquanto a contingência está ativa.
3. Vínculos existentes antes da ativação permanecem intactos e continuam sendo processados normalmente.

**Fluxo alternativo — vínculo dentro do mesmo board:**
1. Um vínculo pai/filho é estabelecido entre issues do mesmo board.
2. A contingência não impede esse vínculo, pois ele não aciona o efeito de propagação entre boards.

**Critérios de aceite:**
- Dado que a contingência está ativa, quando uma nova relação pai/filho entre issues de boards distintos é solicitada, então ela é impedida ou sinalizada, e não é executada silenciosamente.
- Dado que a contingência está ativa, quando uma relação pai/filho é solicitada entre issues do mesmo board, então ela é processada normalmente.
- Dado que a contingência é desativada, quando novas relações entre boards são solicitadas, então o comportamento normal de prevenção/reconciliação (RF-01 a RF-05) volta a se aplicar sem exigir novo deploy.

## Fora de escopo (explícito)

- Definição de arquitetura, API, classes, algoritmo de detecção ou estratégia de persistência (etapa técnica).
- Prototipagem ou implementação de qualquer mecanismo.
- Quebra em stories.
- Tratamento dos pares de issues duplicadas sem relação pai/filho (#204/#210 a #208/#214) — fora do baseline deste épico, conforme decisão de negócio registrada em `problem-space.md`.
- Limpeza dos resíduos já materializados de incidentes anteriores (#84/#85/#86) — operação manual à parte, não coberta por este baseline.
- Escolha de mecanismo técnico de implantação ou de detecção para a contenção (RF-09) — apenas o comportamento observável é especificado aqui.
