# Diligência de Negócio — Migração de boards

Status: bloqueado — aguardando entrevista com o dono
Owner: product
Last updated: 2026-08-21

## Recomendação executiva

**Não aprovar nem recusar ainda.** Há uma hipótese coerente de risco operacional:
retirar uma coluna da configuração pode deixar issues sem classificação e fora do
fluxo normal de trabalho. Porém, o histórico da issue #91 está vazio e não traz
ocorrências, volume afetado, horas de recuperação, prazo, meta patrocinadora nem
regras de destino confirmadas. Sem esses dados, não é possível fechar dor,
retorno ou prioridade com evidência.

A entrevista foi aberta no comentário da issue. As respostas do dono serão
tratadas como hipóteses e deverão ser confrontadas com ocorrências, logs e dados
do board antes da decisão.

## Inputs verificados

- Issue #91, “Migração de boards”.
- Histórico da issue #91: vazio em 21/08/2026.
- README do produto: a seleção de trabalho percorre colunas configuradas e a
  sincronização depende da classificação da issue no board.
- Busca no repositório por uma regra declarativa de migração de colunas: não foi
  encontrada capacidade equivalente à proposta da issue.
- Documentação pública de GitHub Projects, Jira Cloud e Azure Boards listada em
  [Referências](#referências).

## Problema e evidência disponível

### Fato estabelecido

O produto organiza e seleciona trabalho por board e coluna. Portanto, uma issue
sem coluna deixa de ter uma posição inequívoca no fluxo; isso ameaça sua
visibilidade, priorização, execução e a qualidade de métricas por etapa.

### Hipóteses ainda não comprovadas

1. A remoção de colunas ocupadas acontece ou acontecerá com frequência suficiente
   para justificar automação.
2. O provedor efetivamente deixa itens sem `Status` no cenário exato relatado, em
   vez de bloquear a alteração ou aplicar outro comportamento.
3. Todas as issues de uma coluna removida podem ir para um único destino sem
   decisão caso a caso.
4. A migração deve ser imediata e automática, e não uma operação deliberada com
   validação humana.
5. Preservar temporariamente a configuração anterior é uma necessidade de
   negócio; por enquanto, é apenas uma solução sugerida, não um requisito
   validado.

A decisão exige um exemplo reproduzível e dados das mudanças de board já feitas
ou planejadas.

## Mercado e alternativas

- **GitHub Projects:** `Status` é um campo de seleção única. A documentação
  pública consultada explica opções e valores padrão, inclusive que remover um
  valor padrão não altera itens existentes, mas não documenta um fluxo guiado de
  remapeamento ao retirar uma opção. Logo, não há base documental para delegar a
  proteção ao provedor.
- **Jira Cloud:** ao atualizar um workflow, o produto alerta sobre itens em
  statuses que serão excluídos e pede que sejam movidos para um status válido.
- **Azure Boards:** a orientação oficial é identificar os itens afetados,
  escolher estados válidos, mover em lote e verificar o resultado antes de
  ocultar ou remover um estado. Se isso não for feito, os itens mantêm o valor,
  mas ficam inválidos e precisam ser corrigidos antes de novas edições.

O padrão de mercado observado é **não tratar a retirada de uma etapa ocupada
como uma simples alteração de configuração**: é preciso impedir a mudança ou
migrar explicitamente os itens afetados.

### Alternativas de produto

| Alternativa | Benefício | Limitação/risco | Ordem de esforço preliminar |
|---|---|---|---|
| Manter processo manual com checklist | Sem desenvolvimento; adequado se o evento for raríssimo | Depende de disciplina e mantém risco de erro humano | Baixa |
| Bloquear retirada enquanto houver issues | Evita itens sem coluna com regra simples | Operador ainda move itens manualmente; pior para alto volume | Baixa a média |
| Exigir destino explícito e migrar o conjunto antes de concluir a retirada | Reduz trabalho manual e registra a intenção de negócio | Exige regras para falha parcial, repetição, auditoria e encerramento | Média a alta |
| Enviar automaticamente para uma coluna padrão | Pouco atrito operacional | Pode corromper o significado do fluxo e métricas sem decisão explícita | Baixa a média, mas não recomendada sem aceite do risco |

As ordens acima são comparativas de escopo de produto, não estimativas de
engenharia nem decisão de arquitetura.

## Resultado de produto proposto para validação

Se os dados confirmarem recorrência e impacto, o incremento deve garantir que:

1. nenhuma mudança de configuração deixe uma issue sem coluna;
2. uma coluna vazia possa ser retirada sem migração;
3. uma coluna ocupada só seja retirada após todas as suas issues terem destino
   válido e explícito no mesmo board;
4. quando não houver destino válido, a mudança seja interrompida com orientação
   acionável e sem alterar a classificação existente;
5. a conclusão seja verificável: total de origem antes, total movido, total de
   falhas e confirmação de origem vazia;
6. repetição após interrupção não duplique nem perca trabalho;
7. histórico e demais atributos das issues sejam preservados.

Ainda precisam de confirmação do dono: destino único versus decisão por issue,
momento da migração, comportamento esperado em falhas, necessidade de aprovação,
escopo de provedores e prazo operacional.

## Retorno e como medir

### Benefícios esperados

- evitar issues invisíveis ou paradas fora do fluxo;
- evitar triagem e correção manual após uma mudança estrutural;
- preservar métricas de quantidade e tempo por etapa;
- reduzir risco de execução na etapa errada ou de perda de prioridade.

### Métricas propostas

| Métrica | Alvo preliminar | Evidência necessária |
|---|---:|---|
| Issues sem coluna causadas por mudança configurada | 0 | Comparação antes/depois e auditoria da mudança |
| Issues no destino declarado após uma migração concluída | 100% | Contagem de origem e destino por execução |
| Migrações com perda/duplicação de issue | 0 | Reconciliação dos IDs antes/depois |
| Tempo de recuperação manual | Tendência a 0 | Registro de incidentes e horas gastas |
| Tempo para concluir mudança de board | A definir | Baseline e SLA informados pelo dono |

### Cálculo de retorno

O retorno poderá ser estimado como:

`(incidentes evitados × horas médias de recuperação × custo-hora) + custo de atraso evitado − custo de entrega e operação`

Hoje nenhum dos fatores possui baseline. Aprovar com ROI alegado seria
suposição. Se o evento for raro, a alternativa de bloqueio/checklist pode ter
melhor relação custo-benefício; se for recorrente ou de alto impacto, a migração
declarada tende a justificar o esforço adicional.

## Custo de não fazer

Qualitativamente: trabalho pode ficar sem posição operacional, métricas podem
subcontar o fluxo, o operador precisa descobrir e corrigir itens manualmente e
há risco de execução atrasada ou no contexto errado. Quantitativamente, o custo
permanece desconhecido até obter frequência, volume médio, tempo de recuperação
e impacto de prazo das ocorrências reais ou mudanças planejadas.

## Aderência a metas e políticas

- **Aderência provável:** confiabilidade da sincronização, integridade do estado
  do trabalho e operação segura por configuração.
- **Políticas atendidas pela proposta:** não perder issues, não escolher destino
  silenciosamente e manter evidência verificável da mudança.
- **Lacuna:** nenhuma meta, OKR, prazo regulatório ou compromisso operacional foi
  informado. O dono deve indicar a meta patrocinadora e o custo de atraso.

## Fora de escopo nesta etapa

- escolher tecnologia, persistência, API, algoritmo ou arquitetura;
- definir formato final de configuração;
- redesenhar workflows ou decidir quais colunas cada board deve ter;
- criar stories;
- migração entre boards, salvo confirmação explícita posterior do dono.

## Gate para decisão

A issue fica em análise com `need_human`. Ela estará apta a aprovação ou recusa
quando houver:

1. respostas do dono às perguntas registradas no comentário;
2. ao menos uma evidência de ocorrência ou plano concreto de mudança, com volume;
3. regra de destino e tratamento de exceções confirmados;
4. baseline, alvo e forma de medição aceitos;
5. meta patrocinadora, prazo e custo de atraso;
6. ordem de esforço revisada por engenharia, sem antecipar arquitetura.

## Referências

1. [GitHub Docs — About single select fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-single-select-fields)
2. [Atlassian — Create, edit and delete statuses in team-managed spaces](https://support.atlassian.com/jira-software-cloud/docs/create-edit-and-delete-statuses-in-team-managed-projects/)
3. [Microsoft Learn — Customize the workflow (Inheritance process)](https://learn.microsoft.com/en-us/azure/devops/organizations/settings/work/customize-process-workflow?view=azure-devops)

Conteúdo das fontes externas foi parafraseado para respeitar restrições de
licenciamento.
