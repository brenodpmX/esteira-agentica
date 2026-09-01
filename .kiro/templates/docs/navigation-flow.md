# Navigation Flow

## Utilidade

Define o fluxo de navegação de uma feature: telas mapeadas, transições entre elas, estados e decisões de UX. Serve como referência para arquitetura, engenharia e QA validarem a experiência antes da implementação.

## Layout de Documentação

```markdown
# Fluxo de Navegação — <nome da feature>

Status: draft | approved | deprecated
Owner: ux
Last updated: YYYY-MM-DD

## Inputs
- <user stories utilizadas>

## Telas mapeadas
1. <nome da tela>
2. ...

## Fluxo — <contexto>
<tela origem>
  → (<ação>)    → <tela destino>
  → (<ação>)    → <tela destino>

## Estados
| Tela | Loading | Erro | Vazio |
|------|---------|------|-------|
| ...  | ...     | ...  | ...   |

## Decisões de UX
- <decisão>: <justificativa>

## Dúvidas em aberto
- <dúvida> (ou "Nenhuma.")
```

## Caminho do Arquivo

`doc/ux/<slug-story>/navigation-flow.md`
