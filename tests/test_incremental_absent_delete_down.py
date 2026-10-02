"""Testes de poda por ausência no caminho único de sincronização (`sync_remote`).

Migrado do antigo caminho incremental: o invariante preservado é a poda
(delete-down) de issues presentes no snapshot (com id) mas AUSENTES do fetch
atual — arquivadas (o ProjectV2 remove itens arquivados da connection `items`)
ou deletadas no board. A sincronização única reconcilia o board inteiro a cada
execução, sem corte por data da última atualização.
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


def _seed_snapshot(board_id, issues):
    snap = Snapshot(board_id).load()
    for i in issues:
        snap.issues.append(i)
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


SNAP_AT = "2026-09-22T00:00:00Z"


def test_absent_from_fetch_triggers_delete_down():
    """Issue no snapshot ausente do fetch -> delete-down; a presente não some."""
    board = Board(FakePort(listed=[
        # #69 (arquivada no board) NÃO vem no fetch; #70 sim.
        Issue(id="70", title="", body="", column="backlog", updated_at=SNAP_AT),
    ]))
    _seed_snapshot("story", [
        {"id": "69", "column": "encerrado", "status": "ok", "updated_at": SNAP_AT},
        {"id": "70", "column": "backlog", "status": "ok", "updated_at": SNAP_AT},
    ])
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == [(SyncEvent.DELETE_DOWN.value, "69")]


def test_present_issue_not_deleted():
    board = Board(FakePort(listed=[
        Issue(id="70", title="", body="", column="backlog", updated_at=SNAP_AT),
    ]))
    _seed_snapshot("story", [
        {"id": "70", "column": "backlog", "status": "ok", "updated_at": SNAP_AT},
    ])
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == []  # presente e não modificada -> nenhum evento


def test_modified_change_down():
    board = Board(FakePort(listed=[
        Issue(id="71", title="", body="", column="planejamento-tecnico",
              updated_at="2026-09-24T12:00:00Z"),  # mais recente que o snapshot
    ]))
    _seed_snapshot("story", [
        {"id": "71", "column": "backlog", "status": "ok", "updated_at": SNAP_AT},
    ])
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == [(SyncEvent.CHANGE_DOWN.value, "71")]


def test_new_issue_create_down():
    board = Board(FakePort(listed=[
        Issue(id="82", title="", body="", column="backlog",
              updated_at="2026-09-24T12:00:00Z"),  # não está no snapshot
    ]))
    _seed_snapshot("story", [])
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
        {"id": "69", "column": "encerrado", "status": "ok", "updated_at": SNAP_AT},
        {"id": "71", "column": "backlog", "status": "ok", "updated_at": SNAP_AT},
    ])
    q = ChangeQueue()

    sync_remote("story", board, q)

    by_id = {i: e for e, i in _drain(q)}
    assert by_id["69"] == SyncEvent.DELETE_DOWN.value
    assert by_id["71"] == SyncEvent.CHANGE_DOWN.value


# ─────────────────────────────────────────────────────────────────────────────
# GUARDA anti-fetch-incompleto (fix delete-down falso-positivo)
# ─────────────────────────────────────────────────────────────────────────────


class ProbePort(FakePort):
    """FakePort cujo get_issue devolve um resultado configurável por id.

    `probes` mapeia issue_id -> Issue | None (None => node nulo => deletada).
    Ids ausentes do mapa caem no comportamento padrão do FakePort (coluna "").
    """

    def __init__(self, listed=None, probes=None):
        super().__init__(listed=listed)
        self._probes = probes or {}

    def get_issue(self, board_id, issue_id, fullsync=False):
        if issue_id in self._probes:
            return self._probes[issue_id]
        return super().get_issue(board_id, issue_id, fullsync=fullsync)


def test_incomplete_fetch_suppresses_delete_down():
    """Ausente do fetch mas AINDA VIVA no board (coluna definida, não arquivada)
    => fetch incompleto => NÃO podar (delete-down suprimido)."""
    board = Board(ProbePort(
        listed=[  # #69 não veio no fetch (hiccup de paginação); #70 veio
            Issue(id="70", title="", body="", column="backlog", updated_at=SNAP_AT),
        ],
        probes={  # releitura prova que #69 continua viva e ativa
            "69": Issue(id="69", title="", body="", column="desenvolvimento",
                        updated_at=SNAP_AT, archived=False),
        },
    ))
    _seed_snapshot("story", [
        {"id": "69", "column": "desenvolvimento", "status": "ok", "updated_at": SNAP_AT},
        {"id": "70", "column": "backlog", "status": "ok", "updated_at": SNAP_AT},
    ])
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == []  # nenhuma poda: ausência era fetch incompleto


def test_deleted_issue_confirmed_prunes():
    """Releitura devolve None (node nulo => deletada de fato) => poda."""
    board = Board(ProbePort(
        listed=[Issue(id="70", title="", body="", column="backlog", updated_at=SNAP_AT)],
        probes={"69": None},
    ))
    _seed_snapshot("story", [
        {"id": "69", "column": "encerrado", "status": "ok", "updated_at": SNAP_AT},
        {"id": "70", "column": "backlog", "status": "ok", "updated_at": SNAP_AT},
    ])
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == [(SyncEvent.DELETE_DOWN.value, "69")]


def test_archived_issue_confirmed_prunes():
    """Releitura devolve a issue arquivada => poda intencional de arquivadas."""
    board = Board(ProbePort(
        listed=[Issue(id="70", title="", body="", column="backlog", updated_at=SNAP_AT)],
        probes={"69": Issue(id="69", title="", body="", column="encerrado",
                            updated_at=SNAP_AT, archived=True)},
    ))
    _seed_snapshot("story", [
        {"id": "69", "column": "encerrado", "status": "ok", "updated_at": SNAP_AT},
        {"id": "70", "column": "backlog", "status": "ok", "updated_at": SNAP_AT},
    ])
    q = ChangeQueue()

    sync_remote("story", board, q)

    assert _drain(q) == [(SyncEvent.DELETE_DOWN.value, "69")]
