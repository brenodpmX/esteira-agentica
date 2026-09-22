"""Testes do _auto_advance: mover arquivos + atualizar snapshot + enfileirar change-up.

Regressão do bug em que o auto-advance movia os arquivos da coluna todo para a
próxima coluna mas NÃO atualizava o snapshot nem informava a ChangeQueue,
fazendo o keep_task refazer um auto-advance no-op a cada ciclo e nunca
selecionar tarefas prontas.
"""

import json
from pathlib import Path

import pytest

from src.__main__ import _auto_advance
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot


@pytest.fixture
def task_board(tmp_path, monkeypatch):
    """Board 'task' com a issue #39 em backlog (3 arquivos) e snapshot."""
    monkeypatch.chdir(tmp_path)

    board_dir = Path(".pipe/boards/task")
    backlog = board_dir / "backlog"
    backlog.mkdir(parents=True)

    stem = "39-testes_automatizados"
    (backlog / f"{stem}-body.md").write_text("# Testes automatizados\n\nbody\n")
    (backlog / f"{stem}-history.md").write_text("hist\n")
    (backlog / f"{stem}-addcomment.md").write_text("")

    snapshot = {
        "board": {"backlog": "Backlog", "planning-poker": "Planning Poker"},
        "issues": [
            {
                "id": "39",
                "column": "backlog",
                "body_path": f".pipe/boards/task/backlog/{stem}-body.md",
                "body_mtime": "1.0",
                "updated_at": "2026-07-21T20:50:28Z",
                "status": "ok",
                "labels": [],
                "parent": None,
                "children": [],
                "blocked_by": [],
                "blocks": [],
                "archived": False,
                "state": "open",
            }
        ],
        "last_sync": None,
        "last_board_update": "2026-07-21T20:50:28Z",
    }
    (board_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=2))

    return board_dir, stem


def test_auto_advance_moves_files(task_board):
    board_dir, stem = task_board
    snap = Snapshot("task").load()
    issue = snap.issue("39")

    _auto_advance("task", issue, "planning-poker", snap)

    planning = board_dir / "planning-poker"
    for suffix in ("-body.md", "-history.md", "-addcomment.md"):
        assert (planning / f"{stem}{suffix}").exists(), f"faltou mover {suffix}"
        assert not (board_dir / "backlog" / f"{stem}{suffix}").exists(), \
            f"arquivo {suffix} não deveria permanecer no backlog"


def test_auto_advance_updates_snapshot(task_board):
    board_dir, stem = task_board
    snap = Snapshot("task").load()
    issue = snap.issue("39")

    _auto_advance("task", issue, "planning-poker", snap)

    # Recarrega do disco para confirmar persistência
    reloaded = Snapshot("task").load().issue("39")
    assert reloaded["status"] == "change-up"
    assert reloaded["body_path"] == f".pipe/boards/task/planning-poker/{stem}-body.md"
    # A coluna permanece a de origem para o apply_change_up propagar o movimento
    assert reloaded["column"] == "backlog"


def test_auto_advance_enqueues_change_up(task_board):
    snap = Snapshot("task").load()
    issue = snap.issue("39")

    _auto_advance("task", issue, "planning-poker", snap)

    item = ChangeQueue().getNext()
    assert item is not None, "esperava um item enfileirado"
    assert item.id == "39"
    assert item.board == "task"
    assert item.event == "change-up"


def test_auto_advance_change_up_is_deduplicated(task_board):
    """Chamar auto-advance e depois detectar a mesma mudança não duplica a fila."""
    snap = Snapshot("task").load()
    issue = snap.issue("39")

    _auto_advance("task", issue, "planning-poker", snap)

    # Segunda tentativa de enfileirar o mesmo alvo deve deduplicar
    from src.core.board import ChangeItem, SyncEvent
    added = ChangeQueue().add(ChangeItem.of(SyncEvent.CHANGE_UP, id="39", board="task"))
    assert added is False

    queue = ChangeQueue()
    first = queue.getNext()
    queue.remove(first.uuid)
    assert queue.getNext() is None, "não deveria haver item duplicado"


# ── keep_task: sentinela AUTO_ADVANCED vs None vs task ────────────────────────

_CONFIG = {
    "boards": {
        "task": {
            "todo": "backlog",
            "columns": {
                "backlog": {"name": "Backlog", "change": {"advance": "planning-poker"}},
                "planning-poker": {
                    "name": "Planning Poker",
                    "agent": "tech-lead",
                    "change": {"advance": "casos-de-teste"},
                },
            },
        }
    }
}


def _add_planning_issue(board_dir, issue_id, stem, updated_at):
    """Adiciona uma issue elegível em planning-poker (arquivo + snapshot)."""
    planning = board_dir / "planning-poker"
    planning.mkdir(parents=True, exist_ok=True)
    body = planning / f"{stem}-body.md"
    body.write_text("# Task pronta\n\nsem comandos de bloqueio\n")
    (planning / f"{stem}-addcomment.md").write_text("")

    snap_file = board_dir / "snapshot.json"
    data = json.loads(snap_file.read_text())
    data["issues"].append({
        "id": issue_id,
        "column": "planning-poker",
        "body_path": str(body),
        "body_mtime": "1.0",
        "updated_at": updated_at,
        "status": "ok",
        "labels": [], "parent": None, "children": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
    })
    snap_file.write_text(json.dumps(data, indent=2))


def test_keep_task_returns_auto_advanced_for_todo(task_board):
    """Só há issue no backlog (todo) → keep_task faz auto-advance e sinaliza AUTO_ADVANCED."""
    from src.__main__ import keep_task, AUTO_ADVANCED

    result = keep_task("task", _CONFIG)

    assert result is AUTO_ADVANCED


