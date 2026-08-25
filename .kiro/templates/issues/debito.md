# Débito

## Utilidade

Sinalização criada por um agente quando encontra bloqueio, inconsistência ou falta de informação que impede sua continuidade. Quando requer ação humana, deve conter a tag `/need_human` no final do arquivo.

## Layout de Issue

```markdown
# <título do débito>

## Descrição
<o que está inconsistente, faltando ou bloqueando>

## Impacto
<o que fica bloqueado por este débito>

## Origem
<agente e etapa que detectou>

## Resolução sugerida
<ação necessária para resolver>

## Referências (obrigatório)
- **Branch desta issue**: `<branch>` — branch de correção do débito. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #<id> — <nome da issue que originou o débito>   (a issue bloqueada por este débito)
- **Branch da issue pai**: `<branch-pai>`   (branch de origem, sobre a qual a correção é aplicada)

<adicionar tags aqui>
```

## Board

`debito` — abra o débito na coluna do responsável que se entende deve iniciar a correção (`product`, `ux`, `architecture` ou `humano`), conforme o domínio da lacuna. Qualquer coluna de raciocínio também pode escalar para `humano` quando a resolução exigir decisão humana.
