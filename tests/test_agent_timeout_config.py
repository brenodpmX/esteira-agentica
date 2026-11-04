import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

from src.adapters.kiro_cli_agent import KiroCliAgent
from src.core import config as cfg
from src.core.agent import AgentParams
from src.core.config import (
    ConfigError, validate_agent_timeout, resolve_agent_timeout,
)


class TestValidateAgentTimeout(unittest.TestCase):

    def test_ausente_valida_e_resolve_default(self):
        validate_agent_timeout({})
        self.assertEqual(resolve_agent_timeout({}), 3600)

    def test_valor_valido(self):
        validate_agent_timeout({"agent_timeout_seg": 7200})
        self.assertEqual(resolve_agent_timeout({"agent_timeout_seg": 7200}), 7200)

    def test_minimo_valido(self):
        validate_agent_timeout({"agent_timeout_seg": 1})
        self.assertEqual(resolve_agent_timeout({"agent_timeout_seg": 1}), 1)

    def test_invalidos(self):
        for value in (0, -10, 3600.0, "3600", True, False, None):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError) as ctx:
                    validate_agent_timeout({"agent_timeout_seg": value})
                self.assertIn("agent_timeout_seg", str(ctx.exception))

    def test_check_config_rejeita_invalido(self):
        with TemporaryDirectory() as d:
            pipe = Path(d) / "pipe.yml"
            pipe.write_text("sleep: 1\nagent_timeout_seg: -1\n")
            with patch.object(cfg, "_validate_env"), \
                 patch.object(cfg, "PIPE_FILE", pipe):
                with self.assertRaises(ConfigError) as ctx:
                    cfg.check_config()
        self.assertIn("agent_timeout_seg", str(ctx.exception))


class TestTimeoutNoAdapter(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        esteira = Path(self.tmp.name) / "esteira"
        self.repo = esteira / "repo" / "main"
        self.repo.mkdir(parents=True)
        self.steering = steering = esteira / ".kiro" / "steering" / "esteira.md"
        steering.parent.mkdir(parents=True)
        steering.write_text("---\ninclusion: always\n---\n#x\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _params(self, **extra):
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng", model="m",
            issue_id="1", board_id="task", col_id="doing",
            prompt="P", work_dir=str(self.repo), **extra,
        )

    def _run(self, params, side_effect=None):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            if side_effect:
                raise side_effect
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        agent = KiroCliAgent()
        with patch("subprocess.run", side_effect=fake_run), \
             patch("src.adapters.kiro_cli_agent.SessionIndex") as mock_idx, \
             patch("src.adapters.kiro_cli_agent.STEERING_FILE", self.steering), \
             patch.object(agent, "_session_exists", return_value=False), \
             patch.object(agent, "_latest_session_id", return_value=None):
            mock_idx.return_value.get.return_value = None
            out = agent._run(params, self.repo)
        return captured, out

    def test_default_3600(self):
        kw, _ = self._run(self._params())
        self.assertEqual(kw["timeout"], 3600)

    def test_configurado_7200(self):
        kw, _ = self._run(self._params(timeout_seg=7200))
        self.assertEqual(kw["timeout"], 7200)

    def test_mensagem_timeout_reflete_valor(self):
        exc = subprocess.TimeoutExpired(cmd="x", timeout=7200)
        _, out = self._run(self._params(timeout_seg=7200), side_effect=exc)
        self.assertEqual(out, "[TIMEOUT] Agente excedeu 7200s")


if __name__ == "__main__":
    unittest.main()
