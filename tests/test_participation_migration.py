"""Grupo C (migração) — migração de legados no startup (#310).

Cobre CT-11 (board único → origem), CT-12 (duplicidade sem autorização →
unresolved em ambas) e CT-13 (idempotência e não sobrescrita).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.log import log
from src.core.snapshot import Snapshot
from src.core import participation as P


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log._log_dir = Path("logs")
    log._setup()
    yield


def _cfg():
    cols = {"doing": {"name": "Doing"}}
    return {
        "boards": {
            "platform": "github",
            "epicos": {"name": "Epicos", "columns": cols},
            "historias": {"name": "Historias", "columns": cols},
        }
    }


def _seed(board_id, issues):
    snap = Snapshot(board_id)
    snap.board = {"doing": "Doing"}
    snap.issues = issues
    snap.save()


def _intent(board_id, issue_id):
    issue = Snapshot(board_id).load().issue(issue_id)
    return issue.get("participation_intent") if issue else None


# ── CT-11 — board único vira origem ───────────────────────────────────────────

def test_ct11_single_board_becomes_origin():
    _seed("epicos", [{"id": "1", "column": "doing"}])
    P.migrate_legacy_intents(_cfg())
    assert _intent("epicos", "1") == P.ORIGIN


# ── CT-12 — duplicidade sem autorização vira unresolved em ambas ──────────────

def test_ct12_duplicate_without_authorization_becomes_unresolved_both():
    _seed("epicos", [{"id": "7", "column": "doing"}])
    _seed("historias", [{"id": "7", "column": "doing"}])
    P.migrate_legacy_intents(_cfg())
    assert _intent("epicos", "7") == P.UNRESOLVED
    assert _intent("historias", "7") == P.UNRESOLVED


# ── CT-13 — idempotência e não sobrescrita ────────────────────────────────────

def test_ct13_idempotent_and_never_overwrites():
    # Uma issue já preenchida (authorized) e outra sem o campo.
    _seed("epicos", [
        {"id": "1", "column": "doing", "participation_intent": "authorized"},
        {"id": "2", "column": "doing"},
    ])
    cfg = _cfg()
    P.migrate_legacy_intents(cfg)
    first = Snapshot("epicos").load().issues
    # Já preenchida não muda; sem campo vira origem.
    assert _intent("epicos", "1") == "authorized"
    assert _intent("epicos", "2") == P.ORIGIN

    # Segunda execução não altera nada.
    P.migrate_legacy_intents(cfg)
    second = Snapshot("epicos").load().issues
    assert first == second
