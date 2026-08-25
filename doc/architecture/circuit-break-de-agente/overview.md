# Architecture Overview — Circuit-break de agente

Status: draft
Owner: architecture
Last updated: 2026-08-25

## Inputs
- `README.md` — arquitetura hexagonal, loop principal, cooldown, `need_human` e proteção de estado.
- `doc/product/circuit-break-de-agente/analise-negocio.md` — problema, escopo aprovado e referências de padrões.
- `doc/requirements/circuit-break-de-agente/functional-requirements.md` — RF-001 a RF-008.
- `doc/requirements/circuit-break-de-agente/business-rules.md` — RN-001 a RN-009.
- `doc/requirements/circuit-break-de-agente/non-functional-requirements.md` — NFR-001 a NFR-008.
- `doc/requirements/circuit-break-de-agente/glossary.md` — vocabulário do domínio.
- `doc/ux/circuit-break-de-agente/navigation-flow.md` e protótipos — superfícies e propostas de configuração/sinalização ainda em draft.
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md` — precedentes de falha localizada, estado persistente protegido e processo único.
- Código atual em `src/__main__.py`, `src/core/config.py`, `src/core/board.py`, `src/core/change_queue.py`, `src/core/snapshot.py` e `src/core/session.py`.

## Visão geral
O circuit-break conterá repetições de uma issue sem alterar a arquitetura hexagonal nem criar infraestrutura. Um componente de domínio no core manterá, por contexto ativo `(board, coluna, issue)`, os instantes em que a esteira decidiu entregar a issue ao agente. Antes de retornar uma tarefa em `keep_task`, uma operação atômica remove ocorrências expiradas, verifica o limite e registra a nova ocorrência ou abre o bloqueio.

Ao encontrar `N` ocorrências com idade menor que `T`, a próxima execução não começa. O core persiste primeiro o bloqueio e zera as ocorrências do contexto; depois usa as operações existentes de `BoardPort` para aplicar `need_human` e publicar um comentário idempotente. Falhas parciais de sinalização permanecem pendentes para nova tentativa, mas nunca liberam a execução. A varredura de `keep_task` continua, preservando o trabalho das demais issues.

A contagem é persistida mesmo sem política ativa, conforme RN-007. Quando a política não existe, o componente apenas registra ocorrências; não limita, sinaliza nem muda o comportamento atual. Mudança de coluna detectada pelo core substitui o contexto ativo da issue por um contexto vazio, inclusive quando ela retorna a uma coluna anterior.

## Estilo arquitetural
A solução é uma extensão da arquitetura hexagonal existente:

- **domínio/core:** política temporal, máquina de estados e persistência do contador;
- **orquestração:** `keep_task` chama o gate depois dos filtros atuais e antes de entregar a tarefa;
- **porta externa:** `BoardPort` continua sendo o único caminho para label e comentário;
- **adapter:** GitHub permanece sem regra de circuit-break.

Padrões compatíveis usados, sem adoção literal ou excessiva:

1. **Sliding Window Log:** timestamps exatos por contexto atendem a borda `idade < T` e aos valores arbitrários definidos pelo operador. Contador fixo ou bucket aproximado não garantiria NFR-004.
2. **Circuit Breaker com reset manual:** o estado aberto impede novas execuções, mas não há transição automática half-open. A intervenção já modelada por `need_human` é o reset operacional.
3. **Bulkhead/Poison Item:** o bloqueio pertence à issue; o loop continua procurando outro item. Não existe disjuntor global.
4. **Sinalização idempotente:** um identificador de bloqueio em comentário Markdown evita duplicação após falha parcial ou reinício, sem introduzir outbox/broker.

O nome “circuit-break” é mantido por aderência ao domínio do produto. Tecnicamente, trata-se de um limitador por janela com abertura e liberação humana, não de um detector de falhas de serviço remoto.

## Componentes
| Componente | Responsabilidade |
|-----------|------------------|
| `config.py` | Validar a política opcional e completa (`executions` e `window`, inteiros positivos), sem valores padrão implícitos. |
| `AgentCircuitBreaker` (novo, core) | Executar `admit`, podar a janela, persistir ocorrência antes da entrega, abrir bloqueio, zerar franquia e reconciliar sinalização pendente. |
| `CircuitBreakStore` (novo, core) | Ler e gravar atomicamente o estado versionado em `.pipe/agentCircuitBreak.json`; nunca expor seu path ao agente. |
| `keep_task` | Preservar filtros atuais; antes de `_is_blocked`, reconciliar eventual `trip` pendente; depois dos filtros/cooldown, chamar `admit`; ao bloquear, continuar a varredura em vez de retornar a issue. |
| Pontos de mudança de coluna no core | Notificar o circuit-break quando auto-advance ou sync detectar transição, descartando o contexto anterior. `admit` repete a comparação de coluna como defesa. |
| `Board` / `BoardPort` | Reutilizar `add_label`, `list_comments` e `add_comment`; adapters não decidem limite, janela ou retomada. |
| `ChangeQueue` / sync | Reconciliar a mutação remota para que `/need_human` apareça no body local e o gate `_is_blocked` vigente assuma o bloqueio estável. |
| `context_generator.py` / proteção do agente | Adicionar o novo arquivo à lista de caminhos protegidos e ao contexto gerado. |
| `log.py` | Emitir eventos estruturados de admissão, bloqueio, sinalização pendente e retomada, sem conteúdo protegido. |

### Estado persistido
Formato lógico proposto (não é API pública):

```json
{
  "version": 1,
  "active_contexts": {
    "epic/175": {
      "column": "arquitetura",
      "occurrences": [1787666400, 1787666700],
      "trip": null
    }
  }
}
```

Há no máximo um contexto ativo por `(board, issue)`. `column` completa sua identidade; ao detectar transição, o registro é substituído, garantindo que revisitar a mesma coluna não recupere ocorrências antigas. `occurrences` usa epoch UTC inteiro. Durante um bloqueio, `trip` contém `event_id`, parâmetros e progresso da sinalização; as ocorrências são esvaziadas antes de qualquer chamada externa.

Sem política, os timestamps do contexto ativo são preservados porque não existe uma janela segura para descartá-los. Quando `T` passa a existir, a primeira avaliação remove tudo com idade `>= T`. Contextos de issues que deixam os boards configurados são removidos após reconciliação completa.

## Fluxo principal
```text
sync/process_queue
  -> detecta mudança de coluna
     -> CircuitBreakStore substitui contexto por vazio
  -> keep_task percorre issues
     -> AgentCircuitBreaker.reconcile_pending(board, column, issue)
        -> trip pendente: tenta completar sinalização; DENY; segue outra issue
        -> sem trip: continua
     -> filtros atuais (agent, advance, blocked_by/need_human, cooldown)
     -> AgentCircuitBreaker.admit(board, column, issue, now)
        -> lê estado e remove timestamps com idade >= T (se T existe)
        -> política ativa e count >= N:
             persiste trip + zera ocorrências
             aplica need_human + comentário idempotente via BoardPort
             DENY; segue outra issue
        -> abaixo do limite ou política ausente:
             acrescenta now e persiste
             ALLOW
     -> call_agent(task)
