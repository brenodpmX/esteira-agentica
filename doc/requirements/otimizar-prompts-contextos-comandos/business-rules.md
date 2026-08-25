# Regras de Negócio — Otimizar prompts, contextos e comandos

Status: approved · Owner: requirements · Updated: 2026-08-25
Inputs: `doc/product/otimizar-prompts-contextos-comandos/analise-negocio.md`;
`src/core/agent.py`, `src/core/commands.py`, `src/core/context_generator.py`,
`src/core/config.py`; histórico da issue #92 (respostas do dono em
22 e 25/08/2026).

> Estas regras não redefinem o que a esteira já garante — extraem, do
> comportamento atual e da decisão de negócio aprovada, o que **não pode
> regredir** quando o prompt/contexto for recomposto. Servem de contrato para
> arquitetura e QA validarem qualquer implementação da simplificação.

## RN-001 — Redução de conteúdo estático não remove guardrail

**Regra:** nenhuma instrução de segurança ou política invariável (proteção de
`PROTECTED_PATHS`, confinamento ao workdir, regras de Git seguras) pode ser
omitida, adiada ou tornada "sob demanda" como efeito colateral da redução de
palavras.
**Contexto:** aplica-se a qualquer redistribuição de conteúdo entre prompt
dinâmico, contexto persistente e referências sob demanda.
**Exceções:** nenhuma. Reduzir palavras de uma instrução de segurança (torná-la
mais concisa) é permitido; removê-la ou transformá-la em referência opcional
não é.
**Fonte:** análise de negócio, "Critério para aprovação ou recusa futura":
"Recusar ou devolver (...) se houver perda de guardrail".

## RN-002 — Mover texto para uma camada sempre carregada não conta como redução

**Regra:** conteúdo que hoje está no prompt dinâmico e é apenas realocado para
o contexto persistente (ou vice-versa), sem eliminação real de palavras
sempre entregues ao agente, não conta para as metas de redução dos gates 1 e
2.
**Contexto:** aplica-se à métrica de "total sempre carregado" (prompt +
contexto persistente) usada para validar a entrega.
**Exceções:** nenhuma.
**Fonte:** análise de negócio, seção "Evidência do produto atual": "Apenas
mover texto do prompt para um contexto sempre incluído esconderia a
verbosidade, mas não reduziria consumo de contexto." e "Critério para
aprovação ou recusa futura".

## RN-003 — Conteúdo do operador é responsabilidade do operador

**Regra:** a esteira não define, sugere conteúdo-padrão para, nem impõe
estrutura obrigatória a `contexts/<plataforma>/<agente>.md`. O épico pode
inspecionar esses arquivos como entrada de análise, mas não pode adicionar
regras que alterem seu conteúdo esperado.
**Contexto:** aplica-se a qualquer requisito funcional que toque contexto do
operador.
**Exceções:** a validação de existência/não-vazio já feita por
`_validate_agents()` (`src/core/config.py`) é comportamento preexistente e
não é alterada por este épico, salvo se ligada diretamente ao contrato de
composição (ver RN-006).
**Fonte:** análise de negócio, "Fora de escopo": "definir o conteúdo dos
contextos mantidos pelo operador"; resposta do dono, item 6 (22/08/2026).

## RN-004 — Toda instrução obrigatória precisa de prova de carregamento verificável

**Regra:** para cada instrução classificada como obrigatória (ver glossário),
deve existir uma verificação determinística, executável antes ou
imediatamente após o disparo do adapter, de que essa instrução foi composta e
entregue — não apenas que um arquivo-fonte existe em disco sem relação
comprovada com o que foi de fato passado ao processo do adapter.
**Contexto:** aplica-se ao adapter Kiro atual (`KiroCliAgent`). A prova é de
**carregamento pelo adapter**, não de obediência pelo modelo — este épico não
mede comportamento do modelo.
**Exceções:** nenhuma para o adapter Kiro. Adapters futuros (fora de escopo)
não precisam desta prova nesta entrega.
**Fonte:** análise de negócio, gate de sucesso 4; resposta do dono ao ponto 2
não fechou o mecanismo exato — RN detalha o que é aceitável como prova, mas o
mecanismo concreto é decisão de arquitetura.

## RN-005 — Duplicidade de regra entre camadas sempre carregadas é defeito

