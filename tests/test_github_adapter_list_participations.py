"""Testes de `GitHubBoardAdapter.list_participations` via GraphQL.

Cobre exclusivamente o escopo da issue #248 (story #243):
- query GraphQL nova trazendo `id`, `project.id`, `isArchived` e `Status`
  (via `fieldValues`/`ProjectV2ItemFieldSingleSelectValue`), seguindo o
  padrão de `_PROPAGATED_ITEMS_QUERY`/`_BELONGS_QUERY` já existentes;
- resolução de `board_id` via `self._projects` (mesmo mapeamento de
  `_board_meta`/`_belongs_to_board`), ou `None` quando o project não
  corresponder a nenhum board configurado;
- `status`/`archived` com os defaults `None`/`False` quando ausentes;
- consulta pelo `number` da issue (owner/repo via `self._repo.split("/")`,
  mesmo padrão de `_belongs_to_board`);
- falha do `_gql` propaga (RN-B02) — não é capturada, não retorna `[]`, não
  apenas loga warning (diferente do padrão legado de
  `_remove_propagated_items_without_status`).

Fora de escopo (não testado aqui, conforme a própria issue): decisão de
remoção/classificação de intenção, alteração de
`_remove_propagated_items_without_status`, e chamadas a
`list_participations` a partir de `_add_sub_issue` ou outro fluxo.

Ver `doc/product/integridade-de-issues-entre-boards/casos-de-teste/
248-casos-de-teste-github-adapter-list-participations.md` para a versão
legível/rastreável destes casos (CT01-CT08).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.github_board import GitHubBoardAdapter
from src.core.board import Participation


# ── Helpers ────────────────────────────────────────────────────────────────────

CONFIGURED_BOARD = "backlog"
CONFIGURED_PID = "PVT_configured"
OTHER_PID = "PVT_not_configured"


def _item(item_id: str, project_id: str, status: str | None = None,
          is_archived: bool | None = None, omit_archived: bool = False):
    """Monta um nó de `projectItems` no formato real do GraphQL do GitHub."""
    field_nodes = []
    if status is not None:
        field_nodes.append({"field": {"name": "Status"}, "name": status})
    node = {
        "id": item_id,
        "project": {"id": project_id},
        "fieldValues": {"nodes": field_nodes},
    }
    if not omit_archived:
        node["isArchived"] = bool(is_archived)
    return node


def _adapter(nodes, projects=None):
    """Adapter com `_gql` fake e `_gh`/`_api` proibidos no caminho produtivo."""
    a = GitHubBoardAdapter()
    a._repo = "owner/repo"
    a._projects = projects if projects is not None else {
        CONFIGURED_BOARD: {"project_id": CONFIGURED_PID, "status_field_id": "fid", "options": {}}
    }

    calls = {"query": []}

    def fake_gql(query, **variables):
        calls["query"].append((query, variables))
        return {"repository": {"issue": {"projectItems": {"nodes": nodes}}}}

    def forbidden(*args, **kwargs):
        raise AssertionError("Projects V2 não existe na REST API - _gh/_api proibidos")

    a._gql = fake_gql
    a._gh = forbidden
    a._api = forbidden
    return a, calls


def _raising_adapter(exc, projects=None):
    a = GitHubBoardAdapter()
    a._repo = "owner/repo"
    a._projects = projects if projects is not None else {
        CONFIGURED_BOARD: {"project_id": CONFIGURED_PID, "status_field_id": "fid", "options": {}}
    }

    def fake_gql(query, **variables):
        raise exc

    def forbidden(*args, **kwargs):
        raise AssertionError("Projects V2 não existe na REST API - _gh/_api proibidos")

    a._gql = fake_gql
    a._gh = forbidden
    a._api = forbidden
    return a


# ── CT01 — board_id/status resolvidos quando project está configurado ────────

def test_list_participations_resolve_board_id_e_status_quando_project_configurado():
    nodes = [_item("PVTI_1", CONFIGURED_PID, status="Doing", is_archived=False)]
    adapter, calls = _adapter(nodes)

    result = adapter.list_participations("76")

    assert len(result) == 1
    p = result[0]
    assert isinstance(p, Participation)
    assert p.item_id == "PVTI_1"
    assert p.project_id == CONFIGURED_PID
    assert p.board_id == CONFIGURED_BOARD
    assert p.status == "Doing"
    assert p.archived is False

    # Consulta feita com number inteiro (mesmo padrão de _belongs_to_board).
    _, variables = calls["query"][0]
    assert variables["number"] == 76


# ── CT02 — board_id/status None quando project não configurado ───────────────

def test_list_participations_board_id_e_status_none_quando_project_nao_configurado():
    nodes = [_item("PVTI_2", OTHER_PID, status=None, is_archived=False)]
    adapter, _ = _adapter(nodes)

    result = adapter.list_participations("76")

    assert len(result) == 1
    p = result[0]
    assert p.board_id is None
    assert p.status is None
    assert p.project_id == OTHER_PID
    assert p.item_id == "PVTI_2"


# ── CT03 — dois items, um resolvido e um não (cenário exato do "Como testar") ─

def test_list_participations_dois_items_um_resolvido_um_nao():
    nodes = [
        _item("PVTI_1", CONFIGURED_PID, status="Doing", is_archived=False),
        _item("PVTI_2", OTHER_PID, status=None, is_archived=False),
    ]
    adapter, _ = _adapter(nodes)

    result = adapter.list_participations("76")

    assert len(result) == 2

    resolved = next(p for p in result if p.item_id == "PVTI_1")
    unresolved = next(p for p in result if p.item_id == "PVTI_2")

    assert resolved.board_id == CONFIGURED_BOARD
    assert resolved.status == "Doing"

    assert unresolved.board_id is None
    assert unresolved.status is None


# ── CT04 — archived reflete isArchived, default False quando ausente ─────────

def test_list_participations_archived_reflete_isarchived_com_default_false():
    nodes = [
        _item("PVTI_1", CONFIGURED_PID, status="Doing", is_archived=True),
        _item("PVTI_2", OTHER_PID, status=None, omit_archived=True),
    ]
    adapter, _ = _adapter(nodes)

    result = adapter.list_participations("76")

    archived_item = next(p for p in result if p.item_id == "PVTI_1")
    no_archived_key_item = next(p for p in result if p.item_id == "PVTI_2")

    assert archived_item.archived is True
    assert no_archived_key_item.archived is False


# ── CT05 — projectItems vazio devolve [] sem erro ─────────────────────────────

def test_list_participations_projectitems_vazio_retorna_lista_vazia():
    adapter, _ = _adapter([])

    result = adapter.list_participations("76")

    assert result == []


# ── CT06 — falha do _gql propaga (RN-B02) ─────────────────────────────────────

def test_list_participations_falha_do_gql_propaga_excecao():
    adapter = _raising_adapter(RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        adapter.list_participations("76")


# ── CT07 — consulta por number com owner/repo split; query traz campos exigidos

def test_list_participations_consulta_por_number_com_owner_repo_split():
    adapter, calls = _adapter([])

    adapter.list_participations("76")

    assert len(calls["query"]) == 1
    query, variables = calls["query"][0]
    assert variables["owner"] == "owner"
    assert variables["repo"] == "repo"
    assert variables["number"] == 76

    assert "projectItems" in query
    assert "isArchived" in query
    assert "ProjectV2ItemFieldSingleSelectValue" in query
