# Customização do exemplo de Referência (cenário hipotético)

> Cenário hipotético: nenhum dado real. Ajuste apenas os valores listados como substituíveis.

## Valores substituíveis

- `git.repo.main`: repositório do seu GitHub Project de teste.
- `boards.exemplo.columns.planejamento.target-prompt`: instrução dada ao Planejador na coluna Planejamento.
- `boards.exemplo.columns.desenvolvimento.target-prompt`: instrução dada ao Desenvolvedor na coluna Desenvolvimento.
- `agents.kiro-cli.revisor.model`: modelo usado pelo Revisor.

## Configuração fixa

- `boards.exemplo.columns.planejamento.change.advance`
- `boards.exemplo.columns.desenvolvimento.change.advance`
- `boards.exemplo.columns.desenvolvimento.gitevents`
- `boards.exemplo.columns.revisao.gitevents`
- `boards.exemplo.columns.revisao.change.advance`
- `boards.exemplo.columns.final.archive`
- `git.flow.feature.branch_pattern`

## Ajuste de exemplo

O ajuste abaixo é coberto: após aplicá-lo, o resultado observável continua sendo produzido.

<!-- ajuste-testavel -->
```yaml
caminho: boards.exemplo.columns.planejamento.target-prompt
novo_valor: Leia a issue, escreva no corpo um plano de até cinco linhas com escopo e critérios de aceitação e avance a issue.
```
