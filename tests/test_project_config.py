"""
Casos de Teste — F1.1 (item "Visão geral"): validação da seção `project`.

Decisão aprovada: `project.name` e `project.summary` são OBRIGATÓRIOS no
pipe.yml; `project.humans` é OPCIONAL (lista de {name, role}). O gerador de
contexto injeta esses valores nas seções 'Projeto' e 'Papéis humanos' do
steering.

Valida (`_validate_project`):
  - name/summary ausentes ou vazios → ConfigError
  - humans ausente → OK (opcional)
  - humans presente com item malformado → ConfigError
"""

import unittest

from src.core.config import _validate_project, ConfigError


def _project(**over) -> dict:
    base = {"name": "Esteira Agêntica", "summary": "Resumo do projeto."}
    base.update(over)
    return base


class TestProjectValidation(unittest.TestCase):

    def test_name_e_summary_validos_ok(self):
        try:
            _validate_project(_project())
        except ConfigError as e:
            self.fail(f"project válido não deveria falhar: {e}")

    def test_name_ausente_falha(self):
        with self.assertRaises(ConfigError):
            _validate_project({"summary": "x"})

    def test_summary_ausente_falha(self):
        with self.assertRaises(ConfigError):
            _validate_project({"name": "x"})

    def test_name_vazio_falha(self):
        with self.assertRaises(ConfigError):
            _validate_project(_project(name="   "))

    def test_summary_vazio_falha(self):
        with self.assertRaises(ConfigError):
            _validate_project(_project(summary=""))

    def test_nao_dict_falha(self):
        with self.assertRaises(ConfigError):
            _validate_project("não é mapa")

    def test_humans_ausente_ok(self):
        try:
            _validate_project(_project())
        except ConfigError as e:
            self.fail(f"humans é opcional: {e}")

    def test_humans_lista_valida_ok(self):
        try:
            _validate_project(_project(humans=[{"name": "Breno", "role": "dono"}]))
        except ConfigError as e:
            self.fail(f"humans válido não deveria falhar: {e}")

    def test_humans_nao_lista_falha(self):
        with self.assertRaises(ConfigError):
            _validate_project(_project(humans={"name": "Breno", "role": "dono"}))

    def test_humans_item_sem_role_falha(self):
        with self.assertRaises(ConfigError):
            _validate_project(_project(humans=[{"name": "Breno"}]))

    def test_humans_item_sem_name_falha(self):
        with self.assertRaises(ConfigError):
            _validate_project(_project(humans=[{"role": "dono"}]))

    def test_mensagem_referencia_o_campo(self):
        try:
            _validate_project({"name": "x"})
            self.fail("esperava ConfigError")
        except ConfigError as e:
            self.assertIn("summary", str(e))


if __name__ == "__main__":
    unittest.main()
