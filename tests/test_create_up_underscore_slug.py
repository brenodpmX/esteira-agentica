"""Teste de regressão: body sem id numérico e com slug em underscore deve
disparar create-up.

Cenário do bug: uma issue criada localmente cujo arquivo segue o padrão de
slug do próprio sistema (`_slugify` gera underscores) fica com apenas UM hífen
no nome — o do sufixo `-body`. Ex.:

    decidir_destino_conteudo_divergente_hotfix27-body.md

A detecção antiga usava a heurística `body_file.name.count("-") >= 2` para
reconhecer "issue nova sem id", o que descartava silenciosamente esses nomes
(1 hífen < 2) e nunca gerava o create-up. A correção troca o `elif` por `else`:
todo `*-body.md` que NÃO começa com id numérico é uma issue local nova.
"""

import json

import pytest

from src.core.change_queue import ChangeQueue
from src.core.sync import detect_local_changes


def _write_snapshot(board_dir, issues):
    snapshot = {
        "board": {"architecture": "Debito Arquitetural"},
        "issues": issues,
        "last_sync": "2026-08-04T10:00:00Z",
        "last_board_update": "2026-08-04T10:00:00Z",
    }
    (board_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=2))


@pytest.fixture
def boards_dir(tmp_path, monkeypatch):
    """Board `debito` com um body de slug-underscore (1 hífen) e sem snapshot."""
    boards_base = tmp_path / ".pipe" / "boards"
    board_dir = boards_base / "debito"
    arch = board_dir / "architecture"
    arch.mkdir(parents=True)

    # Body sem id numérico, slug em underscore -> apenas 1 hífen (-body).
    body = arch / "decidir_destino_conteudo_divergente_hotfix27-body.md"
    body.write_text("# Decidir destino\n\nbody\n\n@---\n/labels git\n")

    # Snapshot vazio (nenhuma issue registrada ainda).
    _write_snapshot(board_dir, [])

    monkeypatch.setattr("src.core.sync.BOARDS_DIR", boards_base)
    monkeypatch.setattr("src.core.snapshot.BOARDS_DIR", boards_base)

    pipe_dir = tmp_path / ".pipe"
    monkeypatch.setattr("src.core.change_queue.PIPE_DIR", pipe_dir)
    monkeypatch.setattr("src.core.change_queue.QUEUE_FILE", pipe_dir / "changeQueue.json")

    return board_dir, body


def test_underscore_slug_body_triggers_create_up(boards_dir):
    """Slug em underscore (1 hífen) e sem id numérico gera exatamente 1 create-up."""
    board_dir, body = boards_dir

    # Pré-condição do bug: o nome tem apenas 1 hífen.
    assert body.name.count("-") == 1

    queue = ChangeQueue()
    detect_local_changes("debito", queue)

    item = queue.getNext()
    assert item is not None, "Esperava create-up para body sem id numérico"
    assert item.event == "create-up"
    assert item.id is None
    assert item.identifier == str(body)

    # Não deve haver um segundo item.
    queue.remove(item.uuid)
    assert queue.getNext() is None


def test_underscore_slug_body_already_known_is_not_recreated(boards_dir):
    """Se o body já está registrado no snapshot por body_path, não recria."""
    board_dir, body = boards_dir

    # Registrar a issue local (id=None) com o body_path já conhecido.
    _write_snapshot(board_dir, [
        {
            "id": None,
            "column": "architecture",
            "body_path": str(body),
            "body_mtime": str(body.stat().st_mtime),
            "status": "create-up",
        }
    ])

    queue = ChangeQueue()
    detect_local_changes("debito", queue)

    assert queue.getNext() is None, "Body já conhecido não deve gerar novo create-up"
