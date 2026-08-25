# Casos de Teste — Desversionar `.kiro/agents/pipe_context.json` para reativar o contexto gerado no startup

Status: draft
Owner: quality
Last updated: 2026-08-24

## Inputs

- Task #205 — Desversionar `.kiro/agents/pipe_context.json` para reativar o
  contexto gerado no startup (board Task, coluna Casos de Teste)
- Issue de origem: #203 — Problemas na execução do kiro (board Incidente),
  defeito **D4**
- Referência técnica: `doc/incidente/problemas-execucao-kiro/ticket.md`
  (defeito D4) — não disponível neste branch no momento da elaboração destes
  casos (ver seção de dúvidas/lacunas)
- Incidente "Issue Fantasma" — Correção 2 (commit `dde5adc`), que introduziu a
  geração de `.pipe/CONTEXT.md`/`.kiro/agents/pipe_context.json` no startup

## Observação de escopo

Task #205 é uma operação de controle de versão (`git rm --cached` +
`.gitignore`) mais validação (sem alteração de código) da regra de
regeneração já implementada em `src/core/context_generator.py`. Os casos
abaixo cobrem exatamente os 4 itens do escopo e os critérios de aceite da
issue. Fora de escopo desta task (não devem ganhar caso de teste aqui):
mudanças em `.kiro/templates/**` (task separada, D3) e em `_detect_failure`
(task separada, D5).

Verificado no repositório neste momento (estado anterior à correção):
`.kiro/agents/pipe_context.json` está rastreado (`git ls-files` retorna o
caminho) e não consta em `.gitignore` — confirma a premissa da issue.

## CT-001 — `.kiro/agents/pipe_context.json` deixa de estar rastreado pelo git

**Tipo:** integração (controle de versão)
**Critério de aceitação:** "`.kiro/agents/pipe_context.json` não está mais
rastreado pelo git em nenhum branch após o merge."

**Pré-condição:**
- Branch da task com `git rm --cached .kiro/agents/pipe_context.json`
  aplicado e committado.

**Passos:**
1. Executar `git ls-files | grep '^\.kiro/agents/pipe_context\.json$'` na
   branch da task.
2. Executar `git log --follow -- .kiro/agents/pipe_context.json` e confirmar
   que o histórico anterior ao commit de remoção é preservado (arquivo
   removido do índice, não do histórico).
3. Verificar no filesystem local que o arquivo `.kiro/agents/pipe_context.json`
   ainda existe (o `git rm --cached` remove do índice, não do disco).

**Resultado esperado:**
- `git ls-files` não retorna mais o caminho.
- O histórico do arquivo permanece consultável via `--follow` (não é uma
  reescrita de histórico).
- O arquivo continua presente no disco, apenas não rastreado.

## CT-002 — `.kiro/agents/pipe_context.json` está listado no `.gitignore`

**Tipo:** integração (controle de versão)
**Critério de aceitação:** "está listado no `.gitignore`."

**Pré-condição:**
- CT-001 concluído.

**Passos:**
1. Inspecionar o `.gitignore` do projeto e confirmar entrada para
   `.kiro/agents/pipe_context.json` (ou padrão equivalente que o cubra, ex.:
   `.kiro/agents/pipe_context.json` explícito — evitar glob amplo demais que
   ignore outros agentes legítimos em `.kiro/agents/`).
2. Criar/tocar o arquivo localmente (`touch .kiro/agents/pipe_context.json`)
   e executar `git status`.
3. Confirmar que o arquivo não aparece como "untracked" nem "modified".

**Resultado esperado:**
- `.gitignore` contém a entrada.
- `git status` não lista o arquivo, mesmo presente no disco e alterado.
- Nenhum outro arquivo em `.kiro/agents/` é afetado pela entrada adicionada
  (regressão: ignorar agentes legítimos que devam permanecer versionados,
  caso existam).

## CT-003 — Regra de regeneração em `generate_context` cobre "arquivo existente porém desatualizado"

