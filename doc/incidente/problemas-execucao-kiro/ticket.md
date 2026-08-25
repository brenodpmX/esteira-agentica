# Incidente — Problemas na execução do kiro (#203)

## Registro

**Incidente ID:** 203
**Status:** Análise técnica concluída — aguardando decisão de tratamento
**Owner:** engenharia
**Data de Abertura:** 2026-08-24 20:38
**Versão em execução:** 1.9.1 (`kiro-cli 2.18.1`)
**Last Updated:** 2026-08-24

### Descrição

Execuções de agente passaram a falhar com frequência em dois projetos distintos
(`esteira-agentica` e `br.com.escrevas`), sempre com o mesmo par de mensagens no
final do output do `kiro-cli`:

```
Kiro is having trouble responding right now:
   0: Failed to receive the next message: request_id: <id>,
      error: dispatch failure (io error): request or response body error
Location:
   crates/chat-cli/src/cli/chat/mod.rs:2213
error: Tool approval required but --no-interactive was specified.
       Use --trust-all-tools to automatically approve tools.
[exit-code: 1]
```

A leitura da linha consolidada no log da esteira sugeria falta da flag
`--trust-all-tools`. A análise técnica descarta essa hipótese.

## Triagem

Registrada no body da issue. Conclusões mantidas: problema confirmado, comum aos
dois projetos, e o adapter já passa `--no-interactive` **e** `--trust-all-tools`
juntos.

Duas hipóteses da triagem foram **descartadas** nesta etapa:

- divergência de versão do `kiro-cli` / `permissions.yaml` com regra `deny` nos
  hosts afetados — a mensagem de aprovação é sintoma secundário, não causa;
- `model: claude-sonnet-4-20250514` — não existe no `pipe.yml` em execução; os
  13 agentes usam modelos válidos. A string só aparece no exemplo do `README.md`.

## Análise técnica

### Evidência analisada

| Fonte | O que foi verificado |
|---|---|
| `logs/2026-08-21.json`, `2026-08-22.json`, `2026-08-24.json` | contagem de execuções, falhas e assinaturas de erro |
| `logs/175/2026-08-24_20-38-06.md` | log completo da falha citada na issue |
| `logs/175/2026-08-24_21-12-44.md` | execução seguinte, concluída, com o mesmo gatilho |
| `logs/91/2026-08-21_11-36-11.md` | segunda ocorrência do erro de aprovação |
| `logs/177/2026-08-22_21-31-32.md` | `dispatch failure` **sem** erro de aprovação (discriminante) |
| `logs/203/2026-08-24_21-39-38.md` | execução da triagem, marcada como falha indevidamente |
| `src/adapters/kiro_cli_agent.py` | montagem do comando e `_detect_failure` |
| `.kiro/agents/pipe_context.json` (repo e `KIRO_HOME`) | conflito de agente |
| `pipe.yml`, `contexts/kiro-cli/*.md` | referências a `.kiro/templates/**` |
| upstream `kirodotdev/Kiro` #6065 | mesmo erro, mesmo modo de uso |

Os diretórios `/home/breno/pipes/*` citados na issue são do host do relator e não
são acessíveis deste ambiente. A análise foi feita sobre os logs equivalentes da
própria esteira, que reproduzem o mesmo padrão — inclusive a execução exata
(`logs/175/2026-08-24_20-38-06.md`) anexada à issue.

### Causa

Não é uma causa única. São **cinco defeitos independentes** que se somam; um é a
causa da interrupção, outro é a causa da leitura errada do sintoma, e três
ampliam a exposição.

