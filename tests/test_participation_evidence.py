"""Grupo E — observabilidade e evidência de execução (#310).

Cobre CT-14 (eventos de reconciliação sucesso/falha com campos mínimos e sem
segredos), CT-21 (rollout_evidence no startup, campo ausente sinalizado),
CT-22 (remoção externa sem inferir autoria) e CT-23 (ausência de segredos).
"""

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.log import log
from src.core.board import Board, BoardPort
from src.core.participation import Participation, ParticipationQueryError
from src.core import participation as P
from src.core import participation_reconcile as PR

SECRET_BODY = "CORPO_SECRETO_456"
FAKE_TOKEN = "ghp_tokenfalso_zzz999"


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log._log_dir = Path("logs")
    log._setup()
    yield


def _log_lines():
    path = Path("logs") / f"{date.today().strftime('%Y-%m-%d')}.json"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _event_lines(event):
    return [ln for ln in _log_lines() if event in ln]


def _cfg():
    cols = {"doing": {"name": "Doing"}}
    return {
        "boards": {
            "platform": "github",
            "epicos": {"name": "Epicos", "columns": cols},
            "historias": {"name": "Historias", "columns": cols},
        }
    }


class FakePort(BoardPort):
    def __init__(self, participations=None, raise_on_remove=None):
        self._parts = {str(k): v for k, v in (participations or {}).items()}
        self.raise_on_remove = raise_on_remove
        self.removed = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def get_issue(self, board_id, issue_id, fullsync=False): return None
    def create_issue(self, board_id, title, body, column): return None
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass

    def set_parts(self, issue_id, parts):
        self._parts[str(issue_id)] = parts

    def list_participations(self, issue_id):
        return list(self._parts.get(str(issue_id), []))

    def remove_from_board(self, board_id, issue_id):
        if self.raise_on_remove:
            raise self.raise_on_remove
        self.removed.append((board_id, str(issue_id)))


# ── CT-14 — eventos de reconciliação (sucesso + falha), campos mínimos ────────

def test_ct14_reconcile_success_and_failure_fields_no_secrets():
    known = [
        Participation("Io", "historias", "Po", "doing"),
        Participation("Ip", "epicos", "Pp", ""),
    ]
    # Sucesso.
    port_ok = FakePort(participations={"500": known})
    PR.reconcile_remote_presence(
        Board(port_ok), "500", "epicos", _cfg(),
        known_participations=known, has_cross_board_parent=True,
    )
    reconciled = _event_lines("participation_reconciled")
    assert reconciled
    line = reconciled[-1]
    for field in ("issue", "origin_board", "propagated_board",
                  "detected_at", "reconciled_at"):
        assert field in line

    # Falha de remoção.
    port_fail = FakePort(participations={"501": known},
                         raise_on_remove=RuntimeError("x"))
    with pytest.raises(RuntimeError):
        PR.reconcile_remote_presence(
            Board(port_fail), "501", "epicos", _cfg(),
            known_participations=known, has_cross_board_parent=True,
        )
    failed = _event_lines("participation_reconcile_failed")
    assert failed
    fline = failed[-1]
    for field in ("issue", "board", "attempt", "next_attempt_at", "error_kind"):
        assert field in fline

    # Sem segredos em nenhuma linha de evento.
    for ln in _log_lines():
        assert SECRET_BODY not in ln
        assert FAKE_TOKEN not in ln


# ── CT-21 — evidência de execução no startup, com campo ausente sinalizado ────

def test_ct21_rollout_evidence_all_present(monkeypatch):
    monkeypatch.setenv("PIPE_ENVIRONMENT", "producao")
    ev = P.rollout_evidence("1.22.0", commit="abc123")
    assert ev["version"] == "1.22.0"
    assert ev["commit"] == "abc123"
    assert ev["environment"] == "producao"
    assert ev["started_at"]
    line = _event_lines("rollout_evidence")[-1]
    for field in ("version", "commit", "environment", "started_at"):
        assert field in line


