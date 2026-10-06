"""Testes da correção de duplicação e ausência de coluna em sub-issues propagadas.

Suíte canônica do Fenômeno 1 (incidente "issues criadas em dois boards
indevidamente"). Cobre:

- `remove_from_board` (primitiva no port e no adapter GitHub);
- pós-hook `_remove_propagated_items_without_status` — implementação REAL,
  exercitada via mock de `_gql` (Projects V2 só existe no GraphQL; `_gh`/`_api`
  não podem ser chamados no caminho produtivo);
- fallback de coluna em `create_issue` (issue nunca nasce sem `Status`);
- guard de `_apply_create_down`, que só descarta com PROVA de propagação
  (issue já registrada em outro board configurado com coluna conhecida);
- reconciliação de coluna vazia em `_apply_change_down` (escreve no board) e
  ausência de escrita em movimentação remota legítima;
- `detect_board_changes` tratando coluna vazia como divergência.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.github_board import GitHubBoardAdapter
from src.core.board import Board, BoardPort, Issue
from src.core.change_queue import ChangeQueue
from src.core.log import log


# ── Fake adapter que registra chamadas em vez de bater na rede ────────────────

class FakePort(BoardPort):
    def __init__(self):
        self.calls = []
        self.remove_raises = None

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
        if self.remove_raises:
            raise self.remove_raises


# ── Helpers do adapter GitHub (pós-hook e create_issue) ───────────────────────

CHILD_BOARD = "story"
CHILD_PID = "PVT_child"
PARENT_PID = "PVT_parent"


def _item(item_id: str, project_id: str, status: str | None):
    """Monta um nó de `projectItems` no formato real do GraphQL do GitHub."""
    field_nodes = []
    if status is not None:
        field_nodes.append({"field": {"name": "Status"}, "name": status})
    return {
        "id": item_id,
        "project": {"id": project_id},
        "fieldValues": {"nodes": field_nodes},
    }


def _adapter(items, projects=None):
    """Adapter com `_gql` fake e `_gh`/`_api` proibidos no caminho produtivo."""
    a = GitHubBoardAdapter()
    a._repo = "owner/repo"
    a._projects = projects if projects is not None else {
        CHILD_BOARD: {"project_id": CHILD_PID, "status_field_id": "fid", "options": {}}
    }

    calls = {"query": [], "mutation": []}

    def fake_gql(query, **variables):
        if "deleteProjectV2Item" in query:
            calls["mutation"].append(variables)
            return {"deleteProjectV2Item": {"deletedItemId": variables.get("itemId")}}
        calls["query"].append((query, variables))
        return {"repository": {"issue": {"projectItems": {"nodes": items}}}}

    def forbidden(*args, **kwargs):
        raise AssertionError("Projects V2 não existe na REST API - _gh/_api proibidos")

    a._gql = fake_gql
    a._gh = forbidden
    a._api = forbidden
    return a, calls


# ── remove_from_board (primitiva) ─────────────────────────────────────────────

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


# ── Pós-hook: implementação real (matriz 1 a 6) ───────────────────────────────

def test_poshook_usa_graphql_e_nunca_rest():
    """(1) Pós-hook real consulta via GraphQL; `_gh`/`_api` nunca são chamados."""
    a, calls = _adapter([_item("ITEM_child", CHILD_PID, "Doing")])

    a._remove_propagated_items_without_status("42", CHILD_BOARD)

    assert len(calls["query"]) == 1
    query, variables = calls["query"][0]
    assert "projectItems" in query and "fieldValues" in query
    assert "ProjectV2ItemFieldSingleSelectValue" in query
    assert variables == {"owner": "owner", "repo": "repo", "number": 42}


def test_poshook_remove_item_de_outro_project_sem_status():
    """(2) Item de outro project sem Status é removido com project_id/item_id da query."""
    a, calls = _adapter([
        _item("ITEM_child", CHILD_PID, "Doing"),
        _item("ITEM_parent", PARENT_PID, None),
    ])

    a._remove_propagated_items_without_status("42", CHILD_BOARD)

    assert calls["mutation"] == [{"pid": PARENT_PID, "itemId": "ITEM_parent"}]


def test_poshook_preserva_item_do_project_de_origem_sem_status():
    """(3) Item do project informado é preservado mesmo sem Status."""
    a, calls = _adapter([_item("ITEM_child", CHILD_PID, None)])

    a._remove_propagated_items_without_status("42", CHILD_BOARD)

    assert calls["mutation"] == []


def test_poshook_preserva_item_com_status_em_qualquer_project():
    """(4) Item com Status é multi-board consciente: preservado."""
    a, calls = _adapter([
        _item("ITEM_child", CHILD_PID, "Doing"),
        _item("ITEM_outro", "PVT_outro", "To Do"),
    ])

    a._remove_propagated_items_without_status("42", CHILD_BOARD)

    assert calls["mutation"] == []


def test_poshook_sem_project_de_origem_resolvido_nao_remove_nada():
    """(5) Project de origem não resolvido: sem exclusão garantida, não remove."""
    a, calls = _adapter([_item("ITEM_parent", PARENT_PID, None)], projects={})

    a._remove_propagated_items_without_status("42", CHILD_BOARD)

    assert calls["query"] == []
    assert calls["mutation"] == []


def test_poshook_multiplos_items_remove_so_os_elegiveis():
    """(6) Vários projectItems: remove só os elegíveis, numa única passagem."""
    a, calls = _adapter([
        _item("ITEM_child", CHILD_PID, None),          # origem -> preserva
        _item("ITEM_parent", PARENT_PID, None),        # outro sem Status -> remove
        _item("ITEM_multi", "PVT_multi", "Doing"),     # outro com Status -> preserva
        _item("ITEM_vazio", "PVT_vazio", "   "),       # Status em branco -> remove
    ])

    a._remove_propagated_items_without_status("42", CHILD_BOARD)

    assert len(calls["query"]) == 1
    assert calls["mutation"] == [
        {"pid": PARENT_PID, "itemId": "ITEM_parent"},
        {"pid": "PVT_vazio", "itemId": "ITEM_vazio"},
    ]


def test_add_sub_issue_encadeia_poshook_com_board_de_origem():
    """`_add_sub_issue` vincula via REST e encadeia o pós-hook com o board informado."""
    a, calls = _adapter([_item("ITEM_parent", PARENT_PID, None)])

    api_calls = []
    def fake_api(method, path, **fields):
        api_calls.append((method, path, fields))
        return ""

    a._api = fake_api          # o vínculo de sub-issue É REST (existe)
    a._get_issue_db_id = lambda num: 12345 if num == "42" else None

    a._add_sub_issue("10", "42", current_board_id=CHILD_BOARD)

    assert api_calls[0][0] == "POST"
    assert api_calls[0][1] == "/repos/owner/repo/issues/10/sub_issues"
    # Pós-hook real executado: item propagado no project do pai removido.
    assert calls["mutation"] == [{"pid": PARENT_PID, "itemId": "ITEM_parent"}]


# ── Fallback de coluna em create_issue (matriz 7 e 8) ─────────────────────────

def _create_issue_adapter(options):
    a = GitHubBoardAdapter()
    a._repo = "owner/repo"
    a._projects = {
        "b": {"project_id": "pid", "status_field_id": "fid", "options": options}
    }
    a._penalty_check = lambda: None
    a._gh = lambda *args, **kw: "https://github.com/owner/repo/issues/42\n"

    field_updates = []

    def fake_gql(query, **variables):
        if "addProjectV2ItemById" in query:
            return {"addProjectV2ItemById": {"item": {"id": "ITEM_new"}}}
        if "updateProjectV2ItemFieldValue" in query:
            field_updates.append(variables)
            return {}
        return {"repository": {"issue": {"id": "NODE_42",
                                        "updatedAt": "2024-01-01T00:00:00Z"}}}

    a._gql = fake_gql
    return a, field_updates


def test_create_issue_coluna_invalida_usa_fallback_com_warning(monkeypatch):
    """(7) Coluna inexistente nas opções: usa a primeira e loga warning."""
    a, field_updates = _create_issue_adapter({"todo": "OPT_todo", "doing": "OPT_doing"})

    warnings = []
    monkeypatch.setattr(log, "warning",
                        lambda mod, msg, *a_, **kw: warnings.append(msg))

    issue = a.create_issue("b", "Teste", "corpo", "inexistente")

    assert issue.column == "todo"
    assert field_updates == [{"pid": "pid", "itemId": "ITEM_new",
                              "fieldId": "fid", "optionId": "OPT_todo"}]
    assert any("inexistente" in m and "fallback" in m for m in warnings)


def test_create_issue_coluna_valida_sem_fallback(monkeypatch):
    """(8) Coluna válida: aplica a própria coluna, sem warning de fallback."""
    a, field_updates = _create_issue_adapter({"todo": "OPT_todo", "doing": "OPT_doing"})

    warnings = []
    monkeypatch.setattr(log, "warning",
                        lambda mod, msg, *a_, **kw: warnings.append(msg))

    issue = a.create_issue("b", "Teste", "corpo", "doing")

    assert issue.column == "doing"
    assert field_updates == [{"pid": "pid", "itemId": "ITEM_new",
                              "fieldId": "fid", "optionId": "OPT_doing"}]
    assert not any("fallback" in m for m in warnings)


# ── Guard do create-down (agora via reconciliação de participação #310) ───────
#
# A partir de #310, o guard de `_apply_create_down` deixou de usar o
# `_propagation_proof` baseado em snapshot e passou a usar
# `reconcile_remote_presence`, que classifica a presença via
# `classify_participation` consultando `list_participations` (GraphQL). Os
# testes abaixo exercitam o caminho REAL com um FakePort que implementa
# `list_participations`, provando a integração (não só a função isolada).

CONFIG = {
    "boards": {
        "platform": "github",
        "b": {"columns": {"todo": {"name": "To Do"}, "doing": {"name": "Doing"}}},
        "outro_board": {"columns": {"todo": {"name": "To Do"}, "doing": {"name": "Doing"}}},
    }
}


def _snapshot_com_issue(board_id: str, issue_id: str, column: str):
    from src.core.snapshot import Snapshot
    snap = Snapshot(board_id).load()
    snap.board = {"todo": "To Do", "doing": "Doing"}
    snap.issues.append({"id": issue_id, "column": column, "status": "ok"})
    snap.save()


def _board_com_issue(issue: Issue, participations=None):
    from src.core.participation import Participation, ParticipationQueryError
    port = FakePort()
    board = Board(port)
    board._port.get_issue = lambda bid, iid, fullsync=False: issue
    parts = participations

    def _list(issue_id):
        if parts is None:
            raise ParticipationQueryError(f"#{issue_id} - sem list_participations")
        return list(parts)

    board._port.list_participations = _list
    return port, board


def test_create_down_issue_nova_sem_outra_presenca_cria_arquivos(monkeypatch, tmp_path):
    """(9) Issue nova, presença única no board atual, sem parent cross-board:
    classificada `origin` e cria arquivos com fallback de coluna."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync
    from src.core.participation import Participation
    from src.core.snapshot import Snapshot

    snap = Snapshot("b").load()
    snap.board = {"todo": "To Do"}
    snap.save()

    # Presença única no board atual (sem outra presença, sem parent cross-board).
    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="",
              updated_at="2024-01-01T00:00:00Z"),
        participations=[Participation("I5", "b", "Pb", "")],
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_create_down("b", item, board, ChangeQueue(), CONFIG)

    assert ("remove_from_board", "5") not in port.calls
    body = tmp_path / ".pipe/boards/b/todo/5-teste-body.md"
    assert body.exists()
    # Persiste a intenção classificada no snapshot (RF-08/RF-10).
    assert Snapshot("b").load().issue("5")["participation_intent"] == "origin"


