"""CT-14 — Ordem do full sync e snapshot efetivo (#305 / RF-17).

Exercita o código REAL de `src.__main__.board_startup_sync`, com `FakePort` e
`sync_remote` neutralizado (sem rede). Verifica:

- CT-14a: a reconciliação da estrutura remota ocorre ANTES de gravar o snapshot;
- CT-14b: o snapshot reflete a estrutura efetiva (inclui origens retidas) e os
  diretórios locais dessas origens são preservados;
- CT-14c: uma falha genérica de reconciliação não sobrescreve o snapshot anterior.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.__main__ as m
from src.core.board import Board, BoardPort, Issue
from src.core.snapshot import Snapshot


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Neutraliza a descoberta remota (sync_remote) — sem rede.
    monkeypatch.setattr(m, "sync_remote", lambda *a, **k: None)
    yield


class SpyPort(BoardPort):
    """Port espião: registra a ordem das operações estruturais e de snapshot.

    `published[board]` = opções remotas; `issues[board]` = dict id->Issue.
    """

    def __init__(self, events, published=None, issues=None, prepare_raises=None):
        self.events = events
        self.published = {b: list(c) for b, c in (published or {}).items()}
        self.issues = {b: {str(i.id): i for i in lst}
                       for b, lst in (issues or {}).items()}
        self.prepare_raises = prepare_raises

    def connect(self, config): pass
    def sync_boards(self, boards): pass

    def prepare_structure(self, boards):
        self.events.append("prepare")
        if self.prepare_raises is not None:
            raise self.prepare_raises
        for b in boards:
            self.published.setdefault(b["id"], [])
            for col in b["columns"]:
                if col not in self.published[b["id"]]:
                    self.published[b["id"]].append(col)

    def remote_columns(self, board_id):
        return list(self.published.get(board_id, []))

    def contract_column(self, board_id, final_columns):
        self.events.append(("contract", board_id, list(final_columns)))
        self.published[board_id] = [
            c for c in self.published.get(board_id, []) if c in final_columns
        ]

    def list_issues(self, board_id):
        return list(self.issues.get(board_id, {}).values())

    def move_issue(self, board_id, issue_id, column, from_column=None):
        iss = self.issues.get(board_id, {}).get(str(issue_id))
        if iss is not None:
            iss.column = column

    def get_issue(self, board_id, issue_id, fullsync=False):
        return self.issues.get(board_id, {}).get(str(issue_id))
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
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
    def remove_from_board(self, board_id, issue_id): pass


def _config():
    return {"boards": {
        "platform": "github",
        "entrega": {"name": "Entrega", "columns": {
            "backlog": {"name": "Backlog"},
            "done": {"name": "Done"},
        }},
    }}


def _issue(id, column):
    return Issue(id=str(id), title="t", body="b", column=column)


# ── CT-14a — Reconciliar o remoto ANTES de gravar o snapshot ──────────────────

def test_ct14a_reconcile_before_snapshot(monkeypatch):
    events = []
    # 'revisao' publicada e vazia -> será contraída na reconciliação.
    port = SpyPort(events, published={"entrega": ["backlog", "revisao", "done"]},
                   issues={"entrega": []})
    m.board = Board(port)

    original_save = Snapshot.save

    def spy_save(self):
        events.append("snapshot_save")
        return original_save(self)

    monkeypatch.setattr(Snapshot, "save", spy_save)

    m.board_startup_sync(_config())

    assert "prepare" in events and "snapshot_save" in events
    assert events.index("prepare") < events.index("snapshot_save")
    # a contração (reconciliação) também precede a gravação do snapshot
    contract_idx = next(i for i, e in enumerate(events)
                        if isinstance(e, tuple) and e[0] == "contract")
    assert contract_idx < events.index("snapshot_save")


# ── CT-14b — Snapshot reflete a estrutura efetiva + preserva diretórios ───────

def test_ct14b_snapshot_includes_retained_source_and_preserves_dir(monkeypatch):
    events = []
    # 'revisao' ocupada e sem destino -> retida (blocked), permanece publicada.
    port = SpyPort(events, published={"entrega": ["backlog", "revisao", "done"]},
                   issues={"entrega": [_issue(10, "revisao")]})
    m.board = Board(port)

    # Diretório local da origem retida com um arquivo.
    retained_dir = Path(".pipe/boards/entrega/revisao")
    retained_dir.mkdir(parents=True, exist_ok=True)
    (retained_dir / "10-x-body.md").write_text("x", encoding="utf-8")

    m.board_startup_sync(_config())

    snap = Snapshot("entrega").load()
    # snapshot inclui a origem retida (estrutura efetiva), não só a config.
    assert "revisao" in snap.board
    assert "backlog" in snap.board and "done" in snap.board
    # diretório local da origem retida preservado.
    assert retained_dir.exists()
    assert (retained_dir / "10-x-body.md").exists()


# ── CT-14c — Falha de reconciliação não sobrescreve snapshot anterior ─────────

def test_ct14c_reconcile_failure_preserves_prior_snapshot(monkeypatch):
    events = []
    # Semeia snapshot anterior conhecido.
    snap = Snapshot("entrega").load()
    snap.board = {"backlog": "Backlog", "antiga": "Antiga", "done": "Done"}
    snap.save()
    prior = Snapshot("entrega").load().board

    # Preparação levanta exceção genérica (não PenaltyException).
    port = SpyPort(events, published={"entrega": ["backlog", "done"]},
                   prepare_raises=RuntimeError("falha reconciliacao"))
    m.board = Board(port)

    with pytest.raises(RuntimeError):
        m.board_startup_sync(_config())

    # snapshot anterior intacto (não sobrescrito).
    after = Snapshot("entrega").load().board
    assert after == prior
