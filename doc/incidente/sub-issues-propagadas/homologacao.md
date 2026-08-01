# Orientações — Ambiente Pré-Produtivo (Homologação)

Branch: `epic99-99-post_mortem_do_incidente_corrigir_duplicacao_e_ausencia_de_coluna_em_sub_issues_propagadas_entre_boards_github_projects_v2`
Issue: #99 — Post Mortem do incidente Corrigir duplicação e ausência de coluna em sub-issues
propagadas entre boards (GitHub Projects V2)

## O que está nesta branch

Esta etapa (`pre-prod`) trata **apenas o documento de post mortem** — não há alteração de
código nesta branch. `main` já estava totalmente contido nela (relação de ancestralidade
direta; `git merge origin/main` resultou em "Already up to date"), então o merge não gerou
conflitos.

Artefato documental desta branch:

- `doc/incidente/sub-issues-propagadas/ticket.md` — post mortem completo: registro, causa
  raiz, linha do tempo consolidada (incluindo as duas tentativas de correção reprovadas em
  code review e a correção final), fatores que permitiram a reincidência por 3 ciclos, e
  recomendações.
- `doc/incidente/sub-issues-propagadas/homologacao.md` — este roteiro.

**Importante para quem for homologar:** a correção de código do incidente subjacente (#98) já
foi implementada, testada e homologada **em outra branch** —
`hotfix98-98-corrigir_duplicacao_e_ausencia_de_coluna_em_sub_issues_propagadas_entre_boards_github_projects_v2`
(commit `01f9e83`, homologado por Isabela Gomes - Tech Lead em 2026-08-01 22:43, com roteiro
próprio em `doc/homologacao-98-sub-issues-propagadas.md` naquela branch). Essa correção ainda
**não está mergeada em `main`** — o PR #103 foi reprovado em code review numa versão anterior
do commit e precisa de uma nova revisão sobre o commit corrigido antes do merge. O que há
para homologar **aqui** é o documento de post mortem, não uma correção de bug em si.

## Validação já realizada nesta etapa

- `git fetch origin` + `git merge origin/main` na branch do épico: **sem conflitos**
  ("Already up to date" — a branch já continha todos os commits de `main`).
- `git diff main --stat`: nenhuma alteração fora do novo diretório
  `doc/incidente/sub-issues-propagadas/` (documentação pura, nenhum arquivo em `src/` ou
  `tests/` alterado).
- Suíte de testes: `python3 -m pytest tests/ -q` → **199 passed, 3 skipped** (mesmo resultado
  de `main` — sem regressão, já que não há alteração de código nesta branch).
- Build da imagem Docker: `./prepare-docker.sh` + `docker compose build` → sucesso.
- Integridade do conteúdo: post mortem revisado contra o histórico completo da issue #98
  (incluindo as 5 verificações consecutivas de Isabela Gomes - Tech Lead na etapa de
  pré-produção daquela correção) e contra o body da issue #88 (registro original do
  incidente).

## Como subir o ambiente pré-produtivo

### Pré-requisitos no host de homologação

- Docker e Docker Compose instalados.
- `gh auth login` já executado no host (gera `~/.config/gh/`).
- Chave SSH configurada no GitHub (por padrão `~/.ssh/id_ed25519`).
- Token do GitHub com escopos `repo` e `project`.
- `kiro-cli` instalado no host (necessário só para o build — é copiado para a imagem).
- Um `pipe.yml` válido na raiz do projeto (não é versionado — deve ser criado/copiado
  manualmente; ver `README.md`, seção "Arquivo pipe.yml", para o formato completo).

### Passo a passo

```bash
# 1. Checkout da branch em homologação
cd /caminho/do/repo
git fetch origin
git checkout epic99-99-post_mortem_do_incidente_corrigir_duplicacao_e_ausencia_de_coluna_em_sub_issues_propagadas_entre_boards_github_projects_v2
git pull

# 2. Preparar o contexto de build (copia o binário kiro-cli do host para a raiz do projeto)
./prepare-docker.sh

# 3. Criar o .env com o token do GitHub
cp .env.example .env
# Editar .env e preencher GH_TOKEN (escopos repo + project)
# Opcionalmente ajustar SSH_KEY_FILE e GH_CONFIG_DIR se diferentes do padrão
#   (~/.ssh/id_ed25519, ~/.config/gh)

# 4. Garantir que existe um pipe.yml na raiz do projeto
#    (não versionado — copiar/criar manualmente)

# 5. Build e subida
docker compose build
docker compose up -d
docker compose logs -f    # acompanhar em tempo real
```

### Roteiro de homologação sugerido

Como esta branch é documentação, o roteiro de homologação é sobre **conteúdo**, não
comportamento de runtime:

1. Ler `doc/incidente/sub-issues-propagadas/ticket.md` e confirmar que a linha do tempo, a
   causa raiz e as recomendações refletem corretamente o histórico real das issues #88 e #98
   (conferir contra `.pipe/boards/incidente/aguardando-tasks/88-...-body.md` e
   `.pipe/boards/incidente/homologacao/98-...-history.md`, se ainda existirem no ambiente de
   homologação).
2. Confirmar que o documento não faz nenhuma afirmação sobre o estado da correção de código
   que não possa ser verificada na branch `hotfix98-...` (ex.: número exato de testes,
   commits, revisor).
3. Subir o ambiente (`docker compose up -d`) apenas para confirmar que a imagem builda e
   inicia sem erros com o `pipe.yml` de homologação — não há comportamento novo de runtime
   para validar nesta branch especificamente.
4. Verificar que as recomendações do post mortem (seção final do `ticket.md`) são acionáveis:
   cada uma referencia um artefato concreto (bug, resíduo de dados, arquivo de código) que já
   existe no repositório ou nos boards.

### Encerrar o ambiente

```bash
docker compose down       # mantém os volumes (pipe_state, pipe_repos, pipe_logs)
docker compose down -v    # remove também os volumes (força re-sync completo na próxima subida)
```

## Após homologação aprovada

- Avançar a issue #99 para a coluna de destino do board `epic` (`homologacao`).
- A correção de código do incidente #98 (branch `hotfix98-...`) segue seu próprio fluxo,
  independente deste post mortem — acompanhar separadamente até o merge do PR em `main`.