def test_create_down_parent_cross_board_presenca_unica_vira_origem(monkeypatch, tmp_path):
    """(9b) Pai cross-board com presença ÚNICA no quadro atual: `origin` — cria
    arquivos e persiste a intenção, sem remover. Presença única não é propagação
    (não há segunda cópia); `unresolved` aqui seria deadlock permanente."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync
    from src.core.participation import Participation
    from src.core.snapshot import Snapshot

    snap = Snapshot("b").load()
    snap.board = {"todo": "To Do"}
    snap.save()
    # Parent #10 reside em 'outro_board' (cross-board), mas a issue tem presença
    # ÚNICA no quadro atual 'b' — nenhuma outra presença em quadro configurado.
    _snapshot_com_issue("outro_board", "10", "doing")

    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="", parent="10",
              updated_at="2024-01-01T00:00:00Z"),
        participations=[Participation("I5", "b", "Pb", "")],
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_create_down("b", item, board, ChangeQueue(), CONFIG)

    assert ("remove_from_board", "5") not in port.calls
    assert (tmp_path / ".pipe/boards/b/todo/5-teste-body.md").exists()
    assert Snapshot("b").load().issue("5")["participation_intent"] == "origin"


def test_create_down_presenca_propagada_com_prova_descarta(monkeypatch, tmp_path):
    """(10) Presença comprovada em outro board configurado (coluna conhecida):
    classificada `propagated`, removida e evento descartado."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync
    from src.core.participation import Participation
    from src.core.snapshot import Snapshot

    snap = Snapshot("b").load()
    snap.board = {"todo": "To Do"}
    snap.save()

    # Prova de propagação: presença confirmada em 'outro_board' com coluna 'doing'
    # (coluna conhecida nas columns de outro_board). Presença no board atual 'b'
    # é a propagada.
    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="", parent="10",
              updated_at="2024-01-01T00:00:00Z"),
        participations=[
            Participation("Io", "outro_board", "Po", "doing"),
            Participation("Ib", "b", "Pb", ""),
        ],
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_create_down("b", item, board, ChangeQueue(), CONFIG)

    assert ("remove_from_board", "5") in port.calls
    assert not (tmp_path / ".pipe/boards/b/todo/5-teste-body.md").exists()


