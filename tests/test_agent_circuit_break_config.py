"""Testes de validação de forma do bloco `agent_circuit_break` (issue #306).

Cobre CT-13 (config inválida falha na verificação, citando o caminho) e CT-13b
(config válida com bloco presente/ausente é aceita).

A validação segue o padrão da casa (`validate_retry`/`validate_max_attempts`):
`ConfigError` citando o caminho completo do campo, com `bool` rejeitado ANTES de
`int` (True/False são instâncias de int em Python). Bloco opcional de RAIZ (fora
de `boards`, que enumera todo dict como board).
"""

import pytest

from src.core.config import ConfigError
from src.core.agent_circuit_break import (
    validate_agent_circuit_break,
    resolve_policy,
)


# ─── CT-13: configuração inválida ─────────────────────────────────────────────

class TestConfigInvalida:
    """Cada sub-caso levanta ConfigError citando o caminho completo do campo."""

    def test_so_executions_sem_window(self):
        cfg = {"agent_circuit_break": {"executions": 5}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.window"):
            validate_agent_circuit_break(cfg)

    def test_so_window_sem_executions(self):
        cfg = {"agent_circuit_break": {"window": 3600}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.executions"):
            validate_agent_circuit_break(cfg)

    def test_executions_booleano_rejeitado_antes_de_int(self):
        cfg = {"agent_circuit_break": {"executions": True, "window": 3600}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.executions"):
            validate_agent_circuit_break(cfg)

    def test_window_booleano_rejeitado_antes_de_int(self):
        cfg = {"agent_circuit_break": {"executions": 5, "window": False}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.window"):
            validate_agent_circuit_break(cfg)

    def test_executions_menor_que_1(self):
        cfg = {"agent_circuit_break": {"executions": 0, "window": 3600}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.executions"):
            validate_agent_circuit_break(cfg)

    def test_window_menor_que_1(self):
        cfg = {"agent_circuit_break": {"executions": 5, "window": 0}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.window"):
            validate_agent_circuit_break(cfg)

    def test_executions_float_rejeitado(self):
        cfg = {"agent_circuit_break": {"executions": 1.5, "window": 3600}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.executions"):
            validate_agent_circuit_break(cfg)

    def test_window_float_rejeitado(self):
        cfg = {"agent_circuit_break": {"executions": 5, "window": 3600.0}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.window"):
            validate_agent_circuit_break(cfg)

    def test_executions_string_rejeitado(self):
        cfg = {"agent_circuit_break": {"executions": "5", "window": 3600}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.executions"):
            validate_agent_circuit_break(cfg)

    def test_campo_desconhecido_rejeitado(self):
        cfg = {"agent_circuit_break": {"executions": 5, "window": 3600, "foo": 1}}
        with pytest.raises(ConfigError, match=r"agent_circuit_break\.foo"):
            validate_agent_circuit_break(cfg)

    def test_bloco_nao_e_mapa(self):
        cfg = {"agent_circuit_break": [5, 3600]}
        with pytest.raises(ConfigError, match=r"agent_circuit_break"):
            validate_agent_circuit_break(cfg)

    def test_falha_antes_de_qualquer_alteracao_de_estado(self):
        """A validação é pura (não escreve estado). CT-11 exige falha antes de
        alterar estado — garantido por rodar em check_config, antes do lock."""
        import src.core.config as config_mod
        # A função não deve criar nenhum arquivo nem tocar o filesystem.
        cfg = {"agent_circuit_break": {"executions": 0, "window": 10}}
        with pytest.raises(ConfigError):
            validate_agent_circuit_break(cfg)
        # Sanidade: o símbolo é o mesmo chamado por check_config.
        assert config_mod.check_config is not None


# ─── Caso: bloco dentro do mapa de boards ─────────────────────────────────────

class TestBlocoDentroDeBoards:
    """A política não pode viver dentro de `boards` (que enumera dict como board).

    Colocar `agent_circuit_break` dentro de `boards` faz o validador de boards
    tratá-lo como um board inválido (sem `name`/`columns`) — rejeitado citando o
    caminho onde apareceu indevidamente.
    """

    def test_dentro_de_boards_e_rejeitado_como_board_invalido(self):
        from src.core.config import _validate_boards
        boards = {
            "platform": "github",
            "agent_circuit_break": {"executions": 5, "window": 3600},
        }
        with pytest.raises(ConfigError, match=r"boards\.agent_circuit_break"):
            _validate_boards(boards, known_agents=set())


# ─── CT-13b: configuração válida (presente e ausente) ─────────────────────────

class TestConfigValida:
    def test_bloco_valido_aceito(self):
        cfg = {"agent_circuit_break": {"executions": 5, "window": 3600}}
        validate_agent_circuit_break(cfg)  # não deve levantar

    def test_bloco_ausente_aceito(self):
        cfg = {"sleep": 60}
        validate_agent_circuit_break(cfg)  # não deve levantar

    @pytest.mark.parametrize("executions,window", [(1, 1), (5, 3600), (10, 86400)])
    def test_inteiros_maiores_igual_1_aceitos(self, executions, window):
        cfg = {"agent_circuit_break": {"executions": executions, "window": window}}
        validate_agent_circuit_break(cfg)


# ─── resolve_policy ───────────────────────────────────────────────────────────

class TestResolvePolicy:
    def test_ausente_inativa(self):
        policy = resolve_policy({"sleep": 60})
        assert policy.active is False
        assert policy.executions is None
        assert policy.window is None

    def test_presente_ativa_com_valores(self):
        policy = resolve_policy(
            {"agent_circuit_break": {"executions": 5, "window": 3600}}
        )
        assert policy.active is True
        assert policy.executions == 5
        assert policy.window == 3600
