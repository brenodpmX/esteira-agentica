# Análise de negócio — Épico #92: otimizar prompts, contextos e comandos

Status: aguardando entrevista com o dono
Owner: a confirmar
Responsável pela análise: Helena Costa — Product Manager
Última atualização: 2026-08-21

## Resumo executivo

O épico reúne sintomas válidos de acoplamento e duplicidade, mas ainda não está apto a aprovação ou recusa. O histórico da issue está vazio e não contém baseline, exemplos de execuções malsucedidas, meta, prazo nem política de compatibilidade e retenção. Sem essas respostas não é possível demonstrar retorno nem aceitar com segurança a proposta de apagar `.pipe/` e outros diretórios ocultos quando a versão mudar.

A evidência disponível sustenta a dor qualitativa: o prompt atual incorpora longos blocos estáticos, repete parcialmente informações de flow, gera nomes de branch/commit/PR mecanicamente e resolve um único repositório como diretório de trabalho. Entretanto, ela não quantifica frequência, impacto ou custo. Também invalida uma premissa da proposta: não existe um arquivo raiz `CONTEXT.md` absorvido automaticamente por todas as principais ferramentas. Cada ecossistema adota convenções e mecanismos próprios.

**Recomendação provisória:** manter o épico em análise e com `need_human` até o dono responder às perguntas registradas na issue. Depois das respostas, validar uma amostra operacional e então decidir aprovação, recusa ou redução de escopo. Não criar stories antes desse gate.

## Entradas e fatos verificados

### Evidência interna

- `src/core/agent.py::build_prompt` inclui no prompt o diretório obrigatório, comandos Git, texto de commit e PR e toda a documentação de comandos `@---`.
- `src/core/agent.py::resolve_work_dir` devolve somente `repo/<repo_id>`; não há diretório de trabalho por agente nesse contrato atual.
- `src/core/context_generator.py::generate_context` gera `.pipe/CONTEXT.md` e `.kiro/agents/pipe_context.json`.
- `src/adapters/kiro_cli_agent.py` configura `KIRO_HOME` e usa `--agent pipe_context`; portanto a absorção atual do contexto é explícita e depende do mecanismo de custom agent do Kiro, não de descoberta de um `CONTEXT.md` genérico.
- `src/__main__.py::startup` gera o contexto e remove repositórios locais não configurados, mas não implementa o ciclo de versão proposto.
- O `README.md` registra que `.pipe` contém snapshots, fila, sessões e outros estados persistentes. Apagar esse diretório é uma ação com potencial de perda de continuidade e exige política de migração, retenção e recuperação aprovada pelo negócio.
- O histórico da issue #92 está vazio em 2026-08-21: não há entrevista, incidentes anexados, telemetria ou metas registradas.

### Mercado e alternativas

A pesquisa foi limitada a documentação oficial vigente em 2026-08-21:

