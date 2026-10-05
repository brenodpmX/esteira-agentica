"""Casos de Teste — captura de consumo via stream-json (kiro-cli 2.27.x).

Desde o kiro-cli 2.27.x o modo texto deixou de imprimir a linha-resumo de
créditos/tempo; o consumo passou a ser exposto apenas em
``--output-format stream-json`` (evento ``metadata.meteringUsage``). Estes testes
cobrem:

- o parser dos eventos ACP (transcript legível + consumo + linha-resumo);
- a captura do consumo em ``_run`` (reportado quando há medição; indisponível
  quando não há);
- a exposição em ``ExecutionResult.consumo`` por ``execute``;
- a gravação do consumo medido no registro de execução (fim-a-fim do wiring).
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

from src.adapters.kiro_cli_agent import KiroCliAgent
from src.core.agent import AgentParams
from src.core.execution_record import Consumo, DISPONIVEL, INDISPONIVEL


def _ev(obj: dict) -> str:
    return json.dumps(obj)


def _stream(metering=None, turn_ms=None, status="success", with_tool=False,
            msg="ok") -> str:
    """Monta um stdout stream-json plausível."""
    lines = [_ev({"type": "runStarted",
                  "data": {"payloadSchema": "acp", "engine": "v2"}})]
    lines.append(_ev({"type": "metadata",
                      "data": {"sessionId": "s", "contextUsagePercentage": 0.8}}))
    if with_tool:
        lines.append(_ev({"type": "sessionUpdate", "data": {"sessionId": "s",
            "update": {"sessionUpdate": "tool_call",
                       "title": "Running: echo hi", "kind": "execute"}}}))
        lines.append(_ev({"type": "sessionUpdate", "data": {"sessionId": "s",
            "update": {"sessionUpdate": "tool_call_update", "status": "completed"}}}))
    for ch in (msg, ):
        lines.append(_ev({"type": "sessionUpdate", "data": {"sessionId": "s",
            "update": {"sessionUpdate": "agent_message_chunk",
                       "content": {"type": "text", "text": ch}}}}))
    final_meta = {"sessionId": "s", "contextUsagePercentage": 1.9}
    if metering is not None:
        final_meta["meteringUsage"] = metering
    if turn_ms is not None:
        final_meta["turnDurationMs"] = turn_ms
    lines.append(_ev({"type": "metadata", "data": final_meta}))
    lines.append(_ev({"type": "runFinished", "data": {"sessionId": "s",
        "status": status, "stopReason": "end_turn", "finalText": msg}}))
    return "\n".join(lines) + "\n"


class TestParseStreamJson(unittest.TestCase):

    def setUp(self):
        self.agent = KiroCliAgent()

    def test_metering_unico_soma_e_unidade(self):
        raw = _stream(metering=[{"value": 0.136, "unit": "credit",
                                 "unitPlural": "credits"}], turn_ms=2861)
        transcript, valor, unidade = self.agent._parse_stream_json(raw)
        self.assertAlmostEqual(valor, 0.136)
        self.assertEqual(unidade, "credit")
        self.assertIn("ok", transcript)
        self.assertIn("▸ Credits: 0.14", transcript)
        self.assertIn("Time: 0m 2s", transcript)
        # A linha-resumo é a última (restaura o comportamento antigo).
        self.assertTrue(transcript.strip().splitlines()[-1].startswith("▸ Credits:"))

    def test_metering_segmentado_eh_somado(self):
        raw = _stream(metering=[{"value": 0.117, "unit": "credit"},
                                {"value": 0.082, "unit": "credit"}], turn_ms=6325)
        _, valor, unidade = self.agent._parse_stream_json(raw)
        self.assertAlmostEqual(valor, 0.199)
        self.assertEqual(unidade, "credit")

    def test_tool_calls_viram_linhas_tool(self):
        raw = _stream(metering=[{"value": 0.2, "unit": "credit"}],
                      with_tool=True, msg="feito")
        transcript, _, _ = self.agent._parse_stream_json(raw)
        self.assertIn("[tool] Running: echo hi", transcript)
        self.assertIn("[tool] status: Completed", transcript)
        self.assertIn("feito", transcript)

    def test_sem_metering_retorna_none(self):
        raw = _stream(metering=None)
        transcript, valor, unidade = self.agent._parse_stream_json(raw)
        self.assertIsNone(valor)
        self.assertIsNone(unidade)
        self.assertNotIn("▸ Credits:", transcript)

    def test_vazio_degrada(self):
        self.assertEqual(self.agent._parse_stream_json(""), ("", None, None))

    def test_linha_nao_json_preservada(self):
        raw = "linha solta\n" + "Error: dispatch failure\n"
        transcript, valor, _ = self.agent._parse_stream_json(raw)
        self.assertIn("dispatch failure", transcript)  # hint sobrevive
        self.assertIsNone(valor)

    def test_run_finished_nao_sucesso_anexa_erro(self):
        raw = _stream(metering=None, status="error")
        transcript, _, _ = self.agent._parse_stream_json(raw)
        self.assertIn("[ERRO] runFinished status=error", transcript)


class TestRunCapturaConsumo(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.esteira = Path(self.tmp.name) / "esteira"
        self.repo = self.esteira / "repo" / "main"
        self.repo.mkdir(parents=True)
        self.steering = self.esteira / ".kiro" / "steering" / "esteira.md"
        self.steering.parent.mkdir(parents=True)
        self.steering.write_text("---\ninclusion: always\n---\n#x\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _params(self):
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng", model="m",
            issue_id="1", board_id="task", col_id="doing",
            prompt="PROMPT_FULL", work_dir=str(self.repo),
            context=None, continuation_prompt=None,
        )

    def _run_with_stdout(self, stdout, returncode=0, stderr=""):
        agent = KiroCliAgent()

        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = returncode
            r.stdout = stdout
            r.stderr = stderr
            return r

        with patch("subprocess.run", side_effect=fake_run), \
             patch("src.adapters.kiro_cli_agent.SessionIndex") as mock_idx, \
             patch("src.adapters.kiro_cli_agent.STEERING_FILE", self.steering), \
             patch.object(agent, "_session_exists", return_value=False), \
             patch.object(agent, "_latest_session_id", return_value=None):
            mock_idx.return_value.get.return_value = None
            out = agent._run(self._params(), self.repo)
        return agent, out

    def test_cmd_usa_stream_json(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            r = MagicMock(); r.returncode = 0; r.stdout = _stream(
                metering=[{"value": 0.1, "unit": "credit"}]); r.stderr = ""
            return r

        agent = KiroCliAgent()
        with patch("subprocess.run", side_effect=fake_run), \
             patch("src.adapters.kiro_cli_agent.SessionIndex") as mock_idx, \
             patch("src.adapters.kiro_cli_agent.STEERING_FILE", self.steering), \
             patch.object(agent, "_session_exists", return_value=False), \
             patch.object(agent, "_latest_session_id", return_value=None):
            mock_idx.return_value.get.return_value = None
            agent._run(self._params(), self.repo)
        self.assertIn("--output-format", captured["cmd"])
        self.assertIn("stream-json", captured["cmd"])

    def test_run_reporta_consumo_quando_ha_metering(self):
        agent, out = self._run_with_stdout(
            _stream(metering=[{"value": 0.5, "unit": "credit"}], turn_ms=1000))
        self.assertIsInstance(agent._last_consumo, Consumo)
        self.assertEqual(agent._last_consumo.disponibilidade, DISPONIVEL)
        self.assertAlmostEqual(agent._last_consumo.valor, 0.5)
        self.assertEqual(agent._last_consumo.unidade, "credit")
        self.assertEqual(agent._last_consumo.origem, "kiro-cli")

    def test_run_indisponivel_sem_metering(self):
        agent, out = self._run_with_stdout(_stream(metering=None))
        self.assertEqual(agent._last_consumo.disponibilidade, INDISPONIVEL)
        self.assertIsNone(agent._last_consumo.valor)
        self.assertEqual(agent._last_consumo.origem, "kiro-cli")

    def test_run_exit_code_preservado_com_consumo(self):
        agent, out = self._run_with_stdout(
            _stream(metering=[{"value": 0.3, "unit": "credit"}]),
            returncode=1)
        self.assertIn("[exit-code: 1]", out)
        self.assertAlmostEqual(agent._last_consumo.valor, 0.3)


class TestExecuteExpoeConsumo(unittest.TestCase):

    def test_execute_anexa_consumo_ao_result(self):
        agent = KiroCliAgent()
        params = AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng", model="m",
            issue_id="7", board_id="task", col_id="doing",
            prompt="P", work_dir="/tmp", context=None,
        )
        consumo = Consumo.reportado(0.9, "credit", "kiro-cli")

        def fake_run(self_, p, wd):
            self_._last_consumo = consumo
            return "pong\n▸ Credits: 0.90 • Time: 0m 1s"

        with patch("src.adapters.kiro_cli_agent.KiroCliAgent._create_log",
                   return_value=Path("/tmp/_x.md")), \
             patch("src.adapters.kiro_cli_agent.KiroCliAgent._run", fake_run), \
             patch("src.adapters.kiro_cli_agent.KiroCliAgent._append_log"), \
             patch("src.adapters.kiro_cli_agent.log"):
            res = agent.execute(params)
        self.assertIsNotNone(res.consumo)
        self.assertAlmostEqual(res.consumo.valor, 0.9)
        self.assertEqual(res.consumo.unidade, "credit")

    def test_execute_sem_run_consumo_fica_none(self):
        # _run mockado que NÃO define _last_consumo (contrato legado): o reset
        # por execução garante None, e o chamador degrada para indisponível.
        agent = KiroCliAgent()
        params = AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng", model="m",
            issue_id="8", board_id="task", col_id="doing",
            prompt="P", work_dir="/tmp", context=None,
        )
        with patch("src.adapters.kiro_cli_agent.KiroCliAgent._create_log",
                   return_value=Path("/tmp/_y.md")), \
             patch("src.adapters.kiro_cli_agent.KiroCliAgent._run",
                   return_value="ok"), \
             patch("src.adapters.kiro_cli_agent.KiroCliAgent._append_log"), \
             patch("src.adapters.kiro_cli_agent.log"):
            res = agent.execute(params)
        self.assertIsNone(res.consumo)


if __name__ == "__main__":
    unittest.main()
