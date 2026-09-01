"""Casos de teste para: resolver autorização multi-board via label
board-intent-<board_id>.

Issue #264 — Resolver autorização multi-board via label `board-intent-<board_id>`.
Issue pai (US-01): #242 — Classificação de intenção de participação em board.

Cobre exclusivamente a função pura `authorized_boards(labels, config)`, que
resolve o conjunto de `board_id`s autorizados a partir de labels
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

Status: RED (função ainda não existe; testes devem falhar por ImportError
até a implementação ser feita).
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.participation_policy import (
    authorized_boards,
    BOARD_INTENT_LABEL_PREFIX,
)


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
