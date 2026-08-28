# Regras de Negócio — Integridade de issues entre boards

Status: baseline de requisitos
Owner: requirements
Last updated: 2026-08-26

## Inputs
- `doc/product/integridade-de-issues-entre-boards/vision.md`
- `doc/product/integridade-de-issues-entre-boards/problem-space.md`
- `doc/product/integridade-de-issues-entre-boards/epicos.md`
- Histórico de entrevista com o dono (issue #230, 2026-08-26)
- `doc/requirements/integridade-de-issues-entre-boards/functional-requirements.md`
- `doc/requirements/integridade-de-issues-entre-boards/glossary.md`
- `doc/incidente/sub-issues-propagadas/ticket.md` (correção anterior, já em `main`, recorrente)

Este documento refina, para uso de arquitetura/engenharia/QA, as regras de
negócio implícitas em `vision.md`/`problem-space.md` e nos requisitos
funcionais RF-01 a RF-09. Não define arquitetura, tecnologia, classes ou
estratégia de persistência — apenas o comportamento de negócio exigido e seu
tratamento nas bordas.

## RN-B01 — Participação sem prova de intenção nunca é executável

**Descrição:** uma participação (item de Project V2) só pode se tornar
elegível a despacho de agente depois que sua intencionalidade for confirmada.
Na ausência dessa confirmação, a participação é tratada como suspeita de
propagação, não como issue nova legítima.
**Contexto:** aplica-se à avaliação de elegibilidade antes de `keep_task`
considerar qualquer participação recém-observada em um board.
**Exceções:** a criação original de uma issue em um board (fluxo normal de
`create-up`/`create-down`, sem relação pai/filho envolvida) já é, por
definição, intencional e não precisa de confirmação adicional.
**Comportamento na borda:** enquanto a intencionalidade não é confirmada, a
participação permanece em estado de espera — não é removida por padrão e não
é executada por padrão. A decisão entre "reconciliar" e "manter como issue
legítima" depende da prova de propagação (RN-B02), nunca de um prazo por si
só decorrido.
**Rastreamento:** referencia RF-01. Ver `glossary.md` — "Participação não
intencional (propagação)".

## RN-B02 — Prova de propagação exige presença anterior em outro board configurado

**Descrição:** uma participação sem `Status` só pode ser classificada como
propagação (e, portanto, candidata a reconciliação) quando a mesma issue já
está registrada, com coluna conhecida, em outro board presente no `pipe.yml`.
**Contexto:** aplica-se à decisão de reconciliar automaticamente uma
participação recém-detectada, tanto no fluxo de vínculo (`_add_sub_issue`)
quanto na descoberta remota (`create-down`).
**Exceções:** um snapshot local de board que não está mais configurado em
`pipe.yml` não serve como prova. A simples presença de um campo `parent`
isolado, sem essa prova de presença em outro board configurado, também não
basta.
**Comportamento na borda:** quando a prova não pode ser obtida (por exemplo,
por falha transitória na consulta ao outro board), a participação permanece
em espera (RN-B01) em vez de ser tratada como issue nova por omissão — o
padrão seguro é não despachar, não descartar a suspeita.
**Rastreamento:** referencia RF-01, RF-02. Ver `glossary.md` — "Prova de
propagação", "Board configurado".

## RN-B03 — Reconciliação nunca altera a relação pai/filho

**Descrição:** o ato de reconciliar uma participação não intencional (remover
do board indevido ou impedir seu despacho) não pode, em nenhuma circunstância,
remover, modificar ou invalidar a relação pai/filho nativa que originou a
propagação.
**Contexto:** aplica-se a toda operação de reconciliação, automática ou
assistida por operador.
**Exceções:** nenhuma. A relação pai/filho é o motivo de existir da
propagação, não seu efeito colateral a ser eliminado.
**Comportamento na borda:** se uma operação de reconciliação, por qualquer
falha, arriscar remover a relação pai/filho junto com a participação, a
operação inteira deve ser abortada em vez de prosseguir parcialmente — é
preferível manter uma participação indevida ainda não reconciliada do que
perder a hierarquia.
**Rastreamento:** referencia RF-03. Amarra direta com a garantia equivalente
já validada no incidente #88 (preservação da relação ao remover a
participação propagada).

