"""Grupo C (gate) — barreira final na seleção de tarefas (#310).

Cobre CT-08, CT-09, CT-10. O gate (`participation.gate_keep` e o filtro em
`keep_task`) só deixa passar intenção confirmada (origin/authorized), ignora as
demais para seleção/avanço, emite evento deduplicado e NÃO faz chamada de rede.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.log import log
from src.core.board import Board, BoardPort
from src.core.snapshot import Snapshot
from src.core import participation as P
import src.__main__ as M


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log._log_dir = Path("logs")
    log._setup()
    P.reset_dispatch_dedup()
    yield


def _log_text():
    path = Path("logs") / f"{date.today().strftime('%Y-%m-%d')}.json"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _blocked_count(issue_id):
    text = _log_text()
    return sum(
        1 for ln in text.splitlines()
        if "dispatch_blocked_unconfirmed_intent" in ln and f"'issue': '{issue_id}'" in ln
    )


# ── CT-08 — gate confirma candidatos e bloqueia intenção não confirmada ───────

@pytest.mark.parametrize("intent,allowed", [
    ("origin", True),
    ("authorized", True),
    ("propagated", False),
    ("unresolved", False),
    (None, False),
])
def test_ct08_gate_decision_per_intent(intent, allowed):
    issue = {"id": "10", "column": "doing"}
    if intent is not None:
        issue["participation_intent"] = intent
    assert P.gate_allows(issue) is allowed
    kept = P.gate_keep("entrega", "doing", issue)
    assert kept is allowed
    if not allowed:
        assert "dispatch_blocked_unconfirmed_intent" in _log_text()


# ── CT-10 — deduplicação do evento de despacho bloqueado ──────────────────────

def test_ct10_dedup_same_board_column_issue():
    issue = {"id": "20", "column": "doing", "participation_intent": "propagated"}
    P.gate_keep("entrega", "doing", issue)
    P.gate_keep("entrega", "doing", issue)  # 2ª: não reemite
    assert _blocked_count("20") == 1

    # Mudar de coluna reemite.
    P.gate_keep("entrega", "review", issue)
    assert _blocked_count("20") == 2

    # Reiniciar o processo (reset) reemite na coluna original.
    P.reset_dispatch_dedup()
    P.gate_keep("entrega", "doing", issue)
    assert _blocked_count("20") == 3


# ── CT-09 — gate não faz nenhuma chamada de rede ──────────────────────────────

class ExplodingPort(BoardPort):
    """Qualquer método levanta AssertionError se chamado (dublê que falha)."""

    def _boom(self, *a, **k):
        raise AssertionError("o gate NÃO pode tocar a porta de board")

    connect = sync_boards = list_issues = get_issue = _boom
    create_issue = move_issue = update_issue = add_comment = _boom
    list_comments = close_issue = remove_from_board = list_participations = _boom


def _cfg():
    return {
        "boards": {
            "platform": "github",
            "entrega": {
                "name": "Entrega",
                "columns": {
                    "todo": {"name": "To Do"},
                    "doing": {"name": "Doing", "agent": "dev",
                              "change": {"advance": "done"}},
                    "done": {"name": "Done", "archive": True},
                },
                "todo": "todo",
            },
        },
        "agents": {"github": {"dev": {"name": "Dev", "model": "m"}}},
    }


def _seed_snapshot(intents):
    snap = Snapshot("entrega")
    snap.board = {"todo": "To Do", "doing": "Doing", "done": "Done"}
    col_dir = Path(".pipe/boards/entrega/doing")
    col_dir.mkdir(parents=True, exist_ok=True)
    issues = []
    for idx, intent in enumerate(intents, start=1):
        body = col_dir / f"issue-{idx}-body.md"
        body.write_text("# Issue\n\ncorpo\n", encoding="utf-8")
        issue = {
            "id": str(idx), "column": "doing", "status": "ok",
            "created_at": f"2026-01-0{idx}T00:00:00Z",
            "body_path": str(body),
        }
        if intent is not None:
            issue["participation_intent"] = intent
        issues.append(issue)
    snap.issues = issues
    snap.save()


def test_ct09_gate_runs_without_network():
    cfg = _cfg()
    # Não confirmadas EXPLÍCITAS mais antigas (avaliadas primeiro pelo gate); a
    # confirmada mais nova é selecionada ao final — provando que o gate avaliou
    # as demais sem tocar a porta de rede.
    _seed_snapshot(["propagated", "unresolved", "origin"])
    M.board = Board(ExplodingPort())
    task = M.keep_task("entrega", cfg)
    assert task is not None
    assert task["issue"]["id"] == "3"  # a confirmada (origin)
    # As não confirmadas, avaliadas antes, geraram evento de bloqueio.
    assert "dispatch_blocked_unconfirmed_intent" in _log_text()
