"""
Casos de Teste — F0.6 (E9): fechamento como label do adapter (hexagonal).

O core é agnóstico: só adiciona/remove a label `completed`/`not_planned`. O
adapter do board (GitHub) interpreta essa label e fecha a issue COM O MOTIVO.
Reabrir não existe (ação humana).

Valida:
  - _interpret_closing_labels fecha com reason=completed / not_planned
  - not_planned tem precedência sobre completed
  - label não-terminal não fecha
  - close_issue monta `gh issue close --reason <motivo>`
  - o adapter não expõe mais reopen_issue (E9)
"""

import unittest
from unittest.mock import patch

from src.adapters.github_board import GitHubBoardAdapter


def _bare_adapter() -> GitHubBoardAdapter:
    """Instância sem __init__ (evita dependências de config/subprocess)."""
    adapter = object.__new__(GitHubBoardAdapter)
    return adapter


class TestInterpretClosingLabels(unittest.TestCase):

    def _adapter_capturando_close(self):
        adapter = _bare_adapter()
        calls = []
        adapter.close_issue = lambda b, i, reason=None: calls.append((b, i, reason))
        return adapter, calls

    def test_completed_fecha_com_reason_completed(self):
        adapter, calls = self._adapter_capturando_close()
        adapter._interpret_closing_labels("board", "5", ["backend", "completed"])
        self.assertEqual(calls, [("board", "5", "completed")])

    def test_not_planned_fecha_com_reason_not_planned(self):
        adapter, calls = self._adapter_capturando_close()
        adapter._interpret_closing_labels("board", "7", ["not_planned"])
        self.assertEqual(calls, [("board", "7", "not_planned")])

    def test_not_planned_tem_precedencia(self):
        adapter, calls = self._adapter_capturando_close()
        adapter._interpret_closing_labels("board", "9", ["completed", "not_planned"])
        self.assertEqual(calls, [("board", "9", "not_planned")])

    def test_label_comum_nao_fecha(self):
        adapter, calls = self._adapter_capturando_close()
        adapter._interpret_closing_labels("board", "1", ["backend", "security"])
        self.assertEqual(calls, [])

    def test_sem_labels_nao_fecha(self):
        adapter, calls = self._adapter_capturando_close()
        adapter._interpret_closing_labels("board", "1", [])
        self.assertEqual(calls, [])


class TestCloseIssueReason(unittest.TestCase):

    def _adapter(self):
        adapter = _bare_adapter()
        adapter._repo = "owner/repo"
        adapter._throttle_value = 0
        adapter._penalty_check = lambda: None
        adapter._assert_belongs_to_board = lambda b, i: True
        return adapter

    def test_close_com_reason_monta_flag(self):
        adapter = self._adapter()
        captured = {}
        adapter._gh = lambda *a, **k: captured.setdefault("args", list(a))
        adapter.close_issue("board", "5", reason="not_planned")
        self.assertIn("--reason", captured["args"])
        # O token interno `not_planned` é traduzido para o valor aceito pelo
        # `gh issue close --reason`, que é `not planned` (com espaço).
        self.assertIn("not planned", captured["args"])
        self.assertNotIn("not_planned", captured["args"])
        self.assertIn("close", captured["args"])

    def test_close_com_reason_completed_monta_flag(self):
        adapter = self._adapter()
        captured = {}
        adapter._gh = lambda *a, **k: captured.setdefault("args", list(a))
        adapter.close_issue("board", "5", reason="completed")
        self.assertIn("--reason", captured["args"])
        self.assertIn("completed", captured["args"])

    def test_close_sem_reason_nao_inclui_flag(self):
        adapter = self._adapter()
        captured = {}
        adapter._gh = lambda *a, **k: captured.setdefault("args", list(a))
        adapter.close_issue("board", "5")
        self.assertNotIn("--reason", captured["args"])

    def test_close_reason_invalido_ignorado(self):
        adapter = self._adapter()
        captured = {}
        adapter._gh = lambda *a, **k: captured.setdefault("args", list(a))
        adapter.close_issue("board", "5", reason="qualquer")
        self.assertNotIn("--reason", captured["args"])


class TestSemReopen(unittest.TestCase):

    def test_adapter_nao_expoe_reopen_issue(self):
        """E9: reabrir não existe na esteira."""
        self.assertFalse(hasattr(GitHubBoardAdapter, "reopen_issue"))


if __name__ == "__main__":
    unittest.main()
