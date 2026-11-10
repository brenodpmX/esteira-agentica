# Validação interna dos exemplos

Cenários hipotéticos: nenhum registro contém dado real.

## Regra

Cada exemplo (`minimalista` e `referencia-hipotetica`) é validado por uma pessoa interna que usa somente o `USO.md` do próprio exemplo, sem recorrer a conhecimento não documentado da implementação.

Se o validador precisar de qualquer informação fora do `USO.md` para concluir o ciclo, isso é uma lacuna de documentação e conta como falha do exemplo: corrige-se a documentação e a validação é repetida.

Falha por pré-requisito de ambiente já declarado no `USO.md` não conta como falha do exemplo, mas também gera registro, indicando o pré-requisito faltante.

Toda execução, com sucesso ou com falha, gera um registro em `doc/exemplos/registros/validacao/<exemplo>-<AAAA-MM-DD>-<n>.md`.

Nenhuma apresentação de um exemplo acontece antes de existir um registro de validação com sucesso daquele exemplo.

## Formato do registro

Uma linha `chave: valor` por campo, no início da linha:

```
exemplo: <minimalista | referencia-hipotetica>
data: <AAAA-MM-DD>
versao_suportada: <versão da Esteira>
resultado: <sucesso | falha>
ponto_da_falha: <obrigatório quando falha; n/a quando sucesso>
ajuda_necessaria: <descrição ou nenhuma>
tempo_observado: <duração>
falhas: <lista ou nenhuma>
duvidas: <lista ou nenhuma>
qualidade_vs_objetivo: <avaliação contra o objetivo declarado do exemplo>
modelo: <modelo usado ou n/a>
tokens: <observado no cenário ou n/a>
custo: <observado no cenário ou n/a>
cenario: <identificação do cenário hipotético>
```

## Regras de preenchimento

- `tokens` e `custo` só são informados junto de `modelo`, `cenario` e `versao_suportada`; nunca são apresentados como valor típico ou universal.
- O resultado é avaliado contra o objetivo declarado em `exemplo.yml`, sem meta numérica de conversão, adoção ou retorno.
- Valores de `pipe.yml` e dos contextos publicados não são alterados para fazer a validação passar.
