# Casos de Teste — Integridade de participação de issues entre quadros de trabalho

- **Issue:** #310
- **Story relacionada:** confiabilidade; bloqueia #316
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-10-05
- **Branch:** `feature/310-integridade_de_participacao_de_issues_entre_quadros_de_trabalho`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA) da
> issue #310 e dos seus 23 cenários obrigatórios (CT-01 a CT-23). Cada caso tem
> resultado esperado explícito e verificável. Os testes são da suíte Python do
> motor (pytest, em `tests/`).

---

## Contexto de arquitetura (baseline do código atual)

Confirmado por leitura do código: `participation_intent`,
`safety.cross_board_parent_links`, o rótulo `board-intent-<id>` e o evento
`rollout_evidence` **não existem** hoje — o escopo é genuinamente novo.

Pontos de partida reaproveitáveis:

- `src/adapters/github_board.py::_remove_propagated_items_without_status` —
  pós-hook que já consulta `projectItems`/`fieldValues` via GraphQL e remove,
  por `deleteProjectV2Item`, itens sem `Status` de projects diferentes do
  informado. É chamado por `_add_sub_issue` (acionado por `set_parent` /
  `set_children`). **Limitação confirmada:** só age quando o item chega sem
  `Status`; um item que já chegue com coluna não é tocado — é exatamente a
  brecha do RN-06.
- `src/core/sync.py::_propagation_proof(board_id, issue_id, config)` — função
  pura (sem rede) que decide, a partir do **snapshot local**, se uma issue tem
  prova de propagação (presença com coluna conhecida em outro board
  configurado). Usada pelo guard em `_apply_create_down`. É o parente mais
  próximo da futura `classify_participation` — mas resolve apenas o caso
  `create-down`, não cobre `change-down`/coluna preenchida, e não produz um
  campo persistente de intenção.
- `src/core/board.py::BoardPort` já define `remove_from_board` (abstrato,
  default `log.warning` nos adapters que não implementam); `list_participations`
  **não existe** e precisa ser criado (RF-06/RF-07/RF-08 exigem a porta
  `list_participations(issue_id)`).
- `src/core/snapshot.py::Snapshot` persiste `issues: [{...}]` por board; cada
  issue é um dict livre — adicionar `participation_intent` é compatível com o
  formato atual (campo ausente = legado, conforme CT-11/12/13).
- `src/core/config.py` segue o padrão `validate_*`/`ConfigError` citando o
  caminho da chave (`validate_retry`, `validate_registro`,
  `validate_agent_circuit_break`, `validate_column_migrations`) — o mesmo
  padrão vale para `safety.cross_board_parent_links` (CA-13/CT-20).
- `src/core/agent_circuit_break.py` é o precedente mais próximo de estado
  persistente protegido (`.pipe/agentCircuitBreak.json`, nunca exposto ao
  agente) — mesmo padrão esperado para o estado de retentativa de
  `participation_intent` não resolvida (se persistido fora do snapshot) e para
  a contingência relida sem cache.
- `src/__main__.py::keep_task` filtra por `status == 'ok'`, bloqueio
  (`_is_blocked`), cooldown; **não há hoje nenhum filtro por intenção de
  participação** — é o ponto de inserção do gate final (RF-10/CT-08/CT-09).