def test_create_down_propagada_com_coluna_preenchida_tambem_descarta(monkeypatch, tmp_path):
    """(10b/CT-03) Coluna preenchida NÃO isenta: presença com prova em outro
    board é removida mesmo chegando com Status no board atual."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync
    from src.core.participation import Participation
    from src.core.snapshot import Snapshot

    snap = Snapshot("b").load()
    snap.board = {"todo": "To Do", "doing": "Doing"}
    snap.save()

    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="doing", parent="10",
              updated_at="2024-01-01T00:00:00Z"),
        participations=[
            Participation("Io", "outro_board", "Po", "doing"),
            Participation("Ib", "b", "Pb", "Doing"),
        ],
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_create_down("b", item, board, ChangeQueue(), CONFIG)

    assert ("remove_from_board", "5") in port.calls
    assert not (tmp_path / ".pipe/boards/b/doing/5-teste-body.md").exists()


def test_create_down_autorizada_por_rotulo_cria_arquivos(monkeypatch, tmp_path):
    """(10c/CT-04) Rótulo `board-intent-<board atual>` autoriza participação
    multi-quadro: `authorized`, não removida, cria arquivos."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync
    from src.core.participation import Participation
    from src.core.snapshot import Snapshot

    snap = Snapshot("b").load()
    snap.board = {"todo": "To Do"}
    snap.save()

    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="", parent="10",
              labels=["board-intent-b"],
              updated_at="2024-01-01T00:00:00Z"),
        participations=[
            Participation("Io", "outro_board", "Po", "doing"),
            Participation("Ib", "b", "Pb", ""),
        ],
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_create_down("b", item, board, ChangeQueue(), CONFIG)

    assert ("remove_from_board", "5") not in port.calls
    assert (tmp_path / ".pipe/boards/b/todo/5-teste-body.md").exists()
    assert Snapshot("b").load().issue("5")["participation_intent"] == "authorized"


