# Epic

## Utilidade

Solicitação de origem humana que inicia o ciclo completo da esteira. É o nível mais alto de trabalho — acima de user stories. Passa por análise de negócio, planejamento, implementação e publicação.

## Layout de Issue

```markdown
# <título do épico>

## Descrição
<o que o humano precisa>

## Contexto
<por que este épico existe>

## Resultado esperado
<o que se espera ao final>

## Referências (obrigatório)
- **Branch desta issue**: `<branch>` — branch vinculada a este épico. Todo agente que atuar nesta issue DEVE trabalhar nesta branch; não crie nem use outra.
- **Issue pai**: #<id> — <nome da issue pai>   (use "nenhuma" quando for um épico de origem humana sem pai; preencha quando o épico nascer de outra issue, ex.: Post Mortem originado de incidente)
- **Branch da issue pai**: `<branch-pai>`   (use "nenhuma" quando não houver issue pai)

<adicionar tags aqui>
```

## Board

`epic` — coluna `backlog`
