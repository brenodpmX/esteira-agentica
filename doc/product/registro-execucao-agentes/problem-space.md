# Problem Space — Registro de execução de agentes

Status: aguardando decisões do dono (`need_human`)
Owner de negócio: Breno de Paula
Responsável pela diligência: Helena Costa — Product Manager
Última atualização: 2026-08-22

## Decisão de negócio

**Manter em Análise de Negócio.** A dor e a demanda por análise em lote estão
validadas, e há evidência de que créditos e duração já aparecem ao fim de
execuções reais. O investimento ainda não deve ser aprovado nem recusado: falta
o dono aceitar a unidade de consumo que é de fato observável, a definição de
resultado/retrabalho, metas do primeiro ciclo e a política mínima de acesso e
exclusão.

Não há decisão de tecnologia ou arquitetura neste documento.

## Inputs e método

- Issue #176 e respostas do dono em 21 e 22/08/2026.
- Implementação atual em `src/__main__.py` e
  `src/adapters/kiro_cli_agent.py`.
- Amostra agregada dos logs locais disponíveis em `/app/logs`, sem incorporar
  prompt ou chat à documentação.
- Documentação oficial de Kiro, Langfuse e LangSmith, consultada em 22/08/2026.

As respostas do dono foram tratadas como hipóteses e confrontadas com o produto
e fontes externas. Conteúdo das fontes externas foi resumido e parafraseado.

## Dor validada

Operadores de IA, SREs e responsáveis por monitoramento conseguem investigar
uma execução lendo seu log, mas não responder em lote, com rastreabilidade:

- quantas execuções ocorreram e quanto tempo/consumo acumularam;
- quais falharam, foram interrompidas ou não produziram avanço;
- quantas novas execuções representaram retrabalho;
- quanto uma issue e toda a sua linhagem histórica consumiram;
- como consumo e resultado variam por board, etapa, agente e modelo.

O registro atual é um Markdown por execução com parâmetros, prompt e chat. Ele
não constitui uma série estruturada nem preserva, como campos consultáveis, o
início/fim, duração, resultado e consumo. A continuidade de sessão também não é
um substituto para um registro de execuções: uma mesma sessão pode participar de
mais de uma entrega ao agente.

## Evidência interna e baseline possível

A documentação pública do modo headless do Kiro não promete telemetria de uso
no contrato de saída. Entretanto, os logs reais disponíveis no host encerram
execuções com `Credits` e `Time`; portanto, créditos e duração são observáveis
na versão atualmente usada e devem ser registrados com sua fonte, sem assumir
que esse formato será universal ou permanente.

Amostra local de 21–22/08/2026:

- 24 arquivos de execução em 11 issues;
- 22 arquivos com resumo extraível de créditos e duração; 2 sem resumo no
  instante da aferição;
- 123,99 créditos e 1,12 hora acumulados nas 22 execuções;
- mediana de 5,81 créditos e 3,14 minutos por execução;
- intervalo observado: 0,35–11,54 créditos e 0,57–5,73 minutos.

Esta é uma amostra de disponibilidade, não um baseline histórico representativo
nem uma meta. Sete registros contêm marcadores de falhas internas de ferramenta,
mas isso não prova sete execuções malsucedidas: hoje não existe taxonomia que
separe falha terminal, falha recuperada e ausência de avanço. Repetições por
issue também não podem ser chamadas de retrabalho sem considerar etapa e avanço.
Essas limitações são parte da dor, não dados a preencher por suposição.

## Unidade de consumo e custo

A meta verbal do dono é medir tokens, tempo, retrabalho e custo até o nível de
épico. As evidências impõem distinções:

- o Kiro cobra créditos fracionários por requisição;
- a saída real observada fornece créditos e duração por execução;
- o modo headless público não documenta tokens nem créditos como contrato de
  saída;
- o relatório corporativo do Kiro fornece créditos por usuário/dia e tipo de
  cliente, não por execução ou issue;
- créditos, tokens e moeda não são unidades intercambiáveis.

