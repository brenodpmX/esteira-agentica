# Problem Space — Limitador de consumo de IA

Status: draft — recomendado para aprovação de negócio
Owner: product
Last updated: 2026-08-25

## Inputs
- Issue #177 "Limitador de consumo de IA" e histórico da entrevista com o dono
- `doc/product/limitador-consumo-ia/vision.md`
- [Kiro Pricing](https://kiro.dev/pricing/)
- [Kiro Billing](https://kiro.dev/docs/billing/)
- [OpenAI Spend limits](https://developers.openai.com/api/docs/guides/spend-limits)

## Contexto

O dono opera várias pipes sobre uma mesma conta do Kiro e quer reservar mais
capacidade para trabalhos prioritários. Uma pipe também pode usar mais de uma
plataforma de IA, cada qual com consumo e cota próprios. Portanto, o objeto do
controle não é a pipe inteira, mas a combinação pipe/plataforma: esgotar a cota
de uma plataforma pode parar algumas colunas, sem impedir outras plataformas da
mesma pipe ou outros trabalhos elegíveis.

Não houve incidente. A demanda nasceu da observação de uso contínuo e também
pode servir a clientes que desejem distribuir capacidade ao longo do mês.

As fontes oficiais consultadas em 25/08/2026 confirmam que o Kiro consome
créditos fracionários por requisição, oferece franquias por plano e renova o
limite no ciclo de cobrança. Planos pagos permitem capacidade adicional; preço
e condições podem mudar e devem ser verificados antes de qualquer cálculo
financeiro. A documentação pública mostra controle e acompanhamento no nível da
conta/plano, mas não demonstrou alocação por pipe.

Como referência de mercado, a OpenAI distingue alertas — que não interrompem
tráfego — de limites rígidos por organização ou projeto. Também informa que a
aplicação do limite não é instantânea e pode haver pequeno excedente. Isso
sustenta separar alerta de bloqueio e não prometer teto absoluto.

## Problemas

- **Disputa por capacidade compartilhada:** consumo menos prioritário pode
  reduzir a capacidade disponível para trabalho prioritário.
- **Falta de isolamento local:** não há política independente para cada
  combinação pipe/plataforma e período.
- **Risco de bloqueio excessivo:** tratar a pipe inteira como esgotada impediria
  plataformas que ainda têm cota.
- **Unidade ambígua:** chamar toda medida externa de token ocultaria unidades
  autoritativas distintas, como créditos no Kiro.
- **Teto não absoluto:** o consumo só é conhecido ao final; a última execução
  iniciada abaixo da cota pode ultrapassá-la.
- **Medição incompleta:** ausência de consumo não equivale a zero e, pela decisão
  do dono, deve operar em falha aberta.
- **Ausência de baseline:** não se conhece a frequência de bloqueios, excedentes,
  falsos bloqueios ou impacto em trabalho prioritário.

## Impacto

### Custo de não fazer

Não há perda histórica quantificada. Permanecem riscos:

- **operacional:** capacidade compartilhada pode se esgotar antes da execução de
  trabalho prioritário;
- **financeiro:** quando houver add-ons ou overage, alocação inadequada pode
  contribuir para compra adicional, sem prova atual de valor evitável;
- **gestão:** o cliente depende de acompanhamento e intervenção manual;
- **continuidade:** sem isolamento, uma reação ampla ao esgotamento pode parar
  plataformas e pipes que ainda poderiam trabalhar.

Eventual estimativa monetária exige `consumo adicional causalmente evitável ×
tarifa contratada`. Tentativas bloqueadas não revelam quanto consumiriam e não
podem ser contabilizadas automaticamente como economia.

### Custo e risco de fazer

O controle adiciona risco de falso bloqueio, fronteira temporal incorreta,
política mal dimensionada e falsa sensação de teto absoluto. Operar em falha
aberta preserva disponibilidade quando não há medição, mas não contém consumo
nesses casos. Esses riscos exigem política opcional, explicação auditável e
primeiro ciclo instrumentado.

## Alternativas e mercado

1. **Usar somente o limite da conta do provedor:** menor esforço, mas atua de
   forma ampla e não reserva capacidade por pipe/plataforma.
2. **Alertar sem bloquear:** melhora visibilidade, porém depende de reação humana
   e não preserva capacidade automaticamente.
3. **Administrar cotas manualmente:** pode atender baixa escala, mas é sujeito a
   erro e não produz uma decisão consistente por tentativa.
4. **Separar contas ou contratos:** cria isolamento mais forte, mas aumenta custo
   e administração e pode não ser permitido pelo provedor.
5. **Aplicar limite local por pipe/plataforma:** atende a granularidade pedida e
   mantém trabalhos elegíveis, com o custo de depender de medição confiável.
6. **Não fazer:** evita complexidade e falsos bloqueios, mas aceita integralmente
   os riscos operacional, financeiro e de gestão descritos.

A alternativa 5 é recomendada porque é opcional, localizada e compatível com o
controle preventivo pedido. Os controles nativos continuam sendo a última linha
de proteção da conta.

## Retorno e como medi-lo

O retorno inicial é preservação de capacidade e continuidade, não ROI monetário
comprovado. A aferição deve acompanhar, por combinação e período:

- consumo reconhecido versus limites configurados;
- tentativas impedidas e motivos;
- excedente da última execução iniciada antes do limite;
- consumo indisponível, falsos bloqueios e tempo até retomada;
- ocorrências de trabalho prioritário atrasado por esgotamento da conta;
- continuidade das demais combinações elegíveis durante um bloqueio.

O primeiro ciclo forma o baseline. O implantador deve designar o responsável
pela publicação e revisão antes de ativar a política. Esse responsável recomenda
manter, ajustar ou retirar o controle. Comparação financeira só deve ocorrer
quando houver tarifa e causalidade comprovadas.

## Aderência a metas e políticas

- **Meta:** o dono aceitou métricas operacionais e avanço preventivo sem
  incidente, baseline ou OKR formal.
- **Autonomia do cliente:** prioridades, cotas, orçamento, overage e contratação
  permanecem sob responsabilidade do cliente.
- **Fidelidade da unidade:** a comunicação usa a unidade da plataforma e não
  presume conversão entre créditos, tokens ou moeda.
- **Disponibilidade:** somente a combinação que atingiu a cota é bloqueada;
  outras combinações elegíveis continuam.
- **Auditabilidade:** decisão, medição indisponível e condição de retomada ficam
  explicáveis em terminal, arquivo e controle de execuções.
- **Falha aberta:** medição indisponível não bloqueia; a indisponibilidade deve
  ser visível para não criar falsa garantia de contenção.
- **Tempo:** o cliente pode configurar o fuso; sem configuração, usa-se o fuso
  local da máquina. Diário vira à meia-noite; semanal e mensal reiniciam nos
  dias escolhidos pelo cliente.
- **Privacidade e retenção:** não foram identificados novos dados pessoais. A
  evidência deve limitar-se a identificadores operacionais, unidade, consumo,
  limite, período e decisão, seguindo as políticas vigentes de logs.

## Ordem de esforço para planejamento

Ordem relativa de negócio, sem estimativa nem decisão de arquitetura:

1. **Contrato da medição:** unidade por plataforma e estados medido, zero e
   indisponível.
2. **Política e períodos:** combinação pipe/plataforma, limites opcionais,
   precedência de qualquer limite atingido, resets e fuso.
3. **Decisão localizada:** impedir a nova chamada e preservar todas as demais
   combinações elegíveis.
4. **Explicação e retomada:** warnings, registro da tentativa, reset, aumento ou
   desativação da cota e excedente da execução anterior.
5. **Aferição:** baseline, falsos bloqueios, indisponibilidade, continuidade e
   revisão pelo responsável designado.

A ordem reduz o risco de aplicar bloqueio sobre medida ou fronteira ambígua. O
tamanho e a viabilidade pertencem ao planejamento posterior.

## Oportunidade

A adoção de agentes aumenta a disputa por capacidade compartilhada. Um controle
opcional e granular permite aprender antes de um incidente e separa claramente
a política do cliente da cobrança do provedor. A diligência sustenta avançar
para aprovação de negócio.

Conteúdo externo foi parafraseado para conformidade com restrições de
licenciamento.
