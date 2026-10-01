"""Matriz fixa de cenários com registro de medição (CA-15).

Matriz = 5 fluxos de Git × {com transição, sem transição} × {com agente
auxiliar (agent-hub), sem} = 20 combinações.

CT-28 — existe exatamente um registro por combinação, com campos obrigatórios
CT-29 — os campos de medição têm os tipos corretos em todas as combinações
"""

import itertools
from pathlib import Path
from unittest.mock import patch

import pytest

from tests._composicao_helpers import (
    canonical_config, make_task, FakeAdapterNoTokens,
)

FLOWS = ["create", "use", "merge", "create-merge", "no-branch"]
TRANSICAO = [True, False]
AUX = [True, False]
MATRIZ = list(itertools.product(FLOWS, TRANSICAO, AUX))


def _write_steering(tmp_path: Path) -> Path:
    steering = tmp_path / ".kiro" / "steering" / "esteira.md"
    steering.parent.mkdir(parents=True, exist_ok=True)
    steering.write_text("---\ninclusion: always\n---\n# ctx\n", encoding="utf-8")
    return steering


def _record_for(tmp_path, gitevents, com_transicao, com_aux):
    import src.__main__ as main
    config = canonical_config()
    # agente auxiliar: agent-hub mapeado + label na issue
    col_overrides = {}
    issue_labels = None
    if com_aux:
        col_overrides["agent-hub"] = {"low": "dev"}
        issue_labels = ["agent-hub-low"]
    change = {"advance": "execucao-testes"} if com_transicao else {}
    # Para use/merge, a branch já existe (anotação); para create/create-merge
    # resolvemos do pattern. no-branch não usa branch.
    body = None
    if gitevents in ("use", "merge"):
        body = "# foo\n\nDesc.\n\n📝\nbranch: feature/308-foo\n"
    task = make_task(
        tmp_path, gitevents=gitevents, col_overrides=col_overrides,
        change=change, issue_labels=issue_labels, body=body,
    )
    boards_dir = tmp_path / ".pipe" / "boards"
    steering = _write_steering(tmp_path)
    with patch("src.core.agent.BOARDS_DIR", boards_dir), \
         patch("src.__main__.STEERING_FILE", steering):
        from src.core.agent import build_prompt
        prompt = build_prompt(config, task)
        return main.compose_execution_record(
            FakeAdapterNoTokens(), prompt, None, task["column"], task["issue"]
        )


class TestMatrizMedicao:

    @pytest.mark.parametrize("gitevents,com_transicao,com_aux", MATRIZ)
    def test_registro_presente_com_campos_obrigatorios(
            self, tmp_path, gitevents, com_transicao, com_aux):
        rec = _record_for(tmp_path, gitevents, com_transicao, com_aux)
        for campo in ("prompt_dinamico", "contexto_sempre_carregado",
                      "total_sempre_carregado", "referencias_sob_demanda_incluidas",
                      "instrucoes_obrigatorias_carregadas", "tokens_entrada",
                      "execucao", "adapter"):
            assert campo in rec, f"campo '{campo}' ausente para {gitevents}/{com_transicao}/{com_aux}"

    def test_vinte_combinacoes(self):
        assert len(MATRIZ) == 20


class TestMatrizTipos:

    @pytest.mark.parametrize("gitevents,com_transicao,com_aux", MATRIZ)
    def test_tipos_corretos(self, tmp_path, gitevents, com_transicao, com_aux):
        rec = _record_for(tmp_path, gitevents, com_transicao, com_aux)
        for bloco in ("prompt_dinamico", "contexto_sempre_carregado"):
            for metr in ("caracteres", "palavras", "linhas"):
                assert isinstance(rec[bloco][metr], int)
        for metr in ("caracteres", "palavras"):
            assert isinstance(rec["total_sempre_carregado"][metr], int)
        assert isinstance(rec["referencias_sob_demanda_incluidas"], list)
        assert rec["tokens_entrada"] is None or isinstance(rec["tokens_entrada"], int)
        assert isinstance(rec["instrucoes_obrigatorias_carregadas"], bool)