**Regra:** se a mesma regra (mesmo guardrail, mesma restrição) aparecer, em
texto equivalente, tanto no prompt dinâmico quanto no contexto persistente
(ambos sempre carregados), isso é uma duplicidade a eliminar — a regra deve
existir em exatamente uma camada sempre carregada.
**Contexto:** aplica-se ao inventário de instruções (RF-001) e à composição
final.
**Exceções:** uma regra pode aparecer resumida em uma camada e detalhada em
uma referência sob demanda (isso não é duplicidade sempre carregada).
**Fonte:** análise de negócio, gate de sucesso 3 e escopo aprovado "remover
duplicidade entre prompt, contexto gerado e contexto do operador".

## RN-006 — Configuração de `pipe.yml` só muda se ligada à composição de instruções

**Regra:** qualquer novo campo ou alteração de campo existente em `pipe.yml`
proposto por este épico deve ter relação direta e explícita com pelo menos um
de: objetivo da etapa, workflow (transições/eventos), branch/flow,
repositório/workdir, ou composição de instruções (o que entra no prompt vs.
contexto vs. referência sob demanda).
**Contexto:** aplica-se a toda proposta de mudança de configuração derivada
deste épico.
**Exceções:** correções de validação já existentes e não relacionadas à
composição (ex.: `boards.rerun_cooldown`, `sync.max_attempts`) não são objeto
deste épico e não devem ser tocadas.
**Fonte:** análise de negócio, escopo aprovado: "revisar apenas as opções de
`pipe.yml` que influenciam diretamente objetivo da etapa, workflow, branch,
repositório/workdir e composição de instruções."

## RN-007 — Mensagem de commit/PR reflete o trabalho real, sem template fixo obrigatório

**Regra:** a mensagem de commit e o título/corpo do PR deixam de ser um
literal fixo montado pela esteira (`f'{coluna}: {título}'` e
`"merge: {branch} -> {base}"` / `"Automated PR from agent"`) e passam a ser
compostos pelo agente a partir do que foi efetivamente realizado na execução.
**Contexto:** aplica-se apenas à composição de conteúdo da mensagem; não
altera a obrigação de commitar/dar push/abrir PR quando `gitevents` exigir
(essa obrigação continua sendo garantia de workflow, fora desta regra).
**Exceções/pendência:** os limites aceitáveis de liberdade do agente ao
compor a mensagem — em especial, se o agente pode decidir não commitar ou
pular a etapa quando julgar não haver mudança relevante — **ainda não foram
definidos pelo dono do produto** (ver observação de bloqueio no
`functional-requirements.md`, RF-007). Esta regra vale apenas para "conteúdo
da mensagem", não para "se commitar".
**Fonte:** análise de negócio, escopo aprovado: "garantir que mensagens de
commit e PR reflitam a mudança realizada, sem obrigar copy mecânico quando o
agente dispõe do resultado real"; resposta do dono, item 4 (25/08/2026), que
devolveu a pergunta sobre limites sem fechá-los.

## RN-008 — Meta de redução é medida sobre matriz fixa de cenários, não sobre um caso isolado

**Regra:** os gates de redução de 40% (prompt) e 20% (total sempre carregado)
são calculados sobre a mesma matriz fixa de cenários antes/depois (ver
RF-006), nunca sobre um único cenário escolhido ad hoc que favoreça o
resultado.
**Contexto:** aplica-se ao benchmark exigido pelo escopo aprovado
("fornecer benchmark antes/depois").
**Exceções:** nenhuma.
**Fonte:** análise de negócio, gates de sucesso 1–2 e nota sobre a matriz
fixa; ponto 3 da rodada de dúvidas de 23/08/2026, resolvido nesta entrega (ver
RF-006) por não ter sido uma decisão de negócio pendente, e sim de
especificação de teste dentro do escopo já aprovado.

## RN-009 — Nenhuma redução pode depender de suposição sobre custo/erro não comprovado

**Regra:** nenhum requisito funcional ou critério de aceitação deste épico
pode ser justificado citando taxa de erro, "delírio" ou custo financeiro como
fato — apenas como hipótese já registrada e não validada pela análise de
negócio.
**Contexto:** aplica-se à redação de toda justificativa de requisito.
**Exceções:** métricas de acompanhamento (não bloqueantes) podem coletar
esses dados para validação futura, mas não podem ser citadas como fato já
comprovado.
**Fonte:** análise de negócio, seção "Entrevista com o dono e tratamento das
hipóteses": "Hipótese ainda não provada: mais palavras causam mais erros ou
delírios."
