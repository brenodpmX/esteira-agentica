# Incidente — Parent Recursivo (#76)

## Registro

**Incidente ID:** 97
**Status:** Em Análise
**Owner:** engenharia
**Data de Abertura:** 2026-08-01 13:29
**Last Updated:** 2026-08-01 13:35

### Descrição

A esteira agêntica v1.6.0 entrou em loop de erro tentando aplicar
`set_parent(76, 76)` na issue `#76` do board `story`. O GitHub rejeita a
operação e o evento permanece na cabeça da fila global, travando **toda** a
esteira (nenhuma tarefa executada) por 2h37 até parada manual.

**Erro retornado:**

```
gh: An error occurred while adding the sub-issue to the parent issue.
Sub issue cannot be the same as the parent issue (HTTP 422)
```

### Impacto observado

- Parada total da esteira entre 10:49:40 e 13:29:17 (nenhuma execução de agente).
- 225 ciclos com o mesmo erro (10:52:28 → 13:17:15), logados como "não fatal".
- Título e body da issue `#76` no GitHub sobrescritos por conteúdo de outro arquivo.
- ~700–900 requisições de API desperdiçadas.

## Triagem

**Problema confirmado:** sim, reproduzível a partir do log anexado à issue.

**Classificação:** bug de robustez do core (falta de validação de
auto-referência em `/parent`) combinado a dado de entrada inválido.

**Severidade:** Média (elevada a Alta na análise técnica, ver abaixo).

**Recomendação da triagem:** validar `parent_id != issue_id` antes de chamar a
API e tratar o 422 de self-parent como erro definitivo, sem reenfileirar.

— Isabela Gomes - Tech Lead

## Análise Técnica

### Sequência de eventos (todas as linhas verificadas em log)

