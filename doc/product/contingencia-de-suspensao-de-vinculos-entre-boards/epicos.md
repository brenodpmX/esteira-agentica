# Épicos — Contingência de suspensão de vínculos entre boards

Status: draft — recomendação de aprovação negocial
Owner: product
Last updated: 2026-08-27

## Inputs
- `doc/product/contingencia-de-suspensao-de-vinculos-entre-boards/vision.md`
- `doc/product/contingencia-de-suspensao-de-vinculos-entre-boards/problem-space.md`
- Issue #241 e histórico aprovado do épico pai #230.

> Este documento delimita blocos de valor; não cria stories nem define arquitetura.

## Épico: Suspensão operacional seletiva

**Objetivo:** permitir que o operador interrompa temporariamente novas exposições decorrentes de vínculos pai/filho entre boards distintos, mantendo o restante da esteira e as hierarquias seguras em operação.

**Escopo:**
- Ativar e desativar a suspensão durante a operação, sem restart ou novo deploy.
- Recusar somente novas tentativas de vínculo pai/filho entre boards distintos enquanto a suspensão estiver ativa.
- Registrar cada recusa com evidência suficiente para auditoria e nova submissão consciente.
- Preservar relações dentro do mesmo board.
- Preservar vínculos entre boards estabelecidos antes da ativação.
- Não reproduzir automaticamente pedidos recusados após a desativação.
- Restaurar o comportamento normal imediatamente após a desativação.

**Fora de escopo:**
- Escolher chave, arquivo, mecanismo de recarga, componente, API ou arquitetura.
- Remover ou alterar vínculos já existentes.
- Classificar ou reconciliar participações indevidas.
- Definir a elegibilidade de despacho dos demais fluxos.
- Substituir a prevenção definitiva do épico #230.
- Criar stories nesta etapa.
- Produzir sozinho a evidência de encerramento do incidente completo.

## Critérios negociais de aceite
1. Enquanto a suspensão estiver ativa, toda nova tentativa entre boards distintos é recusada e registrada antes de criar o vínculo.
2. Relações solicitadas dentro do mesmo board continuam disponíveis.
3. Vínculos existentes, inclusive entre boards, permanecem intactos.
4. A decisão passa a valer durante a operação, sem restart ou novo deploy, tanto ao ativar quanto ao desativar.
5. Ao desativar, o fluxo normal é retomado sem executar automaticamente pedidos recusados durante a suspensão.
6. Um estado inválido de controle não pode produzir comportamento ambíguo; a operação deve receber orientação acionável.

## Ordem relativa
**1 de 6 no épico #230.** É a contenção imediata e independente; não elimina nem posterga a obrigação de entregar prevenção, reconciliação, gate de despacho e observabilidade definitivos.

## Gate de aprovação
O bloco está apto à aprovação negocial porque possui dor comprovada, autorização explícita do dono, custo de não fazer, limites, métricas e ordem. A aprovação se refere ao resultado operacional, não a uma implementação específica.