**Tipo:** unitário (validação de comportamento já implementado, sem mudança
de código esperada)
**Critério de aceitação:** Escopo item 3 — confirmar que a regra é "recria se
não existir OU se `pipe.yml` for mais novo que `CONTEXT.md`", sem necessidade
de alteração se já cobrir o caso.

**Pré-condição:**
- Ambiente de teste com `PIPE_FILE`, `CONTEXT_FILE` e `AGENT_FILE` controláveis
  (via mock/monkeypatch dos Paths do módulo, padrão já usado em
  `tests/test_context_generator.py`).

**Passos:**
1. Caso A — arquivo ausente: garantir que `CONTEXT_FILE` não existe; chamar
   `_needs_regeneration()`; esperar `True`.
2. Caso B — `pipe.yml` mais novo: criar `CONTEXT_FILE` e, em seguida,
   `PIPE_FILE` com mtime posterior (ex.: `os.utime` explícito); chamar
   `_needs_regeneration()`; esperar `True`.
3. Caso C — `CONTEXT_FILE` atualizado (mtime igual ou posterior ao
   `pipe.yml`): chamar `_needs_regeneration()`; esperar `False`.
4. Caso D — `pipe.yml` ausente mas `CONTEXT_FILE` existente: chamar
   `_needs_regeneration()`; esperar `False` (comportamento documentado no
   código: só compara mtime se `PIPE_FILE` existir).
5. Revisar `tests/test_context_generator.py` para confirmar se os casos A–D já
   têm cobertura equivalente; se sim, apenas validar que passam na branch
   atual (`pytest tests/test_context_generator.py`); se não, sinalizar lacuna
   (sem implementar — fora do escopo desta task, que é validação).

**Resultado esperado:**
- Os 4 casos comportam-se conforme a regra documentada no README e no
  docstring de `generate_context`.
- Suíte `tests/test_context_generator.py` passa sem alteração de código em
  `src/core/context_generator.py`.
- Nenhuma mudança de lógica é necessária (achado esperado desta validação,
  conforme o próprio escopo da issue prevê como resultado possível).

## CT-004 — Warning "Agent conflict for pipe_context. Using workspace version." não é mais emitido

**Tipo:** E2E (execução real do agente)
**Critério de aceitação:** "Uma execução de agente após a correção não emite
mais o warning `Agent conflict for pipe_context. Using workspace version.`"

**Pré-condição:**
- CT-001 e CT-002 aplicados (arquivo desversionado e ignorado).
- Ambiente com `kiro-cli` configurado, `KIRO_HOME` apontando para o `.kiro` da
  esteira (conforme `src/adapters/kiro_cli_agent.py::_run`) e cwd no clone do
  próprio repositório (self-hosting: o `.kiro/agents/pipe_context.json` de
  workspace, quando presente e rastreado, é justamente o deste repo).

**Passos:**
1. Antes da correção (baseline, opcional se já documentado em log anterior):
   confirmar em pelo menos um log de execução real (`logs/<issue_id>/*.md`)
   a presença da linha `WARNING: Agent conflict for pipe_context. Using
   workspace version.`.
2. Após a correção: executar um ciclo real da esteira (ou `kiro-cli chat
   --no-interactive --agent pipe_context` diretamente no cwd do repo clonado)
   e capturar o log/stderr da execução.
3. Buscar (`grep -i "agent conflict"`) no log gerado.

**Resultado esperado:**
- O warning não aparece no log da execução pós-correção.
- A execução usa o agente `pipe_context` proveniente de `KIRO_HOME` (gerado no
  startup a partir do `pipe.yml` real), não de um arquivo de workspace
  desatualizado.

## CT-005 — Contexto injetado contém as tabelas de boards/colunas e git flow preenchidas

**Tipo:** E2E (validação de conteúdo real)
**Critério de aceitação:** "O contexto injetado numa execução real contém a
tabela de boards/colunas e a tabela de git flow preenchidas (não vazias),
refletindo o `pipe.yml` do projeto em execução." + Escopo item 4 (validação
local).

**Pré-condição:**
- `.kiro/agents/pipe_context.json` de workspace removido do disco (para
  forçar a leitura do gerado em `KIRO_HOME`, eliminando qualquer resíduo local
  antigo) ou já desversionado conforme CT-001/CT-002.
