# Homologação — #98: Duplicação e ausência de coluna em sub-issues propagadas entre boards

Branch: `hotfix98-98-corrigir_duplicacao_e_ausencia_de_coluna_em_sub_issues_propagadas_entre_boards_github_projects_v2`
Commit: `8319752`

## O que foi corrigido

Quando uma sub-issue é vinculada a um parent que está em outro board (GitHub Projects V2),
o GitHub propaga automaticamente o item para todos os projects do parent, sem `Status`
definido. Antes desta correção, a esteira interpretava a ausência de coluna como "issue nova"
e criava uma duplicata local (arquivos + snapshot). Agora:

1. Após vincular uma sub-issue (`_add_sub_issue`), a esteira consulta os projects do item e
   remove (`remove_from_board` / mutation `deleteProjectV2Item`) qualquer propagação com
   `Status` vazio — preservando itens legítimos que já tenham coluna própria no mesmo board.
2. Se ainda assim chegar um evento de coluna vazia no `_apply_create_down` e a issue já
   pertencer a outro board (tem `parent` ou já existe em outro snapshot), o evento é
   descartado (chama `remove_from_board`, não cria arquivo local).
3. `create_issue` e `_apply_change_down` aplicam fallback para a primeira coluna configurada
   quando a coluna remota vier vazia, em vez de deixar o item sem `Status`.
4. `detect_board_changes` não ignora mais coluna vazia — trata como divergência a corrigir.

**Fora de escopo** (não faz parte desta homologação): limpeza do resíduo já existente
(#84/#85/#86 duplicados no project `story`) — é operação manual, com a esteira parada.

## Validação já realizada nesta preparação

- Merge de `main` na branch do hotfix: sem conflitos (branch já estava atualizada).
- Suíte de testes completa: **201 passed, 3 skipped** (`pytest`).
- Build da imagem Docker (`docker compose build`): sucesso.
- Smoke test de import dos módulos alterados dentro do container: sucesso.

### Cobertura específica da correção

Os dois testes adicionados em `tests/test_sub_issue_propagation_fix.py` validam:

- `create-down` com coluna vazia e issue conhecida em outro board: não cria
  arquivos locais;
- `create-down` com coluna vazia, sem parent e desconhecida em outros boards:
  cria na primeira coluna local.

Os seguintes cenários dependem do adapter/API do GitHub e devem ser confirmados
no roteiro manual abaixo: remoção efetiva do item propagado via
`deleteProjectV2Item`, preservação da sub-issue legítima com `Status`, fallback
de `create_issue`, reaplicação da coluna no `change-down` e detecção de coluna
vazia como divergência. Portanto, o resultado da suíte não substitui a
homologação em um project de staging.

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
