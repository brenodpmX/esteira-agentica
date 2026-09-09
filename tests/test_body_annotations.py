"""
Casos de Teste — F0.4 (E2): parser das anotações do -body.md (5 partes)

Estrutura do -body.md:
  corpo · 📝 · anotações · @--- · comandos

A esteira NÃO escreve no -body.md; apenas interpreta. Este parser reconhece a
região de anotações (entre `📝` e `@---`): pai, branch pai, branch, boards.

Valida:
  - parse_annotations lê pai (id + nome), branch pai, branch, boards
  - branch "(ainda não criada)" ⇒ None
  - split_annotations separa corpo das anotações no `📝`
  - parse_body devolve as 5 partes coerentes (corpo, anotações, comandos)
  - sem `📝`: body inteiro é corpo, anotações vazias
"""

import unittest

from src.core.commands import (
    IssueAnnotations,
    parse_annotations,
    split_annotations,
    parse_body,
)


class TestParseAnnotations(unittest.TestCase):

    def test_pai_com_id_e_nome(self):
        annot = parse_annotations("pai: #10 - Implementar login")
        self.assertEqual(annot.parent, "10")
        self.assertEqual(annot.parent_name, "Implementar login")

    def test_pai_so_id(self):
        annot = parse_annotations("pai: #42")
        self.assertEqual(annot.parent, "42")
        self.assertIsNone(annot.parent_name)

    def test_branch_pai(self):
        annot = parse_annotations("branch pai: feature/10-login")
        self.assertEqual(annot.parent_branch, "feature/10-login")

    def test_branch_trabalho(self):
        annot = parse_annotations("branch: feature/11-jwt")
        self.assertEqual(annot.branch, "feature/11-jwt")

    def test_branch_ainda_nao_criada_vira_none(self):
        annot = parse_annotations("branch: (ainda não criada)")
        self.assertIsNone(annot.branch)

    def test_boards_lista(self):
        annot = parse_annotations("boards: task, bug")
        self.assertEqual(annot.boards, ["task", "bug"])

    def test_todas_as_chaves(self):
        text = (
            "pai: #10 - Épico X\n"
            "branch pai: feature/10-epico\n"
            "branch: feature/11-story\n"
            "boards: task\n"
        )
        annot = parse_annotations(text)
        self.assertEqual(annot.parent, "10")
        self.assertEqual(annot.parent_name, "Épico X")
        self.assertEqual(annot.parent_branch, "feature/10-epico")
        self.assertEqual(annot.branch, "feature/11-story")
        self.assertEqual(annot.boards, ["task"])

    def test_chave_desconhecida_ignorada(self):
        annot = parse_annotations("qualquer: coisa\nbranch: b1")
        self.assertEqual(annot.branch, "b1")
        self.assertTrue(annot.parent is None)

    def test_vazio(self):
        self.assertTrue(parse_annotations("").is_empty())


class TestSplitAnnotations(unittest.TestCase):

    def test_separa_corpo_e_anotacoes(self):
        body = "Corpo da issue.\n\n📝\nbranch: feature/1-x\nboards: task"
        corpo, annot = split_annotations(body)
        self.assertEqual(corpo, "Corpo da issue.")
        self.assertEqual(annot.branch, "feature/1-x")
        self.assertEqual(annot.boards, ["task"])

    def test_sem_separador_tudo_e_corpo(self):
        corpo, annot = split_annotations("Só corpo, sem anotações.")
        self.assertEqual(corpo, "Só corpo, sem anotações.")
        self.assertTrue(annot.is_empty())

    def test_ultimo_separador_vence(self):
        body = "Corpo\n📝\nlixo\n📝\nbranch: b2"
        corpo, annot = split_annotations(body)
        self.assertEqual(annot.branch, "b2")


class TestParseBody(unittest.TestCase):

    def test_cinco_partes(self):
        raw = (
            "Implementar endpoint de login.\n"
            "\n"
            "📝\n"
            "pai: #10 - Épico Auth\n"
            "branch pai: feature/10-auth\n"
            "branch: feature/11-login\n"
            "boards: task\n"
            "@---\n"
            "/parent #10\n"
            "/blocks #10\n"
        )
        corpo, annot, cmds = parse_body(raw)
        self.assertEqual(corpo, "Implementar endpoint de login.")
        self.assertEqual(annot.parent, "10")
        self.assertEqual(annot.parent_branch, "feature/10-auth")
        self.assertEqual(annot.branch, "feature/11-login")
        self.assertEqual(annot.boards, ["task"])
        self.assertEqual(cmds.parent, "10")
        self.assertEqual(cmds.blocks, ["10"])

    def test_corpo_nao_contem_anotacoes_nem_comandos(self):
        raw = "Corpo.\n📝\nbranch: b1\n@---\n/labels x"
        corpo, annot, cmds = parse_body(raw)
        self.assertNotIn("branch:", corpo)
        self.assertNotIn("@---", corpo)
        self.assertNotIn("/labels", corpo)

    def test_sem_anotacoes_so_comandos(self):
        raw = "Corpo.\n@---\n/labels x"
        corpo, annot, cmds = parse_body(raw)
        self.assertEqual(corpo, "Corpo.")
        self.assertTrue(annot.is_empty())
        self.assertEqual(cmds.labels, ["x"])

    def test_sem_nada(self):
        corpo, annot, cmds = parse_body("Apenas o corpo.")
        self.assertEqual(corpo, "Apenas o corpo.")
        self.assertTrue(annot.is_empty())
        self.assertTrue(cmds.is_empty())


if __name__ == "__main__":
    unittest.main()
