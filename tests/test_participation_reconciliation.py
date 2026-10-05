"""Grupo B — reconciliação (imediata e tardia), falha e retentativa (#310).

Cobre CT-01, CT-01b, CT-02, CT-03, CT-05, CT-15, CT-16, CT-17-retentativa e
CT-02-generico. Usa um `FakePort` offline: `list_participations` é controlável
(inclusive levantando exceção para simular falha transitória) e
`remove_from_board` é espião que registra chamadas.
"""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.log import log
from src.core.board import Board, BoardPort, Issue
from src.core.participation import Participation, ParticipationQueryError, PROPAGATED, UNRESOLVED
from src.core import participation_reconcile as PR


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log._log_dir = Path("logs")
    log._setup()
    yield


def _log_text():
    path = Path("logs") / f"{date.today().strftime('%Y-%m-%d')}.json"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _cfg():
    cols = {"doing": {"name": "Doing"}}
    return {
        "boards": {
            "platform": "github",
            "epicos": {"name": "Epicos", "columns": cols},
            "historias": {"name": "Historias", "columns": cols},
            "tarefas": {"name": "Tarefas", "columns": cols},
            # par sintético (CT-02-generico): nunca referenciado no código.
            "squads": {"name": "Squads", "columns": cols},
            "iniciativas": {"name": "Iniciativas", "columns": cols},
        }
    }


class FakePort(BoardPort):
    """Porta offline: list_participations controlável, remove_from_board espião.

    - `participations`: dict issue_id -> lista de Participation retornada.
    - `raise_on_list`: se truthy, list_participations levanta esse erro.
    - `raise_on_remove`: se truthy, remove_from_board levanta esse erro.
    - `removed`: lista espiã de (board_id, issue_id) removidos.
    - `relations_touched`: espião — DEVE permanecer vazio (RN-03).
    """

    def __init__(self, participations=None, raise_on_list=None, raise_on_remove=None):
        self._parts = {str(k): v for k, v in (participations or {}).items()}
        self.raise_on_list = raise_on_list
        self.raise_on_remove = raise_on_remove
        self.removed = []
        self.relations_touched = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def get_issue(self, board_id, issue_id, fullsync=False): return None
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass

    def list_participations(self, issue_id):
        if self.raise_on_list:
            raise self.raise_on_list
        return list(self._parts.get(str(issue_id), []))

    def remove_from_board(self, board_id, issue_id):
        if self.raise_on_remove:
            raise self.raise_on_remove
        self.removed.append((board_id, str(issue_id)))

    # Relações pai/filho — se chamadas, registram violação (não devem ser tocadas).
    def set_parent(self, board_id, issue_id, parent_id, known_current=None):
        self.relations_touched.append(("set_parent", board_id, str(issue_id)))
    def set_children(self, board_id, issue_id, children_ids, known_current=None):
        self.relations_touched.append(("set_children", board_id, str(issue_id)))


# ── CT-01 — reconciliação imediata pós-vínculo preserva a hierarquia ──────────

def test_ct01_immediate_reconcile_removes_propagated_preserves_hierarchy():
    # Filha do board 'tarefas' propagada para 'historias' (board do pai).
    known = [
        Participation("Ita", "tarefas", "Pta", "doing"),       # origem conhecida
        Participation("Ihi", "historias", "Phi", ""),           # propagada (sem col)
    ]
    port = FakePort(participations={"500": known})
    board = Board(port)
    PR.reconcile_after_link(board, "500", "historias", _cfg(), labels=[])
    assert ("historias", "500") in port.removed
    assert port.relations_touched == []  # RN-03: hierarquia intacta
    text = _log_text()
    assert "participation_reconciled" in text


# ── CT-01b — múltiplos filhos: cada reconciliação preserva as demais relações ─

def test_ct01b_multiple_children_each_reconcile_isolated():
    cfg = _cfg()
    # Três filhos; cada um conhecido em seu board de origem + propagado em epicos.
    def known_for(origin):
        return [
            Participation("Io", origin, "Po", "doing"),
            Participation("Ie", "epicos", "Pe", ""),
        ]
    port = FakePort(participations={
        "601": known_for("historias"),
        "602": known_for("tarefas"),
        "603": known_for("historias"),
    })
    board = Board(port)
    for child in ("601", "602", "603"):
        PR.reconcile_after_link(board, child, "epicos", cfg, labels=[])
    assert ("epicos", "601") in port.removed
    assert ("epicos", "602") in port.removed
    assert ("epicos", "603") in port.removed
    assert port.relations_touched == []


# ── CT-02 — reconciliação tardia na descoberta remota (sem coluna) ────────────

def test_ct02_late_reconcile_remote_presence_no_column():
    known = [
        Participation("Ihi", "historias", "Phi", "doing"),  # origem
        Participation("Iep", "epicos", "Pep", ""),           # propagada sem col
    ]
    port = FakePort(participations={"700": known})
    board = Board(port)
    result = PR.reconcile_remote_presence(
        board, "700", "epicos", _cfg(), column="",
        known_participations=known, has_cross_board_parent=True,
    )
    assert result.intent == PROPAGATED
    assert ("epicos", "700") in port.removed
    text = _log_text()
    assert "participation_reconciled" in text


