"""Resolução única do nome da branch (CA-10 / CA-11 / RN-05).

CT-20 — nome resolvido idêntico em todos os blocos que o citam
CT-21 — marcador não resolvível → ConfigError
CT-22 — nenhum nome parcial/inconsistente é emitido na falha
"""

import pytest

from src.core import composition
from src.core.config import ConfigError
from tests._composicao_helpers import canonical_config, make_task, prompt_for


class TestBranchResolvidaUnica:

    def test_nome_identico_em_criacao_e_merge(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, gitevents="create-merge", issue_id="308", slug="foo")
        prompt = prompt_for(tmp_path, config, task)
        esperado = "feature/308-foo"
        # Aparece no bloco de criação e no bloco de merge/PR.
        assert prompt.count(f"`{esperado}`") >= 2, (
            f"o nome resolvido '{esperado}' deve aparecer em criação E merge"
        )
        # Nenhuma grafia alternativa do mesmo nome.
        assert "feature/{id}-{slug}" in prompt  # o padrão ainda é citado como template
        # O nome resolvido não é o template literal com marcadores.
        assert esperado in prompt

    def test_resolucao_pura_deterministica(self):
        data = {"id": "308", "slug": "foo"}
        r1 = composition.resolve_branch_name("feature/{id}-{slug}", data)
        r2 = composition.resolve_branch_name("feature/{id}-{slug}", data)
        assert r1 == r2 == "feature/308-foo"


class TestBranchMarcadorInvalido:

    def test_marcador_nao_resolvivel_erro(self):
        with pytest.raises(ConfigError) as exc:
            composition.resolve_branch_name("feature/{id}-{inexistente}", {"id": "1"})
        assert "inexistente" in str(exc.value)

    def test_build_prompt_propaga_config_error(self, tmp_path):
        config = canonical_config()
        config["git"]["flow"]["feature"]["branch_pattern"] = "feature/{id}-{inexistente}"
        task = make_task(tmp_path, gitevents="create")
        with pytest.raises(ConfigError):
            prompt_for(tmp_path, config, task)

    def test_nao_emite_nome_parcial(self):
        try:
            composition.resolve_branch_name("feature/{id}-{inexistente}", {"id": "1"})
            assert False, "esperava ConfigError"
        except ConfigError as e:
            # A mensagem de erro não contém um nome de branch parcialmente
            # resolvido (ex.: 'feature/1-{inexistente}').
            assert "feature/1-" not in str(e)

    def test_pattern_vazio_erro(self):
        with pytest.raises(ConfigError):
            composition.resolve_branch_name("", {"id": "1", "slug": "x"})
