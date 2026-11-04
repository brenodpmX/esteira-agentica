"""
Classificação de erro de sincronismo: categoria 'corrigivel_pelo_agente' (HTTP 422 /
Validation Failed). A escalação e o fail-stop (antiga remediação E4) pertencem ao
circuit-breaker de sincronismo (#309) — ver tests/test_sync_circuit_breaker.py.
"""

import unittest

from src.core.sync import classify_error
from src.core.board import PenaltyException


class TestClassifyError(unittest.TestCase):

    def test_validation_failed_e_corrigivel(self):
        self.assertEqual(classify_error(Exception("HTTP 422: Validation Failed")),
                         "corrigivel_pelo_agente")

    def test_422_e_corrigivel(self):
        self.assertEqual(classify_error(Exception("gh: 422: Unprocessable")),
                         "corrigivel_pelo_agente")

    def test_penalty_e_rate_limit(self):
        self.assertEqual(classify_error(PenaltyException(10)), "rate_limit")

    def test_issue_fantasma_e_definitivo(self):
        self.assertEqual(
            classify_error(Exception("Could not resolve to an issue or pull request")),
            "definitivo")

    def test_outro_erro_e_transitorio(self):
        self.assertEqual(classify_error(Exception("timeout de rede")), "transitorio")

    def test_definitivo_tem_precedencia_sobre_corrigivel(self):
        # Mensagem com ambos: 'não pertence' (definitivo) vence.
        self.assertEqual(
            classify_error(Exception("não pertence a este board; validation failed")),
            "definitivo")


if __name__ == "__main__":
    unittest.main()
