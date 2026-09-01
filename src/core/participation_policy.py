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

from enum import Enum

from src.core.log import log

# Prefixo das labels de intenção de participação em board (ex.: board-intent-epic).
BOARD_INTENT_LABEL_PREFIX = "board-intent-"


class ParticipationClassification(str, Enum):
    """Estados de classificação de uma participação de issue em um board.

    Definidos em ADR-001. Segue o padrão str, Enum de SyncEvent
    (src/core/board.py) para evitar strings soltas espalhadas pelo código.
    """
    ORIGIN = "origin"            # criação original / primeira participação comprovada
    AUTHORIZED = "authorized"    # autorização explícita via label board-intent-<board_id>
    PROPAGATED = "propagated"    # propagada de outro board configurado
    UNRESOLVED = "unresolved"    # ambíguo/sem prova suficiente (fail-closed)


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


def classify_participation(
    board_id: str,
    labels: list[str],
    known_participations: list,
    config: dict,
) -> ParticipationClassification:
    """Classifica a participação da issue no board `board_id`.

    Função pura: não faz I/O de rede, não lê/escreve snapshot, não decide
    remoção nem persistência. Apenas recebe dados já carregados pelo chamador
    e devolve a classificação (ADR-001, RN-B01, RN-B02, RN-B04, RN-B10).

    - `board_id`: board avaliado.
    - `labels`: labels da issue (já carregadas pelo chamador).
    - `known_participations`: participações JÁ CONFIRMADAS da mesma issue em
      QUALQUER board. Pode incluir a própria participação em `board_id`, que é
      ignorada ao decidir "outro board". Cada item precisa expor `board_id`
      (str | None) e `status` (str | None) via duck typing - não importamos o
      módulo Participation de outra branch/story para não criar dependência de
      merge entre stories paralelas.
    - `config`: dict do pipe.yml (usa apenas config["boards"]).

    Regras, em ordem estrita de prioridade:

    1. Autorização explícita tem prioridade: se `board_id` está em
       authorized_boards(labels, config), retorna AUTHORIZED,
       independentemente de outras participações.
    2. Se não há NENHUMA participação confirmada com board_id resolvido
       (!= None) e diferente do avaliado, retorna ORIGIN (RN-B01, exceção de
       criação original).
    3. Se há ao menos uma participação com board_id resolvido, diferente do
       avaliado e presente em config["boards"] (ignorando "platform"), retorna
       PROPAGATED - com ou sem status preenchido (RN-B02: Status não isenta a
       classificação).
    4. Qualquer outro caso retorna UNRESOLVED - nunca infere ORIGIN por
       omissão quando há dúvida (participações apenas em boards não mais
       configurados, ou dados ambíguos/contraditórios).

    Determinística: usa apenas pertencimento a conjuntos, nunca a ordem de
    known_participations ou de config["boards"].
    """
    # Regra 1 — autorização explícita prevalece sobre qualquer evidência.
    if board_id in authorized_boards(labels, config):
        return ParticipationClassification.AUTHORIZED

    valid_boards = set(config.get("boards", {}).keys()) - {"platform"}

    # Particiona as participações de OUTROS boards (!= avaliado) em dois grupos,
    # usando apenas pertencimento a conjuntos (determinístico):
    #   - propagated_boards: board_id resolvido e AINDA presente em config.
    #   - ambiguous: board_id não resolvido (None) OU resolvido mas fora da
    #     config atual — nenhum dos dois serve como prova (RN-B02).
    propagated_boards: set[str] = set()
    has_ambiguous = False
    for participation in known_participations:
        other_board = participation.board_id
        if other_board == board_id:
            # Participação no próprio board avaliado: não é "outro board".
            continue
        if other_board is None:
            has_ambiguous = True
        elif other_board in valid_boards:
            propagated_boards.add(other_board)
        else:
            # Resolvido, porém board não está mais em config["boards"].
            has_ambiguous = True

    # Regra 3 — participação comprovada em outro board configurado → PROPAGATED.
    # (checada antes de ORIGIN/UNRESOLVED por ter prioridade sobre ambos).
    if propagated_boards:
        return ParticipationClassification.PROPAGATED

    # Regra 4 — há dados ambíguos (board None ou fora da config) sem outra
    # evidência → UNRESOLVED. Nunca inferir ORIGIN por omissão quando há dúvida.
    if has_ambiguous:
        return ParticipationClassification.UNRESOLVED

    # Regra 2 — nenhuma participação em outro board (só o avaliado ou vazio) → ORIGIN.
    return ParticipationClassification.ORIGIN
