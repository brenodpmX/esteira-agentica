# Change File — Post-Mortem de Produto — Incidente reportado em 01/08/2026

**Data:** 2026-08-05
**Issue:** #104 — Post-Mortem de Produto — Incidente reportado em 01/08/2026
**Branch:** `epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026`
**Versão:** 1.7.0
**Status:** pré-produção (aguardando homologação humana)

## Resumo

Esta etapa preparou o ambiente pré-produtivo para homologação do épico. O
épico #104 é, até este ponto, **exclusivamente documental**: consolida o
post-mortem do incidente #97 ("parent recursivo") em artefatos de Produto,
Requisitos, Arquitetura e User Stories, e decompõe a correção em cinco frentes
(C1–C5) rastreadas como user stories filhas (#138–#142) ainda ativas no board
`story`. Nenhum código de correção das cinco frentes foi implementado nesta
branch — a implementação está sob responsabilidade das user stories filhas,
que continuam bloqueando o fechamento de #104.

## Alterações entregues nesta branch

### Documentação de Produto

- `doc/product/confiabilidade-parent-recursivo/problem-space.md`
- `doc/product/confiabilidade-parent-recursivo/vision.md`
- `doc/product/confiabilidade-parent-recursivo/post-mortem.md`

### Documentação de Requisitos

- `doc/product/confiabilidade-parent-recursivo/epicos.md` — 5 épicos (um por
  frente C1–C5).
- `doc/requirements/confiabilidade-parent-recursivo/business-rules.md` —
  RN-001 a RN-010.
- `doc/requirements/confiabilidade-parent-recursivo/non-functional-requirements.md`

### Documentação de Arquitetura

- `doc/architecture/confiabilidade-parent-recursivo/arquitetura.md` — desenho
  hexagonal sem novos serviços/infraestrutura: resolução determinística de
  body, sanitização de auto-referência, erros tipados com
  tentativa/rotação/dead-letter, guarda de integridade de snapshot e
  exclusividade via `fcntl.flock`.
- `CONTEXT.md` atualizado para referenciar a nova arquitetura.

### User Stories

- `doc/stories/confiabilidade-parent-recursivo/user-stories.md` — US-01 a
  US-05, cada uma mapeada 1:1 a uma frente C1–C5 e criada como issue filha em
  `story/backlog` (#138–#142).

## Merge com `main`

A branch do épico estava 3 commits atrás de `main` (`origin/main`), que havia
evoluído de forma independente:

- `feat(loop): descoberta local global por ciclo (desacopla up de down)` —
  refatora `sync_board` em `detect_local_all` + `sync_remote_board`.
- `style(banner): ajusta caracteres do banner ASCII`.
- `test(sync): regressão para create-up de body com slug em underscore`.

O merge de `main` na branch do épico foi automático (estratégia `ort`), sem
conflitos — a branch do épico só havia tocado documentação, `README.md` e
`CONTEXT.md`. `CONTEXT.md` teve merge automático de ambos os lados (referência
à nova arquitetura preservada de um lado, refatoração do loop preservada do
outro).

## Validação realizada

- `git diff --check` entre `main` e a branch do épico: sem problemas de
  whitespace.
- Todos os 8 artefatos documentais do épico presentes e íntegros após o merge.
- Suíte de testes: **211 aprovados, 3 ignorados** (inclui os dois arquivos de
  teste trazidos por `main`: `test_create_up_underscore_slug.py` e
  `test_detect_local_all.py`).
- Build Docker (`docker compose build`) concluído sem erros com o código
  pós-merge.
- Versões confirmadas na imagem: Python 3.12.13, git 2.47.3, gh 2.94.0,
  kiro-cli 2.16.0, PyYAML 6.0.3.
- Smoke test `docker compose run --rm pipe kiro-cli chat --help` executado com
  sucesso (launcher + `kiro-cli-chat` respondendo corretamente).
- `docker compose config` validado com `.env.example` — todos os volumes,
  variáveis e binds resolvem corretamente.
- Ambiente de build (binários `kiro-cli`/`kiro-cli-chat`, volumes e containers
  de teste) removido após a validação; nenhum artefato binário foi versionado
  (`.gitignore` confirmado).

## Compatibilidade e limitações

- Nenhuma mudança de comportamento runtime nesta etapa — o merge trouxe apenas
  a evolução já existente em `main` (refatoração do loop de descoberta), sem
  alteração funcional relacionada ao épico #104.
- As cinco frentes de correção (C1–C5 / US-01–US-05) **não estão presentes**
  nesta branch. O incidente #97 permanece "mitigado, com risco residual" até
  a implementação e homologação conjunta de #138–#142.
- Distribuição Docker permanece válida apenas para Linux `amd64` (herdado do
  epic #1 "Rodar no Docker").

## Instruções para homologação em pré-produção

### Pré-requisitos no host de homologação

- Docker Engine com Docker Compose V2 (`docker compose`).
- `kiro-cli` completo (launcher + `kiro-cli-chat`) instalado no `PATH`.
- Chave SSH registrada no GitHub.
- Token do GitHub com escopos `repo` e `project`.
- API key do Kiro (`app.kiro.dev` → API Keys).

### Passo a passo

1. **Obter o código desta branch:**
   ```bash
   git fetch origin
   git checkout epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026
   ```

2. **Preparar o contexto de build** (copia os binários do Kiro CLI do host
   para a raiz do repositório; não é versionado):
   ```bash
   ./prepare-docker.sh
   ```
   Verifique que a saída confirma a cópia de **ambos** `kiro-cli` e
   `kiro-cli-chat`. Copiar somente o launcher causa
   `No such file or directory (os error 2)` na execução do agente.

3. **Configurar credenciais:**
   ```bash
   cp .env.example .env
   ```
   Preencha `GH_TOKEN`, `KIRO_API_KEY` e, se necessário, `SSH_KEY_FILE` /
   `GH_CONFIG_DIR` (os padrões servem na maioria dos hosts).

4. **Configurar a esteira:** crie `pipe.yml` na raiz (não versionado) e os
   contextos de agente em `contexts/<plataforma>/<agente>.md`, apontando para
   o board/projeto de homologação (recomenda-se um board de teste, não o
   board de produção, para não interferir no board real do épico #104).

5. **Construir e iniciar:**
   ```bash
   docker compose build
   docker compose up -d
   docker compose logs -f
   ```

6. **Smoke test dos binários embarcados:**
   ```bash
   docker compose run --rm pipe kiro-cli chat --help
   ```
   Deve exibir o help do subcomando `chat` sem erro de binário ausente.

7. **Verificar inicialização saudável:** nos logs, confirmar nesta ordem
   geral: validação do `pipe.yml`, verificação dos repositórios,
   sincronização dos boards, início da esteira e seleção/execução de tarefas.

8. **O que homologar neste épico especificamente:**
   - Confirmar que o merge com `main` não alterou comportamento observável do
     loop principal (a refatoração de `detect_local_all`/`sync_remote_board`
     em `sync_board` é interna; o comportamento externo — descoberta local
     global por ciclo + descoberta remota por board na rotação — deve ser
     idêntico ao já homologado em `main`).
   - Confirmar que os documentos do épico estão acessíveis e íntegros no
     repositório (`doc/product/`, `doc/requirements/`,
     `doc/architecture/`, `doc/stories/` em `confiabilidade-parent-recursivo/`).
   - **Não** homologar as cinco correções C1–C5 nesta etapa — elas ainda não
     foram implementadas; serão homologadas quando as user stories filhas
     (#138–#142) chegarem a esta mesma etapa.

9. **Encerrar o ambiente:**
   ```bash
   docker compose down       # preserva volumes
   docker compose down -v    # remove também estado persistido
   ```
   Após o teste, remova os binários copiados (`kiro-cli`, `kiro-cli-chat`) da
   raiz do repositório se não forem reutilizar o contexto de build.

### Aprovação esperada

Como este épico ainda não contém as correções C1–C5, a homologação nesta
etapa deve confirmar apenas: (a) o ambiente sobe corretamente com o código
mesclado; (b) a suíte de testes e o smoke test do Kiro CLI passam; e (c) a
documentação do épico está completa e coerente com o que foi aprovado nas
etapas anteriores (Negócio, Requisitos, Arquitetura, Stories). A resolução
definitiva do incidente #97 continua condicionada à entrega e homologação de
US-01 a US-05.
