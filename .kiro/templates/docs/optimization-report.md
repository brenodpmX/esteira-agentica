# Optimization Report

## Utilidade

Documenta análise de desempenho da esteira com evidências e problemas identificados. Após gerar o relatório, o optimizer aplica as melhorias diretamente nos agentes e prompts.

## Layout de Documentação

```markdown
# Relatório de Otimização — <referência épico>

Owner: optimizer
Date: YYYY-MM-DD

## Dados analisados
- Período: ...
- Execuções: ...
- Issues processadas: ...

## Problemas identificados

### 1. <título>
**Evidência:** ...
**Impacto:** ...
**Melhoria proposta:** ...

## Alterações aplicadas
- <arquivo alterado> — <o que mudou>
- ...

## Agentes por custo
| Agente | Tokens | Observação |
|--------|--------|------------|
| ... | ... | ... |
```

## Caminho do Arquivo

`doc/optimization/report-<slug-epic>.md`
