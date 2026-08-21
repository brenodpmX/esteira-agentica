# Análise de negócio — limitador de consumo de tokens

**Data:** 2026-08-21  
**Issue:** #177 — Limitador de consumo de tokens  
**Etapa:** Análise de Negócio  
**Responsável:** Helena Costa — Product Manager  
**Status:** diligência em andamento; aguardando evidências do dono

## Conclusão executiva

**Recomendação atual: não aprovar nem recusar ainda.** A intenção de controlar
consumo é coerente com governança de custo e continuidade operacional, mas o
épico chegou prescrevendo configuração e persistência sem demonstrar a dor, o
baseline, a meta ou o retorno.

Há ainda uma divergência central a resolver: o Kiro atualmente mede o serviço em
**créditos fracionários**, cujo consumo depende da complexidade e do modelo, e
não em tokens. Os planos renovam a franquia no ciclo mensal e capacidade
adicional custa US$ 0,04 por crédito nos planos pagos. Assim, limitar tokens pode
não limitar a unidade faturada nem o custo. A aprovação depende de confirmar
qual plataforma/contrato gera a dor e qual unidade é auditável e economicamente
relevante.

## Problema e hipótese de valor

**Hipótese de dor:** execuções automatizadas podem consumir capacidade ou gerar
cobrança adicional sem um guardrail definido, reduzindo previsibilidade
financeira e podendo esgotar a franquia antes do fim do ciclo.

**Públicos potencialmente afetados:** dono do orçamento, operação da esteira e
times que dependem das entregas dos agentes.

**Valor esperado, ainda não comprovado:** reduzir consumo excedente não
planejado sem interromper trabalho prioritário. Para Kiro, bloquear uso dentro
da franquia já contratada não gera economia marginal por si só; o benefício pode
ser preservar capacidade até o fim do ciclo. Economia direta só existe se evitar
add-ons, overage ou upgrade que de fato ocorreriam.

## Evidências disponíveis

### Internas

- O body original descreve limites diário, semanal e mensal e bloqueio antes da
  execução, mas não apresenta incidente, série histórica, fatura, frequência de
  estouro, impacto ou meta.
- O histórico da issue está vazio em 21/08/2026.
- O repositório documenta que falhas repetidas já podem queimar quota e possui
  `rerun_cooldown`; isso comprova preocupação com desperdício, mas não comprova
  que o problema financeiro ou de capacidade atual exija um novo limitador.
- Não foi encontrada documentação interna com baseline de tokens, créditos,
  custo por execução ou estouros de franquia.

### Mercado e alternativas

1. **Controle nativo do Kiro.** O Kiro vende franquias mensais em créditos,
   atualiza o uso no dashboard ao menos a cada cinco minutos, renova a franquia
   no ciclo de cobrança e permite add-ons nos planos pagos. É a alternativa de
   menor esforço se o objetivo for apenas impedir gasto adicional, desde que o
   contrato e a configuração reais confirmem que overage/compra automática não
   ocorrerão.
2. **Controle nativo do provedor por gasto.** A OpenAI oferece alertas e hard
   limits mensais por organização/projeto. Ao atingir um hard limit, requisições
   falham; a própria documentação alerta que a aplicação não é instantânea e
   pode haver pequeno excedente. Isso mostra que alertar antes de bloquear e
   definir impacto operacional são práticas essenciais.
3. **Gateway/controle intermediário.** O LiteLLM oferece budgets por diferentes
   escopos e janelas, inclusive janelas simultâneas, mas exige infraestrutura e
   contabilização confiáveis para enforcement. É benchmark de mercado, não uma
   recomendação arquitetural.
4. **Observabilidade sem bloqueio.** Medir unidade faturável, emitir alertas e
   revisar o limite manualmente preserva continuidade, mas não contém sozinho
   um runaway entre detecção e ação.
5. **Não construir.** Usar franquia e controles nativos evita custo de produto e
   manutenção. É preferível se não houver overage involuntário, incidente ou
   escassez de capacidade durante o ciclo.

## Custo de não fazer

Ainda não é possível monetizar. Devem ser separados:

- **custo incremental evitável:** add-ons, overage ou upgrade causado por
  automação excedente;
- **custo de capacidade:** trabalho prioritário atrasado porque a franquia foi
  consumida cedo;
- **custo operacional:** tempo de diagnóstico, retomada e replanejamento;
- **risco de bloqueio indevido:** entregas atrasadas por um teto mal calibrado.

Cálculo mínimo proposto por ciclo:

`custo evitável = gasto excedente atribuível à esteira + horas de recuperação × custo-hora`

No Kiro, quando aplicável:

`gasto excedente = créditos adicionais evitáveis × US$ 0,04`

Sem volumes históricos e impacto, qualquer valor seria especulativo.

