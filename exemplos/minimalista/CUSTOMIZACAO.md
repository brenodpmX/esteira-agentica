# Customização do exemplo Minimalista (cenário hipotético)

> Cenário hipotético: nenhum dado real. Ajuste apenas os valores listados como substituíveis.

## Valores substituíveis

- `git.repo.main`: repositório do seu GitHub Project de teste.
- `boards.exemplo.columns.execucao.target-prompt`: instrução dada ao agente na coluna Execução.
- `agents.kiro-cli.dev.model`: modelo usado pelo agente.

## Configuração fixa

- `boards.exemplo.columns.execucao.agent`
- `boards.exemplo.columns.execucao.change.advance`
- `boards.exemplo.columns.final.archive`
- `git.flow.feature.branch_pattern`

## Ajuste de exemplo

O ajuste abaixo é coberto: após aplicá-lo, o resultado observável continua sendo produzido.

<!-- ajuste-testavel -->
```yaml
caminho: boards.exemplo.columns.execucao.target-prompt
novo_valor: Leia a issue, escreva no comentário da issue um resumo de duas linhas do que foi pedido e avance a issue.
```
