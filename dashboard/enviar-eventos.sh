#!/usr/bin/env bash
# Envia eventos de teste para o dashboard (pipe "teste-manual").
# Exemplos:
#   ./enviar-eventos.sh cenario                 # árvore completa com execuções espaçadas
#   ./enviar-eventos.sh issue --board epicos
#   ./enviar-eventos.sh execucao --issue 1 --agente revisor --resultado "falha terminal" --consumo 12
#   ./enviar-eventos.sh --help
set -euo pipefail
cd "$(dirname "$0")"
exec docker compose --profile exemplo run --rm --no-deps -T \
  -e TESTE_PIPE_ID="${TESTE_PIPE_ID:-teste-manual}" -e TESTE_PIPE_NOME="${TESTE_PIPE_NOME:-teste-manual}" \
  gerador enviar_eventos.py "$@"
