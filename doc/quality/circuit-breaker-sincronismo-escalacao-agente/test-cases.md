# Casos de Teste — Circuit-breaker de sincronismo com escalação ao agente e encerramento controlado

- **Issue:** #309
- **Story relacionada:** consolidação das proteções dispersas contra falha de
  sincronismo (`sync.max_attempts`, remediação E4, `agent_circuit_break` #306);
  bloqueia #316
- **Autor(a):** Camila Rocha — Engenheira de Qualidade (QA)
- **Data:** 2026-11-04
- **Branch:** `feature/309-circuit-breaker-sincronismo-escalacao-agente`

> Todo caso de teste abaixo é derivado de um critério de aceitação (CA 1–14) da
> issue #309 e dos 13 cenários obrigatórios (CT-01..CT-13) do seu próprio
> Detalhamento. Os testes são da suíte Python do motor (pytest, em `tests/`).
> Os casos de janela/tempo usam **relógio controlável** (`monkeypatch` de
> `time.time` ou equivalente) — nunca `sleep` real.

---

## Contexto de arquitetura (baseline do código atual)

O mecanismo não existe hoje como peça única; as proteções que ele absorve ou com
que convive estão confirmadas no código:

- **`src/core/sync.py::classify_error`** classifica toda exceção de sincronismo
  em `rate_limit` (via `PenaltyException`), `definitivo` (mensagens estáveis de
  alvo inexistente/isolamento de board), `definitivo_cli` (uso inválido da CLI
  `gh`), `corrigivel_pelo_agente` (HTTP 422/"Validation Failed") ou
  `transitorio` (default). **Esta função é o ponto de ancoragem natural** para
  o novo circuit-breaker decidir o que conta como "falha de sincronismo" —
  `rate_limit` já está isolado de todas as demais categorias (CA-12/RF-12).
- **`src/core/sync.py::apply_changes`** é o ponto único onde cada item da fila é
  tentado e a exceção é capturada e classificada. É aqui que hoje: (a)
  `corrigivel_pelo_agente` gera um `RemediationSignal` e sai da fila sem retry
  cego; (b) `transitorio` incrementa `item.attempts` e reenfileira até esgotar
  `sync.max_attempts` (`resolve_max_attempts`, default 3), indo então para
  dead-letter; (c) `definitivo`/`definitivo_cli` vão direto para dead-letter.
  **Nenhum destes três caminhos hoje bloqueia a issue nem conta para um teto
  de bloqueios por issue/plataforma** — é a lacuna que esta issue fecha.
- **Remediação E4 (`RemediationSignal`/`RemediationFailStop`)** — hoje em
  `src/__main__.py`: `_remediated_targets` (set em memória, por episódio) marca
  alvos já remediados; `remediate_pending` chama o agente **uma vez** por alvo
  (reconstruindo o `task` via `_build_task_for_target`, que lê o snapshot — NÃO
  o `keep_task`); na reincidência do mesmo alvo, `_remediation_fail_stop`
  levanta `RemediationFailStop`, capturado no loop principal (`main()`) que só
  faz `running = False` (**não** levanta `SystemExit` com código ≠ 0 hoje — ver
  nota de risco em CT-10). Esta entrega **absorve** esse mecanismo (RF-13/CA-14):
  o dono passa a ser o circuit-breaker; não pode haver os dois ativos em
  paralelo para a mesma responsabilidade (RNF-06/RN-11).
- **`agent_circuit_break` (#306, `src/core/agent_circuit_break.py`)** é o
  **molde de implementação** que esta issue deve seguir para o novo mecanismo
  (mesmo padrão de qualidade já testado em produção), mas é um mecanismo
  **distinto e não alterado** (teto de execuções do AGENTE por
  `(board, coluna, issue)`; este novo circuit-breaker é teto de FALHAS DE SYNC
  por issue e por plataforma). Pontos do molde que os casos abaixo cobram
  tecnicamente do novo mecanismo, por analogia direta:
  - política opt-in por bloco de config ausente ⇒ sem erro, defaults aplicados
    (`CircuitBreakPolicy`-like, `validate_*`/`resolve_*` em `config.py`);
  - persistência atômica (arquivo temporário + `fsync` + `os.replace`) em JSON
    protegido, versão lógica do estado, fail-closed em corrupção/ilegibilidade
    (`CircuitBreakStateError`-like);
  - ordem obrigatória do bloqueio: persistir evento + esvaziar contagem **antes**
    de qualquer chamada externa;
  - gate de capacidade do adaptador na inicialização
    (`adapter_can_apply_label`/`check_label_capability`), chamado em `main()`
    **antes** de `board_startup_sync` — o novo mecanismo, ao escalar ao agente,
    não depende de label (usa dispatch de agente), mas se a escalação também
    aplicar algum marcador no board, o mesmo gate se aplica.
  - fonte única de contagem: assim como a #306/#307 compartilham fonte, este
    circuit-breaker tem **sua própria** fonte única para "falhas de sync por
    issue" e "issues bloqueadas por plataforma" — não reaproveita os contadores
    do #306 (que contam execuções de AGENTE, fato distinto).
- **`PROTECTED_PATHS`** (`src/core/agent.py`) lista os arquivos de estado interno
  que o agente nunca acessa, e `build_prompt` valida que nenhum apareça no
  prompt enviado. O novo arquivo de estado do circuit-breaker de sync entra
  nessa lista (mesmo padrão de `.pipe/agentCircuitBreak.json`).
- **`sync_remote`** (descoberta down) já enfileira **sempre** `fullsync=True`
  (ver `tests/test_sync_unico_sem_segundo_modo.py::test_fullsync_not_used_as_down_scope_selector`)
  — mas `_apply_create_down`/`_apply_change_down` ainda chamam
  `board_obj.get_issue(..., fullsync=item.fullsync)`, e a `BoardPort.get_issue`
  ainda tem o parâmetro `fullsync` com semântica de "trazer ou não as deps via
  REST extra". RF-14/CA-9 pedem eliminar esse parâmetro/modo parcial — a chamada
  única passa a trazer relações de bloqueio sempre, sem bifurcação.
- **`Board.apply_commands`** (`src/core/board.py`) chama `set_blocked_by`/
  `set_blocks` apenas quando o desejado difere do conhecido; a rejeição de
  "relação já existente" hoje propagaria como exceção genérica (`transitorio`,
  reentra no retry). RF-15/CA-10 pedem tratá-la como sucesso idempotente no
  **adaptador** (`src/adapters/github_board.py`), sem abortar o restante das
  relações do mesmo lote.
- **`_apply_change_up`** grava `issue_data["body_mtime"]` e chama `snap.save()`
  **depois** de `board_obj.apply_commands(...)` ter sido chamado com sucesso —
  ou seja, se `apply_commands` levantar exceção, a marca temporal do corpo
  **não** é gravada antes de a exceção propagar. RF-16/CA-11 pedem inverter essa
  ordem: persistir a marca temporal do corpo no estado local **antes** de a
  falha propagar.

> **Decisão de design NÃO fixada pela QA (é do desenvolvimento):** nome e
> localização do núcleo do circuit-breaker (classe(s), módulo, nome do arquivo
> de estado, assinatura exata das funções, ponto exato de interceptação dentro
> de `apply_changes`/`main()`). Os casos abaixo testam **comportamento e
> invariantes observáveis** descritos nos CAs/RFs/RNs da issue, não assinaturas.
> Onde um caso cita um símbolo concreto (`classify_error`, `apply_changes`,
> `sync_remote`, `RemediationSignal`, `check_label_capability`), o alvo é
> **provável** pela arquitetura atual; se o desenvolvimento adotar outro nome,
> o caso vale sobre o comportamento equivalente.

### Ponto de atenção explícito herdado do corpo da issue (não decidido por mim)

A issue documenta, na seção "Riscos e pontos de atenção", que a interação
mecânica exata entre o esgotamento de `sync.max_attempts` (retry transitório) e
o incremento do contador de bloqueio de issue **não foi detalhada por Breno** —
é detalhe de implementação a definir no desenvolvimento, **sem alterar o
comportamento observável dos critérios de aceitação**. Os casos abaixo (Grupo A)
fixam o comportamento observável exigido pelos CAs (contagem de falhas de sync
≠ rate limit, bloqueio ao atingir `issue.max_failures`) e **não** fixam se esse
contador é incrementado a cada tentativa transitória individual ou só ao
esgotar `max_attempts` — ambas as implementações são aceitáveis desde que os
resultados observáveis dos casos abaixo se verifiquem.

---

## Rastreabilidade (CA → casos)

| CA | Requisito/Regra | Caso(s) |
|----|------------------|---------|
| CA-1 (CT-01 da issue) | RF-01, RF-02 / RN-01, RN-02 | CT-01, CT-02 |
| CA-2 (CT-02 da issue) | RF-03 / RN-03 | CT-03 |
| CA-3 (CT-02 da issue) | RF-04 / RN-04 | CT-04 |
| CA-4 (CT-03 da issue) | RF-05 / RN-04 | CT-05 |
| CA-5 (CT-04 da issue) | RF-06, RF-07 / RN-05, RN-06 | CT-06, CT-07 |
| CA-6 (CT-05 da issue) | RF-08 / RN-07 | CT-08 |
| CA-7 (CT-05 da issue) | RF-10 | CT-09 |
| CA-8 (CT-06 da issue) | RF-11 / RN-09 | CT-10, CT-11 |
| CA-9 (CT-10 da issue) | RF-14 / RN-12 | CT-12 |
| CA-10 (CT-08 da issue) | RF-15 / RN-13 | CT-13 |
| CA-11 (CT-09 da issue) | RF-16 / RN-14 | CT-14 |
| CA-12 (CT-07 da issue) | RF-12 / RN-10 | CT-15, CT-16 |
| CA-13 (CT-11 da issue) | RF-17 / RN-15 | CT-17, CT-17b |
| CA-14 (CT-12 da issue) | RF-13 / RN-11 | CT-18 |
| — (robustez de borda, derivado de RN-03/RN-04) | RF-04 | CT-19 |
| — (isolamento de plataforma, derivado de RN-06) | RF-07 | CT-20 |
| — (segurança do estado, análogo a RNF do #306) | — | CT-21 |
| — (cenário obrigatório CT-13 da issue) | RF-17 / RN-15 | CT-22 |

> Cobertura: os 13 cenários obrigatórios da issue (CT-01..CT-13 do corpo) mapeiam
> 1:1 ou 1:N para os casos deste documento (ver tabela "Mapa CT da issue → casos"
> ao final). Não há CA sem caso, nem caso sem CA de origem. O escopo está
> completo e internamente consistente para derivar estes casos — não há
> contradição ou lacuna que exija devolver ao planejamento.

---

## Convenções para o desenvolvimento (todos os casos automatizados)

- **Offline, sem rede:** usar um `BoardPort` fake espião controlável, no padrão
  de `tests/test_remedios_bloqueio.py` e `tests/test_agent_circuit_break.py`. O
  fake deve permitir **injetar falhas controladas** nas operações de sincronismo
  (`update_issue`, `apply_commands`/`set_blocked_by`/`set_blocks`, `get_issue`,
  `move_issue`) para simular falha de conexão/aplicação de comando, e registrar
  as chamadas de dispatch ao agente dedicado (espião, sem executar `kiro-cli`).
- **Isolamento de estado:** `monkeypatch.chdir(tmp_path)` autouse por teste, para
  que `.pipe/`, `logs/` fiquem isolados. Qualquer cache de módulo do novo
  circuit-breaker (contadores em memória, se houver) deve ser limpo em fixture
  autouse, para não vazar estado entre testes — mesmo padrão de `_rerun_cache`/
  `_remediated_targets` em `test_remediation_loop.py`/`test_rerun_cooldown.py`.
- **Relógio controlável:** nos casos de janela/duração (CT-02, CT-04, CT-07,
  CT-19) o relógio é injetado/`monkeypatch`ado — nunca `sleep` real.
- **Nunca** fazer `monkeypatch` do próprio símbolo sob teste (lição do incidente
  #106). O núcleo de decisão do circuit-breaker (contagem, transição de estado,
  bloqueio) é exercitado de verdade; só o **provedor** (board port), o
  **relógio** e o **dispatch ao agente dedicado** são substituídos por espiões/
  fakes.
- **Rate limit não é fake de exceção genérica:** os casos que precisam excluir
  rate limit da contagem usam `PenaltyException` real (`from src.core.board
  import PenaltyException`), nunca uma string "rate limit" em uma exceção
  genérica — a classificação é estrutural (`classify_error`), não por
  varredura de texto (mesmo princípio de `test_rate_limit_detection.py`).
- **Evidência:** verificar log estruturado lendo `logs/<data>.json` e localizando
  o evento pelo campo `event`. Nunca inspecionar `.pipe/...` como fonte de
  evidência de comportamento de negócio — isso é auditoria de implementação, não
  de contrato observável (exceto nos casos que a própria QA marca como
  "verificação de teste da persistência", ex.: CT-21, CT-22).
- **Config mínima:** cada caso assume um `pipe.yml`/`config: dict` válido com
  (quando pertinente) o bloco `sync.circuit_breaker` conforme o contrato do
  corpo da issue (`issue.max_failures`, `issue.block_duration`,
  `issue.max_blocks`, `platform.max_blocked_issues`, `platform.block_window`,
  `platform.block_duration`, `half_open.success_threshold`, `persistence`).

---

## Grupo A — Bloqueio de issue por falhas de sincronismo (CT-01 da issue)

### CT-01 — Bloqueio de issue ao atingir `issue.max_failures` falhas consecutivas

- **CA de origem:** CA-1 — "Dado que uma issue falha ao sincronizar
  (erro de conexão/aplicação de comando, exceto rate limit/penalty)
  `issue.max_failures` vezes consecutivas, quando o limite é atingido, então a
  sincronização dessa issue fica bloqueada por `issue.block_duration` segundos
  e suas mudanças de subida permanecem na fila sem serem processadas durante
  esse período."
- **Tipo:** unitário (núcleo do circuit-breaker + `apply_changes`)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py` (novo)
- **Pré-condição:** `sync.circuit_breaker.issue.max_failures: 3`; fila com um
  `CHANGE_UP` para a issue `#42` do board `entrega`; fake de board configurado
  para falhar de forma **transitória não-rate-limit** (ex.: `update_issue`
  levanta `Exception("timeout de rede")`, classificada como `transitorio` por
  `classify_error`) em toda tentativa.
- **Passos:**
  1. Chamar `apply_changes`/processar a fila 3 vezes consecutivas para o mesmo
     item (reenfileirando entre as chamadas, conforme o mecanismo esgota ou não
     `sync.max_attempts` antes — ver nota de interação no topo do documento).
  2. Verificar o estado de bloqueio da issue após a 3ª falha.
- **Resultado esperado:** após a falha que completa `issue.max_failures = 3`
  falhas consecutivas da MESMA issue, a issue entra em estado bloqueado; um
  log estruturado de bloqueio de issue é emitido com, no mínimo,
  `{evento, board, issue, falhas_consecutivas, bloqueado_ate}`.
- **Observações:** cobre RF-01, RN-01. "Consecutivas" é por issue — falhas de
  outra issue não contam para este contador (ver CT-20 para o contador de
  plataforma, que é por issues distintas).

### CT-02 — Issue bloqueada: mudanças de subida retidas na fila sem reprocessamento

- **CA de origem:** CA-1 (mesma origem de CT-01, segunda cláusula do "então").
- **Tipo:** unitário (fila + circuit-breaker)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** issue `#42` já bloqueada (CT-01 completado); uma nova
  mudança de subida para `#42` é enfileirada (`CHANGE_UP`) **durante** o
  período de bloqueio (relógio controlado para não ter decorrido
  `issue.block_duration`).
- **Passos:**
  1. Enfileirar novo `CHANGE_UP` para `#42` enquanto bloqueada.
  2. Rodar o processamento da fila.
  3. Verificar se `update_issue`/`apply_commands` foram chamados no fake de
     board para esta issue.
- **Resultado esperado:** o item permanece na fila (não removido, não
  reenfileirado com nova tentativa) OU é reconhecidamente retido sem qualquer
  chamada de rede/aplicação de comando ao board para `#42` durante o bloqueio —
  nenhuma chamada de sincronismo é feita para a issue bloqueada; outros itens da
  fila de OUTRAS issues continuam sendo processados normalmente no mesmo ciclo
  (isolamento por issue, análogo ao isolamento do #306).
- **Observações:** cobre RF-02, RN-02. É o invariante central: bloqueio pausa,
  não descarta.

---

## Grupo B — Meio-aberto: expiração, fechamento e reabertura (CT-02/CT-03 da issue)

### CT-03 — Expiração do bloqueio leva a meio-aberto e retentativa no ciclo seguinte

- **CA de origem:** CA-2 — "Dado que uma issue está bloqueada, quando a duração
  de bloqueio expira, então a issue entra em estado meio-aberto e é retentada
  no ciclo seguinte."
- **Tipo:** unitário (circuit-breaker), relógio controlável
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** issue `#42` bloqueada com `issue.block_duration = 300`;
  relógio avançado para `t0 + 300` (ou mais) após o início do bloqueio.
- **Passos:**
  1. Bloquear a issue (reaproveitando a sequência de CT-01).
  2. Avançar o relógio controlado para além de `issue.block_duration`.
  3. Processar a fila/avaliar a issue no ciclo seguinte.
- **Resultado esperado:** a issue passa a ser avaliada em estado meio-aberto —
  a próxima tentativa de sincronismo **é feita** (não é mais retida
  incondicionalmente como em CT-02); um log de transição de estado é emitido
  com, no mínimo, `{evento, board, issue, estado_anterior, estado_novo}`
  (`aberto` → `meio-aberto` ou nomenclatura equivalente).
- **Observações:** cobre RF-03, RN-03. A duração é lida de
  `issue.block_duration`; o teste deve variar esse valor (ex.: parametrizado)
  para confirmar que não é uma constante fixa no código.

### CT-04 — Amostra de sucessos em meio-aberto fecha o circuito e zera os contadores

- **CA de origem:** CA-3 — "Dado que uma issue em estado meio-aberto sincroniza
  com sucesso o número de vezes configurado para fechar o circuito, quando essa
  amostra se completa, então o circuito fecha e os contadores de falha da issue
  são zerados."
- **Tipo:** unitário (circuit-breaker)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** `sync.circuit_breaker.half_open.success_threshold: 2`;
  issue `#42` em meio-aberto (pós CT-03); fake de board configurado para
  **suceder** nas próximas tentativas de sincronismo desta issue.
- **Passos:**
  1. Levar a issue a meio-aberto.
  2. Processar com sucesso a 1ª tentativa em meio-aberto — verificar que o
     circuito ainda NÃO fechou (amostra incompleta).
  3. Processar com sucesso a 2ª tentativa (completa `success_threshold = 2`).
- **Resultado esperado:** somente após completar as 2 tentativas bem-sucedidas
  consecutivas o circuito fecha; os contadores de falha consecutiva da issue
  são zerados; um log de fechamento do circuito é emitido. Antes de completar a
  amostra (após só 1 sucesso), a issue permanece em meio-aberto, não "fechada"
  prematuramente.
- **Observações:** cobre RF-04, RN-04. `success_threshold` deve ser lido da
  config (variar o valor em um sub-caso, ex. `1`, para confirmar
  parametrização).

### CT-05 — Falha em meio-aberto reabre o bloqueio

- **CA de origem:** CA-4 — "Dado que uma issue em estado meio-aberto falha ao
  sincronizar, quando a falha ocorre, então o circuito reabre e a issue volta a
  ficar bloqueada por `issue.block_duration` segundos."
- **Tipo:** unitário (circuit-breaker)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** issue `#42` em meio-aberto (pós CT-03); fake de board
  configurado para **falhar** (não rate limit) na tentativa em meio-aberto.
- **Passos:**
  1. Levar a issue a meio-aberto.
  2. Processar a tentativa em meio-aberto com falha de sincronismo.
- **Resultado esperado:** o circuito reabre imediatamente — a issue volta ao
  estado bloqueado por `issue.block_duration` segundos (prazo recontado a partir
  do momento da falha em meio-aberto, não do bloqueio anterior); um log de
  reabertura é emitido. Uma única falha na amostra é suficiente para reabrir
  (não exige esgotar um contador separado de falhas em meio-aberto).
- **Observações:** cobre RF-05, RN-04 (a mesma regra de "falha reabre" aplicada
  ao estado meio-aberto). Testar que o novo prazo de bloqueio é efetivamente
  `issue.block_duration` a partir do instante da reabertura (relógio
  controlado).

---

## Grupo C — Bloqueio de plataforma (CT-04 da issue)

### CT-06 — Bloqueio de plataforma ao acumular issues distintas bloqueadas na janela

- **CA de origem:** CA-5 — "Dado que `platform.max_blocked_issues` issues
  distintas da mesma plataforma foram bloqueadas dentro de
  `platform.block_window` segundos, quando o limite é atingido, então a
  plataforma inteira fica bloqueada por `platform.block_duration` segundos e
  nenhum sync de subida ou descida é processado para aquela plataforma nesse
  período, sem interromper o processamento de outras plataformas."
- **Tipo:** unitário (circuit-breaker de plataforma), relógio controlável
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** `sync.circuit_breaker.platform.max_blocked_issues: 5`,
  `platform.block_window: 600`; 5 issues DISTINTAS do mesmo board/plataforma
  bloqueadas (cada uma atingindo seu próprio `issue.max_failures`) dentro da
  janela de 600s (relógio controlado para garantir que todas as 5 ocorrem
  dentro da janela).
- **Passos:**
  1. Bloquear 5 issues distintas dentro da janela de 600s.
  2. Verificar o estado da plataforma após o 5º bloqueio.
- **Resultado esperado:** ao atingir a 5ª issue bloqueada dentro da janela, a
  plataforma inteira entra em estado bloqueado por `platform.block_duration`
  segundos; um log de bloqueio de plataforma é emitido com, no mínimo,
  `{evento, board, issues_bloqueadas, janela, bloqueado_ate}`. Uma 6ª issue
  (nova, ainda não bloqueada) também não tem seu sync processado enquanto a
  plataforma está bloqueada (verificado em CT-07).
- **Observações:** cobre RF-06, RN-05. "Issues distintas" — bloquear a MESMA
  issue repetidamente (reabertura em meio-aberto) não deve contar múltiplas
  vezes para este contador (sub-caso: reabrir 2x a mesma issue conta como 1
  issue distinta bloqueada, não 2).

### CT-07 — Plataforma bloqueada: sincronismo (subida e descida) pulado só para ela

- **CA de origem:** CA-5 (segunda cláusula) e Escopo ("sem interromper o
  restante da esteira").
- **Tipo:** unitário/integração (loop de ciclo + circuit-breaker de plataforma)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** plataforma do board `entrega` bloqueada (pós CT-06); um
  segundo board `outro-board` configurado em uma plataforma distinta (ou,
  minimamente, o teste verifica que a etapa de sincronismo do board bloqueado é
  pulada sem lançar exceção que interrompa o ciclo do `__main__`).
- **Passos:**
  1. Com a plataforma bloqueada, chamar a etapa de sincronismo (local/remota)
     do board afetado.
  2. Chamar a etapa de sincronismo de outro board/plataforma não bloqueada no
     mesmo ciclo.
- **Resultado esperado:** nenhuma chamada de sync (subida OU descida) é feita
  para o board/plataforma bloqueada enquanto o bloqueio está ativo (`list_issues`,
  `update_issue`, etc. não acionados no fake de board para esse board); o board/
  plataforma não bloqueado é sincronizado normalmente no mesmo ciclo, sem
  esperar o desbloqueio do primeiro. O loop principal não lança excecão nem
  para por este motivo.
- **Observações:** cobre RF-07, RN-06. É o requisito central de isolamento por
  plataforma — ver também CT-20 (variação sobre múltiplas plataformas).

---

## Grupo D — Escalação ao agente dedicado e encerramento controlado (CT-05/CT-06 da issue)

### CT-08 — Escalação ao agente dedicado após `issue.max_blocks` bloqueios consecutivos

- **CA de origem:** CA-6 — "Dado que uma issue foi bloqueada `issue.max_blocks`
  vezes consecutivas, quando o limite é atingido, então o agente dedicado de
  correção da esteira é acionado uma única vez, com um prompt que contém o
  fato da falha, o log de erro completo e a instrução de correção."
- **Tipo:** unitário (escalação), dispatch ao agente substituído por espião
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** `sync.circuit_breaker.issue.max_blocks: 3`; issue `#42`
  bloqueada 3 vezes consecutivas (cada ciclo de bloqueio → expiração →
  meio-aberto → falha → reabertura, sem nunca fechar o circuito entre elas —
  "consecutivas").
- **Passos:**
  1. Levar a issue a 3 bloqueios consecutivos (sem fechamento do circuito entre
     eles).
  2. Verificar se e quantas vezes o agente dedicado foi acionado.
- **Resultado esperado:** ao atingir o 3º bloqueio consecutivo, o agente
  dedicado de correção é acionado **exatamente uma vez** (dispatch espião
  chamado 1x); o prompt entregue contém, de forma inequívoca, as três partes
  exigidas pelo contrato de escalação: (a) o fato de que a sincronização
  falhou, (b) o log de erro completo da falha, e (c) a instrução de corrigir a
  issue para que ela sincronize. Um log de escalação é emitido com, no mínimo,
  `{evento, board, issue, agente_dedicado, bloqueios_consecutivos}`.
- **Observações:** cobre RF-08, RF-09, RN-07, RN-08. O agente dedicado NÃO é o
  agente resolvido por `resolve_agent_id` para a coluna atual da issue (ver nota
  de decisão do dono do produto: "agente dedicado de correção da esteira", não
  "último agente que executou").

### CT-08b — Escalação acionada uma única vez por episódio (freio de repetição)

- **CA de origem:** CA-6 (cláusula "uma única vez").
- **Tipo:** unitário (escalação)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** issue `#42` já escalada (pós CT-08); novo bloqueio ocorre
  para a MESMA issue sem que o episódio de escalação tenha sido resolvido
  (nenhuma correção aplicada).
- **Passos:**
  1. Provocar um bloqueio adicional da mesma issue, já escalada.
  2. Verificar quantas vezes o agente dedicado foi acionado no total.
- **Resultado esperado:** o agente dedicado **não** é acionado uma segunda vez
  para o mesmo episódio de escalação (dispatch espião permanece em 1 chamada
  total); o próximo bloqueio sem resolução segue para o caminho de encerramento
  controlado (ver CT-10), não para uma nova escalação.
- **Observações:** cobre RN-07 (freio análogo ao `_remediated_targets` do E4,
  agora dentro do circuit-breaker).

### CT-09 — Retentativa do sync no ciclo seguinte à correção do agente dedicado

- **CA de origem:** CA-7 — "Dado que o agente dedicado corrigiu a issue, quando
  o próximo ciclo ocorre, então o sync dessa issue é retentado."
- **Tipo:** unitário/integração (pós-escalação)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** issue `#42` escalada (pós CT-08); dispatch espião do agente
  dedicado simulado como concluído; fake de board configurado para suceder na
  próxima tentativa de sync (simulando que o agente corrigiu o problema).
- **Passos:**
  1. Completar a escalação (CT-08).
  2. Avançar para o ciclo seguinte.
  3. Verificar se o sync da issue é retentado.
- **Resultado esperado:** no ciclo seguinte à atuação do agente dedicado, o
  sincronismo da issue `#42` É retentado (não permanece bloqueada
  indefinidamente esperando uma ação externa que não existe — a retentativa é
  automática no próximo ciclo).
- **Observações:** cobre RF-10. Complementar a CT-08: aqui o foco é que o fluxo
  CONTINUA após a escalação, não trava esperando confirmação manual.

### CT-10 — Encerramento controlado quando o sync falha de novo após a correção

- **CA de origem:** CA-8 — "Dado que o sync falha novamente após a correção do
  agente dedicado, quando a falha é detectada, então a esteira encerra com
  código de saída diferente de zero e registra issue, board, erro, número de
  tentativas e o agente que corrigiu."
- **Tipo:** unitário/integração (encerramento), subprocesso real para o código
  de saída
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py` (núcleo da decisão) e
  um teste de processo (`tests/test_sync_circuit_breaker_exit_code.py` ou
  extensão de `tests/test_sigterm_shutdown.py`, que já testa código de saída via
  subprocesso) para o código de saída real.
- **Pré-condição:** issue `#42` pós-escalação (pós CT-09), mas a próxima
  tentativa de sync **falha de novo** (fake de board configurado para falhar
  outra vez).
- **Passos:**
  1. Completar a escalação e a retentativa com falha (em vez de sucesso, como em
     CT-09).
  2. Verificar o sinal de encerramento devolvido pelo núcleo de decisão.
  3. (Teste de processo) Rodar o loop principal em subprocesso com este cenário
     e capturar o código de saída do processo.
- **Resultado esperado:** o núcleo do circuit-breaker sinaliza encerramento
  crítico (equivalente a uma exceção fail-stop, análoga porém NÃO a
  `RemediationFailStop` — ver RN-11); o processo principal termina com **código
  de saída diferente de zero** (ao contrário do comportamento atual de
  `RemediationFailStop`, que hoje só seta `running = False` sem `SystemExit`
  — ver nota de risco abaixo); um log de erro crítico é emitido com, no mínimo,
  `{evento, board, issue, erro, tentativas, agente_que_corrigiu}`.
- **Observações:** cobre RF-11, RN-09, RNF-02 (determinismo do encerramento,
  sem depender de temporização externa). **Nota de risco observada no código
  atual:** `main()` hoje captura `RemediationFailStop` e apenas faz
  `running = False` dentro do laço `while running`, saindo do `try/finally` sem
  jamais levantar `SystemExit(≠0)` — o processo atual terminaria com código 0
  nesse caminho. Este caso **fixa o comportamento exigido** (código ≠ 0); é
  responsabilidade do desenvolvimento garantir que o nível de `main()` propague
  o código de saída diferente de zero no caminho de encerramento crítico deste
  circuit-breaker (ex.: `raise SystemExit(1)` ou devolver o valor para o
  chamador do processo), e não apenas logar e sair do loop silenciosamente.

### CT-11 — Conteúdo completo do registro de encerramento crítico

- **CA de origem:** CA-8 (cláusula "registra issue, board, erro, número de
  tentativas e o agente que corrigiu").
- **Tipo:** unitário (log estruturado)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** mesmo cenário de CT-10 (encerramento crítico disparado).
- **Passos:**
  1. Disparar o encerramento crítico.
  2. Ler `logs/<data>.json` e localizar o evento de erro crítico.
- **Resultado esperado:** o registro contém, no mínimo, os cinco campos:
  identificação da issue, board, descrição/causa do erro, número de tentativas
  realizadas até o encerramento, e a identificação do agente dedicado que atuou
  na correção (ex.: `agent_id`/nome do agente dedicado). Nenhum dos cinco campos
  está ausente ou vazio.
- **Observações:** cobre RNF-04 (rastreabilidade de decisão). Separado de CT-10
  para isolar a asserção de conteúdo do log da asserção de código de saída
  (responsabilidades de verificação distintas).

---

## Grupo E — Descida sempre completa e idempotência de relação existente (CT-10/CT-08 da issue)

### CT-12 — Sincronização de descida sempre traz o estado completo, sem modo parcial

- **CA de origem:** CA-9 — "Dado qualquer sincronização de descida, quando ela
  é executada, então o estado completo da plataforma é buscado, incluindo
  relações de bloqueio, sem qualquer modo parcial."
- **Tipo:** unitário (contrato de `get_issue`/`sync_remote`/`_apply_*_down`)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py` ou extensão de
  `tests/test_sync_unico_sem_segundo_modo.py`/`tests/test_sync_unico_deps.py`
- **Pré-condição:** uma issue com relações `blocked_by`/`blocks` presentes no
  fake de board; qualquer caminho de descida é exercitado: descoberta
  (`sync_remote`), criação (`CREATE_DOWN`) e modificação (`CHANGE_DOWN`).
- **Passos:**
  1. Para cada caminho de descida (descoberta, create-down, change-down),
     verificar com que argumento/semântica o board é consultado.
  2. Verificar se as relações de bloqueio vêm preenchidas no resultado,
     independentemente de qualquer flag de "modo reduzido".
- **Resultado esperado:** toda chamada de descida traz as relações de bloqueio
  preenchidas; não existe nenhum caminho de código em que uma descida devolva
  `blocked_by`/`blocks` deliberadamente vazios/não-buscados por economia de
  chamadas (o parâmetro `fullsync` de `BoardPort.get_issue`, se mantido por
  compatibilidade de assinatura, não pode mais ter o efeito de omitir deps — ou
  é removido). Nenhuma bifurcação de comportamento "parcial vs. completo"
  sobrevive no caminho de descida.
- **Observações:** cobre RF-14, RN-12. Este caso é uma guarda de regressão
  arquitetural: deve falhar se qualquer novo/antigo caminho reintroduzir uma
  descida que omita deps.

### CT-13 — Relação de bloqueio já existente é tratada como sucesso idempotente

- **CA de origem:** CA-10 — "Dado que a plataforma reporta uma relação de
  bloqueio como já existente, quando a esteira tenta registrá-la, então a
  operação é tratada como sucesso, registrada em log, e as relações seguintes
  continuam sendo processadas."
- **Tipo:** unitário (adaptador de plataforma)
- **Arquivo/alvo:** `tests/test_github_board_contract.py` (extensão) ou novo
  `tests/test_sync_circuit_breaker_idempotencia_relacao.py`
- **Pré-condição:** uma issue com duas relações de bloqueio desejadas a
  registrar (`blocked_by #10, #20`, por exemplo); o adapter de board é
  acionado para registrar ambas em sequência; a chamada para a primeira relação
  (`#10`) retorna/levanta o sinal específico de "relação já existente" da
  plataforma (ex.: mensagem de erro característica do GitHub para dependência
  duplicada — a ser confirmada e isolada pelo desenvolvimento, análogo a
  `_DEFINITIVE_MESSAGE_SUBSTRINGS`/`_CORRIGIVEL_MESSAGE_SUBSTRINGS` de
  `classify_error`).
- **Passos:**
  1. Acionar o registro das duas relações de bloqueio em sequência.
  2. Verificar o resultado da operação e se a segunda relação (`#20`) foi
     processada.
- **Resultado esperado:** a tentativa de registrar a relação já existente
  (`#10`) é tratada como **sucesso** (não propaga como exceção para
  `classify_error`/`apply_changes`, não conta como falha de sincronismo para
  este circuit-breaker — CT-01 não deve ser afetado por isso); um log de skip
  idempotente é registrado; a relação seguinte (`#20`) é processada
  normalmente, na mesma chamada/lote (a operação não aborta no meio).
- **Observações:** cobre RF-15, RN-13. Importante: "relação já existente" NÃO
  incrementa o contador de falhas deste circuit-breaker (é sucesso, não falha) —
  sub-caso explícito a verificar junto.

---

## Grupo F — Persistência de progresso do corpo antes de propagar falha (CT-09 da issue)

### CT-14 — Marca temporal do corpo gravada antes de propagar a exceção de sync

- **CA de origem:** CA-11 — "Dado que a aplicação de comandos de sincronismo
  falha, quando a exceção ocorre, então a marca temporal do corpo da issue é
  gravada no estado local antes de a exceção ser propagada, e a issue não é
  redescoberta e reprocessada em loop por essa causa."
- **Tipo:** unitário (`_apply_change_up`/snapshot)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py` ou extensão de
  `tests/test_remedios_bloqueio.py`
- **Pré-condição:** issue `#42` com `CHANGE_UP` pendente; `board_obj.
  apply_commands` (ou o setter de relação invocado por ele, ex. `set_blocked_by`)
  configurado para levantar exceção (falha de aplicação de comando).
- **Passos:**
  1. Processar o `CHANGE_UP` com a falha configurada.
  2. Inspecionar o snapshot (`issue_data["body_mtime"]`) imediatamente após a
     exceção ser capturada por `apply_changes` — **antes** de qualquer nova
     execução do ciclo de descoberta local.
  3. Rodar `detect_local_changes` no ciclo seguinte (sem alterar o arquivo
     local) e verificar se um novo `CHANGE_UP` é gerado para a mesma versão do
     corpo.
- **Resultado esperado:** o `body_mtime` gravado no snapshot reflete o mtime do
  arquivo local **já no momento da falha** (gravado antes da exceção propagar
  para `apply_changes`), e não apenas após uma futura tentativa bem-sucedida;
  como consequência, `detect_local_changes` no ciclo seguinte **não** redetecta
  o mesmo conteúdo como uma nova modificação local (não há `CHANGE_UP`
  duplicado gerado pela mesma causa) — rompendo o loop de redescoberta descrito
  no CA.
- **Observações:** cobre RF-16, RN-14. Este caso reproduz exatamente a classe de
  incidente descrita na "Descrição" da issue (issue redescoberta e reprocessada
  em loop pela mesma falha).

---

## Grupo G — Rate limit fora do circuit-breaker (CT-07 da issue)

### CT-15 — Erro de rate limit/penalty não incrementa nenhum contador do circuit-breaker

- **CA de origem:** CA-12 — "Dado um erro classificado como rate limit/penalty
  da plataforma, quando ele ocorre, então ele não incrementa nenhum contador
  deste circuit-breaker (é tratado exclusivamente pelo mecanismo de throttle/
  penalty já existente)."
- **Tipo:** unitário (classificação + contagem)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** issue `#42`; fake de board configurado para levantar
  `PenaltyException` (não uma exceção genérica) em `issue.max_failures - 1`
  tentativas consecutivas (ou seja, um número de ocorrências de rate limit que,
  SE contassem, teria quase atingido o limite de bloqueio).
- **Passos:**
  1. Processar a issue `issue.max_failures - 1` vezes, cada vez recebendo
     `PenaltyException`.
  2. Verificar o estado de bloqueio da issue após essas ocorrências.
  3. Processar mais uma vez com sucesso (sem penalty) e verificar que o
     contador de falhas de sync não avançou por causa dos eventos de penalty
     anteriores.
- **Resultado esperado:** nenhuma das ocorrências de `PenaltyException` é
  contabilizada como falha de sincronismo deste circuit-breaker; a issue
  **não** entra em estado bloqueado por este mecanismo em decorrência delas; o
  tratamento de rate limit continua exclusivamente a cargo do mecanismo de
  throttle/penalty já existente (`PenaltyException` propagando como hoje,
  log do throttle inalterado).
- **Observações:** cobre RF-12, RN-10. Reaproveita o princípio de
  `test_rate_limit_detection.py` (detecção estrutural, nunca por varredura de
  texto) — aqui aplicado à EXCLUSÃO da contagem, não à detecção em si.

### CT-16 — Rate limit intercalado com falhas reais não acelera o bloqueio

- **CA de origem:** CA-12 (reforço — intercalação).
- **Tipo:** unitário (contagem)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** sequência intercalada de falhas da issue `#42`:
  transitório real, `PenaltyException`, transitório real, `PenaltyException`,
  transitório real — com `issue.max_failures: 3`.
- **Passos:**
  1. Processar a sequência intercalada acima.
  2. Verificar em que ponto exato o bloqueio ocorre.
- **Resultado esperado:** o bloqueio ocorre exatamente na 3ª falha REAL
  (transitória/não-rate-limit) consecutiva **entre falhas reais** — os eventos
  de `PenaltyException` no meio não contam nem quebram a "consecutividade" das
  falhas reais (ou, alternativamente, se o desenho do desenvolvimento tratar
  penalty como evento neutro que não interrompe a sequência de falhas reais, o
  comportamento observável mínimo exigido é: o número de falhas REAIS
  necessárias para bloquear continua sendo exatamente `issue.max_failures`,
  nunca menos). Nenhuma combinação de penalties acelera ou atrasa o bloqueio.
- **Observações:** cobre RF-12, RN-10 em cenário de intercalação — fecha a
  lacuna de "o que acontece à sequência consecutiva quando um evento neutro
  aparece no meio", que o CA-12 implica mas não detalha explicitamente.

---

## Grupo H — Configuração e defaults (CT-11 da issue)

### CT-17 — Defaults aplicados sem erro quando o bloco `sync.circuit_breaker` está ausente

- **CA de origem:** CA-13 — "Dado que qualquer parâmetro de configuração do
  circuit-breaker de sincronismo está ausente, quando a esteira inicia, então
  o valor padrão correspondente é aplicado sem erro."
- **Tipo:** unitário (config), **parametrizado**
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker_config.py` (novo)
- **Pré-condição:** sub-casos:
  1. config **sem** a chave `sync.circuit_breaker` (bloco inteiro ausente);
  2. config com `sync.circuit_breaker` presente mas **apenas um** subcampo
     preenchido (ex.: só `issue.max_failures`), demais ausentes;
  3. config com `sync.circuit_breaker.persistence` ausente (demais presentes).
- **Passos:** chamar a validação de config (`check_config`/validação dedicada)
  e, em seguida, a resolução dos parâmetros efetivos para cada sub-caso.
- **Resultado esperado:** nenhum sub-caso levanta `ConfigError`; os valores
  efetivos resolvidos correspondem exatamente aos defaults do contrato do
  corpo da issue: `persistence: file`, `issue.max_failures: 3`,
  `issue.block_duration: 300`, `issue.max_blocks: 3`,
  `platform.max_blocked_issues: 5`, `platform.block_window: 600`,
  `platform.block_duration: 900`, `half_open.success_threshold: 2`. A esteira
  inicia normalmente (sem `SystemExit`) em todos os sub-casos.
- **Observações:** cobre RF-17, RN-15, RNF-03 (configurabilidade). Seguir o
  padrão de `validate_agent_circuit_break`/`resolve_policy` (`bool` rejeitado
  antes de `int`, mensagem citando o caminho do campo quando um valor presente
  for inválido — ver CT-17b).

### CT-17b — Valores presentes fora da restrição são rejeitados citando o caminho

- **CA de origem:** CA-13 (contraparte — valores presentes mas inválidos não
  são "ausência", então devem ser validados).
- **Tipo:** unitário (config), **parametrizado**
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker_config.py`
- **Pré-condição:** sub-casos, cada um com exatamente um campo inválido:
  1. `issue.max_failures: 0` (deve ser >= 1, conforme tabela de validação do
     corpo da issue);
  2. `issue.max_failures: true` (bool rejeitado antes de int);
  3. `issue.block_duration: -1`;
  4. `issue.max_blocks: 0`;
  5. `platform.max_blocked_issues: 0`;
  6. `platform.block_window: 0`;
  7. `platform.block_duration: 0`;
  8. `half_open.success_threshold: 0`;
  9. `persistence: "disk"` (fora do enum `file`/`memory`);
  10. campo desconhecido dentro de qualquer nível (ex.: `issue.foo: 1`).
- **Passos:** chamar a validação de config para cada sub-caso.
- **Resultado esperado:** cada sub-caso levanta `ConfigError` cuja mensagem cita
  o caminho completo do campo inválido (ex.: `sync.circuit_breaker.issue.
  max_failures`); a falha ocorre antes de qualquer alteração de estado
  (análogo ao posicionamento de `validate_agent_circuit_break` em
  `check_config`, antes de `InstanceLock.acquire()`).
- **Observações:** cobre RNF-03 e a validação de forma implícita em CA-13 (um
  valor presente mas fora de restrição não é "ausente" — não pode ser
  silenciosamente aceito nem silenciosamente substituído pelo default).

---

## Grupo I — Absorção da remediação E4 (CT-12 da issue)

### CT-18 — Erro hoje tratado por E4 é conduzido pelo circuit-breaker, sem mecanismo paralelo

- **CA de origem:** CA-14 — "Dado que um erro de sincronismo hoje tratado pela
  remediação E4 (erro de validação do board corrigível pelo agente) ocorre,
  quando ele é detectado, então o tratamento (escalação ao agente dedicado,
  fail-stop na reincidência) é conduzido por este circuit-breaker, sem um
  mecanismo de remediação paralelo e independente ativo ao mesmo tempo."
- **Tipo:** unitário/integração (guarda de arquitetura + comportamento)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py` e uma guarda de
  regressão dedicada (ex.: `tests/test_remediation_e4_absorvida.py`)
- **Pré-condição:** uma falha classificada como `corrigivel_pelo_agente`
  (HTTP 422/"Validation Failed", a mesma condição hoje tratada por
  `RemediationSignal`/`RemediationFailStop`) ocorre repetidamente na mesma
  issue, em quantidade suficiente para escalar segundo as regras deste novo
  circuit-breaker (ou seja, trafega pelo MESMO caminho de contagem de falhas de
  issue que CT-01/CT-08, não por um caminho separado de E4).
- **Passos:**
  1. Provocar a sequência de falhas `corrigivel_pelo_agente` necessária para
     escalar ao agente dedicado deste circuit-breaker.
  2. Verificar: (a) que a escalação ocorreu pelo caminho do circuit-breaker
     (mesmo contrato de prompt/log de CT-08); (b) que `RemediationSignal`/
     `RemediationFailStop` NÃO são mais produzidos/consumidos em paralelo para
     este mesmo evento (ausência de duplo acionamento de agente para a mesma
     causa).
  3. Guarda de regressão: inspecionar estaticamente que não há dois caminhos de
     código ativos simultaneamente tratando "erro corrigível pelo agente +
     fail-stop na reincidência" (um é absorvido/removido, ou o antigo delega
     inteiramente ao novo).
- **Resultado esperado:** existe **um único** caminho de escalação+fail-stop
  para erro corrigível pelo agente — o do circuit-breaker desta issue; não há
  dois acionamentos de agente (um do E4 antigo, outro do novo mecanismo) para a
  mesma falha; não há duas contagens independentes de "quantas vezes esta falha
  já ocorreu" disputando a decisão.
- **Observações:** cobre RF-13, RN-11, RNF-06 (dono único da responsabilidade).
  Este é o caso mais sensível a como o desenvolvimento implementa a absorção —
  a QA fixa o **resultado observável** (uma só escalação, um só fail-stop por
  episódio, nenhuma duplicação), não o mecanismo de remoção/delegação do código
  antigo.

---

## Grupo J — Robustez de borda e isolamento (derivados de RN-03/RN-04/RN-06)

### CT-19 — Bordas de duração de bloqueio (expiração exata não libera prematuramente)

- **CA de origem:** derivado de CA-2/CA-3 (RN-03/RN-04) — precisão temporal do
  contrato "quando a duração de bloqueio expira".
- **Tipo:** unitário (circuit-breaker), relógio controlável, **parametrizado**
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** issue bloqueada com `issue.block_duration: 300`; três
  sub-casos de relógio: `t0 + 299`, `t0 + 300`, `t0 + 301` (onde `t0` é o
  instante do bloqueio).
- **Passos:** para cada sub-caso, posicionar o relógio no instante alvo e
  verificar se a issue já é avaliada em meio-aberto (sync tentado) ou ainda
  retida (bloqueio ainda vigente).
- **Resultado esperado:** em `t0 + 299` a issue permanece bloqueada (bloqueio
  ainda vigente, sync NÃO tentado); em `t0 + 300` e `t0 + 301` a issue já está
  em meio-aberto (sync tentado). O caso fixa a borda exata do contrato
  (consistente com a borda fechada em `T` já adotada pelo
  `agent_circuit_break`/#306 para janelas, aplicada aqui à duração de bloqueio)
  — se o desenvolvimento adotar borda estritamente maior (`> 300` em vez de
  `>= 300`), o caso deve ser ajustado para refletir a decisão documentada, mas
  a fronteira **precisa ser determinística e testada**, não implícita.
- **Observações:** cobre RNF-01 (ausência de loop) por precisão temporal.

### CT-20 — Duas plataformas distintas bloqueiam de forma independente

- **CA de origem:** derivado de CA-5 (RN-06), reforçando "sem interromper o
  restante da esteira" com múltiplas plataformas reais (não apenas múltiplos
  boards da mesma plataforma).
- **Tipo:** integração (circuit-breaker de plataforma + loop)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** dois boards configurados em plataformas distintas (ou dois
  adapters fake distintos simulando plataformas diferentes); a plataforma A
  acumula bloqueios de issue até bloquear a plataforma inteira; a plataforma B
  nunca falha.
- **Passos:**
  1. Bloquear a plataforma A (sequência de CT-06).
  2. No mesmo ciclo/rodada do loop, processar o sincronismo da plataforma B.
- **Resultado esperado:** a plataforma B realiza sincronismo normalmente
  (chamadas de up/down acontecem), sem qualquer atraso ou bloqueio decorrente do
  estado da plataforma A; a plataforma A permanece bloqueada e pulada até
  `platform.block_duration` expirar.
- **Observações:** cobre RF-07, RN-06 de forma mais forte que CT-07 (múltiplas
  plataformas reais, não apenas múltiplos boards). Fora de escopo real hoje
  (a esteira só tem o adapter GitHub), mas o teste deve validar a
  **generalização estrutural** do isolamento por `board_id`/plataforma, não
  assumir hardcoded um único board global.

### CT-21 — Estado do circuit-breaker de sync não expõe conteúdo sensível e é protegido

- **CA de origem:** aplicação, por extensão arquitetural, do mesmo padrão de
  segurança de estado já exigido ao `agent_circuit_break` (#306) — a issue não
  lista um RNF equivalente explícito, mas o contrato de "Configuração e
  contratos" exige persistência em "arquivo JSON protegido (mesmo padrão de
  `.pipe/agentCircuitBreak.json`)".
- **Tipo:** varredura/revisão (guarda estática) + unitário
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py` e extensão de
  `tests/test_build_prompt_protected_paths.py`
- **Pré-condição:** issue com corpo contendo um marcador único (ex.:
  `CORPO_SECRETO_456`); circuit-breaker provoca bloqueio/escalação.
- **Passos:**
  1. Provocar bloqueio e escalação.
  2. Ler o arquivo de estado persistido do circuit-breaker (verificação de
     teste da persistência).
  3. Verificar que o novo caminho de estado está listado em `PROTECTED_PATHS`
     e que `build_prompt` rejeita o caminho se ele aparecer no prompt.
- **Resultado esperado:** o estado persistido contém apenas identificação de
  contexto, contadores, timestamps e progresso de sinalização — nunca
  `CORPO_SECRETO_456`, prompt completo ou credencial; `PROTECTED_PATHS` lista o
  novo arquivo; `build_prompt` levanta `ValueError` se o caminho aparecer no
  prompt enviado ao agente (mesmo padrão dos demais `.pipe/*`).
- **Observações:** alinhado à política de arquivos protegidos já existente; sem
  este caso, um novo arquivo de estado poderia escapar da lista e ser acessível
  ao agente por engano.

### CT-22 — Persistência `memory` não sobrevive a reinício do processo

- **CA de origem:** cenário obrigatório CT-13 da issue — "Dado
  `sync.circuit_breaker.persistence: memory` configurado, quando o processo
  reinicia, então o estado do circuit-breaker não sobrevive."
- **Tipo:** unitário (persistência)
- **Arquivo/alvo:** `tests/test_sync_circuit_breaker.py`
- **Pré-condição:** `sync.circuit_breaker.persistence: memory`; issue com
  contadores de falha acumulados (abaixo do limite de bloqueio); simular
  "reinício do processo" limpando qualquer estrutura em memória do módulo
  (equivalente ao padrão usado para `_rerun_cache`/`_remediated_targets` em
  outros testes de reinício), preservando (ou não, dependendo de onde
  `memory` vive) qualquer arquivo em disco.
- **Passos:**
  1. Acumular falhas abaixo do limite de bloqueio com `persistence: memory`.
  2. "Reiniciar" o processo (limpar estado em memória do módulo).
  3. Verificar a contagem de falhas da issue após o reinício.
- **Resultado esperado:** após o reinício simulado, a contagem de falhas da
  issue volta a zero (o estado não sobreviveu); a issue não está mais "a uma
  falha de ser bloqueada" como estava antes do reinício. Sub-caso de controle:
  com `persistence: file`, o mesmo reinício simulado preserva a contagem
  (estado sobrevive) — reforçando a distinção comportamental entre as duas
  opções.
- **Observações:** cobre RF-17, RNF-03. Distinção comportamental central da
  chave `persistence`; sem este caso, as duas opções seriam indistinguíveis em
  teste.

---

## Mapa: cenários obrigatórios da issue (CT-01..CT-13) → casos deste documento

| CT da issue | Descrição | Caso(s) neste documento |
|-------------|-----------|--------------------------|
| CT-01 | Bloqueio de issue por falhas | CT-01, CT-02 |
| CT-02 | Meio-aberto e fechamento | CT-03, CT-04 |
| CT-03 | Meio-aberto e reabertura | CT-05 |
| CT-04 | Bloqueio de plataforma | CT-06, CT-07, CT-20 |
| CT-05 | Escalação ao agente dedicado | CT-08, CT-08b, CT-09 |
| CT-06 | Encerramento crítico | CT-10, CT-11 |
| CT-07 | Rate limit não conta | CT-15, CT-16 |
| CT-08 | Relação já existente idempotente | CT-13 |
| CT-09 | Progresso gravado em falha | CT-14 |
| CT-10 | Descida sempre completa | CT-12 |
| CT-11 | Defaults de configuração | CT-17, CT-17b |
| CT-12 | Absorção da remediação E4 | CT-18 |
| CT-13 | Persistência configurável | CT-22 |

> Os 13 cenários obrigatórios (CT-01..CT-13 da issue) estão integralmente
> cobertos; as robustezes de borda e isolamento adicionais (CT-19, CT-20,
> CT-21) e a segurança do estado completam a cobertura sem extrapolar o escopo.

---

## Fora de escopo dos casos (alinhado à issue)

Os seguintes **não** são testados aqui por estarem fora do escopo da issue:

- painel ou métricas visuais de circuit-breaker;
- notificação externa (webhook, e-mail) no bloqueio de plataforma;
- circuit-breaker para o fluxo de execução de agentes em tarefas normais (tema
  do `agent_circuit_break`/#306, distinto e não alterado — os casos acima
  tratam-no apenas como referência arquitetural, nunca testam seu
  comportamento);
- tratamento ou alteração do mecanismo de rate limit/penalty em si (só sua
  EXCLUSÃO da contagem deste circuit-breaker é testada — CT-15/CT-16);
- otimização de agrupamento de chamadas de sincronismo à plataforma;
- execução assíncrona de agentes e seus efeitos sobre sessão/agente em
  execução;
- criação de um novo agente configurável no `pipe.yml` para a correção da
  esteira além do necessário para a escalação definida aqui (o "agente
  dedicado" referenciado nos casos é tratado como já resolvível pela
  configuração existente — a forma exata de declará-lo é decisão de
  desenvolvimento, não testada aqui como requisito de schema novo, pois a
  issue explicitamente tira isso de escopo).

### Não regressão

A suíte existente deve continuar passando, em especial:
`tests/test_error_classification.py` (classify_error, inalterado nas
categorias que não o papel de disparo de E4 de `corrigivel_pelo_agente`, que
migra de dono mas mantém a classificação em si), `tests/
test_remediation_loop.py` (se E4 for removido/delegado, os testes que hoje
exercitam `RemediationSignal`/`RemediationFailStop`/`remediate_pending`
diretamente devem ser atualizados pelo desenvolvimento para refletir a nova
forma — não são "não regressão" no sentido literal, pois o comportamento
OBSERVÁVEL migra de dono por decisão desta issue, mas o resultado observável
agregado, CT-18, deve se manter: uma escalação, um fail-stop, sem duplicação),
`tests/test_sync_unico_sem_segundo_modo.py`, `tests/test_sync_optimization.py`,
`tests/test_remedios_bloqueio.py` (remédios 1/2/3 de bloqueio, inalterados por
esta issue) e `tests/test_rate_limit_detection.py` (detecção de rate limit
continua estrutural, por `PenaltyException`/status HTTP/GraphQL, nunca por
varredura de texto).
