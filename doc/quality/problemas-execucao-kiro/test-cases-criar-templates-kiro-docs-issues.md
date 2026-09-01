# Casos de Teste — Criar `.kiro/templates/docs/` e `.kiro/templates/issues/` referenciados por `pipe.yml` e `contexts/kiro-cli/*.md`

Status: draft
Owner: quality
Last updated: 2026-08-24

## Inputs

- Task #204 — Criar `.kiro/templates/docs/` e `.kiro/templates/issues/`
  referenciados por `pipe.yml` e `contexts/kiro-cli/*.md` (board Task, coluna
  Casos de Teste)
- Issue de origem: #203 — Problemas na execução do kiro (board Incidente),
  defeito **D3** (amplificador: `.kiro/templates/**` referenciado e
  inexistente)
- Upstream relacionado (contexto, não causa raiz desta task):
  [kirodotdev/Kiro#6065](https://github.com/kirodotdev/Kiro/issues/6065)

## Observação de escopo

Task #204 é **agregação/redação de templates de documentação e issues**, sem
alteração de código-fonte da esteira (`src/`). Por isso os casos abaixo
validam **existência, conteúdo mínimo e efeito observável no log do agente**
(ausência do erro `Directory not found`), não comportamento de código. Fora de
escopo desta task, conforme o body: `src/adapters/kiro_cli_agent.py`
(`_detect_failure`, D5) e `.kiro/agents/pipe_context.json` (D4) — não devem
sofrer alteração de comportamento por esta entrega.

O diretório afetado é `.kiro/templates/` no(s) projeto(s) que referenciam o
template em `pipe.yml`/`contexts/kiro-cli/*.md` (ex.: `br.com.escrevas`); os
casos abaixo são escritos de forma agnóstica ao projeto concreto, aplicáveis a
qualquer repositório que apresente a mesma lacuna — incluindo este, caso o
levantamento (CT-001) confirme que a lacuna também existe aqui.

## CT-001 — Levantamento de referências a `.kiro/templates/docs/**` e `.kiro/templates/issues/**`

**Tipo:** integração (revisão documental/estática)
**Critério de aceitação:** Escopo item 1 — levantar todas as referências em
`pipe.yml` e `contexts/kiro-cli/*.md`, com nome exato de arquivo esperado e
etapa/coluna de uso.

**Pré-condição:**
- Repositório do projeto afetado disponível com `pipe.yml` e
  `contexts/kiro-cli/*.md`.

**Passos:**
1. Buscar (`grep -rn "templates/docs\|templates/issues"`) em `pipe.yml` e em
   cada `contexts/kiro-cli/*.md`.
2. Para cada ocorrência, anotar: arquivo esperado (ex.: `vision.md`,
   `epic.md`, `bug.md`), coluna/etapa que o referencia e board correspondente.
3. Consolidar a lista de arquivos únicos esperados em `templates/docs/` e em
   `templates/issues/`.

**Resultado esperado:**
- Lista completa e sem omissões dos arquivos esperados por tipo de diretório
  (docs vs. issues), cobrindo as ~20 referências citadas no body da task.
- Cada arquivo da lista tem pelo menos uma etapa/coluna de uso identificada
  (nenhuma referência órfã sem contexto de uso).

## CT-002 — Diretórios `.kiro/templates/docs/` e `.kiro/templates/issues/` existem e estão versionados

**Tipo:** integração
**Critério de aceitação:** "`.kiro/templates/docs/` e `.kiro/templates/issues/`
existem e estão versionados no(s) projeto(s) afetado(s), com todos os arquivos
referenciados por `pipe.yml`/`contexts/kiro-cli/*.md` presentes."

**Pré-condição:**
- CT-001 concluído (lista de arquivos esperados disponível).
- Templates criados no projeto afetado.

**Passos:**
1. Executar `git ls-files | grep '^\.kiro/templates/'` no repositório do
   projeto afetado.
2. Comparar a saída com a lista consolidada em CT-001.
3. Confirmar que os arquivos estão rastreados pelo git (não apenas presentes
   no filesystem local/ignorados).

**Resultado esperado:**
- Todo arquivo da lista de CT-001 aparece na saída do `git ls-files`.
- Nenhum arquivo esperado está ausente ou presente apenas fora do controle de
  versão (ex.: listado em `.gitignore`).

## CT-003 — Cada template de issue cobre os capítulos exigidos pela etapa que o referencia

**Tipo:** integração
**Critério de aceitação:** Escopo item 2 — modelo por tipo de issue,
cobrindo os capítulos que os agentes das colunas correspondentes precisam
preencher.

**Pré-condição:**
- `.kiro/templates/issues/` criado (epic, story/user-story, task, bug, débito
  — conforme uso real do `pipe.yml` do projeto afetado).

**Passos:**
1. Para cada arquivo em `.kiro/templates/issues/`, localizar no `pipe.yml` os
   `target-prompt` das colunas que o referenciam (ex.: `epic.md` referenciado
   na etapa de negócio do board Epic).
2. Verificar se o template contém, no mínimo, os campos/capítulos citados
   explicitamente nesses `target-prompt` (ex.: para `bug.md`: capítulo de
   "Referências" com "Issue original" e "Branch original", conforme os
   `target-prompt` de revisão de MR que preenchem esses campos).
3. Verificar se o template segue a convenção de comandos `@---` documentada no
   README (bloco de comandos separado do conteúdo, ex.: `/parent`,
   `/blocked_by`, `/labels`), quando a etapa correspondente usa esses
   comandos.

**Resultado esperado:**
- Nenhum template de issue referenciado carece de um capítulo exigido por
  algum `target-prompt` que o usa.
- Templates que precisam de campos de vínculo (bug↔epic/story, débito↔task)
  contêm esses campos.

## CT-004 — Cada template de doc cobre o conteúdo exigido pela etapa que o referencia

**Tipo:** integração
**Critério de aceitação:** Escopo item 3 — modelos de documentação
referenciados (ex.: ticket de incidente, post-mortem, changelog, conforme uso
real).

**Pré-condição:**
- `.kiro/templates/docs/` criado.

**Passos:**
1. Para cada arquivo em `.kiro/templates/docs/`, localizar no `pipe.yml`
   os `target-prompt` que o referenciam (ex.: `test-cases.md` na etapa "Casos
   de Teste"; `incidente.md` na etapa "Documentar incidente";
   `release-notes.md` na etapa de publicação).
2. Verificar se o template contém os capítulos citados explicitamente no
   `target-prompt` (ex.: `incidente.md` deve ter capítulo "Registro" —
   citado no `target-prompt` da etapa "Documentar incidente" — e também
   "Ação proposta" e "Tarefas de correção", citados em etapas posteriores do
   mesmo fluxo).
3. Verificar se o `test-cases.md` usado nesta própria task está entre os
   arquivos cobertos e é consistente com o formato usado nesta entrega.

**Resultado esperado:**
- Nenhum template de doc referenciado carece de um capítulo mencionado
  explicitamente por algum `target-prompt` do `pipe.yml`.

## CT-005 — Nenhuma referência a `.kiro/templates/**` fica sem arquivo correspondente (regressão de `Directory not found`)

**Tipo:** E2E (execução real ou revisão de log)
**Critério de aceitação:** "Uma nova execução de agente que anteriormente
falhava com `Directory not found: /app/.kiro/templates/...` não apresenta mais
esse erro no log."

**Pré-condição:**
- Templates criados e versionados (CT-002 aprovado).
- Log de agente anterior disponível com o erro
  `Tool validation failed: ... Directory not found: /app/.kiro/templates/docs`
  (ou `/issues`), conforme citado no body da task (confirmado em 18 logs).

**Passos:**
1. Selecionar uma issue/coluna que anteriormente disparou o erro (ex.: etapa
   de Casos de Teste, que referencia `test-cases.md`).
2. Reexecutar o agente na mesma coluna (ou revisar um log novo equivalente,
   gerado após a criação dos templates).
3. Inspecionar o log de execução (`logs/<issue_id>/<timestamp>.md`) em busca
   da string `Directory not found` e de `Tool 'shell'/'read' execution
   skipped due to validation failures`.

**Resultado esperado:**
- O log da nova execução não contém `Directory not found` referente a
  `.kiro/templates/docs` ou `.kiro/templates/issues`.
- Nenhum lote de ferramentas é cancelado por esse motivo (ausência de `Tool ...
  execution skipped due to validation failures in other tools` motivado por
  path de template).

## CT-006 — Nenhuma mudança de comportamento fora da criação dos templates

**Tipo:** integração (revisão de diff)
**Critério de aceitação:** "Nenhuma mudança de comportamento além da criação
dos templates (sem alterar lógica de código-fonte da esteira)."

**Pré-condição:**
- Diff completo da branch da task disponível.

**Passos:**
1. Revisar o diff da branch e confirmar que as únicas mudanças são arquivos
   sob `.kiro/templates/docs/` e `.kiro/templates/issues/` (e, se aplicável,
   ajuste de `.gitignore` para deixar de ignorar esse diretório, caso
   estivesse ignorado).
2. Confirmar que nenhum arquivo em `src/` foi alterado.
3. Confirmar que `.kiro/agents/pipe_context.json` não foi alterado (fora de
   escopo — defeito D4, task separada).

**Resultado esperado:**
- Diff contém apenas arquivos de template (e, no máximo, `.gitignore` se
  necessário para versionar o diretório).
- Nenhuma alteração em `src/adapters/kiro_cli_agent.py` ou em
  `.kiro/agents/pipe_context.json`.

## Dúvidas / lacunas identificadas durante a elaboração dos casos

- O documento `doc/incidente/problemas-execucao-kiro/ticket.md`, citado como
  referência no body desta task e no body da issue de origem #203, não está
  disponível neste branch (`origin/epic`) no momento da elaboração destes
  casos — o histórico de #203 indica que foi commitado apenas na branch
  `hotfix203-203-problemas_na_execucao_do_kiro`, ainda não mesclada. Os casos
  acima foram elaborados a partir do conteúdo já reproduzido no body/history
  de #203 e no body desta task, que contêm o defeito D3 na íntegra — não foi
  necessário abrir débito por isso, pois não há ambiguidade quanto ao que
  testar. Fica registrado para o caso de a etapa de desenvolvimento precisar
  do documento completo antes do merge da branch do hotfix.
