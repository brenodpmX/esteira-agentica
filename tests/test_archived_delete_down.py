"""Testes do gatilho archived -> delete-down.

Cobrem o comportamento (v1.14.0) em que itens arquivados no board:
- NÃO são reinseridos no board local (sem create/change-down);
- servem apenas como gatilho de delete-down quando o id ainda existe no
  snapshot, tanto na varredura completa (`detect_board_changes`) quanto no
  sync incremental por-ciclo (`sync_remote`), desacoplando a poda do
  startup/diária;
- são ignorados quando já não estão no snapshot (idempotência).

Também cobrem o parsing do adapter que passa a superficializar arquivadas como
Issue leve (archived=True, sem coluna).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


# ── Fakes / helpers ───────────────────────────────────────────────────────────

class FakePort(BoardPort):
    """Adapter fake: retorna listas pré-configuradas de issues."""

    def __init__(self, listed=None, since_listed=None):
        self._listed = listed or []
        self._since_listed = since_listed if since_listed is not None else (listed or [])

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return list(self._listed)
    def list_issues_since(self, board_id, since): return list(self._since_listed)
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


def _seed_snapshot(board_id, issues, last_update=None):
    snap = Snapshot(board_id).load()
    for i in issues:
        snap.issues.append(i)
    if last_update is not None:
        snap.last_board_update = last_update
    snap.save()


def _drain(queue):
    """Retorna [(event, id), ...] de todos os itens da fila."""
    out = []
    while True:
        item = queue.getNext()
        if item is None:
            break
        out.append((item.event, item.id))
        queue.remove(item.uuid)
    return out


# ── Adapter: parsing de arquivadas ────────────────────────────────────────────

def test_adapter_list_issues_surfaces_archived_as_trigger(monkeypatch):
    from src.adapters.github_board import GitHubBoardAdapter

    adapter = object.__new__(GitHubBoardAdapter)
    monkeypatch.setattr(GitHubBoardAdapter, "_tp", "", raising=False)
    monkeypatch.setattr(adapter, "_penalty_check", lambda: None, raising=False)
    monkeypatch.setattr(adapter, "_board_meta", lambda board_id: {"project_id": "PID"}, raising=False)

    page = {
        "node": {"items": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {  # arquivada -> gatilho leve
                    "isArchived": True,
                    "content": {"number": 69, "title": "arquivada",
                                "updatedAt": "2026-09-24T20:55:50Z"},
                },
                {  # normal
                    "isArchived": False,
                    "fieldValues": {"nodes": [
                        {"field": {"name": "Status"}, "name": "backlog"}
                    ]},
                    "content": {"number": 70, "title": "ativa", "body": "b",
                                "updatedAt": "2026-09-24T10:00:00Z",
                                "labels": {"nodes": [{"name": "x"}]}},
                },
                {"isArchived": False, "content": None},  # sem content -> ignora
            ],
        }}
    }
    monkeypatch.setattr(adapter, "_gql", lambda query, **kw: page, raising=False)

    issues = adapter.list_issues("story")
    by_id = {i.id: i for i in issues}

    assert set(by_id) == {"69", "70"}
    assert by_id["69"].archived is True
    assert by_id["69"].column == ""      # não reinserida: sem coluna
    assert by_id["70"].archived is False
    assert by_id["70"].column == "backlog"
    assert by_id["70"].labels == ["x"]


def test_adapter_list_issues_since_always_includes_archived(monkeypatch):
    """Arquivadas passam mesmo com updated_at <= since (gatilho por-ciclo)."""
    from src.adapters.github_board import GitHubBoardAdapter

    adapter = object.__new__(GitHubBoardAdapter)
    monkeypatch.setattr(GitHubBoardAdapter, "_tp", "", raising=False)
    monkeypatch.setattr(adapter, "_penalty_check", lambda: None, raising=False)
    monkeypatch.setattr(adapter, "list_issues", lambda board_id: [
        # arquivada com updated_at IGUAL ao since -> não passaria por '> since'
        Issue(id="69", title="", body="", column="", archived=True,
              updated_at="2026-09-24T20:00:00Z"),
        # normal antiga -> filtrada
        Issue(id="80", title="", body="", column="backlog",
              updated_at="2026-09-24T19:00:00Z"),
        # normal recente -> passa
        Issue(id="81", title="", body="", column="backlog",
              updated_at="2026-09-24T21:00:00Z"),
    ], raising=False)

    out = adapter.list_issues_since("story", since="2026-09-24T20:00:00Z")
    ids = {i.id for i in out}
    assert "69" in ids   # arquivada incluída apesar de updated_at == since
    assert "81" in ids   # recente
    assert "80" not in ids  # antiga, não arquivada -> filtrada


# ── detect_board_changes (varredura completa) ─────────────────────────────────

def test_detect_archived_in_snapshot_triggers_delete_down():
    board = Board(FakePort(listed=[
        Issue(id="69", title="", body="", column="", archived=True,
              updated_at="2026-09-24T20:55:50Z"),
    ]))
    _seed_snapshot("story", [
        {"id": "69", "column": "encerrado", "status": "ok",
         "updated_at": "2026-09-24T18:00:00Z"},
    ])
    snap = Snapshot("story").load()
    q = ChangeQueue()

    board.detect_board_changes("story", snap, q)

    assert _drain(q) == [(SyncEvent.DELETE_DOWN.value, "69")]


def test_detect_archived_not_in_snapshot_is_ignored():
    board = Board(FakePort(listed=[
        Issue(id="999", title="", body="", column="", archived=True,
              updated_at="2026-09-24T20:55:50Z"),
    ]))
    _seed_snapshot("story", [])  # snapshot vazio
    snap = Snapshot("story").load()
    q = ChangeQueue()

    board.detect_board_changes("story", snap, q)

    assert _drain(q) == []  # nem delete-down nem create-down


def test_detect_normal_issues_still_classified():
    """Regressão: o branch de arquivada não afeta create/change-down normais."""
    board = Board(FakePort(listed=[
        Issue(id="70", title="nova", body="", column="backlog",
              updated_at="2026-09-24T10:00:00Z"),                       # unknown -> create
        Issue(id="71", title="mud", body="", column="planejamento-tecnico",
              updated_at="2026-09-24T12:00:00Z"),                       # coluna mudou -> change
    ]))
    _seed_snapshot("story", [
        {"id": "71", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-24T09:00:00Z"},
    ])
    snap = Snapshot("story").load()
    q = ChangeQueue()

    board.detect_board_changes("story", snap, q)

    by_id = {issue_id: event for event, issue_id in _drain(q)}
    assert by_id["70"] == SyncEvent.CREATE_DOWN.value
    assert by_id["71"] == SyncEvent.CHANGE_DOWN.value


# ── sync_remote (incremental por-ciclo) ───────────────────────────────────────

def test_sync_remote_archived_in_snapshot_triggers_delete_down():
    from src.core.sync import sync_remote

    board = Board(FakePort(since_listed=[
        Issue(id="69", title="", body="", column="", archived=True,
              updated_at="2026-09-24T20:55:50Z"),
    ]))
    _seed_snapshot("story", [
        {"id": "69", "column": "encerrado", "status": "ok",
         "updated_at": "2026-09-24T18:00:00Z"},
    ], last_update="2026-09-24T00:00:00Z")  # since truthy -> caminho incremental
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == [(SyncEvent.DELETE_DOWN.value, "69")]


def test_sync_remote_archived_not_in_snapshot_is_ignored():
    from src.core.sync import sync_remote

    board = Board(FakePort(since_listed=[
        Issue(id="999", title="", body="", column="", archived=True,
              updated_at="2026-09-24T20:55:50Z"),
    ]))
    _seed_snapshot("story", [], last_update="2026-09-24T00:00:00Z")
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == []
