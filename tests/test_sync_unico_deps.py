"""CT-02b — Modificação reconcilia dependências de bloqueio (fullsync sempre).

Caso central do RF-05: toda sincronização reconcilia as relações de bloqueio,
não apenas propriedades. O change-down enfileirado pela sincronização única é
`fullsync=True`; ao aplicá-lo, `get_issue` é chamado com `fullsync=True` e o
snapshot passa a refletir as dependências vindas do board (ex.: 80 -> 90).

Reaproveita o invariante do gatilho de par recíproco (condição de parada) já
coberto por `tests/test_sync_optimization.py::test_pair_trigger_*`.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot
from src.core.sync import sync_remote, apply_changes


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


class FakePort(BoardPort):
    """Fake cujo get_issue(fullsync=True) devolve blocked_by=['90'].

    Registra as chamadas de get_issue para asserir que o down foi fullsync.
    """

    def __init__(self, listed=None):
        self._listed = listed or []
        self.get_issue_calls = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return list(self._listed)

    def get_issue(self, board_id, issue_id, fullsync=False):
        self.get_issue_calls.append((issue_id, fullsync))
        issue = Issue(id=issue_id, title="Issue 70", body="corpo",
                      column="desenvolvimento",
                      updated_at="2026-09-24T12:00:00Z")
        if fullsync:
            # Dependência mudou no board: 80 -> 90.
            issue.blocked_by = ["90"]
            issue.blocks = []
        return issue

    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass
    def set_labels(self, board_id, issue_id, labels): pass
    def add_label(self, board_id, issue_id, label): pass
    def remove_label(self, board_id, issue_id, label): pass
    def set_parent(self, board_id, issue_id, parent_id, known_current=None): pass
    def set_children(self, board_id, issue_id, children_ids, known_current=None): pass
    def set_blocked_by(self, board_id, issue_id, blocker_ids, known_current=None): pass
    def set_blocks(self, board_id, issue_id, blocked_ids, known_current=None): pass
    def archive_issue(self, board_id, issue_id): pass
    def unarchive_issue(self, board_id, issue_id): pass


def _seed_snapshot(board_id, issues):
    snap = Snapshot(board_id).load()
    for i in issues:
        snap.issues.append(i)
    snap.save()


def test_ct02b_change_down_is_fullsync():
    """(a) obrigatório: o change-down enfileirado para #70 é fullsync=True."""
    board = Board(FakePort(listed=[
        Issue(id="70", title="Issue 70", body="", column="desenvolvimento",
              updated_at="2026-09-24T12:00:00Z"),
    ]))
    _seed_snapshot("b", [
        {"id": "70", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z", "blocked_by": ["80"], "blocks": []},
    ])
    q = ChangeQueue()

    sync_remote("b", board, q)

    item = q.getNext()
    assert item is not None
    assert item.event == SyncEvent.CHANGE_DOWN.value and item.id == "70"
    assert item.fullsync is True


def test_ct02b_dependencies_reconciled_after_apply():
    """(b) após aplicar o down: get_issue é chamado com fullsync=True e o
    snapshot de #70 reflete blocked_by=['90'] (reconciliado, não mais ['80'])."""
    port = FakePort(listed=[
        Issue(id="70", title="Issue 70", body="", column="desenvolvimento",
              updated_at="2026-09-24T12:00:00Z"),
    ])
    board = Board(port)
    _seed_snapshot("b", [
        {"id": "70", "column": "desenvolvimento", "status": "ok",
         "body_path": ".pipe/boards/b/desenvolvimento/70-issue-70-body.md",
         "updated_at": "2026-09-22T00:00:00Z", "blocked_by": ["80"], "blocks": []},
    ])
    # Precisa existir o arquivo body para o change-down reescrever.
    body_file = Path(".pipe/boards/b/desenvolvimento/70-issue-70-body.md")
    body_file.parent.mkdir(parents=True, exist_ok=True)
    body_file.write_text("# Issue 70\n\ncorpo\n", encoding="utf-8")
    q = ChangeQueue()

    sync_remote("b", board, q)
    apply_changes(board, q, config={})

    # get_issue foi chamado com fullsync=True ao aplicar o change-down.
    assert ("70", True) in port.get_issue_calls

    snap = Snapshot("b").load()
    data = snap.issue("70")
    assert data["blocked_by"] == ["90"]
    assert data["blocks"] == []
