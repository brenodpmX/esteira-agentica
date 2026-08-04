# Arquitetura — Confiabilidade após o incidente Parent Recursivo

**Status:** proposta para validação arquitetural

**Owner:** architecture

**Última atualização:** 2026-08-04

**Incidentes relacionados:** #97 e #104

## 1. Objetivo e decisão

Esta arquitetura implementa as cinco salvaguardas aprovadas para o incidente
Parent Recursivo sem substituir a arquitetura hexagonal existente e sem criar
serviços adicionais. O core continua sequencial, os arquivos locais continuam
sendo a interface de trabalho e o GitHub continua acessado apenas por
`BoardPort`.

A solução usa mecanismos simples e locais:

1. resolução determinística do body e recusa em caso de ambiguidade;
2. sanitização de auto-referências antes da primeira chamada ao board;
3. erros tipados, tentativas limitadas e dead-letter persistente por item;
4. cópia em memória, hash e restauração dos snapshots ao redor do agente; e
5. lock de processo local com `fcntl.flock` mantido durante todo o runtime.

Não são necessários banco de dados, broker, serviço de lock distribuído,
orquestrador de workflows ou novo processo. As evidências internas são
suficientes; não foi necessária pesquisa externa.

## 2. Entradas arquiteturais revisadas

- `CONTEXT.md` — arquitetura hexagonal, fluxo principal, fila at-least-once e
  proteção atual de estado.
- `doc/architecture/rodar-no-docker/arquitetura.md` — processo único no
  Compose, volumes e encerramento por sinal.
- `doc/incidente/parent-recursivo/ticket.md` — causa raiz C1–C5 e reprodução.
- `doc/incidente/parent-recursivo/homologacao.md` e
  `doc/changelogs/97-erro_reportado_dia_010826.md` — estado mitigado e risco
  residual.
- `doc/product/confiabilidade-parent-recursivo/*` — visão, post-mortem e cinco
  épicos aprovados.
- `doc/requirements/confiabilidade-parent-recursivo/*` — RN-001 a RN-010 e
  requisitos não-funcionais.
- Código vigente em `src/core/sync.py`, `src/core/board.py`,
  `src/core/change_queue.py`, `src/core/snapshot.py`, `src/__main__.py` e
  `src/adapters/github_board.py`.

### Diagnóstico do desenho atual

O incidente atravessou quatro limites sem contenção:

```text
arquivo ambíguo
    -> fallback escolhe o primeiro body
    -> comando inválido chega ao adapter
    -> exceção genérica mantém o item na cabeça da fila
    -> loop global não processa nenhum outro trabalho
```

Além disso, `call_agent()` não verifica o estado antes/depois da execução e
`startup()` altera estado antes de garantir exclusividade. As correções devem
ser posicionadas nesses limites, não espalhadas pelos adapters.

## 3. Visão da solução

```text
                         CORE

 arquivos locais -> BodyResolver -> parse/sanitize -> BoardPort -> GitHub
                       |                 |
                       | recusa segura   | erro tipado
                       v                 v
                 IsolationRecord <- ChangeQueue -> dead-letter
                       |
                       +-> log acionável

 InstanceLock -> startup -> sync/keep_task -> SnapshotGuard -> agente
      ^                                              |
      +----------- mantido por todo o processo ------+
```

### Responsabilidades

| Componente | Responsabilidade nova | Não deve fazer |
|---|---|---|
| `sync.py` | resolver body, detectar órfãos, sanitizar antes do primeiro efeito externo e consumir falhas por item | escolher candidato ambíguo ou classificar erro por texto |
| `board.py` | expor erros tipados do port e sanitização defensiva das relações | conhecer arquivos locais ou dead-letter |
| `change_queue.py` | contabilizar tentativa, rotacionar item e isolá-lo com evidência | chamar API do board |
| `github_board.py` | traduzir resposta REST/GraphQL em erro tipado | decidir política de tentativas |
| `snapshot.py` | capturar, comparar e restaurar bytes dos snapshots protegidos | executar sync ou conhecer o agente concreto |
| `__main__.py` | manter o lock durante o processo e envolver `call_agent()` com a guarda | implementar regras de board |

## 4. Decisões arquiteturais

### ADR-01 — Associação segura por identidade, nunca por ordem do filesystem

