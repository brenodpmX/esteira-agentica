# Test Cases

## Utilidade

Define os casos de teste derivados dos critérios de aceitação de uma task. Serve como contrato entre QA e engenharia — o que será validado após a implementação.

## Layout de Documentação

```markdown
# Casos de Teste — <título da task>

Status: draft | approved | deprecated
Owner: quality
Last updated: YYYY-MM-DD

## Inputs
- <task relacionada>
- <user story relacionada>

## CT-001 — <título>

**Tipo:** unitário | integração | E2E
**Critério de aceitação:** <referência>

**Pré-condição:**
- ...

**Passos:**
1. ...

**Resultado esperado:**
- ...
```

## Caminho do Arquivo

`doc/quality/<slug-story>/test-cases-<slug-task>.md`
