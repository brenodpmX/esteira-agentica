# Problem Space — Limitador de consumo de IA

Status: diligência em andamento — aguardando decisões do dono
Owner: product
Last updated: 2026-08-22

## Contexto e evidências

O dono descreveu um cenário preventivo: várias pipes podem usar a mesma conta do
Kiro, mas deveriam receber parcelas diferentes da capacidade conforme a
prioridade escolhida pelo cliente. Também citou o desejo de distribuir consumo ao
longo do mês. Não houve incidente, gasto inesperado ou atraso medido, e não há
baseline ou OKR.

A hipótese foi confrontada com fatos:

- o Kiro comercializa créditos mensais fracionários; tokens não são sua unidade
  econômica pública;
- os planos públicos incluem de 50 a 10.000 créditos, conforme a faixa;
- o saldo do plano reinicia no ciclo mensal e créditos mensais não acumulam;
- planos pagos permitem add-ons a US$ 0,04/crédito; ao esgotar todos os créditos,
  o uso pausa até compra ou renovação;
- o Kiro alerta em 80% do consumo, mas o controle é da conta, sem evidência
  pública de alocação por pipe;
- a versão usada pela esteira termina execuções com resumo de créditos e duração,
  fato também levantado na diligência da issue #176;
- hoje `call_agent` inicia o agente sem uma decisão de orçamento por pipe;
- o circuito da issue #175 limita repetição de uma issue, não o consumo agregado
  de todas as issues de uma pipe.

## Dor e trabalho a realizar

Quando diversas pipes compartilham capacidade, o operador precisa reservar mais
consumo para umas do que para outras ou cadenciar a franquia no tempo. O saldo e
o alerta nativos informam a conta inteira; não impedem uma pipe de consumir a
parcela informalmente reservada a outra.

O trabalho de negócio é: **definir uma cota por pipe, acompanhar o consumo na
unidade realmente reportada e impedir novas execuções quando a cota reconhecida
for alcançada, sem o produto decidir a prioridade do cliente**.

## Hipóteses ainda não comprovadas

- frequência com que múltiplas pipes realmente disputam a mesma conta;
- créditos hoje consumidos por pipe e dispersão entre pipes;
- quantidade de add-ons, pausas ou atrasos que o controle evitaria;
- correlação entre prioridade declarada e impacto econômico;
- tolerância do cliente a bloqueio incorreto ou a excedente de uma execução.

A ausência de incidente não invalida um controle preventivo, mas impede afirmar
ROI ou urgência com números. A primeira aferição deve formar o baseline.

## Mercado e alternativas

### 1. Controles nativos do Kiro

O dashboard informa usados, restantes e limite mensal; o alerta de 80% antecipa
o esgotamento; a própria conta pausa quando o saldo acaba. É a alternativa de
menor esforço e deve continuar sendo usada, mas não distribui capacidade entre
pipes nem preserva uma reserva por prioridade.

### 2. Medir e alertar por pipe, sem bloquear

A issue #176 pode consolidar créditos por execução e pipe. Essa alternativa cria
baseline e reduz risco de falso bloqueio, porém depende de ação humana e não
contém consumo entre a detecção e a intervenção.

### 3. Limite por pipe sobre consumo reconhecido

É o recorte candidato: política opcional, cota definida pelo cliente e impedimento
de nova execução após atingir o valor reconhecido. Resolve a distribuição local,
mas não controla o saldo real da conta, não coordena automaticamente várias
instalações e pode ultrapassar a cota pela última execução já iniciada.

### 4. Separar contas ou assinaturas

Isola franquias no provedor, quando permitido e economicamente adequado. Aumenta
custo e operação e não atende quem legitimamente executa várias pipes sob a mesma
identidade. A decisão pertence ao cliente.

### 5. Limitar tokens

Não recomendada para o Kiro enquanto não houver fonte autoritativa e regra de
correspondência com créditos. Tokens, créditos e custo não são intercambiáveis.

### Referência de outro fornecedor

A OpenAI distingue alerta de gasto e limite rígido por organização/projeto. Sua
documentação também explicita que a aplicação não é instantânea e pode haver
pequeno excedente. Isso valida como padrão de mercado a separação entre
**observar**, **alertar** e **interromper**, além da necessidade de declarar a
tolerância de enforcement; não determina a solução desta esteira.

## Custo de não fazer

Sem o épico, o Kiro ainda impedirá consumo depois do esgotamento da conta, mas a
primeira pipe a consumir continuará usando capacidade sem respeitar a reserva
pretendida para outras. Os impactos possíveis são:

- pausa de trabalho prioritário até renovação ou compra de créditos;
- compra evitável de add-ons para repor capacidade consumida por pipe menos
  prioritária;
- interrupções manuais para vigiar e parar pipes;
- ausência de evidência para ajustar cotas futuras.

O custo só deve ser monetizado com dados reais:

`custo evitável = créditos adicionais atribuíveis ao excesso × tarifa contratual`

`impacto operacional = horas de trabalho prioritário atrasadas × custo/hora aceito`

Não há valores para preencher as fórmulas. Na oferta pública aplicável, add-ons
custam US$ 0,04/crédito; isso não transforma automaticamente créditos incluídos
no plano em economia financeira.

## Riscos de produto

- **Falsa precisão:** chamar token de custo ou converter unidade sem prova.
- **Excedente inevitável:** consumo conhecido apenas depois da execução pode
  superar a cota.
- **Subcontagem:** falhas ou saídas sem resumo podem consumir capacidade sem
  medição local.
- **Bloqueio prolongado:** ciclo/reset mal definido pode impedir trabalho válido.
- **Fragmentação:** cotas independentes não garantem que a soma caiba no saldo da
  conta compartilhada.
- **Dependência circular:** tentativas bloqueadas podem alimentar o circuit-break
  #175; o comportamento precisa ser compreensível para o operador.

## Ordem de esforço relativa

1. **Usar controles nativos — XS:** já disponível; não resolve rateio por pipe.
2. **Medir e alertar — S/M:** forma baseline, mas não garante contenção; converge
   com #176.
3. **Cota mensal por pipe + bloqueio e explicação — M:** menor recorte que atende
   a dor comprovada, desde que o dono aceite consumo reconhecido e excedente.
4. **Múltiplas janelas, reservas, exceções e políticas segmentadas — L:** sem
   evidência nesta etapa.
5. **Coordenação global entre instalações/contas/plataformas — XL:** não requerida
   e fora do primeiro corte.

As classificações são comparativas de negócio, não estimativas técnicas.

## Gate de decisão

Recomendar aprovação somente após o dono confirmar:

1. unidade e tratamento de consumo indisponível/falhas;
2. semântica do teto e tolerância ao excedente da última execução;
3. ciclo, reset e fuso;
4. abrangência de plataforma do primeiro corte;
5. metas de 30 dias, responsável pela aferição e aceite explícito de avançar sem
   baseline/OKR histórico.

Até lá, manter `need_human` e não criar stories.

## Fontes

- [Kiro — Pricing](https://kiro.dev/pricing/)
- [Kiro — Billing](https://kiro.dev/docs/billing/)
- [Kiro — Usage beyond plan limits](https://kiro.dev/docs/billing/add-on-credits/)
- [Kiro — Managing proactive usage notifications](https://kiro.dev/docs/billing/proactive-usage-notifications/)
- [OpenAI — Spend limits](https://developers.openai.com/api/docs/guides/spend-limits)
- Issues internas #175, #176 e #177.

Conteúdo externo parafraseado para conformidade com restrições de licenciamento.