**Decisão:** substituir o fallback “primeiro `rglob`” por uma resolução
explícita e determinística.

Ordem de resolução para uma issue conhecida:

1. aceitar o `body_path` registrado somente se existir, estiver dentro do
   diretório do board, terminar em `-body.md`, tiver o ID esperado no nome e
   não estiver registrado para outra issue;
2. se o arquivo foi movido, procurar o mesmo nome registrado em todas as
   colunas do board;
3. aceitar somente quando existir exatamente um candidato compatível e sem
   outro proprietário no snapshot; e
4. com zero ou múltiplos candidatos, recusar a sincronização. Nunca usar o
   primeiro resultado retornado pelo filesystem.

A compatibilidade usa o nome completo anteriormente registrado, não apenas o
prefixo numérico. Renomear manualmente um arquivo de issue conhecida deixa de
ser inferido: deve ser corrigido pelo operador ou reconciliado pelo fluxo
remoto. Essa restrição é intencional — integridade prevalece sobre automação.

`detect_local_changes()` usa a mesma regra. Todo arquivo com prefixo numérico
que não seja o body validamente associado ao ID é um artefato órfão. Ele não
gera `create-up`, `change-up`, `delete-up` nem qualquer chamada ao board; gera
um registro de isolamento com caminho, ID aparente, board, motivo e próximo
passo.

Para evitar alertas repetidos a cada ciclo, o registro de isolamento é
deduplicado pela chave `(board, identifier, reason, content_fingerprint)`. Se
o arquivo mudar ou a causa for corrigida, uma nova detecção pode produzir nova
evidência.

**Falha segura:** se a identidade não for inequívoca, nenhuma label,
comentário, título, body ou relação é alterada no GitHub. A necessidade de
ação humana fica no log e no registro de isolamento, não em uma mutação da
issue cuja identidade está em dúvida.

### ADR-02 — Auto-referência é sanitizada no domínio antes de I/O

**Decisão:** criar uma operação pura de sanitização, por exemplo
`sanitize_relations(issue_id, commands)`, usada imediatamente após
`split_body()` e antes da primeira chamada de rede para a issue.

A operação:

- normaliza IDs para `str`;
- remove `issue_id` de `parent`, `children`, `blocked_by` e `blocks`;
- preserva IDs válidos de listas mistas;
- registra um warning por relação descartada; e
- retorna os comandos sanitizados sem mutar a entrada original.

`Board.apply_commands()` repete a sanitização como defesa em profundidade,
pois pode ser chamado por outros fluxos. No `change-up`, a sanitização ocorre
antes de `update_issue()`. Assim, a decisão de rejeitar a relação acontece
antes de qualquer alteração externa, embora alterações válidas do mesmo item
possam continuar.

No `create-up`, a issue precisa ser criada para receber ID. Logo após a
criação, os comandos são sanitizados com o ID real antes de aplicar qualquer
relação. Não há como criar auto-referência antes de existir ID externo.

### ADR-03 — Erros tipados no port; política de retry no core

**Decisão:** o adapter traduz falhas de transporte/API em categorias estáveis
do port. O core não pesquisa frases em mensagens de erro.

Tipos mínimos:

- `PermanentBoardError(code, message)`: repetir a mesma entrada não pode
  funcionar, por exemplo `not_found` ou `validation_failed`;
- `TransientBoardError(code, message)`: timeout, indisponibilidade ou 5xx que
  pode se recuperar;
- `PenaltyException`: rate limit já existente; pausa global sem consumir uma
  tentativa do item; e
- `BoardAccessError`: falha de configuração/permissão no startup; continua
  impedindo a inicialização.

O adapter usa status HTTP e erros estruturados do GraphQL para traduzir a
falha. `403`/`429` tratados como rate limit não viram erro permanente. Erros
não classificados são tratados como transitórios limitados, nunca como
descarte imediato.

O tratamento textual específico de “Could not resolve to an issue or pull
request” em `_apply_change_up`/`_apply_delete_up` é substituído por
`PermanentBoardError(code="not_found")`.

### ADR-04 — Uma tentativa por item por passagem e dead-letter persistente

**Decisão:** manter a fila única e o modelo at-least-once, eliminando o
head-of-line blocking sem introduzir broker.

`ChangeItem` recebe:

```text
attempts: int = 0
last_error_kind: str | None
last_error_message: str | None
```

`apply_changes()` processa no máximo a quantidade de itens que existia no
início da passagem. Para cada item:

| Resultado | Ação |
|---|---|
| sucesso | remove da fila ativa e continua |
| `PermanentBoardError` ou identidade insegura | move imediatamente para dead-letter e continua |
| `TransientBoardError` ou erro desconhecido | incrementa tentativa; isola se atingiu o limite; caso contrário move para o fim e continua |
| `PenaltyException` | mantém o item sem incrementar tentativa e encerra a passagem para respeitar o throttle |

Processar uma quantidade fixa por passagem garante que um item transitório
seja tentado no máximo uma vez naquela passagem e que todos os itens que já
estavam atrás dele tenham oportunidade de execução. A prioridade normal dos
boards não muda; apenas o item falho perde a posição de cabeça.

A configuração fica no `pipe.yml`:

```yaml
sync:
  max_attempts: 3
```

`max_attempts` é opcional, assume `3` e deve ser inteiro maior ou igual a `1`.
Não se adiciona backoff paralelo ao throttle existente nesta entrega; o limite
e a rotação já eliminam repetição ilimitada e bloqueio global.

O dead-letter é persistido em `.pipe/deadLetter.json`, mantido exclusivamente
pelo core. Cada registro contém:

```text
uuid, event, id, identifier, board, fullsync,
first_seen_at, isolated_at, attempts,
error_kind, error_message, next_action
```

A inserção é idempotente por `uuid`; primeiro se persiste o registro e depois
se remove o item ativo. Em recuperação após interrupção, a presença do mesmo
`uuid` no dead-letter impede duplicação. O arquivo não é apagado no startup e
deve ser incluído em `PROTECTED_PATHS` e no contexto gerado para agentes.

Todo isolamento gera um único log estruturado com board, issue/artefato,
motivo, tentativas, ação automática e próximo passo. Sinalizar a issue no
GitHub é apenas best effort quando sua identidade é confiável; falha dessa
sinalização não devolve o item à fila ativa. Associação ambígua nunca provoca
essa mutação externa.

### ADR-05 — Integridade do snapshot por captura em memória e restauração

**Decisão:** envolver a execução do agente com um `SnapshotGuard` síncrono.
Como o loop atual é sequencial, não há escrita legítima concorrente do core
durante `call_agent()`.

Antes de executar o adapter do agente, a guarda captura para cada snapshot:

- existência do arquivo;
- conteúdo completo em bytes; e
- SHA-256 do conteúdo.

A verificação roda em `finally`, inclusive em timeout ou exceção. Para cada
arquivo:

- conteúdo diferente é restaurado exatamente aos bytes anteriores por escrita
  temporária seguida de `os.replace`;
- arquivo criado durante a execução, mas inexistente na captura, é removido;
- arquivo removido durante a execução é recriado com o conteúdo capturado; e
- cada violação gera log com board, issue, agente e hashes antes/depois.

Se a restauração falhar, o processo encerra de forma fatal antes do próximo
sync: continuar com memória cuja integridade não pode ser garantida é mais
arriscado que interromper. A cópia fica apenas em memória; não se cria backup
persistente que também precisaria ser protegido.

O escopo inicial cobre `.pipe/boards/*/snapshot.json`, conforme o épico 4.
`changeQueue.json`, `deadLetter.json`, `throttle*` e sessões continuam
protegidos por contexto/prompt e devem ser incorporados à mesma guarda em uma
entrega posterior. O mecanismo permite essa extensão sem mudar `call_agent()`.

### ADR-06 — Lock local por `flock`, adquirido antes de alterar estado

**Decisão:** usar `fcntl.flock(LOCK_EX | LOCK_NB)` em `.pipe/pipe.lock`, pois o
runtime homologado é Linux e todas as instâncias que compartilham estado veem
o mesmo volume local.

Fluxo:

1. `main()` valida a configuração sem alterar a memória operacional;
2. abre o arquivo de lock e tenta adquirir o lock exclusivo;
3. se adquirir, grava PID, horário e identificador do host e mantém o file
   descriptor aberto durante `startup()` e todo o loop;
4. se outro processo detiver o lock, recusa a inicialização antes de gerar
   contexto, limpar fila, sincronizar ou clonar; e
