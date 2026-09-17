# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Build (o código da esteira entra via COPY do contexto — ver Camada 8):
#
#   docker compose build && docker compose up
#
# O `src/` é provisionado no contexto de build pelo Makefile (fetch-app da
# branch de produção). Não requer secret SSH nem build-arg de ref.

# ---------------------------------------------------------------------------
# Camada 2 — Dependências de sistema
# Pacotes em único RUN para minimizar camadas (ADR-02)
# Versões pinadas conforme docker/versions.env (ADR-04)
# gnupg não necessário: repositório APT do gh usa keyring binário via curl
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        git=1:2.47.3-0+deb13u1 \
        openssh-client=1:10.0p1-7+deb13u4 \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Camada 3 — GitHub CLI (gh)
# Instala o .deb pinado direto das releases do GitHub (github.com/cli/cli/releases),
# que ficam arquivadas permanentemente -> pin exato reproduzivel.
# NAO usar o repo APT https://cli.github.com/packages: ele serve APENAS a ultima
# versao publicada, entao qualquer pin exato quebra na proxima release do gh
# (E: Version 'X' for 'gh' was not found). Historico: 2.96.0 -> 2.97.0 -> 2.101.0.
# Versao pinada conforme docker/versions.env (ADR-04).
# ---------------------------------------------------------------------------
ARG GH_VERSION=2.101.0
RUN curl --proto '=https' --tlsv1.2 -fsSL \
        "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.deb" \
        -o /tmp/ghcli.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/ghcli.deb \
    && rm -rf /tmp/ghcli.deb /var/lib/apt/lists/*
RUN gh --version

# ---------------------------------------------------------------------------
# Camada 4 — PyYAML
# Versão pinada conforme docker/versions.env (ADR-04)
# ---------------------------------------------------------------------------
RUN pip install --no-cache-dir pyyaml==6.0.2

# ---------------------------------------------------------------------------
# Camada 4.5 — Toolchain de dev/test para agentes (Opção B: Docker-in-Docker)
# Instalada como root (system-wide) ANTES do usuário pipe. Versões pinadas
# conforme docker/versions.env (ADR-04). Binários baixados por URL (mesmo padrão
# do gh/kiro-cli) — o Dockerfile só tem UM COPY (o do src), sem multi-stage.
#
# Componentes:
#   - cliente docker (binário estático oficial; só o client 'docker')
#   - plugins docker compose v2 + buildx (em /usr/local/lib/docker/cli-plugins)
#   - jq (usado pelos orquestradores dev.sh / run.sh do produto)
#   - JDK Temurin 21 + Apache Maven (build/testes do backend Spring Boot)
# O daemon NÃO roda aqui: vive no sidecar docker:dind (ver docker-compose.yml);
# o agente fala com ele via DOCKER_HOST=tcp://127.0.0.1:2375.
# ---------------------------------------------------------------------------
ARG DOCKER_CLI_URL=https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz
ARG DOCKER_COMPOSE_URL=https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64
ARG DOCKER_BUILDX_URL=https://github.com/docker/buildx/releases/download/v0.17.1/buildx-v0.17.1.linux-amd64
ARG JQ_URL=https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-linux-amd64
ARG TEMURIN_JDK_URL=https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_linux_hotspot_21.0.5_11.tar.gz
ARG MAVEN_URL=https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz

RUN set -eux; \
    # cliente docker (extrai apenas o binário 'docker' do tgz estático)
    curl --proto '=https' --tlsv1.2 -fsSL "$DOCKER_CLI_URL" -o /tmp/docker.tgz; \
    tar -xzf /tmp/docker.tgz -C /usr/local/bin --strip-components=1 docker/docker; \
    rm -f /tmp/docker.tgz; \
    # plugins docker (compose v2 + buildx)
    mkdir -p /usr/local/lib/docker/cli-plugins; \
    curl --proto '=https' --tlsv1.2 -fsSL "$DOCKER_COMPOSE_URL" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose; \
    curl --proto '=https' --tlsv1.2 -fsSL "$DOCKER_BUILDX_URL" \
        -o /usr/local/lib/docker/cli-plugins/docker-buildx; \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose \
             /usr/local/lib/docker/cli-plugins/docker-buildx; \
    # jq
    curl --proto '=https' --tlsv1.2 -fsSL "$JQ_URL" -o /usr/local/bin/jq; \
    chmod +x /usr/local/bin/jq; \
    # JDK Temurin 21 + Maven em /opt, com symlinks estáveis /opt/java e /opt/maven
    mkdir -p /opt/java /opt/maven; \
    curl --proto '=https' --tlsv1.2 -fsSL "$TEMURIN_JDK_URL" -o /tmp/jdk.tgz; \
    tar -xzf /tmp/jdk.tgz -C /opt/java --strip-components=1; \
    rm -f /tmp/jdk.tgz; \
    curl --proto '=https' --tlsv1.2 -fsSL "$MAVEN_URL" -o /tmp/maven.tgz; \
    tar -xzf /tmp/maven.tgz -C /opt/maven --strip-components=1; \
    rm -f /tmp/maven.tgz; \
    # smoke tests (falha cedo no build se algo não instalou)
    docker --version; \
    docker compose version; \
    docker buildx version; \
    jq --version; \
    JAVA_HOME=/opt/java /opt/java/bin/java -version; \
    JAVA_HOME=/opt/java /opt/maven/bin/mvn -version

# ---------------------------------------------------------------------------
# Camada 5 — Usuário não-root (ADR-05)
# uid determinístico 1000; HOME gravável para ~/.ssh e sessões do kiro-cli
# ---------------------------------------------------------------------------
RUN useradd --create-home --uid 1000 pipe
WORKDIR /app
RUN chown pipe:pipe /app
USER pipe

# Diretórios montados como named volumes em runtime (ver docker-compose.yml).
# Criados como 'pipe' para que cada volume — vazio na primeira criação — herde a
# posse pipe:pipe. Sem isto, o Docker cria o mountpoint como root e o usuário
# não-root falha ao escrever (PermissionError em logs/, .pipe/, repo/, ~/.kiro).
RUN mkdir -p /app/.pipe /app/repo /app/logs /home/pipe/.kiro

# ---------------------------------------------------------------------------
# Camada 6 — kiro-cli (ADR-03)
# Instalado como usuário pipe → ~/.local/bin (PATH ainda não inclui esse dir)
# Smoke test usa path absoluto: ENV PATH só é definido na camada seguinte
# ---------------------------------------------------------------------------
ARG KIRO_CLI_VERSION=2.18.0
ARG KIRO_CLI_URL=https://desktop-release.q.us-east-1.amazonaws.com/latest/kirocli-x86_64-linux.zip

RUN curl --proto '=https' --tlsv1.2 -fsSL "$KIRO_CLI_URL" -o /tmp/kirocli.zip \
    && unzip -q /tmp/kirocli.zip -d /tmp/kirocli_extract \
    && /tmp/kirocli_extract/kirocli/install.sh --no-confirm \
    && rm -rf /tmp/kirocli.zip /tmp/kirocli_extract \
    && ~/.local/bin/kiro-cli --version

# ---------------------------------------------------------------------------
# Camada 7 — Variáveis de ambiente
# PATH inclui ~/.local/bin onde kiro-cli foi instalado
# XDG_RUNTIME_DIR=/tmp necessário para kiro-cli em container
# ---------------------------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    XDG_RUNTIME_DIR=/tmp \
    JAVA_HOME=/opt/java \
    MAVEN_HOME=/opt/maven \
    DOCKER_HOST=tcp://127.0.0.1:2375 \
    PATH=/home/pipe/.local/bin:/opt/java/bin:/opt/maven/bin:$PATH

# ---------------------------------------------------------------------------
# Camada 8 — Código da esteira via COPY do contexto (supersede ADR-07)
# Camada mais volátil — última para preservar o cache das anteriores.
# O `src/` é provisionado no contexto de build pelo Makefile (fetch-app da
# branch de produção). Usar COPY (em vez de `git clone`) faz o cache-key desta
# camada ser o CHECKSUM dos arquivos: qualquer mudança no código invalida a
# camada automaticamente, então `docker compose build` sempre baka o código
# atual. O `git clone` anterior era cacheado pela string do comando e NÃO
# re-clonava novos commits da mesma branch — deixando código velho na imagem.
# ---------------------------------------------------------------------------
COPY --chown=pipe:pipe src /app/src

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
CMD ["python", "-m", "src"]
