"""
Casos de Teste — F0.8 (E4): loop de remediação para erros corrigíveis pelo agente.

- classify_error ganha categoria 'corrigivel_pelo_agente' (HTTP 422 / Validation
  Failed) — NÃO entra no retry cego.
- apply_changes sinaliza (RemediationSignal) e remove o item da fila (sem
  dead-letter imediato).
- __main__ orquestra: 1 remediação por alvo → fail-stop na reincidência.
- build_remediation_prompt injeta os erros e NÃO pede refazer a tarefa.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.core.sync import classify_error, RemediationSignal, RemediationFailStop
from src.core.board import PenaltyException
from src.core.agent import build_remediation_prompt


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


class TestBuildRemediationPrompt(unittest.TestCase):

    def test_inclui_erros_e_nao_pede_refazer(self):
        p = build_remediation_prompt({}, {}, "422: blocked_by inválido #999")
        self.assertIn("422: blocked_by inválido #999", p)
        self.assertIn("Não refaça a tarefa", p)
        self.assertIn("Erros da sincronização", p)

    def test_sem_erros_usa_placeholder(self):
        p = build_remediation_prompt({}, {}, "")
        self.assertIn("(sem detalhes)", p)


class TestApplyChangesSignalsRemediation(unittest.TestCase):
    """apply_changes deve coletar RemediationSignal e remover o item da fila
    (sem retry cego) quando o erro é corrigível pelo agente."""

    def test_corrigivel_gera_signal_e_remove_da_fila(self):
        from src.core import sync
        from src.core.change_queue import ChangeQueue
        from src.core.board import ChangeItem, SyncEvent

        item = ChangeItem.of(SyncEvent.CHANGE_UP.value, id="5", board="task")

        queue = MagicMock(spec=ChangeQueue)
        # getNext: item, depois None (fila esvazia após remoção).
        queue.getNext.side_effect = [item, None]

        board_obj = MagicMock()

        def raise_422(*a, **k):
            raise Exception("HTTP 422: Validation Failed")

        with patch.object(sync, "_apply_change_up", side_effect=raise_422):
            signals = sync.apply_changes(board_obj, queue, {})

        self.assertEqual(len(signals), 1)
        self.assertIsInstance(signals[0], RemediationSignal)
        self.assertEqual(signals[0].issue_id, "5")
        self.assertEqual(signals[0].board_id, "task")
        queue.remove.assert_called_with(item.uuid)


class TestRemediateOrchestration(unittest.TestCase):
    """__main__.remediate_pending: 1 remediação por alvo; fail-stop na reincidência."""

    def setUp(self):
        import src.__main__ as m
        m._remediated_targets.clear()

    def _signal(self):
        return RemediationSignal(board_id="task", issue_id="5",
                                 event="change-up", reason="422: rel inválida")

    def test_primeira_remediacao_chama_agente(self):
        import src.__main__ as m
        called = {}

        def fake_call(config, task, remediation_errors=None):
            called["errors"] = remediation_errors
            called["task"] = task

        with patch.object(m, "_build_task_for_target", return_value={"x": 1}), \
             patch.object(m, "call_agent", fake_call):
            m.remediate_pending({}, [self._signal()])

        self.assertEqual(called["errors"], "422: rel inválida")
        self.assertIn(("task", "5"), m._remediated_targets)

    def test_reincidencia_e_fail_stop(self):
        import src.__main__ as m
        m._remediated_targets.add(("task", "5"))
        with patch.object(m, "call_agent") as mock_call:
            with self.assertRaises(RemediationFailStop):
                m.remediate_pending({}, [self._signal()])
            mock_call.assert_not_called()

    def test_sem_task_e_fail_stop(self):
        import src.__main__ as m
        with patch.object(m, "_build_task_for_target", return_value=None):
            with self.assertRaises(RemediationFailStop):
                m.remediate_pending({}, [self._signal()])


class TestComposeInputRemediation(unittest.TestCase):
    """_compose_input com remediation_prompt.

    - COM sessão confirmada (resuming): envia só os erros (a sessão já carrega
      persona + tarefa).
    - SEM sessão (resuming=False): anexa persona + prompt completo ANTES dos
      erros, para o agente não ficar sem contexto (guarda anti-delírio).
    """

    def _params(self):
        from src.core.agent import AgentParams
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng", model="m",
            issue_id="1", board_id="task", col_id="doing",
            prompt="PROMPT_FULL", work_dir="/tmp",
            context="PERSONA", continuation_prompt="CONT",
            remediation_prompt="ERROS_422",
        )

    def test_remediacao_com_sessao_envia_so_erros(self):
        from src.adapters.kiro_cli_agent import KiroCliAgent
        out = KiroCliAgent()._compose_input(self._params(), resuming=True)
        self.assertEqual(out, "ERROS_422")
        self.assertNotIn("PROMPT_FULL", out)
        self.assertNotIn("PERSONA", out)

    def test_remediacao_sem_sessao_inclui_contexto_completo(self):
        from src.adapters.kiro_cli_agent import KiroCliAgent
        out = KiroCliAgent()._compose_input(self._params(), resuming=False)
        self.assertIn("ERROS_422", out)
        self.assertIn("PROMPT_FULL", out)
        self.assertIn("PERSONA", out)


if __name__ == "__main__":
    unittest.main()