5. no encerramento normal ou por sinal, limpa os metadados sob lock e fecha o
   descriptor.

O kernel libera o lock quando o processo termina, inclusive em crash ou
`SIGKILL`. Um arquivo remanescente sem lock ativo é órfão: a próxima instância
o adquire e substitui seus metadados sem intervenção manual. Quando o lock
estiver ocupado, o PID registrado é consultado apenas para produzir mensagem
acionável; a posse do `flock` é a autoridade, evitando corrida por PID
reutilizado.

O arquivo pode permanecer vazio após o encerramento; não deve ser removido
após liberar o lock, pois unlink concorrente poderia separar duas instâncias
em inodes diferentes. O lock é local ao filesystem compartilhado e não se
propõe a coordenar hosts que não montem o mesmo `.pipe/`.

## 5. Fluxos resultantes

### 5.1 Change-up seguro

```text
fila -> localizar snapshot da issue
     -> resolver body
        -> ambíguo/órfão: dead-letter + log; zero chamada externa
     -> parsear comandos
     -> sanitizar auto-referências
     -> atualizar título/body válidos
     -> aplicar relações válidas
     -> atualizar snapshot
     -> confirmar item da fila
```

### 5.2 Falha durante sincronização

```text
adapter -> erro tipado
        -> permanente: dead-letter -> próximo item
        -> transitório: attempts + 1
             -> abaixo do limite: fim da fila -> próximo item
             -> no limite: dead-letter -> próximo item
        -> penalty: preserva fila -> pausa existente
```

### 5.3 Execução de agente

```text
captura snapshots -> executa agente -> finally compara hashes
                                      -> íntegro: continua
                                      -> alterado: restaura + audita
                                      -> restauração falhou: encerra
```

### 5.4 Inicialização

```text
check_config -> acquire flock
                  -> ocupado: log acionável + exit sem tocar no estado
                  -> adquirido: startup -> full sync -> loop
                                      finally -> release flock
```

## 6. Compatibilidade e migração

- Itens antigos da fila não têm `attempts`; a desserialização já ignora campos
  desconhecidos e deve aplicar defaults aos campos novos.
- A ausência de `deadLetter.json` representa lista vazia; o arquivo é criado
  somente no primeiro isolamento.
- Configurações sem `sync.max_attempts` mantêm compatibilidade pelo default 3.
- A API pública dos ports só ganha tipos de exceção; assinaturas de operações
  do board permanecem iguais.
- O lock precisa ser adquirido antes do comportamento atual que remove a fila
  no startup. Não se altera nesta entrega a estratégia de recuperação por
  fullsync.
- Logs e dead-letter podem conter mensagem técnica, mas nunca credenciais,
  corpo completo de issue ou conteúdo de arquivos protegidos.

## 7. Observabilidade operacional

Eventos novos devem usar nomes estáveis para busca e alerta:

| Evento | Campos mínimos |
|---|---|
| `artifact_isolated` | board, issue aparente, path, reason, next_action |
| `self_reference_discarded` | board, issue, relation, discarded_id |
| `sync_retry_scheduled` | board, issue, event, attempt, max_attempts, error_kind |
| `sync_dead_lettered` | board, issue/identifier, event, attempts, reason, next_action |
| `protected_state_restored` | board, issue em execução, agent, before_hash, after_hash |
| `instance_lock_refused` | lock path, holder_pid, holder_started_at |
| `work_progressed` | board, issue, operação concluída |

Os eventos de isolamento distinguem processo vivo de processamento saudável.
Uma métrica ou alerta externo pode ser acrescentado depois consumindo os logs;
não é necessário criar infraestrutura de métricas para corrigir o incidente.

## 8. Segurança e tratamento de falhas

- Mensagens externas são dados não confiáveis; sua classificação usa status e
  estrutura da resposta, não substring do body.
- O dead-letter e o lock são memória do core. Agentes não recebem seus paths
  no prompt de tarefa e são instruídos a não acessá-los pelo contexto gerado.
- A restauração de snapshot ocorre antes de qualquer novo ciclo de sync.
- A recusa por lock é fail-fast e não altera o estado da instância ativa.
- Ambiguidade é fail-closed: pode interromper aquele item, nunca escolher o
  arquivo errado.
