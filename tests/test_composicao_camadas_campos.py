"""Objetivo e passo a passo em campos próprios (CA-9).

CT-18 — ambos presentes aparecem em campos distintos
CT-19 — passo a passo ausente mantém a etapa válida (sem a seção Passos)
"""

from tests._composicao_helpers import canonical_config, make_task, prompt_for


class TestObjetivoPasso:

    def test_ambos_presentes(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, col_overrides={
            "target-prompt": "Implementar a feature X",
            "step-prompt": "1. Ler issue\n2. Codar\n3. Testar",
        })
        prompt = prompt_for(tmp_path, config, task)
        assert "**Objetivo:** Implementar a feature X" in prompt
        assert "**Passos:**" in prompt
        assert "1. Ler issue" in prompt
        # Objetivo e Passos são campos distintos (ordem: objetivo antes de passos).
        assert prompt.index("**Objetivo:**") < prompt.index("**Passos:**")

    def test_so_objetivo(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, col_overrides={
            "target-prompt": "Só o objetivo",
            "step-prompt": "",
        })
        prompt = prompt_for(tmp_path, config, task)
        assert "**Objetivo:** Só o objetivo" in prompt
        assert "**Passos:**" not in prompt

    def test_passo_ausente_chave_inexistente(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, col_overrides={"target-prompt": "Objetivo"})
        task["column"].pop("step-prompt", None)
        prompt = prompt_for(tmp_path, config, task)
        assert "**Passos:**" not in prompt
        assert isinstance(prompt, str) and len(prompt) > 100
