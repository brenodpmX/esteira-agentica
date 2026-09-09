"""
Casos de Teste — F0.3 (P1.4): persona injetada via AgentParams.context

A persona do agente vive em `contexts/<platform>/<agent_id>.md` e NÃO vai para
o steering. É lida por código no dispatch (`call_agent`) e injetada em
`AgentParams.context`; o adapter concatena persona + prompt (`_compose_input`) e
registra a persona no log (`_build_log`).

Valida:
  - call_agent lê contexts/<platform>/<agent_id>.md e preenche params.context
  - _compose_input concatena persona antes do prompt
  - _build_log inclui seção "## Persona" quando há context (e omite sem context)
"""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

from src.core.agent import AgentParams
from src.adapters.kiro_cli_agent import KiroCliAgent


# ─────────────────────────────────────────────────────────────────────────────
# _compose_input — persona antes do prompt
# ─────────────────────────────────────────────────────────────────────────────

class TestComposeInput(unittest.TestCase):

    def _params(self, context):
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng",
            model="m", issue_id="1", board_id="task", col_id="doing",
            prompt="PROMPT_DA_TAREFA", work_dir="/tmp", context=context,
        )

    def test_persona_precede_o_prompt(self):
        agent = KiroCliAgent()
        out = agent._compose_input(self._params("PERSONA_DEV"))
        self.assertIn("PERSONA_DEV", out)
        self.assertIn("PROMPT_DA_TAREFA", out)
        self.assertLess(out.index("PERSONA_DEV"), out.index("PROMPT_DA_TAREFA"))

    def test_sem_persona_retorna_so_prompt(self):
        agent = KiroCliAgent()
        out = agent._compose_input(self._params(None))
        self.assertEqual(out, "PROMPT_DA_TAREFA")


# ─────────────────────────────────────────────────────────────────────────────
# _build_log — seção Persona
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildLogPersona(unittest.TestCase):

    def _params(self, context):
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng",
            model="m", issue_id="1", board_id="task", col_id="doing",
            prompt="PROMPT_X", work_dir="/tmp", context=context,
        )

    def test_log_contem_persona_quando_ha_context(self):
        agent = KiroCliAgent()
        log_md = agent._build_log(self._params("PERSONA_TESTE_123"))
        self.assertIn("## Persona", log_md)
        self.assertIn("PERSONA_TESTE_123", log_md)

    def test_log_omite_persona_sem_context(self):
        agent = KiroCliAgent()
        log_md = agent._build_log(self._params(None))
        self.assertNotIn("## Persona", log_md)


# ─────────────────────────────────────────────────────────────────────────────
# call_agent — lê persona do arquivo e injeta em params.context
# ─────────────────────────────────────────────────────────────────────────────

class TestCallAgentPersona(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self._old_cwd = os.getcwd()
        os.chdir(self.cwd)
        # Persona em contexts/kiro-cli/dev.md (relativo ao cwd)
        persona_dir = self.cwd / "contexts" / "kiro-cli"
        persona_dir.mkdir(parents=True)
        (persona_dir / "dev.md").write_text("PERSONA_ENGENHEIRO\n", encoding="utf-8")

    def tearDown(self):
        os.chdir(self._old_cwd)
        self.tmp.cleanup()

    def _config_task(self):
        config = {
            "agents": {"kiro-cli": {"dev": {"name": "Eng", "model": "m"}}},
            "boards": {
                "platform": "github",
                "task": {
                    "name": "Task", "flow": "feature",
                    "columns": {"doing": {"name": "Doing", "agent": "dev"}},
                },
            },
            "git": {"repo": {"main": "x"}, "flow": {"base": "main",
                    "feature": {"prefix": "feature/"}}},
        }
        task = {
            "board_id": "task",
            "board": config["boards"]["task"],
            "column": config["boards"]["task"]["columns"]["doing"],
            "col_id": "doing",
            "issue": {"id": "1", "body_path": str(self.cwd / "slug-body.md")},
        }
        (self.cwd / "slug-body.md").write_text("# Título\n\nCorpo.\n")
        return config, task

    def test_call_agent_injeta_persona_em_context(self):
        import src.__main__ as m

        config, task = self._config_task()
        captured = {}

        def fake_execute(self, params):
            captured["params"] = params

        with patch.object(m, "build_prompt", return_value="PROMPT_MOCK"), \
             patch.object(m, "resolve_repo_id", return_value="main"), \
             patch.object(m, "resolve_work_dir", return_value=self.cwd), \
             patch.object(m.KiroCliAgent, "execute", fake_execute), \
             patch("src.core.agent_guard.AgentGuard") as mock_ag, \
             patch.object(m, "SnapshotGuard") as mock_sg:
            mock_ag.return_value.__enter__ = lambda s: None
            mock_ag.return_value.__exit__ = lambda s, *a: False
            mock_sg.return_value.__enter__ = lambda s: None
            mock_sg.return_value.__exit__ = lambda s, *a: False
            m.call_agent(config, task)

        self.assertIn("params", captured)
        self.assertEqual(captured["params"].context, "PERSONA_ENGENHEIRO")


if __name__ == "__main__":
    unittest.main()
