"""Testes de INTEGRAÇÃO da integridade de participação entre quadros (#310).

Diferente dos testes unitários (que chamam `participation`/`participation_reconcile`
diretamente), estes exercitam os CAMINHOS REAIS do motor da esteira, provando que
a classificação/reconciliação está LIGADA ao fluxo de produção:

- RF-07 — `sync._apply_change_up` dispara `reconcile_after_link` quando um
  vínculo pai/filho CROSS-BOARD é aplicado (via `_reconcile_links_after_apply`).
- RF-08 — `sync._apply_create_down` classifica e reconcilia a presença nova e
  persiste `participation_intent` no snapshot.
- RF-10 — `__main__.keep_task` aplica o gate final (sem rede) e bloqueia issue
  sem intenção confirmada.
- RF-12 — `sync._filter_suspended_cross_board_parent` recusa vínculo cross-board
  quando a contingência está suspensa (via `guard_cross_board_link`).
- RF-13/CT-22 — `__main__.sync_remote_board` chama `detect_external_removal`.
- RF-15 — o log de execução de agente (`kiro_cli_agent._build_log`) carrega
  `participation_intent` e `origin_board`.

Nenhum teste chama as funções de `participation_reconcile` isoladamente: todos
entram pelo ponto de orquestração real.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, Issue
from src.core.change_queue import ChangeQueue
from src.core.log import log
from src.core.participation import Participation, ParticipationQueryError


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log._log_dir = Path("logs")
    log._setup()
    yield


def _log_text():
    path = Path("logs") / f"{date.today().strftime('%Y-%m-%d')}.json"
    return path.read_text(encoding="utf-8") if path.exists() else ""


CONFIG = {
    "boards": {
        "platform": "github",
        "tarefas": {"columns": {"doing": {"name": "Doing"}}},
        "historias": {"columns": {"doing": {"name": "Doing"}}},
        "epicos": {"columns": {"doing": {"name": "Doing"}}},
    }
}


class FakePort(BoardPort):
    """Porta offline: espiã de remoções e relações; list_participations controlável."""

    def __init__(self, participations=None, raise_on_list=None, raise_on_remove=None,
                 issue=None):
        self._parts = {str(k): list(v) for k, v in (participations or {}).items()}
        self.raise_on_list = raise_on_list
        self.raise_on_remove = raise_on_remove
        self._issue = issue
        self.removed = []
        self.relations_touched = []
        self.comments = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def get_issue(self, board_id, issue_id, fullsync=False):
        return self._issue
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass

    def set_parts(self, issue_id, parts):
        self._parts[str(issue_id)] = list(parts)

    def list_participations(self, issue_id):
        if self.raise_on_list:
            raise self.raise_on_list
        return list(self._parts.get(str(issue_id), []))

    def remove_from_board(self, board_id, issue_id):
        if self.raise_on_remove:
            raise self.raise_on_remove
        self.removed.append((board_id, str(issue_id)))

    def set_parent(self, board_id, issue_id, parent_id, known_current=None):
        self.relations_touched.append(("set_parent", board_id, str(issue_id)))
    def set_children(self, board_id, issue_id, children_ids, known_current=None):
        self.relations_touched.append(("set_children", board_id, str(issue_id)))
    def set_labels(self, board_id, issue_id, labels): pass
    def set_blocked_by(self, board_id, issue_id, blocker_ids, known_current=None): pass
    def set_blocks(self, board_id, issue_id, blocked_ids, known_current=None): pass


def _snap_issue(board_id, issue_id, column="doing", **extra):
    from src.core.snapshot import Snapshot
    snap = Snapshot(board_id).load()
    snap.board = {"doing": "Doing"}
    data = {"id": str(issue_id), "column": column, "status": "ok"}
    data.update(extra)
    snap.issues.append(data)
    snap.save()
    return snap


def _write_body_with_parent(board_id, col, issue_id, slug, parent_id):
    """Cria o -body.md local com /parent #parent e registra no snapshot."""
    from src.core.snapshot import Snapshot
    body_dir = Path(".pipe/boards") / board_id / col
    body_dir.mkdir(parents=True, exist_ok=True)
    body_path = body_dir / f"{issue_id}-{slug}-body.md"
    body_path.write_text(f"# {slug}\n\ncorpo\n\n@---\n/parent #{parent_id}\n",
                         encoding="utf-8")
    snap = Snapshot(board_id).load()
    snap.board = {"doing": "Doing"}
    snap.issues.append({
        "id": str(issue_id), "column": col, "body_path": str(body_path),
        "body_mtime": "1", "updated_at": "2024-01-01T00:00:00Z", "status": "ok",
        "parent": None,
    })
    snap.save()
    return body_path


