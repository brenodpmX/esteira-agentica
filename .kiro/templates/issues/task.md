# Task

## Utilidade

Define uma unidade mínima de trabalho executável pela engenharia. Contém escopo, critério de aceite e classificação de effort para determinar o nível de modelo a ser utilizado na implementação.

## Layout de Issue

```markdown
# <título da task>

effort: low | medium | high

## User Story
<referência à story relacionada>

## Descrição
<o que deve ser feito — objetivo e direto>

## Escopo técnico
<o que está incluso>

## Fora de escopo
<limites claros>

## Critério de aceite
- Implementação segue arquitetura
- Código cobre cenário descrito
- Testes unitários criados
- Sem quebra de funcionalidades existentes

## Referências (obrigatório)
- **Branch desta issue**: `<branch>` — branch vinculada a esta task. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #<id> — <nome da story>   (a story que originou esta task)
- **Branch da issue pai**: `<branch-pai>`   (branch da story)

<adicionar tags aqui>
```

## Board

`task` — coluna `backlog`