## RN-B04 — Participação multi-board exige autorização explícita e verificável

**Descrição:** uma issue só pode permanecer elegível em mais de um board
simultaneamente quando existir um registro explícito de autorização para
aquela participação — nunca por ausência de reconciliação ou por omissão de
verificação.
**Contexto:** aplica-se à avaliação de qualquer participação em mais de um
board, presente ou futura.
**Exceções:** nenhum caso de uso real está confirmado pelo dono até
26/08/2026 (ver histórico da issue #230); a regra vale preventivamente para
quando um caso surgir, sem exigir nova entrega de negócio.
**Comportamento na borda:** a ausência de autorização explícita é o padrão —
uma participação em dois boards sem autorização registrada deve ser tratada
como propagação suspeita (RN-B01), nunca interpretada como multi-board
intencional por padrão.
**Rastreamento:** referencia RF-04.

## RN-B05 — Resíduo da janela do incidente não conta contra a meta de validação

**Descrição:** as 17 participações e os 7 despachos indevidos ocorridos em
25–26/08/2026 (issues #221–#223, #226–#229 e #231–#240) compõem um baseline de
resíduo conhecido, anterior à entrega, e não podem ser contados como falha da
nova entrega durante a janela de validação de 30 dias.
**Contexto:** aplica-se à apuração de métricas de sucesso (zero execução
indevida, zero remoção manual, zero resíduo novo) descritas em `vision.md` e
no RF-08.
**Exceções:** se qualquer uma dessas 17 issues sofrer uma **nova** propagação
ou um **novo** despacho indevido após o início da janela de validação (por
exemplo, por uma nova relação pai/filho estabelecida depois do deploy), esse
evento novo conta normalmente contra a meta — o resíduo cobre apenas os fatos
já ocorridos até 26/08/2026.
**Comportamento na borda:** a fronteira entre "resíduo" e "nova ocorrência" é
temporal e definida pelo início da janela de validação (RN-B08), não pelo
número da issue — não se deve excluir uma issue inteira do escopo de medição
apenas por ela já aparecer na lista de resíduo.
**Rastreamento:** referencia RF-08.

## RN-B06 — Limpeza de resíduo materializado é operação manual, fora desta entrega

**Descrição:** resíduos já materializados localmente por incidentes
anteriores (#84/#85/#86) e as 17 participações já removidas manualmente em
25–26/08/2026 não são eliminados retroativamente pela prevenção/reconciliação
entregue neste épico; a limpeza desses resíduos é operação manual separada,
com a esteira parada.
**Contexto:** aplica-se à definição de "concluído" para este épico — a
entrega previne e reconcilia novas ocorrências, mas não varre o estado já
existente antes de sua disponibilização.
**Exceções:** nenhuma. Se a limpeza retroativa vier a ser necessária, é um
esforço distinto, já registrado como fora de escopo tanto no incidente #88
quanto neste épico.
**Comportamento na borda:** a existência de resíduo histórico não pode ser
usada como evidência de que a prevenção nova falhou — os dois fatos são
independentes e devem ser reportados separadamente (ver RN-B05).
**Rastreamento:** referencia seção "Fora de escopo" de `functional-requirements.md`.

## RN-B07 — Contingência de suspensão é temporária e não retroativa

**Descrição:** a contingência de suspender novos vínculos pai/filho entre
boards distintos, autorizada pelo dono em 26/08/2026, é uma medida temporária
de contenção — não substitui a prevenção definitiva (RF-01 a RF-05) e não se
aplica a vínculos já estabelecidos antes de sua ativação.
**Contexto:** aplica-se ao comportamento descrito em RF-09: ativação,
vigência e desativação da contingência.
**Exceções:** vínculos pai/filho dentro do mesmo board nunca são afetados,
pois não acionam o efeito de propagação entre Projects que motiva a
contingência.
**Comportamento na borda:** desativar a contingência não exige novo deploy —
o comportamento normal de prevenção/reconciliação deve retomar
imediatamente. Enquanto ativa, uma tentativa de novo vínculo entre boards
distintos deve ser impedida ou sinalizada para intervenção humana, nunca
executada silenciosamente como se a contingência estivesse inativa.
**Rastreamento:** referencia RF-09.

## RN-B08 — Evidência de rollout é pré-condição para iniciar a janela de validação

**Descrição:** a janela de validação de 30 dias e de ao menos 17 novas
relações entre boards só pode começar a ser contada a partir do momento em
que existe evidência verificável (commit/versão, ambiente, data) de que a
correção está de fato em execução no ambiente relevante — merge em `main`,
isoladamente, não inicia a contagem.
**Contexto:** aplica-se à apuração das métricas de sucesso de `vision.md` e
ao fechamento do épico.
**Exceções:** nenhuma. O precedente que motiva esta regra é exatamente o
deste épico: o PR #102 foi mesclado em 19/08/2026 e a recorrência ocorreu
mesmo assim em 25–26/08/2026, porque merge não prova execução em produção.
**Comportamento na borda:** se a evidência de rollout for perdida ou não
puder ser produzida, a janela de validação não pode ser declarada iniciada
nem concluída — a ausência de evidência é tratada como bloqueio de
fechamento, não como aprovação por omissão.
**Rastreamento:** referencia RF-06 e RF-08. Ver `glossary.md` — "Evidência de
rollout", "Janela de validação".

## RN-B09 — Toda apuração de meta exige registro auditável, não inferência

**Descrição:** as métricas de sucesso (zero execução indevida, 100% de
reconciliação antes de `Status` executável, zero remoção manual, zero
resíduo novo) só podem ser declaradas atingidas com base em registros
auditáveis de detecção, reconciliação e despacho — nunca por ausência de
reclamação do dono ou por amostragem informal.
**Contexto:** aplica-se ao fechamento da janela de validação de 30 dias e à
apuração de créditos evitados.
**Exceções:** nenhuma. O relato do dono foi tratado como hipótese e
confrontado com API do GitHub e logs durante a diligência de negócio
(ver `problem-space.md`); a mesma exigência de confrontação com evidência se
aplica ao fechamento da validação.
**Comportamento na borda:** créditos evitados só podem ser calculados a
partir de despachos indevidos efetivamente impedidos e do consumo médio
observado (baseline comprovado: 20,35 créditos em cinco execuções
concluídas) — não há base para estimar ROI financeiro sem preço real por
crédito e horas de limpeza medidas.
**Rastreamento:** referencia RF-07.

## RN-B10 — Cobertura por comportamento de fluxo, não por par de boards hardcoded

**Descrição:** a prevenção e a reconciliação devem se aplicar a qualquer par
de fluxos com relação pai/filho hierárquica (hoje: Story→Epic, Task→User
Story), e a qualquer novo par que venha a existir no futuro, sem exigir
tratamento específico codificado para cada combinação de boards.
**Contexto:** aplica-se ao comportamento observável exigido de qualquer
solução técnica proposta na etapa de arquitetura.
**Exceções:** nenhuma. Esta regra existe porque a amostra de negócio já
comprovou o efeito em dois pares distintos (Stories de #93/#91 propagadas
para Epics; Tasks de #226/#228/#229 propagadas para User Stories) com o
mesmo mecanismo subjacente do GitHub.
**Comportamento na borda:** a introdução de um novo board ou de um novo nível
de hierarquia no `pipe.yml` não deve exigir alteração de regra de negócio
para que a prevenção continue válida — apenas configuração do board em si.
**Rastreamento:** referencia RF-05.

## RN-B11 — Isolamento entre boards não altera relações válidas entre eles

**Descrição:** a fronteira de execução por board é sobre elegibilidade de
despacho de agente, não sobre a existência das relações pai/filho ou
`blocked_by`/`blocks` entre issues de boards distintos, que continuam válidas
e sincronizadas normalmente.
**Contexto:** aplica-se para não confundir "isolar a execução" com "isolar os
dados" — issues de boards diferentes continuam podendo se relacionar
(hierarquia, bloqueio) sem que isso implique participação cruzada indevida.
**Exceções:** nenhuma.
**Comportamento na borda:** um board que bloqueia outro (`/blocks`) ou é
bloqueado por outro (`/blocked_by`) continua funcionando entre boards
distintos exatamente como hoje; apenas a propagação de **participação** (item
de Project V2) é o alvo desta regra, não o vínculo lógico de bloqueio.
**Rastreamento:** referencia RF-01, RF-03; decorre da distinção entre
"relação pai/filho" e "participação" definida em `glossary.md`.
