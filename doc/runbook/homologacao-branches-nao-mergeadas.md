# Runbook de Homologação — Branches não mergeadas (#73)

> Etapa: Pré-produção → Homologação
> Épico: #73 "Branches não mergeadas"
> Pré-requisito: leia `doc/runbook/docker.md` para a operação geral do
> ambiente Docker Compose (build, subida, logs, parar/reiniciar). Este
> documento cobre apenas o que é específico da homologação do épico #73.

## O que este épico entregou

O épico #73 tratou o acúmulo de branches não mergeadas do repositório
(faxina pontual — sem mudança de processo ou automação de encerramento).
As três user stories filhas concluíram:

| Story | Entrega | Estado |
|-------|---------|--------|
| #74 — Remoção segura do resíduo já integrado | 12 branches confirmadas como já integradas em `main`/`epic` removidas do remoto | Encerrada |
| #75 — Limpeza de branches órfãs de tarefas arquivadas | 8 branches órfãs removidas; 2 (`hotfix23`, `hotfix24`) preservadas em branches de merge dedicadas (`temp-hotfix23-merge`, `temp-hotfix24-merge`) para decisão sobre manter o ticket de incidente em `main`/`epic` | Encerrada |
| #76 — Consolidação de duplicidade e nomenclatura antiga | Branch de nomenclatura antiga `feature/1` removida; duplicata #46/#47 consolidada; issue renomeada para refletir a entrega real | Encerrada |

Evidência detalhada de cada decisão (branch a branch, com a razão e a
verificação usada): `doc/product/branchs-nao-mergeadas/panorama-branches.md`.

**Natureza da entrega:** operações de `git branch`/`git push --delete` no
remoto — não há código de produto novo em `src/`. Por isso a branch
`epic73-73-branchs_nao_mergeadas` não carrega commits de código; ela recebeu
apenas a documentação de negócio e o merge de `main` (para trazer o código de
produção mais recente e permitir a homologação do ambiente).

## O que NÃO faz parte desta homologação

- Não há funcionalidade nova de aplicação para testar manualmente na UI ou
  via chamadas — a mudança é higiene de repositório.
- A homologação aqui é: (1) validar que o ambiente Docker sobe normalmente
  com o código atual da `main` mesclado nesta branch, e (2) validar, por
  inspeção do repositório remoto, que o estado das branches corresponde ao
  documentado no panorama.

## Passo 1 — Validar o estado das branches no remoto

Sem precisar do container, valide diretamente com `git`/`gh` que a faxina
foi aplicada:

```bash
git fetch origin
git branch -a | sed 's/remotes\/origin\///' | sort
```

Confirme que:
- As branches listadas em `panorama-branches.md`, seção "resíduo já
  integrado" (12 branches, ex.: `feature7-7-...`, `hotfix5-5-...`,
  `feature28-28-...` etc.) **não aparecem** mais na lista.
- As 8 branches órfãs absorvidas (`epic16` a `epic21`, `epic36`, `hotfix27`)
  **não aparecem**.
- `temp-hotfix23-merge` e `temp-hotfix24-merge` existem (preservação
  temporária, pendente de decisão — não é bug).
- `feature/1-1-rodar_no_docker` (nomenclatura antiga) **não aparece**.
- `main`, `epic` e as branches de tarefas ativas continuam intactas.

## Passo 2 — Subir o ambiente Docker Compose com o código mesclado

Esta branch (`epic73-73-branchs_nao_mergeadas`) já contém o merge de `main`,
então o ambiente sobe com o código de produção mais recente. Siga o
[runbook geral](docker.md) a partir do Passo 2 (o repositório já está
clonado):

```bash
cd /app/repo/main
cp .env.example .env
# edite .env: GH_TOKEN, KIRO_API_KEY, SSH_KEY_FILE_HOST, PIPE_STATE_DIR/PIPE_REPO_DIR/PIPE_LOGS_DIR
# crie o pipe.yml na raiz conforme o README (não versionado)

docker compose build
docker compose up -d
docker compose logs pipe -f
```

Saída esperada de arranque bem-sucedido (mesma do runbook geral):

```
[Config]   pipe.yml válido
[Startup]  Verificando repositórios
[Board]    Sincronizando estrutura local
[Board]    Sincronizando boards remotos
[Sleep]    Nenhuma atividade - dormindo 60s (retorna às ...)
```

Se preferir estado acessível no host (logs/`.pipe`/`repo` fora de named
volumes), use o override de desenvolvimento:

```bash
docker compose -f docker-compose.yml -f compose.dev.yml up -d
```

## Passo 3 — Critérios de aceite da homologação

- [ ] `docker compose build` conclui sem erro com o código desta branch.
- [ ] `docker compose up -d` inicia o container e o log mostra o fluxo
      `[Config]` → `[Startup]` → `[Board]` sem erro.
- [ ] `docker compose ps` mostra o serviço `pipe` em execução (`Up`).
- [ ] O panorama de branches (Passo 1) confirma a remoção das branches de
      resíduo/órfãs e a ausência da nomenclatura antiga.
- [ ] Nenhuma branch de tarefa ativa (`main`, `epic`, e as branches das
      issues em andamento no momento da homologação) foi removida.
- [ ] `temp-hotfix23-merge`/`temp-hotfix24-merge` seguem preservadas até
      decisão explícita sobre incorporar o histórico de incidente.

## Passo 4 — Encerrar o ambiente após a homologação

```bash
docker compose down       # preserva volumes/estado
# ou, para limpeza completa do estado de teste:
docker compose down -v
```

## Pendências conhecidas (fora do escopo desta homologação)

- Decisão sobre `hotfix23`/`hotfix24`: preservar o ticket de incidente em
  `main`/`epic` como histórico ou descartar. Registrado em
  `doc/product/branchs-nao-mergeadas/stories/limpeza-branches-orfas-arquivadas.md`.
- O desalinhamento entre `origin/epic` e `origin/main` (débito de issue
  separada, #165/#146/#147) é anterior a este épico e não faz parte do seu
  escopo; `tests/test_epic_merge_ausente_146_147.py` documenta esse débito
  de forma independente.
