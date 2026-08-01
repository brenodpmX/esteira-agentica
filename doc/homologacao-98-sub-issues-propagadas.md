# Homologação — #98: Duplicação e ausência de coluna em sub-issues propagadas entre boards

Branch: `hotfix98-98-corrigir_duplicacao_e_ausencia_de_coluna_em_sub_issues_propagadas_entre_boards_github_projects_v2`
Commit: `01f9e83` (inclui correção pós code review do PR #103 — ver seção "Histórico de revisão")

## O que foi corrigido

Quando uma sub-issue é vinculada a um parent que está em outro board (GitHub Projects V2),
o GitHub propaga automaticamente o item para todos os projects do parent, sem `Status`
definido. Antes desta correção, a esteira interpretava a ausência de coluna como "issue nova"
e criava uma duplicata local (arquivos + snapshot). Agora:

1. Após vincular uma sub-issue (`_add_sub_issue`), a esteira consulta via **GraphQL**
   (`projectItems{nodes{id project{id} fieldValues...}}`, mesmo padrão de
   `_belongs_to_board`/`get_issue`) os projects do item e remove (`remove_from_board` /
   mutation `deleteProjectV2Item`) qualquer propagação com `Status` vazio — preservando
   itens legítimos que já tenham coluna própria no mesmo board.
2. Se ainda assim chegar um evento de coluna vazia no `_apply_create_down` e a issue já
   pertencer a outro board (tem `parent` ou já existe em outro snapshot), o evento é
   descartado (chama `remove_from_board`, não cria arquivo local).
3. `create_issue` e `_apply_change_down` aplicam fallback para a primeira coluna configurada
   quando a coluna remota vier vazia, em vez de deixar o item sem `Status`.
4. `detect_board_changes` não ignora mais coluna vazia — trata como divergência a corrigir.

**Fora de escopo** (não faz parte desta homologação): limpeza do resíduo já existente
(#84/#85/#86 duplicados no project `story`) — é operação manual, com a esteira parada.

## Histórico de revisão

O PR #103 foi **reprovado** em code review (Bruno Ferreira): o pós-hook do item 1
(`_remove_propagated_without_column`) chamava um endpoint REST inexistente
(`/repos/{owner}/{repo}/issues/{n}/projectitems`), que falhava silenciosamente em produção —
ou seja, a causa raiz do incidente não era corrigida de fato, apesar da suíte de testes
passar. Além disso, 2 dos 4 cenários de teste exigidos no escopo estavam ausentes.

Essas duas pendências foram corrigidas nesta preparação de pré-produção:

- `_remove_propagated_without_column` foi reescrito usando GraphQL (mesmo padrão real já
  usado por `_belongs_to_board`/`get_issue` no mesmo arquivo), eliminando a chamada REST
  inexistente.
- Os 2 cenários de teste faltantes foram adicionados, exercitando o adapter real via mock de
  `_gql`/`_gh` (sem monkeypatch do próprio método sob teste): pós-hook preservando item
  legítimo com `Status`, e fallback de coluna em `create_issue`.
- Adicionado teste para `detect_board_changes` tratando coluna vazia como divergência, e um
  teste de regressão para a interação entre o guard do `create-down` e o fallback do
  `change-down` (risco de reversão circular apontado no ponto 3 do code review).

O bug aberto no board `bug` (`correcao-98-sub-issues-propagadas-reincide-endpoint-inexistente`)
referente a este defeito pode ser encerrado após esta correção ser homologada.

## Validação já realizada nesta preparação

- Merge de `main` na branch do hotfix: sem conflitos (auto-merge; branch já continha o que
  era necessário além dos arquivos de documentação recém-adicionados em `main`).
- Suíte de testes completa: **208 passed, 3 skipped** (`pytest`) — 7 testes novos em relação
  à versão reprovada (201 passed).
- Build da imagem Docker (`docker compose build`): sucesso.
- Smoke test dentro do container construído: confirmado que
  `_remove_propagated_without_column` usa GraphQL (`_gql`) e não chama mais `_gh`/REST.

### Cobertura específica da correção

Os testes em `tests/test_sub_issue_propagation_fix.py` agora cobrem os 4 cenários do item 5
do escopo original, todos exercitando código real (sem fakes substituindo o método sob teste):

- `create-down` com coluna vazia e issue conhecida em outro board: não cria arquivos locais
  e chama `remove_from_board`.
- `create-down` com coluna vazia, sem parent e desconhecida em outros boards: cria na
  primeira coluna local (fallback).
- Pós-hook (`_remove_propagated_without_column`) remove item com `Status` vazio via
  `deleteProjectV2Item`, e **preserva** item com `Status` definido (sub-issue legítima).
- Fallback de coluna em `create_issue` quando a opção informada não existe no project.
- `detect_board_changes` gera `change-down` quando a coluna remota vem vazia divergindo do
  snapshot.
- Regressão: o guard do `create-down` impede que a issue chegue a ter entrada no snapshot
  deste board, logo o fallback do `change-down` nunca reaplica coluna a um item que deveria
  permanecer removido do project (interação apontada no ponto 3 do code review).

Ainda assim, a suíte usa um `FakeBoardPort`/mocks de `_gql`/`_gh` — a validação final contra
o comportamento real da API do GitHub Projects V2 (rate limits, schema exato de resposta,
timing de propagação) só é possível no roteiro manual de homologação abaixo.

## Como subir o ambiente pré-produtivo para homologação

### Pré-requisitos no host de homologação

- Docker e Docker Compose instalados.
- `gh auth login` já executado no host (gera `~/.config/gh/`).
- Chave SSH configurada no GitHub (por padrão `~/.ssh/id_ed25519`).
- Token do GitHub com escopos `repo` e `project`.
- `kiro-cli` instalado no host (necessário só para o build — é copiado para a imagem).
- Um `pipe.yml` válido apontando para o **board de homologação/staging** (não para o board de
  produção real) — ver `README.md`, seção "Arquivo pipe.yml", para o formato completo.

> **Atenção:** como esta correção interage diretamente com sub-issues e propagação entre
> boards no GitHub Projects V2, a homologação deve usar um board/projeto de teste (ou uma
> cópia) — não o board de produção — para não gerar side-effects reais em issues de produção
> durante a validação manual.

### Passo a passo

```bash
# 1. Checkout da branch em homologação
cd /caminho/do/repo
git checkout hotfix98-98-corrigir_duplicacao_e_ausencia_de_coluna_em_sub_issues_propagadas_entre_boards_github_projects_v2
git pull

# 2. Preparar o contexto de build (copia o binário kiro-cli do host)
./prepare-docker.sh

# 3. Criar o .env com o token do GitHub de homologação
cp .env.example .env
# Editar .env e preencher GH_TOKEN (escopos repo + project) do ambiente de staging
# Opcionalmente ajustar SSH_KEY_FILE e GH_CONFIG_DIR se diferentes do padrão

# 4. Garantir que existe um pipe.yml na raiz apontando para o board de homologação
#    (pipe.yml não é versionado — copiar/criar manualmente)

# 5. Build e subida
docker compose build
docker compose up -d
docker compose logs -f   # acompanhar em tempo real
```

### Roteiro de homologação manual sugerido

1. Criar (ou usar) um epic/story de teste em um board e uma task filha em outro board.
2. Vincular a task filha ao parent (`/parent #N` no body) e deixar a esteira sincronizar.
3. No GitHub Projects V2, confirmar que o item da sub-issue **não aparece** sem `Status` no
   project do parent (a remoção automática deve ter ocorrido).
4. Confirmar que a sub-issue não aparece como tarefa executável no board do parent e que não
   foi criado um segundo conjunto local de arquivos da issue nesse board.
5. Confirmar que uma sub-issue legítima, já pertencente ao mesmo board do parent com coluna
   própria, **não** é removida pelo pós-hook (regressão).
6. Verificar os logs (`docker compose logs -f` ou `logs/`) pelas operações
   `remove_propagated_without_column`, `remove_from_board` e `create_issue`, investigando
   warnings inesperados ou uso do fallback de coluna.

### Encerrar o ambiente

```bash
docker compose down       # mantém os volumes (pipe_state, pipe_repos, pipe_logs)
docker compose down -v    # remove também os volumes (força re-sync completo na próxima subida)
```
