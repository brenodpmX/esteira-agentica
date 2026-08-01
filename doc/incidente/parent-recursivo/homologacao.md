# Orientações — Ambiente Pré-Produtivo (Homologação)

Branch: `hotfix97-97-erro_reportado_dia_010826`
Issue: #97 — Erro reportado dia 01/08/26 (incidente "Parent Recursivo")

## O que está nesta branch

Esta etapa (`pre-prod`) trata **apenas a documentação do incidente** — não há
alteração de código nesta branch. `main` já estava totalmente contido nela
(relação de ancestralidade direta), então o merge não gerou conflitos.

Único artefato novo: `doc/incidente/parent-recursivo/ticket.md` — registro
completo do incidente #97 (Triagem → Análise Técnica → Decisão de tratamento
→ Tarefas de correção C1–C5).

**Importante para quem for homologar:** as correções de código propriamente
ditas (C1–C5, descritas no ticket) ainda **não foram implementadas**. Elas
existem como 5 tasks separadas no board `task` (coluna `aguardando-tasks` /
`backlog`), a serem executadas em etapas futuras, na ordem C2 → C3 → C1 → C4
→ C5. O que há para homologar aqui é o **estado do repositório após o reparo
manual do incidente** (issue #76 restaurada, snapshot corrigido, arquivos
órfãos removidos) e a suíte de testes/documentação — não uma correção de bug
em si.

## Validação já realizada nesta etapa

- `git diff main...hotfix97-97-erro_reportado_dia_010826 --stat` → apenas
  `doc/incidente/parent-recursivo/ticket.md` (282 linhas adicionadas).
- Merge de `main` na branch do épico: **sem conflitos** (branch já continha
  todos os commits de `main`).
- Suíte de testes: `python3 -m pytest tests/ -q` → **199 passed, 3 skipped**.
- Build da imagem Docker: `docker compose build` → sucesso.
- Sanity check de import dos módulos dentro da imagem (`src.__main__`,
  `src.core.*`, `src.adapters.*`) → sem erros.

## Pré-requisitos para subir o ambiente

1. **Docker e Docker Compose** instalados no host de homologação.
2. **`gh auth login`** já executado no host — gera `~/.config/gh/` (usado
   somente para obter o diretório de config; a autenticação efetiva do
   container é via `GH_TOKEN`).
3. **Chave SSH** configurada no GitHub, presente no host (padrão
   `~/.ssh/id_ed25519`).
4. **Token do GitHub** (`GH_TOKEN`) com escopos `repo` e `project`.
5. **Binário `kiro-cli`** disponível no `PATH` do host (usado por
   `prepare-docker.sh` para copiar para o contexto de build). Já está
   presente na raiz deste checkout (`./kiro-cli`), então este passo pode ser
   pulado se for usar o mesmo checkout.
6. **`pipe.yml`** — arquivo de configuração da esteira. **Não é versionado**
   (está no `.gitignore`) e precisa ser criado/copiado manualmente na raiz do
   projeto antes de subir o ambiente. Ver formato no `README.md`, seção
   "Configuração → Arquivo pipe.yml".

## Passo a passo

```bash
cd /home/breno/pipes/pipe/repo/main

# 1. Confirmar que está na branch correta
git status
git branch --show-current   # deve mostrar hotfix97-97-erro_reportado_dia_010826

# 2. Preparar o contexto de build (copia o binário kiro-cli, se necessário)
./prepare-docker.sh

# 3. Criar o .env com o token do GitHub
cp .env.example .env
# editar .env e preencher GH_TOKEN (e opcionalmente SSH_KEY_FILE, GH_CONFIG_DIR
# se diferentes dos padrões ~/.ssh/id_ed25519 e ~/.config/gh)

# 4. Garantir que pipe.yml existe na raiz (copiar do ambiente de referência
#    ou criar seguindo o README — NÃO versionar este arquivo)
ls pipe.yml   # deve existir antes do próximo passo

# 5. Build e execução
docker compose build
docker compose up -d

# 6. Acompanhar logs
docker compose logs -f
```

## Verificação de saúde

- `docker compose ps` — container `pipe` deve estar `Up` e não reiniciando em
  loop (`restart: unless-stopped` no compose reinicia sozinho em caso de
  crash — restarts frequentes nos primeiros minutos indicam problema de
  configuração, não do processo em si).
- `docker compose logs -f` — checar por:
  - Mensagem de startup indicando SSH configurado, `CONTEXT.md`/agente
    `pipe_context` gerados, e clone dos repositórios configurados em
    `pipe.yml`.
  - Ausência de exceptions não tratadas repetidas no mesmo padrão do
    incidente #97 (`"Erro no ciclo (não fatal)"` repetindo indefinidamente
    para o mesmo item é sinal de alerta — ver seção "Issues fantasmas" e
    "Causa raiz" do incidente no `ticket.md`).
- Verificar no board de incidente/tarefas (GitHub Projects) que os itens
  esperados aparecem/avançam de acordo com `pipe.yml`.

## Persistência de dados entre reinícios

| Volume | Caminho no container | Conteúdo |
|--------|----------------------|----------|
| `pipe_state` | `/app/.pipe` | Snapshots, fila de mudanças, índice de sessões |
| `pipe_repos` | `/app/repo` | Clones dos repositórios git |
| `pipe_logs` | `/app/logs` | Logs de execução |

Para forçar um re-sync completo (estado limpo), remova os volumes — **ação
destrutiva, irreversível para o estado local** (não afeta o GitHub, apenas o
cache local de snapshots/fila/sessões):

```bash
docker compose down -v
```

## Parar o ambiente

```bash
docker compose down       # mantém os volumes (estado preservado)
```

## Ponto de atenção para o homologador

Como esta issue trata do **incidente #97** (não de uma correção de código),
a homologação aqui deve focar em:

1. Confirmar que a documentação do incidente (`ticket.md`) está completa e
   consistente com o relato original (comparar com o body/histórico da issue
   #97 no board `incidente`).
2. Confirmar que o ambiente sobe normalmente com o código atual (sem as
   correções C1–C5, que ainda não existem) — ou seja, validar que **nada foi
   quebrado** ao consolidar a documentação, não que o bug do incidente foi
   corrigido.
3. As correções de código (C1–C5) serão homologadas separadamente quando as
   respectivas tasks forem concluídas.

---
Preparado por: Isabela Gomes - Tech Lead
