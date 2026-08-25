# Non-Functional Requirements

## Utilidade

Atributos de qualidade do sistema, mensuráveis. Input para arquitetura e critério de validação para QA. Sem número/unidade/condição, não é NFR.

## Layout de Documentação

```markdown
# Requisitos Não-Funcionais — <épico>
Status: draft | approved | deprecated · Owner: requirements · Updated: YYYY-MM-DD
Inputs: <artefatos usados>

| ID | Atributo | Requisito (mensurável) | Como medir |
|----|----------|------------------------|-----------|
| NFR-001 | Performance | <ex.: p95 < 300ms sob <condição>> | <método/fonte> |
| NFR-002 | Segurança | ... | ... |
| NFR-003 | Escalabilidade | ... | ... |
| NFR-004 | Disponibilidade | ... | ... |

Atributos conforme o caso: performance, segurança, escalabilidade,
disponibilidade, usabilidade, observabilidade, conformidade, portabilidade.
```

## Caminho do Arquivo

`doc/requirements/<slug-epic>/non-functional-requirements.md`