- `pipe.yml` válido disponível com pelo menos um board com colunas e pelo
  menos um flow de git configurado.

**Passos:**
1. Apagar (se existir) o `.kiro/agents/pipe_context.json` local de workspace.
2. Rodar o startup da esteira (`python -m src` ou equivalente) e aguardar a
   geração de `.pipe/CONTEXT.md` / `.kiro/agents/pipe_context.json` (função
   `generate_context`, chamada em `startup()`).
3. Abrir o `.kiro/agents/pipe_context.json` gerado (campo `prompt`) e/ou
   `.pipe/CONTEXT.md` e localizar a seção "## Boards e colunas".
4. Confirmar que, para cada board configurado em `pipe.yml` (exceto a chave
   `platform`), há uma subseção `### Board: <nome> (id: ...)` com uma tabela
   `| Coluna (id) | Nome | Agente |` listando as colunas reais.
5. Localizar a seção "## Git flow e branches" e confirmar que a tabela
   `| Flow | Prefixo | Origem | Merge em |` lista os flows definidos em
   `git.flow` do `pipe.yml` (excluindo a chave `base`), com prefixo/origem/
   merge coerentes com o YAML.
6. Comparar linha a linha com o `pipe.yml` usado, sem omissões nem boards/
   flows fantasmas.

**Resultado esperado:**
- Nenhuma das duas tabelas está vazia (ao contrário do arquivo congelado
  anterior, cujas seções de boards/colunas e git flow estavam vazias).
- O conteúdo reflete fielmente o `pipe.yml` em uso no momento do startup.

## CT-006 — Nenhuma mudança de lógica em `src/core/context_generator.py`

**Tipo:** integração (revisão de diff)
**Critério de aceitação:** "Nenhuma alteração de lógica em
`src/core/context_generator.py` além do que o item 3 do escopo indicar ser
necessário (validação, não mudança, é o esperado)."

**Pré-condição:**
- Diff completo da branch da task disponível.

**Passos:**
1. Revisar o diff e confirmar que `src/core/context_generator.py` não foi
   alterado (ou, se CT-003 revelar uma lacuna real na regra de regeneração,
   confirmar que qualquer alteração está estritamente restrita a corrigir
   essa lacuna específica, sem mudanças adicionais de comportamento).
2. Confirmar que as únicas mudanças de código de produção são:
   `git rm --cached .kiro/agents/pipe_context.json` e a entrada no
   `.gitignore`.
3. Confirmar que nenhum arquivo em `.kiro/templates/**` foi alterado (fora de
   escopo, D3) e que `src/adapters/kiro_cli_agent.py::_detect_failure` não foi
   tocado (fora de escopo, D5).

**Resultado esperado:**
- Diff restrito ao escopo da issue: remoção do arquivo do índice, entrada no
  `.gitignore` e, no máximo, testes/documentação de suporte à validação
  (CT-003).
- Nenhuma regressão de comportamento fora do que a issue pede.

## Dúvidas / lacunas identificadas durante a elaboração dos casos

- O documento `doc/incidente/problemas-execucao-kiro/ticket.md`, citado como
  referência técnica no body da task (defeito D4), não está disponível neste
  branch (`origin/epic`) no momento da elaboração destes casos — mesma lacuna
  já registrada pela task irmã #204 para o defeito D3. O conteúdo do defeito
  D4 já está reproduzido de forma completa e sem ambiguidade no body desta
  própria issue (#205), o que foi suficiente para elaborar os casos acima sem
  necessidade de abrir débito. Fica registrado para o caso de a etapa de
  desenvolvimento precisar do ticket completo antes do merge do hotfix.
- CT-003 e CT-006 assumem que a validação da regra de regeneração pode revelar
  uma lacuna real (não apenas confirmar que já está correta); os passos foram
  escritos para cobrir ambos os desfechos sem prejulgar o resultado, conforme
  o próprio escopo da issue admite ("sem necessidade de mudança de código se a
  regra já cobrir o caso").

— Camila Rocha - Engenheira de Qualidade (QA)
