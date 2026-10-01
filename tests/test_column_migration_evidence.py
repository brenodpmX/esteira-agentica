"""CT-OBS-01/02, CT-17, CT-SEC-01 — Evidência por tentativa e segurança (#305).

A evidência é consultável no log diário da esteira (`logs/<data>.json`), SEM
abrir arquivos internos protegidos (`.pipe/...`). Cada tentativa produz
exatamente um registro `column_migration_attempt` com os campos de contagem/
resultado; `completed` em nível INFO, `blocked`/`interrupted` em WARNING; a
mensagem de `blocked`/`interrupted` é auto-contida; nenhum conteúdo sensível
(corpo de issue, credencial, estado protegido) vaza na evidência.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue
from src.core.log import log
from src.core import column_withdrawal as cw
from src.core.column_withdrawal import reconcile_withdrawals


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Força o singleton de log a reabrir o arquivo diário no cwd isolado.
    log._log_dir = Path("logs")
    log._setup()
    yield


def _log_lines():
    path = Path("logs") / f"{date.today().strftime('%Y-%m-%d')}.json"
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _event_lines():
    return [ln for ln in _log_lines() if cw.EVENT in ln]


class FakePort(BoardPort):
    def __init__(self, published=None, issues=None):
        self.published = {b: list(c) for b, c in (published or {}).items()}
        self.issues = {b: {str(i.id): i for i in lst}
                       for b, lst in (issues or {}).items()}
        self.noop_move = False

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def prepare_structure(self, boards): pass
    def remote_columns(self, board_id): return list(self.published.get(board_id, []))
    def contract_column(self, board_id, final_columns):
        self.published[board_id] = [c for c in self.published.get(board_id, [])
                                    if c in final_columns]
    def list_issues(self, board_id): return list(self.issues.get(board_id, {}).values())
    def move_issue(self, board_id, issue_id, column, from_column=None):
        if self.noop_move:
            return
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


def _issue(id, column, body="b"):
    return Issue(id=str(id), title="t", body=body, column=column)


def _cfg(columns, migrations=None):
    board_cfg = {"name": "B", "columns": {c: {"name": c} for c in columns}}
    if migrations is not None:
        board_cfg["column-migrations"] = migrations
    return {"boards": {"platform": "github", "b": board_cfg}}


# ── CT-OBS-01 — Campos e níveis por tentativa ─────────────────────────────────

def test_ct_obs01_fields_and_levels():
    # completed (coluna ocupada migrada)
    port = FakePort(published={"b": ["backlog", "revisao", "done"]},
                    issues={"b": [_issue(10, "revisao")]})
    reconcile_withdrawals(Board(port), _cfg(["backlog", "done"],
                                            {"revisao": "done"}))
    # blocked (destino ausente)
    port = FakePort(published={"b": ["backlog", "espera", "done"]},
                    issues={"b": [_issue(20, "espera")]})
    reconcile_withdrawals(Board(port), _cfg(["backlog", "done"]))
    # interrupted (sem progresso)
    port = FakePort(published={"b": ["backlog", "trava", "done"]},
                    issues={"b": [_issue(30, "trava")]})
    port.noop_move = True
    reconcile_withdrawals(Board(port), _cfg(["backlog", "done"],
                                            {"trava": "done"}))

    lines = _event_lines()
    completed = [l for l in lines if "result=completed" in l]
    blocked = [l for l in lines if "result=blocked" in l]
    interrupted = [l for l in lines if "result=interrupted" in l]
    assert len(completed) == 1 and len(blocked) == 1 and len(interrupted) == 1

    # Campos presentes na linha (via o dict extra serializado).
    for key in ("board", "source", "initial_count", "moved_count",
                "remaining_count", "result"):
        assert f"'{key}'" in completed[0]

    # Níveis: completed INFO; blocked/interrupted WARNING.
    assert " - INFO - " in completed[0]
    assert " - WARNING - " in blocked[0]
    assert " - WARNING - " in interrupted[0]

    # reason presente/não-vazio em blocked e interrupted.
    assert "destino_ausente" in blocked[0]
    assert "sem_progresso" in interrupted[0]


# ── CT-OBS-02 — Mensagem de blocked é auto-contida ────────────────────────────

def test_ct_obs02_blocked_message_self_contained():
    port = FakePort(published={"b": ["backlog", "revisao", "done"]},
                    issues={"b": [_issue(10, "revisao")]})
    reconcile_withdrawals(Board(port), _cfg(["backlog", "done"],
                                            {"revisao": "naoexiste"}))
    blocked = [l for l in _event_lines() if "result=blocked" in l]
    assert len(blocked) == 1
    msg = blocked[0]
    # board, origem e motivo específico legíveis na própria linha textual.
    assert "board=b" in msg
    assert "source=revisao" in msg
    assert "destino_inexistente" in msg


# ── CT-17 — Evidência coerente por execução (não acumulada) ───────────────────

def test_ct17_per_execution_counts_not_accumulated():
    # N=3; move exatamente 1 por execução e falha; contadores por tentativa.
    issues = [_issue(10, "revisao"), _issue(11, "revisao"), _issue(12, "revisao")]
    port = FakePort(published={"b": ["backlog", "revisao", "done"]},
                    issues={"b": issues})

    moved_counter = {"n": 0}
    real_move = port.move_issue

    def move_once(board_id, issue_id, column, from_column=None):
        if moved_counter["n"] >= 1:
            raise Exception("transporte")
        real_move(board_id, issue_id, column, from_column)
        moved_counter["n"] += 1

    config = _cfg(["backlog", "done"], {"revisao": "done"})

    results = []
    for _ in range(6):
        moved_counter["n"] = 0
        port.move_issue = move_once
        attempts = reconcile_withdrawals(Board(port), config)
        a = next(a for a in attempts if a.source == "revisao")
        results.append((a.result, a.moved_count))
        if a.result == cw.RESULT_COMPLETED:
            break

    # Cada tentativa reflete o estado DAQUELA execução: moved_count<=1, nunca
    # um acumulado (jamais 2 ou 3 numa única tentativa de passagem única).
    for _, mc in results:
        assert mc <= 1
    assert results[-1][0] == cw.RESULT_COMPLETED
    # soma dos moved_count = N (3), distribuída por execução.
    assert sum(mc for _, mc in results) == 3


# ── CT-SEC-01 — Logs não contêm conteúdo sensível ────────────────────────────

def test_ct_sec01_no_sensitive_content_in_evidence():
    marker = "CORPO_SECRETO_123"
    port = FakePort(published={"b": ["backlog", "revisao", "done"]},
                    issues={"b": [_issue(10, "revisao", body=marker),
                                  _issue(11, "revisao", body=marker)]})
    reconcile_withdrawals(Board(port), _cfg(["backlog", "done"],
                                            {"revisao": "done"}))

    for line in _event_lines():
        assert marker not in line
        assert "snapshot.json" not in line
        assert "changeQueue.json" not in line
