# Vision — Limitador de consumo de IA

Status: draft — recomendado para aprovação de negócio
Owner: product
Last updated: 2026-08-25

## Inputs
- Issue #177 "Limitador de consumo de IA" e histórico da entrevista com o dono
- [Kiro Pricing](https://kiro.dev/pricing/)
- [Kiro Billing](https://kiro.dev/docs/billing/)
- [OpenAI Spend limits](https://developers.openai.com/api/docs/guides/spend-limits)

## Problema

Várias pipes — e diferentes plataformas de agente dentro de uma mesma pipe —
podem consumir capacidade de IA compartilhada. Hoje, o cliente não consegue
aplicar cotas independentes à combinação pipe/plataforma. Assim, consumo menos
prioritário pode esgotar capacidade que o cliente pretendia preservar para outro
trabalho, enquanto a falta de isolamento pode interromper mais trabalho do que o
necessário.

A dor é preventiva: o dono confirmou que não houve incidente, perda financeira,
baseline ou OKR formal. O valor deve ser validado como controle de alocação e
redução de risco, sem alegar economia histórica.

## Solução

Permitir uma política opcional de consumo para cada combinação pipe/plataforma,
com limites diário, semanal e mensal independentes e combináveis. Quando o
consumo reconhecido estiver maior ou igual a qualquer limite aplicável, a
próxima tentativa naquela combinação é registrada e explicada, mas o agente não
é acionado.

A execução iniciada abaixo do limite pode terminá-la acima dele; o controle não
promete teto absoluto. Se a medição estiver indisponível, a execução continua e
a indisponibilidade é distinguida de consumo zero.

Cada plataforma mantém a unidade que informa — créditos no Kiro — sem conversão
presumida para tokens ou moeda. O fuso pode ser configurado pelo cliente; sem
configuração, vale o fuso local da máquina. O cliente continua responsável por
prioridades, cotas, orçamento, contratação e pela designação de quem afere o
primeiro ciclo.

O bloqueio é restrito à plataforma cuja cota foi atingida naquela pipe. Outras
plataformas da mesma pipe, bem como outras pipes elegíveis, continuam operando.

## Público-alvo

Operadores da esteira que usam uma ou mais plataformas de IA em múltiplas pipes
e precisam distribuir capacidade entre trabalhos com prioridades ou ritmos
diferentes.

## Proposta de valor

Dar ao cliente controle configurável, localizado e auditável sobre consumo de
IA, preservando a continuidade das combinações pipe/plataforma ainda elegíveis e
sem substituir os controles contratuais do provedor.

## Métricas de sucesso

No primeiro ciclo completo após a ativação:

- 100% das tentativas em que o consumo reconhecido esteja maior ou igual a um
  limite aplicável são impedidas antes do acionamento do agente;
- 100% dos bloqueios informam pipe, plataforma, unidade, consumo, limite,
  período atingido e condição de retomada;
- zero acionamentos após uma decisão de bloqueio e zero bloqueios sem política;
- zero impacto do limite de uma combinação sobre outra combinação elegível,
  inclusive outra plataforma na mesma pipe;
- consumo indisponível fica separado de zero e não gera bloqueio;
- excedente da última execução iniciada antes do limite, falsos bloqueios, tempo
  de retomada, tentativas impedidas e impacto em trabalho prioritário são
  acompanhados;
- o responsável designado pelo implantador publica o baseline ao fim do primeiro
  ciclo e recomenda manter, ajustar ou retirar o controle.

Não há meta monetária. O consumo de uma tentativa impedida é contrafactual e não
será tratado como economia observada; eventual ROI financeiro exigirá tarifa
contratual e causalidade verificáveis.

## Recomendação

**Aprovar.** A dor preventiva, o escopo, as regras de continuidade e a forma de
aferição foram aceitos pelo dono e confrontados com referências de mercado. O
gate seguinte é a aprovação humana de negócio; não restam perguntas abertas de
diligência.