Consequência de negócio: o primeiro corte pode medir **créditos reportados pelo
Kiro** e duração por execução. Tokens devem ficar `indisponíveis` quando a fonte
não os reportar. Custo monetário só pode ser exibido quando houver regra aprovada
e auditável que considere plano, franquia, adicional e período; não se deve
multiplicar créditos por um preço presumido.

## Resultado de negócio proposto — pendente de aceite

Disponibilizar um registro independente do TTL dos logs para cada entrega de uma
issue a um agente e uma consulta/exportação da issue raiz com todos os seus
descendentes históricos, de modo que operação e SRE respondam análises em lote
sem abrir logs individuais.

Cada execução deve expor, no mínimo:

- identidade da execução e da issue;
- início, fim e duração;
- board e etapa no momento da execução;
- plataforma, agente e modelo;
- resultado da execução e evidência de avanço da issue, como dimensões
  separadas;
- consumo reportado com valor, unidade, fonte e disponibilidade, distinguindo
  zero de indisponível;
- referência ao log detalhado, sem duplicar prompt/chat no registro analítico.

A visão de uma issue raiz deve:

- incluir todos os descendentes já vinculados, mesmo removidos posteriormente,
  conforme a resposta do dono;
- identificar itens sem registro e relações inválidas;
- impedir ciclo e dupla contagem;
- agregar quantidade, duração e consumo por issue e no total;
- permitir segmentação por board, etapa, plataforma, agente, modelo e resultado.

“Primeiro corte sem dashboard” significa entregar o dado consultável e
exportável para uso por operação/monitoramento, mas não incluir ainda interface
gráfica dedicada, alertas ou avaliação automática de qualidade.

## Retorno e como medir

O retorno inicial é **capacidade de gestão**, não uma economia monetária já
comprovada. O épico cria o baseline hoje inexistente para decisões posteriores
sobre modelos, etapas, reexecuções e capacidade.

Metas propostas para aceite do dono, medidas nos primeiros 30 dias após a
entrega:

1. pelo menos 95% das execuções iniciadas possuem registro com identidade,
   tempo, resultado e fonte de consumo;
2. 100% das ausências de consumo são explícitas como indisponíveis, nunca zero
   ou estimativa silenciosa;
3. uma consulta de issue raiz retorna 100% dos descendentes históricos
   conhecidos, sem ciclo ou dupla contagem, e sinaliza os sem registro;
4. um operador responde quantidade, duração, créditos reportados, resultados e
   repetições de uma issue raiz em até 5 minutos, sem ler logs individualmente;
5. ao final dos 30 dias são publicados o baseline de taxa de falha terminal,
   repetição sem avanço, cobertura de consumo e créditos/duração por etapa.

O retorno monetário só poderá ser calculado depois desse período, com uma regra
de custo aprovada e dados sobre tempo manual ou desperdício evitado.

## Custo de não fazer

- A amostra já soma 123,99 créditos em 22 execuções sem atribuição consolidada;
  o volume continuará crescendo sem uma base para explicar consumo.
- Falhas terminais, falhas recuperadas e reexecuções sem avanço permanecem
  misturadas nos logs, impedindo priorizar confiabilidade.
- Toda análise por épico exige localizar e interpretar arquivos, repetir a
  consolidação e correr risco de dupla contagem.
- Expirar logs pelo TTL elimina evidência antes de existir uma série histórica.
- Decisões sobre agente/modelo permanecem anedóticas; não é possível provar
  economia, regressão ou melhoria.

Não foi atribuído valor monetário a esses impactos por falta de baseline e de
regra de conversão de créditos.

## Mercado e alternativas

O mercado confirma o padrão “execução/trace + filhos + uso + custo”, mas também
confirma que custo depende de telemetria ou preço fornecido:

- **Langfuse** registra uso e custo por geração e permite agregação; recebe o
  uso/custo do provedor ou infere com modelo, tokenizer e tabela de preços. Ele
  alerta que alguns modelos não permitem inferência correta sem uso reportado.
- **LangSmith** mostra tokens/custo por trace e por filhos, com agregação; exige
  contagem de tokens, modelo/provedor e preço, ou custo enviado diretamente.
