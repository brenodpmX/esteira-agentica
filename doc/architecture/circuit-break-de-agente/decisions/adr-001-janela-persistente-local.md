# ADR-001 — Janela deslizante persistente em estado local

Status: proposed
Owner: architecture
Last updated: 2026-08-25

## Inputs
- `doc/requirements/circuit-break-de-agente/functional-requirements.md` (RF-001, RF-002, RF-004, RF-006, RF-007)
- `doc/requirements/circuit-break-de-agente/business-rules.md` (RN-001, RN-002, RN-003, RN-006, RN-007)
- `doc/requirements/circuit-break-de-agente/non-functional-requirements.md` (NFR-001, NFR-004, NFR-005, NFR-007, NFR-008)
- `src/__main__.py` (`keep_task`, cooldown e loop sequencial)
- `src/core/session.py`, `src/core/change_queue.py`, `src/core/snapshot.py` (precedentes de persistência local)
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md` (InstanceLock e proteção de estado)

## Contexto
O mecanismo precisa contar toda decisão de entrega, aplicar uma janela temporal exata, sobreviver a restart, continuar registrando sem política ativa e esquecer a franquia quando a issue muda de coluna. O runtime é um processo sequencial com exclusividade sobre `.pipe`; adicionar armazenamento externo resolveria um problema de concorrência que o produto não possui.

Foram consideradas:

1. cache apenas em memória, como o cooldown — simples, mas restart libera o limite e perde a contagem feita sem política;
2. contador fixo com timestamp inicial — pequeno, mas não implementa janela deslizante exata;
3. buckets temporais — mais compactos, porém aproximam a borda e violam NFR-004;
4. banco SQLite — correto, mas adiciona schema/transação/dependência operacional desnecessários ao volume atual;
5. lista de timestamps persistida em JSON — exata, inspecionável pelo core e coerente com o estado existente.

## Decisão
Criar `CircuitBreakStore` no core, persistido em `.pipe/agentCircuitBreak.json`, com schema versionado e escrita atômica por arquivo temporário, `fsync` e `os.replace`.

O store mantém um contexto ativo por `(board, issue)` com:

- `column`, que completa a identidade `(board, coluna, issue)`;
- `occurrences`, lista ordenada de epoch UTC para decisões de entrega;
- `trip`, evento de bloqueio pendente ou `null`.

`admit(context, now, policy)` executa sob uma única sequência read-modify-write:

1. se a coluna observada difere da persistida, substitui o contexto por um vazio;
2. se há `T`, remove timestamps cuja idade seja `>= T`;
3. se existe `trip`, retorna `DENY_PENDING_SIGNAL`;
4. se a política existe e o total é `>= N`, grava um novo `trip`, esvazia `occurrences` e retorna `DENY_TRIPPED`;
5. caso contrário, acrescenta `now`, persiste e retorna `ALLOW`.

A ocorrência é persistida antes de a tarefa sair de `keep_task`. Portanto, um erro posterior ainda conta como decisão de entrega, conforme RN-001. Sem política, o passo 5 continua ocorrendo e nenhum bloqueio é avaliado.

Os pontos do core que detectam auto-advance ou mudança remota chamam `reset_context(board, issue, new_column)`. A comparação no próprio `admit` é defesa adicional. O histórico da coluna anterior é descartado, não arquivado: ele não participa de decisões futuras e reter histórico não é requisito.

## Justificativa
A lista de timestamps é a estrutura mais simples que satisfaz simultaneamente janela deslizante exata, ativação posterior da política e persistência. JSON preserva o modelo operacional atual; `InstanceLock` elimina concorrência entre processos e dispensa banco. Um contexto ativo por issue garante que retorno à mesma coluna comece uma franquia nova.

Persistir antes da entrega torna check e registro atomicamente observáveis do ponto de vista do loop. Se a gravação falhar, a issue não é entregue; permitir seria incompatível com a meta de zero execuções excedentes.

## Consequências
- Positivas: borda temporal exata; restart não burla o limite; nenhuma dependência nova; estado compatível com volumes Docker; testes determinísticos com relógio injetável.
- Negativas: sem política não há `T` para podar ocorrências, então a lista do contexto ativo cresce linearmente até mudança de coluna, remoção da issue ou ativação da política.
- Negativas: uma decisão registrada pode contar mesmo que uma falha interna posterior impeça o adapter de iniciar; isso é intencional porque o evento de domínio é a decisão de entrega, não o resultado externo.
- Riscos: clock do host retroceder pode prolongar a permanência de timestamps. A primeira versão assume relógio sincronizado e registra anomalia; relógio distribuído está fora de escopo.
- Riscos: JSON corrompido não pode ser tratado como vazio sem abrir o gate. O startup deve falhar com diagnóstico e preservar o arquivo para recuperação.
