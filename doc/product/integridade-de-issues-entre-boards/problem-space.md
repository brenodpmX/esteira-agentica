# Problem Space — Integridade de issues entre boards

Status: draft — recomendação de aprovação negocial
Owner: product
Last updated: 2026-08-26

## Inputs
- Issue #230, seu histórico e respostas do dono em 2026-08-26.
- API e timelines do GitHub para as issues #204–#240.
- Logs de agente das issues #221, #222, #223, #226, #232 e #235.
- `doc/incidente/sub-issues-propagadas/ticket.md` e `homologacao.md`.
- `doc/changes/88-sub-issues-propagadas-entre-boards.md`.
- [GitHub Docs — Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues).
- [GitHub Docs — About Projects](https://docs.github.com/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects).

## Contexto
O GitHub trata sub-issues como sua estrutura nativa para decompor trabalho e expõe a relação e o progresso também em Projects. O produto suporta hierarquias de até oito níveis e cem sub-issues por pai; por isso, abandonar permanentemente essa capacidade reduziria rastreabilidade e iria contra o uso esperado da plataforma.

Projects também oferece campos, automações e adição automática de itens. Essa flexibilidade exige que a esteira diferencie participação deliberada de um efeito automático do vínculo pai/filho. O board é uma fronteira de execução, não apenas uma visualização: tipo, coluna e agente dependem dele.

O incidente #88 já havia identificado a propagação de filhas sem `Status`. A correção final (`a00ba7c`) foi homologada e entrou em `main` pelo PR #102 em 19/08/2026. A resposta do dono de que “produção sempre usa main” foi tratada como hipótese: ela confirma a política de branch, mas não identifica sozinha o commit do artefato em execução.

A recorrência, contudo, pôde ser comprovada independentemente do relato do dono pelos eventos e logs posteriores ao merge.

## Evidência observada em 25–26/08/2026

| Grupo | Filhas | Board intencional | Board propagado do pai | Resultado |
|---|---:|---|---|---|
| Stories de #93 | #221–#223 | User Stories | Epics | 3/3 propagadas; 3 execuções de Product Manager no board errado |
| Stories de #91 | #226–#229 | User Stories | Epics | 4/4 propagadas; #226 teve tentativa de execução no board errado |
| Tasks das stories #226/#228/#229 | #231–#240 | Tasks | User Stories | 10/10 propagadas; #232 e #235 executadas como stories |

Fatos verificáveis:
- **17 de 17** relações recentes (100%) geraram adição automática ao Project do pai, feita por `github-project-automation` segundos após o vínculo.
- **17 de 17** exigiram remoção posterior pelo usuário `brenodpm`; não houve remoção preventiva eficaz na janela observada.
- **6 de 17 issues** (35,3%) chegaram a executar no board errado: #221, #222, #223, #226, #232 e #235.
- Foram encontrados **7 despachos indevidos**. Cinco concluíram e registraram **20,35 créditos**; dois terminaram em erro sem créditos registrados.
- Os logs provam a troca de papel: #221–#223 e #226 foram entregues a Product Manager como épicos; #232 e #235 foram entregues a Tech Lead como stories, embora fossem tasks.
- O relato de “pelo menos 50%” não foi confirmado na amostra completa: a taxa comprovada por issue foi 35,3%. A direção e a gravidade do problema foram confirmadas, e o custo mínimo é suficiente para justificar ação.

Há ainda cinco pares de issues com títulos repetidos (#204/#210, #205/#211, #206/#212, #207/#213 e #208/#214). As timelines mostram que elas não tinham parent e permaneceram somente no board Tasks; portanto, não são prova do mecanismo entre boards e ficam fora do baseline deste épico. Esse fenômeno já aparece tratado separadamente em #219/#225.

## Problemas
- **Fronteira de execução violada:** uma filha herda presença no board do pai sem intenção do dono.
- **Agente e instrução incompatíveis:** o mesmo conteúdo é interpretado como outro nível de trabalho.
- **Cascata potencial:** uma task tratada como story recebe instrução para criar novas tasks, ampliando trabalho sem fundamento.
- **Custo de IA:** já há 20,35 créditos comprovadamente consumidos em execuções erradas; duas tentativas adicionais falharam.
- **Retrabalho operacional:** 17 remoções manuais foram necessárias na amostra.
- **Baixa confiabilidade da entrega anterior:** código mesclado e homologado não se traduziu em resultado observável no runtime.
- **Medição incompleta:** ainda não existe conversão dos créditos e do tempo de limpeza em moeda, portanto não se deve inventar ROI financeiro.

## Impacto e custo de não fazer
No volume observado, cada nova relação entre boards teve 100% de chance de gerar participação indevida e 35,3% de chance comprovada de disparar pelo menos um agente errado. Manter o cenário implica:
- repetição do consumo mínimo observado de créditos a cada lote comparável;
- tempo humano recorrente para identificar e remover itens;
- risco de alteração concorrente de body, status e relações;
- criação em cascata de trabalho sem lastro quando o papel errado recebe permissão para decompor a issue;
- perda de confiança no board, forçando conferência manual e reduzindo o benefício da automação.

O retorno será medido primeiro em unidades operacionais — execuções, créditos, remoções e resíduos evitados. Conversão financeira só deve ser acrescentada quando houver preço efetivo por crédito e tempo de limpeza medido.

## Pesquisa de mercado e alternativas
A referência de mercado aplicável é a própria plataforma integrada. O GitHub posiciona sub-issues como mecanismo de hierarquia e Projects como ferramenta flexível com campos e automações. Isso favorece preservar hierarquia e tornar a automação segura, em vez de trocar de ferramenta sem evidência.

| Alternativa | Benefício | Limite/risco | Decisão de negócio |
|---|---|---|---|
| Manter apenas a correção já mesclada | Nenhum novo esforço de construção | Recorrência pós-merge comprovada; resultado insuficiente | Rejeitada como resposta isolada |
| Limpeza manual após cada propagação | Contenção imediata | Não evita agentes errados, custa operação e não escala | Apenas emergência |
| Suspender temporariamente novos vínculos pai/filho | Interrompe a fonte durante contenção | Perde hierarquia, progresso e rastreabilidade | Autorizada pelo dono como contingência temporária |
| Substituir hierarquia por labels/campos | Pode separar visualizações | Não oferece a mesma relação pai/filho e exige mudança ampla de processo | Não justificada neste momento |
| Unificar todos os tipos em um único board | Elimina fronteira entre Projects | Mistura fluxos, agentes e políticas; muda o produto inteiro | Fora de escopo |
| Garantir intenção antes da execução e reconciliar efeitos automáticos | Preserva hierarquia e evita processamento indevido | Exige entrega e prova operacional | Direção de negócio recomendada; arquitetura em etapa posterior |

## Oportunidade
Resolver agora evita que o crescimento do número de agentes e relações multiplique um defeito já reproduzido em toda a amostra recente. A prioridade é operacional, mesmo sem OKR formal informado: integridade do roteamento é pré-condição para metas de autonomia, custo e confiabilidade da esteira.

## Ordem de esforço e gates
1. **Contenção e evidência do runtime:** registrar a versão efetiva, impedir temporariamente novos vínculos se a exposição continuar e preservar evidência do incidente.
2. **Integridade antes do despacho:** assegurar que participação não intencional nunca torne a issue elegível no board errado e que resíduos sejam reconciliados sem ação manual.
3. **Preservação de usos legítimos:** manter relações pai/filho e proteger qualquer participação multi-board explicitamente autorizada.
4. **Observabilidade e validação:** medir adições automáticas, reconciliação, despachos, créditos e intervenções durante 30 dias e no mínimo 17 relações.
5. **Limpeza do resíduo:** tratar itens e efeitos já materializados sem confundi-los com a prevenção de novas ocorrências.

A confirmação exata do commit em execução é evidência obrigatória de rollout, mas não bloqueia a aprovação do problema: a recorrência e o impacto já estão comprovados.
