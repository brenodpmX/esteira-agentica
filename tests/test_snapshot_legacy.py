"""CT-07 / CT-07b — Retrocompatibilidade do snapshot legado.

RN-05: a descontinuação do campo de corte incremental (`last_board_update`) não
pode quebrar a leitura de snapshots antigos que ainda o contenham (campo
desconhecido é ignorado, não rejeitado); e o snapshot recém-escrito não
reintroduz o campo.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot, BOARDS_DIR
from src.core.sync import sync_remote


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


class FakePort(BoardPort):
    def __init__(self, listed=None):
        self._listed = listed or []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return list(self._listed)
    def get_issue(self, board_id, issue_id, fullsync=False):
        return Issue(id=issue_id, title="", body="", column="")
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


def _write_legacy_snapshot(board_id):
    """Escreve um snapshot.json legado contendo o campo de corte descontinuado."""
    path = BOARDS_DIR / board_id / "snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    legacy = {
        "board": {"backlog": "Backlog"},
        "issues": [
            {"id": "40", "column": "backlog", "status": "ok",
             "updated_at": "2026-09-01T00:00:00Z"},
        ],
        "last_sync": "2026-09-01T00:00:00Z",
        "last_board_update": "2026-09-01T00:00:00Z",  # campo legado/descontinuado
    }
    path.write_text(json.dumps(legacy, indent=2, ensure_ascii=False),
                    encoding="utf-8")


# ── CT-07: leitura de snapshot legado não falha ───────────────────────────────

def test_ct07_legacy_snapshot_loads_without_error():
    _write_legacy_snapshot("b")

    # load() não deve levantar — chave desconhecida é ignorada.
    snap = Snapshot("b").load()
    assert snap.issue("40") is not None
    assert snap.last_sync == "2026-09-01T00:00:00Z"


def test_ct07_sync_runs_normally_over_legacy_snapshot():
    """A sincronização ocorre normalmente sobre um snapshot legado, SEM usar o
    valor legado como corte: issue nova com updated_at antigo ainda é detectada."""
    _write_legacy_snapshot("b")
    board = Board(FakePort(listed=[
        Issue(id="40", title="", body="", column="backlog",
              updated_at="2026-09-01T00:00:00Z"),  # inalterada
        Issue(id="51", title="", body="", column="backlog",
              updated_at="2026-08-01T00:00:00Z"),  # nova, updated_at < corte legado
    ]))
    q = ChangeQueue()

    sync_remote("b", board, q)

    events = []
    while True:
        it = q.getNext()
        if it is None:
            break
        events.append((it.event, it.id))
        q.remove(it.uuid)
    # #51 criada apesar do updated_at anterior ao corte legado (corte não decide).
    assert (SyncEvent.CREATE_DOWN.value, "51") in events


# ── CT-07b: campo de corte é descontinuado na escrita ─────────────────────────

def test_ct07b_rewritten_snapshot_drops_legacy_cut_field():
    """Após load+save de um snapshot legado, o payload novo NÃO contém mais o
    campo de corte incremental (descontinuado)."""
    _write_legacy_snapshot("b")

    Snapshot("b").load().save()

    raw = json.loads((BOARDS_DIR / "b" / "snapshot.json").read_text(encoding="utf-8"))
    assert "last_board_update" not in raw


def test_ct07b_fresh_snapshot_has_no_cut_field():
    """Snapshot criado do zero não possui o campo de corte."""
    snap = Snapshot("b").load()
    snap.issues.append({"id": "1", "column": "backlog", "status": "ok"})
    snap.save()

    raw = json.loads((BOARDS_DIR / "b" / "snapshot.json").read_text(encoding="utf-8"))
    assert "last_board_update" not in raw
