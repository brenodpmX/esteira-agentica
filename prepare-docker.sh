#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# prepare-docker.sh — Prepara o contexto de build Docker
#
# O Dockerfile precisa dos binários do kiro-cli no contexto de build.
# Este script os copia do host para a raiz do projeto antes do docker-compose.
#
# ATENÇÃO: `kiro-cli` é apenas um launcher. O subcomando `chat` — usado pela
# esteira — é executado via `exec` num binário irmão, `kiro-cli-chat`, instalado
# ao lado dele. Copiar somente o launcher faz o container falhar com
# "error: No such file or directory (os error 2)" (issue #120).
#
# `kiro-cli-term` (integração de shell interativo) não é usado pela esteira e
# não é copiado.
#
# Uso:
#   ./prepare-docker.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Binários necessários no contexto de build (launcher + implementação do chat)
KIRO_BINARIES=(kiro-cli kiro-cli-chat)

# Localizar o launcher no host
KIRO_HOST="$(command -v kiro-cli 2>/dev/null || echo "")"

if [[ -z "$KIRO_HOST" ]]; then
    echo "ERRO: kiro-cli não encontrado no PATH do host."
    echo "      Instale kiro-cli antes de executar este script."
    exit 1
fi

# Diretório real da instalação (resolve symlinks) — é onde vivem os binários irmãos
KIRO_DIR="$(dirname "$(readlink -f "$KIRO_HOST")")"

echo "kiro-cli encontrado em: $KIRO_HOST"
echo "Diretório de instalação: $KIRO_DIR"

# Validar a presença de todos os binários no host antes de copiar qualquer um
for name in "${KIRO_BINARIES[@]}"; do
    if [[ ! -f "${KIRO_DIR}/${name}" ]]; then
        echo "ERRO: ${name} não encontrado em ${KIRO_DIR}."
        if [[ "$name" == "kiro-cli-chat" ]]; then
            echo "      O binário kiro-cli é um launcher: o subcomando 'chat' é"
            echo "      executado por kiro-cli-chat, que deve estar instalado ao lado."
            echo "      Sem ele o container falha com 'No such file or directory (os error 2)'."
        fi
        echo "      Reinstale o kiro-cli no host para obter a instalação completa."
        exit 1
    fi
done

for name in "${KIRO_BINARIES[@]}"; do
    src="${KIRO_DIR}/${name}"
    dest="${SCRIPT_DIR}/${name}"

    if [[ -f "$dest" ]]; then
        echo "${name} já presente no contexto de build. Pulando cópia."
    else
        echo "Copiando ${name} ($(du -sh "$src" | cut -f1)) para o contexto de build..."
        cp "$src" "$dest"
        chmod +x "$dest"
        echo "Copiado: $dest ($(du -sh "$dest" | cut -f1))"
    fi
done

total="$(du -shc "${KIRO_BINARIES[@]/#/${SCRIPT_DIR}/}" | tail -1 | cut -f1)"
echo ""
echo "Binários no contexto de build: ${KIRO_BINARIES[*]} (total ${total})"
echo ""
echo "Contexto de build pronto. Execute:"
echo "  docker compose build"
echo "  docker compose up"
