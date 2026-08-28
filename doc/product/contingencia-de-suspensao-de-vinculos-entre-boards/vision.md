# Vision — Contingência de suspensão de vínculos entre boards

Status: draft — recomendação de aprovação negocial
Owner: product
Last updated: 2026-08-27

## Inputs
- Issue #241 — Contingência de suspensão de vínculos entre boards.
- Issue pai #230 e histórico da entrevista com o dono em 26/08/2026.
- Documentação de negócio aprovada do épico #230 em `doc/product/integridade-de-issues-entre-boards/`, consultada na branch `epic230-230-integridade_de_issues_entre_boards`.
- [GitHub Docs — Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues).
- [LaunchDarkly Docs — Kill switch flags](https://launchdarkly.com/docs/eu-docs/home/flags/killswitch).
- [Atlassian Support — Link work items](https://support.atlassian.com/jira-software-cloud/docs/link-issues/).

## Problema
Enquanto a prevenção definitiva de participações indevidas entre boards não está disponível no ambiente operacional, cada novo vínculo pai/filho entre boards distintos mantém aberta a fonte do incidente comprovado no épico #230. Na amostra de 25–26/08/2026, 17 de 17 vínculos propagaram a filha ao board do pai, 17 exigiram remoção manual e seis issues receberam sete despachos no fluxo errado. Cinco execuções concluídas consumiram 20,35 créditos; duas falharam sem consumo registrado.

A operação precisa conter novas exposições sem interromper toda a esteira, sem apagar hierarquias existentes e sem impedir relações internas ao mesmo board.

## Solução
Oferecer ao operador um controle temporário, reversível e auditável que suspenda somente a criação de novos vínculos pai/filho entre boards distintos. A proteção deve poder entrar e sair de vigor durante a operação, sem restart ou novo deploy. Vínculos anteriores e vínculos dentro do mesmo board permanecem intactos. Tentativas recusadas não ficam pendentes para execução automática posterior.

Esta visão define o comportamento e os limites de negócio. Mecanismo de configuração, componentes e arquitetura não são decididos neste artefato.

## Público-alvo
- Operador e dono da esteira, responsáveis por conter incidentes e autorizar a retomada.
- Times e agentes que dependem de cada board como fronteira confiável de execução.
- Usuários que precisam preservar hierarquias já estabelecidas durante a contingência.

## Proposta de valor
Reduzir imediatamente o raio de exposição do incidente com impacto mínimo: novos vínculos de risco são interrompidos, mas o restante da automação e a hierarquia existente continuam disponíveis. A contingência compra tempo seguro para a entrega definitiva sem converter limpeza manual em processo permanente.

## Métricas de sucesso
- 100% das novas tentativas de vínculo entre boards distintos recusadas e registradas enquanto a suspensão estiver ativa.
- Zero execução em board errado originada por vínculo solicitado após a ativação.
- Zero vínculo pai/filho preexistente removido ou alterado pela contingência.
- 100% das tentativas de vínculo dentro do mesmo board processadas normalmente.
- Ativação e desativação efetivas durante a operação, sem restart ou novo deploy.
- Zero vínculo recusado reproduzido automaticamente após a reativação.
- Retorno apurado por despachos, créditos e remoções manuais evitados; conversão monetária somente quando houver preço por crédito e tempo operacional medido.

## Decisão recomendada
**Aprovar como contenção temporária e primeira entrega do épico #230.** A dor, o custo mínimo e a autorização do dono já foram validados. A aprovação não substitui a prevenção definitiva nem autoriza decisões de tecnologia nesta etapa.