- **Relatório corporativo do Kiro** é alternativa parcial para governança de
  assinatura: entrega CSV diário com créditos por usuário e cliente, mas não
  resolve atribuição por execução, issue ou hierarquia.
- **Continuar com logs + scripts ad hoc** tem menor investimento inicial, mas
  mantém esforço recorrente, contrato frágil, dependência do TTL e ausência de
  uma taxonomia compartilhada.
- **Adotar plataforma externa de observabilidade** oferece recursos maduros,
  porém adiciona integração, operação e política de dados e ainda não cria
  tokens que o provedor não expõe. A escolha de produto/arquitetura pertence a
  etapa posterior.

A diferenciação necessária para esta esteira não é um dashboard genérico, mas a
atribuição nativa à issue, etapa e linhagem histórica do board.

## Ordem de esforço sugerida

Ordem por dependência de valor, sem estimativa técnica:

1. registro íntegro por execução, resultado básico, duração e consumo reportado;
2. consulta/exportação por issue e filtros operacionais;
3. linhagem histórica e agregação sem dupla contagem;
4. aferição de repetição sem avanço/retrabalho com taxonomia aceita;
5. conversão monetária, dashboard e alertas somente após fonte, baseline e
   necessidade comprovados.

Os itens 1–3 formam o primeiro corte proposto. Os itens 4–5 carregam maior
incerteza de negócio e não devem bloquear a coleta inicial, mas a definição de
“retrabalho” precisa ser aceita antes de a métrica ser publicada.

## Aderência a metas e políticas

A demanda é aderente à operação confiável e ao controle de consumo, mas o dono
não indicou OKR, prazo ou responsável pela aferição. A política mínima já
fechada é manter o registro estatístico independente do TTL do log e não
replicar prompt/chat sem necessidade.

Permanecem sem decisão: prazo de retenção do registro, perfis autorizados para
consulta/exportação, direito de exclusão e efeito da exclusão de uma issue. Sem
isso, não há gate de governança suficiente para aprovação.

## Fora de escopo do primeiro corte

- dashboard e alertas;
- avaliação automática de qualidade do conteúdo do agente;
- promessa de tokens ou custo monetário sem fonte verificável;
- cópia de prompt/chat para a base analítica;
- decisão de tecnologia, arquitetura ou fornecedor;
- criação de stories.

## Gates pendentes

O dono deve confirmar:

1. créditos reportados pelo Kiro como unidade autoritativa inicial, mantendo
   tokens e moeda como indisponíveis quando não houver fonte;
2. a taxonomia `concluída`, `falha terminal`, `timeout`, `interrompida` e
   `resultado desconhecido`, separada de “issue avançou: sim/não”, e a regra de
   retrabalho proposta no comentário da issue;
3. as cinco metas de 30 dias;
4. retenção, acesso, exportação e exclusão;
5. o primeiro corte sem dashboard/alertas, além de OKR/prazo e responsável pela
   aferição.

Aprovar se os cinco gates forem respondidos de forma consistente. Reavaliar ou
recusar se tokens/custo exato forem obrigatórios sem fonte disponível, ou se não
houver responsável e critério de sucesso.

## Fontes

- Produto atual:
  [`src/adapters/kiro_cli_agent.py`](../../../src/adapters/kiro_cli_agent.py) e
  logs locais de 21–22/08/2026.
- [Kiro — Billing](https://kiro.dev/docs/billing/): cobrança em créditos
  fracionários por requisição.
- [Kiro — Headless mode](https://kiro.dev/docs/cli/headless/): contrato público
  de execução headless, sem campo documentado de uso por execução.
- [Kiro — Viewing per-user activity](https://kiro.dev/docs/enterprise/monitor-and-track/user-activity/):
  CSV diário com créditos agregados por usuário/cliente.
- [Langfuse — Token & Cost Tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking):
  uso/custo ingerido ou inferido, com limitações quando a telemetria não existe.
- [LangSmith — Cost tracking](https://docs.langchain.com/langsmith/cost-tracking):
  agregação em traces condicionada a tokens/preço ou custo informado.
