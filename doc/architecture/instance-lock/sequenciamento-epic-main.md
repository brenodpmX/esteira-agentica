# Sequenciamento de branches para InstanceLock

- **Status:** aceito, com execução operacional pendente
- **Data:** 2026-08-05
- **Issues:** #104, #142, #150, #151 e #163
- **PRs relacionados:** #122, #161, #162 e #164

## Contexto

A issue #150 implementa `InstanceLock`/`LockHeldError`, e a #151 integra essa
primitiva ao início e ao encerramento de `main()`. Ambas materializam a frente
"instância única" da story #142, que é filha do épico #104. No GitHub, os
vínculos de parent de #150 e #151 ainda estão vazios; isso é uma divergência de
rastreabilidade a corrigir, não uma nova definição de produto.

O fluxo vigente fez #150 e #151 nascerem da branch genérica `epic`. A #150 já
foi incorporada nela pelo PR #161, e o PR #162 de #151 também aponta para ela.
Isso não entrega a capacidade em produção, cuja execução publicada parte de
`main`.

A investigação negocial da #163 confirmou que `epic` não é a branch da issue
#1 "Rodar no Docker". Essa issue possui a branch canônica
`epic1-1-rodar_no_docker`, mergeada em `main` pelo PR #122, e está encerrada no
board. A branch `epic`, por sua vez, recebeu PRs de várias hierarquias e funciona
como tronco de integração compartilhado; portanto, não existe uma única issue
que possa legitimamente fornecer seu número e slug.

Em 2026-08-05, `main` tinha 27 commits exclusivos e `epic`, 121. Uma promoção
direta de `epic` para `main` misturaria dezenas de entregas sem escopo de release
e já apresentou conflitos em arquivos de runtime. Renomear `epic` diretamente
para a branch de uma issue também seria incorreto: atribuiria a uma hierarquia o
histórico de várias outras, quebraria PRs abertos e colidiria com branches
canônicas já existentes.

## Decisão negocial

1. **A hierarquia responsável por InstanceLock é #104 → #142 → #150/#151.**
   As branches canônicas de consolidação são
   `story142-142-garantir_uma_unica_instancia_por_diretorio_de_estado` e
   `epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026`.
2. **A branch genérica `epic` deixa de ser veículo de entrega de
   InstanceLock.** Ela não será renomeada em lugar para #1, #104 ou #142,
   porque não pertence exclusivamente a nenhuma dessas issues.
3. **A retirada/aposentadoria de `epic` será uma migração operacional
   separada.** Antes de remover ou renomear a referência remota, é obrigatório
   migrar PRs abertos, atualizar configurações de flow e comprovar que nenhum
   trabalho depende dela. A ação foi registrada em uma task própria; esta
   definição não autoriza apagar a branch de forma imediata.
4. **A sequência de promoção do InstanceLock será
   #150 → #151 → story #142 → epic #104 → `main`.** A #151 só é considerada
   entregue quando essa cadeia chegar a `main`.
5. **Não haverá merge direto `epic` → `main` nem cherry-pick cego do commit
   atual da #151.** O delta da #151 deve preservar todo o loop vigente,
   especialmente `detect_local_all`, e conter somente a integração do lock.

Essa decisão substitui a proposta anterior de usar uma branch de backport
independente diretamente em `main`: a orientação humana superveniente exige
primeiro restabelecer a correspondência entre hierarquia de issues e branches.
A promoção final continua controlada, mas passa pelas branches canônicas da
story e do épico antes de alcançar produção.

## Sequência obrigatória

1. Corrigir a rastreabilidade de #150/#151 com a story #142. Como o `main`
   ainda não contém a proteção homologada contra propagação de sub-issues entre
   boards, o vínculo deve ser aplicado somente com a esteira parada ou após a
   proteção correspondente estar integrada e validada.
2. Partir da branch canônica da story #142, atualizada a partir de `main`, e
   reaplicar primeiro a unidade lógica da #150 (`bc2e6b6`, depois `ba93fe9`, ou
   patch semanticamente equivalente).
3. Sobre esse resultado, aplicar o delta mínimo da #151. Não fazer cherry-pick
   cego de `46948aa`, pois o commit altera lógica de sincronização fora do
   escopo.
4. Substituir o PR #162 por um PR da correção para a branch da story #142 e
   validar testes unitários de lock, integração com `main()`, startup, SIGTERM e
   suíte completa.
5. Integrar a story #142 na branch canônica do épico #104 somente após revisão
   e homologação da frente de instância única.
6. Promover o épico #104 para `main` em evento de release explícito, com escopo,
   janela, validação e responsável definidos. Esse merge é o gate de entrega da
   #151 em produção.
