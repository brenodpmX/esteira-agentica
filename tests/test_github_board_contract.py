"""CT-13 / CT-02b — Preparação não destrutiva vs. contração no adapter (#305).

Exercita `GitHubBoardAdapter.prepare_structure`, `contract_column` e
`remote_columns` com um `_gql` fake que simula o estado do campo Status e
registra as mutações emitidas — SEM rede. O objetivo é provar que:

- preparação é estritamente ADITIVA (cria colunas/campo/board ausentes,
  preserva TODAS as opções existentes com seus ids, nunca remove);
- contração substitui a lista exata preservando os ids das opções que
  permanecem (única operação que remove).
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.github_board import GitHubBoardAdapter


class FakeGqlAdapter(GitHubBoardAdapter):
    """Adapter com `_gql` fake dirigido por reconhecimento de query.

    Mantém o estado do campo Status de um único project em `self._options`
    (lista de {id, name}) e registra todas as mutações em `self.mutations`.
    """

    def __init__(self, options, has_field=True):
        self._repo = "owner/repo"
        self._projects = {}
        self._options = list(options)   # [{"id":..., "name":...}]
        self._has_field = has_field
        self.mutations = []             # strings de mutation emitidas
        self._next_id = 1000

    # Sem rede e sem throttle real.
    def _penalty_check(self):
        pass

    def _gql(self, query, **vars):
        q = query
        if "projectsV2(first" in q:
            return {"organization": {"projectsV2": {"nodes": [
                {"id": "PROJ1", "number": 1, "title": "Entrega"}]}}}
        if "organization(login" in q or "user(login:$login){id}" in q:
            return {"organization": {"id": "ORG1"}, "user": {"id": "ORG1"}}
        if "createProjectV2(" in q:
            return {"createProjectV2": {"projectV2": {
                "id": "PROJ1", "number": 1, "title": vars.get("title", "Entrega")}}}
        if "fields(first:20)" in q:  # _get_status_field
            if not self._has_field:
                return {"node": {"fields": {"nodes": []}}}
            return {"node": {"fields": {"nodes": [
                {"id": "FIELD1", "name": "Status",
                 "options": [dict(o) for o in self._options]}]}}}
        if "createProjectV2Field(" in q:  # _create_status_field
            self.mutations.append(q)
            self._has_field = True
            names = re.findall(r'name:"([^"]+)"', q)
            # a primeira ocorrência é name:"Status"; as demais são opções
            opt_names = [n for n in names if n != "Status"]
            self._options = [{"id": self._mk_id(), "name": n} for n in opt_names]
            return {"createProjectV2Field": {"projectV2Field": {"id": "FIELD1"}}}
        if "updateProjectV2Field(" in q:  # _update_status_options
            self.mutations.append(q)
            self._apply_update(q)
            return {"updateProjectV2Field": {"projectV2Field": {"id": "FIELD1"}}}
        raise AssertionError(f"query não reconhecida pelo fake: {q[:80]}")

    def _mk_id(self):
        self._next_id += 1
        return f"OPT{self._next_id}"

    def _apply_update(self, mutation):
        """Reconstrói self._options a partir da lista singleSelectOptions enviada.

        Opções com `id:"..."` preservam o id; sem id são novas (ganham id novo).
        A nova lista é EXATAMENTE a enviada (contração remove ausentes).
        """
        # extrai cada bloco {...}
        blocks = re.findall(r'\{[^{}]*\}', mutation)
        new_opts = []
        for b in blocks:
            name_m = re.search(r'name:"([^"]+)"', b)
            if not name_m:
                continue
            id_m = re.search(r'id:"([^"]+)"', b)
            new_opts.append({
                "id": id_m.group(1) if id_m else self._mk_id(),
                "name": name_m.group(1),
            })
        self._options = new_opts


def _opts(*names):
    return [{"id": f"OPT{i}", "name": n} for i, n in enumerate(names, 1)]


BOARDS = [{"id": "entrega", "name": "Entrega",
           "columns": ["backlog", "done"]}]


# ── CT-13a — Preparação cria destino, não remove origem retirada ──────────────

def test_ct13a_prepare_adds_new_preserves_withdrawn():
    adapter = FakeGqlAdapter(options=_opts("backlog", "revisao", "done"))
    # Config deseja [backlog, done, entregue]; revisao sai da config (retida).
    boards = [{"id": "entrega", "name": "Entrega",
               "columns": ["backlog", "done", "entregue"]}]

    adapter.prepare_structure(boards)

    names = [o["name"] for o in adapter._options]
    assert "entregue" in names          # coluna nova criada
    assert "revisao" in names           # retirada NÃO removida na preparação
    assert set(["backlog", "done"]).issubset(set(names))
    # Nenhuma mutação de contração (remoção): revisao segue presente.
    # Ids originais preservados para as que já existiam.
    by_name = {o["name"]: o["id"] for o in adapter._options}
    assert by_name["backlog"] == "OPT1"
    assert by_name["revisao"] == "OPT2"
    assert by_name["done"] == "OPT3"


def test_ct13a_prepare_noop_when_all_present():
    adapter = FakeGqlAdapter(options=_opts("backlog", "done"))
    adapter.prepare_structure(BOARDS)
    # Nada a criar: nenhuma mutação emitida.
    assert adapter.mutations == []


# ── CT-13b — Preparação cria campo Status ausente preservando opções ──────────

def test_ct13b_prepare_creates_field_when_absent():
    adapter = FakeGqlAdapter(options=[], has_field=False)
    adapter.prepare_structure(BOARDS)
    assert any("createProjectV2Field(" in m for m in adapter.mutations)
    names = [o["name"] for o in adapter._options]
    assert names == ["backlog", "done"]


def test_ct13b_prepare_preserves_extra_legacy_option():
    adapter = FakeGqlAdapter(options=_opts("backlog", "legado", "done"))
    adapter.prepare_structure(BOARDS)  # config = [backlog, done]
    names = [o["name"] for o in adapter._options]
    assert "legado" in names           # opção extra preservada
    by_name = {o["name"]: o["id"] for o in adapter._options}
    assert by_name["legado"] == "OPT2" # id intacto


# ── CT-02b — Contração remove apenas a origem, preserva ids das demais ────────

def test_ct02b_contract_removes_only_source_preserves_ids():
    adapter = FakeGqlAdapter(options=_opts("backlog", "revisao", "done", "arquivo"))
    adapter._projects["entrega"] = {
        "project_id": "PROJ1", "status_field_id": "FIELD1",
        "options": {o["name"]: o["id"] for o in adapter._options},
    }

    adapter.contract_column("entrega", ["backlog", "done", "arquivo"])

    names = [o["name"] for o in adapter._options]
    assert names == ["backlog", "done", "arquivo"]  # revisao removida
    by_name = {o["name"]: o["id"] for o in adapter._options}
    assert by_name["backlog"] == "OPT1"
    assert by_name["done"] == "OPT3"
    assert by_name["arquivo"] == "OPT4"  # ids preservados (não recriados)


def test_remote_columns_reads_published_options():
    adapter = FakeGqlAdapter(options=_opts("backlog", "revisao", "done"))
    adapter._projects["entrega"] = {
        "project_id": "PROJ1", "status_field_id": "FIELD1",
        "options": {o["name"]: o["id"] for o in adapter._options},
    }
    assert adapter.remote_columns("entrega") == ["backlog", "revisao", "done"]
