# Change File — Pré-produção: Post-Mortem de Produto (#104), C1–C5 integradas

**Data:** 2026-08-19
**Issue:** #104 — Post-Mortem de Produto — Incidente reportado em 01/08/2026
**Branch:** `epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026`
**Status:** pré-produção (aguardando homologação humana)

## Resumo

Esta execução repete a preparação do ambiente pré-produtivo do épico #104
após a conclusão das cinco user stories filhas (#138–#142, frentes C1–C5 do
incidente #97). Ao contrário da entrega anterior
(`104-post_mortem_de_produto_incidente_reportado_em_01082026.md`, 05/08), que
era exclusivamente documental, esta branch agora está sincronizada com `main`
e **inclui as cinco correções de código já implementadas e mescladas em
produção**:

- **C1 — Associação segura** (US-03/#140): resolução determinística do body
  da issue por identidade (#146); detecção de arquivos órfãos sem match
  confiável (#147), sem alterar issues.
- **C2 — Relações válidas** (US-01/#138): sanitização de auto-referência em
  `parent`/`children`/`blocked_by`/`blocks` (#143) antes de qualquer chamada
  ao board.
- **C3 — Falha isolada** (US-02/#139): classificação de erros de sincronismo
  e fim do head-of-line blocking na fila global (#144/#145).
- **C4 — Estado protegido** (US-04/#141): `SnapshotGuard`/
  `SnapshotIntegrityError` (#149) — captura, compara e restaura o snapshot ao
  redor da execução do agente.
- **C5 — Instância única** (US-05/#142): `InstanceLock`/`LockHeldError`
  (#150/#151/#152), integrado a `main()` com recusa fail-fast antes do
  `startup()`. A integração havia ficado presa apenas em `epic`; a
  reconciliação #196 promoveu-a para `main`.

## Alterações desta execução

- Merge de `origin/main` (200 commits) na branch do épico, que estava apenas
  6 commits adiante de um ponto muito anterior de `main`.
- Conflito único em `CONTEXT.md`, resolvido substituindo a seção "Arquitetura
  planejada: confiabilidade Parent Recursivo" (que descrevia C1–C5 como
  pendentes) por uma seção que documenta as cinco frentes como entregues,
  com rastreabilidade às issues/commits de cada uma.
- Nenhuma alteração em `src/`: `git diff --stat` contra `origin/main` confirma
  que a branch do épico não diverge em código, apenas nos artefatos
  documentais do próprio épico (Produto, Requisitos, Arquitetura, Stories) e
  no `CONTEXT.md`.

## Validação realizada

- `git diff --check` (whitespace) entre a branch mesclada e `origin/main`: sem
  problemas.
- Os 9 artefatos documentais do épico confirmados presentes e íntegros após o
  merge (`doc/product/`, `doc/requirements/`, `doc/architecture/`,
  `doc/stories/confiabilidade-parent-recursivo/`, e o changelog anterior).
- Suíte de testes (`pytest tests/ -q`): **1121 aprovados, 28 ignorados, 1
  xpassed, 24 falhas**. As 24 falhas foram comparadas linha a linha contra a
  mesma suíte executada em `origin/main` sem o merge — são **idênticas e
  pré-existentes**, não introduzidas por esta integração. Categorias:
  - `test_agent_log_descritivo.py` (15) e `test_agent_failure_detection.py`
    (1): formato de log em revisão, não relacionado a #104.
  - `test_dockerfile.py` (3): `KIRO_CLI_SHA256` não referenciado na
    verificação de hash do Dockerfile atual — gap real, pré-existente,
    fora do escopo deste épico.
  - `test_epic_merge_ausente_146_147.py` (2): compara `HEAD` contra
    `origin/epic` (branch agregadora de integração), não contra `origin/main`;
    não se aplica ao fluxo desta issue.
  - Falhas remanescentes de bootstrap de referência local (ex.: refs git
    inexistentes no ambiente do agente).
- Validação estática dos arquivos de compose (`docker-compose.yml`,
  `compose.dev.yml`, `compose.ephemeral.yml`): parseados com sucesso via
  `yaml.safe_load`, estrutura de `services`/`secrets`/`volumes` íntegra.
- Suíte estrutural Docker (`test_docker_compose.py`, `test_dockerfile.py`,
  `test_docker_runbook.py`, `test_versions_env.py`): 213 aprovados, 24
  ignorados, as mesmas 3 falhas pré-existentes de `KIRO_CLI_SHA256` acima.

### Limitação desta validação

O ambiente de execução desta tarefa **não tem o daemon Docker disponível**
(`docker`/`docker compose` inexistentes no sandbox do agente). Portanto,
**não foi possível** executar `docker compose build`, `docker compose up` ou
o smoke test do `kiro-cli` nesta rodada — diferente da entrega anterior
(05/08), que rodou em ambiente com Docker. A validação aqui se limitou a:
análise estática dos arquivos de compose/Dockerfile, suíte de testes
automatizada (que cobre a estrutura do Dockerfile/compose via parsing, não
via build real) e revisão do runbook existente.

**A homologação humana em pré-produção deve, portanto, executar o build e o
smoke test reais** (passo a passo abaixo), já que este agente não pôde
confirmá-los diretamente nesta rodada.

## Compatibilidade

- Sem mudança de schema do `pipe.yml`.
- Sem mudança de volumes ou variáveis de ambiente do compose nesta etapa —
  as mudanças de `PIPE_STATE_DIR`/`PIPE_REPO_DIR`/`PIPE_LOGS_DIR` e do
  Docker secret de SSH já estavam em `main` antes deste merge.
- O Dockerfile atual **baixa o `kiro-cli` durante o build** (não requer mais
  cópia manual de binários do host, ao contrário do procedimento descrito na
  entrega documental anterior de 05/08, já obsoleto).

## Instruções para homologação em pré-produção

### Pré-requisitos no host de homologação

- Docker Engine com Docker Compose V2 (`docker compose`, sem hífen).
- Chave SSH registrada no GitHub (usada como Docker secret no build e no
  runtime).
- Token do GitHub (`GH_TOKEN`) com escopos `repo` e `project`.
- API key do Kiro (`KIRO_API_KEY`), plano Pro/Pro+ ou superior, gerada em
  `app.kiro.dev` → **API Keys**.
- Não é necessário instalar `kiro-cli` nem `gh` no host: o build os baixa nas
  versões pinadas em `docker/versions.env` (validadas por SHA-256).

### Passo a passo

1. **Obter o código desta branch:**
   ```bash
   git fetch origin
   git checkout epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026
   ```

2. **Configurar credenciais:**
   ```bash
   cp .env.example .env
   ```
   Preencha `GH_TOKEN`, `KIRO_API_KEY` e `SSH_KEY_FILE_HOST` (caminho
   **absoluto** da chave privada no host — o compose não expande `~` em
   `secrets.file`). Não defina `PIPE_SSH_KEY_FILE`: é fixado pelo compose como
   `/run/secrets/ssh_key`.

3. **Configurar a esteira:** crie `pipe.yml` na raiz (não versionado, ver
   exemplo no `README.md`) e os contextos de agente em
   `contexts/<plataforma>/<agente>.md`. Recomenda-se apontar para um board de
   homologação/teste, não para o board de produção real do épico #104, para
   não interferir na issue em andamento.
   ```bash
   mkdir -p .pipe repo logs   # cria com posse do seu usuário, evita criação como root
   ```

4. **Construir a imagem:**
   ```bash
   docker compose build
   ```
   Confirme que o build conclui sem erro de SHA-256 do `kiro-cli` ou do `gh`
   (ver tabela de solução de problemas no `README.md` caso falhe).

5. **Validar a configuração do compose antes de subir:**
   ```bash
   docker compose config
   ```
   Confirme que os volumes, variáveis e o secret SSH resolvem corretamente
   (sem erros de variável ausente).

6. **Subir a esteira:**
   ```bash
   docker compose up -d
   docker compose logs -f
   ```

7. **Smoke test do kiro-cli embarcado na imagem:**
   ```bash
   docker compose run --rm pipe kiro-cli chat --help
   ```
   Deve exibir o help do subcomando `chat` sem erro de binário ausente.

8. **Verificar inicialização saudável** nos logs, na ordem: validação do
   `pipe.yml` → verificação/clone dos repositórios → sincronização dos
   boards → início do loop principal.

9. **O que homologar neste épico especificamente:**
   - Confirmar que o ambiente sobe com o código de `main` mesclado, incluindo
     as cinco correções C1–C5 (`InstanceLock`, `SnapshotGuard`, sanitização de
     auto-referência, classificação de erros/dead-letter, resolução
     determinística de body).
   - Confirmar que os 9 artefatos documentais do épico
     (`doc/product/`, `doc/requirements/`, `doc/architecture/`,
     `doc/stories/confiabilidade-parent-recursivo/`) estão presentes,
     acessíveis e coerentes com as aprovações de Negócio, Requisitos,
     Arquitetura e Stories já registradas no histórico da issue.
   - Confirmar, se possível, um teste dirigido de reprodução do cenário do
     incidente #97 (auto-referência em `/parent`) — a suíte automatizada já
     cobre isso (`tests/test_regressao_colisao_76.py`,
     `tests/test_sanitize_relations.py`), mas a homologação em pré-produção
     pode repetir manualmente para confiança adicional antes da liberação em
     produção.

10. **Encerrar o ambiente:**
    ```bash
    docker compose down       # preserva volumes nomeados
    docker compose down -v    # remove também todo o estado persistido
    ```

### Aprovação esperada

A homologação nesta etapa deve confirmar: (a) o ambiente sobe corretamente
com o código de `main` (incluindo C1–C5) mesclado à branch do épico; (b) o
build e o smoke test do `kiro-cli` funcionam de ponta a ponta em um host com
Docker real (não confirmado pelo agente nesta rodada); e (c) a documentação
do épico está completa e coerente com as aprovações anteriores. Após esta
homologação, o incidente #97 pode ser reclassificado — a decisão final de
"resolvido" versus "mitigado" cabe à homologação humana, não a este agente.

— Isabela Gomes - Tech Lead