| Hora | Evento | Evidência |
|------|--------|-----------|
| 10:33:44 | Agente Tech Lead executa `#76` em `planejamento-tecnico` e cria 3 arquivos de task **corretamente sem prefixo numérico** em `.pipe/boards/task/backlog/` | `logs/76/2026-08-01_10-33-44.md:294,374,495` |
| 10:36:27 | `change-up` move `#76` para `aguardando-tasks`; `change-down` reescreve o body | `logs/2026-08-01.json:802-816` |
| 10:36:57 | Agente de Operações inicia em `#76`; **essa execução estoura o timeout de 3600s** e é morta às 11:36 (chat não gravado) | `logs/76/2026-08-01_10-36-57.md` (`[TIMEOUT] Agente excedeu 3600s`) |
| 10:39 | Surgem em `story/aguardando-tasks/` **3 cópias das tasks com prefixo numérico `76-`** (proibido). Duas contêm `/parent #76` e `/labels git, cleanup` | `ls -la .pipe/boards/story/aguardando-tasks/` (mtime 10:39) |
| 10:45–10:47 | A mesma execução chama o adapter do GitHub **fora do fluxo da esteira** (`set_parent` de #94/#95/#96 → 76) | `logs/2026-08-01.json:835-844` |
| 10:48:43 | **Segunda instância da esteira** é iniciada enquanto a execução anterior seguia viva; startup apaga a fila | `logs/2026-08-01.json:846-851` |
| 10:49:20 | `#94/#95/#96` aparecem como `create-down` — foram criadas direto na API, não via `create-up` | `logs/2026-08-01.json:888-894` |
| 10:49:40 | Agente roda de novo em `#76` e **reescreve `.pipe/boards/story/snapshot.json`** (arquivo protegido) para inserir `children`/`blocked_by` | `logs/76/2026-08-01_10-49-40.md:414,577` |
| ~10:52:10 | O agente move os 3 arquivos de `#76` de `aguardando-tasks` para `change-file` (advance) | `logs/76/2026-08-01_10-49-40.md` (bloco `mv`) |
| 10:52:20 | `change-up #76`: o `body_path` do snapshot aponta para `aguardando-tasks/76-consolidacao_...` que **já não existe**. `_find_issue_files` cai no fallback `rglob("76-*-body.md")` e devolve **um arquivo órfão** | `src/core/sync.py:32-52` |
| 10:52:21–25 | Sequência aplicada com o conteúdo do órfão: `update_issue`, `set_labels ['git','cleanup']`, `set_parent 76` | `logs/2026-08-01.json:910-912` |
| 10:52:28 | `_add_sub_issue("76","76")` → HTTP 422; exceção sobe ao `except Exception` de `main()` e vira "Erro no ciclo (não fatal)" | `src/adapters/github_board.py:1115-1122`, `src/__main__.py:496-498` |
| 10:52:28→13:17:15 | 225 repetições idênticas; nenhum agente executado; parada manual (`KeyboardInterrupt`) | `grep -c "Erro no ciclo"` |
| 13:28:07 | Restart: startup remove a fila, `change-down` reconcilia `#76` e a esteira volta a andar | `logs/2026-08-01.json:2168-2173` |

### Reprodução do caminho no core

Executando o parse do arquivo órfão + `apply_commands` com o estado conhecido
do snapshot, o resultado é exatamente a sequência do log:

```
parent parseado: 76
chamadas: [('set_labels', '76', ['git', 'cleanup']), ('set_parent', '76', '76')]
```

### Causa raiz — 4 defeitos encadeados

**C1. Fallback cego na resolução do arquivo da issue** (`src/core/sync.py:32-52`)
Quando o `body_path` registrado no snapshot está obsoleto (arquivo movido), o
fallback `rglob("{id}-*-body.md")` retorna o **primeiro** arquivo que casa com o
prefixo, sem validar que ele pertence àquela issue. Com arquivos órfãos
prefixados `76-` na mesma pasta, a esteira passou a tratar um arquivo de task
como se fosse o body da story `#76`. É o gatilho imediato e também a origem da
corrupção de dados — `update_issue` sobrescreveu a issue com o conteúdo errado
**antes** de falhar.

**C2. Nenhuma validação de auto-referência** (`src/core/board.py:300-302,322-411`;
`src/core/commands.py:parse_commands`)
Nada impede `parent == issue_id` (nem em `children`, `blocked_by`, `blocks`).
A condição só é detectada pela API do GitHub, já em rede.

**C3. Fila sem tratamento de mensagem-veneno** (`src/core/change_queue.py`,
`src/core/sync.py:436-465`)
O modelo é at-least-once: `getNext()` apenas espia e `remove(uuid)` só ocorre
após sucesso. Qualquer exceção não-`Penalty` aborta `apply_changes` e o item
fica na cabeça de uma fila **única e global** para todos os boards →
head-of-line blocking. Combinado com `if had_changes or queue.size() > 0:
index = 0; continue` em `main()`, a esteira nunca chega a `keep_task` — daí a
parada total, e não apenas do board `story`. Hoje só o erro de issue fantasma
(`Could not resolve to an issue or pull request`) é tratado como definitivo;
qualquer outro 4xx repete para sempre.

**C4. Proteção do estado interno é apenas declarativa**
`PROTECTED_PATHS`/`build_prompt` validam somente o texto do prompt e o
`CONTEXT.md` apenas instrui. Na prática o agente leu e **reescreveu**
`snapshot.json`, criou arquivos com prefixo numérico proibido, chamou o adapter
direto e subiu uma segunda instância da esteira. Não há enforcement no
filesystem, verificação de integridade pós-execução nem lock de instância.

### Agravantes

- Arquivos com prefixo numérico que não correspondem a nenhuma issue do
  snapshot são **silenciosamente ignorados** por `detect_local_changes` (o ramo
  de `create-up` só considera arquivos sem prefixo). Trabalho local nunca sobe
  e ninguém é avisado.
- 225 erros idênticos sem nenhum escalonamento: sem contador de tentativas, sem
  `need_human`, sem alerta.
- Timeout de agente (3600s) mata a execução sem registrar o chat, apagando a
  trilha de auditoria justamente da execução que gerou os arquivos órfãos.

### Estado atual (pós-incidente)

- `#76` no GitHub está com título e labels de outra tarefa:
  `Remover branch feature/1-1-rodar_no_docker (nomenclatura antiga)`,
  labels `git`, `cleanup` (verificado com `gh issue view 76`).
- O conteúdo original da story está preservado em
  `.pipe/boards/story/change-file/76-consolidacao_de_duplicidade_e_nomenclatura_antiga-body.md`
  → **recuperável**.
- Ainda existem **4 arquivos** com prefixo `76-` em duas colunas do board
  `story` → a colisão persiste e a reincidência é possível.
- `snapshot.json` do board `story` foi editado à mão pelo agente.

### Respostas da análise

**Qual a causa?**
`body_path` obsoleto no snapshot (arquivos movidos pelo agente) + arquivos
órfãos com prefixo `76-` → fallback do `_find_issue_files` devolve o arquivo
errado → o comando `/parent #76` do órfão é aplicado à própria `#76` → HTTP 422
→ item-veneno na cabeça da fila global → esteira parada. Nenhum deploy está
envolvido: o último commit é de 2026-07-23; a falha é de dados sobre defeitos
pré-existentes.

**Qual o risco?**
- Disponibilidade: **Alto**. Parada total, silenciosa (log "não fatal") e sem
  autorrecuperação. Qualquer erro 4xx não mapeado reproduz o mesmo padrão.
- Integridade: **Médio-alto**. Já se materializou: conteúdo de issue
  sobrescrito no board e snapshot adulterado. Uma issue pode ser sobrescrita
  por outra sempre que houver colisão de prefixo.
- Financeiro: **Baixo**. Apenas quota de API (~700–900 chamadas), dentro do
  limite de 5000 pontos/h.

**Existe workaround?**
Sim, em dois níveis.
1. *Imediato (foi o que ocorreu às 13:28):* parar e reiniciar a esteira — o
   startup remove a fila e descarta o item-veneno. Efeito colateral: perde
   eventos pendentes (parcialmente mitigado pelo fullsync de startup).
2. *Para este caso concreto:* remover os 3 arquivos órfãos com prefixo `76-`
   de `story/aguardando-tasks/`, restaurar o body da story a partir de
   `change-file/76-consolidacao_...-body.md` e corrigir título/body de `#76` no
   GitHub. Enquanto os órfãos existirem, a reincidência é possível.

Nenhum dos dois evita a recorrência do padrão — ambos são paliativos.

**Quanto custa corrigir?**

| # | Correção | Arquivos | Esforço |
|---|----------|----------|---------|
| C1 | Fallback seguro na resolução do body: exigir que o arquivo não esteja registrado para outra issue e que o slug seja compatível; sem match confiável, não sincroniza, loga erro e marca `need_human`. Reportar arquivos órfãos com prefixo numérico em vez de ignorá-los | `src/core/sync.py` (`_find_issue_files`, `detect_local_changes`) | 3h |
| C2 | Validar auto-referência em `parent`/`children`/`blocked_by`/`blocks`: descartar a referência à própria issue com warning | `src/core/board.py`, `src/core/commands.py` | 1h |
| C3 | Erro definitivo não reenfileira: 4xx não-transitório é descartado com warning + `need_human`; contador de tentativas na fila com dead-letter | `src/core/sync.py`, `src/core/change_queue.py`, `src/core/board.py` | 4h |
| C4 | Enforcement do estado interno: hash do snapshot antes/depois da execução do agente, com restauração e log em caso de alteração | `src/core/snapshot.py`, `src/__main__.py` | 3h |
| C5 | Lock de instância única (`.pipe/pipe.lock`) impedindo segunda esteira em paralelo | `src/__main__.py` | 1,5h |

**Total:** ~12,5h (≈2 dias de 1 dev sênior), testes de regressão incluídos.
**Hotfix mínimo:** C2 + C3 em ~5h — encerra o loop e a parada total, mas
**não** impede a sobrescrita de conteúdo entre issues; para isso C1 é
obrigatória.

**Ordem recomendada:** C2 → C3 → C1 → C4 → C5. C2/C3 são independentes e
podem sair juntas como hotfix; C1 é a correção de integridade; C4/C5 fecham a
porta que permitiu o dado inválido entrar.

— Bruno Ferreira - Engenheiro de Software SR

## Decisão de tratamento

**Opção escolhida: 1 — continuar como incidente produtivo.**

### Justificativa

A análise técnica classificou o risco de disponibilidade como **Alto** (parada
total e silenciosa, sem autorrecuperação, reproduzível por qualquer 4xx não
mapeado) e o de integridade como **Médio-alto**, com dano **já materializado**:
a issue `#76` está no GitHub com título/labels de outra tarefa, o
`snapshot.json` do board `story` foi adulterado manualmente pelo próprio agente,
e ainda restam 4 arquivos órfãos com prefixo `76-` no board `story` — ou seja,
a condição que originou o incidente **persiste** e pode reincidir a qualquer
sync seguinte. Isso não é compatível com Opção 2 (task de correção pontual):
- Opção 2 pressupõe problema leve/intermediário resolvido por uma única task
  de correção, com o trabalho desta issue já concluído ao criá-la. Aqui há
  causa raiz de **4 defeitos encadeados** (C1–C4) mais um item de hardening
  (C5), estado de dados já corrompido pendente de reparo, e risco de
  recorrência enquanto os arquivos órfãos não forem removidos — isso excede o
  escopo de uma task isolada e exige planejamento técnico rastreável (várias
  issues, com ordem de execução definida) e acompanhamento pelo próprio fluxo
  de incidente.
- Não é Opção 3 (nova funcionalidade): não há pedido de funcionalidade nova,
  apenas correção de defeitos de robustez em código existente.
- Não é Opção 4 (nada a fazer): o problema é confirmado, reproduzível, com
  corrupção de dados já ocorrida e risco Alto de disponibilidade documentado.

### Ação proposta

Manter a issue `#97` no board de incidente e seguir o fluxo normal:

1. **Reparo do estado corrompido (pré-requisito, antes ou em paralelo às
   correções de código):**
   - Restaurar título/body da issue `#76` no GitHub a partir do conteúdo
     preservado em
     `.pipe/boards/story/change-file/76-consolidacao_de_duplicidade_e_nomenclatura_antiga-body.md`.
   - Remover os 3 arquivos órfãos com prefixo `76-` em
     `.pipe/boards/story/aguardando-tasks/` (e o eventual 4º arquivo com esse
     prefixo identificado no board `story`), após confirmar que nenhum
     conteúdo útil se perde.
   - Auditar/corrigir manualmente o `snapshot.json` do board `story` (foi
     editado à mão pelo agente durante o incidente) antes de confiar nele
     novamente.
2. **Planejamento técnico** (próxima etapa do fluxo, `planejamento-tecnico`):
   decompor as correções C1–C5 já dimensionadas na Análise Técnica em tasks
   rastreáveis no board `task`, na ordem recomendada **C2 → C3 → C1 → C4 →
   C5**:
   - C2 — Validar auto-referência em `parent`/`children`/`blocked_by`/`blocks`
     (`src/core/board.py`, `src/core/commands.py`) — ~1h.
   - C3 — Erro definitivo não reenfileira; contador de tentativas e
     dead-letter na fila (`src/core/sync.py`, `src/core/change_queue.py`,
     `src/core/board.py`) — ~4h.
   - C1 — Fallback seguro em `_find_issue_files`/`detect_local_changes`,
     rejeitando match ambíguo e reportando arquivos órfãos com prefixo
     numérico em vez de ignorá-los (`src/core/sync.py`) — ~3h.
   - C4 — Verificação de integridade do `snapshot.json` antes/depois da
     execução do agente, com restauração automática em caso de alteração
     (`src/core/snapshot.py`, `src/__main__.py`) — ~3h.
   - C5 — Lock de instância única (`.pipe/pipe.lock`) impedindo segunda
     esteira em paralelo (`src/__main__.py`) — ~1,5h.
   - Esforço total estimado: ~12,5h. Hotfix mínimo (C2+C3, ~5h) encerra o
     loop e a parada total, mas não impede sobrescrita de conteúdo entre
     issues — C1 é obrigatória para integridade.
3. Nenhuma nova issue é criada nesta etapa (Decisão de tratamento): a criação
   das tasks C1–C5 é responsabilidade da etapa `planejamento-tecnico`,
   seguindo o fluxo padrão do board de incidente.

— Isabela Gomes - Tech Lead

## Tarefas de correção

Decomposição das correções C1–C5 (Análise Técnica) em tasks rastreáveis no
board `task`, seguindo a ordem recomendada **C2 → C3 → C1 → C4 → C5**. As
dependências entre tasks (`/blocked_by`) seguem essa mesma ordem, exceto C4/C5
que são independentes entre si e de C1 (fecham frentes diferentes: proteção de
estado interno e lock de instância).

| # | Task | Arquivos | Esforço | Depende de |
|---|------|----------|---------|------------|
| C2 | Validar auto-referência em parent/children/blocked_by/blocks | `src/core/board.py`, `src/core/commands.py` | 1h | — |
| C3 | Erro definitivo não reenfileira + contador de tentativas e dead-letter | `src/core/sync.py`, `src/core/change_queue.py`, `src/core/board.py` | 4h | C2 |
| C1 | Fallback seguro na resolução do body da issue + reportar arquivos órfãos | `src/core/sync.py` | 3h | C3 |
| C4 | Verificação de integridade do snapshot antes/depois da execução do agente | `src/core/snapshot.py`, `src/__main__.py` | 3h | C1 |
| C5 | Lock de instância única (`.pipe/pipe.lock`) | `src/__main__.py` | 1,5h | C1 |

Tasks criadas no board `task` (coluna `todo`):

- C2 — `validar_auto_referencia_em_relacoes_parentchildrenblocked_byblocks-body.md`
- C3 — `erro_definitivo_nao_reenfileira_contador_de_tentativas_e_dead_letter_na_fila-body.md`
- C1 — `fallback_seguro_na_resolucao_do_body_da_issue_e_reporte_de_arquivos_orfaos-body.md`
- C4 — `verificacao_de_integridade_do_snapshot_na_execucao_do_agente-body.md`
- C5 — `lock_de_instancia_unica_da_esteira-body.md`

Cada task referencia esta issue (`#97`) como pai (`/parent #97`) e registra as
dependências de ordem via `/blocked_by`/`/blocks` conforme a tabela acima.

— Isabela Gomes - Tech Lead
