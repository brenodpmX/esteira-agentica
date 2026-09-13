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
# Repositório APT oficial do GitHub com chave GPG assinada
# Versão pinada conforme docker/versions.env (ADR-04)
# ---------------------------------------------------------------------------
RUN curl --proto '=https' --tlsv1.2 -fsSL \
        https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh=2.97.0 \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Camada 4 — PyYAML
# Versão pinada conforme docker/versions.env (ADR-04)
# ---------------------------------------------------------------------------
RUN pip install --no-cache-dir pyyaml==6.0.2

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
    PATH=/home/pipe/.local/bin:$PATH

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
