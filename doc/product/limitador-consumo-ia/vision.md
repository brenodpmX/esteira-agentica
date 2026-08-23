# Vision — Limitador de consumo de IA

Status: diligência em andamento — aguardando decisões do dono
Owner: product
Last updated: 2026-08-22

## Visão

Permitir que quem opera mais de uma pipe sobre a mesma capacidade de IA distribua
essa capacidade de forma previsível entre as pipes, preservando maior parcela
para trabalhos prioritários e evitando que uma pipe consuma silenciosamente a
franquia compartilhada.

## Inputs

- Issue #177 "Limitador de consumo de IA" e entrevista registrada no histórico.
- Issue #176 "Registro de execução de agentes".
- Issue #175 "Circuit-break de agente".
- Saída observada do Kiro CLI e comportamento atual de `call_agent`.
- Documentação oficial de cobrança, créditos e alertas do Kiro.
- Documentação oficial de limites de gasto da OpenAI como referência de mercado.

## Público-alvo

Pessoa ou organização que configura e opera uma ou mais instâncias da esteira e
compartilha uma conta ou franquia de IA entre elas. O cliente continua responsável
por definir orçamento, prioridade, tolerância a interrupção e soma das cotas.

## Problema validado

O Kiro controla consumo no nível da conta: publica saldo mensal, alerta em 80% e
interrompe uso quando os créditos disponíveis acabam. Esse controle não distribui
a franquia entre pipes. Assim, uma pipe de menor prioridade pode consumir a
capacidade que o operador pretendia reservar a outra.

Não houve incidente nem perda quantificada. A demanda é preventiva, originada da
observação de uso contínuo. Portanto, ainda não existe baseline que permita
estimar frequência, economia ou ROI monetário.

## Proposta de valor

Transformar uma franquia compartilhada em cotas explícitas por pipe, decididas
pelo cliente. Pipes prioritárias podem receber cotas maiores; pipes sem política
mantêm o comportamento atual. Ao reconhecer que uma cota foi alcançada, a
esteira deixa de iniciar novas execuções naquela pipe e explica a decisão.

O produto não escolherá prioridades, comprará créditos, administrará overage nem
garantirá que a soma das cotas corresponda ao contrato do cliente.

## Unidade econômica

Para o Kiro, a unidade contratada é **crédito fracionário**, não token. Créditos
variam com complexidade e modelo, são medidos a 0,01 e renovam a cada ciclo
mensal. Tokens só poderão aparecer como dimensão adicional se uma fonte os
expuser explicitamente; não serão convertidos em créditos ou moeda por hipótese.

A versão do Kiro observada reporta créditos e duração ao fim de execuções, mas a
exposição pública do provedor é agregada e atualizada periodicamente. O limite
só pode prometer controle sobre consumo reconhecido; a tolerância ao atraso e a
dados indisponíveis permanece pendente de decisão do dono.

## Resultado de negócio pretendido

- consumo de cada pipe comparável à cota configurada para seu ciclo;
- nenhuma nova execução iniciada depois que a pipe reconhecer ter atingido a
  cota;
- capacidade preservada para pipes às quais o cliente atribuiu cotas maiores;
- toda tentativa impedida com motivo, consumo reconhecido, cota e ciclo visíveis;
- comportamento atual preservado quando não houver política configurada.

## Retorno e como medir

O retorno inicial é redução de exposição e previsibilidade, não economia já
comprovada. Medir por ciclo e por pipe:

1. créditos consumidos versus cota configurada;
2. execuções e créditos evitados depois do bloqueio;
3. excedente sobre a cota causado pela última execução aceita ou por atraso da
   fonte;
4. quantidade de bloqueios, falsos bloqueios e tempo até retomada;
5. trabalhos prioritários atrasados por esgotamento da conta compartilhada;
6. créditos adicionais evitáveis, quando aplicável, valorizados pela tarifa
   contratual verificável.

A tarifa pública atual de add-on do Kiro é US$ 0,04 por crédito, mas créditos do
plano são capacidade já contratada e não devem ser tratados como economia em
caixa. Uma meta e uma janela de avaliação ainda precisam ser aceitas pelo dono.

## Aderência a metas e políticas

Não há OKR, meta quantitativa, política de FinOps ou orçamento formal informado.
A proposta é coerente com previsibilidade de consumo, isolamento de impacto e
controle pelo cliente, mas isso é uma hipótese de aderência — não substitui uma
meta aprovada. O dono deve decidir se o caráter preventivo justifica avançar sem
ROI histórico e aceitar os indicadores de sucesso.

## Decisões pendentes

- aceitar créditos como unidade autoritativa inicial e definir o tratamento de
  consumo ausente ou de execução com falha;
- aceitar que uma execução já iniciada pode fazer a cota ultrapassar o teto;
- definir ciclo, reinício e fuso da cota, sem inventar necessidade diária ou
  semanal;
- confirmar se o primeiro corte é Kiro ou uma regra multiplataforma condicionada
  a unidade reportada;
- aprovar metas, horizonte de aferição e prioridade em relação ao registro #176.

Sem essas decisões, a visão não está apta à aprovação.
