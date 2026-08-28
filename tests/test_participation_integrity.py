"""Testes do modelo `Participation` e do contrato `list_participations` no BoardPort.

Cobre exclusivamente o escopo da issue #247 (story #243):
- `Participation` como dataclass simples em `src/core/board.py`.
- `BoardPort.list_participations`: operação opcional (default no-op,
  `log.warning` + retorno de lista vazia, mesmo padrão de
  `remove_from_board`/`set_labels`/etc.).
- `Board.list_participations`: delegação pura ao port (mesmo padrão de
  `Board.connect`/`Board.check_access`).

Fora de escopo (não testado aqui, conforme a própria issue): GraphQL real no
`GitHubBoardAdapter`, classificação de intenção (`origin`/`authorized`/
`propagated`/`unresolved`), e qualquer chamada a `list_participations` a
partir de `_add_sub_issue` ou outro fluxo.

Ver `doc/product/integridade-de-issues-entre-boards/casos-de-teste/
247-casos-de-teste-participation-list-participations.md` para a versão
legível/rastreável destes casos (CT01-CT06).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue, Participation


# ── Fake adapter mínimo (só os métodos abstratos obrigatórios) ────────────────

class FakePort(BoardPort):
    """Implementa apenas os métodos abstratos de BoardPort.

    Não sobrescreve list_participations - exercita o default de BoardPort.
    """

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
    def close_issue(self, board_id, issue_id): pass


class FakePortWithParticipations(FakePort):
    """Sobrescreve list_participations com uma resposta fixa e registra chamadas."""

    def __init__(self, participations):
        self._participations = participations
        self.calls = []

    def list_participations(self, issue_id):
        self.calls.append(("list_participations", issue_id))
        return self._participations


# ── CT01 — Participation é um dataclass simples instanciável ──────────────────

def test_participation_instantiation_with_all_fields():
    p = Participation(
        board_id="backlog",
        item_id="PVTI_1",
        project_id="PVT_1",
        status="Doing",
        archived=False,
    )
    assert p.board_id == "backlog"
    assert p.item_id == "PVTI_1"
    assert p.project_id == "PVT_1"
    assert p.status == "Doing"
    assert p.archived is False


def test_participation_archived_defaults_to_false():
    p = Participation(
        board_id="backlog",
        item_id="PVTI_1",
        project_id="PVT_1",
        status="Doing",
    )
    assert p.archived is False


def test_participation_accepts_none_board_id_and_status():
    p = Participation(
        board_id=None,
        item_id="PVTI_2",
        project_id="PVT_2",
        status=None,
    )
    assert p.board_id is None
    assert p.status is None
    assert p.item_id == "PVTI_2"
    assert p.project_id == "PVT_2"


# ── CT02 — list_participations é operação opcional (não abstrata) ────────────

def test_fake_port_without_override_instantiates_successfully():
    # Não deve levantar TypeError por método abstrato pendente.
    fake = FakePort()
    assert isinstance(fake, BoardPort)


def test_board_port_default_list_participations_returns_empty_list():
    fake = FakePort()
    result = fake.list_participations("76")
    assert result == []


# ── CT03 — default loga warning e não lança exceção ───────────────────────────

def test_default_list_participations_logs_warning_without_raising(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.core.board.log.warning",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    fake = FakePort()
    result = fake.list_participations("76")
    assert result == []
    assert len(calls) == 1


# ── CT04 — Board.list_participations delega ao port ───────────────────────────

def test_board_list_participations_delegates_to_port():
    fixed = [
        Participation(board_id="backlog", item_id="PVTI_1", project_id="PVT_1", status="Doing"),
        Participation(board_id=None, item_id="PVTI_2", project_id="PVT_2", status=None),
    ]
    fake = FakePortWithParticipations(fixed)
    board = Board(fake)

    result = board.list_participations("76")

    assert result == fixed


def test_board_list_participations_returns_same_objects_as_port():
    fixed = [
        Participation(board_id="backlog", item_id="PVTI_1", project_id="PVT_1", status="Doing"),
    ]
    fake = FakePortWithParticipations(fixed)
    board = Board(fake)

    result = board.list_participations("76")

    assert result is fixed
    assert result[0] is fixed[0]


def test_board_list_participations_passes_issue_id_unchanged():
    fake = FakePortWithParticipations([])
    board = Board(fake)

    board.list_participations("76")

    assert fake.calls == [("list_participations", "76")]


# ── CT05 — Board.list_participations com port sem override retorna [] ────────

def test_board_list_participations_with_default_port_returns_empty_list():
    board = Board(FakePort())
    result = board.list_participations("76")
    assert result == []
