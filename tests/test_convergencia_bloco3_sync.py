import io
import time
from pathlib import Path

import pytest

import src.__main__ as main
from src.core import participation_reconcile as PR
from src.core import sync_circuit_breaker as scb
from src.core.board import Board, ChangeItem, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.log import log
from src.core.participation import (
    Classification, Participation, ParticipationQueryError, UNRESOLVED,
)
from src.core.snapshot import Snapshot
from src.core.sync import apply_changes
from src.core.sync_circuit_breaker import SyncCircuitBreaker
from tests.test_sync_circuit_breaker import Clock, FakePort as SyncFakePort

CHILD_BOARD = "tarefas"
PARENT_BOARD = "epicos"
CHILD = "5"
PARENT = "10"
PENDING_ISSUE = "900"


class ConvergencePort(SyncFakePort):
    def __init__(self, participations=None):
        super().__init__()
        self.update_error = None
        self.list_error = None
        self._parts = {str(k): list(v) for k, v in (participations or {}).items()}
        self.list_calls = []
        self.removed = []

    def update_issue(self, board_id, issue_id, title=None, body=None):
        if self.update_error is not None:
            raise self.update_error

    def list_participations(self, issue_id):
        self.list_calls.append(str(issue_id))
        if self.list_error is not None:
            raise self.list_error
        return list(self._parts.get(str(issue_id), []))

    def remove_from_board(self, board_id, issue_id):
        self.removed.append((board_id, str(issue_id)))


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scb.reset_memory_state()
    yield
    scb.reset_memory_state()


@pytest.fixture(autouse=True)
def log_buffer():
    original = log._file
    buffer = io.StringIO()
    log._file = buffer
    yield buffer
    log._file = original


def make_config(issue=None, platform=None) -> dict:
    return {
        "boards": {
            "platform": "github",
            CHILD_BOARD: {"columns": {"doing": {"name": "Doing"}}},
            PARENT_BOARD: {"columns": {"doing": {"name": "Doing"}}},
            "historias": {"columns": {"doing": {"name": "Doing"}}},
        },
        "sync": {"circuit_breaker": {
            "persistence": "file",
            "issue": issue or {"max_failures": 3, "block_duration": 300,
                               "max_blocks": 3},
            "platform": platform or {"max_blocked_issues": 5, "block_window": 600,
                                     "block_duration": 900},
            "half_open": {"success_threshold": 2},
        }},
    }


def propagated_parts():
    return {CHILD: [
        Participation("Ita", CHILD_BOARD, "Pta", "doing"),
        Participation("Iep", PARENT_BOARD, "Pep", ""),
    ]}


def seed_cross_board_link():
    parent_snap = Snapshot(PARENT_BOARD).load()
    parent_snap.board = {"doing": "Doing"}
    parent_snap.issues.append({"id": PARENT, "column": "doing", "status": "ok"})
    parent_snap.save()

    body_dir = Path(".pipe/boards") / CHILD_BOARD / "doing"
    body_dir.mkdir(parents=True, exist_ok=True)
    body_path = body_dir / f"{CHILD}-filha-body.md"
    body_path.write_text(f"# filha\n\ncorpo\n\n@---\n/parent #{PARENT}\n",
                         encoding="utf-8")
    snap = Snapshot(CHILD_BOARD).load()
    snap.board = {"doing": "Doing"}
    snap.issues.append({
        "id": CHILD, "column": "doing", "body_path": str(body_path),
        "body_mtime": "1", "updated_at": "2024-01-01T00:00:00Z", "status": "ok",
        "parent": None,
    })
    snap.save()


def change_up_cycle(port, config, breaker):
    ChangeQueue().add(ChangeItem.of(SyncEvent.CHANGE_UP, id=CHILD, board=CHILD_BOARD))
    return apply_changes(Board(port), ChangeQueue(), config, breaker=breaker)


def queued_ids():
    return [i.id for i in ChangeQueue().items()]


