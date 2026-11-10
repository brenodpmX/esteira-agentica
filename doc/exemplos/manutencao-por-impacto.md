# Manutenção dos exemplos por impacto

## Regra

Toda mudança do produto que alcance a etapa de documentação deve avaliar se afeta algum exemplo publicado. A avaliação é obrigatória e gera um registro.

- Se a mudança afeta um exemplo: o exemplo deve ser atualizado e revalidado (novo registro de validação interna com sucesso) antes do release em que a mudança entra em produção.
- Se não afeta: registra-se a ausência de impacto, com a justificativa.

Exemplo desatualizado por mudança não avaliada é falha de processo, não comportamento aceitável.

Esta é uma regra de processo, não automação: nenhuma configuração de coluna dispara a avaliação automaticamente.

## Formato do registro de impacto

Salvo em `doc/exemplos/registros/impacto/`, uma linha `chave: valor` por campo:

```
mudanca: <identificação da mudança do produto>
afeta_exemplo: <sim | nao>
exemplos_afetados: <exemplos ou nenhum>
acao: <o que foi atualizado, ou justificativa da ausência de impacto>
revalidacao: <caminho do registro de validação, obrigatório quando afeta_exemplo é sim>
```
