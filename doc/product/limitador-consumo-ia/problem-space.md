# Problem Space — Limitador de consumo de IA

Status: draft — diligência concluída com pendências do dono
Owner: product
Last updated: 2026-08-24

## Inputs
- Issue #177 "Limitador de consumo de IA" e histórico da entrevista com o dono
- `doc/product/limitador-consumo-ia/vision.md`
- `src/adapters/kiro_cli_agent.py`
- [Kiro Pricing](https://kiro.dev/pricing/)
- [Kiro Billing](https://kiro.dev/docs/billing/)
- [OpenAI Spend limits](https://developers.openai.com/api/docs/guides/spend-limits)

## Contexto

O dono opera várias pipes sobre uma mesma conta do Kiro e quer distribuir a
capacidade entre elas, reservando mais para as prioritárias e menos para as
demais. Também enxerga o uso de limites para distribuir consumo ao longo do mês.
Não houve incidente: a demanda nasceu da observação de uso contínuo.

A pesquisa oficial confirma que o Kiro mede consumo em **créditos
fracionários**, e não em tokens. Em 24/08/2026, os planos públicos incluíam uma
franquia mensal; planos pagos permitiam add-ons a US$ 0,04 por crédito, e o uso
do plano renovava no ciclo de cobrança. O painel informado pelo provedor podia
ter atraso de atualização. Preço e condições são variáveis de mercado e devem
ser consultados novamente antes de qualquer cálculo financeiro.

O histórico afirma que a execução bem-sucedida da versão usada pela esteira
informa consumo ao final. O código atual registra a última linha significativa
da saída e comenta que ela tipicamente contém tempo e tokens, mas não comprova
um contrato estruturado e estável de medição. Essa disponibilidade precisa ser
validada por plataforma nas etapas técnicas; para negócio, consumo indisponível
não pode ser tratado como zero.

## Problemas

- **Disputa por capacidade compartilhada:** não há reserva por pipe, então uma
  carga pode reduzir a capacidade disponível para outra.
- **Ausência de controle local por janela:** o controle da conta não expressa a
  intenção do cliente por pipe nos recortes diário, semanal e mensal.
- **Unidade ambígua:** chamar toda medida de token ocultaria que o Kiro cobra em
  créditos e que outras plataformas podem usar unidades distintas.
- **Teto não absoluto:** como o custo é conhecido após uma execução, a última
  chamada iniciada abaixo do limite pode terminá-la acima dele.
- **Lacuna de observabilidade:** sem baseline, não se conhece distribuição entre
  pipes, frequência de bloqueio, excedente ou atraso de trabalho prioritário.
- **Fronteira temporal incompleta:** dia, semana e mês não são determinísticos
  sem fuso, apesar de o dono já ter definido os eventos de reset.

## Impacto

### Custo de não fazer

Não há perda histórica quantificada. O risco permanece em três dimensões:

- **operacional:** trabalho prioritário pode parar após consumo da capacidade por
  pipes menos prioritárias;
- **financeira:** o cliente pode comprar capacidade adicional que teria evitado
  com outra alocação, quando add-ons ou overage estiverem habilitados;
- **gestão:** o operador continuará dependendo de acompanhamento e intervenção
  manual para preservar franquia.

Uma estimativa monetária só será válida com evidência contratual:
`consumo adicional evitável × tarifa contratada da unidade`. Não se assume que
todo consumo impedido seria gasto adicional, nem se atribui valor financeiro a
créditos incluídos sem demonstrar custo marginal.

### Custo de fazer

O controle adiciona risco de falso bloqueio, parada por fronteira temporal
incorreta e sensação de proteção absoluta, embora uma execução possa ultrapassar
o teto. Também exige manutenção para cada plataforma cuja medição seja aceita.
Esses custos justificam um primeiro ciclo instrumentado e política opcional.

## Alternativas e mercado

1. **Não fazer e usar somente o saldo do provedor:** menor esforço, mas não
   reserva capacidade por pipe nem expressa prioridades do cliente.
2. **Alertar sem bloquear:** melhora visibilidade e reduz risco de interrupção
   indevida, mas depende de reação humana e não preserva capacidade quando não há
   operador disponível.
3. **Operação manual de cotas:** atende casos pequenos, porém é sujeita a erro,
   não escala e não produz decisão auditável por tentativa.
4. **Separar contas/contratos por pipe:** oferece isolamento forte, mas pode
   elevar custo e esforço administrativo e nem sempre é permitido pelo contrato.
5. **Controle opcional por pipe:** atende o recorte pedido com isolamento lógico,
   desde que a unidade venha da plataforma e a limitação de excedente seja
   comunicada com transparência.

Como referência de mercado, a OpenAI separa alerta de gasto e limite rígido por
projeto e informa que a aplicação de um hard limit não é instantânea, podendo
haver pequeno excedente. Isso corrobora duas regras de negócio: alerta não
substitui bloqueio e um limitador baseado em consumo reconhecido não deve
prometer teto absoluto.

## Retorno e como medi-lo

O retorno inicial é redução de risco e preservação de capacidade, não ROI
monetário já demonstrado. A aferição compara, por pipe e período:

- consumo reconhecido versus limites configurados;
- quantidade de tentativas impedidas e unidade de consumo preservada;
- excedente causado pela última execução iniciada antes do limite;
- consumo indisponível, falsos bloqueios e tempo até retomada;
- ocorrências de trabalho prioritário atrasado por esgotamento da conta;
- impacto — que deve ser zero — sobre outras pipes elegíveis.

O primeiro ciclo forma o baseline. Depois dele, o responsável designado deve
recomendar manter, ajustar ou retirar o controle. Valorização monetária depende
de tarifa e causalidade comprovadas.

## Aderência a metas e políticas

- **Meta:** o dono aceitou as metas operacionais da visão e o avanço preventivo
  sem incidente, baseline ou OKR formal.
- **Autonomia do cliente:** limites e prioridades são decisões do cliente; a
  esteira não administra orçamento, overage ou compra adicional.
- **Fidelidade da unidade:** cada plataforma mantém sua unidade autoritativa;
  não há conversão implícita entre tokens, créditos e moeda.
- **Disponibilidade:** uma pipe bloqueada não interrompe outras elegíveis.
- **Auditabilidade:** decisão de bloqueio e consumo indisponível precisam ser
  distinguíveis e explicáveis em terminal, arquivo e controle de execuções.
- **Falha aberta aceita:** se o consumo não puder ser medido, a execução continua
  e a indisponibilidade é registrada. Essa escolha reduz falso bloqueio, mas não
  garante contenção durante falhas de medição.
- **Segurança e retenção:** não foram identificados novos dados pessoais; a
  telemetria deve limitar-se a identificadores operacionais, unidade, consumo,
  limite, período e decisão, respeitando as políticas já vigentes de logs.

## Ordem de esforço para planejamento

Ordem relativa, sem estimativa e sem decisão de arquitetura:

1. **Contrato de negócio da medição:** identificar, por plataforma, unidade,
   disponibilidade e estados zero/indisponível.
2. **Política e fronteiras de período:** limites opcionais, combinação das
   janelas, eventos de reset e fuso confirmado.
3. **Decisão e explicação do bloqueio:** impedir nova chamada, registrar a
   tentativa e preservar outras pipes.
4. **Retomada e casos de borda:** mudanças de política, reset, excedente da última
   execução, falhas de medição e continuidade operacional.
5. **Aferição do primeiro ciclo:** baseline, falsos bloqueios, excedente e decisão
   de continuidade.

A ordem reduz o risco de construir bloqueio sobre uma medida ou fronteira
ambígua. Tamanho e viabilidade pertencem ao planejamento técnico posterior.

## Oportunidade

A adoção crescente de agentes aumenta a chance de disputa por uma franquia
compartilhada. Um controle opcional agora permite aprender com dados antes de um
incidente e cria uma fronteira explícita entre política do cliente e cobrança do
provedor. A oportunidade é válida, mas a aprovação final depende de definir fuso
e responsável pela aferição.

Conteúdo externo foi parafraseado para conformidade com restrições de
licenciamento.
