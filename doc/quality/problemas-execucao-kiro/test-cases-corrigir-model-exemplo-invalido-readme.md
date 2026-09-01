# Casos de Teste — Corrigir `model` de exemplo inválido no `README.md`

Status: draft
Owner: quality
Last updated: 2026-08-25

## Inputs

- Task #207 — Corrigir `model` de exemplo inválido no `README.md` (board
  Task, coluna Casos de Teste)
- Issue de origem: #203 — Problemas na execução do kiro (board Incidente),
  correção **C5**
- Referência técnica: `doc/incidente/problemas-execucao-kiro/ticket.md`
  (item "Fatos que ajustam o escopo" / correção C5)
- `docker/versions.env` — versão de `kiro-cli` atualmente pinada
  (`KIRO_CLI_VERSION=2.18.0`)

## Observação de escopo

Task puramente documental: substituir a string de modelo inválida
`claude-sonnet-4-20250514` no exemplo de `pipe.yml` do `README.md` por um
identificador válido na versão de `kiro-cli` pinada, e confirmar que não há
outras ocorrências no repositório. Fora de escopo (não devem ganhar caso de
teste aqui): qualquer mudança de código-fonte ou de configuração de execução
real dos 13 agentes (a própria issue confirma que eles já usam modelos
válidos — a string inválida existe apenas no exemplo do README).

Verificado no repositório neste momento (estado anterior à correção): a
única ocorrência de `claude-sonnet-4-20250514` é `README.md:50`, dentro do
bloco de exemplo `agents.kiro-cli.dev` da seção "Configuração"
(`grep -rn "claude-sonnet-4-20250514"` na raiz do repositório, sem exclusões
de path, não retorna nenhum outro arquivo).

## CT-001 — Identificador de modelo escolhido é válido na versão pinada do `kiro-cli`

**Tipo:** integração (validação de ambiente)
**Critério de aceitação:** "O exemplo de `pipe.yml` no `README.md` usa um
identificador de modelo válido na versão de `kiro-cli` pinada em
`docker/versions.env`."

**Pré-condição:**
- Ambiente com `kiro-cli` na versão pinada (`KIRO_CLI_VERSION` de
  `docker/versions.env`) instalado e acessível via `kiro-cli`.
- Identificador candidato definido pela etapa de Desenvolvimento (ex.: via
  consulta à documentação oficial do kiro-cli para essa versão ou listagem de
  modelos suportada pelo CLI).

**Passos:**
1. Executar `kiro-cli --version` e confirmar que a versão instalada
   corresponde a `KIRO_CLI_VERSION` de `docker/versions.env`.
2. Executar `kiro-cli chat --model <candidato> "oi" --no-interactive
   --trust-all-tools` com o identificador escolhido para o exemplo.
3. Repetir o mesmo comando com a string antiga (`claude-sonnet-4-20250514`)
   para reconfirmar a reprodução do defeito relatado na issue.

**Resultado esperado:**
- O comando com o identificador candidato executa sem o erro `error: Model
  '<candidato>' does not exist` (exit-code diferente de 1 por esse motivo
  específico).
- O comando com `claude-sonnet-4-20250514` reproduz `error: Model
  'claude-sonnet-4-20250514' does not exist` (exit-code 1), confirmando que o
  defeito documentado na issue é real e específico dessa string.

## CT-002 — `README.md` usa o identificador válido no exemplo de `pipe.yml`

**Tipo:** integração (revisão de conteúdo)
**Critério de aceitação:** "O exemplo de `pipe.yml` no `README.md` usa um
identificador de modelo válido..." (parte textual do critério).

**Pré-condição:**
- CT-001 concluído (identificador candidato validado).

**Passos:**
1. Abrir `README.md`, seção "Configuração", bloco de exemplo `agents.kiro-cli.dev`.
2. Localizar a linha `model: <valor>` dentro desse bloco.
3. Confirmar que `<valor>` é exatamente o identificador validado em CT-001,
   sem erros de digitação.
