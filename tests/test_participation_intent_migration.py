"""Testes — Migrar snapshots legados sem `participation_intent` no full sync
de startup (task #257, story #245).

Cobrem os casos CT-01..CT-07 de
`doc/quality/integridade-de-issues-entre-boards/casos-de-teste/test-cases-migrar-snapshots-legados-participation-intent.md`.

A função sob teste (`migrate_legacy_participation_intent`) é pura em I/O de
rede: só lê/escreve snapshots locais (`.pipe/boards/<board_id>/snapshot.json`),
sem tocar em `Board`/`BoardPort`/adapter.
"""

import json
from pathlib import Path

import pytest

from src.core.participation_migration import migrate_legacy_participation_intent
from src.core.snapshot import Snapshot


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures / helpers
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def boards_env(tmp_path, monkeypatch):
    """Isola BOARDS_DIR em tmp_path e troca o cwd.

    `BOARDS_DIR` é patchado tanto em `src.core.snapshot` (fonte) quanto no
    módulo da migração, caso ele importe o símbolo diretamente.
    """
    monkeypatch.chdir(tmp_path)
    boards_base = tmp_path / ".pipe" / "boards"
    boards_base.mkdir(parents=True)
    monkeypatch.setattr("src.core.snapshot.BOARDS_DIR", boards_base)
    return tmp_path


def _config(*board_ids: str) -> dict:
    """Config mínimo: platform + N boards configurados com colunas."""
    cfg = {"boards": {"platform": "github"}}
    for bid in board_ids:
        cfg["boards"][bid] = {"columns": {"backlog": {"name": "Backlog"}}}
    return cfg


def _write_snapshot(board_id: str, issues: list[dict]) -> None:
    snap = Snapshot(board_id)
    snap.issues = issues
    snap.save()


def _load_issue(board_id: str, issue_id: str) -> dict | None:
    return Snapshot(board_id).load().issue(issue_id)


# ══════════════════════════════════════════════════════════════════════════════
# CT-01 — Issue em board único legado recebe `origin`
# ══════════════════════════════════════════════════════════════════════════════

def test_ct01_single_board_legacy_becomes_origin(boards_env):
    config = _config("task", "bug")
    _write_snapshot("task", [{"id": "100", "column": "backlog"}])
    _write_snapshot("bug", [])

    migrate_legacy_participation_intent(config)

    issue = _load_issue("task", "100")
    assert issue["participation_intent"] == "origin"
    # Nenhuma outra chave removida/alterada.
    assert issue["column"] == "backlog"


# ══════════════════════════════════════════════════════════════════════════════
# CT-02 — Mesma issue em dois boards configurados legados recebe `unresolved`
# ══════════════════════════════════════════════════════════════════════════════

def test_ct02_duplicate_across_configured_boards_becomes_unresolved(boards_env):
    config = _config("task", "bug")
    _write_snapshot("task", [{"id": "200", "column": "backlog"}])
    _write_snapshot("bug", [{"id": "200", "column": "backlog"}])

    migrate_legacy_participation_intent(config)

    assert _load_issue("task", "200")["participation_intent"] == "unresolved"
    assert _load_issue("bug", "200")["participation_intent"] == "unresolved"


# ══════════════════════════════════════════════════════════════════════════════
# CT-03 — Entrada já preenchida não é sobrescrita (mesmo em duplicidade)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct03_existing_value_not_overwritten_authorized(boards_env):
    config = _config("task", "bug")
    _write_snapshot("task", [{"id": "300", "column": "backlog",
                              "participation_intent": "authorized"}])
    _write_snapshot("bug", [{"id": "300", "column": "backlog"}])

    migrate_legacy_participation_intent(config)

    # Board A: mantém "authorized" (não sobrescrito).
    assert _load_issue("task", "300")["participation_intent"] == "authorized"
    # Board B (não migrado): recebe "unresolved" (A conta como presença).
    assert _load_issue("bug", "300")["participation_intent"] == "unresolved"


def test_ct03_existing_none_not_overwritten(boards_env):
    """Campo presente com valor None explícito NÃO deve ser tocado.

    Caso-guarda: exige `"participation_intent" not in issue_dict`, nunca
    `.get(...)`.
    """
    config = _config("task", "bug")
    _write_snapshot("task", [{"id": "301", "column": "backlog",
                              "participation_intent": None}])
    _write_snapshot("bug", [{"id": "301", "column": "backlog"}])

    migrate_legacy_participation_intent(config)

    issue_a = _load_issue("task", "301")
    assert "participation_intent" in issue_a
    assert issue_a["participation_intent"] is None
    # Board B (não migrado) recebe "unresolved".
    assert _load_issue("bug", "301")["participation_intent"] == "unresolved"


