"""Testes da contingência de suspensão de vínculos pai/filho entre boards.

Cobrem o gate `safety.cross_board_parent_links: suspended` em
`Board.apply_commands` (via `_is_cross_board_link_blocked`) e sua integração
com `_apply_change_up`/`_find_snapshot_issue`.

Cenários (issue #256 / story #241 / CT01–CT11 dos casos de teste):
- parent novo bloqueado entre boards distintos quando suspended;
- parent novo aplicado no mesmo board;
- parent novo aplicado quando enabled/ausente;
- remoção de parent nunca bloqueada;
- children como SET: bloqueio parcial, bloqueio total, remoção sempre aplicada;
- ausência de resolve_board_fn preserva comportamento atual;
- alvo não rastreado (None) não bloqueado;
- releitura do pipe.yml sem cache em memória;
- integração com _apply_change_up + _find_snapshot_issue.
"""

import sys
from pathlib import Path

import pytest

# Permite importar o pacote src quando rodado de qualquer lugar.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue
from src.core.commands import IssueCommands


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola .pipe/ e o pipe.yml em um diretório temporário por teste."""
    monkeypatch.chdir(tmp_path)
    yield


def _write_pipe(value=None):
    """Escreve um pipe.yml mínimo no cwd, opcionalmente com a chave de safety.

    `value=None` omite a seção safety inteiramente (chave ausente).
    """
    lines = ["sleep: 60\n"]
    if value is not None:
        lines.append("safety:\n")
        lines.append(f"  cross_board_parent_links: {value}\n")
    Path("pipe.yml").write_text("".join(lines), encoding="utf-8")


# ── Fake adapter que registra chamadas em vez de bater na rede ────────────────

class FakePort(BoardPort):
    def __init__(self):
        self.calls = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def list_issues_since(self, board_id, since): return []
    def get_issue(self, board_id, issue_id, fullsync=False):
        return Issue(id=issue_id, title="", body="", column="")
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id):
        self.calls.append(("close", issue_id))
    def reopen_issue(self, board_id, issue_id):
        self.calls.append(("reopen", issue_id))
    def set_labels(self, board_id, issue_id, labels):
        self.calls.append(("set_labels", issue_id, sorted(labels)))
    def add_label(self, board_id, issue_id, label): pass
    def remove_label(self, board_id, issue_id, label): pass
    def set_parent(self, board_id, issue_id, parent_id, known_current=None):
        self.calls.append(("set_parent", issue_id, parent_id))
    def set_children(self, board_id, issue_id, children_ids, known_current=None):
        self.calls.append(("set_children", issue_id, sorted(children_ids)))
    def set_blocked_by(self, board_id, issue_id, blocker_ids, known_current=None):
        self.calls.append(("set_blocked_by", issue_id, sorted(blocker_ids)))
    def set_blocks(self, board_id, issue_id, blocked_ids, known_current=None):
        self.calls.append(("set_blocks", issue_id, sorted(blocked_ids)))
    def archive_issue(self, board_id, issue_id):
        self.calls.append(("archive", issue_id))
    def unarchive_issue(self, board_id, issue_id):
        self.calls.append(("unarchive", issue_id))


def _ops(port):
    return [c[0] for c in port.calls]


def _base_known(**over):
    known = {
        "labels": [], "parent": None, "children": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
    }
    known.update(over)
    return known


# ── Helper para capturar logs cross_board_link_blocked ────────────────────────

@pytest.fixture
def blocked_events(monkeypatch):
    """Captura os warnings com event_type=cross_board_link_blocked."""
    from src.core import board as board_mod
    events = []
    orig_warning = board_mod.log.warning

    def _capture(module, msg, *args, **extra):
        if extra.get("event_type") == "cross_board_link_blocked":
            events.append(extra)
        return orig_warning(module, msg, *args, **extra)

    monkeypatch.setattr(board_mod.log, "warning", _capture)
    return events


# ── CT01: parent novo bloqueado (suspended + board distinto) ──────────────────

def test_parent_new_blocked_when_suspended_cross_board(blocked_events):
    _write_pipe("suspended")
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(parent="10")
    known = _base_known()

    deltas = board.apply_commands(
        "board-a", "1", cmds, known=known,
        resolve_board_fn=lambda tid: "board-b",
    )

    assert "set_parent" not in _ops(port)
    assert len(blocked_events) == 1
    ev = blocked_events[0]
    assert ev["relation"] == "parent"
    assert ev["target_id"] == "10"
    assert ev["board_id"] == "board-a"
    assert ev["issue_id"] == "1"
    assert "10" not in deltas["parent"]["added"]


# ── CT02: parent novo aplicado (mesmo board) ──────────────────────────────────

def test_parent_new_applied_when_same_board(blocked_events):
    _write_pipe("suspended")
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(parent="10")
    known = _base_known()

    deltas = board.apply_commands(
        "board-a", "1", cmds, known=known,
        resolve_board_fn=lambda tid: "board-a",
    )

    assert ("set_parent", "1", "10") in port.calls
    assert blocked_events == []
    assert "10" in deltas["parent"]["added"]


# ── CT03: parent novo aplicado quando enabled / chave ausente ─────────────────

@pytest.mark.parametrize("value", ["enabled", None])
def test_parent_new_applied_when_not_suspended(blocked_events, value):
    _write_pipe(value)
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(parent="10")
    known = _base_known()

    board.apply_commands(
        "board-a", "1", cmds, known=known,
        resolve_board_fn=lambda tid: "board-b",
    )

    assert ("set_parent", "1", "10") in port.calls
    assert blocked_events == []


# ── CT04: remoção de parent nunca é bloqueada ─────────────────────────────────

def test_parent_removal_never_blocked(blocked_events):
    _write_pipe("suspended")
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands()  # parent ausente -> remoção
    known = _base_known(parent="10")

    deltas = board.apply_commands(
        "board-a", "1", cmds, known=known,
        resolve_board_fn=lambda tid: "board-b",
    )

    assert ("set_parent", "1", None) in port.calls
    assert blocked_events == []
    assert "10" in deltas["parent"]["removed"]


# ── CT05: children — bloqueio parcial (um distinto, um mesmo board) ───────────

def test_children_partial_block(blocked_events):
    _write_pipe("suspended")
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(children=["10", "20"])
    known = _base_known()

    # 10 em board distinto (bloqueado), 20 no mesmo board (aplicado).
    def resolve(tid):
        return "board-b" if tid == "10" else "board-a"

    deltas = board.apply_commands(
        "board-a", "1", cmds, known=known, resolve_board_fn=resolve,
    )

    set_children_calls = [c for c in port.calls if c[0] == "set_children"]
    assert len(set_children_calls) == 1
    assert set_children_calls[0][2] == ["20"]  # sorted, só o mesmo board
    assert len(blocked_events) == 1
    assert blocked_events[0]["target_id"] == "10"
    assert blocked_events[0]["relation"] == "children"
    assert set(deltas["children"]["added"]) == {"20"}


# ── CT06: children — todos bloqueados e sem diferença: não chama set_children ─

def test_children_all_blocked_skips_set(blocked_events):
    _write_pipe("suspended")
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(children=["10"])
    known = _base_known()

    deltas = board.apply_commands(
        "board-a", "1", cmds, known=known,
        resolve_board_fn=lambda tid: "board-b",
    )

    assert "set_children" not in _ops(port)
    assert len(blocked_events) == 1
    assert blocked_events[0]["target_id"] == "10"
    assert "10" not in deltas["children"]["added"]


# ── CT07: children — remoção sempre aplicada ──────────────────────────────────

def test_children_removal_always_applied(blocked_events):
    _write_pipe("suspended")
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands()  # children vazio -> remove o conhecido
    known = _base_known(children=["10"])

    deltas = board.apply_commands(
        "board-a", "1", cmds, known=known,
        resolve_board_fn=lambda tid: "board-b",
    )

    set_children_calls = [c for c in port.calls if c[0] == "set_children"]
    assert len(set_children_calls) == 1
    assert set_children_calls[0][2] == []  # nada desejado
    assert blocked_events == []
    assert "10" in deltas["children"]["removed"]


# ── CT08: ausência de resolve_board_fn preserva comportamento atual ───────────

def test_no_resolve_fn_preserves_behavior(blocked_events):
    _write_pipe("suspended")
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(parent="10", children=["20"])
    known = _base_known()

    # Sem resolve_board_fn: gate ignorado, tudo aplicado.
    board.apply_commands("board-a", "1", cmds, known=known)

    assert ("set_parent", "1", "10") in port.calls
    assert ("set_children", "1", ["20"]) in port.calls
    assert blocked_events == []


# ── CT09: alvo não rastreado (None) não é bloqueado ───────────────────────────

def test_untracked_target_not_blocked(blocked_events):
    _write_pipe("suspended")
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(parent="10")
    known = _base_known()

    board.apply_commands(
        "board-a", "1", cmds, known=known,
        resolve_board_fn=lambda tid: None,
    )

    assert ("set_parent", "1", "10") in port.calls
    assert blocked_events == []


# ── CT10: releitura do pipe.yml sem cache em memória ──────────────────────────

def test_config_reread_no_memory_cache(blocked_events):
    _write_pipe("enabled")
    port = FakePort()
    board = Board(port)
    resolve = lambda tid: "board-b"

    # 1ª chamada: enabled -> aplica.
    cmds1 = IssueCommands(parent="10")
    board.apply_commands("board-a", "1", cmds1, known=_base_known(),
                         resolve_board_fn=resolve)
    assert ("set_parent", "1", "10") in port.calls
    assert blocked_events == []

    # Altera o pipe.yml em disco, sem recriar objetos.
    _write_pipe("suspended")

    # 2ª chamada: suspended -> bloqueia.
    cmds2 = IssueCommands(parent="20")
    board.apply_commands("board-a", "2", cmds2, known=_base_known(),
                         resolve_board_fn=resolve)
    assert ("set_parent", "2", "20") not in port.calls
    assert len(blocked_events) == 1
    assert blocked_events[0]["target_id"] == "20"


# ── CT11: integração com _apply_change_up + _find_snapshot_issue ──────────────

def test_integration_apply_change_up_blocks_cross_board(blocked_events):
    from src.core import sync
    from src.core.board import ChangeItem, SyncEvent
    from src.core.snapshot import Snapshot

    _write_pipe("suspended")

    # Snapshot de board-a (issue 1, coluna dev) e board-b (issue 99).
    snap_a = Snapshot("board-a")
    snap_a.issues = [{
        "id": "1", "title": "t", "column": "dev",
        "parent": None, "children": [], "labels": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
    }]
    snap_a.save()

    snap_b = Snapshot("board-b")
    snap_b.issues = [{
        "id": "99", "title": "other", "column": "todo",
        "parent": None, "children": [], "labels": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
    }]
    snap_b.save()

    # Arquivo -body.md da issue 1 em board-a/dev com /parent #99 (board-b).
    board_dir = sync.BOARDS_DIR / "board-a" / "dev"
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "1-issue-body.md").write_text(
        "# t\n\nCorpo.\n\n@---\n/parent #99\n", encoding="utf-8"
    )

    port = FakePort()
    board = Board(port)
    item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="board-a")

    sync._apply_change_up("board-a", item, board)

    # Vínculo cross-board bloqueado (mesmo efeito de CT01, via fluxo real).
    assert "set_parent" not in _ops(port)
    assert len(blocked_events) == 1
    assert blocked_events[0]["target_id"] == "99"
    assert blocked_events[0]["relation"] == "parent"
