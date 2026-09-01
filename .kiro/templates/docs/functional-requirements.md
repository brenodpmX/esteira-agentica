# Functional Requirements

## Utilidade

O que o sistema deve fazer, no nível do épico: requisitos funcionais rastreáveis, atores, dados e fluxos. Base para UX, arquitetura e a quebra em stories. Cada requisito é testável isoladamente.

## Layout de Documentação

```markdown
# Requisitos Funcionais — <épico>
Status: draft | approved | deprecated · Owner: requirements · Updated: YYYY-MM-DD
Inputs: <artefatos usados>

## Atores
- <ator/persona>: <papel/objetivo no sistema>

## Dados
- <entidade>: <descrição, atributos-chave, restrições>

## Requisitos
### RF-001 — <título>
- Descrição: <o sistema deve...; uma capacidade>
- Ator: <quem dispara>
- Pré-condição: <estado necessário>
- Fluxo principal: <passos do caminho feliz>
- Alternativos/exceções: <desvios e tratamento>
- Critérios de aceitação:
  - Dado <contexto>, quando <ação>, então <resultado>
- Fonte: <artefato de negócio> · Regras: <RN-XXX aplicáveis>
```

## Caminho do Arquivo

`doc/requirements/<slug-epic>/functional-requirements.md`
