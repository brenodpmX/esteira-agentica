# Decisão arquitetural — destino do conteúdo divergente da hotfix27

**Data:** 2026-08-04
**Issue:** #125 — Decidir destino do conteúdo divergente da branch hotfix27
**Origem:** `epic`
**Branch da decisão:** `temp-hotfix27-merge`
**Status:** Decidido — recriar correção mínima sobre `epic`

## Contexto

A task #86 pretendia remover a branch órfã
`hotfix27-27-log_nao_descritivo`, assumindo que seu conteúdo já havia sido
absorvido pelo `epic`. A absorção foi parcial: o commit `6587e2c` adicionou
título e coluna ao resumo de execução, mas o formato atual em
`src/adapters/kiro_cli_agent.py` ainda interpola ambos incondicionalmente:

```python
f'[{params.board_id}] #{params.issue_id} "{params.title}" '
f'@ {params.col_name} agent=...'
```

`AgentParams.title` e `AgentParams.col_name` têm valor padrão vazio. Além
disso, `call_agent` pode produzir título vazio quando o body não existe ou a
primeira linha está vazia, e uma coluna pode ter `name` vazio. Logo, o estado
atual ainda pode gerar saídas poluídas como:

```text
[task] #5 "" @  agent='...'
```

A hotfix evita o problema montando os segmentos de título e coluna somente
quando há valor:

```python
title_str = f' "{params.title}"' if params.title else ""
col_str = f" @ {params.col_name}" if params.col_name else ""
```

## Evidências avaliadas

- `origin/epic..origin/hotfix27-27-log_nao_descritivo` contém atualmente 11
  commits exclusivos, incluindo mudanças e documentação de outros incidentes.
- A branch também está atrás do `epic` em funcionalidades recentes; portanto,
  suas histórias divergiram nas duas direções.
- O commit relevante da hotfix é `3640ffc` (`Execução de tratamento: Log não
  descritivo`), mas ele também altera extração de título e estruturas já
  evoluídas no `epic`.
- A suíte existente (`tests/test_agent_log_descritivo.py`) verifica que campos
  vazios não causam exceção, porém não exige a ausência de `""` e `@` sem
  conteúdo. Assim, o defeito de apresentação permanece sem teste de regressão
  preciso.

## Decisão

Escolhida a **opção (a): recriar a correção mínima em uma nova task, partindo
do `epic` atual**.

Não será feito merge nem cherry-pick de commits da hotfix27. A implementação
deve transportar a intenção — segmentos condicionais no resumo — e não o
histórico da branch. Isso preserva as evoluções já consolidadas no `epic`,
reduz o risco de regressão e produz um diff pequeno e auditável.

A correção é técnica e não depende de definição de produto ou UX: quando um
campo opcional não possui valor, seu delimitador visual também deve ser
omitido. Quando ambos existem, o formato homologado permanece inalterado.

## Escopo da task de implementação

1. Em `KiroCliAgent.execute`, montar os segmentos de título e coluna
   condicionalmente.
2. Manter inalterado o formato completo quando ambos estão preenchidos:
   `#<id> "<título>" @ <coluna> agent=...`.
3. Adicionar testes de saída exata para quatro combinações:
   - título e coluna preenchidos;
   - apenas título preenchido;
   - apenas coluna preenchida;
   - ambos vazios.
4. Não trazer alterações de `src/__main__.py`, `src/core/agent.py`, docs ou
   commits alheios a partir da hotfix27.

## Critérios de aceite

- O resumo não contém `""` quando `title` está vazio.
- O resumo não contém `@` sem nome quando `col_name` está vazio.
- Board, número da issue, agente e caminho do log continuam presentes.
- O formato homologado para campos preenchidos não muda.
- Testes direcionados e suíte relacionada passam sobre o `epic` vigente.

## Destino da branch antiga

A branch `hotfix27-27-log_nao_descritivo` deve ser **preservada até a task de
implementação ser integrada ao `epic`**. A nova task bloqueia a #86 para que a
remoção não ocorra antes disso.

Após a integração:

1. verificar a presença dos segmentos condicionais e dos testes no `epic`;
2. confirmar que nenhum outro conteúdo exclusivo da hotfix foi aprovado para
   transporte;
3. remover a branch remota hotfix27 como resíduo histórico.

## Consequências

- **Positivas:** correção pequena, sem importar histórico defasado; risco baixo;
  intenção da hotfix preservada; critério objetivo para remoção posterior.
- **Custo:** uma task curta adicional e manutenção temporária da branch antiga.
- **Risco residual:** remover a hotfix antes da integração perderia a única
  referência remota da correção; mitigado pelo bloqueio explícito da #86.
