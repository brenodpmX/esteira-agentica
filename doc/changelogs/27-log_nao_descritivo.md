# Change File — #27: Log não descritivo

**Data:** 2026-08-04
**Issue:** #27 — Log não descritivo
**Branch:** `hotfix27-27-log_nao_descritivo`
**Status:** Homologado

---

## Resumo

O resumo de execução de agentes no terminal passou a identificar a tarefa e a
etapa em processamento. Informações de diagnóstico detalhadas continuam
registradas no arquivo Markdown de cada execução.

## Alterações entregues

### 1. Resumo descritivo no terminal

A linha emitida por `KiroCliAgent.execute` agora apresenta:

```text
[<board>] #<issue> "<título>" @ <etapa> agent='<agente>' log='<arquivo>'
```

Exemplo:

```text
09:47:03 [Agent] [task] #25 "Log não descritivo" @ Análise Técnica agent='Sofia Carvalho - Engenheira de Software PL' log='logs/25/2026-07-20_19-47-03.md'
```

O formato anterior exibia `model` e `cwd`, mas não informava o título nem a
etapa. Esses dois campos foram retirados somente do resumo do terminal para
reduzir ruído operacional.

### 2. Contexto da tarefa no `AgentParams`

`AgentParams` recebeu os campos opcionais `title` e `col_name`. `call_agent`
preenche os valores antes de chamar o adapter:

- `title`: primeira linha do `-body.md`, sem o marcador Markdown; se ela não
  estiver disponível ou estiver vazia, usa o slug do arquivo;
- `col_name`: nome humanizado configurado para a coluna; se não existir, usa o
  `col_id`.

Os campos opcionais preservam a compatibilidade com construções existentes de
`AgentParams` que ainda não os forneçam. Nesses casos, os trechos ausentes são
omitidos do resumo.

### 3. Log detalhado preservado

O arquivo `logs/<issue_id>/<timestamp>.md` continua registrando os parâmetros
completos, incluindo `model` e diretório de trabalho, além de prompt e chat.
Não houve mudança no snapshot, na sincronização, nas sessões ou no fluxo de
git.

## Arquivos da implementação

- `src/core/agent.py`
- `src/__main__.py`
- `src/adapters/kiro_cli_agent.py`

## Documentação

- `README.md`: formato e conteúdo do resumo de terminal;
- `CONTEXT.md`: origem, transporte e fallbacks dos novos campos;
- `doc/homologacao/27-log_nao_descritivo.md`: roteiro e resultado da
  homologação.

## Validação

- Pré-produção: `199 passed, 3 skipped`.
- Configuração do Docker Compose validada sem erros.
- Homologação humana aprovada em 04/08/2026.
