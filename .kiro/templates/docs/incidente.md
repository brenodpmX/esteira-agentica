# Incidente Produtivo

## Utilidade

Documentação de acompanhamento de Problemas e Incidentes reportados em produção

## Layout de Documentação

```markdown
# Incidente — <nome do incidente>

Status: Triagem | análise | deprecated
Owner: product
Last updated: YYYY-MM-DD

## Registro
> Contém informações preliminares do incidente/problema

### Descrição:
- Data: <Data e hora da ocorrência>
- Reportado por: <Quem reportou>

<Descrição do que foi reportado sobre o incidente>

### Evidências
<Preencher evidências e caso possua arquivos adicionar no mesmo diretório e vincular abaixo>

### Impacto:
<Qual o impacto o incidente traz para o projeto>

## Triagem

### Classificação:
<Classificação do incidente>

### Severidade:
<severidade segundo a classificação>

### Prioridade:
<prioridade>

### Workaround:
<alternativas de workarounds>

## Análise Técnica
<Relatório da análise técnica>

## Decisão de tratamento
<Decisão escolhida>

<motivos que levaram a esta decisão>

## Tarefas de correção
<lista de tarefas abertas para correção>
```

## Classificação de severidade

| Severidade   | Descrição                                    | Exemplo                         |
| ------------ | -------------------------------------------- | ------------------------------- |
| P1 - Crítica | Sistema parado ou perda financeira relevante | Pagamentos indisponíveis        |
| P2 - Alta    | Funcionalidade importante comprometida       | Emissão de boletos falhando     |
| P3 - Média   | Problema com workaround                      | Relatório gera dados incorretos |
| P4 - Baixa   | Problema cosmético                           | Texto errado na tela            |


## Ação proposta
<descrição completa da ação proposta>

## Caminho do Arquivo

`doc/incidente/<slug-incidente>/ticket.md`