# ── RF-07 — change-up com /parent cross-board dispara reconcile_after_link ─────

def test_rf07_change_up_cross_board_parent_triggers_reconcile(monkeypatch):
    """CT-01 pelo caminho real: aplicar /parent cross-board em `_apply_change_up`
    remove a presença propagada da filha no quadro do pai, sem tocar hierarquia."""
    from src.core import sync

    # Pai #10 reside em 'epicos'; filha #5 em 'tarefas'. Vínculo cross-board.
    _snap_issue("epicos", "10", "doing")
    _write_body_with_parent("tarefas", "doing", "5", "filha", "10")

    # A filha #5 está propagada em 'epicos' (quadro do pai), origem em 'tarefas'.
    parts = {
        "5": [
            Participation("Ita", "tarefas", "Pta", "doing"),
            Participation("Iep", "epicos", "Pep", ""),
        ]
    }
    issue = Issue(id="5", title="filha", body="corpo", column="doing",
                  updated_at="2024-01-02T00:00:00Z")
    port = FakePort(participations=parts, issue=issue)
    board = Board(port)

    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_UP, id="5", board="tarefas")
    sync._apply_change_up("tarefas", item, board, ChangeQueue(), CONFIG)

    # Reconciliação real executada: presença propagada em 'epicos' removida.
    assert ("epicos", "5") in port.removed
    # Hierarquia nunca tocada pela reconciliação (RN-03). set_parent pode ser
    # chamado pela aplicação do comando, mas nunca para desfazer o vínculo.
    assert not any(c[0] == "set_children" for c in port.relations_touched)
    text = _log_text()
    assert "participation_reconciled" in text


def test_rf07_same_board_parent_does_not_reconcile(monkeypatch):
    """Vínculo pai/filho no MESMO quadro não dispara reconciliação."""
    from src.core import sync

    _snap_issue("tarefas", "10", "doing")
    _write_body_with_parent("tarefas", "doing", "5", "filha", "10")

    issue = Issue(id="5", title="filha", body="corpo", column="doing",
                  updated_at="2024-01-02T00:00:00Z")
    # list_participations lançaria se chamado — prova que não é consultado.
    port = FakePort(raise_on_list=ParticipationQueryError("não deve consultar"),
                    issue=issue)
    board = Board(port)

    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_UP, id="5", board="tarefas")
    # Não deve levantar: caminho same-board nem chega a list_participations.
    sync._apply_change_up("tarefas", item, board, ChangeQueue(), CONFIG)
    assert port.removed == []


# ── RF-08 — create-down classifica e persiste participation_intent ────────────

def test_rf08_create_down_persists_origin_intent(monkeypatch):
    """CT-origem pelo caminho real: issue nova de presença única vira `origin`
    e o snapshot persiste `participation_intent`."""
    from src.core import sync
    from src.core.snapshot import Snapshot

    snap = Snapshot("tarefas").load()
    snap.board = {"doing": "Doing"}
    snap.save()

    issue = Issue(id="7", title="Nova", body="corpo", column="doing",
                  updated_at="2024-01-01T00:00:00Z")
    port = FakePort(participations={"7": [Participation("I7", "tarefas", "Pta", "doing")]},
                    issue=issue)
    board = Board(port)

    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="7", board="tarefas",
                              fullsync=True)
    sync._apply_create_down("tarefas", item, board, ChangeQueue(), CONFIG)

    data = Snapshot("tarefas").load().issue("7")
    assert data is not None
    assert data["participation_intent"] == "origin"
    assert port.removed == []


