# Diligência de negócio — Migração segura de colunas de boards

**Épico:** #91 — Migração de boards
**Responsável pela análise:** Helena Costa — Product Manager
**Data:** 22/08/2026
**Decisão recomendada:** aprovar com métricas obrigatórias de resultado

## 1. Resumo executivo

Recomenda-se aprovar uma proteção de integridade para a retirada de colunas dos boards. O problema foi confirmado por duas fontes independentes:

1. o dono relata alterações frequentes de colunas e recuperação manual recorrente de issues que ficam sem classificação, embora não exista histórico quantitativo das ocorrências;
2. o comportamento atual do produto, verificado em `src/adapters/github_board.py`, compara a lista configurada com as opções existentes e, quando há diferença, atualiza o campo Status apenas com a lista nova. Não há, antes dessa atualização, regra de negócio que identifique itens na opção retirada, mova-os e confirme o esvaziamento.

A ausência de números impede calcular ROI financeiro ou economia histórica. Ela não invalida a decisão porque há um risco de integridade demonstrável no fluxo atual e a operação declarada é não assistida: `pipe.yml` pode estar em Git enquanto a esteira roda em container, sem oportunidade confiável de intervenção manual entre a mudança e a sincronização.

A aprovação deve ser tratada como correção de confiabilidade, não como mecanismo geral de movimentação. O valor será comprovado após a entrega por telemetria de cada mudança estrutural.

## 2. Entrevista e validação das hipóteses

A entrevista foi conduzida pelo histórico da issue em 21/08/2026. As respostas do dono foram tratadas como hipóteses e confrontadas com o produto e referências de mercado.

| Hipótese do dono | Validação | Conclusão |
|---|---|---|
| Colunas são adicionadas e retiradas com frequência, gerando issues órfãs corrigidas à mão. | Não há ocorrências, volumes ou horas registrados. O código atual confirma o mecanismo capaz de produzir perda de classificação ao retirar uma opção. | Dor tecnicamente plausível e risco atual confirmado; frequência e custo histórico permanecem não quantificados. |
| Todas as issues da coluna retirada podem ir para um único destino. | Escopo explicitamente restringido pelo dono; não há necessidade declarada de decisão por issue. | Regra de negócio aceita para este épico. |
| O destino fica no mesmo board. | Confirmado pelo dono. | Migração entre boards fica fora de escopo. |
| A coluna deve permanecer enquanto houver issues. | Confirmado duas vezes: a retirada só conclui após a origem ficar vazia. | Invariante principal de segurança. |
| Não há SLA mínimo. | Confirmado pelo dono. | Segurança e consistência prevalecem sobre velocidade; ainda assim duração e tentativas serão medidas. |
| A decisão cabe a quem opera a esteira. | A mudança parte da configuração usada pela instância. | Não se cria neste épico um novo fluxo de aprovação ou perfil de autorização. |
| Não existe OKR patrocinador. | Confirmado pelo dono. | Aderência é a políticas de confiabilidade e integridade, não a uma meta comercial declarada. |
| Movimentação manual não é alternativa suficiente. | A execução pode ser desacoplada do repositório e não assistida em container. | Um processo exclusivamente manual não atende o modo operacional declarado. |

## 3. Dor fechada

Hoje, retirar da configuração uma coluna ainda ocupada pode retirar sua opção de Status antes de realocar os itens. A consequência é trabalho sem etapa inequívoca, com perda de visibilidade, priorização, execução e métricas do fluxo. A recuperação depende de encontrar e reclassificar itens manualmente, algo incompatível com uma sincronização automatizada e não assistida.

**Usuário afetado:** pessoa ou equipe que opera a esteira e depende do board para conduzir trabalho.
**Momento da dor:** sincronização seguinte a uma alteração estrutural que remove uma coluna ocupada.
**Impacto:** classificação inconsistente, recuperação manual e risco de decisões baseadas em um board incompleto.

## 4. Resultado de produto aprovado

Quando uma coluna for retirada da configuração:

- se estiver vazia, sua retirada poderá concluir sem migração;
- se contiver issues, deverá existir um único destino válido, no mesmo board, para todos os itens da origem;
- as issues deverão ser movidas ao destino antes da retirada da coluna;
- a coluna de origem permanecerá ativa enquanto houver qualquer item nela;
- ausência ou invalidade do destino impedirá a retirada e preservará a classificação existente;
- falhas ou interrupções impedirão a retirada, permitirão novas tentativas e não poderão perder nem duplicar issues;
- IDs, conteúdo, relações e demais atributos das issues deverão ser preservados;
- cada tentativa deverá informar contagem inicial, itens movidos, itens restantes e resultado da retirada.

O épico é um remédio para mudança estrutural. Não deve virar regra cotidiana de roteamento de issues.

## 5. Fora de escopo

- migração de issues entre boards;
- escolha de destino diferente por issue;
- arquivar ou encerrar issues como efeito da retirada;
- limite de WIP ou capacidade da coluna;
- novo fluxo de autorização, aprovação ou janela de mudança;
- formato da configuração, tecnologia, arquitetura ou decomposição em stories;
- promessa de prazo máximo para concluir a migração.

## 6. Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Não fazer e continuar corrigindo manualmente | Recusada. Mantém risco de integridade e depende de intervenção que pode não existir no modo container. |
| Apenas bloquear a retirada de coluna ocupada | Reduz dano, mas transfere toda a movimentação para uma atuação manual que o dono declarou não ser operacionalmente garantida. Pode ser comportamento seguro quando não houver destino, mas não resolve o caso normal. |
| Escolher automaticamente uma coluna padrão | Recusada. Introduz decisão de negócio não declarada e pode classificar trabalho no estágio errado. |
| Migrar todos os itens para um destino explícito e só então retirar | Selecionada. Resolve a dor com regra inequívoca e mantém falhas em estado seguro. |
| Criar um mecanismo geral de roteamento ou migração entre boards | Recusada para este épico. Amplia escopo sem demanda ou retorno demonstrado. |

