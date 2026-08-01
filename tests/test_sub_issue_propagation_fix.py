"""Testes da correção de duplicação e ausência de coluna em sub-issues propagadas.

Cobrem:
- remove_from_board (primitiva no port e adapter GitHub)
- Pós-hook em _add_sub_issue remove itens propagados sem Status
- Guard em _apply_create_down descarta eventos com coluna vazia e issue em outro board
- Fallback de coluna em _apply_change_down quando coluna remota vazia
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.github_board import GitHubBoardAdapter
from src.core.board import Board, BoardPort, Issue
from src.core.change_queue import ChangeQueue
from src.core.commands import IssueCommands


# ── Fake adapter que registra chamadas em vez de bater na rede ────────────────

class FakePort(BoardPort):
    def __init__(self):
        self.calls = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def list_issues_since(self, board_id, since): return []
    def get_issue(self, board_id, issue_id, fullsync=False):
        self.calls.append(("get_issue", issue_id, fullsync))
        return Issue(id=issue_id, title="", body="", column="")
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None):
        self.calls.append(("move_issue", issue_id, column, from_column))
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
    def remove_from_board(self, board_id, issue_id):
        self.calls.append(("remove_from_board", issue_id))


# ── Testes de remove_from_board ───────────────────────────────────────────────

def test_remove_from_board_port_default_not_implemented():
    """Port default deve logar warning (não levantar)."""
    port = FakePort()
    board = Board(port)
    # Não deve levantar (log warning já testado em outros testes).
    board.remove_from_board("b", "1")


def test_remove_from_board_github_adapter():
    """Adapter GitHub deve chamar GraphQL deleteProjectV2Item."""
    a = GitHubBoardAdapter()
    a._repo = "owner/repo"
    a._projects = {
        "b": {
            "project_id": "pid123",
            "status_field_id": "fid123",
            "options": {}
        }
    }

    gql_calls = []
    def fake_gql(query, **vars):
        gql_calls.append((query, vars))
        return {}

    a._gql = fake_gql
    a._find_item_id = lambda bid, iid: f"item_id_{iid}"

    a.remove_from_board("b", "42")

    # O GraphQL deve ser chamado com a mutation correta
    assert len(gql_calls) == 1
    query, vars = gql_calls[0]
    assert "deleteProjectV2Item" in query
    assert vars["pid"] == "pid123"
    assert vars["itemId"] == "item_id_42"


# ── Testes de pós-hook em _add_sub_issue ─────────────────────────────────────

def test_add_sub_issue_calls_remove_propagated():
    """Pós-hook deve chamar _remove_propagated_items_without_status após vincular."""
    a = GitHubBoardAdapter()
    a._repo = "owner/repo"
    a._projects = {"board1": {"project_id": "pid123"}}

    db_ids = {"42": 12345}
    def fake_get_issue_db_id(num):
        return db_ids.get(num)

    def fake_api(method, path, **fields):
        # Simular sucesso na criação do vínculo
        return ""

    def fake_remove_propagated(issue_num, exclude_board):
        # Registrar chamada para verificar
        a._remove_propagated_calls = getattr(a, "_remove_propagated_calls", [])
        a._remove_propagated_calls.append((issue_num, exclude_board))

    a._get_issue_db_id = fake_get_issue_db_id
    a._api = fake_api
    a._remove_propagated_items_without_status = fake_remove_propagated

    # Chamar com board_id
    a._add_sub_issue("10", "42", current_board_id="board1")

    # Verificar pós-hook chamado
    assert hasattr(a, "_remove_propagated_calls")
    assert ("42", "board1") in a._remove_propagated_calls


# ── Testes de _apply_create_down com guard de coluna vazia ───────────────────

def test_apply_create_down_coluna_vazia_issue_nova_cria_arquivo(monkeypatch, tmp_path):
    """Coluna vazia E issue nova (não em outro board) -> cria arquivo com fallback."""
    monkeypatch.chdir(tmp_path)

    from src.core import sync
    from src.core.snapshot import Snapshot

    port = FakePort()
    board = Board(port)

    # Criar snapshot
    snap = Snapshot("b").load()
    snap.board = {"todo": "col1"}
    snap.save()

    # Issue nova (não em snapshot de outro board) com coluna vazia
    issue = Issue(id="5", title="Teste", body="", column="", updated_at="2024-01-01T00:00:00Z")

    def fake_get_issue(bid, iid, fullsync=False):
        return issue

    board._port.get_issue = fake_get_issue

    queue = ChangeQueue()
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    # Deve criar arquivo (coluna vazia mas issue nova)
    sync._apply_create_down("b", item, board, queue)

    # Verificar que arquivo foi criado
    body_path = tmp_path / ".pipe" / "boards" / "b" / "todo" / "5-teste-body.md"
    assert body_path.exists()


def test_apply_create_down_coluna_vazia_issue_em_outro_board_descarta(monkeypatch, tmp_path):
    """Coluna vazia E issue já em outro board -> remove e descarta."""
    monkeypatch.chdir(tmp_path)

    from src.core import sync
    from src.core.snapshot import Snapshot

    port = FakePort()
    board = Board(port)

    # Criar snapshot com issue em outro board
    snap = Snapshot("outro_board").load()
    snap.issues.append({"id": "5", "column": "doing", "status": "ok"})
    snap.save()

    # Issue já existe em outro board com coluna vazia (propagação automática)
    issue = Issue(id="5", title="Teste", body="", column="", updated_at="2024-01-01T00:00:00Z")

    def fake_get_issue(bid, iid, fullsync=False):
        return issue

    board._port.get_issue = fake_get_issue

    queue = ChangeQueue()
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    # Deve remover do board e descartar (não criar arquivo)
    sync._apply_create_down("b", item, board, queue)

    # Verificar que remove_from_board foi chamado
    assert ("remove_from_board", "5") in port.calls
    # Verificar que NÃO criou arquivo
    body_path = tmp_path / ".pipe" / "boards" / "b" / "todo" / "5-teste-body.md"
    assert not body_path.exists()


def test_apply_create_down_coluna_vazia_issue_com_parent_descarta(monkeypatch, tmp_path):
    """Coluna vazia E issue com parent -> remove e descarta (propagação automática)."""
    monkeypatch.chdir(tmp_path)

    from src.core import sync
    from src.core.snapshot import Snapshot

    port = FakePort()
    board = Board(port)

    # Criar snapshot vazio (issue nova no board atual, mas tem parent)
    snap = Snapshot("b").load()
    snap.board = {"todo": "col1"}
    snap.save()

    # Issue com parent (propagação automática) e coluna vazia
    issue = Issue(id="5", title="Teste", body="", column="", parent="10",
                  updated_at="2024-01-01T00:00:00Z")

    def fake_get_issue(bid, iid, fullsync=False):
        return issue

    board._port.get_issue = fake_get_issue

    queue = ChangeQueue()
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    # Deve remover do board e descartar
    sync._apply_create_down("b", item, board, queue)

    # Verificar que remove_from_board foi chamado
    assert ("remove_from_board", "5") in port.calls
    # Verificar que NÃO criou arquivo
    body_path = tmp_path / ".pipe" / "boards" / "b" / "todo" / "5-teste-body.md"
    assert not body_path.exists()


# ── Testes de _apply_change_down com coluna vazia ─────────────────────────────

def test_apply_change_down_coluna_vazia_reaplica_snapshot(monkeypatch, tmp_path):
    """Coluna vazia no board -> reaplicar coluna do snapshot local."""
    monkeypatch.chdir(tmp_path)

    from src.core import sync
    from src.core.snapshot import Snapshot

    port = FakePort()
    board = Board(port)

    # Criar snapshot com issue na coluna "todo"
    snap = Snapshot("b").load()
    snap.issues.append({
        "id": "5", "column": "todo", "body_path": ".pipe/boards/b/todo/5-teste-body.md",
        "body_mtime": "1234", "updated_at": "2024-01-01T00:00:00Z", "status": "ok"
    })
    snap.save()

    # Criar arquivo na coluna INCORRETA (fazendo o move ser necessário)
    (tmp_path / ".pipe" / "boards" / "b" / "doing").mkdir(parents=True)
    body_path = tmp_path / ".pipe" / "boards" / "b" / "doing" / "5-teste-body.md"
    body_path.write_text("# Teste\n\n@---\n/labels test\n")

    # Issue com coluna vazia no board (propagação automática)
    issue = Issue(id="5", title="Teste", body="", column="", updated_at="2024-01-02T00:00:00Z")

    def fake_get_issue(bid, iid, fullsync=False):
        return issue

    board._port.get_issue = fake_get_issue

    queue = ChangeQueue()
    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_DOWN, id="5", board="b", fullsync=True)

    # Deve reaplicar coluna do snapshot (todo) e mover o arquivo de doing -> todo
    sync._apply_change_down("b", item, board, queue, config=None)

    # Verificar que move_issue foi chamado (coluna, from_column pode variar)
    move_calls = [c for c in port.calls if c[0] == "move_issue" and c[1] == "5" and c[2] == "todo"]
    assert len(move_calls) == 1


def test_apply_change_down_coluna_nula_reaplica_snapshot(monkeypatch, tmp_path):
    """Coluna None no board -> reaplicar coluna do snapshot local."""
    monkeypatch.chdir(tmp_path)

    from src.core import sync
    from src.core.snapshot import Snapshot

    port = FakePort()
    board = Board(port)

    # Criar snapshot com issue na coluna "todo"
    snap = Snapshot("b").load()
    snap.issues.append({
        "id": "5", "column": "todo", "body_path": ".pipe/boards/b/todo/5-teste-body.md",
        "body_mtime": "1234", "updated_at": "2024-01-01T00:00:00Z", "status": "ok"
    })
    snap.save()

    # Criar arquivo na coluna INCORRETA (fazendo o move ser necessário)
    (tmp_path / ".pipe" / "boards" / "b" / "doing").mkdir(parents=True)
    body_path = tmp_path / ".pipe" / "boards" / "b" / "doing" / "5-teste-body.md"
    body_path.write_text("# Teste\n\n@---\n/labels test\n")

    # Issue com coluna None no board
    issue = Issue(id="5", title="Teste", body="", column=None, updated_at="2024-01-02T00:00:00Z")

    def fake_get_issue(bid, iid, fullsync=False):
        return issue

    board._port.get_issue = fake_get_issue

    queue = ChangeQueue()
    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_DOWN, id="5", board="b", fullsync=True)

    # Deve reaplicar coluna do snapshot (todo) e mover o arquivo
    sync._apply_change_down("b", item, board, queue, config=None)

    # Verificar que move_issue foi chamado (coluna, from_column pode variar)
    move_calls = [c for c in port.calls if c[0] == "move_issue" and c[1] == "5" and c[2] == "todo"]
    assert len(move_calls) == 1


# ── Testes de detect_board_changes com coluna vazia ───────────────────────────

def test_detect_board_changes_coluna_vazia_detecta_diferenca():
    """Coluna vazia no remote != coluna no snapshot -> detecta como mudança."""
    from src.core import sync
    from src.core.snapshot import Snapshot

    port = FakePort()
    board = Board(port)

    # Issue no board com coluna vazia
    remote_issues = [Issue(id="5", title="Teste", body="", column="", updated_at="2024-01-02T00:00:00Z")]

    def fake_list_issues(board_id):
        return remote_issues

    def fake_get_issue(bid, iid, fullsync=False):
        if iid == "5":
            return Issue(id="5", title="Teste", body="", column="", updated_at="2024-01-02T00:00:00Z")
        return Issue(id=iid, title="", body="", column="")

    board._port.list_issues = fake_list_issues
    board._port.get_issue = fake_get_issue

    # Snapshot com issue tendo coluna "doing"
    snap = Snapshot("b").load()
    snap.issues.append({
        "id": "5", "column": "doing", "body_path": ".pipe/boards/b/doing/5-teste-body.md",
        "body_mtime": "1234", "updated_at": "2024-01-01T00:00:00Z", "status": "ok"
    })
    snap.save()

    queue = ChangeQueue()

    # Deve detectar mudança (coluna vazia != "doing")
    changed = board.detect_board_changes("b", snap, queue)

    # Verificar que ChangeDown foi enfileirado
    item = queue.getNext()
    assert item is not None
    assert item.id == "5"
    assert item.event == "change-down"
