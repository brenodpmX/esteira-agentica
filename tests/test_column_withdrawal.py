"""Testes do núcleo de decisão da retirada segura de colunas (#305).

Grupo A/B/C dos casos de teste: decisão/drenagem, falha/retomada/idempotência,
isolamento e contagem. Exercita a política de verdade sobre um `FakePort`
controlável — sem rede, sem `monkeypatch` do símbolo sob teste (lição #106).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue, PenaltyException
from src.core import column_withdrawal as cw
from src.core.column_withdrawal import (
    reconcile_withdrawals, reconcile_structure,
    RESULT_COMPLETED, RESULT_BLOCKED, RESULT_INTERRUPTED,
    REASON_DESTINO_AUSENTE, REASON_DESTINO_INEXISTENTE,
    REASON_DESTINO_MESMO_BOARD_INVALIDO, REASON_DESTINO_E_ORIGEM,
    REASON_DESTINO_TAMBEM_RETIRADO, REASON_SEM_PROGRESSO,
)


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


class FakePort(BoardPort):
    """Port fake controlável e espião, sem rede.

    - `published[board]` é a lista ordenada de opções de Status remotas.
    - `issues[board]` é um dict issue_id -> Issue (com .column).
    - `list_issues` devolve a lista corrente; um hook `on_list` permite mutar o
      estado entre leituras (ex.: injetar issue que chega durante a drenagem).
    - `move_issue` aplica a mudança de coluna, conta chamadas, e pode falhar na
      N-ésima chamada ou ser no-op (simula provedor que não reduz a origem).
    - `contract_column` remove do `published` as opções que não estão na lista
      final e registra a chamada.
    """

    def __init__(self, published=None, issues=None):
        self.published = {}
        self.issues = {}
        if published:
            for b, cols in published.items():
                self.published[b] = list(cols)
        if issues:
            for b, lst in issues.items():
                self.issues[b] = {str(i.id): i for i in lst}
        self.move_calls = []          # (board, issue_id, column)
        self.get_issue_calls = 0
        self.update_issue_calls = 0
        self.contract_calls = []      # (board, final_columns)
        self.prepare_calls = []
        self.list_calls = []          # board por chamada (ordem)
        # Controles de falha/no-op na drenagem:
        self.fail_move_after = None   # levanta exc após N moves (contagem global)
        self.fail_exc = Exception("transporte")
        self.noop_move = False        # move_issue não altera a coluna
        self.move_once_then_fail = False  # move 1 e falha (por execução)
        self._moved_this_run = 0
        self.on_list = None           # callback(board) chamado a cada list_issues

    # ── primitivas ────────────────────────────────────────────────────────────
    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def prepare_structure(self, boards):
        self.prepare_calls.append(boards)
        for b in boards:
            self.published.setdefault(b["id"], [])
            for col in b["columns"]:
                if col not in self.published[b["id"]]:
                    self.published[b["id"]].append(col)

    def remote_columns(self, board_id):
        return list(self.published.get(board_id, []))

    def contract_column(self, board_id, final_columns):
        self.contract_calls.append((board_id, list(final_columns)))
        self.published[board_id] = [
            c for c in self.published.get(board_id, []) if c in final_columns
        ]

    def list_issues(self, board_id):
        self.list_calls.append(board_id)
        if self.on_list:
            self.on_list(board_id)
        return list(self.issues.get(board_id, {}).values())

    def move_issue(self, board_id, issue_id, column, from_column=None):
        if self.move_once_then_fail and self._moved_this_run >= 1:
            raise self.fail_exc
        if self.fail_move_after is not None and len(self.move_calls) >= self.fail_move_after:
            raise self.fail_exc
        self.move_calls.append((board_id, str(issue_id), column))
        self._moved_this_run += 1
        if not self.noop_move:
            iss = self.issues.get(board_id, {}).get(str(issue_id))
            if iss is not None:
                iss.column = column

    def begin_run(self):
        self._moved_this_run = 0

    # ── restantes (não usados pela política de migração) ───────────────────────
    def get_issue(self, board_id, issue_id, fullsync=False):
        self.get_issue_calls += 1
        return self.issues.get(board_id, {}).get(str(issue_id))
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def update_issue(self, board_id, issue_id, title=None, body=None):
        self.update_issue_calls += 1
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


def _issue(id, column, title="t", body="b"):
    return Issue(id=str(id), title=title, body=body, column=column)


def _by_result(attempts, source):
    for a in attempts:
        if a.source == source:
            return a
    return None


def _config(board_id="b", columns=None, migrations=None, extra_boards=None):
    cols = columns or ["backlog", "done"]
    board_cfg = {"name": board_id.upper(), "columns": {c: {"name": c} for c in cols}}
    if migrations is not None:
        board_cfg["column-migrations"] = migrations
    boards = {"platform": "github", board_id: board_cfg}
    for eb_id, eb_cols in (extra_boards or {}).items():
        boards[eb_id] = {"name": eb_id.upper(),
                         "columns": {c: {"name": c} for c in eb_cols}}
    return {"boards": boards}


# ── CT-01 — Retirada de coluna vazia ──────────────────────────────────────────

def test_ct01_empty_column_withdrawn_completed():
    port = FakePort(published={"b": ["backlog", "revisao", "done"]},
                    issues={"b": []})
    board = Board(port)
    config = _config(columns=["backlog", "done"])

    attempts = reconcile_withdrawals(board, config)

    a = _by_result(attempts, "revisao")
    assert a is not None
    assert a.result == RESULT_COMPLETED
    assert a.initial_count == 0 and a.moved_count == 0 and a.remaining_count == 0
    assert port.move_calls == []
    assert ("b", ["backlog", "done"]) in port.contract_calls
    assert "revisao" not in port.remote_columns("b")


def test_ct01b_empty_reads_before_contract():
    """Há uma leitura (list_issues) imediatamente antes da contração."""
    port = FakePort(published={"b": ["backlog", "revisao", "done"]}, issues={"b": []})
    board = Board(port)
    config = _config(columns=["backlog", "done"])

    reconcile_withdrawals(board, config)

    # Pelo menos uma leitura ocorreu e a contração foi acionada depois.
    assert port.list_calls  # leu antes
    assert port.contract_calls  # contraiu


# ── CT-02 — Migração de coluna ocupada com destino válido ─────────────────────

def test_ct02_occupied_migrated_then_contracted():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(11, "revisao"), _issue(12, "revisao")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    attempts = reconcile_withdrawals(board, config)

    a = _by_result(attempts, "revisao")
    assert a.result == RESULT_COMPLETED
    assert a.initial_count == 3 and a.moved_count == 3 and a.remaining_count == 0
    moved = [c for (_, _, c) in port.move_calls]
    assert moved == ["done", "done", "done"]
    assert "revisao" not in port.remote_columns("b")
    assert ("b", ["backlog", "done"]) in port.contract_calls


def test_ct02b_contract_preserves_other_options():
    """Contração remove só a origem; demais opções (inclusive retida) permanecem."""
    port = FakePort(
        published={"b": ["backlog", "revisao", "done", "arquivo"]},
        issues={"b": [_issue(10, "revisao"), _issue(20, "arquivo")]},
    )
    board = Board(port)
    # 'arquivo' também fora da config e ocupada sem destino -> retida (blocked).
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    reconcile_withdrawals(board, config)

    pub = port.remote_columns("b")
    assert "revisao" not in pub          # contraída
    assert "arquivo" in pub              # retida, preservada
    assert set(["backlog", "done"]).issubset(set(pub))


# ── CT-03 — Preservação de atributos ──────────────────────────────────────────

def test_ct03_only_move_issue_called():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(11, "revisao")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    reconcile_withdrawals(board, config)

    assert len(port.move_calls) == 2
    assert port.get_issue_calls == 0
    assert port.update_issue_calls == 0


# ── CT-04 — Destino ausente ───────────────────────────────────────────────────

def test_ct04_missing_destination_blocked():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(11, "revisao")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"])  # sem column-migrations

    attempts = reconcile_withdrawals(board, config)

    a = _by_result(attempts, "revisao")
    assert a.result == RESULT_BLOCKED
    assert a.reason == REASON_DESTINO_AUSENTE
    assert a.initial_count == 2 and a.moved_count == 0 and a.remaining_count == 2
    assert port.move_calls == []
    assert "revisao" in port.remote_columns("b")  # não retirada


# ── CT-05 — Destino inválido ──────────────────────────────────────────────────

def test_ct05a_destination_inexistente():
    port = FakePort(published={"b": ["backlog", "revisao", "done"]},
                    issues={"b": [_issue(10, "revisao")]})
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "naoexiste"})

    attempts = reconcile_withdrawals(board, config)
    a = _by_result(attempts, "revisao")
    assert a.result == RESULT_BLOCKED and a.reason == REASON_DESTINO_INEXISTENTE
    assert port.move_calls == []
    assert "revisao" in port.remote_columns("b")


def test_ct05b_destination_other_board():
    port = FakePort(published={"A": ["backlog", "revisao", "done"]},
                    issues={"A": [_issue(10, "revisao")]})
    board = Board(port)
    config = _config(board_id="A", columns=["backlog", "done"],
                     migrations={"revisao": "colunaB"},
                     extra_boards={"B": ["colunaB", "outra"]})

    attempts = reconcile_withdrawals(board, config)
    a = _by_result(attempts, "revisao")
    assert a.result == RESULT_BLOCKED
    assert a.reason == REASON_DESTINO_MESMO_BOARD_INVALIDO
    assert port.move_calls == []


def test_ct05c_destination_equals_source():
    port = FakePort(published={"b": ["backlog", "revisao", "done"]},
                    issues={"b": [_issue(10, "revisao")]})
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "revisao"})

    attempts = reconcile_withdrawals(board, config)
    a = _by_result(attempts, "revisao")
    assert a.result == RESULT_BLOCKED and a.reason == REASON_DESTINO_E_ORIGEM
    assert port.move_calls == []


# ── CT-06 — Destinos em ciclo / também em retirada ────────────────────────────

def test_ct06_cycle_both_blocked():
    port = FakePort(
        published={"b": ["backlog", "revisao", "espera", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(20, "espera")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"],
                     migrations={"revisao": "espera", "espera": "revisao"})

    attempts = reconcile_withdrawals(board, config)

    ar = _by_result(attempts, "revisao")
    ae = _by_result(attempts, "espera")
    assert ar.result == RESULT_BLOCKED and ar.reason == REASON_DESTINO_TAMBEM_RETIRADO
    assert ae.result == RESULT_BLOCKED and ae.reason == REASON_DESTINO_TAMBEM_RETIRADO
    assert port.move_calls == []
    assert "revisao" in port.remote_columns("b")
    assert "espera" in port.remote_columns("b")


def test_ct06_asymmetric_destination_withdrawn():
    """Destino aponta para outra coluna também em retirada -> bloqueia."""
    port = FakePort(
        published={"b": ["backlog", "revisao", "espera", "done"]},
        issues={"b": [_issue(10, "revisao")]},  # 'espera' vazia
    )
    board = Board(port)
    # revisao -> espera (espera também fora da config, mas vazia: será retirada)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "espera"})

    attempts = reconcile_withdrawals(board, config)
    a = _by_result(attempts, "revisao")
    assert a.result == RESULT_BLOCKED and a.reason == REASON_DESTINO_TAMBEM_RETIRADO


# ── CT-07 — Issue que chega durante a drenagem ────────────────────────────────

def test_ct07_issue_arrives_during_drain():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(11, "revisao")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    state = {"injected": False}

    def on_list(board_id):
        # Após drenar as 2 iniciais (ambas em done), injeta #12 em revisao uma vez.
        if not state["injected"]:
            cur = port.issues["b"]
            if all(i.column == "done" for i in cur.values()):
                cur["12"] = _issue(12, "revisao")
                state["injected"] = True

    port.on_list = on_list

    attempts = reconcile_withdrawals(board, config)
    a = _by_result(attempts, "revisao")

    assert a.result == RESULT_COMPLETED
    assert a.moved_count == 3  # #10, #11, #12
    assert a.remaining_count == 0
    assert "revisao" not in port.remote_columns("b")
    # Contração só após origem vazia (todas em done).
    assert all(i.column == "done" for i in port.issues["b"].values())


# ── CT-08 — Falha parcial e retomada ──────────────────────────────────────────

def test_ct08_partial_failure_then_resume():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(11, "revisao"), _issue(12, "revisao")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    # Execução 1: falha após mover 1 (M=1).
    port.fail_move_after = 1
    attempts1 = reconcile_withdrawals(board, config)
    a1 = _by_result(attempts1, "revisao")
    assert a1.result == RESULT_INTERRUPTED
    assert a1.moved_count == 1 and a1.remaining_count == 2
    assert "revisao" in port.remote_columns("b")  # não contraída
    moved_cols = [i.column for i in port.issues["b"].values()]
    assert moved_cols.count("done") == 1 and moved_cols.count("revisao") == 2

    # Execução 2: sem falha -> migra só as 2 restantes e contrai.
    port.fail_move_after = None
    port.move_calls.clear()
    attempts2 = reconcile_withdrawals(board, config)
    a2 = _by_result(attempts2, "revisao")
    assert a2.result == RESULT_COMPLETED
    assert len(port.move_calls) == 2  # apenas as restantes
    assert "revisao" not in port.remote_columns("b")
    assert {i.id for i in port.issues["b"].values()} == {"10", "11", "12"}
    assert all(i.column == "done" for i in port.issues["b"].values())


# ── CT-09 — Falhas sucessivas: não perda / não duplicação ─────────────────────

def test_ct09_successive_failures_no_loss_no_dup():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(11, "revisao"), _issue(12, "revisao")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    total_moves = 0
    results = []
    for _ in range(6):  # teto defensivo; converge antes
        port.begin_run()
        port.move_once_then_fail = True
        attempts = reconcile_withdrawals(board, config)
        a = _by_result(attempts, "revisao")
        total_moves += a.moved_count
        results.append(a.result)
        if a.result == RESULT_COMPLETED:
            break

    assert results[-1] == RESULT_COMPLETED
    assert all(r == RESULT_INTERRUPTED for r in results[:-1])
    assert total_moves == 3  # exatamente N moves no total
    assert {i.id for i in port.issues["b"].values()} == {"10", "11", "12"}
    assert all(i.column == "done" for i in port.issues["b"].values())
    assert "revisao" not in port.remote_columns("b")


# ── CT-10 — Sem progresso ─────────────────────────────────────────────────────

def test_ct10_no_progress_interrupted():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(11, "revisao")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})
    port.noop_move = True  # move aceito mas não reduz a origem

    attempts = reconcile_withdrawals(board, config)
    a = _by_result(attempts, "revisao")

    assert a.result == RESULT_INTERRUPTED
    assert a.reason == REASON_SEM_PROGRESSO
    assert "revisao" in port.remote_columns("b")  # não contraída
    assert a.remaining_count == 2


# ── CT-11 — Isolamento entre origens ──────────────────────────────────────────

def test_ct11_isolation_between_sources():
    port = FakePort(
        published={"b": ["backlog", "revisao", "espera", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(20, "espera")]},
    )
    board = Board(port)
    # revisao -> done (válido); espera sem destino (bloqueada).
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    attempts = reconcile_withdrawals(board, config)

    ar = _by_result(attempts, "revisao")
    ae = _by_result(attempts, "espera")
    assert ar.result == RESULT_COMPLETED
    assert ae.result == RESULT_BLOCKED and ae.reason == REASON_DESTINO_AUSENTE
    assert "revisao" not in port.remote_columns("b")
    assert "espera" in port.remote_columns("b")  # retida/preservada
    # issue de espera intacta
    assert port.issues["b"]["20"].column == "espera"


def test_ct11_isolation_between_boards():
    port = FakePort(
        published={"A": ["backlog", "revisao", "done"],
                   "B": ["backlog", "velha", "done"]},
        issues={"A": [_issue(10, "revisao")],
                "B": [_issue(99, "velha")]},
    )
    board = Board(port)
    config = _config(board_id="A", columns=["backlog", "done"],
                     migrations={"revisao": "done"},
                     extra_boards={"B": ["backlog", "done"]})
    # B.velha fora da config, sem destino -> blocked, não impede A.

    attempts = reconcile_withdrawals(board, config)
    assert _by_result(attempts, "revisao").result == RESULT_COMPLETED
    assert _by_result(attempts, "velha").result == RESULT_BLOCKED
    assert "revisao" not in port.remote_columns("A")
    assert "velha" in port.remote_columns("B")


# ── CT-15 — Contagem de chamadas ──────────────────────────────────────────────

def test_ct15_exactly_n_status_mutations():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(i, "revisao") for i in (10, 11, 12, 13)]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    reconcile_withdrawals(board, config)

    assert len(port.move_calls) == 4           # N mutações de Status
    assert port.get_issue_calls == 0           # sem releitura de conteúdo por issue
    assert port.update_issue_calls == 0


# ── CT-16 — Idempotência: reexecução no estado convergido ─────────────────────

def test_ct16_idempotent_no_extra_moves():
    port = FakePort(
        published={"b": ["backlog", "done"]},   # revisao JÁ contraída
        issues={"b": [_issue(10, "done"), _issue(11, "done")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})

    attempts = reconcile_withdrawals(board, config)

    assert attempts == []            # nenhuma coluna retirada a tratar
    assert port.move_calls == []
    assert port.contract_calls == []


# ── CT-RL-01 — Rate limit respeitado na drenagem ──────────────────────────────

def test_ct_rl01_penalty_propagates_and_no_contract():
    port = FakePort(
        published={"b": ["backlog", "revisao", "done"]},
        issues={"b": [_issue(10, "revisao"), _issue(11, "revisao"), _issue(12, "revisao")]},
    )
    board = Board(port)
    config = _config(columns=["backlog", "done"], migrations={"revisao": "done"})
    port.fail_move_after = 1
    port.fail_exc = PenaltyException(30)

    with pytest.raises(PenaltyException):
        reconcile_withdrawals(board, config)

    assert "revisao" in port.remote_columns("b")  # não contraída
    # 1 issue movida antes da penalidade.
    assert [i.column for i in port.issues["b"].values()].count("done") == 1


# ── reconcile_structure chama preparação antes da reconciliação ───────────────

def test_reconcile_structure_prepares_first():
    port = FakePort(published={"b": ["backlog", "revisao", "done"]}, issues={"b": []})
    board = Board(port)
    config = _config(columns=["backlog", "done"])

    attempts = reconcile_structure(board, config)

    assert port.prepare_calls, "prepare_structure deve ser chamado"
    assert _by_result(attempts, "revisao").result == RESULT_COMPLETED