# ══════════════════════════════════════════════════════════════════════════════
# CT-04 — Entrada em board NÃO configurado não conta como duplicidade → origin
# ══════════════════════════════════════════════════════════════════════════════

def test_ct04_unconfigured_board_not_counted(boards_env):
    # 'task' configurado; 'removido' NÃO está em config["boards"].
    config = _config("task")
    _write_snapshot("task", [{"id": "400", "column": "backlog"}])
    _write_snapshot("removido", [{"id": "400", "column": "backlog"}])

    migrate_legacy_participation_intent(config)

    # task: presença em único board configurado → origin.
    assert _load_issue("task", "400")["participation_intent"] == "origin"
    # board não configurado: não é iterado/gravado.
    removido = _load_issue("removido", "400")
    assert "participation_intent" not in removido


# ══════════════════════════════════════════════════════════════════════════════
# CT-05 — Idempotência: segunda execução não altera nada
# ══════════════════════════════════════════════════════════════════════════════

def test_ct05_idempotent(boards_env):
    config = _config("task", "bug")
    _write_snapshot("task", [
        {"id": "100", "column": "backlog"},          # origin
        {"id": "200", "column": "backlog"},          # unresolved (dup)
    ])
    _write_snapshot("bug", [{"id": "200", "column": "backlog"}])
    _write_snapshot("removido", [{"id": "400", "column": "backlog"}])

    migrate_legacy_participation_intent(config)

    def _snap_bytes(board_id):
        return (boards_env / ".pipe" / "boards" / board_id / "snapshot.json").read_bytes()

    after_first = {b: _snap_bytes(b) for b in ("task", "bug", "removido")}

    migrate_legacy_participation_intent(config)

    after_second = {b: _snap_bytes(b) for b in ("task", "bug", "removido")}
    assert after_second == after_first


# ══════════════════════════════════════════════════════════════════════════════
# CT-06 — Salva apenas snapshots efetivamente alterados
# ══════════════════════════════════════════════════════════════════════════════

def test_ct06_saves_only_changed_snapshots(boards_env, monkeypatch):
    config = _config("task", "bug")
    _write_snapshot("task", [{"id": "500", "column": "backlog"}])  # será alterado
    _write_snapshot("bug", [{"id": "600", "column": "backlog",
                             "participation_intent": "origin"}])   # nada a fazer

    saved_boards = []
    original_save = Snapshot.save

    def _spy_save(self):
        saved_boards.append(self._board_id)
        return original_save(self)

    monkeypatch.setattr(Snapshot, "save", _spy_save)

    migrate_legacy_participation_intent(config)

    assert "task" in saved_boards
    assert "bug" not in saved_boards


# ══════════════════════════════════════════════════════════════════════════════
# CT-07 — board_full_sync chama a migração após sincronizar, antes de retornar
# ══════════════════════════════════════════════════════════════════════════════

def test_ct07_board_full_sync_calls_migration_in_order(tmp_path, monkeypatch):
    import src.__main__ as main_mod

    monkeypatch.chdir(tmp_path)
    boards_base = tmp_path / ".pipe" / "boards"
    monkeypatch.setattr("src.core.snapshot.BOARDS_DIR", boards_base)

    config = {
        "boards": {
            "platform": "github",
            "task": {"columns": {"backlog": {"name": "Backlog"}}},
        }
    }

    events = []

    class FakeBoard:
        def board_ids(self, cfg):
            return [bid for bid, c in cfg["boards"].items()
                    if bid != "platform" and isinstance(c, dict)]

        def sync_boards(self, cfg):
            events.append("sync_boards")

        def detect_board_changes(self, board_id, snap, queue):
            events.append("detect_board_changes")
            return 0

    monkeypatch.setattr(main_mod, "board", FakeBoard())

    def _spy_migrate(cfg):
        events.append("migrate")
        assert cfg is config

    monkeypatch.setattr(main_mod, "migrate_legacy_participation_intent", _spy_migrate)

    main_mod.board_full_sync(config)

    # Chamada exatamente uma vez.
    assert events.count("migrate") == 1
    # Ordem: sync_boards → detect_board_changes → migrate.
    assert events.index("sync_boards") < events.index("detect_board_changes")
    assert events.index("detect_board_changes") < events.index("migrate")
    # migrate é o último evento antes do retorno.
    assert events[-1] == "migrate"
