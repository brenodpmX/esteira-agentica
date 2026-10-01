"""Prompt de continuidade (CA-13).

CT-24 — instrui continuar de onde parou e aponta arquivos + transição
CT-25 — não é maior, em palavras, que a primeira execução para a mesma tarefa
"""

from unittest.mock import patch

from src.core.agent import build_continuation_prompt
from tests._composicao_helpers import canonical_config, make_task, prompt_for


def _continuation(tmp_path, config, task) -> str:
    boards_dir = tmp_path / ".pipe" / "boards"
    with patch("src.core.agent.BOARDS_DIR", boards_dir):
        return build_continuation_prompt(config, task)


class TestContinuidadeConteudo:

    def test_instrui_continuar_e_aponta_arquivos(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path)
        cont = _continuation(tmp_path, config, task)
        assert "já trabalhou nesta etapa" in cont
        assert "não recomece do zero" in cont
        assert "-history.md" in cont
        assert "-addcomment.md" in cont
        assert "Transição de coluna" in cont
        assert "advance" in cont


class TestContinuidadeTamanho:

    def test_continuacao_nao_maior_em_palavras(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path)
        primeira = prompt_for(tmp_path, config, task)
        cont = _continuation(tmp_path, config, task)
        assert len(cont.split()) <= len(primeira.split()), (
            f"continuação={len(cont.split())} palavras não deve exceder "
            f"primeira={len(primeira.split())} palavras"
        )
