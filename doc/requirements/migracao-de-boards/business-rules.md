# Regras de Negócio — Migração Segura de Colunas de Boards

Status: aprovado
Owner: requirements
Last updated: 2026-08-22

## Inputs
- `/app/.pipe/boards/epic/requisitos/91-migracao_de_boards-body.md`
- `/app/.pipe/boards/epic/requisitos/91-migracao_de_boards-history.md`
- `doc/requirements/migracao-de-boards/glossary.md`
- `src/adapters/github_board.py` (`sync_boards`, `_update_status_options`) —
  confirma o mecanismo de risco: a sincronização atual substitui a lista
  completa de opções do campo `Status` pela nova configuração sem verificar
  se a coluna retirada ainda contém issues.

Este documento refina, para uso de arquitetura/engenharia/QA, as regras já
acordadas com o dono do épico (histórico da issue #91, respostas de
21/08/2026 e 22/08/2026). Não repete a redação de negócio do body; adiciona
contexto de aplicação, exceções e comportamento esperado nas bordas.

## RN-001 — Coluna vazia pode ser retirada diretamente

**Descrição:** se, no momento da avaliação, a coluna a ser retirada não
possui nenhuma issue classificada nela, a retirada pode ser concluída sem
etapa adicional de migração.
**Contexto:** aplica-se à detecção de divergência entre `boards.<board>.columns`
do `pipe.yml` e as opções atuais do campo `Status` no board remoto.
**Exceções:** nenhuma.
**Comportamento na borda:** a contagem de issues na coluna deve refletir o
estado remoto no momento da avaliação, não um estado em cache desatualizado —
uma issue movida para a coluna entre a última sincronização e o momento da
retirada não pode ser ignorada (ver RN-004).
**Rastreamento:** body da issue #91, "se estiver vazia, a retirada poderá
concluir diretamente".

## RN-002 — Coluna ocupada exige destino único e explícito antes da retirada