def test_create_down_prova_de_board_fora_da_config_nao_descarta(monkeypatch, tmp_path):
    """(11) Presença em project fora da config (board_id="") não prova: a
    presença única configurada é `origin` e cria arquivos."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync
    from src.core.participation import Participation
    from src.core.snapshot import Snapshot

    snap = Snapshot("b").load()
    snap.board = {"todo": "To Do"}
    snap.save()

    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="",
              updated_at="2024-01-01T00:00:00Z"),
        participations=[
            Participation("Ib", "b", "Pb", ""),
            Participation("Ix", "", "Px", "doing"),  # project não configurado
        ],
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_create_down("b", item, board, ChangeQueue(), CONFIG)

    assert ("remove_from_board", "5") not in port.calls
    assert (tmp_path / ".pipe/boards/b/todo/5-teste-body.md").exists()


def test_create_down_falha_de_consulta_fica_unresolved_adiada(monkeypatch, tmp_path):
    """(12) Falha transitória de consulta (ParticipationQueryError): `unresolved`,
    sem remoção, sem arquivos; pendência adiada registrada (RN-09/CT-05)."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync
    from src.core import participation_reconcile as PR
    from src.core.snapshot import Snapshot

    snap = Snapshot("b").load()
    snap.board = {"todo": "To Do"}
    snap.save()

    # FakePort sem participations => list_participations levanta ParticipationQueryError.
    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="",
              updated_at="2024-01-01T00:00:00Z"),
        participations=None,
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_create_down("b", item, board, ChangeQueue(), CONFIG)

    assert ("remove_from_board", "5") not in port.calls
    assert not (tmp_path / ".pipe/boards/b/todo/5-teste-body.md").exists()
    entry = PR.pending_entry("b", "5")
    assert entry is not None and entry["next_attempt_at"]


