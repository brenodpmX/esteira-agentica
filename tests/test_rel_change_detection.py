"""RF-05 extensão — mudança de relação é percebida sem bump de updated_at.

Dependências nativas (blocked_by/blocking) e vínculos de sub-issue não movem o
updatedAt da issue nem o Status/coluna. Antes, a sincronização única só
divergia por updated_at ou coluna, então uma troca de bloqueio feita no board
nunca era reconciliada localmente — um bloqueio obsoleto persistia no body e
podia congelar a fila. Agora:

1. O adapter dobra blockedBy/blocking/parent/subIssues/state na MESMA query de
   list_issues (custo ~zero), populando as relações em cada Issue.
2. sync_remote compara essas relações contra o snapshot e enfileira change-down
   (fullsync) quando divergem, independente de qualquer timestamp.
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
from src.adapters.github_board import GitHubBoardAdapter


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


# ── 1. Parsing: list_issues popula as relações dobradas na query ──────────────

class _ListIssuesAdapter(GitHubBoardAdapter):
    """Adapter com _gql fake que devolve uma página de items com relações."""

    def __init__(self, page):
        self._repo = "owner/repo"
        self._projects = {"b": {"project_id": "PROJ1"}}
        self._page = page

    def _penalty_check(self):
        pass

    def _board_meta(self, board_id):
        return {"project_id": "PROJ1"}

    def _gql(self, query, **vars):
        if "items(first:5" in query:
            return {"node": {"items": self._page}}
        raise AssertionError(f"query inesperada: {query[:60]}")


def _content(number, **rel):
    base = {
        "number": number, "title": f"Issue {number}", "body": "corpo",
        "updatedAt": "2026-10-05T12:00:00Z", "state": "OPEN",
        "labels": {"nodes": []},
        "parent": None,
        "subIssues": {"totalCount": 0, "nodes": []},
        "blockedBy": {"totalCount": 0, "nodes": []},
        "blocking": {"totalCount": 0, "nodes": []},
    }
    base.update(rel)
    return base


def _item(content, column="backlog"):
    return {
        "id": f"PVTI_{content['number']}",
        "isArchived": False,
        "fieldValues": {"nodes": [
            {"field": {"name": "Status"}, "name": column}]},
        "content": content,
    }


def test_list_issues_parses_folded_relations():
    page = {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [
        _item(_content(
            73,
            parent={"number": 3},
            subIssues={"totalCount": 2, "nodes": [{"number": 221}, {"number": 222}]},
            blockedBy={"totalCount": 1, "nodes": [{"number": 226}]},
            blocking={"totalCount": 2, "nodes": [{"number": 79}, {"number": 3}]},
        ), column="aguardando-tasks"),
    ]}
    adapter = _ListIssuesAdapter(page)

    issues = adapter.list_issues("b")

    assert len(issues) == 1
    i = issues[0]
    assert i.id == "73"
    assert i.column == "aguardando-tasks"
    assert i.state == "open"
    assert i.parent == "3"
    assert i.children == ["221", "222"]
    assert i.blocked_by == ["226"]
    assert i.blocks == ["79", "3"]


def test_list_issues_truncation_warns(capsys):
    """totalCount > nós recebidos emite warning (mudança além da página)."""
    page = {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [
        _item(_content(
            9,
            blockedBy={"totalCount": 99, "nodes": [{"number": 10}]},
        )),
    ]}
    adapter = _ListIssuesAdapter(page)

    issues = adapter.list_issues("b")

    assert issues[0].blocked_by == ["10"]
    assert "truncado" in capsys.readouterr().out


# ── 2. Detecção: relação diverge sem updated_at/coluna mudarem ────────────────

class _ListPort(BoardPort):
    def __init__(self, listed):
        self._listed = listed

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return list(self._listed)
    def get_issue(self, board_id, issue_id, fullsync=False):
        return Issue(id=issue_id, title="x", body="x", column="aguardando-tasks",
                     updated_at="2026-10-05T12:00:00Z")
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, *a, **k): pass
    def update_issue(self, *a, **k): pass
    def add_comment(self, *a, **k): pass
    def list_comments(self, *a, **k): return []
    def close_issue(self, *a, **k): pass
    def set_labels(self, *a, **k): pass
    def add_label(self, *a, **k): pass
    def remove_label(self, *a, **k): pass
    def set_parent(self, *a, **k): pass
    def set_children(self, *a, **k): pass
    def set_blocked_by(self, *a, **k): pass
    def set_blocks(self, *a, **k): pass
    def archive_issue(self, *a, **k): pass
    def unarchive_issue(self, *a, **k): pass


def _seed(board_id, issues):
    snap = Snapshot(board_id).load()
    for i in issues:
        snap.issues.append(i)
    snap.save()


_TS = "2026-10-05T12:00:00Z"  # idêntico em snapshot e remoto: sem bump


def _listed_issue(**rel):
    base = dict(id="73", title="x", body="x", column="aguardando-tasks",
                updated_at=_TS, blocked_by=[], blocks=[], parent=None, children=[])
    base.update(rel)
    return Issue(**base)


def _snap_issue(**rel):
    base = {"id": "73", "column": "aguardando-tasks", "status": "ok",
            "updated_at": _TS, "blocked_by": [], "blocks": [],
            "parent": None, "children": []}
    base.update(rel)
    return base


@pytest.mark.parametrize("remote_rel,snap_rel", [
    ({"blocked_by": []}, {"blocked_by": ["226"]}),   # bloqueio obsoleto removido no board
    ({"blocked_by": ["226"]}, {"blocked_by": []}),   # bloqueio novo no board
    ({"blocks": ["79"]}, {"blocks": []}),
    ({"parent": "3"}, {"parent": None}),
    ({"children": ["221"]}, {"children": []}),
])
def test_relation_divergence_enqueues_change_down(remote_rel, snap_rel):
    board = Board(_ListPort([_listed_issue(**remote_rel)]))
    _seed("b", [_snap_issue(**snap_rel)])
    q = ChangeQueue()

    sync_remote("b", board, q)

    item = q.getNext()
    assert item is not None, f"sem change-down para {remote_rel} vs {snap_rel}"
    assert item.event == SyncEvent.CHANGE_DOWN.value
    assert item.id == "73"
    assert item.fullsync is True


def test_no_divergence_when_relations_equal():
    """Relações iguais + mesmo updated_at/coluna => nenhum evento."""
    board = Board(_ListPort([_listed_issue(blocked_by=["226"], blocks=["79"],
                                           parent="3", children=["221"])]))
    _seed("b", [_snap_issue(blocked_by=["226"], blocks=["79"],
                            parent="3", children=["221"])])
    q = ChangeQueue()

    sync_remote("b", board, q)

    assert q.getNext() is None


def test_order_insensitive_no_false_positive():
    """Mesma relação em ordem diferente não é divergência."""
    board = Board(_ListPort([_listed_issue(blocked_by=["226", "79"])]))
    _seed("b", [_snap_issue(blocked_by=["79", "226"])])
    q = ChangeQueue()

    sync_remote("b", board, q)

    assert q.getNext() is None
