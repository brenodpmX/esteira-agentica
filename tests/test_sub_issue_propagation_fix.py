"""Testes da correção para duplicação e ausência de coluna em sub-issues propagadas.

Cobrem os cinco itens do escopo técnico da issue #98:
1. Primitiva remove_from_board via mutation GraphQL deleteProjectV2Item
2. Pós-hook em _add_sub_issue remove item duplicado com Status vazio
3. Guard em _apply_create_down descarta evento com coluna vazia e issue já em outro board
4. Fallback de coluna no create_issue e _apply_change_down
5. detect_board_changes trata coluna vazia como divergência a corrigir
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.adapters.github_board import GitHubBoardAdapter
from src.core.board import Board, Issue, BoardPort
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot
from src.core.sync import _apply_create_down, _apply_change_down


class FakeBoardPort(BoardPort):
    """Fake port para testes sem dependência de API real."""
    
    def __init__(self):
        self._projects = {}
        self._issues = {}
        self._issues_by_number = {}
        self._items_by_issue = {}  # {board_id: {issue_id: {id, status}}}
        self._col_options = {}  # {board_id: [colunas]}
    
    def connect(self, config: dict) -> None:
        pass
    
    def check_access(self, config: dict) -> None:
        pass
    
    def sync_boards(self, boards: list[dict]) -> None:
        for board in boards:
            bid = board["id"]
            self._col_options[bid] = board.get("columns", [])
            self._projects[bid] = {
                "project_id": f"PID_{bid}",
                "status_field_id": f"FID_{bid}",
                "options": {col: f"OID_{col}" for col in board.get("columns", [])}
            }
    
    def list_issues(self, board_id: str) -> list[Issue]:
        return list(self._issues.get(board_id, {}).values())
    
    def list_issues_since(self, board_id: str, since: str) -> list[Issue]:
        return self.list_issues(board_id)
    
    def get_issue(self, board_id: str, issue_id: str, fullsync: bool = False) -> Issue:
        return self._issues.get(board_id, {}).get(issue_id)
    
    def create_issue(self, board_id: str, title: str, body: str, column: str) -> Issue:
        issue = Issue(
            id=str(len(self._issues.get(board_id, {})) + 100),
            title=title, body=body, column=column,
            updated_at="2026-08-01T00:00:00Z"
        )
        if board_id not in self._issues:
            self._issues[board_id] = {}
        self._issues[board_id][issue.id] = issue
        return issue
    
    def move_issue(self, board_id: str, issue_id: str, column: str, from_column: str = None) -> None:
        pass
    
    def update_issue(self, board_id: str, issue_id: str, title: str = None, body: str = None) -> None:
        pass
    
    def add_comment(self, board_id: str, issue_id: str, comment: str) -> None:
        pass
    
    def list_comments(self, board_id: str, issue_id: str) -> list[dict]:
        return []
    
    def close_issue(self, board_id: str, issue_id: str) -> None:
        pass
    
    def archive_issue(self, board_id: str, issue_id: str) -> None:
        pass
    
    def unarchive_issue(self, board_id: str, issue_id: str) -> None:
        pass
    
    def remove_from_board(self, board_id: str, issue_id: str) -> None:
        """Simula remoção de item do project."""
        pass
    
    def set_parent(self, board_id: str, issue_id: str, parent_id: str | None, known_current=None) -> None:
        pass
    
    def set_children(self, board_id: str, issue_id: str, children_ids: list[str], known_current: list[str] | None = None) -> None:
        pass
    
    def set_blocked_by(self, board_id: str, issue_id: str, blocker_ids: list[str], known_current: list[str] | None = None) -> None:
        pass
    
    def set_blocks(self, board_id: str, issue_id: str, blocked_ids: list[str], known_current: list[str] | None = None) -> None:
        pass
    
    def add_issue(self, board_id: str, issue: Issue) -> None:
        if board_id not in self._issues:
            self._issues[board_id] = {}
        self._issues[board_id][issue.id] = issue


class FakeBoard:
    """Wrapper fake para testes - delega para port."""
    def __init__(self, port):
        self._port = port
    
    def get_issue(self, board_id: str, issue_id: str, fullsync: bool = False) -> Issue:
        return self._port.get_issue(board_id, issue_id, fullsync)
    
    def list_comments(self, board_id: str, issue_id: str) -> list[dict]:
        return self._port.list_comments(board_id, issue_id)
    
    def remove_from_board(self, board_id: str, issue_id: str) -> None:
        return self._port.remove_from_board(board_id, issue_id)
    
    def archive_issue(self, board_id: str, issue_id: str) -> None:
        return self._port.archive_issue(board_id, issue_id)
    
    def unarchive_issue(self, board_id: str, issue_id: str) -> None:
        return self._port.unarchive_issue(board_id, issue_id)


# ── Testes do item 3: Guard em _apply_create_down ─────────────────────────────

def test_apply_create_down_coluna_vazia_descarta_se_pertence_a_outro_board(tmp_path, monkeypatch):
    """Guard em _apply_create_down: se coluna vazia E issue já pertence a outro board, descarta."""
    monkeypatch.chdir(tmp_path)
    
    # Criar structure de pastas
    board_dir = tmp_path / ".pipe/boards/task"
    board_dir.mkdir(parents=True)
    
    # Criar snapshot do board 'task' vazio
    snap = Snapshot("task")
    snap.board = {"todo": "To Do", "doing": "Doing", "done": "Done"}
    snap.issues = []
    snap.save()
    
    # Criar board 'story' com a mesma issue #123
    story_board_dir = tmp_path / ".pipe/boards/story"
    story_board_dir.mkdir(parents=True)
    (story_board_dir / "backlog").mkdir(parents=True)
    story_snap = Snapshot("story")
    story_snap.board = {"backlog": "Backlog", "planning": "Planning"}
    story_snap.issues = [{
        "id": "123",
        "column": "backlog",
        "body_path": str(story_board_dir / "backlog" / "123-teste-body.md"),
        "body_mtime": "1.0",
        "updated_at": "2026-08-01T00:00:00Z",
        "status": "ok",
        "parent": "456",
    }]
    story_snap.save()
    (story_board_dir / "backlog" / "123-teste-body.md").write_text("# Teste\n\nbody\n")
    
    # Fake port com issue #123 em 'task' com coluna vazia (propagada sem Status)
    port = FakeBoardPort()
    port.add_issue("task", Issue(id="123", title="Teste", body="body", column=""))
    port.add_issue("task", Issue(id="124", title="Outra", body="body", column="todo"))
    
    # Criar Board wrapper
    board_obj = FakeBoard(port)
    
    # Executar _apply_create_down
    _apply_create_down("task", type('obj', (object,), {
        "id": "123",
        "event": "create-down",
        "fullsync": False,
    })(), board_obj)
    
    # Verificar que NÃO criou arquivos para #123 em 'task'
    todo_dir = board_dir / "todo"
    assert not todo_dir.exists() or not any(todo_dir.glob("123-*"))


def test_apply_create_down_coluna_vazia_cria_se_issue_nova(tmp_path, monkeypatch):
    """Guard em _apply_create_down: se coluna vazia mas issue é nova (sem parent/outro board), cria com fallback."""
    monkeypatch.chdir(tmp_path)
    
    board_dir = tmp_path / ".pipe/boards/task"
    board_dir.mkdir(parents=True)
    
    snap = Snapshot("task")
    snap.board = {"todo": "To Do", "doing": "Doing", "done": "Done"}
    snap.issues = []
    snap.save()
    
    # Fake port com issue #123 em 'task' com coluna vazia (nova issue)
    port = FakeBoardPort()
    port.add_issue("task", Issue(id="123", title="Teste", body="body", column=""))
    port.add_issue("task", Issue(id="124", title="Outra", body="body", column="todo"))
    
    # Criar Board wrapper
    board_obj = FakeBoard(port)
    
    # Executar _apply_create_down
    _apply_create_down("task", type('obj', (object,), {
        "id": "123",
        "event": "create-down",
        "fullsync": False,
    })(), board_obj)
    
    # Verificar que criou arquivos (fallback para primeira coluna)
    todo_dir = board_dir / "todo"
    assert todo_dir.exists()
    assert any(todo_dir.glob("123-*"))


# ── Teste da interação entre item 3 (guard create-down) e item 4 (fallback
#    change-down): garante que o guard, ao já descartar o evento e chamar
#    remove_from_board no create-down, impede que a issue chegue a ter um
#    old_col nesse board — logo o fallback de _apply_change_down nunca reaplica
#    uma coluna para um item que deveria estar removido do project (ponto 3 do
#    code review do PR #103).

def test_guard_create_down_impede_fallback_circular_do_change_down(tmp_path, monkeypatch):
    """Uma issue propagada sem coluna (com parent) é descartada no create-down
    e nunca ganha entrada no snapshot deste board — portanto um change-down
    subsequente para o mesmo id não encontra old_col e não reaplica coluna,
    não reintroduzindo o item removido pelo pós-hook."""
    monkeypatch.chdir(tmp_path)

    board_dir = tmp_path / ".pipe/boards/task"
    board_dir.mkdir(parents=True)
    snap = Snapshot("task")
    snap.board = {"todo": "To Do", "doing": "Doing", "done": "Done"}
    snap.issues = []
    snap.save()

    # Issue #123 já pertence a outro board (story) — cenário de propagação.
    story_board_dir = tmp_path / ".pipe/boards/story"
    story_board_dir.mkdir(parents=True)
    (story_board_dir / "backlog").mkdir(parents=True)
    story_snap = Snapshot("story")
    story_snap.board = {"backlog": "Backlog"}
    story_snap.issues = [{
        "id": "123",
        "column": "backlog",
        "body_path": str(story_board_dir / "backlog" / "123-teste-body.md"),
        "body_mtime": "1.0",
        "updated_at": "2026-08-01T00:00:00Z",
        "status": "ok",
        "parent": "456",
    }]
    story_snap.save()
    (story_board_dir / "backlog" / "123-teste-body.md").write_text("# Teste\n\nbody\n")

    port = FakeBoardPort()
    port.add_issue("task", Issue(id="123", title="Teste", body="body", column=""))

    removed = []
    original_remove = port.remove_from_board
    def tracking_remove(board_id, issue_id):
        removed.append((board_id, issue_id))
        return original_remove(board_id, issue_id)
    port.remove_from_board = tracking_remove

    board_obj = FakeBoard(port)

    _apply_create_down("task", type('obj', (object,), {
        "id": "123", "event": "create-down", "fullsync": False,
    })(), board_obj)

    # Guard descartou e chamou remove_from_board — sem arquivos nem snapshot local.
    assert removed == [("task", "123")]
    todo_dir = board_dir / "todo"
    assert not todo_dir.exists() or not any(todo_dir.glob("123-*"))
    snap_after = Snapshot("task").load()
    assert snap_after.issue("123") is None, (
        "Issue descartada pelo guard não deve ter entrada no snapshot deste "
        "board — garante que um change-down futuro não encontre old_col e "
        "não reaplique coluna (fallback circular do ponto 3 do code review)"
    )



def _make_adapter(projects: dict) -> GitHubBoardAdapter:
    adapter = GitHubBoardAdapter()
    adapter._repo = "owner/repo"
    adapter._projects = projects
    return adapter


def test_create_issue_usa_fallback_quando_coluna_invalida():
    """create_issue: coluna inexistente nas opções do project cai para a primeira
    coluna configurada e emite warning (item 4 do escopo, github_board.py)."""
    adapter = _make_adapter({
        "task": {
            "project_id": "PID_task",
            "status_field_id": "FID_task",
            "options": {"todo": "OID_todo", "doing": "OID_doing"},
        }
    })

    gh_calls = []
    gql_calls = []

    def mock_gh(*args, **kwargs):
        gh_calls.append(args)
        # 'gh issue create' retorna a URL da issue criada
        return "https://github.com/owner/repo/issues/42"

    def mock_gql(query, **kwargs):
        gql_calls.append((query, kwargs))
        if "addProjectV2ItemById" in query:
            return {"addProjectV2ItemById": {"item": {"id": "ITEM_1"}}}
        if "updateProjectV2ItemFieldValue" in query:
            return {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "ITEM_1"}}}
        # query de node_id/updatedAt
        return {"repository": {"issue": {"id": "NODE_1", "updatedAt": "2026-08-01T00:00:00Z"}}}

    with patch.object(adapter, "_gh", side_effect=mock_gh), \
         patch.object(adapter, "_gql", side_effect=mock_gql), \
         patch("src.adapters.github_board.log") as mock_log:

        issue = adapter.create_issue("task", "Título", "body", column="coluna_inexistente")

    # Deve ter aplicado o fallback para a primeira coluna configurada
    assert issue.column == "todo"
    # Deve ter movido o item usando a option_id da coluna de fallback
    move_calls = [c for c in gql_calls if "updateProjectV2ItemFieldValue" in c[0]]
    assert move_calls, "Deveria ter chamado updateProjectV2ItemFieldValue com o fallback"
    assert move_calls[0][1]["optionId"] == "OID_todo"
    # Deve ter emitido warning sobre a coluna inválida
    assert mock_log.warning.called


def test_create_issue_usa_coluna_informada_quando_valida():
    """create_issue: quando a coluna existe nas opções, usa-a diretamente (sem fallback)."""
    adapter = _make_adapter({
        "task": {
            "project_id": "PID_task",
            "status_field_id": "FID_task",
            "options": {"todo": "OID_todo", "doing": "OID_doing"},
        }
    })

    def mock_gh(*args, **kwargs):
        return "https://github.com/owner/repo/issues/43"

    def mock_gql(query, **kwargs):
        if "addProjectV2ItemById" in query:
            return {"addProjectV2ItemById": {"item": {"id": "ITEM_2"}}}
        if "updateProjectV2ItemFieldValue" in query:
            return {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "ITEM_2"}}}
        return {"repository": {"issue": {"id": "NODE_2", "updatedAt": "2026-08-01T00:00:00Z"}}}

    with patch.object(adapter, "_gh", side_effect=mock_gh), \
         patch.object(adapter, "_gql", side_effect=mock_gql), \
         patch("src.adapters.github_board.log") as mock_log:

        issue = adapter.create_issue("task", "Título", "body", column="doing")

    assert issue.column == "doing"
    assert not mock_log.warning.called


# ── Testes do item 5: detect_board_changes trata coluna vazia como divergência ─

def test_detect_board_changes_trata_coluna_vazia_como_divergencia(tmp_path, monkeypatch):
    """detect_board_changes: issue remota sem Status (coluna vazia) deve gerar
    change-down mesmo quando o snapshot conhece uma coluna — não deve ser
    ignorada por causa da condição `issue.column and ...` (item 5 do escopo)."""
    monkeypatch.chdir(tmp_path)

    port = FakeBoardPort()
    port.sync_boards([{"id": "task", "columns": ["todo", "doing", "done"]}])
    port.add_issue("task", Issue(
        id="123", title="Teste", body="body", column="",
        updated_at="2026-08-01T00:00:00Z",
    ))

    board = Board(port)

    snap = Snapshot("task")
    snap.board = {"todo": "To Do", "doing": "Doing", "done": "Done"}
    snap.issues = [{
        "id": "123",
        "column": "todo",
        "updated_at": "2026-08-01T00:00:00Z",
        "status": "ok",
    }]
    snap.save()

    queue = ChangeQueue()

    added = board.detect_board_changes("task", snap, queue)

    assert added == 1, "Coluna remota vazia divergindo da conhecida deve gerar 1 mudança"
    queued = queue._read()
    assert any(
        item.id == "123" and item.event == "change-down"
        for item in queued
    ), "Deveria enfileirar change-down para a issue com coluna vazia"


# ── Testes do item 2: Pós-hook _remove_propagated_without_column (adapter real) ─

def _project_items_response(nodes: list) -> dict:
    return {
        "repository": {
            "issue": {
                "projectItems": {"nodes": nodes}
            }
        }
    }


def _item_node(item_id: str, project_id: str, status: str | None) -> dict:
    field_values = []
    if status is not None:
        field_values.append({
            "field": {"name": "Status"},
            "name": status,
        })
    return {
        "id": item_id,
        "project": {"id": project_id},
        "fieldValues": {"nodes": field_values},
    }


def test_remove_propagated_without_column_remove_item_com_status_vazio():
    """Pós-hook real: item propagado sem Status (campo Status ausente/vazio) é
    removido do project via mutation deleteProjectV2Item, usando GraphQL —
    não o endpoint REST inexistente que causou a reincidência (#98/PR #103)."""
    adapter = _make_adapter({})

    response = _project_items_response([
        _item_node("ITEM_propagado", "PID_pai", status=None),
    ])

    gql_calls = []

    def mock_gql(query, **kwargs):
        gql_calls.append((query, kwargs))
        if "deleteProjectV2Item" in query:
            return {"deleteProjectV2Item": {"deletedItemId": "ITEM_propagado"}}
        return response

    with patch.object(adapter, "_gql", side_effect=mock_gql), \
         patch.object(adapter, "_gh") as mock_gh:

        adapter._remove_propagated_without_column("999")

    # Nunca deve chamar _gh (endpoint REST inexistente removido)
    assert not mock_gh.called, "Não deve usar _gh/REST — apenas GraphQL"

    delete_calls = [c for c in gql_calls if "deleteProjectV2Item" in c[0]]
    assert len(delete_calls) == 1, "Deveria remover exatamente o item sem Status"
    assert delete_calls[0][1]["pid"] == "PID_pai"
    assert delete_calls[0][1]["itemId"] == "ITEM_propagado"


def test_remove_propagated_without_column_preserva_item_com_status():
    """Pós-hook real: sub-issue legítima do mesmo board, já com Status/coluna
    definida, NÃO deve ser removida (discriminador de segurança do item 2)."""
    adapter = _make_adapter({})

    response = _project_items_response([
        _item_node("ITEM_legitimo", "PID_mesmo_board", status="Doing"),
    ])

    gql_calls = []

    def mock_gql(query, **kwargs):
        gql_calls.append((query, kwargs))
        return response

    with patch.object(adapter, "_gql", side_effect=mock_gql), \
         patch.object(adapter, "_gh") as mock_gh:

        adapter._remove_propagated_without_column("999")

    assert not mock_gh.called
    delete_calls = [c for c in gql_calls if "deleteProjectV2Item" in c[0]]
    assert delete_calls == [], "Item com Status definido não deve ser removido"


def test_remove_propagated_without_column_trata_multiplos_projects():
    """Pós-hook real: entre vários projectItems, remove apenas os sem Status,
    preservando os que já têm coluna — mesmo dentro da mesma chamada."""
    adapter = _make_adapter({})

    response = _project_items_response([
        _item_node("ITEM_legitimo", "PID_mesmo_board", status="Doing"),
        _item_node("ITEM_propagado", "PID_pai", status=None),
    ])

    gql_calls = []

    def mock_gql(query, **kwargs):
        gql_calls.append((query, kwargs))
        if "deleteProjectV2Item" in query:
            return {"deleteProjectV2Item": {"deletedItemId": kwargs.get("itemId")}}
        return response

    with patch.object(adapter, "_gql", side_effect=mock_gql):
        adapter._remove_propagated_without_column("999")

    delete_calls = [c for c in gql_calls if "deleteProjectV2Item" in c[0]]
    assert len(delete_calls) == 1
    assert delete_calls[0][1]["itemId"] == "ITEM_propagado"
