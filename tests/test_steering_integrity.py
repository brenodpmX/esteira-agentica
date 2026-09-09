"""
Casos de Teste — F0.9 (P1.5): guarda de integridade do steering + config readonly.

- config._validate_agents NÃO cria mais arquivos de contexto (persona): apenas
  valida existência e não-vazio, orientando o operador.
- context_generator.ensure_steering_integrity: reescreve o steering se ausente
  ou divergente (retorna True), no-op se íntegro (retorna False).
"""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.core.config import _validate_agents, ConfigError
from src.core import context_generator as cg


_AGENTS = {"kiro-cli": {"dev": {"name": "Eng"}}}


class TestConfigNaoCriaContexto(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self._old = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self._old)
        self.tmp.cleanup()

    def test_contexto_ausente_falha_sem_criar(self):
        with self.assertRaises(ConfigError):
            _validate_agents(_AGENTS)
        # NÃO deve ter criado o arquivo nem o diretório.
        self.assertFalse(Path("contexts/kiro-cli/dev.md").exists())

    def test_contexto_vazio_falha(self):
        p = Path("contexts/kiro-cli/dev.md")
        p.parent.mkdir(parents=True)
        p.write_text("   \n", encoding="utf-8")
        with self.assertRaises(ConfigError):
            _validate_agents(_AGENTS)

    def test_contexto_preenchido_ok(self):
        p = Path("contexts/kiro-cli/dev.md")
        p.parent.mkdir(parents=True)
        p.write_text("Persona do engenheiro.\n", encoding="utf-8")
        try:
            _validate_agents(_AGENTS)
        except ConfigError as e:
            self.fail(f"não deveria falhar com contexto preenchido: {e}")


class TestSteeringIntegrity(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self.steering = self.cwd / ".kiro" / "steering" / "esteira.md"
        self.config = {
            "git": {"repo": {"main": "x"}, "flow": {"base": "main"}},
            "boards": {"platform": "github"},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _patch(self):
        return patch("src.core.context_generator.STEERING_FILE", self.steering)

    def test_ausente_reescreve_e_retorna_true(self):
        with self._patch():
            diverged = cg.ensure_steering_integrity(self.config)
        self.assertTrue(diverged)
        self.assertTrue(self.steering.exists())
        self.assertIn("inclusion: always", self.steering.read_text())

    def test_integro_retorna_false(self):
        with self._patch():
            cg.ensure_steering_integrity(self.config)   # cria
            diverged = cg.ensure_steering_integrity(self.config)  # já íntegro
        self.assertFalse(diverged)

    def test_divergente_reescreve_e_retorna_true(self):
        with self._patch():
            cg.ensure_steering_integrity(self.config)
            self.steering.write_text("CORROMPIDO PELO AGENTE\n", encoding="utf-8")
            diverged = cg.ensure_steering_integrity(self.config)
        self.assertTrue(diverged)
        self.assertNotIn("CORROMPIDO", self.steering.read_text())
        self.assertIn("inclusion: always", self.steering.read_text())


if __name__ == "__main__":
    unittest.main()