## 7. Pesquisa de mercado

O padrão observado é evitar a exclusão cega de um estado ocupado:

- O Jira Cloud, ao atualizar um workflow com status removidos, solicita o mapeamento dos itens para novos status antes de salvar a mudança. Também documenta que a exclusão direta de um status simplificado só é permitida quando nenhum item o utiliza.
- A documentação de configuração de colunas do Jira alerta que status sem mapeamento podem retirar itens da visualização do board, reforçando o impacto de deixar trabalho sem coluna.
- A referência pública da mutação `updateProjectV2Field` do GitHub descreve a atualização do campo, mas não documenta garantia de remapeamento seguro dos itens quando uma opção é retirada. Portanto, não há base para delegar essa proteção ao provedor.

A proposta é aderente ao padrão de mercado de mapear ou impedir a retirada; diferencia-se apenas por executar de forma não assistida.

## 8. Retorno e medição

### Benefício esperado

- evitar issues sem classificação após mudanças estruturais;
- eliminar recuperação manual causada por esse evento;
- manter métricas e priorização do board confiáveis;
- permitir evolução frequente do fluxo sem supervisão no instante da sincronização.

### Indicadores por evento

1. quantidade de colunas cuja retirada foi solicitada;
2. quantidade de issues encontradas na origem;
3. quantidade movida ao destino;
4. quantidade restante na origem após cada tentativa;
5. retiradas concluídas e impedidas;
6. falhas e número de novas tentativas;
7. issues sem coluna atribuíveis à mudança estrutural;
8. intervenções manuais e tempo gasto em recuperação.

### Metas de aceite e resultado

- **0** issues sem coluna causadas por retirada configurada;
- **100%** das issues inicialmente encontradas no destino explícito antes da retirada;
- **0** perda ou duplicação de issues;
- **0** retirada concluída com a origem ainda ocupada;
- **0** alteração da classificação existente quando o destino for ausente ou inválido;
- **100%** dos eventos com contagens e resultado verificáveis.

Como não existe baseline histórico, o retorno será medido prospectivamente. Nos primeiros 90 dias, registrar para cada evento `itens × tempo médio observado de recuperação evitada`. Se não houver mudanças estruturais no período, não se deve alegar economia; apenas a cobertura do risco estará comprovada.

## 9. Custo de não fazer

Não há valor monetário comprovado. O custo observável é variável e cresce com:

`mudanças de coluna × itens afetados × tempo de descoberta e reclassificação`

Além das horas manuais, permanece exposição a trabalho invisível, atraso de execução e métricas incorretas. Como a operação pode ser não assistida, o defeito pode persistir até uma inspeção humana posterior. A falta de histórico impede quantificar o custo, mas não elimina o risco funcional confirmado.

## 10. Ordem de esforço e prioridade

**Ordem de esforço de negócio: média.** O escopo é limitado a um board e a um destino único, mas exige comportamento seguro em interrupções, repetição, validação de conclusão e evidência operacional. Esta classificação é apenas uma ordem de grandeza para decisão de portfólio; a estimativa de engenharia será feita na etapa apropriada.

**Prioridade recomendada:** correção de confiabilidade antes de novas capacidades de administração estrutural do board. Não há urgência por data ou SLA declarados, portanto a prioridade relativa deve considerar a agenda de confiabilidade do produto.

## 11. Aderência a metas e políticas

Não há OKR, receita ou compromisso externo associado. A aderência é às políticas e princípios já documentados do produto:

- preservação da integridade do estado e das issues;
- falha segura, sem aplicar mudança destrutiva incompleta;
- operação automatizada e repetível;
- observabilidade suficiente para auditoria e suporte;
- escopo mínimo, sem decisão implícita de roteamento.

## 12. Riscos e condições para aprovação

| Risco | Condição de negócio |
|---|---|
| Destino ambíguo ou inexistente | Não retirar a coluna nem alterar a classificação atual. |
| Falha parcial | Manter a origem ativa, registrar o restante e permitir nova tentativa segura. |
| Volume elevado | Não há limite funcional declarado; medir duração e progresso, sem relaxar integridade. |
| Alegação de ROI sem baseline | Reportar somente dados prospectivos observados. |
| Expansão para roteamento geral | Manter fora deste épico e exigir nova diligência. |

## 13. Decisão

**Aprovar para a próxima etapa**, com os resultados e limites desta diligência como contrato de negócio. A recomendação se sustenta na confirmação do mecanismo de risco no produto atual, na operação não assistida e na aderência ao padrão de mercado. A inexistência de evidência histórica quantitativa deve constar da decisão e impede alegar payback, mas será sanada prospectivamente pelas métricas obrigatórias sem bloquear a correção de integridade.

## Referências

1. Código atual: `src/adapters/github_board.py`, métodos `sync_boards` e `_update_status_options`.
2. Atlassian, [Move work items to new statuses while updating your workflow](https://support.atlassian.com/jira-software-cloud/docs/move-issues-to-new-statuses-while-updating-your-workflow/).
3. Atlassian, [Configure columns](https://support.atlassian.com/jira-software-cloud/docs/configure-columns/).
4. GitHub, [GraphQL API reference](https://docs.github.com/en/graphql/reference/input-objects#updateprojectv2fieldinput).
5. Entrevista com o dono registrada no histórico da issue #91 em 21/08/2026.

Conteúdo de fontes externas foi resumido e reformulado; nenhuma garantia não documentada do provedor foi presumida.
