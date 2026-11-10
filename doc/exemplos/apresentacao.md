# Apresentação dos exemplos

Cenários hipotéticos: nenhum registro contém dado real.

## Pré-condição

Só se apresenta um exemplo que já tenha ao menos um registro de validação interna com sucesso, de data igual ou anterior à da apresentação (veja `validacao-interna.md`).

## Roteiro

1. Contextualize: a Esteira executa agentes de IA sobre um board, processando issues por coluna.
2. Apresente o objetivo, o público e o caso de uso do exemplo, lendo o `exemplo.yml`.
3. Mostre o `pipe.yml` e os contextos de agente, separando valores substituíveis de configuração fixa.
4. Mostre a issue de exemplo entrando na coluna de entrada e o resultado observável esperado.
5. Declare os limites do exemplo e que o cenário é hipotético.
6. Peça ao público que diga com as próprias palavras o que entendeu, sem correção do apresentador.
7. Peça uma decisão explícita e registre o resultado.

## Formato do registro

Salvo em `doc/exemplos/registros/apresentacao/<exemplo>-<AAAA-MM-DD>-<n>.md`, uma linha `chave: valor` por campo:

```
exemplo: <minimalista | referencia-hipotetica>
data: <AAAA-MM-DD>
compreensao_observada: <o que o público entendeu, sem correção do apresentador>
decisao: <interesse | recusa | pendente>
objecoes: <ao menos uma quando decisao é recusa>
proximo_passo: <acordado, ou acompanhamento agendado quando pendente>
```

## Regras

- A decisão é `interesse`, `recusa` ou `pendente`.
- Recusa exige ao menos uma objeção registrada.
- Decisão `pendente` exige `proximo_passo` com acompanhamento agendado; ausência de decisão nunca é tratada como interesse.
- Opinião ou visualização genérica não substitui a decisão explícita.
- Não há meta numérica de conversão, adoção ou retorno: o aprendizado é qualitativo e não se generaliza como taxa.