class TestApplyChangesConvergence:
    def test_ct04a_issue_bloqueada_nao_tenta_reconciliacao(self):
        config = make_config()
        seed_cross_board_link()
        breaker = SyncCircuitBreaker(config, clock=Clock())
        port = ConvergencePort(participations=propagated_parts())
        port.update_error = Exception("timeout de rede")
        for _ in range(3):
            change_up_cycle(port, config, breaker)
        assert breaker.issue_blocked(CHILD_BOARD, CHILD)

        port.update_error = None
        change_up_cycle(port, config, breaker)

        assert port.list_calls == []
        assert port.removed == []
        assert queued_ids() == [CHILD]

    def test_ct04a_contraprova_issue_livre_reconcilia(self):
        config = make_config()
        seed_cross_board_link()
        breaker = SyncCircuitBreaker(config, clock=Clock())
        port = ConvergencePort(participations=propagated_parts())

        change_up_cycle(port, config, breaker)

        assert port.list_calls == [CHILD]
        assert (PARENT_BOARD, CHILD) in port.removed
        assert queued_ids() == []
        assert not breaker.issue_blocked(CHILD_BOARD, CHILD)

    def test_ct04b_falha_de_reconciliacao_e_contada_pelo_circuit_breaker(self, log_buffer):
        config = make_config()
        seed_cross_board_link()
        breaker = SyncCircuitBreaker(config, clock=Clock())
        port = ConvergencePort(participations=propagated_parts())
        port.list_error = ParticipationQueryError("falha ao consultar presenças")

        change_up_cycle(port, config, breaker)
        change_up_cycle(port, config, breaker)
        assert not breaker.issue_blocked(CHILD_BOARD, CHILD)
        change_up_cycle(port, config, breaker)

        assert port.list_calls == [CHILD, CHILD, CHILD]
        assert breaker.issue_blocked(CHILD_BOARD, CHILD)
        assert queued_ids() == [CHILD]
        text = log_buffer.getvalue()
        assert "participation_reconcile_failed" in text
        assert "sync_circuit_breaker_issue_blocked" in text

        change_up_cycle(port, config, breaker)
        assert port.list_calls == [CHILD, CHILD, CHILD]

    def test_ct04b_sucesso_de_reconciliacao_zera_contagem(self):
        config = make_config()
        seed_cross_board_link()
        breaker = SyncCircuitBreaker(config, clock=Clock())
        port = ConvergencePort(participations=propagated_parts())
        port.list_error = ParticipationQueryError("falha ao consultar presenças")
        change_up_cycle(port, config, breaker)
        change_up_cycle(port, config, breaker)

        port.list_error = None
        change_up_cycle(port, config, breaker)

        assert (PARENT_BOARD, CHILD) in port.removed
        assert not breaker.issue_blocked(CHILD_BOARD, CHILD)
        assert queued_ids() == []


def block_platform(port, config):
    ids = ("1", "2")
    snap = Snapshot(PARENT_BOARD).load()
    for issue_id in ids:
        snap.issues.append({"id": issue_id, "column": "doing", "status": "ok"})
    snap.save()
    breaker = SyncCircuitBreaker(config, clock=Clock(time.time()))
    port.error = Exception("timeout de rede")
    for issue_id in ids:
        ChangeQueue().add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id=issue_id,
                                        board=PARENT_BOARD))
    apply_changes(Board(port), ChangeQueue(), config, breaker=breaker)
    port.error = None
    return breaker


def platform_config():
    return make_config(
        issue={"max_failures": 1, "block_duration": 3600, "max_blocks": 99},
        platform={"max_blocked_issues": 2, "block_window": 3600,
                  "block_duration": 3600},
    )


def seed_pending():
    PR.defer_pending(PARENT_BOARD, PENDING_ISSUE, Classification(UNRESOLVED, {}), 300)


class TestSyncRemoteBoardConvergence:
    def test_ct04c_plataforma_bloqueada_suprime_detect_external_removal(self, monkeypatch):
        config = platform_config()
        port = ConvergencePort(participations={PENDING_ISSUE: [
            Participation("Io", "historias", "Po", "doing")]})
        block_platform(port, config)
        assert SyncCircuitBreaker(config).platform_blocked("github")
        seed_pending()
        before = PR.pending_entry(PARENT_BOARD, PENDING_ISSUE)
        monkeypatch.setattr(main, "board", Board(port))

        result = main.sync_remote_board(PARENT_BOARD, config)

        assert result is False
        assert port.list_calls == []
        assert PR.pending_entry(PARENT_BOARD, PENDING_ISSUE) == before

    def test_ct04c_contraprova_plataforma_livre_detecta_remocao(self, monkeypatch, log_buffer):
        config = platform_config()
        port = ConvergencePort(participations={PENDING_ISSUE: [
            Participation("Io", "historias", "Po", "doing")]})
        seed_pending()
        assert not SyncCircuitBreaker(config).platform_blocked("github")
        monkeypatch.setattr(main, "board", Board(port))

        main.sync_remote_board(PARENT_BOARD, config)

        assert port.list_calls == [PENDING_ISSUE]
        assert PR.pending_entry(PARENT_BOARD, PENDING_ISSUE) is None
        assert "participation_removed_externally" in log_buffer.getvalue()
