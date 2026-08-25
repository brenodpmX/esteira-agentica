# Épicos — Limitador de consumo de IA

Status: draft — blocos propostos para aprovação condicionada
Owner: product
Last updated: 2026-08-24

## Inputs
- Issue #177 "Limitador de consumo de IA" e histórico da entrevista com o dono
- `doc/product/limitador-consumo-ia/vision.md`
- `doc/product/limitador-consumo-ia/problem-space.md`

## Épico: Política de consumo por pipe e plataforma

**Objetivo:** permitir que o cliente expresse quanto uma pipe pode consumir em
cada plataforma e período, sem a esteira escolher prioridades em seu lugar.

**Escopo:**
- política opcional por pipe e plataforma;
- limites diário, semanal e mensal configuráveis, separadamente ou em conjunto;
- qualquer limite aplicável atingido torna a pipe inelegível para nova execução;
- reset diário na virada do dia, semanal no dia escolhido e mensal no dia
  escolhido, todos governados por um fuso ainda pendente de decisão;
- ausência de política preserva o comportamento vigente;
- alteração ou desativação da política pode tornar a pipe elegível novamente.

**Fora de escopo:**
- definição automática de prioridades ou cotas;
- validação de que a soma das cotas cabe no contrato do cliente;
- administração de orçamento, overage, compra de add-ons ou contrato do provedor;
- dashboard e recomendação automática de limites.

## Épico: Consumo reconhecido e transparência da unidade

**Objetivo:** basear a política no consumo efetivamente informado pela plataforma
e tornar confiável o entendimento da decisão.

**Escopo:**
- consumo associado à pipe e à plataforma na unidade autoritativa reportada;
- apresentação do termo da plataforma, como créditos no Kiro;
- distinção explícita entre consumo zero e consumo indisponível;
- continuidade da execução quando a medição estiver indisponível, com registro do
  fato;
- acompanhamento de consumo por pipe e por janela configurada;
- proibição de conversão implícita entre tokens, créditos, requisições e moeda.

**Fora de escopo:**
- estimar consumo ausente;
- criar taxa de conversão sem fonte auditável;
- padronizar economicamente unidades de plataformas diferentes;
- decidir tecnologia, armazenamento ou contrato técnico dos adaptadores.

## Épico: Bloqueio, continuidade e aferição

**Objetivo:** impedir consumo adicional reconhecidamente fora da política sem
interromper o restante da esteira e produzir evidência para avaliar o controle.

**Escopo:**
- antes de nova chamada, impedir o agente quando o consumo reconhecido do
  período estiver maior ou igual a qualquer limite aplicável;
- permitir que uma execução já iniciada termine, mesmo que ultrapasse o limite;
- registrar toda tentativa impedida no controle de execuções;
- emitir warning em terminal e arquivo com pipe, plataforma, unidade, consumo,
  limite, período atingido e condição de retomada;
- manter outras pipes elegíveis em execução;
- retomar após reset, aumento ou desativação do limite;
- medir tentativas impedidas, excedente, consumo indisponível, falsos bloqueios,
  tempo de retomada e impacto em trabalho prioritário;
- publicar baseline ao fim do primeiro ciclo e decidir manter, ajustar ou
  retirar o controle.

**Fora de escopo:**
- interromper uma execução em andamento;
- prometer teto absoluto ou ausência de excedente;
- bloquear toda a plataforma ou todas as pipes por uma única pipe;
- definir o comportamento do circuit breaker do épico #175;
- criar stories nesta etapa.

## Critérios transversais para derivação posterior

1. Sem política, a execução mantém o comportamento atual.
2. Se qualquer limite aplicável estiver atingido, nenhuma nova chamada do agente
   ocorre para aquela pipe.
3. A última execução iniciada abaixo do limite pode excedê-lo; o excedente é
   medido e a próxima tentativa é bloqueada.
4. Consumo indisponível não equivale a zero, fica visível e não bloqueia.
5. Uma pipe bloqueada não impede outras pipes elegíveis.
6. Cada bloqueio é explicável e auditável nas saídas acordadas.
7. Unidades diferentes não são somadas ou convertidas sem regra e fonte
   auditáveis.
8. Os resets só podem ser aceitos depois de definido o fuso aplicável.

## Gate

Não derivar stories nem avançar para aprovação enquanto o dono não confirmar:

- o fuso usado nas fronteiras diária, semanal e mensal;
- o responsável por publicar e revisar o baseline do primeiro ciclo.
