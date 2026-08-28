# Vision — Integridade de issues entre boards

Status: draft — recomendação de aprovação negocial
Owner: product
Last updated: 2026-08-26

## Inputs
- Issue #230 e histórico da entrevista com o dono.
- Timeline e estado das issues #221–#223, #226–#229 e #231–#240, consultados pela API do GitHub em 2026-08-26.
- Logs de execução em `/app/logs/<issue>/` para #221, #222, #223, #226, #232 e #235.
- PR #102, issue #88, commit homologado `a00ba7c` e documentação em `doc/incidente/sub-issues-propagadas/`.
- [GitHub Docs — Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues).
- [GitHub Docs — About Projects](https://docs.github.com/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects).

## Problema
Ao estabelecer uma relação pai/filho entre issues que pertencem a boards distintos, o GitHub adiciona automaticamente a filha ao Project do pai. A esteira não está eliminando essa participação não intencional antes de torná-la elegível naquele fluxo. Como consequência, a mesma issue pode receber coluna e agente incompatíveis com seu tipo, consumir créditos, alterar seu conteúdo e até originar trabalho sem fundamento.

A recorrência é posterior ao merge da correção do incidente #88: nas 17 relações observadas em 25 e 26/08/2026, todas as filhas foram adicionadas ao board do pai e depois removidas manualmente. Seis issues dispararam sete execuções no board errado; cinco dessas execuções registraram consumo total de 20,35 créditos e duas terminaram em erro sem consumo registrado.

## Solução
Entregar integridade operacional de ponta a ponta: uma issue deve ser processada somente nos boards cuja participação seja intencional, e a associação automática decorrente de uma relação pai/filho deve ser neutralizada antes de qualquer execução indevida. A entrega deve preservar a hierarquia pai/filho e continuar compatível com participação multi-board explicitamente intencional, ainda que o dono não tenha hoje um caso de uso para ela.

A solução de negócio inclui contenção temporária, prevenção, detecção, evidência de resultado e tratamento dos resíduos da janela do incidente. A escolha de tecnologia e arquitetura pertence às etapas técnicas posteriores.

## Público-alvo
- Dono e operadores da esteira, responsáveis por priorização, custo e limpeza operacional.
- Agentes e equipes que dependem de cada board representar um tipo e um fluxo de trabalho confiáveis.
- Usuários que usam hierarquia de issues para decompor épicos, stories e tasks sem misturar seus processos.

## Proposta de valor
Restabelecer confiança no board como fronteira de execução: cada agente recebe apenas trabalho do fluxo que lhe corresponde, sem perder a hierarquia nativa do GitHub. O retorno imediato é evitar créditos desperdiçados, retrabalho manual e cascatas de issues indevidas; o retorno estrutural é permitir que a automação cresça sem ampliar o risco de “delírio” entre níveis de trabalho.

## Métricas de sucesso
- **Zero execução em board errado** durante 30 dias após a disponibilização da correção.
- **100% das participações não intencionais reconciliadas antes de receber Status executável**, medidas pela timeline do GitHub e pelos logs da esteira.
- **Zero remoção manual** de item propagado no período de observação.
- **Zero resíduo local ou remoto novo** causado por propagação entre boards.
- **100% das relações pai/filho válidas preservadas** e nenhuma participação multi-board explicitamente autorizada removida.
- A janela de aceite deve conter ao menos **17 novas relações entre boards**, igual à amostra observada; se o volume em 30 dias for menor, a observação continua até atingir 17.
- Créditos evitados medidos por `execuções indevidas impedidas × consumo médio observado`. O baseline mínimo comprovado é 20,35 créditos em cinco execuções concluídas, além de duas tentativas com erro.

## Decisão recomendada
**Aprovar o problema e o resultado de negócio**, não uma implementação específica. A recorrência e o custo foram comprovados depois do merge do PR #102. A entrega só pode ser considerada concluída com evidência no runtime e na janela de sucesso; presença do código em `main`, isoladamente, não constitui resultado.
