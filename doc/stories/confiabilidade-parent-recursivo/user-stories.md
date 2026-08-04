# User Stories — Confiabilidade após o incidente Parent Recursivo

Status: prontas para planejamento técnico
Owner: product (Helena Costa — Product Manager)
Last updated: 2026-08-04
Épico de origem: #104 "Post-Mortem de Produto — Incidente reportado em 01/08/2026" (board `epic`)

## Inputs aprovados

- `doc/product/confiabilidade-parent-recursivo/problem-space.md`
- `doc/product/confiabilidade-parent-recursivo/vision.md`
- `doc/product/confiabilidade-parent-recursivo/post-mortem.md`
- `doc/product/confiabilidade-parent-recursivo/epicos.md`
- `doc/requirements/confiabilidade-parent-recursivo/business-rules.md`
- `doc/requirements/confiabilidade-parent-recursivo/non-functional-requirements.md`
- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md`
- `doc/incidente/parent-recursivo/ticket.md`

## Objetivo da decomposição

Transformar as cinco frentes aprovadas do épico #104 em fatias de valor
independentes, testáveis e rastreáveis. Cada story reduz um risco específico do
incidente #97 sem ampliar o escopo aprovado nem prescrever uma implementação
além das decisões arquiteturais já validadas.

As tasks técnicas C1–C5 já existem no board `task`, derivadas do incidente #97.
Elas são referências de execução das stories abaixo e **não devem ser criadas
novamente** no planejamento técnico. Quando as stories receberem IDs, o
planejamento deve reconciliar a rastreabilidade das tasks existentes sem gerar
duplicatas.

## Mapa das stories

| Story | Resultado de valor | Regras | Arquitetura | Task existente | Nível |
|---|---|---|---|---|---|
| US-01 | Relações consigo mesma são recusadas antes do board | RN-001, RN-005 | ADR-02 | C2 | medium |
| US-02 | Falhas definitivas ou recorrentes deixam de bloquear a fila global | RN-002–RN-005 | ADR-03, ADR-04 | C3 | high |
| US-03 | Artefatos ambíguos ou órfãos não alteram issues | RN-005–RN-007 | ADR-01 | C1 | high |
| US-04 | Interferência do agente no snapshot é revertida e auditada | RN-005, RN-008 | ADR-05 | C4 | high |
| US-05 | Uma segunda instância é recusada antes de tocar o estado | RN-009 | ADR-06 | C5 | medium |

RN-010 é transversal: nenhuma entrega isolada permite declarar o incidente
resolvido. O encerramento depende da homologação conjunta das cinco stories.

## Ordem recomendada

`US-01 (C2) → US-02 (C3) → US-03 (C1) → US-04 (C4) + US-05 (C5)`.

US-01 e US-02 entregam a contenção mínima da indisponibilidade. US-03 elimina o
risco de uma associação insegura alterar a issue errada. US-04 e US-05 fecham
frentes independentes de proteção do estado e exclusividade de execução. Como
as stories ainda não possuem IDs, as dependências ficam documentadas aqui; os
vínculos no board devem ser reconciliados após o primeiro sincronismo.

---

## US-01 — Impedir relações de uma issue consigo mesma

**Como** operador da esteira,
**quero** que relações de hierarquia e bloqueio autorreferentes sejam recusadas
antes de qualquer chamada ao board,
**para** impedir uma operação logicamente impossível sem interromper relações
válidas nem o restante do processamento.

### Contexto e valor

No incidente #97, a esteira tentou aplicar `set_parent(76, 76)`. A API recusou
a operação, mas a ausência de validação permitiu que o erro alcançasse a borda
externa. Esta story cria a primeira barreira de proteção e reduz imediatamente
o risco de paralisação por dados inválidos previsíveis.

### Critérios de aceitação

- **Dada** uma issue que se referencia em `parent`, `children`, `blocked_by` ou
  `blocks`, **quando** seus comandos forem processados, **então** cada
  autorreferência é descartada antes da primeira chamada ao board.
- **Dada** uma lista que mistura o próprio ID e IDs válidos, **quando** ela for
  validada, **então** somente o próprio ID é descartado e as relações válidas
  continuam sendo processadas.
- A validação cobre as quatro relações, inclusive quando mais de uma aparece no
  mesmo body, sem exceções.
- Cada descarte registra board, issue, relação e ID descartado, com motivo
  compreensível ao operador e sem exigir leitura de estado interno.
- Os testes comprovam que nenhuma chamada de relação autorreferente alcança o
  adapter e que a entrada original não é alterada pela validação.

### Fora de escopo

Classificação de erros que já chegaram à API, política de tentativas,
dead-letter e resolução da identidade de arquivos.

### Rastreabilidade

- Épico aprovado: frente 1 — validação de relações antes do board.
- Regras: RN-001 e RN-005.
- Arquitetura: ADR-02.
- Task técnica existente: C2 — `validar_auto_referencia_em_relacoes_parentchildrenblocked_byblocks-body.md`.

---

## US-02 — Isolar falhas sem bloquear os demais trabalhos

**Como** operador da esteira,
**quero** que falhas definitivas ou repetidamente transitórias sejam retiradas
do fluxo ativo com evidência e próximo passo,
**para** que um item inválido não monopolize a fila nem paralise outros boards.

### Contexto e valor

A mesma rejeição foi repetida 225 vezes durante aproximadamente 2h37 e impediu
o processamento útil de todos os boards. Esta story elimina o head-of-line
blocking e torna a recuperação limitada, explícita e orientada.

### Critérios de aceitação

- Erros do board são classificados por categoria estável: um erro definitivo é
  isolado no mesmo ciclo, enquanto um erro transitório segue a política de
  tentativas; rate limit preserva o tratamento global existente sem consumir
  tentativa do item.
- O limite de tentativas é configurável, assume valor seguro quando omitido e
  aceita somente inteiro maior ou igual a 1.
- Cada item é tentado no máximo uma vez por passagem; uma falha abaixo do limite
  move o item para o fim da fila e permite que os demais avancem na ordem de
  prioridade já definida.
- Ao atingir o limite, o item sai da fila ativa e é persistido uma única vez em
  dead-letter, inclusive após reinício ou interrupção entre persistir e remover.
- Todo isolamento registra item, board, evento, motivo, número de tentativas,
  ação automática e próximo passo acionável, sem expor credenciais, body
  completo ou conteúdo de arquivos internos.
- Um item permanente ou transitório seguido por itens saudáveis do mesmo board
  e de outros boards não impede que 100% dos itens elegíveis não afetados sejam
  processados na mesma passagem.
- O cenário de 225 repetições não volta a ocorrer: erros definitivos não são
  retentados e os demais nunca excedem o limite configurado.

### Fora de escopo

Corrigir a origem do artefato ambíguo, criar broker ou filas por board, replay
automático de dead-letter e alterar a política de rate limit.

### Rastreabilidade

- Épico aprovado: frente 2 — contenção de falhas definitivas e repetição.
- Regras: RN-002, RN-003, RN-004 e RN-005.
- Arquitetura: ADR-03 e ADR-04.
- Task técnica existente: C3 — `erro_definitivo_nao_reenfileira_contador_de_tentativas_e_dead_letter_na_fila-body.md`.

---

## US-03 — Associar artefatos a issues somente com identidade inequívoca

**Como** operador da esteira,
**quero** que um arquivo de body seja associado a uma issue somente quando sua
identidade for inequívoca,
**para** impedir que conteúdo, título, labels ou relações de um artefato órfão
sejam aplicados à issue errada.

### Contexto e valor

O fallback por prefixo numérico escolheu um arquivo indevido e substituiu o
conteúdo da issue #76. Integridade prevalece sobre automação: na dúvida, o item
é isolado e nenhuma alteração externa é realizada.

### Critérios de aceitação

- Um caminho registrado só é aceito quando existe, pertence ao diretório do
  board, segue o padrão esperado, contém o ID correto e não pertence a outra
  issue.
- Quando o arquivo foi movido, a busca considera o nome completo registrado e
  só aceita exatamente um candidato compatível; zero ou múltiplos candidatos
  resultam em recusa segura, independentemente da ordem do filesystem.
- Um arquivo com prefixo numérico sem correspondência confiável é tratado como
  órfão: não cria nem altera issue, não gera operação destrutiva e não é
  ignorado silenciosamente.
- Ambiguidade ou orfandade gera evidência visível com board, ID aparente,
  caminho, motivo e próximo passo, deduplicada enquanto causa e conteúdo não
  mudarem.
- A reprodução da colisão `76-*` resulta em zero chamadas de atualização ao
  board e zero substituições de título, body, labels ou relações.
- Arquivos novos sem prefixo numérico continuam seguindo o fluxo normal de
  criação de issue.

### Fora de escopo

Reparar novamente os dados do incidente já recuperado, inferir renomeações
manuais por heurística ou alterar automaticamente uma issue cuja identidade
esteja em dúvida.

### Rastreabilidade

- Épico aprovado: frente 3 — associação segura entre artefato e issue.
- Regras: RN-005, RN-006 e RN-007.
- Arquitetura: ADR-01.
- Task técnica existente: C1 — `fallback_seguro_na_resolucao_do_body_da_issue_e_reporte_de_arquivos_orfaos-body.md`.

---

## US-04 — Restaurar alterações indevidas no snapshot após execução do agente

**Como** operador da esteira,
**quero** que a integridade dos snapshots seja verificada ao redor de cada
execução de agente e restaurada quando houver interferência,
**para** que somente o núcleo mantenha a memória operacional persistente.

### Contexto e valor

As instruções atuais protegem o estado de forma declarativa, mas não garantem
recuperação caso um agente altere, remova ou crie um snapshot. Esta story
adiciona detecção, reversão integral e auditoria antes do próximo sync.

### Critérios de aceitação

- Antes da execução do agente, a esteira captura em memória a existência, os
  bytes completos e o hash de cada snapshot no escopo aprovado.
- A verificação ocorre em `finally`, cobrindo sucesso, erro e timeout do agente.
- Alteração de conteúdo — inclusive com mesmo tamanho ou timestamp —, remoção
  ou criação indevida é detectada e revertida exatamente ao estado anterior por
  operação atômica antes do próximo ciclo de sync.
- Cada reversão registra board, issue em execução, agente e hashes anterior e
  posterior, sem registrar o conteúdo protegido.
- Se a restauração falhar, o processo encerra antes de novo sync com mensagem
  fatal e acionável, em vez de continuar sobre estado cuja integridade não pode
  ser garantida.
- A verificação mantém overhead da ordem de milissegundos para snapshots
  típicos e não interfere em escritas legítimas do núcleo fora da execução do
  agente.

### Fora de escopo

Sandbox de filesystem e extensão da guarda para toda a memória interna; nesta
entrega, o escopo funcional é o snapshot por board aprovado em C4.

### Rastreabilidade

- Épico aprovado: frente 4 — proteção da memória operacional.
- Regras: RN-005 e RN-008.
- Arquitetura: ADR-05.
- Task técnica existente: C4 — `verificacao_de_integridade_do_snapshot_na_execucao_do_agente-body.md`.

---

## US-05 — Garantir uma única instância por diretório de estado

**Como** operador da esteira,
**quero** que somente uma instância opere sobre o mesmo diretório de estado,
**para** evitar concorrência, perda de fila e corrupção da memória operacional.

### Contexto e valor

Uma segunda instância pode alterar o estado antes que a primeira conclua seu
trabalho. A exclusividade deve ser garantida antes de qualquer efeito do
startup, mas sem impedir uma reinicialização legítima após encerramento ou
crash.

### Critérios de aceitação

- A instância adquire exclusividade local antes de qualquer alteração do estado
  persistido e mantém o lock durante startup, loop e encerramento.
- **Dada** uma instância ativa no mesmo estado, **quando** outra tenta iniciar,
  **então** a segunda encerra sem executar startup nem alterar o estado da
  primeira.
- A recusa informa caminho do lock e dados disponíveis do detentor, com
  orientação clara, sem depender de edição manual de arquivos internos.
- Encerramento normal, sinal ou crash libera a posse pelo mecanismo do sistema
  operacional; um arquivo remanescente sem lock ativo permite nova
  inicialização e tem seus metadados substituídos com segurança.
- A verificação é O(1), não depende de varrer o diretório de estado e não aceita
  PID vivo como autoridade maior que a posse efetiva do lock.
- Testes concorrentes comprovam no máximo uma instância ativa por estado e
  reinicialização legítima sem intervenção manual.

### Fora de escopo

Lock distribuído entre hosts que não compartilham o mesmo filesystem e
coordenação entre diretórios de estado distintos.

### Rastreabilidade

- Épico aprovado: frente 5 — exclusividade de instância.
- Regra: RN-009.
- Arquitetura: ADR-06.
- Task técnica existente: C5 — `lock_de_instancia_unica_da_esteira-body.md`.

---

## Critério de encerramento do épico

O incidente permanece **mitigado, com risco residual** durante entregas
parciais. O épico #104 só pode ser considerado resolvido quando:

1. US-01 a US-05 estiverem implementadas e homologadas;
2. a regressão composta do incidente #97 confirmar zero substituições de
   conteúdo, zero autorreferências no adapter, ausência de bloqueio global,
   restauração do estado protegido e instância única; e
3. os logs permitirem identificar item, board, motivo, ação automática e
   próximo passo sem acesso à memória interna.