4. Confirmar que nenhuma outra linha do exemplo de `pipe.yml` foi alterada
   além dessa (diff restrito à string do modelo).

**Resultado esperado:**
- `README.md:50` (ou linha correspondente após a edição) contém
  `model: <identificador válido>`.
- Nenhuma outra parte do bloco de exemplo (`name: engineering`, indentação,
  demais chaves) foi modificada.

## CT-003 — Nenhuma ocorrência remanescente do identificador inválido no repositório

**Tipo:** integração (busca textual)
**Critério de aceitação:** "Nenhuma outra ocorrência do identificador
inválido permanece no repositório (busca por `claude-sonnet-4-20250514` sem
resultados, ou apenas em changelog/histórico onde a menção é factual e não
prescritiva)."

**Pré-condição:**
- CT-002 concluído (README já corrigido na branch da task).

**Passos:**
1. Executar `grep -rn "claude-sonnet-4-20250514" .` na raiz do repositório
   (sem exclusão de diretórios versionados), incluindo `.env.example` e
   `doc/**`.
2. Para cada ocorrência retornada, classificar o arquivo: exemplo/prescritivo
   (ex.: `README.md`, `.env.example`, tutoriais em `doc/`) versus factual/
   histórico (ex.: `CHANGELOG.md` registrando o que uma versão anterior
   continha, ou este próprio documento de casos de teste e o ticket do
   incidente, que citam a string para descrever o defeito).
3. Confirmar que nenhuma ocorrência prescritiva permanece.

**Resultado esperado:**
- `grep` não retorna nenhum arquivo de exemplo/configuração prescritiva
  (`README.md`, `.env.example` e demais docs de setup) com a string antiga.
- Ocorrências remanescentes, se houver, estão restritas a registros
  históricos/factuais (changelog, ticket do incidente, este documento de
  casos de teste) — que não são o exemplo que o usuário copiaria para
  configurar um novo projeto.

## CT-004 — Nenhuma mudança fora do escopo documental

**Tipo:** integração (revisão de diff)
**Critério de aceitação:** "Qualquer mudança de código-fonte ou de
configuração de execução — apenas documentação" (seção "Fora de escopo").

**Pré-condição:**
- Diff completo da branch da task disponível.

**Passos:**
1. Revisar o diff da branch e confirmar que as alterações estão restritas a
   arquivos de documentação (`README.md` e, se aplicável, outro arquivo de
   `doc/` que citasse a string de forma prescritiva).
2. Confirmar que nenhum arquivo em `src/`, `tests/`, `docker/`,
   `docker-compose.yml`, `compose.dev.yml` ou `pipe.yml` real de produção foi
   alterado.
3. Confirmar que `docker/versions.env` (fonte da versão pinada do kiro-cli)
   não foi modificado por esta task — é apenas consultado.

**Resultado esperado:**
- Diff restrito a arquivos de documentação.
- Nenhuma alteração de código-fonte, configuração de execução ou versão
  pinada.

## Dúvidas / lacunas identificadas durante a elaboração dos casos

Nenhuma dúvida ou lacuna que exija débito ou intervenção humana. A issue é
autocontida: descreve o defeito com o comando exato que o reproduz
(`kiro-cli chat --model claude-sonnet-4-20250514`, erro `does not exist`,
exit-code 1) e delega à etapa de Desenvolvimento a escolha do identificador
válido, o que é uma consulta objetiva (documentação/listagem de modelos da
versão pinada), sem ambiguidade de design. A validação real do identificador
candidato (CT-001) depende de a etapa de Desenvolvimento ter acesso a um
ambiente com `kiro-cli` na versão pinada — este documento apenas define o
caso; a execução efetiva do comando é responsabilidade das etapas
subsequentes (Desenvolvimento/Execução de Testes).

— Camila Rocha - Engenheira de Qualidade (QA)