## Retorno e como medir

### Baseline necessário

Observar no mínimo 30 dias ou dois ciclos representativos, conforme volume,
segmentando por plataforma/modelo/agente:

- unidade faturável consumida e custo;
- franquia, overage/add-ons e data de esgotamento;
- execuções iniciadas, concluídas, falhas e reexecuções;
- consumo por entrega concluída;
- horas de indisponibilidade ou trabalho prioritário adiado.

### Indicadores de resultado

- **Primário:** gasto adicional não planejado por ciclo.
- **Guardrail:** entregas prioritárias atrasadas por falta de capacidade ou por
  bloqueio do controle.
- **Eficiência:** unidade faturável por execução concluída.
- **Adoção/operabilidade:** alertas acionáveis, tempo até resposta e quantidade
  de liberações manuais.
- **Qualidade do controle:** excedente após o teto e falsos bloqueios.

### Critério econômico proposto

`ROI = (custo evitado + custo operacional evitado − custo total da solução) / custo total da solução`

O dono deve definir horizonte, retorno mínimo e tolerância a interrupção. Sem
isso, não há base para aprovar investimento.

## Ordem de esforço relativo

Estimativa de negócio, sujeita a discovery técnico posterior:

1. **Muito baixo:** manter controles/franquia nativos e desabilitar overage,
   caso o contrato permita e isso resolva a dor.
2. **Baixo:** visibilidade e alertas sobre a unidade faturável já disponível.
3. **Médio:** bloqueio mensal em um único escopo com política operacional clara.
4. **Alto:** múltiplas janelas simultâneas, múltiplas plataformas, concorrência,
   exceções e retomada segura.

A proposta original está no quarto patamar sem evidência de que os patamares
anteriores sejam insuficientes.

## Aderência a metas e políticas

**Aderência potencial:** previsibilidade de gasto, uso responsável de IA e
continuidade da esteira.

**Não comprovado:** nenhuma meta/OKR, teto orçamentário, política FinOps ou
exigência de compliance foi vinculada à issue.

**Guardrails de negócio necessários:**

- nenhuma credencial, prompt ou conteúdo de issue em telemetria financeira;
- acesso ao consumo limitado a perfis autorizados;
- aviso antes de interrupção quando a operação admitir;
- procedimento e responsável para exceção/retomada;
- trilha auditável de alteração dos limites;
- comportamento explícito quando medição estiver indisponível.

## Perguntas de diligência ao dono

1. Qual incidente ou dado originou o pedido? Informar período, plataforma,
   franquia/contrato, consumo esperado versus realizado, gasto adicional e
   impacto operacional.
2. O objetivo primário é conter gasto, preservar franquia/capacidade, detectar
   runaway ou atender política? Qual meta mensurável e prazo?
3. A unidade faturada é token, crédito, requisição ou moeda? Onde o valor oficial
   pode ser consultado por execução e com qual atraso/precisão?
4. Há overage/compra automática habilitada? Qual teto aprovado e quem é o dono
   do orçamento?
5. Quais execuções podem ser interrompidas? Existe prioridade, reserva crítica,
   exceção emergencial ou obrigação de disponibilidade?
6. Por que são necessárias janelas diária e semanal além do ciclo mensal? Há
   evidência de picos que essas janelas evitariam?
7. Ao atingir o limiar, o resultado desejado é alertar, bloquear novas
   execuções, concluir as já iniciadas ou exigir liberação humana?
8. Quais metas/OKRs e políticas de custo, segurança, retenção e auditoria este
   épico deve atender? Qual retorno mínimo justifica construí-lo?

## Gate de decisão

### Aprovar somente se

- baseline e impacto demonstrarem perda relevante;
- unidade controlada corresponder à unidade de custo/capacidade real;
- meta, owner, horizonte e retorno mínimo estiverem definidos;
- alternativa nativa de menor esforço for insuficiente;
- política de bloqueio e guardrails de continuidade forem aceitos;
- medição de sucesso puder ser feita sem expor conteúdo sensível.

### Recusar ou reformular se

- o contrato já impedir gasto adicional e não houver escassez operacional;
- tokens não tiverem correlação auditável com crédito/custo;
- o custo total superar a perda evitável;
- não houver owner para limite e exceções;
- o bloqueio criar risco maior que o desperdício observado.

## Fontes externas

- [Kiro — Pricing](https://kiro.dev/pricing/)
- [Kiro — Billing](https://kiro.dev/docs/billing/)
- [OpenAI — Spend limits](https://developers.openai.com/api/docs/guides/spend-limits)
- [LiteLLM — Budgets, Rate Limits](https://docs.litellm.ai/docs/proxy/users)

Conteúdo externo resumido e reformulado para conformidade com restrições de
licenciamento. Consulta realizada em 21/08/2026.
