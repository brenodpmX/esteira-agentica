# ADR-0173 — Arquitetura Docker canônica

- **Status:** Aceita
- **Data:** 2026-08-06
- **Issue:** #173
- **Desbloqueia:** #165

## Contexto

As linhas `main` e `epic` implementaram em paralelo contratos incompatíveis para a imagem Docker: execução como `root` versus usuário dedicado, chave SSH por bind mount versus secret e `kiro-cli` copiado do host versus instalado durante o build. A ausência de uma decisão canônica tornou o merge da #165 semanticamente ambíguo.

Esta decisão prioriza menor privilégio, build reproduzível, ausência de artefatos locais implícitos e continuidade das sessões do agente. Não depende de definição de produto ou UX.

## Decisão

### 1. Privilégios e identidade

A imagem pode usar `root` **somente nas camadas de build** que instalam pacotes e preparam diretórios. O processo de runtime deve executar como usuário dedicado `pipe`, com UID e GID determinísticos `1000`, sem `sudo` e sem capacidade de elevar privilégios.

Antes de `USER pipe`, o Dockerfile deve criar e atribuir a `pipe:pipe` todos os caminhos graváveis:

- `/app/.pipe`
- `/app/repo`
- `/app/logs`
- `/home/pipe/.kiro`
- `/home/pipe/.local/share/kiro-cli`

Isso evita que volumes inicialmente vazios sejam materializados com ownership incompatível. Configuração e contextos montados do host permanecem somente leitura.

### 2. Instalação do `kiro-cli`

O `kiro-cli` deve ser instalado **dentro da imagem**, como usuário `pipe`, a partir de artefato oficial para Linux. O build deve fixar:

1. versão exata;
2. URL imutável que identifique essa versão, sem alias `latest`;
3. SHA-256 esperado, validado antes da instalação;
4. smoke test `kiro-cli --version`, que deve corresponder à versão declarada.

O binário fica disponível pelo `PATH` da imagem (`/home/pipe/.local/bin`). É proibido depender da versão instalada na máquina do operador ou copiar um binário preparado pelo host. Portanto, `prepare-docker.sh` deixa de fazer parte do fluxo canônico e deve ser removido na reconciliação da #165.

Se o fornecedor não oferecer URL imutável, o artefato deve ser promovido para repositório controlado e endereçado por versão/digest; apontar para `latest` com checksum antigo apenas transforma uma atualização upstream em quebra não determinística do build.

### 3. Código-fonte e contexto de build

Mantém-se o modelo da linha `epic`: o Dockerfile obtém o código por `git clone` durante o build. A referência é recebida por `PIPE_REF`; builds de produção devem usar tag ou SHA imutável, e não uma branch móvel.

A chave necessária ao clone deve entrar apenas como **BuildKit secret**. O Compose deve declarar explicitamente `build.secrets: [ssh_key]`; declarar somente o secret de runtime não o disponibiliza ao build.

Como nenhum arquivo da aplicação é copiado do contexto local, `.dockerignore` contendo apenas `*` é uma allowlist vazia deliberada e válida. Ela reduz o contexto e impede envio acidental de `.env`, chaves, logs e estado local ao daemon. Se no futuro o build migrar para `COPY`, a alteração do Dockerfile e as negações mínimas no `.dockerignore` devem ocorrer atomicamente e ser cobertas por teste.

### 4. Credencial SSH em runtime

A chave SSH deve ser exposta pelo Compose como secret em `/run/secrets/ssh_key`, somente leitura, e `PIPE_SSH_KEY_FILE` deve apontar para esse caminho interno. A chave nunca deve ser:

- copiada para uma camada da imagem;
- passada por `ARG` ou variável de ambiente;
- montada em `/root/.ssh`;
- registrada em logs.

O arquivo de origem continua no host, informado por `SSH_KEY_FILE_HOST`. Compose secrets não substituem um cofre nem criptografam o arquivo de origem; esta decisão limita a exposição dentro do container e separa o contrato do host do caminho interno. As permissões devem ser as mais restritivas suportadas que ainda permitam leitura pelo UID 1000.

### 5. Volumes e HOME

Os nomes canônicos usam hífen e não underscore:

| Volume | Destino | Finalidade |
|---|---|---|
| `pipe-state` | `/app/.pipe` | estado interno e continuidade da esteira |
| `pipe-repo` | `/app/repo` | clones de trabalho |
| `pipe-logs` | `/app/logs` | logs operacionais |
| `kiro-home` | `/home/pipe/.kiro` | configuração do Kiro |
| `kiro-local` | `/home/pipe/.local/share/kiro-cli` | dados e sessões locais do Kiro |

Os dois volumes do Kiro são parte do contrato não-root: não se deve redirecionar HOME para `/root` nem perder sessões a cada recriação. Renomear volumes existentes exige migração explícita; uma simples troca de nome cria volumes vazios.

### 6. Encerramento por SIGTERM

A suíte canônica testa comportamento, não forma de implementação. Deve permanecer o teste com `monkeypatch` que executa `main()`, observa o registro de `SIGTERM` e comprova o encerramento por `_Shutdown`. Testes baseados apenas em AST são rejeitados porque podem passar sem validar o comportamento e acoplam a suíte à estrutura textual. Não se mantêm duas suítes redundantes para a mesma garantia.

## Alternativas rejeitadas

- **Runtime como root:** simplifica permissões, mas amplia o impacto de comprometimento do agente e mascara ownership incorreto de volumes.
- **Copiar `kiro-cli` do host:** torna o build dependente do estado da workstation, arquitetura do host e execução manual de script.
- **Download por `latest`:** não representa a versão declarada e quebra a reprodutibilidade.
- **Bind mount em `/root/.ssh`:** acopla a aplicação à identidade root e amplia a superfície de credenciais.
- **Volumes com underscore sem HOME do Kiro:** preservam o contrato legado de `main`, mas não atendem ao runtime não-root nem à continuidade das sessões.
- **Teste SIGTERM somente por AST:** valida texto, não o contrato operacional.

## Impacto e critérios para a reconciliação da #165

A #165 deve resolver os oito conflitos conforme esta ADR:

1. preservar `USER pipe` e preparar ownership dos diretórios antes da troca de usuário;
2. preservar instalação interna do Kiro, trocando URL `latest` por origem imutável e eliminando `prepare-docker.sh`;
3. preservar secrets de build/runtime e adicionar `build.secrets` no Compose;
4. preservar volumes com hífen, incluindo `kiro-home` e `kiro-local`;
5. manter `.dockerignore` como `*` enquanto não houver `COPY` local;
6. preservar o teste comportamental de SIGTERM com `monkeypatch`;
7. reconciliar `src/__main__.py`, `src/adapters/kiro_cli_agent.py` e `src/core/sync.py` pelo comportamento mais recente de `epic`, sem reintroduzir variantes antigas apenas para satisfazer conflito textual;
8. atualizar README, runbook e testes para um único contrato.

Validação mínima da implementação resultante:

```bash
docker compose config
docker compose build
docker compose up -d
docker compose exec pipe sh -lc 'test "$(id -u)" = 1000 && test "$(id -g)" = 1000 && kiro-cli --version'
python -m pytest tests/test_dockerfile.py tests/test_docker_compose.py tests/test_sigterm_shutdown.py -v
```

A subida deve ocorrer sem erro de permissão em qualquer volume e sem expor a chave na imagem ou no ambiente do processo.
