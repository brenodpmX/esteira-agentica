"""Política de intenção de participação multi-board.

Resolve, a partir das labels de uma issue e dos boards configurados no
`pipe.yml`, o conjunto de boards para os quais existe autorização explícita
de participação multi-board (RN-B04, ADR-001).

A label reservada segue o padrão `board-intent-<board_id>`, no mesmo espírito
de `agent-level-<valor>` em `src/core/commands.py` (prefixo fixo + sufixo),
mas aqui o sufixo só é válido quando corresponde exatamente a uma chave de
`config["boards"]` (excluindo a chave `platform`, que não é um board).

Esta função é isolada da política de classificação (próxima task) porque tem
regra própria de validação: board inexistente gera warning e é ignorado, sem
levantar exceção nem conceder autorização.
"""

from src.core.log import log

# Prefixo das labels de intenção de participação em board (ex.: board-intent-epic).
BOARD_INTENT_LABEL_PREFIX = "board-intent-"


def authorized_boards(labels: list[str], config: dict) -> set[str]:
    """Resolve o conjunto de board_ids autorizados por label board-intent-<board_id>.

    Considera apenas labels com o prefixo BOARD_INTENT_LABEL_PREFIX. O
    sufixo deve corresponder exatamente a uma chave de config["boards"]
    (excluindo "platform"). Uma label com sufixo que não corresponde a
    nenhum board configurado é ignorada para fins de autorização e gera um
    log.warning (não levanta exceção, não interrompe as demais labels).

    Labels sem o prefixo são ignoradas silenciosamente (não são o alvo
    desta função). Não faz I/O de rede - "config" já é o dict do pipe.yml
    carregado.
    """
    valid_boards = set(config.get("boards", {}).keys()) - {"platform"}

    authorized: set[str] = set()
    for label in labels:
        if not label.startswith(BOARD_INTENT_LABEL_PREFIX):
            continue
        suffix = label[len(BOARD_INTENT_LABEL_PREFIX):]
        if suffix in valid_boards:
            authorized.add(suffix)
        else:
            log.warning(
                "Participation",
                f"label {label!r} ignorada - board {suffix!r} não configurado em pipe.yml",
            )

    return authorized
