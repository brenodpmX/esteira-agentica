"""Grupo A — classificação pura de intenção (#310).

Cobre CT-04, CT-07, CT-01a, CT-01c, CT-origem-01 e CT-06 (determinismo). A
função sob teste (`classify_participation`) é PURA e sem I/O de rede — nenhum
dublê de porta é necessário; só o estado de entrada (config, rótulos,
presenças) é fornecido.
"""

import random
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.log import log
from src.core import participation as P
from src.core.participation import Participation, classify_participation


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log._log_dir = Path("logs")
    log._setup()
    yield


def _cfg():
    return {
        "boards": {
            "platform": "github",
            "entrega": {"name": "Entrega", "columns": {"doing": {"name": "Doing"}}},
            "epicos": {"name": "Epicos", "columns": {"doing": {"name": "Doing"}}},
            "historias": {"name": "Historias", "columns": {"doing": {"name": "Doing"}}},
            "tarefas": {"name": "Tarefas", "columns": {"doing": {"name": "Doing"}}},
        }
    }


def _log_text():
    path = Path("logs") / f"{date.today().strftime('%Y-%m-%d')}.json"
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ── CT-04 — presença autorizada por rótulo válido (com e sem coluna) ──────────

@pytest.mark.parametrize("column", ["", "Doing"])
def test_ct04_authorized_label_regardless_of_column(column):
    labels = ["board-intent-entrega"]
    result = classify_participation(
        "100", "entrega", labels, [], _cfg(), column=column,
    )
    assert result.intent == P.AUTHORIZED
    assert result.confirmed is True
    assert result.should_remove is False


# ── CT-07 — rótulo com quadro inexistente é ignorado (com aviso) ──────────────

def test_ct07_label_with_unknown_board_is_ignored_with_warning():
    labels = ["board-intent-naoexiste"]
    # Sem outra evidência de propagação e sem parent cross-board: cai em origem.
    result = classify_participation("101", "entrega", labels, [], _cfg())
    assert result.intent != P.AUTHORIZED
    assert result.intent == P.ORIGIN  # resto da evidência decide
    text = _log_text()
    assert "participation_authorization_label_invalid" in text
    assert "board-intent-naoexiste" in text
    assert "naoexiste" in text


def test_ct07_malformed_label_does_not_raise():
    # Rótulo com prefixo mas sufixo vazio não deve lançar — apenas ignorado.
    classify_participation("102", "entrega", ["board-intent-"], [], _cfg())


# ── CT-01a — propagação por presença anterior com coluna conhecida ────────────

def test_ct01a_propagated_when_known_presence_with_column_in_other_board():
    known = [Participation(item_id="I1", board_id="historias",
                           project_id="P1", column="doing")]
    result = classify_participation(
        "103", "epicos", [], known, _cfg(), column="",
        has_cross_board_parent=True,
    )
    assert result.intent == P.PROPAGATED
    assert result.should_remove is True
    assert result.evidence["proof_board"] == "historias"


# ── CT-01c — presença isolada sem prova não vira origem nem propagada ─────────

def test_ct01c_isolated_parent_without_proof_is_unresolved():
    # Parent em outro board, mas NENHUMA presença confirmada em board configurado.
    result = classify_participation(
        "104", "epicos", [], [], _cfg(), has_cross_board_parent=True,
    )
    assert result.intent == P.UNRESOLVED
    assert result.intent != P.ORIGIN
    assert result.intent != P.PROPAGATED


def test_ct01c_known_presence_without_known_column_is_unresolved():
    # Duplicidade ambígua: presença em outro board SEM coluna conhecida.
    known = [Participation(item_id="I1", board_id="historias",
                           project_id="P1", column="")]
    result = classify_participation("105", "epicos", [], known, _cfg())
    assert result.intent == P.UNRESOLVED


# ── CT-origem-01 — primeira presença em quadro configurado é origem ───────────

def test_ct_origem_first_presence_is_origin():
    result = classify_participation("106", "entrega", [], [], _cfg())
    assert result.intent == P.ORIGIN
    assert result.confirmed is True


# ── CT-06 — determinismo (ordens diferentes, mesmo resultado) ─────────────────

def test_ct06_determinism_across_orderings():
    cfg = _cfg()
    cases = [
        # (issue, board, labels, known, kwargs)
        ("200", "entrega", [], [], {}),                       # origin
        ("201", "entrega", ["board-intent-entrega"], [], {}),  # authorized
        ("202", "epicos", [],
         [Participation("I", "historias", "P", "doing")],
         {"has_cross_board_parent": True}),                   # propagated
        ("203", "epicos", [], [], {"has_cross_board_parent": True}),  # unresolved
    ]

    def run(order):
        out = {}
        for issue, board, labels, known, kw in order:
            out[issue] = classify_participation(
                issue, board, labels, known, cfg, **kw
            ).intent
        return out

    baseline = run(cases)
    for seed in (1, 2, 3):
        shuffled = cases[:]
        random.Random(seed).shuffle(shuffled)
        assert run(shuffled) == baseline
    assert run(list(reversed(cases))) == baseline

    assert baseline == {
        "200": P.ORIGIN, "201": P.AUTHORIZED,
        "202": P.PROPAGATED, "203": P.UNRESOLVED,
    }
