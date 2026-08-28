# Resolução do débito #273 — dependência entre as tasks #255 e #256

## Contexto

A task #256, que implementa o bloqueio de novos vínculos pai/filho entre boards distintos quando `safety.cross_board_parent_links` está em `suspended`, depende do contrato de configuração entregue pela task #255. Durante a primeira passagem de Casos de Teste de #256, esse contrato ainda não estava disponível em `epic`, motivo pelo qual o trabalho foi corretamente interrompido e o débito #273 foi aberto.

## Decisão de Produto

A sequência obrigatória permanece **#255 antes de #256**. Não será criado placeholder, contrato alternativo nem implementação duplicada em #256.

A dependência está atendida: o PR #283 foi mergeado em `epic` em 28/08/2026, no commit `ad1da07`, entregando em `src/core/config.py`:

- `CROSS_BOARD_LINKS_VALUES`;
- `validate_cross_board_parent_links`;
- `resolve_cross_board_parent_links`;
- `load_current_config`;
- integração da validação em `check_config()`.

Os testes e suas evidências estão registrados em:

- `doc/quality/integridade-de-issues-entre-boards/test-cases-adicionar-e-validar-chave-safety-cross-board-parent-links.md`;
- `doc/quality/integridade-de-issues-entre-boards/test-results-adicionar-e-validar-chave-safety-cross-board-parent-links.md`.

## Encaminhamento para #256

#256 pode retomar a etapa de Casos de Teste e, depois, seguir para implementação. A branch de trabalho de #256 deve partir de uma revisão de `epic` que contenha o commit `ad1da07` ou incorporar esse commit antes de qualquer alteração.

Os casos de teste de #256 devem consumir o contrato real entregue por #255 e cobrir exclusivamente o gate e o evento definidos em seu próprio escopo. Não devem recriar as funções de configuração nem alterar o contrato aprovado em #255.

## Critério de resolução

O débito #273 é considerado resolvido quando esta decisão estiver integrada e #256 puder ser retomada sobre uma base que contenha #255. Não há definição humana ou decisão arquitetural pendente.