# ── CT-03 — coluna preenchida não isenta (mesmo resultado de CT-02) ───────────

def test_ct03_late_reconcile_with_filled_column_same_as_ct02():
    known = [
        Participation("Ihi", "historias", "Phi", "doing"),
        Participation("Iep", "epicos", "Pep", "Doing"),   # propagada COM coluna
    ]
    port = FakePort(participations={"701": known})
    board = Board(port)
    result = PR.reconcile_remote_presence(
        board, "701", "epicos", _cfg(), column="Doing",
        known_participations=known, has_cross_board_parent=True,
    )
    assert result.intent == PROPAGATED
    assert ("epicos", "701") in port.removed


# ── CT-05 — falha transitória de consulta ⇒ não resolvida, adiada ─────────────

def test_ct05_query_failure_is_unresolved_deferred_no_removal():
    port = FakePort(raise_on_list=ParticipationQueryError("boom"))
    board = Board(port)
    result = PR.reconcile_remote_presence(board, "800", "epicos", _cfg())
    assert result.intent == UNRESOLVED
    assert port.removed == []            # sem remoção
    entry = PR.pending_entry("epicos", "800")
    assert entry is not None
    assert entry["next_attempt_at"]      # adiada
    assert entry["attempts"] == 1        # não consome tentativa que descarta
    # Sem arquivos locais de issue criados.
    assert not list(Path(".pipe/boards").glob("**/*-body.md")) if Path(".pipe/boards").exists() else True
    text = _log_text()
    assert "participation_reconcile_failed" in text


# ── CT-15 — falha na remoção propaga erro tipado e preserva hierarquia ────────

def test_ct15_remove_failure_propagates_and_preserves_hierarchy():
    known = [
        Participation("Ita", "tarefas", "Pta", "doing"),
        Participation("Ihi", "historias", "Phi", ""),
    ]
    port = FakePort(participations={"900": known},
                    raise_on_remove=RuntimeError("remove failed"))
    board = Board(port)
    with pytest.raises(RuntimeError):
        PR.reconcile_after_link(board, "900", "historias", _cfg(), labels=[])
    assert port.relations_touched == []   # hierarquia intacta
    text = _log_text()
    assert "participation_reconcile_failed" in text


# ── CT-16 — não resolvida adiada sem consumir tentativa; outros itens seguem ──

def test_ct16_unresolved_defer_does_not_block_other_items():
    # Item não resolvido (falha de consulta) para issue A.
    port_fail = FakePort(raise_on_list=ParticipationQueryError("x"))
    board_fail = Board(port_fail)
    PR.reconcile_remote_presence(board_fail, "A1", "epicos", _cfg())
    entry = PR.pending_entry("epicos", "A1")
    assert entry["attempts"] == 1

    # Outro item (issue B) é processado normalmente no mesmo "ciclo".
    known = [
        Participation("Ih", "historias", "Ph", "doing"),
        Participation("Ie", "epicos", "Pe", ""),
    ]
    port_ok = FakePort(participations={"B1": known})
    board_ok = Board(port_ok)
    result = PR.reconcile_remote_presence(
        board_ok, "B1", "epicos", _cfg(),
        known_participations=known, has_cross_board_parent=True,
    )
    assert result.intent == PROPAGATED
    assert ("epicos", "B1") in port_ok.removed
    # A pendência de A permanece intacta (não foi afetada por B).
    assert PR.pending_entry("epicos", "A1") is not None


# ── CT-17-retentativa — reavaliação após vencer o prazo ───────────────────────

def test_ct17_defer_skipped_until_due_then_eligible():
    cfg = _cfg()
    port = FakePort(raise_on_list=ParticipationQueryError("x"))
    PR.reconcile_remote_presence(Board(port), "C1", "epicos", cfg)
    entry = PR.pending_entry("epicos", "C1")

    # Prazo no futuro: não vencido.
    future = datetime.now(timezone.utc) + timedelta(seconds=600)
    entry["next_attempt_at"] = future.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert PR.is_due(entry) is False

    # Prazo vencido: elegível.
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    entry["next_attempt_at"] = past.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert PR.is_due(entry) is True


# ── CT-02-generico — mesmo mecanismo em qualquer par (inclui par sintético) ───

@pytest.mark.parametrize("origin_board,parent_board", [
    ("historias", "epicos"),
    ("tarefas", "historias"),
    ("iniciativas", "squads"),  # par sintético nunca visto no código
])
def test_ct02_generico_any_hierarchical_pair(origin_board, parent_board):
    known = [
        Participation("Io", origin_board, "Po", "doing"),
        Participation("Ip", parent_board, "Pp", ""),
    ]
    port = FakePort(participations={"1000": known})
    board = Board(port)
    result = PR.reconcile_remote_presence(
        board, "1000", parent_board, _cfg(),
        known_participations=known, has_cross_board_parent=True,
    )
    assert result.intent == PROPAGATED
    assert (parent_board, "1000") in port.removed
    assert port.relations_touched == []