**Descrição:** se a coluna a ser retirada contém uma ou mais issues, todas
devem ter um único destino válido e explícito, no mesmo board, antes de a
retirada ser concluída.
**Contexto:** aplica-se a toda retirada de coluna ocupada. "Único" significa
que não há roteamento por issue — todas as issues da coluna retirada vão
para o mesmo destino (ver histórico, resposta 3: "Sim para a mesma coluna,
este épico é um remédio, não uma funcionalidade a ser usado como regra de
movimentação de board").
**Exceções:** nenhuma. Não há caso em que uma issue da coluna retirada possa
ter destino diferente das demais, nem caso em que o destino seja
arquivamento ou encerramento (fora de escopo, ver body da issue #91).
**Comportamento na borda:** o destino deve ser uma coluna do mesmo board que
permanece na configuração resultante — uma coluna que também está sendo
retirada na mesma operação não é um destino válido, mesmo que declarada
explicitamente.
**Rastreamento:** body da issue #91, "se contiver issues, todas deverão ter
um único destino válido e explícito no mesmo board"; histórico, respostas 3 e
4.

## RN-003 — Destino ausente ou inválido bloqueia a retirada sem alterar a classificação

**Descrição:** quando uma coluna ocupada é retirada da configuração sem um
destino explícito, ou com um destino que não é válido (não existe, não é do
mesmo board, ou é a própria coluna em retirada), a retirada não deve ser
concluída e a classificação atual das issues não deve ser alterada.
**Contexto:** aplica-se à validação prévia à migração, antes de qualquer
chamada que altere o campo `Status` do board.
**Exceções:** nenhuma.
**Comportamento na borda:** a ausência/invalidez do destino deve impedir
tanto a migração das issues quanto a retirada da opção de `Status` — as duas
operações são condicionadas ao mesmo destino válido; não é aceitável migrar
issues para um destino que depois se mostra inválido, nem retirar a coluna
sem migrar.
**Rastreamento:** body da issue #91, "destino ausente ou inválido deverá
impedir a retirada sem alterar a classificação existente"; histórico,
resposta 6.

## RN-004 — A coluna de origem permanece ativa enquanto houver qualquer issue nela

**Descrição:** a opção de `Status` correspondente à coluna retirada não pode
ser removida do board enquanto existir, naquele board, qualquer issue ainda
classificada nela — inclusive issues que chegaram à coluna depois do início
da tentativa de migração.
**Contexto:** aplica-se durante toda a execução da migração, do início da
tentativa até a confirmação de que a coluna está vazia imediatamente antes da
retirada.
**Exceções:** nenhuma.
**Comportamento na borda:** se uma nova issue for classificada na coluna de
origem durante a migração (ex.: por uma sincronização concorrente ou por
ação manual no board), a retirada não pode se concluir até que essa issue
também seja migrada ou saia da coluna — a verificação de "coluna vazia" deve
ser feita novamente antes da retirada efetiva, não apenas no início da
tentativa.
**Rastreamento:** body da issue #91, "a coluna de origem deverá permanecer
ativa enquanto houver qualquer issue nela"; histórico, resposta 6 ("O sistema
deve manter a coluna ativa enquanto houver issues nela, quando estiver vazia
ai sim a exclusão ocorre").

## RN-005 — Interrupção ou falha preserva a origem e permite nova tentativa

**Descrição:** se a migração for interrompida ou falhar antes de concluir
(qualquer issue ainda na origem), a coluna de origem permanece ativa e uma
nova tentativa deve ser possível sem exigir intervenção manual prévia.
**Contexto:** aplica-se a falhas de qualquer natureza durante a execução da
migração (indisponibilidade do provedor, interrupção do processo, rate
limit) — a esteira pode operar sem supervisão em container (histórico,
resposta 10), portanto a recuperação não pode depender de um humano
observar o erro em tempo real.
**Exceções:** nenhuma.
**Comportamento na borda:** uma nova tentativa sobre uma migração
parcialmente concluída deve reconhecer os itens já movidos e não reprocessar
o que já está correto (ver RN-006) — repetir a tentativa não é recomeçar do
zero, é retomar do estado atual.
**Rastreamento:** body da issue #91, "interrupções ou falhas deverão manter
a origem ativa e permitir nova tentativa segura".

## RN-006 — Repetição da migração não perde nem duplica issues

**Descrição:** executar a migração mais de uma vez para a mesma retirada de
coluna (por nova tentativa após falha, ou por reprocessamento da mesma
operação) não pode resultar em uma issue perdida (sem coluna) nem em efeito
duplicado (ex.: dupla contagem, dupla notificação, issue processada duas
vezes de forma que gere inconsistência).
**Contexto:** aplica-se a qualquer reexecução da mesma operação de retirada,
inclusive quando a fila de sincronização da esteira é *at-least-once* (ver
README, seção "change_queue.py").
**Exceções:** nenhuma.
**Comportamento na borda:** uma issue já movida para o destino, ao ser
avaliada novamente por uma tentativa repetida, deve ser reconhecida como já
migrada e não gerar erro nem nova movimentação.
**Rastreamento:** body da issue #91, "repetição não poderá perder nem
duplicar issues"; critérios de sucesso, "zero perda ou duplicação".

## RN-007 — Identidade e atributos da issue são preservados na migração

**Descrição:** a migração altera exclusivamente a classificação de coluna
(`Status`) da issue; id, conteúdo (título, body), relações (`parent`,
`children`, `blocked_by`, `blocks`) e demais atributos (labels, estado
aberto/fechado) não podem ser alterados pela migração.
**Contexto:** aplica-se a toda issue movida da coluna retirada para o
destino.
**Exceções:** nenhuma. Eventos de coluna (`on_in`/`on_out`) configurados para
a coluna de destino continuam se aplicando normalmente pelas regras já
existentes de mudança de coluna (fora do escopo deste épico alterar esse
comportamento) — a migração não deve ser tratada como uma via especial que
ignora `on_in`/`on_out` nem como uma que os suprime; a decisão sobre se
esses eventos disparam é definida pelas regras já vigentes de mudança de
coluna, não recriada aqui.
**Comportamento na borda:** nenhuma.
**Rastreamento:** body da issue #91, "IDs, conteúdo, relações e demais
atributos deverão ser preservados".

## RN-008 — Toda tentativa produz evidência verificável

**Descrição:** cada tentativa de migração deve permitir verificar, no
mínimo: contagem inicial de issues na coluna de origem, itens efetivamente
movidos, itens restantes na origem e o resultado final da retirada
(concluída, bloqueada ou interrompida).
**Contexto:** aplica-se a toda tentativa, com sucesso ou não, incluindo
tentativas bloqueadas por destino ausente/inválido (RN-003).
**Exceções:** nenhuma.
**Comportamento na borda:** a evidência deve ser acessível sem exigir
leitura dos arquivos internos protegidos da esteira (`snapshot.json`,
`changeQueue.json`) — consistente com a proteção de estado interno já
descrita no `README.md`.
**Rastreamento:** body da issue #91, "cada tentativa deverá permitir
verificar contagem inicial, itens movidos, itens restantes e resultado da
retirada"; critérios de sucesso, "100% dos eventos com contagens e resultado
verificáveis".

## RN-009 — Este épico é uma proteção estrutural, não uma regra geral de movimentação

**Descrição:** o mecanismo entregue por este épico só se aplica ao contexto
de retirada de coluna da configuração (mudança estrutural). Ele não
substitui, generaliza ou é reaproveitado como regra de movimentação de
issues fora desse contexto (ex.: `keep_task`, `on_in`/`on_out`, avanço manual
no board).
**Contexto:** aplica-se à interpretação do escopo por arquitetura e
engenharia ao desenhar a solução — evita que a proteção seja generalizada
para além do gatilho de retirada de coluna.
**Exceções:** nenhuma.
**Comportamento na borda:** nenhuma.
**Rastreamento:** body da issue #91, "Este épico é uma proteção para mudança
estrutural, não uma regra geral de movimentação de trabalho"; histórico,
resposta 3.

## RN-010 — Escopo restrito a um único board por operação

**Descrição:** a migração trata da retirada de uma coluna dentro de um único
board; migração de issues entre boards diferentes não faz parte deste
mecanismo.
**Contexto:** aplica-se à validação do destino (RN-002, RN-003) — um destino
em outro board é, por definição, inválido para este mecanismo.
**Exceções:** nenhuma.
**Comportamento na borda:** nenhuma.
**Rastreamento:** body da issue #91, seção "Escopo" ("Não inclui: migração
entre boards"); histórico, resposta 4.
