"""Versionamento incondicional e mensagem de commit/PR (CA-16).

CT-30 — versionamento não é pulado quando o fluxo exige; ausente em no-branch
CT-31 — mensagem de commit/PR descreve a etapa; alvo de merge é o do fluxo
"""

import pytest

from tests._composicao_helpers import canonical_config, make_task, prompt_for


class TestVersionamentoObrigatorio:

    @pytest.mark.parametrize("gitevents", ["create", "use", "merge", "create-merge"])
    def test_secao_versionar_presente_para_fluxos_git(self, tmp_path, gitevents):
        config = canonical_config()
        task = make_task(tmp_path, gitevents=gitevents,
                         body="# foo\n\nDesc.\n\n📝\nbranch: feature/308-foo\n")
        prompt = prompt_for(tmp_path, config, task)
        assert "## Versionar (commit e push)" in prompt
        assert "SEMPRE na branch de trabalho" in prompt

    def test_no_branch_nao_versiona(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, gitevents="no-branch")
        prompt = prompt_for(tmp_path, config, task)
        assert "## Versionar" not in prompt


class TestMensagemReflecteMudanca:

    @pytest.mark.parametrize("gitevents", ["merge", "create-merge"])
    def test_instrui_mensagem_que_descreve_etapa(self, tmp_path, gitevents):
        config = canonical_config()
        task = make_task(tmp_path, gitevents=gitevents,
                         body="# foo\n\nDesc.\n\n📝\nbranch: feature/308-foo\n")
        prompt = prompt_for(tmp_path, config, task)
        assert "mensagem de " in prompt and "descreva esta etapa" in prompt
        # Alvo de merge do fluxo feature é `main`.
        assert "## Abrir merge/PR" in prompt
        assert "para `main`" in prompt