def test_keep_task_returns_none_when_empty(task_board):
    """Sem issues elegíveis nem no todo → None (loop avança de board)."""
    from src.__main__ import keep_task

    # Remove a única issue (39) do snapshot
    snap = Snapshot("task").load()
    snap.issues = []
    snap.save()

    assert keep_task("task", _CONFIG) is None


def test_keep_task_prefers_advanced_column_over_todo(task_board):
    """Com issue pronta em planning-poker e uma no backlog, retorna a de planning-poker.

    Valida a varredura coluna a coluna (última primeiro) + a distinção de retorno:
    NÃO deve fazer auto-advance do backlog enquanto houver tarefa pronta adiante.
    """
    from src.__main__ import keep_task, AUTO_ADVANCED

    board_dir, _ = task_board
    _add_planning_issue(board_dir, "40", "40-task_pronta", "2026-07-22T14:00:00Z")

    result = keep_task("task", _CONFIG)

    assert result is not AUTO_ADVANCED and result is not None
    assert result["issue"]["id"] == "40"
    assert result["col_id"] == "planning-poker"


def _add_backlog_issue(board_dir, issue_id, stem, updated_at, blocked_by=None):
    """Adiciona uma issue no backlog (todo). Se blocked_by, injeta o comando no body."""
    backlog = board_dir / "backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    body = backlog / f"{stem}-body.md"
    text = f"# Issue {issue_id}\n\nconteudo\n"
    if blocked_by:
        refs = ", ".join(f"#{b}" for b in blocked_by)
        text += f"\n@---\n/blocked_by {refs}\n"
    body.write_text(text)
    (backlog / f"{stem}-addcomment.md").write_text("")

    snap_file = board_dir / "snapshot.json"
    data = json.loads(snap_file.read_text())
    data["issues"].append({
        "id": issue_id,
        "column": "backlog",
        "body_path": str(body),
        "body_mtime": "1.0",
        "updated_at": updated_at,
        "status": "ok",
        "labels": [], "parent": None, "children": [],
        "blocked_by": list(blocked_by or []), "blocks": [],
        "archived": False, "state": "open",
    })
    snap_file.write_text(json.dumps(data, indent=2))


def test_keep_task_skips_blocked_todo_and_advances_blocker(task_board):
    """Regressão: auto-advance do todo deve respeitar bloqueios.

    Cenário: duas issues no backlog (todo). A #39 (mais antiga, primeira na
    ordenação) está bloqueada por #41 via /blocked_by; #41 (mais nova) é a
    bloqueante e não está bloqueada. O auto-advance deve PULAR a bloqueada #39
    e avançar a bloqueante #41 — preservando a fila ordenada por bloqueios.
    """
    from src.__main__ import keep_task, AUTO_ADVANCED

    board_dir, stem39 = task_board
    # Torna a #39 (mais antiga) bloqueada por #41.
    body39 = board_dir / "backlog" / f"{stem39}-body.md"
    body39.write_text(
        "# Testes automatizados\n\nbody\n\n@---\n/blocked_by #41\n"
    )
    # Adiciona a bloqueante #41 (mais nova), sem bloqueio.
    _add_backlog_issue(board_dir, "41", "41-bloqueante", "2026-07-22T10:00:00Z")

    result = keep_task("task", _CONFIG)
    assert result is AUTO_ADVANCED

    snap = Snapshot("task").load()
    advanced = snap.issue("41")
    blocked = snap.issue("39")
    # A bloqueante #41 avançou (change-up, agora em planning-poker).
    assert advanced["status"] == "change-up"
    assert advanced["body_path"] == ".pipe/boards/task/planning-poker/41-bloqueante-body.md"
    # A bloqueada #39 permanece parada no backlog.
    assert blocked["status"] == "ok"
    assert blocked["column"] == "backlog"


def test_keep_task_none_when_only_blocked_todo(task_board):
    """Se a única issue do todo está bloqueada, não há auto-advance → None."""
    from src.__main__ import keep_task

    board_dir, stem39 = task_board
    body39 = board_dir / "backlog" / f"{stem39}-body.md"
    body39.write_text("# Testes automatizados\n\nbody\n\n@---\n/blocked_by #99\n")

    assert keep_task("task", _CONFIG) is None


def test_keep_task_todo_autoadvance_respects_age_order(task_board):
    """O auto-advance do todo usa a MESMA ordem de idade do keep_task.

    Duas issues não bloqueadas no backlog (todo): a mais antiga deve avançar
    primeiro (mesma ordenação por idade aplicada às colunas com agente). A #39
    (2026-07-21) é mais antiga que a #42 (2026-07-25) → #39 avança, #42 espera.
    """
    from src.__main__ import keep_task, AUTO_ADVANCED

    board_dir, stem39 = task_board
    _add_backlog_issue(board_dir, "42", "42-mais_nova", "2026-07-25T10:00:00Z")

    result = keep_task("task", _CONFIG)
    assert result is AUTO_ADVANCED

    snap = Snapshot("task").load()
    # A mais antiga (#39) avançou; a mais nova (#42) permanece no backlog.
    assert snap.issue("39")["status"] == "change-up"
    assert snap.issue("39")["column"] == "backlog"  # coluna-origem preservada p/ propagar
    assert snap.issue("39")["body_path"].startswith(".pipe/boards/task/planning-poker/")
    assert snap.issue("42")["status"] == "ok"
    assert snap.issue("42")["column"] == "backlog"

