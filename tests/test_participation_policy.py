"""Testes da política de intenção de participação multi-board.

Cobertura dos casos CT01–CT09 especificados na issue #264:
- CT01: label válida
- CT02: sufixo inválido com warning
- CT03: `platform` sempre inválido
- CT04: ausência de prefixo
- CT05: múltiplas autorizações simultâneas
- CT06: lista vazia
- CT07: determinismo por ordem
- CT08/CT09: pureza (sem mutação de labels/config)
"""

import pytest
from unittest.mock import patch, MagicMock

from src.core.participation_policy import authorized_boards, BOARD_INTENT_LABEL_PREFIX


class TestAuthorizedBoards:
    """Testes da função authorized_boards."""

    # CT01: label válida retorna o board_id correspondente
    def test_valid_label_single_board(self):
        """Label válida retorna o board_id configurado."""
        labels = ["board-intent-epic"]
        config = {"boards": {"epic": {}, "story": {}}}

        result = authorized_boards(labels, config)

        assert result == {"epic"}

    # CT02: sufixo inválido com warning
    @patch("src.core.participation_policy.log")
    def test_invalid_board_id_logs_warning(self, mock_log):
        """Sufixo que não existe em boards configurados gera warning e retorna set vazio."""
        labels = ["board-intent-inexistente"]
        config = {"boards": {"epic": {}}}

        result = authorized_boards(labels, config)

        assert result == set()
        # Verifica que log.warning foi chamado com mensagem apropriada
        mock_log.warning.assert_called_once()
        call_args = mock_log.warning.call_args
        assert "board-intent-inexistente" in str(call_args)
        assert "inexistente" in str(call_args)

    # CT03: `platform` sempre inválido (nunca é um board)
    @patch("src.core.participation_policy.log")
    def test_platform_key_never_valid(self, mock_log):
        """A chave 'platform' nunca é um board válido, mesmo presente em config."""
        labels = ["board-intent-platform"]
        config = {"boards": {"platform": {...}, "epic": {}}}

        result = authorized_boards(labels, config)

        assert result == set()
        # Verifica que warning foi chamado
        mock_log.warning.assert_called_once()
        call_args = mock_log.warning.call_args
        assert "board-intent-platform" in str(call_args)

    # CT04: labels sem o prefixo são ignoradas silenciosamente
    def test_labels_without_prefix_ignored_silently(self):
        """Labels sem prefixo board-intent- são ignoradas sem warning."""
        labels = ["backend", "agent-hub-high", "security"]
        config = {"boards": {"epic": {}}}

        result = authorized_boards(labels, config)

        assert result == set()

    # CT05: múltiplas autorizações simultâneas
    def test_multiple_valid_labels(self):
        """Múltiplas labels válidas retornam o conjunto de boards autorizados."""
        labels = ["board-intent-epic", "board-intent-story"]
        config = {"boards": {"epic": {}, "story": {}}}

        result = authorized_boards(labels, config)

        assert result == {"epic", "story"}

    # CT06: lista vazia retorna set vazio
    def test_empty_labels_returns_empty_set(self):
        """Labels vazia retorna set vazio."""
        labels = []
        config = {"boards": {"epic": {}}}

        result = authorized_boards(labels, config)

        assert result == set()

    # CT07: determinismo por ordem
    def test_determinism_order_independent(self):
        """Mesmo conjunto de labels em ordens diferentes produz o mesmo resultado."""
        config = {"boards": {"epic": {}, "story": {}, "task": {}}}

        # Ordem 1: epic, story, task
        labels1 = ["board-intent-epic", "board-intent-story", "board-intent-task"]
        result1 = authorized_boards(labels1, config)

        # Ordem 2: task, epic, story
        labels2 = ["board-intent-task", "board-intent-epic", "board-intent-story"]
        result2 = authorized_boards(labels2, config)

        # Ordem 3: story, task, epic
        labels3 = ["board-intent-story", "board-intent-task", "board-intent-epic"]
        result3 = authorized_boards(labels3, config)

        # Todos retornam o mesmo conjunto (set é não-ordenado)
        assert result1 == result2 == result3 == {"epic", "story", "task"}

    # CT08: pureza - labels não é mutado
    def test_purity_labels_not_mutated(self):
        """A função não mutaa lista de labels."""
        labels = ["board-intent-epic", "backend"]
        labels_original = list(labels)
        config = {"boards": {"epic": {}}}

        authorized_boards(labels, config)

        assert labels == labels_original

    # CT09: pureza - config não é mutado
    def test_purity_config_not_mutated(self):
        """A função não mutaa dict de config."""
        labels = ["board-intent-epic"]
        config = {"boards": {"epic": {}, "story": {}}}
        config_original = {
            "boards": {k: dict(v) for k, v in config["boards"].items()}
        }

        authorized_boards(labels, config)

        assert config == config_original

    # Caso extra: mistura de labels válidas e inválidas
    @patch("src.core.participation_policy.log")
    def test_mixed_valid_invalid_labels(self, mock_log):
        """Mistura de labels válidas, inválidas e sem prefixo."""
        labels = [
            "board-intent-epic",
            "board-intent-inexistente",
            "backend",
            "board-intent-story",
        ]
        config = {"boards": {"epic": {}, "story": {}}}

        result = authorized_boards(labels, config)

        # Apenas labels válidas (epic, story) são retornadas
        assert result == {"epic", "story"}
        # board-intent-inexistente gera warning
        mock_log.warning.assert_called_once()
        call_args = mock_log.warning.call_args
        assert "board-intent-inexistente" in str(call_args)

    # Caso extra: config vazia (sem boards)
    def test_empty_boards_config(self):
        """Config sem chave 'boards' ou com boards vazio."""
        labels = ["board-intent-epic"]
        config = {"boards": {}}

        result = authorized_boards(labels, config)

        assert result == set()

    # Caso extra: config sem chave 'boards'
    def test_config_missing_boards_key(self):
        """Config sem chave 'boards' não falha."""
        labels = ["board-intent-epic"]
        config = {}

        result = authorized_boards(labels, config)

        assert result == set()

    # Caso extra: prefixo case-sensitive
    def test_prefix_case_sensitive(self):
        """Prefixo é case-sensitive (Board-Intent-epic não funciona)."""
        labels = ["Board-Intent-epic", "BOARD-INTENT-STORY"]
        config = {"boards": {"epic": {}, "story": {}}}

        result = authorized_boards(labels, config)

        # Nenhuma label com prefixo alterado é reconhecida
        assert result == set()
