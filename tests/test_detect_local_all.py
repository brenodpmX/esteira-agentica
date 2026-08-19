"""Regressão: descoberta local (up) é global — roda em TODOS os boards a cada
ciclo, não só no board atual da rotação priorizada.

Motivação: um agente atuando em um board pode criar um artefato (ex.: issue
bloqueante) em OUTRO board. Se a descoberta local ficasse presa ao board da
rotação, boards de baixa prioridade seriam inanidos enquanto os de alta
prioridade têm atividade, atrasando a criação. `detect_local_all` desacopla
isso: descobre localmente em todos os boards; o sync remoto (`sync_remote_board`)
permanece por board.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.__main__ import detect_local_all
from src.core.change_queue import ChangeQueue


def _snapshot(board_dir, cols, issues=None):
    (board_dir / "snapshot.json").write_text(json.dumps({
        "board": cols,
        "issues": issues or [],
        "last_sync": None,
        "last_board_update": None,
    }))


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Dois boards: incidente (prioridade 0, vazio) e bug (prioridade 4, com body novo)."""
    boards_base = tmp_path / ".pipe" / "boards"

    inc = boards_base / "incidente" / "triagem"
    inc.mkdir(parents=True)
    _snapshot(boards_base / "incidente", {"triagem": "Triagem"})

    bug = boards_base / "bug" / "backlog"
    bug.mkdir(parents=True)
    # Body sem id numérico, slug em underscore (1 hífen), criado "por um agente".
    body = bug / "mr_130_em_conflito_com_epic_panorama_branches_desatualizado-body.md"
    body.write_text("# MR 130 em conflito\n\nbody\n\n@---\n/blocks #86\n/labels git\n")
    _snapshot(boards_base / "bug", {"backlog": "Backlog"})

    monkeypatch.setattr("src.core.sync.BOARDS_DIR", boards_base)
    monkeypatch.setattr("src.core.snapshot.BOARDS_DIR", boards_base)
    pipe_dir = tmp_path / ".pipe"
    monkeypatch.setattr("src.core.change_queue.PIPE_DIR", pipe_dir)
    monkeypatch.setattr("src.core.change_queue.QUEUE_FILE", pipe_dir / "changeQueue.json")

    config = {
        "boards": {
            "platform": "github",
            "incidente": {"priority": 0, "columns": {"triagem": {}}},
            "bug": {"priority": 4, "columns": {"backlog": {}}},
        }
    }
    return config, body


def test_detect_local_all_discovers_create_up_in_non_current_board(env):
    """create-up é gerado para o board `bug` mesmo sem ser o board da rotação."""
    config, body = env

    changed = detect_local_all(config)
    assert changed is True

    queue = ChangeQueue()
    items = []
    while True:
        it = queue.getNext()
        if it is None:
            break
        items.append(it)
        queue.remove(it.uuid)

    create_ups = [i for i in items if i.event == "create-up"]
    assert len(create_ups) == 1, f"esperava 1 create-up, obtive {[i.event for i in items]}"
    assert create_ups[0].board == "bug"
    assert create_ups[0].identifier == str(body)


def test_detect_local_all_no_changes_returns_false(env):
    """Sem arquivos novos, detect_local_all retorna False e não enfileira nada."""
    config, body = env
    # Registrar o body no snapshot do bug para que não seja "novo".
    _snapshot(
        Path(body).parents[1],
        {"backlog": "Backlog"},
        issues=[{
            "id": None,
            "column": "backlog",
            "body_path": str(body),
            "body_mtime": str(body.stat().st_mtime),
            "status": "create-up",
        }],
    )

    changed = detect_local_all(config)
    assert changed is False
    assert ChangeQueue().getNext() is None
