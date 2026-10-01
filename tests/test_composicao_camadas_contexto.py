"""Metadados de projeto e proteção do contexto persistente (CA-12 / CA-14 / RN-02).

CT-23 — metadados de projeto (nome, descrição, humanos) no contexto persistente
CT-26 — contexto persistente da raiz protegido contra escrita (no prompt)
CT-27 — integridade do contexto persistente reescrita se divergir
"""

from pathlib import Path
from unittest.mock import patch

from src.core import context_generator
from src.core.context_generator import _build_content, ensure_steering_integrity
from tests._composicao_helpers import canonical_config, make_task, prompt_for


class TestMetadadosProjeto:

    def test_tres_metadados_no_contexto(self):
        config = canonical_config()
        config["project"] = {
            "name": "Projeto X",
            "summary": "Descrição do projeto X.",
            "humans": [{"name": "Ana", "role": "arquiteta"},
                       {"name": "Bob", "role": "revisor"}],
        }
        content = _build_content(config)
        assert "Projeto X" in content           # nome
        assert "Descrição do projeto X." in content  # descrição (summary)
        assert "Ana" in content and "arquiteta" in content  # humano + função
        assert "Bob" in content and "revisor" in content

    def test_sem_humanos_ainda_tem_nome_e_descricao(self):
        config = canonical_config()
        config["project"] = {"name": "Y", "summary": "resumo Y"}
        content = _build_content(config)
        assert "Y" in content
        assert "resumo Y" in content


class TestContextoProtegidoNoPrompt:

    def test_steering_entre_os_protegidos(self):
        # O contexto persistente (.kiro/steering/**/*.md) consta da lista de
        # protegidos emitida no próprio steering.
        content = _build_content(canonical_config())
        assert ".kiro/steering/**/*.md" in content

    def test_steering_nunca_aparece_como_gravavel_no_prompt(self, tmp_path):
        config = canonical_config()
        prompt = prompt_for(tmp_path, config, make_task(tmp_path))
        # O prompt dinâmico não instrui escrever no steering.
        assert "esteira.md" not in prompt
        assert ".kiro/steering" not in prompt


class TestIntegridadeContexto:

    def _setup_steering(self, tmp_path: Path) -> Path:
        steering = tmp_path / ".kiro" / "steering" / "esteira.md"
        steering.parent.mkdir(parents=True, exist_ok=True)
        return steering

    def test_reescreve_quando_diverge(self, tmp_path):
        config = canonical_config()
        steering = self._setup_steering(tmp_path)
        with patch.object(context_generator, "STEERING_FILE", steering):
            steering.write_text("conteúdo corrompido pelo agente\n", encoding="utf-8")
            diverged = ensure_steering_integrity(config)
            assert diverged is True
            restored = steering.read_text(encoding="utf-8")
        assert "conteúdo corrompido" not in restored
        assert restored == _build_content(config)

    def test_integro_retorna_false(self, tmp_path):
        config = canonical_config()
        steering = self._setup_steering(tmp_path)
        with patch.object(context_generator, "STEERING_FILE", steering):
            steering.write_text(_build_content(config), encoding="utf-8")
            assert ensure_steering_integrity(config) is False