def test_rf08_create_down_propagated_removed_and_discarded(monkeypatch):
    """CT-02/CT-03 pelo caminho real: presença propagada (prova em outro quadro)
    é removida e o evento descartado — nenhum arquivo local criado."""
    from src.core import sync
    from src.core.snapshot import Snapshot

    snap = Snapshot("epicos").load()
    snap.board = {"doing": "Doing"}
    snap.save()

    # #8 confirmada em 'tarefas' (coluna conhecida) → propagada em 'epicos'.
    issue = Issue(id="8", title="Propagada", body="corpo", column="Doing",
                  parent="10", updated_at="2024-01-01T00:00:00Z")
    parts = {"8": [
        Participation("Ita", "tarefas", "Pta", "doing"),
        Participation("Iep", "epicos", "Pep", "Doing"),
    ]}
    port = FakePort(participations=parts, issue=issue)
    board = Board(port)

    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="8", board="epicos",
                              fullsync=True)
    sync._apply_create_down("epicos", item, board, ChangeQueue(), CONFIG)

    assert ("epicos", "8") in port.removed
    assert Snapshot("epicos").load().issue("8") is None
    assert not list(Path(".pipe/boards/epicos").glob("**/*-body.md"))


# ── RF-10 — gate final na seleção de tarefas (keep_task), sem rede ────────────

def test_rf10_keep_task_blocks_propagated_intent(monkeypatch):
    """CT-08 pelo caminho real: issue com intenção propagada é ignorada por
    `keep_task` e um evento deduplicado é registrado. O gate não toca a rede."""
    import src.__main__ as main
    from src.core import participation

    participation.reset_dispatch_dedup()
    cfg = {
        "boards": {
            "platform": "github",
            "tarefas": {
                "columns": {"doing": {"name": "Doing", "agent": "dev",
                                      "change": {"advance": "done"}},
                            "done": {"name": "Done"}},
            },
        }
    }
    _snap_issue("tarefas", "9", "doing", participation_intent="propagated",
                created_at="2024-01-01T00:00:00Z")

    result = main.keep_task("tarefas", cfg)
    assert result is None  # bloqueada pelo gate
    assert "dispatch_blocked_unconfirmed_intent" in _log_text()


def test_rf10_keep_task_allows_origin_intent(monkeypatch):
    """Issue com intenção confirmada (origin) permanece candidata normalmente."""
    import src.__main__ as main
    from src.core import participation

    participation.reset_dispatch_dedup()
    cfg = {
        "boards": {
            "platform": "github",
            "tarefas": {
                "columns": {"doing": {"name": "Doing", "agent": "dev",
                                      "change": {"advance": "done"}},
                            "done": {"name": "Done"}},
            },
        }
    }
    _snap_issue("tarefas", "11", "doing", participation_intent="origin",
                body_path="x", created_at="2024-01-01T00:00:00Z")

    result = main.keep_task("tarefas", cfg)
    # Passa pelo gate (retorna a tarefa, dict); não é bloqueada.
    assert result is not None and result != main.AUTO_ADVANCED
    assert result["issue"]["id"] == "11"


# ── RF-12 — contingência recusa vínculo cross-board via guard ─────────────────

def test_rf12_suspended_blocks_cross_board_parent(monkeypatch, tmp_path):
    """CT-18 pelo caminho real: com a contingência suspensa, `_apply_change_up`
    descarta o /parent cross-board (via guard_cross_board_link) e registra."""
    from src.core import sync
    from src.core.config import SAFETY_SUSPENDED

    # pipe.yml em disco com contingência suspensa (releitura sem cache).
    Path("pipe.yml").write_text(
        "safety:\n  cross_board_parent_links: suspended\n", encoding="utf-8")

    _snap_issue("epicos", "10", "doing")
    _write_body_with_parent("tarefas", "doing", "5", "filha", "10")

    issue = Issue(id="5", title="filha", body="corpo", column="doing",
                  updated_at="2024-01-02T00:00:00Z")
    port = FakePort(participations={"5": []}, issue=issue)
    board = Board(port)

    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_UP, id="5", board="tarefas")
    sync._apply_change_up("tarefas", item, board, ChangeQueue(), CONFIG)

    # O /parent cross-board foi recusado: set_parent nunca cria o vínculo.
    assert not any(c[0] == "set_parent" for c in port.relations_touched)
    assert "cross_board_link_blocked" in _log_text()


