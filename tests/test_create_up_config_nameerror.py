"""Testes da issue #339 — create-up com comandos não pode falhar por `config`
nem recriar a issue no board a cada tentativa."""

import sys
from pathlib import Path

import pytest

# Permite importar o pacote src quando rodado de qualquer lugar.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, ChangeItem, Issue, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola .pipe/ em um diretório temporário por teste."""
    monkeypatch.chdir(tmp_path)
    yield


# ══════════════════════════════════════════════════════════════════════════
# Fake adapter que registra chamadas em vez de bater na rede
# ══════════════════════════════════════════════════════════════════════════

class FakePort(BoardPort):
    """BoardPort fake: cria issues com ids sequenciais e registra chamadas."""

    def __init__(self, start_id: int = 100):
        self.calls = []
        self._next_id = start_id

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def list_issues_since(self, board_id, since): return []

    def get_issue(self, board_id, issue_id, fullsync=False):
        return Issue(id=issue_id, title="", body="", column="")

    def create_issue(self, board_id, title, body, column):
        self._next_id += 1
        new_id = str(self._next_id)
        self.calls.append(("create_issue", board_id, title, new_id))
        return Issue(id=new_id, title=title, body=body, column=column)

    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass
    def reopen_issue(self, board_id, issue_id): pass

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

    def archive_issue(self, board_id, issue_id): pass
    def unarchive_issue(self, board_id, issue_id): pass


def _new_body_file(tmp_path: Path, board_id: str, column: str, filename: str,
                    title: str, commands_block: str | None) -> Path:
    """Cria um -body.md novo (sem ID) e o registra no snapshot como
    'pending-create', simulando uma issue local recém-criada pelo agente."""
    col_dir = tmp_path / board_id / column
    col_dir.mkdir(parents=True, exist_ok=True)
    body_path = col_dir / filename

    content = f"# {title}\n\nConteudo de teste.\n"
    if commands_block:
        content += f"\n@---\n{commands_block}\n"
    body_path.write_text(content, encoding="utf-8")

    snap = Snapshot(board_id).load()
    snap.issues.append({
        "body_path": str(body_path),
        "column": column,
        "status": "pending-create",
    })
    snap.save()
    return body_path


def _create_up_item(body_path: Path, board_id: str) -> ChangeItem:
    """Constrói o ChangeItem correto para create-up: a busca em
    _apply_create_up usa item.identifier, nunca item.id."""
    return ChangeItem.of(SyncEvent.CREATE_UP, identifier=str(body_path), board=board_id)


# ══════════════════════════════════════════════════════════════════════════
# Grupo A — Reprodução determinística do bug (CA-1, CA-2)
# ══════════════════════════════════════════════════════════════════════════

class TestCreateUpComComandos:
    @pytest.mark.parametrize("commands_block", [
        "/parent #81",
        "/labels bug",
        "/need_human",
        "/blocked_by #10",
    ])
    def test_create_up_com_comandos_conclui_sem_erro(self, tmp_path, commands_block):
        from src.core import sync

        board_id = "task"
        safe_name = commands_block.strip("/").replace(" ", "_").replace("#", "")
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", f"tarefa-{safe_name}-body.md",
            "Tarefa", commands_block,
        )

        port = FakePort()
        board_obj = Board(port)
        item = _create_up_item(body_path, board_id)

        sync._apply_create_up(board_id, item, board_obj, queue=ChangeQueue(), config={})

        assert len([c for c in port.calls if c[0] == "create_issue"]) == 1
        assert not body_path.exists()

    def test_parent_e_aplicado_e_arquivo_renomeado_com_id(self, tmp_path):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        board_obj = Board(port)
        item = _create_up_item(body_path, board_id)

        sync._apply_create_up(board_id, item, board_obj, queue=ChangeQueue(), config={})

        assert ("set_parent", "101", "81") in port.calls
        assert not body_path.exists()

    def test_config_e_opcional(self, tmp_path):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        item = _create_up_item(body_path, board_id)

        sync._apply_create_up(board_id, item, Board(port), queue=ChangeQueue())

        assert ("set_parent", "101", "81") in port.calls

    def test_sem_bloco_de_comandos_conclui(self, tmp_path):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "tarefa-sem-comando-body.md",
            "Tarefa sem comando", None,
        )

        port = FakePort()
        item = _create_up_item(body_path, board_id)

        sync._apply_create_up(board_id, item, Board(port), queue=ChangeQueue(), config={})

        assert len([c for c in port.calls if c[0] == "create_issue"]) == 1
        assert not body_path.exists()


class TestApplyChangesNaoDuplicaIssue:
    @pytest.mark.parametrize("max_attempts", [1, 3, 5])
    def test_create_issue_chamado_uma_unica_vez(self, tmp_path, max_attempts):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        board_obj = Board(port)
        queue = ChangeQueue()
        queue.add(_create_up_item(body_path, board_id))

        config = {"sync": {"max_attempts": max_attempts}}
        for _ in range(max_attempts):
            sync.apply_changes(board_obj, queue, config=config)

        assert len([c for c in port.calls if c[0] == "create_issue"]) == 1
        assert queue.getNext() is None

    def test_apply_changes_propaga_config_ao_create_up(self, tmp_path, monkeypatch):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        received = {}
        original = sync._apply_create_up

        def _spy(board_id, item, board_obj, queue=None, config=None):
            received["config"] = config
            return original(board_id, item, board_obj, queue, config)

        monkeypatch.setattr(sync, "_apply_create_up", _spy)

        queue = ChangeQueue()
        queue.add(_create_up_item(body_path, board_id))
        config = {"boards": {"task": {}}}
        sync.apply_changes(Board(FakePort()), queue, config=config)

        assert received["config"] == config


class TestParticipationIntentNaoParticipa:
    def test_nenhum_evento_de_participation_e_emitido(self, tmp_path, monkeypatch):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        logged_events = []

        def _capture(module, msg, *args, **kwargs):
            logged_events.append((module, msg, kwargs))

        monkeypatch.setattr(sync.log, "info", _capture)
        monkeypatch.setattr(sync.log, "warning", _capture)

        sync._apply_create_up(
            board_id, _create_up_item(body_path, board_id), Board(FakePort()),
            queue=ChangeQueue(), config={"boards": {"task": {}}},
        )

        markers = (
            "participation_classified", "participation_reconciled",
            "participation_reconcile_failed", "dispatch_blocked_unconfirmed_intent",
        )
        for module, msg, kwargs in logged_events:
            combined = f"{module} {msg} {kwargs}"
            for marker in markers:
                assert marker not in combined

    def test_board_of_issue_nao_resolve_board_distinto_sem_presenca(self):
        from src.core.sync import _board_of_issue

        config = {"boards": {"task": {}, "platform": "github"}}
        assert _board_of_issue("81", config) is None


class TestCreateUpIdentificadorDoItem:
    def test_item_com_id_em_vez_de_identifier_nao_chama_adapter(self, tmp_path):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "todo", "nova-tarefa-body.md",
            "Nova tarefa", "/blocked_by #76, #10",
        )

        port = FakePort()
        item = ChangeItem.of(SyncEvent.CREATE_UP, id=str(body_path), board=board_id)

        sync._apply_create_up(board_id, item, Board(port), queue=ChangeQueue(), config={})

        assert port.calls == []
        assert body_path.exists()