```

### Ordem obrigatória no bloqueio
1. Persistir `trip` e limpar `occurrences`.
2. Aplicar `need_human` por `BoardPort.add_label`.
3. Verificar o marcador `<!-- agent-circuit-break:<event_id> -->` em `list_comments`; publicar apenas se ausente.
4. Solicitar reconciliação remota da issue para materializar `/need_human` localmente.
5. Manter `DENY` até a sinalização estar reconciliada; depois o `_is_blocked` atual mantém a issue parada.
6. Após correção e remoção de `need_human`, a issue volta ao estado fechado com ocorrências vazias e recebe nova franquia.

Essa ordem garante que falha de rede, crash ou reinício entre os passos não permita a execução excedente nem duplique o comentário. A aplicação de label é naturalmente idempotente; o marcador torna o comentário idempotente.

## Compatibilidade e limites
- Não se altera `rerun_cooldown`; cooldown espaça e o circuit-break limita.
- Não há chamada de rede no caminho normal de contagem/admissão; rede só é usada quando o limite abre o bloqueio ou para reconciliar pendência.
- Não há movimento automático de coluna, diagnóstico de causa, dashboard, SLA, orçamento de tokens ou políticas segmentadas.
- Não há reset por reinício do processo: estado persistente evita contornar o limite reiniciando a esteira.
- O relógio de parede UTC do host é premissa operacional; testes usam relógio injetável.
- A UX ainda precisa validar nomes/copy e dados extras. O contrato arquitetural fixa somente os dados mínimos de RN-005 e a necessidade de configuração completa; detalhes adicionais não afetam o core.

## Estratégia de validação
- **Unitários:** bordas `T-1`, `T`, `T+1`; N permitido e N+1 bloqueado; sucesso/erro do agente contam igualmente; ausência de política; retorno à mesma coluna; escrita atômica; estado corrompido; relógio injetado.
- **Máquina de estados:** crash/falha depois de cada passo da sinalização, retry sem comentário duplicado e franquia vazia após bloqueio.
- **Integração do core:** issue bloqueada seguida por outra no mesmo board e em outro board; cooldown combinado; auto-advance e mudança manual; sync refletindo `need_human`; remoção humana concedendo N novas execuções.
- **Regressão:** testes atuais de `keep_task`, cooldown, auto-advance, sync, `AgentGuard`, `SnapshotGuard` e operação sem configuração.
- **Desempenho:** medir `keep_task` sem rede no caminho normal e arquivo com múltiplos contextos; confirmar custo linear apenas no número de ocorrências do contexto avaliado.