def test_rf12_suspended_allows_same_board_parent(monkeypatch):
    """Contingência suspensa NÃO afeta vínculo no mesmo quadro."""
    from src.core import sync

    Path("pipe.yml").write_text(
        "safety:\n  cross_board_parent_links: suspended\n", encoding="utf-8")

    _snap_issue("tarefas", "10", "doing")
    _write_body_with_parent("tarefas", "doing", "5", "filha", "10")

    issue = Issue(id="5", title="filha", body="corpo", column="doing",
                  updated_at="2024-01-02T00:00:00Z")
    port = FakePort(participations={"5": []}, issue=issue)
    board = Board(port)

    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_UP, id="5", board="tarefas")
    sync._apply_change_up("tarefas", item, board, ChangeQueue(), CONFIG)

    # Vínculo no mesmo quadro é aplicado (set_parent chamado).
    assert any(c[0] == "set_parent" for c in port.relations_touched)
    assert "cross_board_link_blocked" not in _log_text()


# ── RF-13 / CT-22 — sync_remote_board chama detect_external_removal ───────────

def test_rf13_sync_remote_board_detects_external_removal(monkeypatch):
    """CT-22 pelo caminho real: uma pendência cuja presença sumiu do quadro é
    detectada como remoção externa durante `sync_remote_board`."""
    import src.__main__ as main
    from src.core import participation_reconcile as PR
    from src.core.participation import Classification, UNRESOLVED

    # Registra uma pendência diretamente (simula adiamento de ciclo anterior).
    PR.defer_pending("epicos", "900", Classification(UNRESOLVED, {}), 300)
    assert PR.pending_entry("epicos", "900") is not None

    # A presença em 'epicos' sumiu (só resta a de origem).
    port = FakePort(participations={"900": [Participation("Io", "historias", "Po", "doing")]})
    main.board = Board(port)
    # sync_remote faz list_issues ([] no fake) → nada a enfileirar; o foco é a
    # chamada de detect_external_removal após o sync.
    main.sync_remote_board("epicos", CONFIG)

    assert "participation_removed_externally" in _log_text()
    assert PR.pending_entry("epicos", "900") is None


# ── RF-15 — log de execução de agente enriquecido ────────────────────────────

def test_rf15_agent_log_contains_participation_intent_and_origin():
    """O markdown de execução do agente carrega participation_intent e origin_board."""
    from src.adapters.kiro_cli_agent import KiroCliAgent
    from src.core.agent import AgentParams

    params = AgentParams(
        platform="github", agent_id="dev", agent_name="engineering",
        model="m", issue_id="42", board_id="tarefas", col_id="doing",
        prompt="faça", work_dir="/tmp/x",
        participation_intent="origin", origin_board="tarefas",
    )
    content = KiroCliAgent()._build_log(params)
    assert "- **participation_intent**: origin" in content
    assert "- **origin_board**: tarefas" in content


def test_rf15_agent_log_omits_participation_fields_when_absent():
    """Sem intenção (legado), o log não inventa as linhas."""
    from src.adapters.kiro_cli_agent import KiroCliAgent
    from src.core.agent import AgentParams

    params = AgentParams(
        platform="github", agent_id="dev", agent_name="engineering",
        model="m", issue_id="42", board_id="tarefas", col_id="doing",
        prompt="faça", work_dir="/tmp/x",
    )
    content = KiroCliAgent()._build_log(params)
    assert "participation_intent" not in content
    assert "origin_board" not in content
