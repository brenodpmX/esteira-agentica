"""
Casos de Teste — F0.7 (E10): sessão por (issue, coluna) + prompt de continuação.

- Chave de sessão muda para issue+coluna (não depende do agente).
- Se existe sessão CONFIRMADA (known_id + _session_exists), envia PROMPT DE
  CONTINUAÇÃO em vez do de execução completa (retoma via --resume-id).
- GUARDA anti-delírio: sem sessão confirmada → prompt de execução completo.

Valida:
  - build_continuation_prompt: texto genérico + ponteiros + transição
  - _compose_input: continuação quando resuming; completo caso contrário
  - _run: com sessão confirmada usa --resume-id + continuação; sem sessão, full
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

from src.core.agent import AgentParams, build_continuation_prompt
from src.adapters.kiro_cli_agent import KiroCliAgent


def _task(tmp: Path) -> dict:
    issue_dir = tmp / ".pipe" / "boards" / "task" / "doing"
    issue_dir.mkdir(parents=True, exist_ok=True)
    body = issue_dir / "slug-body.md"
    body.write_text("# Título\n\nCorpo.\n", encoding="utf-8")
    return {
        "board_id": "task",
        "board": {"flow": "feature", "repo": "main"},
        "col_id": "doing",
        "column": {"name": "Doing", "agent": "dev", "change": {"advance": "done"}},
        "issue": {"id": "1", "body_path": str(body)},
    }


class TestBuildContinuationPrompt(unittest.TestCase):

    def test_contem_texto_generico_e_transicao(self):
        with TemporaryDirectory() as d:
            tmp = Path(d)
            with patch("src.core.agent.BOARDS_DIR", tmp / ".pipe" / "boards"):
                p = build_continuation_prompt({}, _task(tmp))
        self.assertIn("já trabalhou nesta etapa", p)
        self.assertIn("não recomece do zero", p)
        self.assertIn("Transição de coluna", p)
        self.assertIn("advance", p)
        self.assertIn("-history.md", p)


class TestComposeInput(unittest.TestCase):

    def _params(self, resuming_prompt="CONT", context="PERSONA"):
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng", model="m",
            issue_id="1", board_id="task", col_id="doing",
            prompt="PROMPT_FULL", work_dir="/tmp",
            context=context, continuation_prompt=resuming_prompt,
        )

    def test_resuming_usa_continuacao(self):
        agent = KiroCliAgent()
        out = agent._compose_input(self._params(), resuming=True)
        self.assertEqual(out, "CONT")
        self.assertNotIn("PROMPT_FULL", out)

    def test_nao_resuming_usa_prompt_completo_com_persona(self):
        agent = KiroCliAgent()
        out = agent._compose_input(self._params(), resuming=False)
        self.assertIn("PERSONA", out)
        self.assertIn("PROMPT_FULL", out)

    def test_resuming_sem_continuacao_cai_no_completo(self):
        agent = KiroCliAgent()
        out = agent._compose_input(self._params(resuming_prompt=None), resuming=True)
        self.assertIn("PROMPT_FULL", out)


class TestRunResumeGuard(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.esteira = Path(self.tmp.name) / "esteira"
        self.repo = self.esteira / "repo" / "main"
        self.repo.mkdir(parents=True)
        steering = self.esteira / ".kiro" / "steering" / "esteira.md"
        steering.parent.mkdir(parents=True)
        steering.write_text("---\ninclusion: always\n---\n#x\n")
        self.steering = steering

    def tearDown(self):
        self.tmp.cleanup()

    def _params(self):
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="Eng", model="m",
            issue_id="1", board_id="task", col_id="doing",
            prompt="PROMPT_FULL", work_dir=str(self.repo),
            context=None, continuation_prompt="CONT_PROMPT",
        )

    def _run_capture(self, known_id, session_exists):
        captured = {"cmd": []}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        agent = KiroCliAgent()
        with patch("subprocess.run", side_effect=fake_run), \
             patch("src.adapters.kiro_cli_agent.SessionIndex") as mock_idx, \
             patch("src.adapters.kiro_cli_agent.STEERING_FILE", self.steering), \
             patch.object(agent, "_session_exists", return_value=session_exists), \
             patch.object(agent, "_latest_session_id", return_value=None):
            mock_idx.return_value.get.return_value = known_id
            mock_idx.return_value.set.return_value = None
            agent._run(self._params(), self.repo)
        return captured["cmd"]

    def test_sessao_confirmada_usa_resume_e_continuacao(self):
        cmd = self._run_capture(known_id="sess-123", session_exists=True)
        self.assertIn("--resume-id", cmd)
        self.assertIn("sess-123", cmd)
        self.assertIn("CONT_PROMPT", cmd)
        self.assertNotIn("PROMPT_FULL", cmd)

    def test_sem_sessao_usa_prompt_completo(self):
        cmd = self._run_capture(known_id=None, session_exists=False)
        self.assertNotIn("--resume-id", cmd)
        self.assertIn("PROMPT_FULL", cmd)

    def test_id_conhecido_mas_sessao_inexistente_cai_no_completo(self):
        # GUARDA: known_id existe mas _session_exists=False → sem resume, full.
        cmd = self._run_capture(known_id="sess-x", session_exists=False)
        self.assertNotIn("--resume-id", cmd)
        self.assertIn("PROMPT_FULL", cmd)


if __name__ == "__main__":
    unittest.main()
