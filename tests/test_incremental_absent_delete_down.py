"""Testes do delete-down por ausência no sync incremental (`sync_remote`).

Comportamento (v1.14.0): o sync incremental por-ciclo, além de create/change-down
por `updated_at > since`, passa a podar (delete-down) issues presentes no snapshot
mas AUSENTES do fetch atual — arquivadas (o ProjectV2 remove itens arquivados da
connection `items`) ou deletadas no board. Antes só a varredura completa
(`detect_board_changes`, startup/diária) fazia isso, o que congelava boards
`parallel:false` com uma issue terminal arquivada até o full sync do dia seguinte.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot
from src.core.sync import sync_remote


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


class FakePort(BoardPort):
    """Adapter fake: list_issues devolve uma lista pré-configurada."""

    def __init__(self, listed=None):
        self._listed = listed or []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return list(self._listed)
    def list_issues_since(self, board_id, since):
        return [i for i in self._listed if i.updated_at and i.updated_at > since]
    def get_issue(self, board_id, issue_id, fullsync=False):
        return Issue(id=issue_id, title="", body="", column="")
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass
    def reopen_issue(self, board_id, issue_id): pass
    def set_labels(self, board_id, issue_id, labels): pass
    def add_label(self, board_id, issue_id, label): pass
    def remove_label(self, board_id, issue_id, label): pass
    def set_parent(self, board_id, issue_id, parent_id, known_current=None): pass
    def set_children(self, board_id, issue_id, children_ids, known_current=None): pass
    def set_blocked_by(self, board_id, issue_id, blocker_ids, known_current=None): pass
    def set_blocks(self, board_id, issue_id, blocked_ids, known_current=None): pass
    def archive_issue(self, board_id, issue_id): pass
    def unarchive_issue(self, board_id, issue_id): pass


def _seed_snapshot(board_id, issues, last_update):
    snap = Snapshot(board_id).load()
    for i in issues:
        snap.issues.append(i)
    snap.last_board_update = last_update
    snap.save()


def _drain(queue):
    out = []
    while True:
        item = queue.getNext()
        if item is None:
            break
        out.append((item.event, item.id))
        queue.remove(item.uuid)
    return out


SINCE = "2026-09-24T00:00:00Z"


def test_absent_from_fetch_triggers_delete_down():
    """Issue no snapshot ausente do fetch -> delete-down; a presente não some."""
    board = Board(FakePort(listed=[
        # #69 (arquivada no board) NÃO vem no fetch; #70 sim.
        Issue(id="70", title="", body="", column="backlog",
              updated_at="2026-09-22T00:00:00Z"),
    ]))
    _seed_snapshot("story", [
        {"id": "69", "column": "encerrado", "status": "ok", "updated_at": SINCE},
        {"id": "70", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
    ], last_update=SINCE)
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == [(SyncEvent.DELETE_DOWN.value, "69")]


def test_present_issue_not_deleted():
    board = Board(FakePort(listed=[
        Issue(id="70", title="", body="", column="backlog",
              updated_at="2026-09-22T00:00:00Z"),
    ]))
    _seed_snapshot("story", [
        {"id": "70", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
    ], last_update=SINCE)
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == []  # presente e não modificada -> nenhum evento


def test_modified_since_change_down():
    board = Board(FakePort(listed=[
        Issue(id="71", title="", body="", column="planejamento-tecnico",
              updated_at="2026-09-24T12:00:00Z"),  # > since
    ]))
    _seed_snapshot("story", [
        {"id": "71", "column": "backlog", "status": "ok", "updated_at": SINCE},
    ], last_update=SINCE)
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == [(SyncEvent.CHANGE_DOWN.value, "71")]


def test_unknown_since_create_down():
    board = Board(FakePort(listed=[
        Issue(id="82", title="", body="", column="backlog",
              updated_at="2026-09-24T12:00:00Z"),  # > since, não está no snapshot
    ]))
    _seed_snapshot("story", [], last_update=SINCE)
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == [(SyncEvent.CREATE_DOWN.value, "82")]


def test_delete_and_change_together():
    """Poda a ausente e reconcilia a modificada na mesma passada."""
    board = Board(FakePort(listed=[
        Issue(id="71", title="", body="", column="code-review",
              updated_at="2026-09-24T12:00:00Z"),  # modificada -> change
        # #69 ausente -> delete
    ]))
    _seed_snapshot("story", [
        {"id": "69", "column": "encerrado", "status": "ok", "updated_at": SINCE},
        {"id": "71", "column": "backlog", "status": "ok", "updated_at": SINCE},
    ], last_update=SINCE)
    q = ChangeQueue()

    sync_remote("story", board, q)

    by_id = {i: e for e, i in _drain(q)}
    assert by_id["69"] == SyncEvent.DELETE_DOWN.value
    assert by_id["71"] == SyncEvent.CHANGE_DOWN.value
