"""Política de intenção de participação multi-board.

Resolve, a partir das labels de uma issue e dos boards configurados no
pipe.yml, o conjunto de boards para os quais existe autorização explícita
de participação multi-board (RN-B04, ADR-001).

A label reservada segue o padrão `board-intent-<board_id>`, no mesmo
espírito de `agent-level-<valor>` já implementado em `src/core/commands.py`.

O sufixo **não** é livre: só é válido quando corresponde exatamente a uma
chave de `config["boards"]` (excluindo a chave `platform`, que não é um board).
"""

from src.core.log import log

# Prefixo das labels de intenção de participação multi-board.
# Ex.: board-intent-epic, board-intent-story, etc.
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

    Args:
        labels: Lista de labels da issue (strings).
        config: Dict de configuração do pipe.yml (contém chave "boards").

    Returns:
        set[str]: Conjunto de board_ids autorizados pela política.
    """
    authorized = set()
    configured_boards = set(config.get("boards", {}).keys()) - {"platform"}

    for label in labels:
        if label.startswith(BOARD_INTENT_LABEL_PREFIX):
            # Extrai o sufixo (board_id candidato)
            board_id = label[len(BOARD_INTENT_LABEL_PREFIX):]

            # Valida se o sufixo corresponde a um board configurado
            if board_id in configured_boards:
                authorized.add(board_id)
            else:
                # Board não configurado: log.warning e ignora
                log.warning(
                    "Participation",
                    f"label {label!r} ignorada - board {board_id!r} não configurado em pipe.yml"
                )

    return authorized
