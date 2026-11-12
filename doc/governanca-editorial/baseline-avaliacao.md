# Baseline e pós-teste de avaliação da documentação pública

Este registro guarda a medição de quanto o público externo consegue concluir,
sem ajuda e sem abrir o código, as três jornadas da porta de entrada:

1. entender valor, capacidades, limites e pré-requisitos do produto;
2. concluir a primeira execução local, com o container como alternativa;
3. localizar a referência de configuração e exemplos suficientes para avaliar
   adoção.

## Regra de aplicação

O baseline e o pós-teste com participantes reais só são executados quando há
participantes confirmados antes do início da etapa de documentação. Sem essa
confirmação, a entrega segue como entrega mínima: README, inventário,
referência de configuração, comunicação de versão, manual de padrões e gate de
revisão constituem a entrega completa, e a decisão de continuidade é registrada
como `sem baseline disponível`.

## Regra de decisão (quando há participantes)

- Pelo menos 4 de 5 participantes concluem as três jornadas sem ajuda e sem
  consultar o código.
- Em relação ao baseline, a taxa de sucesso sem ajuda aumenta e o tempo mediano
  diminui. Quando o baseline já está no teto, basta não haver regressão.
- Atendidas as duas condições, a decisão é `continuar`; caso contrário,
  `interromper`.

Campos do registro com participantes: `baseline_sucesso`,
`baseline_tempo_mediano`, `pos_teste_sucesso`, `pos_teste_tempo_mediano` e
`decisao_continuidade`, mais os registros individuais por participante
(sucesso ou falha por jornada e tempo).

## Registro atual

```text
participantes_confirmados: nao
data_registro: 2026-11-11
decisao_continuidade: sem baseline disponível
```

Não houve participantes confirmados antes do início da etapa de documentação.
Esta entrega é a entrega mínima e não traz medição de baseline nem de
pós-teste.
