# Vision — Limitador de consumo de IA

Status: draft — aprovação condicionada a decisões do dono
Owner: product
Last updated: 2026-08-24

## Inputs
- Issue #177 "Limitador de consumo de IA" e seu histórico até a resposta do dono
  registrada em 25/08/2026
- `src/adapters/kiro_cli_agent.py` (evidência de que a saída final da execução é
  registrada, mas ainda não constitui contrato de medição)
- [Kiro Pricing](https://kiro.dev/pricing/)
- [Kiro Billing](https://kiro.dev/docs/billing/)
- [OpenAI Spend limits](https://developers.openai.com/api/docs/guides/spend-limits)

## Problema

Várias pipes podem consumir uma mesma capacidade contratada de IA. Hoje, o
cliente não consegue reservar parcelas diferentes dessa capacidade para cada
pipe. Uma pipe de menor prioridade pode, portanto, consumir a franquia que o
cliente pretendia preservar para trabalho prioritário.

A dor é preventiva: o dono confirmou que não houve incidente, gasto adicional
medido, baseline ou OKR formal. O valor não deve ser apresentado como economia
já comprovada, mas como controle de alocação e redução de risco a validar no
primeiro ciclo de uso.

## Solução

Oferecer uma política opcional de consumo por pipe e por plataforma, com limites
diário, semanal e mensal configuráveis. Cada limite configurado é independente;
ao atingir qualquer um deles, uma nova execução daquela pipe é impedida antes
de acionar o agente. Execuções já iniciadas terminam e podem ultrapassar o teto;
o bloqueio passa a valer para a próxima tentativa.

A unidade exibida e contabilizada deve ser a unidade autoritativa informada pela
plataforma — créditos no Kiro. Não haverá conversão presumida entre tokens,
créditos ou moeda. Quando a plataforma não informar consumo, a execução continua
e a ausência de medição fica explícita, pois zero e indisponível são estados
diferentes.

A solução não escolhe prioridades: o cliente expressa sua política por meio dos
limites. Pipes sem política mantêm o comportamento atual, e uma pipe bloqueada
não impede a execução das demais.

## Público-alvo

Operadores da esteira que compartilham uma conta ou capacidade de IA entre duas
ou mais pipes e precisam reservar consumo para cargas com prioridades ou ritmos
diferentes.

## Proposta de valor

Dar ao cliente controle previsível e auditável sobre quanto cada pipe pode
consumir em diferentes janelas de tempo, sem substituir os controles contratuais
do provedor e sem interromper as demais pipes elegíveis.

## Métricas de sucesso

No primeiro ciclo completo após disponibilização:

- 100% das tentativas feitas quando o consumo reconhecido estiver maior ou igual
  a qualquer limite aplicável são impedidas antes de acionar o agente;
- 100% dos bloqueios explicam pipe, plataforma, consumo reconhecido, unidade,
  limite, período atingido e condição de retomada;
- zero acionamentos do agente após uma decisão de bloqueio e zero bloqueios em
  pipes sem política;
- zero impacto de uma pipe bloqueada sobre outras pipes elegíveis;
- excedente entre limite e consumo final da última execução iniciado abaixo do
  teto é medido, sem promessa de teto absoluto;
- execuções com consumo indisponível são contabilizadas separadamente de consumo
  zero;
- tentativas impedidas, falsos bloqueios, tempo de retomada e trabalho
  prioritário atrasado por esgotamento da conta são acompanhados;
- ao fim do primeiro ciclo, é publicado um baseline de consumo por pipe, consumo
  impedido e excedente, permitindo decidir manter, ajustar ou retirar o controle.

Não há meta monetária neste momento. Quando houver tarifa contratual comprovada,
o consumo impedido poderá ser valorizado pela tarifa vigente, sem converter
unidades por estimativa.

## Gate de aprovação

A recomendação é **aprovar condicionada**, pois dor, recorte e medição foram
aceitos pelo dono, mas dois elementos necessários à aferição ainda não têm
responsável ou regra definida:

1. qual fuso determina a virada do dia, o início da semana e o reset mensal;
2. quem responde pela publicação e revisão do baseline do primeiro ciclo.

Até a resposta, a issue deve permanecer em Análise de Negócio com `need_human`.
