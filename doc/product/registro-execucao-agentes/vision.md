# Vision — Registro de execução de agentes

Status: approved
Owner: product
Last updated: 2026-08-25

## Inputs
- Issue #176 e histórico de entrevista com o dono, consultados em 2026-08-25.
- Amostra dos logs locais de 21–22/08/2026 registrada no histórico da issue.
- [Kiro — Viewing per-user activity](https://kiro.dev/docs/enterprise/monitor-and-track/user-activity/)
- [Kiro CLI — Headless mode](https://kiro.dev/docs/cli/headless/)
- [Langfuse — Model Usage & Cost Tracking](https://langfuse.com/docs/model-usage-and-cost)
- [LangSmith — Cost tracking](https://docs.langchain.com/langsmith/cost-tracking)

## Problema
Operadores de IA, SREs e monitoramento conseguem inspecionar uma execução isolada nos logs atuais, mas não conseguem responder de forma confiável e rápida quantas execuções foram necessárias para entregar uma issue ou sua linhagem, quanto tempo e consumo cada etapa demandou, quais resultados ocorreram nem quanto esforço foi repetido sem avanço.

Os logs detalhados expiram e não formam uma série histórica estruturada. Isso impede atribuir consumo a entregas, comparar agentes, modelos e etapas, distinguir falhas terminais de recuperações e medir repetição com uma regra reproduzível.

## Solução
Disponibilizar um registro de negócio por entrega de uma issue a um agente, independente do TTL do log detalhado, e uma consulta/exportação que consolide a issue raiz e todos os seus descendentes históricos conhecidos.

Cada registro deve identificar a execução, a issue, o intervalo e a duração, o board e a etapa, a plataforma, o agente, o modelo, o resultado, se houve avanço e o consumo informado pela fonte. O vocabulário geral será “Tokens”; cada plataforma preservará a unidade nativa reportada por seu adapter, como créditos no Kiro. Valor, unidade, fonte e disponibilidade devem permanecer explícitos, sem equiparar unidades ou estimar dados ausentes.

O registro terá retenção própria configurável em dias. Sem configuração, não haverá expurgo automático. A exclusão da issue não elimina seus registros, e a consulta/exportação será governada pelo operador da esteira. Dashboard, alertas, avaliação automática de qualidade e conversão monetária sem fonte ficam fora deste épico.

## Público-alvo
- Operador responsável pela esteira de IA, para localizar falhas, repetições e concentração de consumo.
- SRE e monitoramento, para acompanhar duração, cobertura e comportamento operacional em lote.
- Produto e responsáveis por entrega, para entender o esforço agregado de uma issue raiz e sua linhagem.
- Responsáveis pelo custo operacional, para analisar a unidade efetivamente reportada pela plataforma sem estimativas não auditáveis.

## Proposta de valor
Transformar evidência efêmera e dispersa em uma visão rastreável por execução e por entrega completa, reduzindo consolidação manual e permitindo formar o primeiro baseline confiável de volume, duração, resultado, repetição e consumo.

O diferencial para a esteira é manter o vínculo com board, etapa, issue e linhagem histórica. Relatórios nativos do Kiro agregam créditos por usuário e dia; ferramentas de observabilidade de mercado agregam traces e uso quando instrumentadas, mas não conhecem automaticamente a semântica de avanço e hierarquia deste produto.

## Métricas de sucesso
Na primeira janela de 30 dias após disponibilização:

- pelo menos 95% das execuções iniciadas com identidade, tempo, resultado e fonte de consumo registrados;
- 100% das ausências de consumo representadas explicitamente como indisponíveis, sem confundir com zero;
- 100% dos descendentes históricos conhecidos retornados sem ciclo ou dupla contagem, com itens sem registro sinalizados;
- operador responder quantidade, duração, consumo, resultados e repetições de uma raiz em até 5 minutos sem abrir logs individuais;
- baseline publicado ao final da janela para falha terminal, repetição sem avanço, cobertura de consumo e consumo/duração por etapa.

A aferição cabe ao operador designado pela organização que executar a esteira; não há hoje responsável nominal, prazo externo ou OKR formal. A janela começa quando a capacidade estiver disponível para uso. ROI monetário não será prometido antes do baseline e de uma regra auditável de conversão.
