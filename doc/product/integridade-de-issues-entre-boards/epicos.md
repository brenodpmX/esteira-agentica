# Épicos — Integridade de issues entre boards

Status: draft — recomendação de aprovação negocial
Owner: product
Last updated: 2026-08-26

## Inputs
- `doc/product/integridade-de-issues-entre-boards/vision.md`
- `doc/product/integridade-de-issues-entre-boards/problem-space.md`
- Issue #230 e histórico da entrevista com o dono.
- Evidências remotas e logs das issues #221–#240.

> Estes são blocos de entrega para delimitar o épico #230; não representam novas issues ou stories criadas nesta análise.

## Épico: Contenção e prova de operação

**Objetivo:** interromper o desperdício enquanto se comprova qual versão está efetivamente em execução e se preserva evidência suficiente para validar a causa.

**Escopo:**
- Registrar ambiente, versão/commit e data do artefato em execução.
- Adotar a contingência temporária aprovada pelo dono caso novas relações continuem expondo issues a boards errados.
- Identificar e isolar participações não intencionais ainda ativas.
- Manter inventário de execuções, créditos e remoções da janela do incidente.

**Fora de escopo:**
- Escolher mecanismo técnico de implantação ou detecção.
- Desabilitar permanentemente relações pai/filho.
- Tratar pares de issues duplicadas sem relação pai/filho, como #204/#210 a #208/#214.

## Épico: Integridade preventiva entre boards

**Objetivo:** garantir que uma issue só seja processada no fluxo em que sua participação é intencional, preservando hierarquia e usos multi-board deliberados.

**Escopo:**
- Impedir despacho de agente no board propagado indevidamente.
- Reconciliar a participação automática sem exigir remoção manual.
- Preservar o board intencional e a relação pai/filho.
- Preservar participação multi-board quando houver autorização explícita.
- Cobrir stories propagadas para Epics e tasks propagadas para User Stories.

**Fora de escopo:**
- Definir arquitetura, APIs, classes ou estratégia de persistência.
- Unificar boards ou redesenhar os fluxos de épico, story e task.
- Criar novos níveis de hierarquia.
- Solucionar duplicação de entidades sem relação com propagação entre Projects.

## Épico: Evidência de resultado e encerramento do incidente

**Objetivo:** demonstrar que a integridade foi restaurada em uso real e que o ganho operacional é sustentado.

**Escopo:**
- Observar 30 dias e pelo menos 17 novas relações entre boards.
- Medir participações não intencionais, tempo até reconciliação, despachos errados, créditos e remoções manuais.
- Confirmar zero nova execução no board errado e zero resíduo novo.
- Confirmar preservação de todas as relações válidas e participações autorizadas.
- Tratar resíduos conhecidos da janela de 25–26/08 sem contabilizá-los como regressão nova.

**Fora de escopo:**
- Declarar sucesso apenas por merge, teste automatizado ou presença do código em `main`.
- Estimar retorno financeiro sem preço real por crédito e horas de limpeza medidas.
- Encerrar outros incidentes ou débitos apenas por proximidade temática.

## Gate de aprovação
O épico pode seguir para aprovação negocial porque dor, recorrência, impacto mínimo, alternativas, ordem e métricas estão comprovados. A aprovação deve ser do resultado acima, mantendo decisões tecnológicas para arquitetura e exigindo evidência do runtime antes de declarar a entrega concluída.