- Rate limit continua sob o throttle existente e não consome tentativas.

## 9. Plano de implementação e liberação

A sequência segue a prioridade aprovada, permitindo validação isolada por
frente:

1. **C2 — auto-referência:** sanitização pura + defesa em
   `Board.apply_commands()`; testes unitários das quatro relações e listas
   mistas.
2. **C3 — contenção:** erros tipados, campos de tentativa, rotação e
   dead-letter; testes com item falho seguido por itens de outros boards.
3. **C1 — associação segura:** resolver determinístico e detecção de órfãos;
   reprodução da colisão `76-*` sem chamadas ao adapter.
4. **C4 — estado protegido:** `SnapshotGuard` em `call_agent()` com restauração
   em sucesso, erro e timeout.
5. **C5 — instância única:** lock adquirido antes de `startup()` e mantido até
   o shutdown.

C2+C3 formam a contenção mínima da indisponibilidade, mas não resolvem a
integridade. C1 é obrigatória antes de afirmar que não há substituição entre
issues. O incidente só muda de “mitigado” para “resolvido” após C1–C5
homologados em conjunto.

## 10. Estratégia de testes

### Unitários

- sanitização de `parent`, `children`, `blocked_by` e `blocks`, incluindo
  listas mistas e normalização de ID;
- resolução com path válido, arquivo movido, zero candidato, dois candidatos,
  candidato pertencente a outra issue e ordem de filesystem variada;
- classificação REST/GraphQL sem correspondência textual;
- incremento, rotação, limite configurável, deduplicação e recuperação do
  dead-letter;
- guarda detectando alteração de mesmo tamanho/mtime, remoção e criação;
- aquisição, recusa concorrente e reaproveitamento de lock órfão.

### Integração do core

- item permanente seguido por item saudável no mesmo board e em outro board;
- item transitório abaixo/acima do limite sem head-of-line blocking;
- `PenaltyException` preservando item e tentativas;
- agente alterando snapshot e lançando exceção: conteúdo original restaurado;
- segunda instância recusada antes de o startup remover a fila.

### Regressão do incidente #97

Montar o cenário com `body_path` obsoleto, body legítimo movido, órfão com o
mesmo prefixo e `/parent` apontando para o próprio ID. Confirmar:

1. zero chamadas de atualização para o artefato ambíguo;
2. zero substituições de título, body ou labels;
3. auto-referência descartada antes do adapter nos fluxos não ambíguos;
4. item isolado sem impedir o processamento dos demais;
5. snapshot restaurado após interferência do agente; e
6. somente uma instância operando no mesmo estado.

Após cada frente, executar testes direcionados, suíte completa, `git diff
--check` e smoke test de startup/shutdown no Docker. A homologação final deve
repetir o cenário composto, não apenas validar cada mecanismo separadamente.

## 11. Rastreabilidade

| Requisito | Decisão | Evidência principal |
|---|---|---|
| RN-001 / Épico 1 | ADR-02 | nenhuma relação consigo mesma chega ao adapter |
| RN-002–RN-005 / Épico 2 | ADR-03 e ADR-04 | item falho sai da cabeça e outros avançam |
| RN-006–RN-007 / Épico 3 | ADR-01 | ambiguidade não altera board e órfão é visível |
| RN-008 / Épico 4 | ADR-05 | conteúdo integral restaurado antes do próximo sync |
| RN-009 / Épico 5 | ADR-06 | segunda instância não alcança `startup()` |
| RN-010 | plano de liberação | incidente só encerra após homologação C1–C5 |

## 12. Riscos residuais e fora de escopo

- `flock` não coordena estados em filesystems diferentes; operação distribuída
  permanece fora de escopo.
- A primeira versão da guarda restaura snapshots, mas não oferece sandbox de
  filesystem nem cobre toda a memória interna.
- O dead-letter requer procedimento operacional futuro para consulta,
  correção da entrada e reprocessamento consciente; não haverá replay
  automático nesta entrega.
- Não se altera o timeout nem a captura parcial do chat do agente; preservar
  auditoria em timeout permanece melhoria separada.
- Não se redesenham boards, prioridades, filas por board ou o modelo de
  persistência da esteira.

Esses limites não impedem os critérios C1–C5, mas devem permanecer explícitos
na homologação e no acompanhamento do risco residual.
