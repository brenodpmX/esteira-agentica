"""Testes de `sanitize_relations` — auto-referência em parent/children/blocked_by/blocks.

Cobrem a issue #143 (US-01 do épico #104 / story #138): impedir que uma issue
seja registrada como sua própria `parent`, `children`, `blocked_by` ou
`blocks` antes de qualquer chamada ao board.

Escopo:
- `sanitize_relations` (função pura, `src/core/commands.py`).
- Defesa em profundidade em `Board.apply_commands` (`src/core/board.py`).
- Integração com `_apply_create_up` e `_apply_change_up` (`src/core/sync.py`).

Nota: estes testes foram escritos ANTES da implementação (etapa "Casos de
Teste" antecede/acompanha a implementação). `sanitize_relations` ainda não
existe em `src/core/commands.py` no momento da escrita — os testes que a
importam devem falhar até a implementação da issue ser feita, e passar depois.
"""

import sys
from pathlib import Path

import pytest

# Permite importar o pacote src quando rodado de qualquer lugar.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.commands import IssueCommands, sanitize_relations
from src.core.board import Board, BoardPort, Issue


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola .pipe/ em um diretório temporário por teste."""
    monkeypatch.chdir(tmp_path)
    yield


# ══════════════════════════════════════════════════════════════════════════
# Fake adapter que registra chamadas em vez de bater na rede
# ══════════════════════════════════════════════════════════════════════════

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
        return Issue(id="76", title=title, body=body, column=column)
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


# ══════════════════════════════════════════════════════════════════════════
# CT01 — remoção isolada por relação (AC1)
# ══════════════════════════════════════════════════════════════════════════

def test_sanitize_removes_self_reference_from_parent():
    cmds = IssueCommands(parent="76")
    result = sanitize_relations("76", cmds)
    assert result.parent is None


def test_sanitize_removes_self_reference_from_children():
    cmds = IssueCommands(children=["76"])
    result = sanitize_relations("76", cmds)
    assert result.children == []


def test_sanitize_removes_self_reference_from_blocked_by():
    cmds = IssueCommands(blocked_by=["76"])
    result = sanitize_relations("76", cmds)
    assert result.blocked_by == []


def test_sanitize_removes_self_reference_from_blocks():
    cmds = IssueCommands(blocks=["76"])
    result = sanitize_relations("76", cmds)
    assert result.blocks == []


def test_sanitize_removes_self_reference_from_all_four_combined():
    """Auto-referência combinada nas quatro relações no mesmo IssueCommands."""
    cmds = IssueCommands(parent="76", children=["76"], blocked_by=["76"], blocks=["76"])
    result = sanitize_relations("76", cmds)
    assert result.parent is None
    assert result.children == []
    assert result.blocked_by == []
    assert result.blocks == []


# ══════════════════════════════════════════════════════════════════════════
# CT02 — lista mista: só a auto-referência é descartada (AC2)
# ══════════════════════════════════════════════════════════════════════════

def test_sanitize_keeps_valid_ids_in_mixed_children_list():
    cmds = IssueCommands(children=["76", "10"])
    result = sanitize_relations("76", cmds)
    assert result.children == ["10"]


def test_sanitize_keeps_valid_ids_in_mixed_blocked_by_list():
    cmds = IssueCommands(blocked_by=["10", "76", "20"])
    result = sanitize_relations("76", cmds)
    assert result.blocked_by == ["10", "20"]


def test_sanitize_keeps_valid_ids_in_mixed_blocks_list():
    cmds = IssueCommands(blocks=["76", "30"])
    result = sanitize_relations("76", cmds)
    assert result.blocks == ["30"]


def test_sanitize_no_self_reference_is_noop_on_values():
    """Sem auto-referência, os valores permanecem intactos (mas é uma cópia — ver CT04)."""
    cmds = IssueCommands(parent="10", children=["2", "3"], blocked_by=["4"], blocks=["5"])
    result = sanitize_relations("76", cmds)
    assert result.parent == "10"
    assert result.children == ["2", "3"]
    assert result.blocked_by == ["4"]
    assert result.blocks == ["5"]


# ══════════════════════════════════════════════════════════════════════════
# CT03 — normalização de tipo (str vs int) antes de comparar (AC3)
# ══════════════════════════════════════════════════════════════════════════

def test_sanitize_str_issue_id_str_relation_ids():
    cmds = IssueCommands(parent="76")
    result = sanitize_relations("76", cmds)
    assert result.parent is None


def test_sanitize_int_issue_id_str_relation_ids():
    cmds = IssueCommands(parent="76")
    result = sanitize_relations(76, cmds)
    assert result.parent is None


def test_sanitize_str_issue_id_int_relation_ids_in_children():
    # children tipicamente é list[str], mas a função deve normalizar mesmo
    # que algum chamador passe int.
    cmds = IssueCommands(children=[76, 10])
    result = sanitize_relations("76", cmds)
    assert result.children == ["10"]


def test_sanitize_int_issue_id_int_relation_id_in_blocked_by():
    cmds = IssueCommands(blocked_by=[76])
    result = sanitize_relations(76, cmds)
    assert result.blocked_by == []


# ══════════════════════════════════════════════════════════════════════════
# CT04 — imutabilidade do objeto de entrada (AC4)
# ══════════════════════════════════════════════════════════════════════════

def test_sanitize_does_not_mutate_input_parent():
    cmds = IssueCommands(parent="76")
    sanitize_relations("76", cmds)
    assert cmds.parent == "76"


def test_sanitize_does_not_mutate_input_lists():
    cmds = IssueCommands(children=["76", "10"], blocked_by=["76"], blocks=["76", "5"])
    sanitize_relations("76", cmds)
    assert cmds.children == ["76", "10"]
    assert cmds.blocked_by == ["76"]
    assert cmds.blocks == ["76", "5"]


def test_sanitize_returns_new_instance():
    cmds = IssueCommands(parent="76")
    result = sanitize_relations("76", cmds)
    assert result is not cmds


def test_sanitize_preserves_other_fields_unchanged():
    cmds = IssueCommands(
        parent="76", labels=["backend", "security"], agent_level="high",
        close="completed", reopen=False, archive=True, need_human=True,
    )
    result = sanitize_relations("76", cmds)
    assert result.labels == ["backend", "security"]
    assert result.agent_level == "high"
    assert result.close == "completed"
    assert result.reopen is False
    assert result.archive is True
    assert result.need_human is True


# ══════════════════════════════════════════════════════════════════════════
# CT05 — log.warning por auto-referência descartada (AC5)
# ══════════════════════════════════════════════════════════════════════════

def test_sanitize_logs_warning_for_each_discarded_relation(monkeypatch):
    calls = []

    def fake_warning(module, msg, *args, **extra):
        calls.append((module, msg, extra))

    from src.core import commands as commands_mod
    monkeypatch.setattr(commands_mod.log, "warning", fake_warning)

    cmds = IssueCommands(parent="76", children=["76"], blocked_by=["76"], blocks=["76"])
    sanitize_relations("76", cmds)

    # Uma auto-referência descartada por relação -> 4 warnings.
    assert len(calls) == 4
    for _module, msg, extra in calls:
        assert "76" in msg or extra.get("issue_id") == "76"


def test_sanitize_logs_warning_contains_relation_name_and_id(monkeypatch):
    calls = []

    def fake_warning(module, msg, *args, **extra):
        calls.append((module, msg, extra))

    from src.core import commands as commands_mod
    monkeypatch.setattr(commands_mod.log, "warning", fake_warning)

    cmds = IssueCommands(blocked_by=["76"])
    sanitize_relations("76", cmds)

    assert len(calls) == 1
    _module, msg, extra = calls[0]
    assert "blocked_by" in msg
    assert "76" in msg


def test_sanitize_no_warning_when_no_self_reference(monkeypatch):
    calls = []

    def fake_warning(module, msg, *args, **extra):
        calls.append((module, msg, extra))

    from src.core import commands as commands_mod
    monkeypatch.setattr(commands_mod.log, "warning", fake_warning)

    cmds = IssueCommands(parent="10", children=["2"], blocked_by=["3"], blocks=["4"])
    sanitize_relations("76", cmds)

    assert calls == []


def test_sanitize_pure_function_no_board_id_required():
    """sanitize_relations não recebe board_id (função pura, sem I/O)."""
    import inspect
    sig = inspect.signature(sanitize_relations)
    params = list(sig.parameters)
    assert "board_id" not in params
    assert params[:2] == ["issue_id", "cmds"]


# ══════════════════════════════════════════════════════════════════════════
# CT06 — integração com Board.apply_commands (AC6)
# ══════════════════════════════════════════════════════════════════════════

def test_apply_commands_blocks_self_reference_in_parent():
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(parent="76")
    board.apply_commands("b", "76", cmds, known=None)
    for call in port.calls:
        if call[0] == "set_parent":
            assert call[2] != "76"
    # set_parent não deve nem ser chamado com valor "76", pois o valor
    # desejado após sanitização é None (sem parent).
    parent_calls = [c for c in port.calls if c[0] == "set_parent"]
    assert not any(c[2] == "76" for c in parent_calls)


def test_apply_commands_blocks_self_reference_in_children():
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(children=["76", "10"])
    board.apply_commands("b", "76", cmds, known=None)
    children_calls = [c for c in port.calls if c[0] == "set_children"]
    assert children_calls, "set_children deveria ser chamado (ainda há '10' válido)"
    for call in children_calls:
        assert "76" not in call[2]


def test_apply_commands_blocks_self_reference_in_blocked_by():
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(blocked_by=["76"])
    board.apply_commands("b", "76", cmds, known=None)
    blocked_by_calls = [c for c in port.calls if c[0] == "set_blocked_by"]
    for call in blocked_by_calls:
        assert "76" not in call[2]


def test_apply_commands_blocks_self_reference_in_blocks():
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(blocks=["76"])
    board.apply_commands("b", "76", cmds, known=None)
    blocks_calls = [c for c in port.calls if c[0] == "set_blocks"]
    for call in blocks_calls:
        assert "76" not in call[2]


def test_apply_commands_self_reference_not_reintroduced_via_stale_known():
    """Auto-referência não deve ser reintroduzida mesmo com `known` desatualizado
    (ex.: known.parent já era '76' de um estado corrompido anterior)."""
    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(parent="76")
    known = {
        "labels": [], "parent": "76", "children": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
    }
    board.apply_commands("b", "76", cmds, known=known)
    parent_calls = [c for c in port.calls if c[0] == "set_parent"]
    assert not any(c[2] == "76" for c in parent_calls)


def test_apply_commands_logs_warning_with_board_id(monkeypatch):
    calls = []

    def fake_warning(module, msg, *args, **extra):
        calls.append((module, msg, extra))

    from src.core import board as board_mod
    monkeypatch.setattr(board_mod.log, "warning", fake_warning)

    port = FakePort()
    board = Board(port)
    cmds = IssueCommands(parent="76")
    board.apply_commands("meu-board", "76", cmds, known=None)

    assert len(calls) == 1
    _module, msg, extra = calls[0]
    assert extra.get("board_id") == "meu-board" or "meu-board" in msg


# ══════════════════════════════════════════════════════════════════════════
# CT07 — integração com _apply_create_up e _apply_change_up (AC7)
# ══════════════════════════════════════════════════════════════════════════

def test_apply_change_up_self_reference_not_sent_to_adapter(tmp_path, monkeypatch):
    """Body local com /blocked_by #<próprio-id> não deve chegar ao adapter."""
    from src.core import sync
    from src.core.change_queue import ChangeQueue
    from src.core.snapshot import Snapshot
    from src.core.board import ChangeItem, SyncEvent

    board_id = "task"
    issue_id = "76"

    col_dir = tmp_path / board_id / "doing"
    col_dir.mkdir(parents=True)
    body_path = col_dir / f"{issue_id}-teste-body.md"
    body_path.write_text(
        "# Teste\n\nConteudo.\n\n@---\n/blocked_by #76, #10\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    snap = Snapshot(board_id).load()
    snap.issues.append({
        "id": issue_id,
        "column": "doing",
        "body_path": str(body_path),
        "body_mtime": str(body_path.stat().st_mtime),
        "status": "ok",
        "labels": [], "parent": None, "children": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
    })
    snap.save()

    port = FakePort()
    board_obj = Board(port)
    item = ChangeItem.of(SyncEvent.CHANGE_UP, id=issue_id, board=board_id)
    queue = ChangeQueue()

    sync._apply_change_up(board_id, item, board_obj, queue=queue, config={})

    blocked_by_calls = [c for c in port.calls if c[0] == "set_blocked_by"]
    for call in blocked_by_calls:
        assert issue_id not in call[2]
    # "10" (id válido) deve continuar presente se set_blocked_by foi chamado.
    if blocked_by_calls:
        assert "10" in blocked_by_calls[0][2]


def test_apply_create_up_self_reference_not_sent_to_adapter(tmp_path, monkeypatch):
    """Issue nova cujo id recém-criado coincide com uma referência do body
    não deve resultar em auto-referência enviada ao adapter."""
    from src.core import sync
    from src.core.change_queue import ChangeQueue
    from src.core.snapshot import Snapshot
    from src.core.board import ChangeItem, SyncEvent, Issue

    board_id = "task"

    col_dir = tmp_path / board_id / "todo"
    col_dir.mkdir(parents=True)
    body_path = col_dir / "nova-tarefa-body.md"
    # FakePort.create_issue sempre retorna id "76" — simula que o id recém
    # criado coincide com a referência declarada no body.
    body_path.write_text(
        "# Nova tarefa\n\nConteudo.\n\n@---\n/blocked_by #76, #10\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    snap = Snapshot(board_id).load()
    snap.issues.append({
        "body_path": str(body_path),
        "column": "todo",
        "status": "pending-create",
    })
    snap.save()

    port = FakePort()
    board_obj = Board(port)
    item = ChangeItem.of(SyncEvent.CREATE_UP, id=str(body_path), board=board_id)
    queue = ChangeQueue()

    sync._apply_create_up(board_id, item, board_obj, queue=queue)

    blocked_by_calls = [c for c in port.calls if c[0] == "set_blocked_by"]
    for call in blocked_by_calls:
        assert "76" not in call[2]
    if blocked_by_calls:
        assert "10" in blocked_by_calls[0][2]


# ══════════════════════════════════════════════════════════════════════════
# CT08 — não-regressão (AC8, verificado via execução completa da suíte)
# ══════════════════════════════════════════════════════════════════════════
# Não há teste específico aqui: o critério é validado executando
# `python -m pytest tests/ -v` e confirmando que os testes já existentes em
# test_sync_optimization.py e demais arquivos de board.py/commands.py/sync.py
# continuam passando após a implementação desta issue.
