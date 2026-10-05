"""Grupo D — contingência reversível `safety.cross_board_parent_links` (#310).

Cobre CT-18 (recusa vínculo cross-board, permite mesmo quadro), CT-19 (relida
do disco sem cache, sem reinício) e CT-20 (validação da chave).
"""

import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.log import log
from src.core.config import validate_safety, ConfigError
from src.core import participation_reconcile as PR


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log._log_dir = Path("logs")
    log._setup()
    yield


def _log_text():
    path = Path("logs") / f"{date.today().strftime('%Y-%m-%d')}.json"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _write_pipe(value):
    data = {"safety": {"cross_board_parent_links": value}} if value is not None else {}
    Path("pipe.yml").write_text(yaml.safe_dump(data), encoding="utf-8")


# ── CT-18 — contingência ativa recusa vínculo cross-board; mesmo quadro ok ────

def test_ct18_suspended_blocks_cross_board_allows_same_board():
    _write_pipe("suspended")

    # Vínculo cross-board: recusado + evento.
    with pytest.raises(PR.CrossBoardLinkBlocked):
        PR.guard_cross_board_link(parent="10", child="20",
                                  parent_board="epicos", child_board="historias",
                                  config_version="suspended")
    assert "cross_board_link_blocked" in _log_text()

    # Vínculo no MESMO quadro: permitido mesmo com contingência suspensa.
    assert PR.guard_cross_board_link("30", "40", "historias", "historias") is True


def test_ct18_enabled_allows_cross_board():
    _write_pipe("enabled")
    assert PR.guard_cross_board_link("10", "20", "epicos", "historias") is True


# ── CT-19 — reversível sem reinício (relida do disco, sem cache) ──────────────

def test_ct19_reversible_without_restart():
    _write_pipe("suspended")
    assert PR.cross_board_links_suspended() is True
    with pytest.raises(PR.CrossBoardLinkBlocked):
        PR.guard_cross_board_link("1", "2", "epicos", "historias")

    # Altera o arquivo em disco (sem reiniciar nada) — efeito imediato.
    _write_pipe("enabled")
    assert PR.cross_board_links_suspended() is False
    assert PR.guard_cross_board_link("1", "2", "epicos", "historias") is True


# ── CT-20 — validação da chave rejeita valor inválido ─────────────────────────

@pytest.mark.parametrize("value", [
    "Enabled", " enabled ", "disabled", "", 123, True, "SUSPENDED",
])
def test_ct20_invalid_values_rejected(value):
    with pytest.raises(ConfigError) as exc:
        validate_safety({"safety": {"cross_board_parent_links": value}})
    msg = str(exc.value)
    assert "safety.cross_board_parent_links" in msg
    assert repr(value) in msg


@pytest.mark.parametrize("config", [
    {},                                    # seção ausente ⇒ enabled
    {"safety": {}},                        # chave ausente ⇒ enabled
    {"safety": {"cross_board_parent_links": "enabled"}},
    {"safety": {"cross_board_parent_links": "suspended"}},
])
def test_ct20_valid_configs_accepted(config):
    validate_safety(config)  # não deve lançar


def test_ct20_safety_not_a_map_rejected():
    with pytest.raises(ConfigError):
        validate_safety({"safety": "enabled"})
