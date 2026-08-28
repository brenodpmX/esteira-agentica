"""Testes de safety.cross_board_parent_links em src/core/config.py (task #255).

Cobrem 1:1 os casos de teste do documento de qualidade
`doc/quality/integridade-de-issues-entre-boards/test-cases-adicionar-e-validar-chave-safety-cross-board-parent-links.md`
(CT01–CT13); CT14 é a execução da suíte completa.

Escopo: apenas a validação (`validate_cross_board_parent_links`), a leitura
(`resolve_cross_board_parent_links`, `load_current_config`) e a integração via
`check_config()`. O gate real de set_parent/set_children (#256) fica fora.
"""

import sys
from pathlib import Path

import pytest
import yaml

# Permite importar o pacote src quando rodado de qualquer lugar.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import (
    ConfigError,
    check_config,
    load_current_config,
    resolve_cross_board_parent_links,
    validate_cross_board_parent_links,
)


def _base_config(**overrides) -> dict:
    """Config mínima válida (mesmo padrão de test_error_classification)."""
    cfg = {
        "sleep": 60,
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": {
                "base": "main",
                "feature": {"prefix": "feature/", "create": "main", "merge": "main"},
            },
        },
        "agents": {},
        "boards": {"platform": "github"},
    }
    cfg.update(overrides)
    return cfg


# ══════════════════════════════════════════════════════════════════════════
# validate_cross_board_parent_links — CT01..CT07
# ══════════════════════════════════════════════════════════════════════════

class TestValidateValid:
    """CT01–CT04 — ausência da chave/seção e valores válidos não levantam."""

    def test_ct01_no_safety_section(self):
        validate_cross_board_parent_links({})

    def test_ct02_safety_present_key_absent(self):
        validate_cross_board_parent_links({"safety": {}})

    def test_ct03_accepts_enabled(self):
        validate_cross_board_parent_links(
            {"safety": {"cross_board_parent_links": "enabled"}}
        )

    def test_ct04_accepts_suspended(self):
        validate_cross_board_parent_links(
            {"safety": {"cross_board_parent_links": "suspended"}}
        )


class TestValidateInvalid:
    """CT05–CT07 — valores inválidos levantam ConfigError acionável."""

    def test_ct05_rejects_case_variation(self):
        with pytest.raises(ConfigError) as excinfo:
            validate_cross_board_parent_links(
                {"safety": {"cross_board_parent_links": "Enabled"}}
            )
        assert "safety.cross_board_parent_links" in str(excinfo.value)

    def test_ct06_rejects_invalid_string(self):
        with pytest.raises(ConfigError) as excinfo:
            validate_cross_board_parent_links(
                {"safety": {"cross_board_parent_links": "off"}}
            )
        assert "safety.cross_board_parent_links" in str(excinfo.value)

    def test_ct07_rejects_non_string(self):
        with pytest.raises(ConfigError) as excinfo:
            validate_cross_board_parent_links(
                {"safety": {"cross_board_parent_links": True}}
            )
        assert "safety.cross_board_parent_links" in str(excinfo.value)


# ══════════════════════════════════════════════════════════════════════════
# resolve_cross_board_parent_links — CT08..CT09
# ══════════════════════════════════════════════════════════════════════════

class TestResolve:
    def test_ct08_default_enabled(self):
        assert resolve_cross_board_parent_links({}) == "enabled"

    def test_ct09_returns_configured_value(self):
        cfg = {"safety": {"cross_board_parent_links": "suspended"}}
        assert resolve_cross_board_parent_links(cfg) == "suspended"

    def test_safety_section_present_key_absent_defaults_enabled(self):
        assert resolve_cross_board_parent_links({"safety": {}}) == "enabled"


# ══════════════════════════════════════════════════════════════════════════
# load_current_config — CT10..CT11
# ══════════════════════════════════════════════════════════════════════════

class TestLoadCurrentConfig:
    def test_ct10_reflects_disk_change_without_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        pipe = tmp_path / "pipe.yml"

        pipe.write_text(
            yaml.safe_dump(
                _base_config(safety={"cross_board_parent_links": "enabled"})
            ),
            encoding="utf-8",
        )
        first = load_current_config()
        assert first["safety"]["cross_board_parent_links"] == "enabled"

        pipe.write_text(
            yaml.safe_dump(
                _base_config(safety={"cross_board_parent_links": "suspended"})
            ),
            encoding="utf-8",
        )
        second = load_current_config()
        assert second["safety"]["cross_board_parent_links"] == "suspended"

    def test_ct11_missing_pipe_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ConfigError):
            load_current_config()

    def test_empty_pipe_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pipe.yml").write_text("", encoding="utf-8")
        with pytest.raises(ConfigError):
            load_current_config()


# ══════════════════════════════════════════════════════════════════════════
# check_config — CT12..CT13 (integração)
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def _valid_env(tmp_path, monkeypatch):
    """Ambiente mínimo para check_config: chave SSH presente e cwd isolado."""
    monkeypatch.chdir(tmp_path)
    ssh_key = tmp_path / "id_ed25519"
    ssh_key.write_text("dummy", encoding="utf-8")
    monkeypatch.setenv("PIPE_SSH_KEY_FILE", str(ssh_key))
    return tmp_path


def _write_pipe(path: Path, config: dict):
    (path / "pipe.yml").write_text(yaml.safe_dump(config), encoding="utf-8")


class TestCheckConfigIntegration:
    def test_ct12_rejects_invalid_cross_board_value(self, _valid_env):
        _write_pipe(
            _valid_env,
            _base_config(safety={"cross_board_parent_links": "invalido"}),
        )
        with pytest.raises(ConfigError) as excinfo:
            check_config()
        assert "safety.cross_board_parent_links" in str(excinfo.value)

    def test_ct13_without_safety_section_still_works(self, _valid_env):
        _write_pipe(_valid_env, _base_config())
        config = check_config()
        assert "safety" not in config
        assert config["boards"]["platform"] == "github"

    def test_valid_suspended_passes_check_config(self, _valid_env):
        _write_pipe(
            _valid_env,
            _base_config(safety={"cross_board_parent_links": "suspended"}),
        )
        config = check_config()
        assert config["safety"]["cross_board_parent_links"] == "suspended"
