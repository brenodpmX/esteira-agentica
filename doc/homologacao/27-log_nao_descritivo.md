# Homologação — #27 Log não descritivo

Guia para o humano validar em ambiente pré-produtivo a correção do log de
execução de agente (título + etapa legíveis, remoção de `model`/`cwd`).

## O que foi corrigido

Log de terminal emitido a cada execução de agente (`KiroCliAgent.execute`,
`src/adapters/kiro_cli_agent.py`).

**Antes:**
```
19:47:03 [Agent] [task] #25 agent='Sofia Carvalho - Engenheira de Software PL' model='claude-sonnet-4.6' cwd='/home/breno/pipes/pipe/repo/main' log='logs/25/2026-07-20_19-47-03.md'
```

**Depois:**
```
09:47:03 [Agent] [task] #25 "Log não descritivo" @ execucao-tratamento agent='Sofia Carvalho - Engenheira de Software PL' log='logs/25/2026-07-20_19-47-03.md'
```

Mudanças: adicionado o título da issue e o nome da etapa (coluna); removidos
`model` e `cwd` (ruído — já registrados no arquivo Markdown de log em
`logs/<issue_id>/<timestamp>.md`).

Arquivos alterados: `src/core/agent.py`, `src/__main__.py`,
`src/adapters/kiro_cli_agent.py`. Sem mudança de snapshot ou de fluxo
funcional. Suíte de testes: 199 passed, 3 skipped.

## Pré-requisitos no host

- Docker e Docker Compose instalados (validado neste ambiente: Docker
  29.6.2, Docker Compose v5.3.1).
- `gh auth login` executado no host (gera `~/.config/gh/`).
- Chave SSH configurada no GitHub (padrão `~/.ssh/id_ed25519`).
- Token do GitHub com escopos `repo` e `project`.
- Binário `kiro-cli` disponível no `PATH` do host (necessário para o
  `prepare-docker.sh` copiá-lo para o contexto de build — não é distribuído
  via repositório público).
- Um `pipe.yml` válido na raiz do projeto (não versionado — ver
  `README.md`, seção "Configuração → Arquivo pipe.yml", para o formato).

## Passo a passo

1. **Ir para a branch já mesclada com `main`:**
   ```bash
   cd /home/breno/pipes/pipe/repo/main
   git checkout hotfix27-27-log_nao_descritivo
   git pull
   ```

2. **Preparar o contexto de build (copia o binário `kiro-cli` do host):**
   ```bash
   ./prepare-docker.sh
   ```

3. **Criar o `.env` com o token do GitHub:**
   ```bash
   cp .env.example .env
   # Editar .env e preencher GH_TOKEN (escopos repo e project)
   # Opcional: SSH_KEY_FILE, GH_CONFIG_DIR se diferentes do padrão
   ```

4. **Garantir que existe um `pipe.yml` na raiz** (não versionado — copiar
   manualmente o arquivo de configuração do ambiente de homologação).

5. **Build e execução:**
   ```bash
   docker compose build
   docker compose up
   ```
   Para rodar em background:
   ```bash
   docker compose up -d
   docker compose logs -f
   ```

6. **Validar a correção:** ao chegar uma tarefa para execução de agente
   (coluna com `agent` configurado), observar no log de terminal (ou em
   `docker compose logs -f`) a linha `[Agent] ...`. Confirmar que ela mostra
   `"<título da issue>" @ <etapa>` em vez de `model='...' cwd='...'`.

7. **Para parar:**
   ```bash
   docker compose down
   ```
   Isso preserva os volumes (`pipe_state`, `pipe_repos`, `pipe_logs`). Para
   forçar um re-sync completo do zero, remova os volumes com
   `docker compose down -v` — **ação destrutiva**, use apenas se
   intencional, pois apaga snapshots, fila de sincronismo e índice de
   sessões persistidos.

## O que verificar na homologação

- [ ] `docker compose build` completa sem erro.
- [ ] `docker compose up` inicia a esteira sem erro de configuração.
- [ ] Ao executar um agente, a linha de log no terminal exibe título da
      issue entre aspas e o nome da etapa após `@`.
- [ ] `model` e `cwd` não aparecem mais na linha de log de terminal.
- [ ] O arquivo `logs/<issue_id>/<timestamp>.md` continua completo (título,
      etapa, model, cwd, prompt, chat) — nada foi removido do log em
      Markdown, apenas do log de terminal.

## Observações

- Não há branch de épico associada a esta issue: o fluxo `hotfix` do
  `pipe.yml` cria a partir de `main` e mescla em `main` diretamente. A
  preparação de pré-produção consistiu em mesclar `main` na branch
  `hotfix27-27-log_nao_descritivo` (fast-forward de conteúdo, sem conflitos)
  para garantir que a homologação rode sobre o estado mais recente do
  projeto (Docker, docs, testes, etc. adicionados por outras branches já
  mescladas em `main`).
- Nenhum comando destrutivo foi executado neste preparo.

— Isabela Gomes - Tech Lead
