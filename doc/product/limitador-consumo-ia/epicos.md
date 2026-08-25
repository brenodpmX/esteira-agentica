# Épicos — Limitador de consumo de IA

Status: draft — recomendado para aprovação de negócio
Owner: product
Last updated: 2026-08-25

## Inputs
- Issue #177 "Limitador de consumo de IA" e histórico da entrevista com o dono
- `doc/product/limitador-consumo-ia/vision.md`
- `doc/product/limitador-consumo-ia/problem-space.md`

## Épico: Política de consumo por pipe e plataforma

**Objetivo:** permitir que o cliente defina quanto cada combinação
pipe/plataforma pode consumir em cada período, sem a esteira escolher
prioridades em seu lugar.

**Escopo:**
- política opcional e independente por combinação pipe/plataforma;
- limites diário, semanal e mensal configuráveis, isolados ou combinados;
- qualquer limite aplicável atingido impede a próxima execução apenas naquela
  combinação;
- reset diário à meia-noite, semanal no dia escolhido e mensal no dia escolhido;
- fuso configurável, com uso do fuso local da máquina quando omitido;
- ausência de política preserva o comportamento vigente;
- reset, aumento ou desativação do limite torna a combinação elegível novamente.

**Fora de escopo:**
- definir automaticamente prioridades ou cotas;
- garantir que a soma das cotas caiba no contrato;
- administrar orçamento, overage, add-ons ou contrato do provedor;
- coordenar cotas entre instalações que não compartilham o mesmo controle;
- dashboard ou recomendação automática de limites.

## Épico: Consumo reconhecido e fidelidade da unidade

**Objetivo:** basear a decisão no consumo informado pela plataforma e tornar
clara a unidade que fundamentou o bloqueio.

**Escopo:**
- consumo associado à combinação pipe/plataforma;
- uso da unidade autoritativa da plataforma, como créditos no Kiro;
- distinção entre consumo zero e consumo indisponível;
- continuidade quando a medição estiver indisponível, com registro explícito;
- apuração separada para cada janela configurada;
- ausência de conversão implícita entre tokens, créditos, requisições e moeda.

**Fora de escopo:**
- estimar consumo ausente;
- criar taxa de conversão sem fonte auditável;
- somar ou comparar economicamente unidades de plataformas diferentes;
- decidir contratos técnicos, armazenamento ou arquitetura dos adaptadores.

## Épico: Bloqueio localizado, continuidade e explicação

**Objetivo:** impedir consumo adicional reconhecidamente fora da política sem
interromper outras combinações elegíveis.

**Escopo:**
- impedir o acionamento quando o consumo reconhecido estiver maior ou igual a
  qualquer limite aplicável;
- permitir que execução já iniciada termine, mesmo que ultrapasse o limite;
- registrar cada tentativa impedida no controle de execuções;
- emitir warning em terminal e arquivo com pipe, plataforma, unidade, consumo,
  limite, período e condição de retomada;
- manter outra plataforma da mesma pipe e outras pipes elegíveis em execução;
- retomar após reset, aumento ou desativação do limite.

**Fora de escopo:**
- interromper execução em andamento;
- prometer teto absoluto ou ausência de excedente;
- bloquear a pipe inteira, toda a plataforma ou toda a conta por uma cota local;
- definir o comportamento do circuit breaker do épico #175.

## Épico: Aferição e decisão de continuidade

**Objetivo:** produzir evidência para decidir se o controle gera valor e deve
ser mantido, ajustado ou retirado.

**Escopo:**
- acompanhar tentativas impedidas, excedente, medição indisponível, falsos
  bloqueios, tempo de retomada e impacto em trabalho prioritário;
- verificar que outras combinações elegíveis continuam operando;
- publicar baseline ao fim do primeiro ciclo completo;
- exigir que o implantador designe o responsável pela aferição antes de ativar a
  política;
- revisar o controle a partir do baseline, sem presumir economia monetária.

**Fora de escopo:**
- atribuir consumo ou economia à tentativa que não foi executada;
- calcular ROI sem tarifa contratual e causalidade comprovadas;
- criar stories ou estimativas nesta etapa.

## Critérios transversais para derivação posterior

1. Sem política, a execução mantém o comportamento atual.
2. Qualquer limite aplicável atingido bloqueia somente a combinação
   pipe/plataforma correspondente.
3. A última execução iniciada abaixo do limite pode excedê-lo; o excedente é
   medido e a próxima tentativa é impedida.
4. Consumo indisponível não equivale a zero, fica visível e não bloqueia.
5. Outra plataforma da mesma pipe e outras pipes elegíveis continuam operando.
6. Cada bloqueio é explicável e auditável nas saídas acordadas.
7. Unidades diferentes não são convertidas ou somadas sem regra auditável.
8. O fuso configurado governa todas as fronteiras; sem ele, vale o fuso local da
   máquina.
9. O implantador designa quem publica e revisa o baseline do primeiro ciclo.

## Gate

A diligência recomenda **aprovar**. Não há pergunta de negócio pendente. Após a
aprovação humana, os blocos podem seguir para planejamento e derivação posterior
sem antecipar tecnologia, arquitetura ou stories nesta etapa.
