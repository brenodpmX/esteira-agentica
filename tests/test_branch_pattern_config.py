"""
Casos de Teste — F1.1 (E1): validação de `branch_pattern` por flow.

E1: cada flow do pipe.yml (exceto `base`) define um `branch_pattern` (template
legível do nome da branch, no formato `<prefix>/<id>-<slug>`). A partir de F1.1
o campo é OBRIGATÓRIO: o agent.py não monta mais o nome — passa o padrão como
instrução e o agente cria a branch conforme (E3).

Valida (`_validate_git`):
  - flow SEM branch_pattern: ConfigError (obrigatório)
  - flow com branch_pattern string válida: aceito
  - flow com branch_pattern vazio / não-string: ConfigError
  - `base` não precisa de branch_pattern
"""

import unittest

from src.core.config import _validate_git, ConfigError


def _git(flow_extra: dict) -> dict:
    flow = {
        "base": "main",
        "story": {"prefix": "story", "create": "main", "merge": "main"},
    }
    flow["story"].update(flow_extra)
    return {"repo": {"main": "git@github.com:u/r.git"}, "flow": flow}


class TestBranchPatternValidation(unittest.TestCase):

    def test_sem_branch_pattern_falha(self):
        # Obrigatório a partir de F1.1: ausência deve falhar.
        with self.assertRaises(ConfigError):
            _validate_git(_git({}))

    def test_branch_pattern_valido_ok(self):
        try:
            _validate_git(_git({"branch_pattern": "story/{id}-{slug}"}))
        except ConfigError as e:
            self.fail(f"branch_pattern válido não deveria falhar: {e}")

    def test_branch_pattern_vazio_falha(self):
        with self.assertRaises(ConfigError):
            _validate_git(_git({"branch_pattern": "   "}))

    def test_branch_pattern_nao_string_falha(self):
        with self.assertRaises(ConfigError):
            _validate_git(_git({"branch_pattern": 123}))

    def test_base_nao_exige_branch_pattern(self):
        # `base` é apenas a branch raiz, não um flow com padrão de nome.
        git = {
            "repo": {"main": "git@github.com:u/r.git"},
            "flow": {
                "base": "main",
                "story": {"prefix": "story", "branch_pattern": "story/{id}-{slug}"},
            },
        }
        try:
            _validate_git(git)
        except ConfigError as e:
            self.fail(f"`base` não deveria exigir branch_pattern: {e}")

    def test_mensagem_de_erro_referencia_o_flow(self):
        try:
            _validate_git(_git({"branch_pattern": ""}))
            self.fail("esperava ConfigError")
        except ConfigError as e:
            self.assertIn("story", str(e))
            self.assertIn("branch_pattern", str(e))

    def test_ausencia_referencia_o_flow(self):
        try:
            _validate_git(_git({}))
            self.fail("esperava ConfigError")
        except ConfigError as e:
            self.assertIn("story", str(e))
            self.assertIn("branch_pattern", str(e))


if __name__ == "__main__":
    unittest.main()