- `src/__main__.py::board_startup_sync` já reconcilia a estrutura remota
  **antes** de gravar o snapshot (ordem fixada pela entrega #305); a migração
  de legados (RF-11/CT-11/12/13) deve rodar no startup, antes da primeira
  `keep_task`, seguindo essa mesma ordenação.
- `src/core/log.py::log.info`/`log.warning` gravam em `logs/<data>.json` com
  campos estruturados via `**extra` — veículo natural para os eventos
  `participation_classified`, `participation_reconciled`,
  `participation_reconcile_failed`, `participation_removed_externally`,
  `dispatch_blocked_unconfirmed_intent`, `cross_board_link_blocked` e
  `rollout_evidence`.

> **Decisão de design NÃO fixada pela QA (é do desenvolvimento):** nome e
> localização exatos do módulo de classificação pura (ex.:
> `src/core/participation.py`), assinatura de `classify_participation(...)`, de
> `list_participations`/`remove_from_board` no adapter real, e onde a migração
> de legados é chamada no `startup()`/`board_startup_sync()`. Os casos abaixo
> testam **comportamento e invariantes observáveis**, não assinaturas. Onde um
> caso cita um símbolo, é o alvo **provável**; se o desenvolvimento adotar outro
> nome, o caso vale sobre o comportamento equivalente — igual à convenção já
> usada em `doc/quality/retirada-segura-colunas-migracao/test-cases.md`.

---

## Rastreabilidade (CA → casos)

| CA / Cenário | Requisito | Regra | Caso(s) |
|---|---|---|---|
| CA-1 / CT-01 — reconciliação imediata pós-vínculo | RF-07 | RN-01, RN-03 | CT-01, CT-01b, CT-01a, CT-01c |
| CA-2 / CT-02, CT-03 — reconciliação na descoberta remota (com/sem coluna) | RF-08, RF-10 | RN-01, RN-06 | CT-02, CT-03 |
| CA-3 / CT-04 — autorização explícita multi-quadro | RF-04, RF-06 | RN-04 | CT-04 |
| CA-4 / CT-05 — evidência ambígua / falha transitória | RF-06, RF-09 | RN-02, RN-09 | CT-05, CT-15, CT-16 |
| CA-5 / CT-06 — determinismo | RF-06 | RN-07 | CT-06 |
| CA-6 / CT-07 — rótulo com quadro inexistente | RF-06 | RN-04 | CT-07 |
| CA-7 / CT-08 — gate confirma candidatos (origem/autorizada) | RF-10 | RN-01 | — (parte de CT-08) |
| CA-8 / CT-08 — gate bloqueia intenção não confirmada | RF-10 | RN-01 | CT-08, CT-10 |
| CA-9 / CT-09 — gate sem rede | RF-10, RNF-04 | — | CT-09 |
| CA-10 / CT-11, CT-12, CT-13 — migração de legados no startup | RF-11 | RN-01 | CT-11, CT-12, CT-13 |
| CA-11 / CT-21 — evidência de execução no startup | RF-14 | RN-10 | CT-21 |
| CA-12 / CT-18 — contingência bloqueia vínculo cross-board | RF-12 | RN-08 | CT-18 |
| CA-13 / CT-20 — validação da chave de contingência | RF-12 | — | CT-20 |
| CA-14 / observabilidade geral | RF-13 | RN-09 | CT-14, CT-15, CT-22, CT-23 |
| CA-15 / CT-22 — remoção externa | RF-13 | — | CT-22 |
| CA-16 / CT-02 (par genérico) | RF-05 | RNF-07 | CT-02-generico |
| CA-17 / apuração sobre registros | — | RN-05, RN-11 | CT-14, CT-17 |

> Observação de cobertura: os 17 CAs mapeiam de forma limpa sobre a arquitetura
> core/adapters existente (porta de board, snapshot, fila, log estruturado),
> sem lacuna que exija devolver ao planejamento (`revisar-escopo`). O
> detalhamento (requisitos funcionais, regras de negócio, contratos de
> configuração/eventos, cenários CT-01 a CT-23, entregáveis) já está completo e
> sem contradição interna — decidido com os critérios de aceitação e a suíte
> existente, conforme o papel desta etapa.

---

## Convenções para o desenvolvimento (todos os casos automatizados)

- **Offline, sem rede:** usar um `BoardPort`/porta de participações fake
  (padrão de `tests/test_sub_issue_propagation_fix.py` e
  `tests/test_column_withdrawal.py`). O fake expõe `list_participations(issue_id)`
  controlável (o teste prepara a lista de retorno, inclusive levantando
  exceção para simular falha transitória) e `remove_from_board(board_id, issue_id)`
  como espião que registra chamadas.
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` por teste (fixture
  `autouse`), para que `.pipe/` e `logs/` fiquem isolados — mesmo padrão da
  suíte existente.
- **Nunca** fazer `monkeypatch` do próprio símbolo sob teste (lição do
  incidente #106) — a política de classificação é exercitada de verdade; só a
  **porta** (provedor remoto) é fake.
- **Determinismo (CT-06):** o mesmo estado de entrada (config, rótulos,
  presenças, snapshot) deve produzir sempre a mesma classificação,
  independentemente da ordem de chamadas/avaliação — testado embaralhando a
  ordem de entrada e comparando o resultado.
- **Gate sem rede (CT-09):** o dublê de porta usado no teste do gate **falha
  (levanta exceção) se qualquer método for chamado** — não apenas "não
  registra chamadas". Isso prova ausência de I/O, não apenas ausência de uso
  incidental.
- Onde um caso cita um símbolo (`classify_participation`, `list_participations`,
  núcleo de reconciliação, `safety.cross_board_parent_links`), o alvo é
  **provável**; se o desenvolvimento adotar outro nome, o caso vale sobre o
  comportamento equivalente.

---

## Grupo A — Classificação pura de intenção (RF-06, sem I/O de rede)

> Alvo principal: a função pura (ex.: `classify_participation(issue, board_id,
> labels, known_participations, boards_config)` → um dos quatro estados) que
> não faz chamada de rede e é a base de todos os gatilhos de reconciliação.

### CT-04 — Presença autorizada por rótulo válido (com ou sem coluna)

- **CA de origem (CA-3):** "Dada uma issue com rótulo de autorização válido
  para o quadro avaliado, quando é classificada, então o resultado é
  autorizada e a presença não é removida, com coluna vazia ou preenchida."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_participation_classification.py` (novo).
- **Pré-condição:** issue com label `board-intent-<id-do-quadro-avaliado>`
  (ex.: `board-intent-entrega`); quadro `entrega` existe na config. Dois
  sub-casos: presença sem `Status` e presença com `Status` preenchido.
- **Passos:**
  1. Classificar a participação da issue no quadro `entrega` com o rótulo
     presente, em cada sub-caso de coluna.
- **Resultado esperado:** resultado `authorized` nos dois sub-casos (coluna
  vazia e preenchida); nenhuma remoção é acionada por quem consome a
  classificação.
- **Observações:** cobre RF-04/RF-06 e RN-04 (coluna não influencia o
  resultado quando há autorização).

### CT-07 — Rótulo de autorização com quadro inexistente é ignorado

- **CA de origem (CA-6):** "Dado um rótulo de autorização que nomeia um quadro
  inexistente, quando a autorização é avaliada, então o rótulo é ignorado e um
  aviso é registrado."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_participation_classification.py`
- **Pré-condição:** issue com label `board-intent-naoexiste`, onde `naoexiste`
  não é nenhum board configurado; nenhuma outra evidência de propagação.
- **Passos:**
  1. Classificar a participação da issue no quadro avaliado.
  2. Verificar o log emitido.
- **Resultado esperado:** o rótulo **não** autoriza (classificação segue pelas
  demais regras — origem/propagada/não resolvida conforme o resto da
  evidência, nunca `authorized` por esse rótulo); é emitido um aviso (`WARNING`)
  citando o rótulo e o quadro inexistente.
- **Observações:** cobre RN-04. Rótulo malformado não deve lançar exceção —
  apenas ser ignorado com aviso.

### CT-01a (classificação) — Propagação detectada por presença anterior com coluna conhecida

- **CA de origem (CA-1, parte de classificação):** presença em outro board
  configurado, com coluna conhecida, classifica como `propagated`.
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_participation_classification.py`
- **Pré-condição:** issue já confirmada (`origin`) no board `historias`,
  coluna `doing`; nova presença detectada no board `epicos`, sem rótulo de
  autorização para `epicos`.
- **Passos:** classificar a participação no board `epicos`.
- **Resultado esperado:** resultado `propagated`.
- **Observações:** cobre RN-01/RN-02 (prova de propagação exige presença
  anterior **com coluna conhecida** em outro board **configurado**).

### CT-01c — Presença isolada sem prova de propagação não é removida por omissão

- **CA de origem (RN-02):** "Relação pai/filho isolada não prova [propagação];
  sem prova, a presença fica não resolvida (espera), nunca vira issue nova por
  omissão."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_participation_classification.py`
- **Pré-condição:** issue nova, com `parent` em outro board, mas **sem**
  nenhuma presença anterior confirmada em board configurado (snapshot não
  rastreia a issue em nenhum outro board) e sem rótulo de autorização.
- **Passos:** classificar a participação.
- **Resultado esperado:** resultado `unresolved` — **nunca** `origin` por
  omissão de prova, e **nunca** `propagated` sem a prova exigida (presença
  confirmada com coluna conhecida em outro board configurado).
- **Observações:** distingue de CT-01 (que tem prova) e evita o falso-positivo
  simétrico (remover sub-issue legítima nova) citado nos riscos da issue.

### CT-origem-01 — Primeira presença em quadro configurado é classificada como origem

- **CA de origem (estados de classificação, tabela "origem"):** "Primeira
  presença em quadro configurado, sem outra presença confirmada."
- **Tipo:** unitário (política)
- **Arquivo/alvo:** `tests/test_participation_classification.py`
- **Pré-condição:** issue nova, criada diretamente no board avaliado, sem
  relação pai/filho envolvida, sem presença conhecida em nenhum outro board.
- **Passos:** classificar a participação.
- **Resultado esperado:** resultado `origin`.
- **Observações:** cobre a exceção de RN-01 ("criação original de uma issue em
  um quadro, sem relação pai/filho envolvida, já é intencional").

### CT-06 — Determinismo da classificação

- **CA de origem (CA-5):** "Dado o mesmo estado de configuração, rótulos e
  presenças, quando a classificação roda em ordens diferentes, então o
  resultado é idêntico."
- **Tipo:** unitário (política), parametrizado
- **Arquivo/alvo:** `tests/test_participation_classification.py`
- **Pré-condição:** um conjunto fixo de N issues com presenças/rótulos
  variados (origem, autorizada, propagada, não resolvida).
- **Passos:**
  1. Classificar todas as N issues em uma ordem.
  2. Embaralhar a ordem (ex.: `random.shuffle` com seed fixa e também ordem
     invertida) e reclassificar.
  3. Comparar os resultados issue a issue.
- **Resultado esperado:** o resultado por issue é **idêntico** em todas as
  ordens testadas.
- **Observações:** cobre RN-07/RNF-05. A função não deve ter efeito colateral
  compartilhado entre chamadas (sem cache mutável entre issues na mesma
  execução que mude o resultado por ordem).

---

## Grupo B — Reconciliação (imediata e tardia), falha e retentativa

> Alvo: os dois gatilhos de reconciliação (RF-07 pós-vínculo, RF-08 descoberta
> remota) e o comportamento de retentativa sem bloqueio de fila (RF-09).

### CT-01 — Reconciliação imediata pós-vínculo preserva a hierarquia

- **CA de origem (CA-1):** "Dado um vínculo pai/filho entre issues de quadros
  distintos, quando a filha é consultada logo após o vínculo e tem presença
  propagada no quadro do pai, então essa presença é removida antes de a
  operação de vínculo ser considerada concluída, e a relação pai/filho
  permanece íntegra."
- **Tipo:** integração (política + porta fake)
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py` (novo).
- **Pré-condição:** vínculo pai/filho recém-criado entre issue do board
  `historias` (pai) e issue do board `tarefas` (filha); a porta fake, ao
  consultar `list_participations` da filha, devolve uma presença no board do
  pai (`historias`) sem autorização.
- **Passos:**
  1. Disparar a reconciliação imediata pós-vínculo para a filha.
  2. Verificar chamadas da porta fake e o estado da relação pai/filho.
- **Resultado esperado:** `remove_from_board(historias, filha)` é chamado
  **antes** de a operação de vínculo ser considerada concluída; a relação
  pai/filho nativa permanece intacta (nenhuma chamada que a desfaça); nenhum
  agente é despachado sobre a presença removida.
- **Observações:** cobre RF-07/RF-03 e RN-03.

### CT-01b — Múltiplos filhos: reconciliação de cada vínculo preserva as demais relações

- **CA de origem (CT-14 do detalhamento):** "Reconciliação preserva hierarquia
  com múltiplos filhos."
- **Tipo:** integração (política + porta fake)
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py`
- **Pré-condição:** um pai no board `epicos` com três filhos em boards
  diferentes (`historias`, `tarefas`, `historias`), cada um com presença
  propagada no board do pai.
- **Passos:**
  1. Reconciliar os três vínculos em sequência.
  2. Verificar que cada remoção afeta só o item correspondente.
- **Resultado esperado:** as três relações pai/filho permanecem íntegras após
  reconciliar cada uma; cada remoção afeta apenas a presença propagada
  correspondente, sem interferir nas demais.
- **Observações:** cobre RF-07/RF-03/RN-03 em escala.

### CT-02 — Reconciliação tardia na descoberta remota (sem coluna)

- **CA de origem (CA-2):** "Dada uma presença nova na descoberta remota, com
  ou sem coluna, quando é classificada como propagada, então é removida, o
  evento só é consumido após a remoção, e nenhum agente é despachado sobre
  ela."
- **Tipo:** integração (política + fila)
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py`
- **Pré-condição:** descoberta remota encontra uma presença nova sem `Status`
  cuja classificação resulta `propagated` (prova de presença anterior em outro
  board configurado).
- **Passos:**
  1. Processar o item de descoberta remota.
  2. Verificar ordem: classificação → remoção → consumo do evento.
- **Resultado esperado:** `remove_from_board` é chamado; o evento da fila só é
  marcado como consumido **após** a remoção concluir com sucesso; nenhum
  agente é despachado sobre essa presença.
- **Observações:** cobre RF-08 e a cláusula "o evento só é consumido após a
  remoção" do CA-2.

### CT-03 — Reconciliação tardia com coluna preenchida (coluna não isenta)

- **CA de origem (CA-2, RN-06):** "Coluna (Status) preenchida ou vazia não
  prova intenção; a classificação é idêntica para presenças com e sem
  coluna."
- **Tipo:** integração (política + fila)
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py`
- **Pré-condição:** mesmo cenário de CT-02, mas a presença propagada **já
  chega com `Status` preenchido** (reproduz a brecha descrita no "ponto de
  partida atual" da issue).
- **Passos:** processar o item; comparar com o resultado de CT-02.
- **Resultado esperado:** mesmo resultado de CT-02 — `propagated`, removida,
  nenhum despacho — **mesmo com coluna preenchida**. A classificação é
  idêntica à de CT-02 (RN-06).
- **Observações:** este é o caso que a proteção parcial atual
  (`_remove_propagated_items_without_status`, que só age sem `Status`) **não**
  cobre — valida a lacuna fechada por esta entrega.

### CT-05 — Falha transitória de consulta classifica como não resolvida

- **CA de origem (CA-4):** "Dada evidência ambígua ou falha transitória de
  consulta, quando processada, então o resultado é não resolvida: sem
  arquivos criados, sem remoção, adiada e reavaliada depois sem consumir
  tentativa."
- **Tipo:** integração (política + porta fake)
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py`
- **Pré-condição:** `list_participations` da porta fake levanta uma exceção
  (erro tipado simulando falha de transporte) ao ser chamada para a issue
  avaliada.
- **Passos:**
  1. Processar a descoberta/reconciliação para essa issue.
  2. Verificar arquivos locais, chamadas de remoção e estado de retentativa.
- **Resultado esperado:** resultado `unresolved`; **nenhum** arquivo local é
  criado; `remove_from_board` **não** é chamado; o item é adiado com
  `next_attempt_at` futuro; a tentativa **não é consumida/incrementada** rumo a
  descarte.
- **Observações:** cobre RN-02/RN-09. A exceção propaga como erro tipado, não
  é silenciada como aviso que descarta o caso.

### CT-15 — Falha na remoção propaga erro tipado e preserva a hierarquia

- **CA de origem (comportamento em falha — "Remoção de presença propagada
  falha na reconciliação imediata"):** "Propaga erro tipado; a relação
  pai/filho já criada é preservada; não desfaz nada."
- **Tipo:** integração (política + porta fake)
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py`
- **Pré-condição:** classificação resulta `propagated`; `remove_from_board` da
  porta fake levanta uma exceção.
- **Passos:**
  1. Disparar a reconciliação imediata pós-vínculo.
  2. Verificar propagação da exceção e estado da relação pai/filho.
- **Resultado esperado:** a exceção **propaga** (erro tipado, não é engolida
  como aviso); a relação pai/filho criada antes **permanece intacta**; nenhuma
  operação parcial arrisca a hierarquia; evento
  `participation_reconcile_failed` é registrado com tentativa e tipo de erro.
- **Observações:** cobre RN-03 ("se qualquer etapa arriscar afetar a relação
  pai/filho, a operação inteira é abortada em vez de prosseguir
  parcialmente") e RN-09.

### CT-16 — Não resolvida é adiada sem consumir tentativa; outros itens seguem processados

- **CA de origem (RF-09, RNF-01):** "Presenças não resolvidas ou com falha
  transitória são adiadas e reavaliadas em ciclos posteriores, sem bloquear
  outras issues da fila e sem consumir tentativa que leve a descarte."
- **Tipo:** integração (fila)
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py`
- **Pré-condição:** fila com um item não resolvido (ex.: cenário de CT-05) e
  outros itens elegíveis de issues distintas.
- **Passos:**
  1. Processar um ciclo da fila contendo o item não resolvido e os demais.
  2. Verificar que os demais itens progridem normalmente.
- **Resultado esperado:** o item não resolvido recebe `next_attempt_at` e
  permanece pendente; os **demais** itens da fila (mesma ou outra issue) são
  processados normalmente no mesmo ciclo — isolamento de falha por item
  (RNF-01).
- **Observações:** cobre RF-09/RNF-01.

### CT-17-retentativa — Reavaliação após vencer o prazo (adiamento)

- **CA de origem (RF-09, tabela "Adiamento sem bloqueio"):** "Itens ainda não
  vencidos são pulados sem consumir tentativa; ao vencer, voltam a ser
  elegíveis para nova classificação."
- **Tipo:** unitário (fila/retentativa)
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py`
- **Pré-condição:** item adiado com `next_attempt_at` no futuro; depois,
  simular avanço do relógio (ou configurar `next_attempt_at` no passado) e
  reavaliar.
- **Passos:**
  1. Com `next_attempt_at` no futuro, rodar um ciclo — verificar que o item é
     pulado.
  2. Com `next_attempt_at` vencido, rodar outro ciclo.
- **Resultado esperado:** no passo 1, o item é pulado (nenhuma reclassificação
  ocorre, nenhuma tentativa é consumida). No passo 2, o item volta a ser
  elegível: se a nova classificação for `origin`/`authorized`, segue para
  materialização normal; se `propagated`, segue para reconciliação; se ainda
  `unresolved`, recebe novo adiamento.
- **Observações:** cobre RF-09 e a linha "Reavaliação após vencer o prazo"
  (CT-17 do detalhamento da issue).

---

## Grupo C — Gate final na seleção de tarefas (RF-10) e migração de legados (RF-11)

### CT-08 — Gate confirma candidatos e bloqueia intenção não confirmada

- **CA de origem (CA-7, CA-8):** "Dada uma issue com intenção confirmada
  (origem ou autorizada) no snapshot, quando a seleção de tarefas a avalia,
  então ela permanece candidata normalmente." / "Dada uma issue com intenção
  propagada, não resolvida ou ausente, quando a seleção de tarefas a avalia,
  então ela é ignorada para seleção e para avanço automático, e um evento de
  despacho bloqueado é registrado de forma deduplicada."
- **Tipo:** unitário (gate), parametrizado
- **Arquivo/alvo:** `tests/test_participation_gate.py` (novo), exercitando o
  gate inserido em `keep_task` (ou função equivalente extraída).
- **Pré-condição:** quatro issues elegíveis por todos os demais filtros
  (coluna com agente, não bloqueada, fora de cooldown), diferindo apenas em
  `participation_intent`: `origin`, `authorized`, `propagated`, ausente.
  Sub-caso adicional: `unresolved`.
- **Passos:**
  1. Rodar `keep_task` (ou o gate isoladamente) para cada issue.
  2. Verificar quais são retornadas como candidatas.
- **Resultado esperado:** `origin` e `authorized` permanecem candidatas
  normalmente (nenhuma mudança de comportamento); `propagated`, `unresolved` e
  ausente são **ignoradas** para seleção e para avanço automático; para cada
  uma destas, é emitido o evento `dispatch_blocked_unconfirmed_intent`.
- **Observações:** cobre RF-10 e as regras de RN-01.

### CT-10 — Deduplicação do evento de despacho bloqueado

- **CA de origem (CT-10 do detalhamento):** "Duas avaliações seguidas da mesma
  issue na mesma coluna → evento emitido apenas na primeira; reemitido só ao
  mudar de coluna ou reiniciar o processo."
- **Tipo:** unitário (gate)
- **Arquivo/alvo:** `tests/test_participation_gate.py`
- **Pré-condição:** issue com intenção `propagated` na coluna `doing`.
- **Passos:**
  1. Avaliar a issue duas vezes seguidas na mesma coluna.
  2. Mover a issue (local) para outra coluna e avaliar de novo.
  3. Reiniciar o estado de deduplicação (simulando novo processo) e avaliar
     de novo na coluna original.
- **Resultado esperado:** o evento `dispatch_blocked_unconfirmed_intent` é
  emitido na 1ª avaliação e **não** na 2ª (mesma issue/coluna); é reemitido ao
  mudar de coluna; é reemitido após reiniciar o processo.
- **Observações:** cobre a cláusula "registrado de forma deduplicada" do CA-8.
  A chave de deduplicação é `(board, coluna, issue)`, análoga à do limitador de
  reexecuções (#306).

### CT-09 — Gate não faz nenhuma chamada de rede

- **CA de origem (CA-9):** "Dado que a seleção de tarefas roda, quando
  avaliada por inspeção/teste, então nenhuma chamada de rede ocorre no
  caminho do gate (verificável por dublê de porta que falha se chamado)."
- **Tipo:** unitário (gate)
- **Arquivo/alvo:** `tests/test_participation_gate.py`
- **Pré-condição:** `BoardPort` fake cujo **qualquer** método levanta
  `AssertionError` se chamado; snapshot já populado com `participation_intent`
  para todas as issues candidatas.
- **Passos:**
  1. Rodar `keep_task` várias vezes, cobrindo os quatro estados de intenção.
- **Resultado esperado:** nenhuma chamada ao dublê ocorre em nenhum dos casos
  — o teste passa sem levantar `AssertionError`.
- **Observações:** cobre RNF-04. Reforça que o gate lê **só** o snapshot
  local.

### CT-11 — Migração de legados: board único vira origem

- **CA de origem (CA-10, CT-11):** "Snapshot legado, issue em um só quadro →
  campo de intenção vira origem."
- **Tipo:** integração (startup)
- **Arquivo/alvo:** `tests/test_participation_migration.py` (novo).
- **Pré-condição:** snapshot de um board com uma issue sem o campo
  `participation_intent`; a issue não aparece em nenhum outro snapshot de
  board configurado.
- **Passos:**
  1. Rodar a migração de legados (função a ser chamada no startup, antes da
     primeira `keep_task`).
  2. Ler o snapshot resultante.
- **Resultado esperado:** `participation_intent` da issue é `origin`.
- **Observações:** cobre RF-11.

### CT-12 — Migração de legados: duplicidade sem autorização vira não resolvida em ambas

- **CA de origem (CA-10, CT-12):** "Mesma issue em dois quadros configurados,
  sem autorização → campo vira não resolvida em ambas; sem escolha automática
  de origem."
- **Tipo:** integração (startup)
- **Arquivo/alvo:** `tests/test_participation_migration.py`
- **Pré-condição:** a mesma issue aparece nos snapshots de dois boards
  configurados, nenhum com `participation_intent`, e sem rótulo
  `board-intent-<id>` para nenhum dos dois.
- **Passos:**
  1. Rodar a migração de legados.
  2. Ler `participation_intent` da issue em cada snapshot.
- **Resultado esperado:** `unresolved` em **ambas** as entradas — a migração
  **não** escolhe automaticamente qual é a origem.
- **Observações:** cobre RF-11 e evita falso-positivo de origem arbitrária.

### CT-13 — Migração de legados: idempotência e não sobrescrita

- **CA de origem (CA-10, CT-13):** "Executar duas vezes; entradas já
  preenchidas → nenhuma entrada já preenchida é alterada; segunda execução
  não muda nada."
- **Tipo:** integração (startup)
- **Arquivo/alvo:** `tests/test_participation_migration.py`
- **Pré-condição:** snapshot misto: uma issue já com `participation_intent`
  (ex.: `authorized`, atribuído manualmente antes da migração) e outra sem o
  campo.
- **Passos:**
  1. Rodar a migração uma vez; registrar o snapshot resultante.
  2. Rodar a migração de novo sobre o resultado.
  3. Comparar os dois snapshots.
- **Resultado esperado:** a entrada já preenchida **nunca** é sobrescrita (nem
  na 1ª nem na 2ª execução); a 2ª execução produz exatamente o mesmo snapshot
  que a 1ª (idempotência).
- **Observações:** cobre RF-11 e a cláusula "campo já presente nunca é
  sobrescrito".

---

## Grupo D — Contingência reversível (`safety.cross_board_parent_links`)

### CT-18 — Contingência ativa recusa vínculo entre quadros distintos; mesmo quadro e vínculos preexistentes seguem intactos

- **CA de origem (CA-12):** "Dada a contingência ativa, quando se solicita um
  novo vínculo entre quadros distintos, então ele é recusado e registrado; um
  vínculo no mesmo quadro e os vínculos preexistentes seguem intactos;
  desativar a contingência restabelece o comportamento normal sem reinício."
- **Tipo:** integração (política + config)
- **Arquivo/alvo:** `tests/test_cross_board_safety.py` (novo).
- **Pré-condição:** `safety.cross_board_parent_links: suspended`; tentativa de
  criar vínculo pai/filho entre issue do board `epicos` e issue do board
  `historias`; vínculo preexistente entre duas issues do mesmo board
  `historias`.
- **Passos:**
  1. Tentar o novo vínculo cross-board com a contingência suspensa.
  2. Tentar um vínculo dentro do **mesmo** board.
  3. Verificar o vínculo preexistente (não deve ser tocado).
- **Resultado esperado:** o vínculo cross-board é **recusado** (nenhuma
  chamada de criação de sub-issue ocorre) e um evento `cross_board_link_blocked`
  é registrado; o vínculo dentro do mesmo board é **permitido** normalmente;
  o vínculo preexistente **permanece intacto** (não é desfeito pela
  contingência).
- **Observações:** cobre RF-12/RN-08.

### CT-19 — Contingência reversível sem reinício (relida do disco, sem cache)

- **CA de origem (CA-12, "Reversibilidade da contingência" RNF-06):** "Ativar/
  desativar a contingência tem efeito a partir do próximo vínculo avaliado,
  sem reinício do processo."
- **Tipo:** integração (política + config)
- **Arquivo/alvo:** `tests/test_cross_board_safety.py`
- **Pré-condição:** processo "em execução" simulado (sem reiniciar o
  interpretador/estado do teste); `pipe.yml` com a chave em `suspended`.
- **Passos:**
  1. Tentar um vínculo cross-board — deve ser recusado.
  2. Alterar o arquivo `pipe.yml` em disco para `enabled` (sem reiniciar nada
     no processo de teste).
  3. Tentar um novo vínculo cross-board.
- **Resultado esperado:** o 1º vínculo é recusado; o 2º (após a alteração em
  disco) é **permitido**, sem qualquer reinicialização de processo ou cache em
  memória que exija recarregar explicitamente a config inteira — a leitura da
  chave usa a data de modificação do arquivo.
- **Observações:** cobre RNF-06 e a cláusula "relida do arquivo a cada
  tentativa de novo vínculo (por data de modificação, sem cache em memória)".

### CT-20 — Validação da chave de contingência rejeita valor inválido

- **CA de origem (CA-13):** "Dada a chave de contingência com valor diferente
  de `enabled`/`suspended`, quando a configuração é validada, então é
  rejeitada com mensagem acionável."
- **Tipo:** unitário (config), parametrizado
- **Arquivo/alvo:** `tests/test_cross_board_safety.py` (ou
  `tests/test_participation_migration.py` — a critério do desenvolvimento,
  desde que cubra `validate_*` em `config.py`).
- **Pré-condição:** sub-casos parametrizados: `"Enabled"` (caixa diferente),
  `" enabled "` (espaços), `"disabled"`, `""`, `123`, `None`, `True`.
- **Passos:** chamar a validação de `safety.cross_board_parent_links` para
  cada sub-caso.
- **Resultado esperado:** cada sub-caso levanta `ConfigError` citando a chave
  `safety.cross_board_parent_links` e o valor recebido; comparação **exata**,
  sem normalizar caixa/espaços — `"Enabled"` e `" enabled "` também são
  rejeitados. Ausência da chave/seção é **válida** e equivale a `enabled`
  (sub-caso adicional, não deve lançar erro).
- **Observações:** cobre CA-13 e a tabela de configuração/contratos da issue.

---

## Grupo E — Observabilidade e evidência de execução

### CT-14 — Eventos de reconciliação (sucesso/falha) com campos mínimos e sem segredos

- **CA de origem (CA-14):** "Dada uma reconciliação bem-sucedida ou falha,
  quando ocorre, então os eventos correspondentes são registrados com os
  campos mínimos e sem segredos."
- **Tipo:** unitário (observabilidade)
- **Arquivo/alvo:** `tests/test_participation_evidence.py` (novo), lendo o
  log do dia em `logs/<data>.json`.
- **Pré-condição:** uma reconciliação bem-sucedida (cenário de CT-01) e uma
  com falha (cenário de CT-15), ambas com issues cujo body contém um marcador
  único (ex.: `CORPO_SECRETO_456`) e um token fictício na config.
- **Passos:**
  1. Provocar as duas reconciliações.
  2. Localizar as linhas `participation_reconciled` e
     `participation_reconcile_failed` no log.
- **Resultado esperado:** `participation_reconciled` contém `issue`,
  `origin_board`, `propagated_board`, `detected_at`, `reconciled_at`;
  `participation_reconcile_failed` contém `issue`, `board`, `attempt`,
  `next_attempt_at`, `error_kind`; **nenhuma** das duas linhas contém o
  marcador do corpo da issue, token/credencial, ou conteúdo de arquivo
  protegido.
- **Observações:** cobre RF-13/RNF-09 e CA-14/CA-23 (segurança).

### CT-21 — Evidência de execução no startup, com campo ausente sinalizado

- **CA de origem (CA-11):** "Dado o início do processo, quando ele sobe,
  então uma evidência de execução com versão, commit, ambiente e início é
  registrada; qualquer campo ausente é registrado explicitamente sem inferir
  sucesso."
- **Tipo:** unitário (startup)
- **Arquivo/alvo:** `tests/test_participation_evidence.py`
- **Pré-condição:** dois sub-casos: (a) versão/commit/ambiente disponíveis
  (ex.: variável de ambiente e arquivo de build presentes); (b) commit
  **ausente** (arquivo de build não encontrado).
- **Passos:**
  1. Rodar o startup (ou a função de emissão de evidência) em cada sub-caso.
  2. Localizar o evento `rollout_evidence` no log.
- **Resultado esperado:** sub-caso (a): evento com `version`, `commit`,
  `environment`, `started_at` todos preenchidos. Sub-caso (b): evento emitido
  com o campo `commit` **sinalizado explicitamente como ausente** (ex.:
  `commit: null`/`"ausente"`), **sem** inferir sucesso nem omitir o campo.
- **Observações:** cobre RF-14/RN-10. "Ambiente obrigatório no runtime de
  produção" é documentado — o teste cobre o registro explícito da ausência,
  não a imposição de falha de startup (fora do escopo testável aqui sem
  especificação adicional de "runtime de produção").

### CT-22 — Remoção externa é registrada sem inferir autoria

- **CA de origem (CA-15):** "Dada uma presença pendente que desaparece sem
  reconciliação automática registrada, quando o ciclo seguinte observa a
  ausência, então um evento de remoção externa é registrado."
- **Tipo:** integração (descoberta remota)
- **Arquivo/alvo:** `tests/test_participation_evidence.py`
- **Pré-condição:** uma presença estava registrada (ex.: `propagated`,
  pendente de reconciliação) no snapshot; na próxima consulta via porta fake,
  essa presença **não aparece mais** em `list_participations`, e não há
  registro de que a reconciliação automática a removeu.
- **Passos:**
  1. Rodar o ciclo de descoberta seguinte.
  2. Verificar o log.
- **Resultado esperado:** evento `participation_removed_externally` é
  registrado com `issue`, `board`, `first_seen_at`, `observed_removed_at`; o
  evento **não** afirma autoria (não infere "removido pela esteira" nem tenta
  recriar a presença).
- **Observações:** cobre RF-13 e a linha "Presença pendente desaparece do
  quadro sem reconciliação automática registrada" da tabela de falhas.

### CT-23 — Nenhum evento contém segredos (varredura)

- **CA de origem (RNF-09, CA-14):** "Nenhum evento contém token, chave, body
  completo de issue ou conteúdo de arquivo protegido."
- **Tipo:** varredura/revisão (guarda estática sobre todos os eventos
  emitidos nesta suíte)
- **Arquivo/alvo:** `tests/test_participation_evidence.py`
- **Pré-condição:** rodar os cenários de CT-01, CT-02, CT-05, CT-08, CT-18,
  CT-21, CT-22 em sequência numa única execução de teste, com um marcador de
  corpo e um token fictício plantados nas issues/config usadas.
- **Passos:**
  1. Executar os cenários.
  2. Ler **todas** as linhas de eventos da família `participation_*`,
     `dispatch_blocked_unconfirmed_intent`, `cross_board_link_blocked` e
     `rollout_evidence` emitidas no log do dia.
- **Resultado esperado:** nenhuma linha contém o marcador do corpo, o token
  fictício, nem caminho/conteúdo de `.pipe/boards/*/snapshot.json`,
  `.pipe/changeQueue.json` ou qualquer arquivo da lista `PROTECTED_PATHS`.
- **Observações:** cobre RNF-09 de forma agregada; complementa CT-14 (que
  verifica os dois eventos centrais isoladamente).

---

## Grupo F — Generalização por par de quadros (sem hardcode)

### CT-02-generico — Mesmo mecanismo cobre qualquer par de fluxo hierárquico, sem tratamento por par

- **CA de origem (CA-16):** "Dado que o mesmo mecanismo cobre os pares de
  fluxo hierárquico existentes (por exemplo, quadro de histórias sob quadro de
  épicos, e quadro de tarefas sob quadro de histórias), quando um novo par de
  fluxo hierárquico é configurado, então a prevenção continua válida sem
  alteração de regra."
- **Tipo:** integração (política), parametrizado por par de boards
- **Arquivo/alvo:** `tests/test_participation_reconciliation.py`
- **Pré-condição:** três configurações de boards parametrizadas: (i)
  `epicos`→`historias` (par já existente no `pipe.yml` de produção), (ii)
  `historias`→`tarefas`, (iii) um par **sintético novo**,
  `squads`→`iniciativas`, configurado apenas no teste, sem qualquer menção a
  esses nomes no código de produção.
- **Passos:**
  1. Rodar o cenário de propagação (equivalente a CT-01/CT-03) para cada par.
  2. Verificar que o resultado é o mesmo nos três pares, inclusive o par
     sintético nunca visto antes.
- **Resultado esperado:** comportamento idêntico (classificação `propagated`,
  reconciliação, hierarquia preservada) nos três pares, **sem** nenhuma
  condição `if board_id == "epicos"` (ou similar) no código avaliado —
  verificável por inspeção de que o par sintético funciona sem alteração de
  código.
- **Observações:** cobre RF-05/RNF-07. É o guard-rail de "sem lista de pares
  codificada".

---

## Fora de escopo dos casos (alinhado à issue)

Os seguintes **não** são testados aqui por estarem fora de escopo da issue:

- limpeza retroativa de presenças/arquivos duplicados já materializados antes
  desta entrega (operação manual separada, com a esteira parada);
- painel, banco de auditoria ou nova stack de métricas;
- banco de dados, mensageria, worker, webhook ou novo serviço;
- uso de REST para dados de item de projeto (dados de projeto são GraphQL,
  exclusivamente — os fakes de porta não devem expor um caminho REST
  alternativo);
- apurar, dentro desta entrega, se a janela de observação foi bem-sucedida —
  os casos cobrem a **capacidade de apurar** (CT-14/CT-17-evidência via
  campos estruturados), não o veredito da janela em si;
- qualquer SLA de tempo de reconciliação alem do "mesmo ciclo" (RNF-03) já
  coberto implicitamente pelos testes de integração (sem medir tempo real de
  parede).

---

## Resumo de arquivos de teste propostos

| Arquivo | Cobre |
|---------|-------|
| `tests/test_participation_classification.py` | CT-04, CT-07, CT-01a, CT-01c, CT-origem-01, CT-06 (política pura, sem rede) |
| `tests/test_participation_reconciliation.py` | CT-01, CT-01b, CT-02, CT-03, CT-05, CT-15, CT-16, CT-17-retentativa, CT-02-generico (gatilhos de reconciliação + retentativa) |
| `tests/test_participation_gate.py` | CT-08, CT-09, CT-10 (barreira final na seleção de tarefas) |
| `tests/test_participation_migration.py` | CT-11, CT-12, CT-13 (migração de legados no startup) |
| `tests/test_cross_board_safety.py` | CT-18, CT-19, CT-20 (contingência reversível) |
| `tests/test_participation_evidence.py` | CT-14, CT-21, CT-22, CT-23 (observabilidade e evidência) |

Sem regressão: a suíte existente de propagação e sync
(`tests/test_sub_issue_propagation_fix.py`, `tests/test_sync_unico*.py`,
`tests/test_incremental_absent_delete_down.py`) deve continuar passando — o
pós-hook `_remove_propagated_items_without_status` e o guard de
`_apply_create_down` continuam válidos como primeira camada; a nova
classificação de intenção é uma camada **adicional** (barreira final), não uma
substituição que quebre o comportamento hoje testado.
