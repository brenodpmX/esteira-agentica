"""CT-01..CT-04 — Sincronização única: reconciliação completa em execução única.

Alvo: o caminho único de descoberta remota (down) `src/core/sync.py::sync_remote`.
A sincronização reconcilia o board inteiro a cada execução, sem corte por data
da última atualização (RN-01) e sem acionamento diário. Cobre:

- CT-01  — criação detectada em execução única.
- CT-01b — criação detectada sem depender de corte temporal (snapshot "quente").
- CT-02  — modificação de propriedade detectada em execução única.
- CT-03  — poda por ausência em execução única.
- CT-03b — poda só atinge itens com identidade definida no board (RN-03).
- CT-04  — leitura parcial por limite não poda e preserva o estado (RN-02).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue, PenaltyException, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot
from src.core.sync import sync_remote


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


class FakePort(BoardPort):
    """Adapter fake: list_issues devolve uma lista; opcionalmente levanta
    PenaltyException para simular limite de requisições (leitura atômica)."""

    def __init__(self, listed=None, raise_on_list=None):
        self._listed = listed or []
        self._raise_on_list = raise_on_list

    def connect(self, config): pass
    def sync_boards(self, boards): pass

    def list_issues(self, board_id):
        if self._raise_on_list is not None:
            raise self._raise_on_list
        return list(self._listed)

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
        out.append(item)
        queue.remove(item.uuid)
    return out


def _events(items):
    return [(i.event, i.id) for i in items]


# ── CT-01: criação detectada em execução única ────────────────────────────────

def test_ct01_create_detected_single_run():
    """Snapshot vazio + board com issue nova -> um create-down fullsync."""
    board = Board(FakePort(listed=[
        Issue(id="50", title="Nova", body="", column="backlog",
              updated_at="2026-09-24T12:00:00Z"),
    ]))
    _seed_snapshot("b", [])
    q = ChangeQueue()

    sync_remote("b", board, q)

    items = _drain(q)
    assert _events(items) == [(SyncEvent.CREATE_DOWN.value, "50")]
    # Create precisa de fullsync (monta o body com deps, sem baseline local).
    assert items[0].fullsync is True


# ── CT-01b: criação sem depender de corte temporal ────────────────────────────

def test_ct01b_create_detected_even_with_hot_snapshot_and_old_updated_at():
    """Issue nova é detectada mesmo com updated_at anterior ao do snapshot
    "quente" — prova a eliminação do corte incremental (RN-01)."""
    board = Board(FakePort(listed=[
        # #40 inalterada; #51 nova com updated_at ANTERIOR a #40 (simula item
        # que não cruzaria o antigo corte por data).
        Issue(id="40", title="Antiga", body="", column="backlog",
              updated_at="2026-09-20T00:00:00Z"),
        Issue(id="51", title="Nova atrasada", body="", column="backlog",
              updated_at="2026-09-01T00:00:00Z"),
    ]))
    _seed_snapshot("b", [
        {"id": "40", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-20T00:00:00Z"},
    ])
    q = ChangeQueue()

    sync_remote("b", board, q)

    items = _drain(q)
    # #51 criada apesar do updated_at antigo; #40 sem divergência não gera evento.
    assert _events(items) == [(SyncEvent.CREATE_DOWN.value, "51")]


# ── CT-02: modificação de propriedade em execução única ───────────────────────

def test_ct02_modification_detected_single_run():
    """Issue com coluna divergente -> change-down na execução única."""
    board = Board(FakePort(listed=[
        Issue(id="60", title="", body="", column="desenvolvimento",
              updated_at="2026-09-22T00:00:00Z"),
    ]))
    _seed_snapshot("b", [
        {"id": "60", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
    ])
    q = ChangeQueue()

    sync_remote("b", board, q)

    items = _drain(q)
    assert _events(items) == [(SyncEvent.CHANGE_DOWN.value, "60")]


# ── CT-03: poda por ausência em execução única ────────────────────────────────

def test_ct03_prune_absent_single_run():
    """Issue com id no snapshot e ausente do fetch -> delete-down; presente fica."""
    board = Board(FakePort(listed=[
        Issue(id="70", title="", body="", column="backlog",
              updated_at="2026-09-22T00:00:00Z"),
    ]))
    _seed_snapshot("b", [
        {"id": "69", "column": "encerrado", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
        {"id": "70", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
    ])
    q = ChangeQueue()

    sync_remote("b", board, q)

    assert _events(_drain(q)) == [(SyncEvent.DELETE_DOWN.value, "69")]


# ── CT-03b: poda só atinge itens com identidade definida (RN-03) ──────────────

def test_ct03b_prune_only_items_with_board_identity():
    """Item local sem id (id=None) nunca é podado; só o id definido ausente."""
    board = Board(FakePort(listed=[
        # Fetch completo e NÃO-vazio, mas sem #71 nem o item sem id.
        Issue(id="99", title="", body="", column="backlog",
              updated_at="2026-09-22T00:00:00Z"),
    ]))
    _seed_snapshot("b", [
        {"id": "71", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
        {"id": None, "column": "backlog", "status": "create-up",
         "body_path": ".pipe/boards/b/backlog/nova-body.md"},
    ])
    q = ChangeQueue()

    sync_remote("b", board, q)

    events = _events(_drain(q))
    # #99 é novo no board -> create-down; #71 ausente com id -> delete-down;
    # o item id=None NUNCA gera delete-down.
    assert (SyncEvent.DELETE_DOWN.value, "71") in events
    assert (SyncEvent.CREATE_DOWN.value, "99") in events
    assert all(e != SyncEvent.DELETE_DOWN.value or i == "71"
               for e, i in events), "id=None não pode ser podado"


# ── CT-04: leitura parcial por limite não poda e preserva o estado (RN-02) ────

def test_ct04_penalty_during_read_does_not_prune_and_preserves_snapshot():
    """list_issues levanta PenaltyException -> propaga, nenhum evento, snapshot
    intacto. A leitura atômica nunca é interpretada como board vazio."""
    board = Board(FakePort(raise_on_list=PenaltyException(30)))
    _seed_snapshot("b", [
        {"id": "69", "column": "encerrado", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
        {"id": "70", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
    ])
    before = Snapshot("b").path.read_text(encoding="utf-8")
    q = ChangeQueue()

    with pytest.raises(PenaltyException):
        sync_remote("b", board, q)

    # Nenhum evento (nem delete-down) enfileirado.
    assert _drain(q) == []
    # Snapshot persistido permanece idêntico (nenhuma issue marcada/alterada).
    after = Snapshot("b").path.read_text(encoding="utf-8")
    assert after == before


# ── CT-05: adiamento de participação não resolvida corta reenfileiramento ─────

def test_ct05_unresolved_pending_not_due_skips_create_down():
    """Issue ausente do snapshot COM pendência de participação ainda não vencida
    não é reenfileirada (throttle); ao vencer o prazo, volta a enfileirar.

    Sem este corte, uma presença `unresolved` (nunca persistida) seria
    redescoberta e re-despachada a cada ciclo — loop sem throttle.
    """
    from datetime import datetime, timedelta, timezone
    from src.core import participation_reconcile as PR
    from src.core.participation import Classification, UNRESOLVED

    board = Board(FakePort(listed=[
        Issue(id="88", title="Nao resolvida", body="", column="backlog",
              updated_at="2026-09-24T12:00:00Z"),
    ]))
    _seed_snapshot("b", [])

    # Pendência registrada com prazo no futuro: não vencida.
    PR.defer_pending("b", "88", Classification(UNRESOLVED, {}), 600)
    entry = PR.pending_entry("b", "88")
    assert PR.is_due(entry) is False

    q = ChangeQueue()
    sync_remote("b", board, q)
    assert _drain(q) == []  # throttle: nada enfileirado enquanto adiada

    # Prazo vencido: volta a enfileirar create-down.
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    entry["next_attempt_at"] = past.strftime("%Y-%m-%dT%H:%M:%SZ")
    PR._save_pending({PR._pending_key("b", "88"): entry})

    q2 = ChangeQueue()
    sync_remote("b", board, q2)
    assert _events(_drain(q2)) == [(SyncEvent.CREATE_DOWN.value, "88")]