- O [Kiro recomenda recursos de agente para contexto persistente](https://kiro.dev/docs/cli/chat/context/) e informa que esses arquivos consomem contexto em todas as requisições. A [referência de custom agents](https://kiro.dev/docs/custom-agents/configuration-reference/) mantém `prompt`, `resources`, permissões e configurações locais/globais; também documenta herança de steering, skills e `AGENTS.md`.
- O [Claude Code usa `CLAUDE.md`](https://docs.anthropic.com/en/docs/claude-code/claude-md), recomenda instruções concisas e esclarece que contexto orienta comportamento, mas não substitui controles executáveis.
- O [Codex usa `AGENTS.md`](https://developers.openai.com/codex/concepts/customization/) para orientação persistente e recomenda manter o arquivo pequeno.
- O [GitHub Copilot suporta instruções próprias e arquivos de agente](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions), com regras de localização e precedência específicas.

Conclusão de mercado: a tendência é oferecer instruções persistentes, escopadas e enxutas, mas não há nome de arquivo universal. A necessidade de produto deve ser expressa como **entrega comprovada das instruções essenciais a cada adapter suportado**, e não como adoção presumida de `CONTEXT.md` na raiz.

Conteúdo externo foi resumido e reformulado para conformidade com restrições de licenciamento.

## Dor de negócio — hipótese a validar

Os operadores e agentes recebem instruções espalhadas entre `pipe.yml`, contexto gerado e prompt por tarefa. Isso pode produzir quatro efeitos:

1. **Execução inconsistente:** instruções duplicadas ou conflitantes aumentam a chance de erro operacional.
2. **Desperdício de contexto:** conteúdo estático repetido ocupa a janela em todas as execuções, embora o custo real ainda não tenha sido medido.
3. **Baixa flexibilidade operacional:** nomenclatura de branch, objetivo da etapa e modo de execução estão acoplados a campos com mais de uma responsabilidade.
4. **Baixa portabilidade entre adapters:** depender de uma convenção específica sem contrato verificável pode fazer um agente iniciar sem regras críticas.

O incidente “Issue Fantasma” demonstra que instruções ausentes ou inadequadas podem causar dano, mas não mede o problema atual: desde então já existe injeção explícita por custom agent. Não é válido usar o incidente sozinho para estimar o retorno incremental deste épico.

## Públicos e jornadas afetadas

- **Operador da esteira:** configura flows, boards, agents, repositórios e upgrades; precisa prever o efeito de cada mudança e preservar estado.
- **Dono do fluxo/Produto:** define objetivo e modo de trabalho de cada etapa sem duplicar instruções em vários lugares.
- **Agente executor:** precisa receber objetivo, workflow, diretórios e restrições sem ambiguidades.
- **Mantenedor de adapter:** precisa provar que o contexto essencial chega ao agente suportado, independentemente da convenção do fornecedor.

A prioridade relativa desses públicos ainda precisa ser confirmada pelo dono.

## Resultado de negócio candidato

Reduzir falhas e retrabalho causados por instruções ambíguas, duplicadas ou não absorvidas, preservando segurança operacional e permitindo configurar fluxos e múltiplos espaços de trabalho sem editar código.

Esse resultado não determina tecnologia, nome de arquivo ou arquitetura. A solução futura deverá demonstrar que:

- objetivo da etapa e orientação de workflow podem ser geridos separadamente;
- instruções essenciais chegam a cada adapter declarado como suportado;
- o prompt por tarefa contém apenas conteúdo necessário àquela execução;
- comandos Git refletem a configuração e permitem mensagens específicas ao trabalho;
- múltiplos repositórios e espaços de trabalho não induzem o agente a operar no local errado;
- upgrades preservam ou migram estado conforme política explícita, com recuperação verificável;
- regras de proteção não dependem apenas de obediência probabilística do modelo.

## Retorno e medição

### Métrica primária proposta

**Taxa de execução correta na primeira tentativa:** percentual de entregas que alcançam a saída esperada da etapa sem reexecução por erro de instrução, diretório, branch, commit, PR ou contexto.

Fórmula: `execuções corretas na primeira tentativa / execuções elegíveis`.

### Métricas de apoio

| Métrica | Por que importa | Baseline/meta |
|---|---|---|
| Reexecuções atribuídas a prompt/contexto/comando | Mede desperdício operacional e de quota | ausente; dono deve fornecer período e meta |
| Tokens estáticos de prompt/contexto por execução (p50/p95) | Mede consumo recorrente | ausente; medir antes/depois com o mesmo mix de tarefas |
| Falhas de Git por diretório, branch ou comando | Mede confiabilidade operacional | ausente |
| Tempo mediano entre entrega ao agente e avanço de coluna | Mede velocidade de fluxo | ausente |
| PRs que exigem correção de título/body/branch | Mede retrabalho humano | ausente |
| Execuções em que o contexto obrigatório não foi carregado | Mede cobertura entre adapters | meta candidata: zero |
| Perda/corrupção de estado em upgrade | Guardrail de segurança | meta: zero |

### Forma de validação proposta

1. Classificar de 20 a 30 execuções recentes por causa de falha/reexecução, sem inferir causa apenas pelo resultado.
2. Capturar baseline de tokens e falhas com a versão atual.
3. Após uma eventual entrega, comparar uma amostra equivalente por adapter e tipo de etapa.
4. Tratar como regressão qualquer perda de estado, execução no diretório incorreto ou ausência de restrição essencial.

A janela, amostra e metas numéricas dependem da resposta do dono e da disponibilidade dos logs.

## Custo de não fazer

Com os dados atuais, só é defensável em termos qualitativos:

- manutenção contínua de conteúdo duplicado e risco de divergência;
- consumo recorrente de contexto por instruções estáticas redundantes;
- reexecuções e intervenção humana quando comandos ou diretórios não correspondem ao trabalho;
- dificuldade para adicionar adapters e múltiplos espaços de trabalho com comportamento previsível;
- risco de repetir incidentes de integridade se regras críticas não forem entregues ou fiscalizadas.

Não há evidência para monetizar esses itens. O custo deverá ser estimado com volume mensal de execuções, taxa de reexecução, tokens por execução e tempo humano de correção fornecidos pelo dono.

## Alternativas de produto a considerar

Estas são alternativas para decisão posterior; não constituem escolha de arquitetura:

1. **Otimização incremental:** remover duplicidades e medir resultados, mantendo o mecanismo de contexto atual.
2. **Contrato comum com adaptação por fornecedor:** definir o conteúdo canônico e exigir prova de ingestão em cada adapter, admitindo arquivos/mecanismos específicos.
3. **Convenção compartilhada mais fallbacks:** adotar uma convenção amplamente aceita e gerar entradas adicionais apenas para ferramentas incompatíveis.
4. **Contexto explícito por configuração:** declarar recursos essenciais no adapter em vez de depender de descoberta implícita.
5. **Não fazer agora:** manter o comportamento atual caso baseline demonstre impacto baixo frente ao risco e esforço de migração.

Critérios de comparação: cobertura dos adapters-alvo, confiabilidade comprovada, tokens recorrentes, compatibilidade, observabilidade, reversibilidade, risco de perda de estado e custo de manutenção.

## Ordem de esforço e risco para priorização

Estimativa relativa de negócio, não estimativa técnica:

| Ordem | Frente de resultado | Esforço/incerteza | Justificativa |
|---|---|---|---|
| 1 | Reduzir duplicidade/copy mecânico e instrumentar baseline | baixo a médio | mudança mais observável e reversível |
| 2 | Separar objetivo da etapa, workflow e descrição de board | médio | exige contrato de configuração e compatibilidade |
| 3 | Tornar nomenclatura de branch configurável e verificável | médio | afeta migração de configuração e branches existentes |
| 4 | Suportar múltiplos repositórios/espaços de trabalho com clareza | médio a alto | amplia jornadas e matriz de testes |
| 5 | Garantir ingestão em múltiplos adapters e rever dependência de `.kiro/` | alto/indefinido | convenções de fornecedores divergem |
| 6 | Definir ciclo de versão e tratamento de estado | alto risco | proposta atual é destrutiva e pode interromper continuidade |

As frentes podem ser aprovadas, recusadas ou sequenciadas separadamente após a entrevista; a tabela não cria stories.

## Aderência a metas e políticas

### Aderência provável

- Confiabilidade e previsibilidade da automação.
- Redução de desperdício de quota/contexto.
- Portabilidade de adapters e configuração.
- Clareza de responsabilidade entre objetivo e workflow.

### Aderência ainda não comprovada

Não há OKR, meta trimestral, compromisso de cliente, prazo regulatório ou orçamento informado na issue. O dono precisa indicar a meta empresarial relacionada e o horizonte de resultado.

### Políticas e guardrails

- Arquivos de memória interna continuam protegidos; contexto é orientação, não controle de segurança suficiente.
- Estado persistente não pode ser descartado em upgrade sem política aprovada de retenção, migração, backup, recuperação e comunicação.
- Migrações de configuração precisam de política explícita de compatibilidade e depreciação.
- Nenhum segredo deve ser incorporado ao contexto.
- A inclusão de conteúdo persistente deve ser mínima, relevante e observável por causa do consumo recorrente de tokens.

## Decisões pendentes da entrevista

1. Quais incidentes ou execuções recentes motivam o épico, com frequência e impacto observados?
2. Qual público e jornada têm prioridade, e quais adapters precisam ser suportados no primeiro resultado?
3. Quais baseline e metas devem ser usados para sucesso, em qual prazo?
4. Há caso real de múltiplos repositórios ou workdir por agente? Qual fluxo hoje falha?
5. Qual é a meta/OKR, compromisso ou política empresarial à qual o épico responde?
6. Qual compatibilidade é exigida para `prefix`, configurações existentes, branches e versões anteriores?
7. Quais dados podem ser descartados em upgrade? Qual retenção, backup, RPO e forma de rollback são obrigatórios?
8. Remover `.kiro/` é objetivo de negócio ou preferência de implementação? Qual resultado mensurável justificaria isso?
9. As frentes podem ser aprovadas e entregues separadamente ou existe uma data/razão para mudança conjunta?

## Gate de decisão

O épico estará apto a avançar quando houver:

- respostas do dono registradas no histórico;
- ao menos uma evidência operacional da dor ou baseline acordado para medi-la;
- métrica primária, metas e janela definidas;
- adapters e jornadas-alvo delimitados;
- política de compatibilidade e tratamento de estado aprovada;
- justificativa de aderência a meta/política;
- decisão de escopo que separe resultado necessário de preferências de implementação.

Até lá, a decisão recomendada é **aguardar**, não aprovar nem recusar.