**D1 — Causa da interrupção (upstream, transitória).**
O `kiro-cli` aborta o turno quando o corpo da requisição/resposta em streaming
quebra (`dispatch failure (io error): request or response body error`). É bug
conhecido do upstream — [Kiro #6065](https://github.com/kirodotdev/Kiro/issues/6065),
**fechado como "not planned"** — reportado exatamente no mesmo modo de uso desta
esteira: `chat --no-interactive --trust-all-tools` em loop autônomo, em container
Linux, com correlação a saídas de ferramenta grandes e sequências longas de
tool calls. O `kiro-cli` **não** faz retry automático. O perfil da esteira
(execuções de 4 a 7 minutos, dezenas de tool calls por turno) é o pior caso
descrito no report. Não há correção upstream a esperar.

**D2 — `Tool approval required` é sintoma secundário, não a causa.**
Evidência direta, no mesmo arquivo de log e poucas linhas antes do erro:

```
All tools are now trusted (!). Kiro will execute tools without asking for confirmation.
```

Ou seja, `--trust-all-tools` foi aceito e aplicado. O adapter monta as duas flags
juntas (`src/adapters/kiro_cli_agent.py:91-92`) e a combinação foi validada neste
ambiente. O que ocorre é: o turno aborta por D1 com um `tool_use` pendente; na
saída, o `kiro-cli` cai no caminho de aprovação desse tool pendente e, sob
`--no-interactive`, encerra com exit 1 e essa mensagem. As duas mensagens são
**consecutivas e independentes** no output bruto; a linha do console as junta com
` | ` porque `_detect_failure` concatena as linhas relevantes.

Discriminante que confirma a ordem causal: `logs/177/2026-08-22_21-31-32.md` tem
`dispatch failure` **sem** o erro de aprovação (nenhum tool pendente no momento
do abort), e `logs/91/2026-08-21_11-36-11.md` tem o erro de aprovação após um
abort por `InternalServerError` — transporte diferente, mesmo sintoma final. A
mensagem de aprovação, portanto, acompanha o abort, não a ausência da flag.

**D3 — Amplificador: `.kiro/templates/**` referenciado e inexistente.**
`pipe.yml` (`target-prompt`) e `contexts/kiro-cli/*.md` mandam os agentes se
basearem em modelos sob `.kiro/templates/docs/` e `.kiro/templates/issues/` —
cerca de 20 referências. **O diretório não existe:** não está versionado
(`git ls-files | grep template` → vazio) nem presente no filesystem. O efeito em
cada execução afetada:

```
Tool validation failed:
Failed to validate tool parameters: Directory not found: /app/.kiro/templates/docs
Tool 'shell' execution skipped due to validation failures in other tools
Tool 'read' execution skipped due to validation failures in other tools
```

O `kiro-cli` valida o lote de tool calls em bloco: um parâmetro inválido
**cancela todas as ferramentas do lote**, inclusive as válidas. Isso aparece em
18 dos arquivos de log de agente. Cada lote perdido é um turno extra, mais
tráfego e mais tempo de execução — exatamente as condições que o report upstream
associa ao D1. Não é a causa do abort, mas alarga a janela de exposição e
desperdiça crédito por conta própria.

**D4 — Amplificador: conflito de agente `pipe_context`.**
Todos os logs registram:

```
WARNING: Agent conflict for pipe_context. Using workspace version.
```

Existem duas definições do agente: a gerada no startup em
`KIRO_HOME=/app/.kiro/agents/pipe_context.json` (6098 B, regerada a cada boot) e
uma **versionada no repositório** em `.kiro/agents/pipe_context.json` (1778 B,
rastreada pelo git desde `ea25d04`). Como o `kiro-cli` roda com `cwd` no clone, a
versão de workspace vence. A copia versionada está congelada num estado antigo em
que as tabelas de **boards/colunas** e de **git flow** estão **vazias**.

Verificação: o contexto injetado na execução atual traz as seções
"Boards e colunas" e "Git flow e branches" sem nenhuma linha de tabela. Ou seja,
a Correção 2 do incidente "Issue Fantasma" — gerar o contexto a partir do
`pipe.yml` — está **inerte em produção** desde que esse arquivo foi versionado.

**D5 — Falso positivo em `_detect_failure` (métrica não confiável).**
`_detect_failure` varre o **output inteiro**, incluindo a narrativa do próprio
agente. Se o agente escreve sobre um erro, a execução é classificada como falha.
Ocorrência concreta: a execução da triagem desta issue
(`logs/203/2026-08-24_21-39-38.md`) terminou normalmente
(`▸ Credits: 4.52 • Time: 4m 2s`, sem `[exit-code:` no encerramento) e ainda
assim foi logada como:

```
21:43:53 - ERROR - Kiro - [incidente] #203 falhou: ...
```

O único gatilho foi a frase `Kiro is having trouble responding right now`
**citada pelo agente** ao analisar o incidente. Reproduzido de forma
determinística chamando `_detect_failure` com um output bem-sucedido cuja
narrativa cita a mensagem: retorna erro em vez de `None`.

É a mesma classe de defeito que o projeto já corrigiu para rate limit — o
`README` registra a decisão de **não** escanear o corpo da resposta em busca da
expressão, justamente para não gerar falso positivo. A regra não foi aplicada
aqui. Consequência: parte do "muitos problemas" relatado é **erro de medição**, e
as métricas de falha por execução não são confiáveis hoje.

### Fatos que ajustam o escopo

- `KIRO_API_KEY` distinta por projeto é irrelevante: nenhuma falha é de
  autenticação. O `Preflight` registra `✓ kiro-cli método ativo: API key`.
- `WARNING: Failed to retrieve MCP settings; MCP functionality disabled` aparece
  em 34 logs. É inofensivo (a esteira não usa MCP), mas é ruído recorrente.
- `logs/<data>.json` é **texto puro**, não JSON, apesar da extensão. Atrapalha
  qualquer análise programática dos logs diários.
- `README.md` documenta `model: claude-sonnet-4-20250514`, que não existe na CLI
  atual. Defeito de documentação, sem relação com este incidente.

### Taxa de falha observada

| Dia | Execuções | Falhas registradas | Observação |
|---|---|---|---|
| 21/08 | 16 | 2 | 1 abort com erro de aprovação |
| 22/08 | 15 | 2 | 1 `dispatch failure` sem erro de aprovação |
| 24/08 | 4 | 2 | 1 abort real (#175) + 1 falso positivo (#203) |

O volume de 24/08 é pequeno; a série não sustenta afirmação de tendência. O que é
sólido: houve **um** abort real por dia útil observado, e ao menos uma das falhas
contabilizadas não é falha.

### Risco

- **Não há** perda de dados, evento de segurança ou corrupção de estado da
  esteira. O snapshot e a fila não são afetados; a issue não avança de coluna e é
  reprocessada.
- **Desperdício de crédito e de tempo, recorrente.** A execução #175 morreu em
  4min27s sem produzir artefato e sem nem reportar crédito consumido (o resumo
  vem só no encerramento normal). Com `sleep: 1800` e `rerun_cooldown: 1800`, uma
  issue que falha de forma persistente é reentregue a cada 30 min — até ~48
  tentativas/dia, cada uma consumindo minutos de modelo.
- **Risco maior e silencioso: efeito colateral parcial.** O abort é no meio do
  turno, sem rollback. O agente pode já ter criado branch, feito commit, dado
  push e movido arquivos de coluna antes de cair — a execução anterior de #175
  fez exatamente isso (push de `epic175-...-work` e `mv` dos arquivos de coluna).
  Uma queda depois desse ponto deixa repositório e board em estado inconsistente,
  que ninguém reconcilia.
- **Risco de reincidência do "Issue Fantasma" (D4).** Enquanto o `pipe_context`
  versionado sombreia o gerado, os agentes atuam sem as instruções derivadas do
  `pipe.yml` — sem tabela de boards/colunas e sem prefixos de branch. É
  exatamente a lacuna que originou aquele incidente.
- **Risco de decisão sobre número errado (D5).** Métrica de falha inflada leva a
  priorizar o problema errado; foi o que levou a triagem à hipótese de
  `permissions.yaml`.

### Existe workaround?

Sim, parcial e sem alterar código. Ordenado por relação custo/efeito:

1. **Criar `.kiro/templates/docs/` e `.kiro/templates/issues/`** com os modelos
   citados (mesmo mínimos). Elimina D3 de imediato: acaba o cancelamento de lotes
   de ferramentas, encurtam as execuções e cai a exposição ao D1.
2. **Remover `.kiro/agents/pipe_context.json` do versionamento** e ignorá-lo no
   `.gitignore`. Resolve D4: o contexto gerado no startup volta a valer.
3. **Não investir em `permissions.yaml` nem em fixar versão do `kiro-cli` nos
   hosts.** A hipótese da triagem não se confirma; seria esforço sem retorno.

Para D1 não há workaround: é transitório e não determinístico. O reprocessamento
automático após o cooldown já cobre o caso, ao custo de repetir a execução. D5
não tem workaround — é código.

### Quanto custa corrigir?

Cinco itens; quatro pequenos e um médio. Estimativa em ordem de esforço, não em
horas.

| # | Correção | Esforço | Observação |
|---|---|---|---|
| C1 | Criar `.kiro/templates/{docs,issues}/` com os modelos referenciados | Pequeno | Sem código. Maior efeito imediato. |
| C2 | Desversionar `.kiro/agents/pipe_context.json` + entrada no `.gitignore` | Pequeno | Uma remoção e uma linha. Restaura a Correção 2 do "Issue Fantasma". |
| C3 | `_detect_failure` avaliar só os canais do `kiro-cli` (exit-code / bloco final / stderr), nunca a narrativa do agente | Pequeno | Com teste de regressão. Padrão já adotado na detecção de rate limit. |
| C4 | Retry com backoff no abort transitório (`dispatch failure`, `InternalServerError`), retomando por `--resume-id` | Médio | Correção real do D1. Exige decisão de idempotência: o agente pode já ter feito push. Precisa de story própria. |
| C5 | Corrigir o `model` de exemplo no `README.md` | Pequeno | Higiene de documentação. |

Recomendação para a Decisão de tratamento: **C1 + C2 como hotfix imediato**
(removem o amplificador e reativam o contexto, risco baixo, sem mudança de
lógica); **C3 em seguida**, para que a métrica de falha volte a ser confiável
antes de qualquer nova medição; **C4 como story separada**, porque o retry sem
tratar efeito colateral parcial pode duplicar push/commit. C4 não deve bloquear
C1–C3, e C1–C3 sozinhas não eliminam o D1.