# ── Reconciliação de coluna no change-down (matriz 13, 14 e 16) ───────────────

def _issue_local(tmp_path, board_id: str, col: str, issue_id: str, slug: str):
    from src.core.snapshot import Snapshot
    snap = Snapshot(board_id).load()
    body_path = Path(".pipe/boards") / board_id / col / f"{issue_id}-{slug}-body.md"
    (tmp_path / body_path.parent).mkdir(parents=True, exist_ok=True)
    (tmp_path / body_path).write_text("# Teste\n\n@---\n/labels test\n")
    snap.issues.append({
        "id": issue_id, "column": col, "body_path": str(body_path),
        "body_mtime": "1234", "updated_at": "2024-01-01T00:00:00Z", "status": "ok",
    })
    snap.save()
    return tmp_path / body_path


def test_change_down_coluna_vazia_reaplica_coluna_no_board(monkeypatch, tmp_path):
    """(13) Status remoto vazio e arquivo já na coluna certa: reaplica no board."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync

    _issue_local(tmp_path, "b", "todo", "5", "teste")
    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="",
              updated_at="2024-01-02T00:00:00Z")
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_change_down("b", item, board, ChangeQueue(), config=None)

    moves = [c for c in port.calls if c[0] == "move_issue"]
    assert moves == [("move_issue", "5", "todo", None)]
    # Arquivo permanece na coluna do snapshot.
    assert (tmp_path / ".pipe/boards/b/todo/5-teste-body.md").exists()


def test_change_down_coluna_nula_reaplica_coluna_no_board(monkeypatch, tmp_path):
    """Coluna None no board recebe o mesmo tratamento de coluna vazia."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync

    _issue_local(tmp_path, "b", "doing", "5", "teste")
    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column=None,
              updated_at="2024-01-02T00:00:00Z")
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_change_down("b", item, board, ChangeQueue(), config=None)

    moves = [c for c in port.calls if c[0] == "move_issue"]
    assert moves == [("move_issue", "5", "doing", None)]