def test_ct21_rollout_evidence_missing_commit_signaled(monkeypatch):
    monkeypatch.setenv("PIPE_ENVIRONMENT", "producao")
    # commit explicitamente ausente (sem checkout e sem arquivo de build).
    monkeypatch.setattr(P, "_resolve_commit", lambda: None)
    ev = P.rollout_evidence("1.22.0")
    assert ev["commit"] is None       # sinalizado como ausente, não omitido
    assert ev["version"] == "1.22.0"
    line = _event_lines("rollout_evidence")[-1]
    assert "'commit': None" in line   # presente e explicitamente nulo
    assert "campos ausentes" in line


# ── CT-22 — remoção externa registrada sem inferir autoria ────────────────────

def test_ct22_external_removal_recorded():
    cfg = _cfg()
    # Presença propagada pendente, com remoção que falha (fica pendente).
    known = [
        Participation("Io", "historias", "Po", "doing"),
        Participation("Ip", "epicos", "Pp", ""),
    ]
    port = FakePort(participations={"900": known},
                    raise_on_remove=RuntimeError("falha remocao"))
    board = Board(port)
    with pytest.raises(RuntimeError):
        PR.reconcile_remote_presence(
            board, "900", "epicos", cfg,
            known_participations=known, has_cross_board_parent=True,
        )
    assert PR.pending_entry("epicos", "900") is not None

    # No ciclo seguinte a presença em 'epicos' sumiu (removida externamente).
    port.set_parts("900", [Participation("Io", "historias", "Po", "doing")])
    PR.detect_external_removal(board, cfg)
    ext = _event_lines("participation_removed_externally")
    assert ext
    line = ext[-1]
    for field in ("issue", "board", "first_seen_at", "observed_removed_at"):
        assert field in line
    # Não infere autoria: a pendência foi limpa.
    assert PR.pending_entry("epicos", "900") is None


# ── CT-23 — nenhum evento contém segredos (varredura agregada) ────────────────

def test_ct23_no_secrets_in_any_event():
    cfg = _cfg()
    known = [
        Participation("Io", "historias", "Po", "doing"),
        Participation("Ip", "epicos", "Pp", ""),
    ]
    # CT-01/CT-02 (reconciliação), CT-08 (gate bloqueado), CT-18 (contingência),
    # CT-21 (evidência), CT-05 (falha de consulta).
    PR.reconcile_remote_presence(
        Board(FakePort(participations={"1": known})), "1", "epicos", cfg,
        known_participations=known, has_cross_board_parent=True,
    )
    P.gate_keep("epicos", "doing", {"id": "2", "participation_intent": "propagated"})
    Path("pipe.yml").write_text(
        "safety:\n  cross_board_parent_links: suspended\n", encoding="utf-8")
    try:
        PR.guard_cross_board_link("3", "4", "epicos", "historias")
    except PR.CrossBoardLinkBlocked:
        pass
    P.rollout_evidence("1.22.0", commit="abc", environment="producao")
    # Falha de consulta (unresolved).
    class FailList(FakePort):
        def list_participations(self, issue_id):
            raise ParticipationQueryError("fail")
    PR.reconcile_remote_presence(Board(FailList()), "6", "epicos", cfg)

    events = ("participation_classified", "participation_reconciled",
              "participation_reconcile_failed", "participation_removed_externally",
              "dispatch_blocked_unconfirmed_intent", "cross_board_link_blocked",
              "rollout_evidence")
    event_lines = [ln for ln in _log_lines() if any(e in ln for e in events)]
    assert event_lines  # houve eventos
    protected = (SECRET_BODY, FAKE_TOKEN, "snapshot.json", "changeQueue.json",
                 "participationPending.json")
    for ln in event_lines:
        for needle in protected:
            assert needle not in ln, f"segredo/protegido vazou: {needle} em {ln}"
