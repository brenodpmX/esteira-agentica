"""Contrato do adapter real `list_participations` (#310).

Exercita `GitHubBoardAdapter.list_participations` com um `_gql` fake que simula
a resposta de `projectItems` — SEM rede. Prova que:
- cada item vira uma `Participation` com project/coluna/arquivamento;
- o quadro configurado é resolvido pelo mapa reverso project_id -> board;
- projects fora da config resolvem board_id vazio;
- falha de consulta propaga como `ParticipationQueryError` (nunca lista vazia).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.github_board import GitHubBoardAdapter
from src.core.participation import ParticipationQueryError


class FakeAdapter(GitHubBoardAdapter):
    def __init__(self, response=None, raise_exc=None):
        self._repo = "owner/repo"
        self._projects = {
            "epicos": {"project_id": "PROJ_EP"},
            "historias": {"project_id": "PROJ_HI"},
        }
        self._response = response
        self._raise_exc = raise_exc

    def _penalty_check(self):
        pass

    def _gql(self, query, **vars):
        if self._raise_exc:
            raise self._raise_exc
        return self._response


def _node(item_id, project_id, status="", archived=False):
    fvs = []
    if status:
        fvs.append({"field": {"name": "Status"}, "name": status})
    return {
        "id": item_id,
        "isArchived": archived,
        "project": {"id": project_id},
        "fieldValues": {"nodes": fvs},
    }


def test_list_participations_maps_items_to_boards():
    response = {"repository": {"issue": {"projectItems": {"nodes": [
        _node("IT1", "PROJ_HI", status="Doing"),
        _node("IT2", "PROJ_EP", status="", archived=True),
        _node("IT3", "PROJ_UNKNOWN", status="Backlog"),
    ]}}}}
    adapter = FakeAdapter(response=response)
    parts = adapter.list_participations("42")
    assert len(parts) == 3

    by_item = {p.item_id: p for p in parts}
    assert by_item["IT1"].board_id == "historias"
    assert by_item["IT1"].column == "Doing"
    assert by_item["IT1"].archived is False

    assert by_item["IT2"].board_id == "epicos"
    assert by_item["IT2"].column == ""
    assert by_item["IT2"].archived is True

    # project fora da config: board resolvido vazio (mas item preservado).
    assert by_item["IT3"].board_id == ""
    assert by_item["IT3"].project_id == "PROJ_UNKNOWN"


def test_list_participations_absent_issue_returns_empty():
    adapter = FakeAdapter(response={"repository": {"issue": None}})
    assert adapter.list_participations("99") == []


def test_list_participations_query_failure_is_typed_error():
    adapter = FakeAdapter(raise_exc=RuntimeError("transport broke"))
    with pytest.raises(ParticipationQueryError):
        adapter.list_participations("7")
