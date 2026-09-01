"""Casos de teste para a política de intenção de participação multi-board.

Issue #264 — Resolver autorização multi-board via label `board-intent-<board_id>`.
Issue #265 — Implementar política pura `classify_participation`
(origin/authorized/propagated/unresolved).
Issue pai (US-01): #242 — Classificação de intenção de participação em board.

## Parte 1 (#264): `authorized_boards(labels, config)`

Resolve o conjunto de `board_id`s autorizados a partir de labels
`board-intent-<board_id>` e da configuração de boards do `pipe.yml`
(RN-B04, ADR-001):

1. Label `board-intent-<board_id>` cujo sufixo corresponde a uma chave de
   `config["boards"]` (exceto `platform`) autoriza o board.
2. Sufixo que não corresponde a nenhum board configurado é ignorado para
   fins de autorização e emite `log.warning` (não levanta exceção).
3. A chave `platform` nunca é um board válido, mesmo presente no dict de
   configuração — sufixo `platform` sempre ignorado com warning.
4. Labels sem o prefixo `board-intent-` são ignoradas silenciosamente (sem
   warning).
5. Múltiplas labels `board-intent-*` autorizam múltiplos boards
   simultaneamente.
6. Lista de labels vazia retorna conjunto vazio.
7. Determinismo: o resultado não depende da ordem das labels de entrada.

## Parte 2 (#265): `classify_participation(board_id, labels, known_participations, config)`

Classifica a participação de uma issue em um board avaliado em um dos
quatro estados de `ParticipationClassification` (ORIGIN, AUTHORIZED,
PROPAGATED, UNRESOLVED), com prioridade estrita entre as regras (ADR-001,
RN-B01, RN-B02, RN-B04, RN-B10):

1. Autorização explícita (via `authorized_boards`) tem prioridade sobre
   qualquer outra evidência → AUTHORIZED.
2. Nenhuma participação confirmada com `board_id` resolvido e diferente do
   avaliado → ORIGIN.
3. Ao menos uma participação com `board_id` resolvido, diferente do
   avaliado, presente em `config["boards"]` (exceto `platform`) →
   PROPAGATED, com ou sem `status` preenchido (RN-B02: Status não isenta a
   classificação).
4. Qualquer outro caso (ex.: participação apenas em board fora de
   `config["boards"]`, ou `board_id=None` sem outra evidência) →
   UNRESOLVED — nunca ORIGIN por omissão quando há dúvida.
5. Determinismo independente da ordem de `known_participations` e das
   chaves de `config["boards"]`.
6. Regressão Story→Epic e Task→User Story (RN-B10): a lógica não depende do
   nome/nível hierárquico do board.

`Participation` é simulada via `SimpleNamespace(board_id=..., status=...)`
(duck typing), sem importar o módulo de outra branch/story ainda não
mesclada, conforme instruído no docstring de `classify_participation`.

Status: RED para a Parte 2 (`classify_participation`/
`ParticipationClassification` ainda não existem; os testes correspondentes
devem falhar até a implementação ser feita). A Parte 1 (`authorized_boards`)
já está implementada (#264) e seus testes devem continuar passando.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.participation_policy import (
    authorized_boards,
    BOARD_INTENT_LABEL_PREFIX,
)

try:
    from src.core.participation_policy import (
        classify_participation,
        ParticipationClassification,
    )
except ImportError:
    classify_participation = None
    ParticipationClassification = None


# ══════════════════════════════════════════════════════════════════════════════
# CT01 — Label com sufixo correspondente a board configurado autoriza (AC1)
# ══════════════════════════════════════════════════════════════════════════════

def test_single_label_matching_board_authorizes_it():
    labels = ["board-intent-epic"]
    config = {"boards": {"epic": {}, "story": {}}}

    result = authorized_boards(labels, config)

    assert result == {"epic"}


def test_prefix_constant_matches_expected_value():
    assert BOARD_INTENT_LABEL_PREFIX == "board-intent-"


# ══════════════════════════════════════════════════════════════════════════════
# CT02 — Sufixo sem board configurado é ignorado e gera warning (AC2)
# ══════════════════════════════════════════════════════════════════════════════

def test_label_with_unconfigured_board_suffix_is_ignored():
    labels = ["board-intent-inexistente"]
    config = {"boards": {"epic": {}}}

    with patch("src.core.participation_policy.log.warning") as mock_warning:
        result = authorized_boards(labels, config)

    assert result == set()
    assert mock_warning.called


def test_label_with_unconfigured_board_suffix_warning_mentions_label_and_board():
    labels = ["board-intent-inexistente"]
    config = {"boards": {"epic": {}}}

    with patch("src.core.participation_policy.log.warning") as mock_warning:
        authorized_boards(labels, config)

    call_text = str(mock_warning.call_args)
    assert "board-intent-inexistente" in call_text
    assert "inexistente" in call_text


# ══════════════════════════════════════════════════════════════════════════════
# CT03 — Sufixo "platform" nunca é um board válido (AC3)
# ══════════════════════════════════════════════════════════════════════════════

def test_platform_suffix_never_authorizes_even_if_key_present():
    labels = ["board-intent-platform"]
    config = {"boards": {"platform": {"name": "github"}, "epic": {}}}

    with patch("src.core.participation_policy.log.warning") as mock_warning:
        result = authorized_boards(labels, config)

    assert result == set()
    assert mock_warning.called


# ══════════════════════════════════════════════════════════════════════════════
# CT04 — Labels sem o prefixo são ignoradas silenciosamente (AC4)
# ══════════════════════════════════════════════════════════════════════════════

def test_labels_without_prefix_are_ignored_without_warning():
    labels = ["backend", "agent-hub-high"]
    config = {"boards": {"epic": {}}}

    with patch("src.core.participation_policy.log.warning") as mock_warning:
        result = authorized_boards(labels, config)

    assert result == set()
    mock_warning.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# CT05 — Múltiplas autorizações simultâneas (AC5)
# ══════════════════════════════════════════════════════════════════════════════

def test_multiple_matching_labels_authorize_multiple_boards():
    labels = ["board-intent-epic", "board-intent-story"]
    config = {"boards": {"epic": {}, "story": {}}}

    result = authorized_boards(labels, config)

    assert result == {"epic", "story"}


def test_mix_of_valid_invalid_and_unrelated_labels():
    labels = [
        "backend",
        "board-intent-epic",
        "board-intent-inexistente",
        "agent-hub-high",
        "board-intent-story",
    ]
    config = {"boards": {"epic": {}, "story": {}}}

    with patch("src.core.participation_policy.log.warning") as mock_warning:
        result = authorized_boards(labels, config)

    assert result == {"epic", "story"}
    assert mock_warning.call_count == 1


# ══════════════════════════════════════════════════════════════════════════════
# CT06 — Lista de labels vazia (AC6)
# ══════════════════════════════════════════════════════════════════════════════

def test_empty_labels_returns_empty_set():
    result = authorized_boards([], {"boards": {"epic": {}}})

    assert result == set()


# ══════════════════════════════════════════════════════════════════════════════
# CT07 — Determinismo independente da ordem das labels (AC7)
# ══════════════════════════════════════════════════════════════════════════════

def test_result_is_order_independent():
    config = {"boards": {"epic": {}, "story": {}, "task": {}}}

    labels_a = ["board-intent-epic", "board-intent-story", "board-intent-task"]
    labels_b = ["board-intent-task", "board-intent-epic", "board-intent-story"]

    result_a = authorized_boards(labels_a, config)
    result_b = authorized_boards(labels_b, config)

    assert result_a == result_b == {"epic", "story", "task"}


def test_result_is_order_independent_with_mixed_valid_and_invalid():
    config = {"boards": {"epic": {}, "story": {}}}

    labels_a = [
        "board-intent-inexistente",
        "board-intent-epic",
        "backend",
        "board-intent-story",
    ]
    labels_b = [
        "board-intent-story",
        "backend",
        "board-intent-epic",
        "board-intent-inexistente",
    ]

    with patch("src.core.participation_policy.log.warning"):
        result_a = authorized_boards(labels_a, config)
        result_b = authorized_boards(labels_b, config)

    assert result_a == result_b == {"epic", "story"}


# ══════════════════════════════════════════════════════════════════════════════
# CT08 — Não faz I/O; consome apenas o dict de config já carregado
# ══════════════════════════════════════════════════════════════════════════════

def test_does_not_mutate_input_labels_or_config():
    labels = ["board-intent-epic", "backend"]
    config = {"boards": {"epic": {}, "story": {}}}
    labels_copy = list(labels)
    config_copy = {"boards": dict(config["boards"])}

    authorized_boards(labels, config)

    assert labels == labels_copy
    assert config == config_copy


# ══════════════════════════════════════════════════════════════════════════════
# PARTE 2 (#265) — classify_participation(board_id, labels, known_participations, config)
# ══════════════════════════════════════════════════════════════════════════════

def _participation(board_id, status=None):
    """Simula Participation via duck typing (SimpleNamespace), sem importar
    o módulo de outra branch/story ainda não mesclada nesta."""
    return SimpleNamespace(board_id=board_id, status=status)


# ══════════════════════════════════════════════════════════════════════════════
# CT01 — Única participação confirmada no próprio board → ORIGIN
# ══════════════════════════════════════════════════════════════════════════════

def test_single_confirmed_participation_in_evaluated_board_returns_origin():
    board_id = "epic"
    labels = []
    known_participations = [_participation("epic")]
    config = {"boards": {"epic": {}, "story": {}}}

    result = classify_participation(board_id, labels, known_participations, config)

    assert result == ParticipationClassification.ORIGIN


# ══════════════════════════════════════════════════════════════════════════════
# CT02 — Label de autorização sem outra participação → AUTHORIZED
# ══════════════════════════════════════════════════════════════════════════════

def test_authorization_label_without_other_participation_returns_authorized():
    board_id = "story"
    labels = ["board-intent-story"]
    known_participations = []
    config = {"boards": {"epic": {}, "story": {}}}

    result = classify_participation(board_id, labels, known_participations, config)

    assert result == ParticipationClassification.AUTHORIZED


# ══════════════════════════════════════════════════════════════════════════════
# CT03 — Autorização prevalece sobre evidência de propagação (ADR-001)
# ══════════════════════════════════════════════════════════════════════════════

def test_authorization_takes_priority_over_propagation_evidence():
    board_id = "story"
    labels = ["board-intent-story"]
    known_participations = [_participation("epic", status="Doing")]
    config = {"boards": {"epic": {}, "story": {}}}

    result = classify_participation(board_id, labels, known_participations, config)

    assert result == ParticipationClassification.AUTHORIZED


# ══════════════════════════════════════════════════════════════════════════════
# CT04 — Participação em outro board configurado, sem autorização, com status → PROPAGATED
# ══════════════════════════════════════════════════════════════════════════════

def test_confirmed_participation_in_other_configured_board_with_status_returns_propagated():
    board_id = "story"
    labels = []
    known_participations = [_participation("epic", status="Doing")]
    config = {"boards": {"epic": {}, "story": {}}}

    result = classify_participation(board_id, labels, known_participations, config)

    assert result == ParticipationClassification.PROPAGATED


# ══════════════════════════════════════════════════════════════════════════════
# CT05 — Mesmo cenário do CT04 sem status → PROPAGATED (RN-B02: Status não influencia)
# ══════════════════════════════════════════════════════════════════════════════

def test_confirmed_participation_in_other_configured_board_without_status_returns_propagated():
    board_id = "story"
    labels = []
    known_participations = [_participation("epic", status=None)]
    config = {"boards": {"epic": {}, "story": {}}}

    result = classify_participation(board_id, labels, known_participations, config)

    assert result == ParticipationClassification.PROPAGATED


# ══════════════════════════════════════════════════════════════════════════════
# CT06 — Participação apenas com board_id=None → UNRESOLVED (não ORIGIN)
# ══════════════════════════════════════════════════════════════════════════════

def test_participation_with_unresolved_board_id_returns_unresolved():
    board_id = "story"
    labels = []
    known_participations = [_participation(None)]
    config = {"boards": {"epic": {}, "story": {}}}

    result = classify_participation(board_id, labels, known_participations, config)

    assert result == ParticipationClassification.UNRESOLVED


# ══════════════════════════════════════════════════════════════════════════════
# CT07 — Participação em board removido de config["boards"] → UNRESOLVED (RN-B02)
# ══════════════════════════════════════════════════════════════════════════════

def test_participation_in_board_removed_from_config_returns_unresolved():
    board_id = "story"
    labels = []
    known_participations = [_participation("board-removido", status="Done")]
    config = {"boards": {"story": {}}}

    result = classify_participation(board_id, labels, known_participations, config)

    assert result == ParticipationClassification.UNRESOLVED


# ══════════════════════════════════════════════════════════════════════════════
# CT08 — Determinismo por ordem de known_participations e de config["boards"]
# ══════════════════════════════════════════════════════════════════════════════

def test_result_is_deterministic_regardless_of_input_order():
    board_id = "story"
    labels = []
    known_participations_a = [
        _participation("epic", status="Doing"),
        _participation(None),
    ]
    known_participations_b = list(reversed(known_participations_a))
    config_a = {"boards": {"epic": {}, "story": {}, "task": {}}}
    config_b = {"boards": dict(reversed(list(config_a["boards"].items())))}

    result_a = classify_participation(board_id, labels, known_participations_a, config_a)
    result_b = classify_participation(board_id, labels, known_participations_b, config_b)

    assert result_a == result_b == ParticipationClassification.PROPAGATED


# ══════════════════════════════════════════════════════════════════════════════
# CT09 — Regressão Story→Epic e Task→User Story (RN-B10)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    "evaluated_board, other_board",
    [
        ("epic", "story"),
        ("story", "task"),
    ],
)
def test_classification_is_independent_of_board_name_or_hierarchy_level(
    evaluated_board, other_board
):
    config = {"boards": {evaluated_board: {}, other_board: {}}}

    # ORIGIN: única participação confirmada no próprio board avaliado.
    assert classify_participation(
        evaluated_board, [], [_participation(evaluated_board)], config
    ) == ParticipationClassification.ORIGIN

    # PROPAGATED: participação confirmada em outro board configurado, sem autorização.
    assert classify_participation(
        evaluated_board, [], [_participation(other_board, status="Doing")], config
    ) == ParticipationClassification.PROPAGATED

    # UNRESOLVED: board_id não resolvido, sem outra evidência.
    assert classify_participation(
        evaluated_board, [], [_participation(None)], config
    ) == ParticipationClassification.UNRESOLVED

    # UNRESOLVED: participação em board fora de config["boards"].
    assert classify_participation(
        evaluated_board,
        [],
        [_participation("board-fora-da-config", status="Done")],
        {"boards": {evaluated_board: {}}},
    ) == ParticipationClassification.UNRESOLVED


# ══════════════════════════════════════════════════════════════════════════════
# CT10 — ParticipationClassification segue o padrão str, Enum com os 4 valores
# ══════════════════════════════════════════════════════════════════════════════

def test_participation_classification_enum_matches_expected_values():
    from enum import Enum

    assert issubclass(ParticipationClassification, str)
    assert issubclass(ParticipationClassification, Enum)
    assert ParticipationClassification.ORIGIN == "origin"
    assert ParticipationClassification.AUTHORIZED == "authorized"
    assert ParticipationClassification.PROPAGATED == "propagated"
    assert ParticipationClassification.UNRESOLVED == "unresolved"
    assert {member.value for member in ParticipationClassification} == {
        "origin",
        "authorized",
        "propagated",
        "unresolved",
    }
