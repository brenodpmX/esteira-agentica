"""CT-OBS-01 / CT-OBS-02 — Observabilidade padronizada do sync (RF-08).

Contrato mínimo de log de sincronização:

    sincronizacao board=<board_id> criados=<n> atualizados=<n> removidos=<n> resultado=<ok|limite|erro>

O log não contém qualificador de modo (full/completo/completa/reduzido/
incremental) nem vaza corpo de issue, caminho de arquivo protegido ou credencial.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import sync as sync_module
from src.core.board import Board, BoardPort, Issue, PenaltyException, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot
from src.core.sync import sync_remote


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


class FakePort(BoardPort):
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


def _capture_info(monkeypatch):
    records = []
    original = sync_module.log.info

    def fake_info(component, msg, *args, **extra):
        records.append((component, msg, extra))

    monkeypatch.setattr(sync_module.log, "info", fake_info)
    return records


_FORBIDDEN_TOKENS = ("full", "completo", "completa", "reduzido",
                     "reduzida", "incremental")


def _sync_lines(records):
    return [(c, m, e) for (c, m, e) in records
            if isinstance(m, str) and m.startswith("sincronizacao board=")]


# ── CT-OBS-01: sucesso emite log no contrato mínimo ───────────────────────────

def test_ct_obs01_success_log_contract(monkeypatch):
    """1 criado, 1 atualizado, 1 removido -> um log parseável com resultado=ok."""
    board = Board(FakePort(listed=[
        # #50 nova -> criado
        Issue(id="50", title="", body="", column="backlog",
              updated_at="2026-09-24T12:00:00Z"),
        # #60 divergente (coluna) -> atualizado
        Issue(id="60", title="", body="", column="desenvolvimento",
              updated_at="2026-09-22T00:00:00Z"),
        # #70 ausente -> removido (não está no fetch)
    ]))
    _seed_snapshot("b", [
        {"id": "60", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
        {"id": "70", "column": "encerrado", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
    ])
    records = _capture_info(monkeypatch)
    q = ChangeQueue()

    sync_remote("b", board, q)

    lines = _sync_lines(records)
    assert len(lines) == 1, f"esperado exatamente 1 log de sync, veio {lines}"
    _, msg, _ = lines[0]

    m = re.search(
        r"sincronizacao board=(\S+) criados=(\d+) atualizados=(\d+) "
        r"removidos=(\d+) resultado=(\w+)", msg)
    assert m, f"log fora do contrato mínimo: {msg!r}"
    assert m.group(1) == "b"
    assert m.group(2) == "1"   # criados
    assert m.group(3) == "1"   # atualizados
    assert m.group(4) == "1"   # removidos
    assert m.group(5) == "ok"

    # Não contém qualificador de modo nem vaza conteúdo protegido.
    low = msg.lower()
    for token in _FORBIDDEN_TOKENS:
        assert token not in low, f"qualificador de modo '{token}' no log: {msg!r}"
    assert "snapshot.json" not in msg
    assert "body" not in low


# ── CT-OBS-02: limite emite resultado=limite e não poda ───────────────────────

def test_ct_obs02_penalty_log_limite_and_no_prune(monkeypatch):
    """list_issues levanta PenaltyException -> log resultado=limite, nenhum
    delete-down enfileirado."""
    board = Board(FakePort(raise_on_list=PenaltyException(30)))
    _seed_snapshot("b", [
        {"id": "69", "column": "encerrado", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
        {"id": "70", "column": "backlog", "status": "ok",
         "updated_at": "2026-09-22T00:00:00Z"},
    ])
    records = _capture_info(monkeypatch)
    q = ChangeQueue()

    with pytest.raises(PenaltyException):
        sync_remote("b", board, q)

    lines = _sync_lines(records)
    assert len(lines) == 1
    _, msg, _ = lines[0]
    m = re.search(r"sincronizacao board=(\S+) .* resultado=(\w+)", msg)
    assert m and m.group(1) == "b" and m.group(2) == "limite"

    # Nenhum evento (nem delete-down) foi enfileirado.
    assert q.getNext() is None
