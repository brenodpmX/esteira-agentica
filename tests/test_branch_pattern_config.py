"""
Casos de Teste — F0.5 (E1): validação de `branch_pattern` por flow.

E1: cada flow do pipe.yml define um `branch_pattern` (template legível do nome
da branch). A obrigatoriedade e o uso descritivo em build_prompt (E3) entram
junto com F1.1 (quando o campo chega no pipe.yml). Por ora a validação é
NÃO-obrigatória, mas SE `branch_pattern` estiver presente deve ser string
não-vazia.

Valida (`_validate_git`):
  - flow sem branch_pattern: não levanta erro (não-obrigatório ainda)
  - flow com branch_pattern string válida: aceito
  - flow com branch_pattern vazio / não-string: ConfigError
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

    def test_sem_branch_pattern_ok(self):
        # Não-obrigatório ainda: ausência não deve falhar.
        try:
            _validate_git(_git({}))
        except ConfigError as e:
            self.fail(f"branch_pattern ausente não deveria falhar: {e}")

    def test_branch_pattern_valido_ok(self):
        try:
            _validate_git(_git({"branch_pattern": "story/#{id}-{nome}"}))
        except ConfigError as e:
            self.fail(f"branch_pattern válido não deveria falhar: {e}")

    def test_branch_pattern_vazio_falha(self):
        with self.assertRaises(ConfigError):
            _validate_git(_git({"branch_pattern": "   "}))

    def test_branch_pattern_nao_string_falha(self):
        with self.assertRaises(ConfigError):
            _validate_git(_git({"branch_pattern": 123}))

    def test_mensagem_de_erro_referencia_o_flow(self):
        try:
            _validate_git(_git({"branch_pattern": ""}))
            self.fail("esperava ConfigError")
        except ConfigError as e:
            self.assertIn("story", str(e))
            self.assertIn("branch_pattern", str(e))


if __name__ == "__main__":
    unittest.main()