def test_change_down_movimentacao_remota_legitima_nao_escreve_no_board(monkeypatch, tmp_path):
    """(14) Movimentação manual no board: move arquivos e NÃO chama move_issue."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync

    _issue_local(tmp_path, "b", "todo", "5", "teste")
    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="doing",
              updated_at="2024-01-02T00:00:00Z")
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_change_down("b", item, board, ChangeQueue(), config=None)

    assert [c for c in port.calls if c[0] == "move_issue"] == []
    assert (tmp_path / ".pipe/boards/b/doing/5-teste-body.md").exists()
    assert not (tmp_path / ".pipe/boards/b/todo/5-teste-body.md").exists()


def test_change_down_coluna_vazia_falha_de_reaplicacao_nao_interrompe(monkeypatch, tmp_path):
    """Reaplicação é oportunista: falha vira warning e o down segue."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync

    _issue_local(tmp_path, "b", "todo", "5", "teste")
    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="",
              updated_at="2024-01-02T00:00:00Z")
    )

    def raising_move(board_id, issue_id, column, from_column=None):
        port.calls.append(("move_issue", issue_id, column, from_column))
        raise Exception("falha transitória")

    board._port.move_issue = raising_move
    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_change_down("b", item, board, ChangeQueue(), config=None)

    assert ("move_issue", "5", "todo", None) in port.calls
    assert (tmp_path / ".pipe/boards/b/todo/5-teste-body.md").exists()


def test_guard_e_fallback_nao_reintroduzem_item_removido(monkeypatch, tmp_path):
    """(16) Item removido pelo guard não volta via fallback do change-down."""
    monkeypatch.chdir(tmp_path)
    from src.core import sync
    from src.core.participation import Participation
    from src.core.snapshot import Snapshot

    snap = Snapshot("b").load()
    snap.board = {"todo": "To Do"}
    snap.save()

    port, board = _board_com_issue(
        Issue(id="5", title="Teste", body="", column="", parent="10",
              updated_at="2024-01-01T00:00:00Z"),
        participations=[
            Participation("Io", "outro_board", "Po", "doing"),  # prova
            Participation("Ib", "b", "Pb", ""),                  # propagada
        ],
    )
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id="5", board="b", fullsync=True)

    sync._apply_create_down("b", item, board, ChangeQueue(), CONFIG)

    # Removida e sem registro local no board atual: o change-down do board 'b'
    # não encontra a issue no snapshot e não reaplica coluna nenhuma.
    port.calls.clear()
    change = sync.ChangeItem.of(sync.SyncEvent.CHANGE_DOWN, id="5", board="b", fullsync=True)
    sync._apply_change_down("b", change, board, ChangeQueue(), config=CONFIG)

    assert [c for c in port.calls if c[0] == "move_issue"] == []
    assert Snapshot("b").load().issue("5") is None


# ── sincronização única com coluna vazia (matriz 15) ──────────────────────────

def test_detect_board_changes_coluna_vazia_detecta_diferenca(monkeypatch, tmp_path):
    """(15) Coluna vazia no remote != coluna no snapshot -> change-down."""
    monkeypatch.chdir(tmp_path)
    from src.core.snapshot import Snapshot
    from src.core.sync import sync_remote

    port = FakePort()
    board = Board(port)

    remote = Issue(id="5", title="Teste", body="", column="",
                   updated_at="2024-01-02T00:00:00Z")
    board._port.list_issues = lambda board_id: [remote]
    board._port.get_issue = lambda bid, iid, fullsync=False: remote

    snap = Snapshot("b").load()
    snap.issues.append({
        "id": "5", "column": "doing", "body_path": ".pipe/boards/b/doing/5-teste-body.md",
        "body_mtime": "1234", "updated_at": "2024-01-01T00:00:00Z", "status": "ok"
    })
    snap.save()

    queue = ChangeQueue()
    sync_remote("b", board, queue)

    item = queue.getNext()
    assert item is not None
    assert item.id == "5"
    assert item.event == "change-down"