7. Inventariar e migrar os PRs ainda baseados em `epic`, atualizar o flow da
   esteira e somente então aposentar a branch genérica. Não apagar ou mover a
   referência enquanto houver dependências abertas.

## Regras de integridade

- A aquisição do lock ocorre após validação de configuração e antes de
  `startup()` ou de qualquer operação que altere estado persistido.
- `LockHeldError` causa recusa fail-fast com saída não zero e metadados
  observáveis do detentor; não inicia adapters, sync ou agentes.
- A liberação fica em `finally` externo e cobre término normal, SIGTERM,
  `KeyboardInterrupt`, falhas de startup e exceções do loop.
- A promoção não pode remover ou substituir comportamentos de sincronização,
  proteção de estado, preflight, logging ou shutdown existentes em `main`.
- Diferenças além de `InstanceLock`, sua integração e testes devem ser retiradas
  ou justificadas explicitamente no PR.

## Consequências

### Positivas

- Restabelece a rastreabilidade entre produto, story, tasks e branches.
- Entrega InstanceLock sem transportar os 121 commits exclusivos da branch
  genérica `epic`.
- Evita atribuir o histórico compartilhado de `epic` à issue #1 ou ao épico
  #104.
- Torna explícito o gate real de conclusão da #151.

### Custos e riscos

- A migração exige substituir PRs e ajustar configurações antes de aposentar
  `epic`.
- A reaplicação de #150/#151 precisa de revisão e testes próprios.
- A criação dos vínculos hierárquicos deve respeitar a mitigação do incidente
  de propagação de sub-issues entre boards.

Esses custos são aceitos porque mantêm escopo e responsabilidade claros,
enquanto renomear ou promover `epic` diretamente preservaria a ambiguidade que
originou o débito.

## Supersessão do item 5 (2026-08-19, bug #196)

O item 5 da Decisão negocial ("Não haverá merge direto `epic` → `main`") e,
por consequência, os itens 5 e 6 da Sequência obrigatória (promoção do
InstanceLock apenas via `epic104` em evento de release) estão **superados**
para esta frente. O histórico da decisão é preservado; esta seção registra a
supersessão e sua justificativa.

**Superado por:** débito #165 / PR #180 (que executou a promoção
`epic` → `main` e deixou em `main` o guard `tests/test_epic_merge_ausente_146_147.py`)
e pelo bug #196, cuja correção promove `epic` para `main` por PR revisado.

**Motivos:**

1. **A premissa factual caducou.** O item 5 foi escrito em 2026-08-05, quando
   `main` tinha 27 commits exclusivos, `epic` tinha 121 e havia conflitos em
   arquivos de runtime. Em 2026-08-19, `main` tem **0** commits exclusivos e é
   ancestral estrito de `epic` (16 commits à frente); o merge é fast-forward
   sem nenhum conflito (`git merge-tree --write-tree` retorna árvore idêntica à
   de `epic`, sem conflito). O risco que motivou a proibição não existe mais.
2. **A rota prescrita é inexequível.** A branch canônica
   `epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026` está
   **181 commits atrás** de `main` (6 à frente), e a issue #104 está em
   `aguardando-stories` bloqueada pela própria story #142 — dependência
   circular. Aguardar o evento de release do épico manteria `main` (a branch
   que a esteira executa em produção) sem proteção contra o incidente #97 por
   prazo indeterminado.
3. **Um invariante oposto já vigora em `main`.** O PR #180 deixou em `main` o
   teste `test_nenhum_commit_de_epic_em_src_falta_em_head`, que **exige**
   `epic ⊆ HEAD`. Manter o item 5 significaria manter um guard permanentemente
   vermelho na suíte.

**O que permanece válido:** as *Regras de integridade* deste documento seguem
integralmente em vigor e foram verificadas na correção do #196 — a promoção não
removeu nenhum comportamento de sincronização de `main` (`detect_local_all`,
`AUTO_ADVANCED`, `sync_remote_board`, `process_queue`, `SnapshotIntegrityError`,
`_Shutdown`) e o delta de `src/__main__.py` é exclusivamente a integração do
lock (aquisição antes de `startup()`, recusa fail-fast em `LockHeldError`,
liberação em `finally` externo). A vedação a cherry-pick cego de `46948aa`
também permanece: a correção **não** usa cherry-pick.

**O que continua fora desta supersessão:** os itens 2, 3 e 7 (aposentadoria da
branch genérica `epic`, migração de PRs abertos e ajuste do flow) seguem
pendentes e não são autorizados por esta seção.

Correção factual de rastreabilidade: o commit da integração da #151 é
`570e699`. O SHA `545089a`, citado no change file da story #142, não existe em
`main` nem em `epic`.
