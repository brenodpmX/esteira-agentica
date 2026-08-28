"""Testes para enriquecimento do log de execução com `participation_intent`.

Task #262 — Enriquecer log de execução do agente com `participation_intent` e
board de origem (User Story #246, RF-07/RN-B09).

Cobertura (mapeada 1:1 aos casos de teste CT-001..CT-013):
  CT-001/002/003 — `AgentParams` aceita `participation_intent` opcional
                   (default `None`) e o campo existe na dataclass.
  CT-004/005     — `call_agent` propaga `issue.get("participation_intent")`.
  CT-006/007     — `_build_log` emite a linha com valor e com placeholder.
  CT-008/009/010 — posição/ordem/condicional no bloco `## Parâmetros`.
  CT-011         — board de origem é o `board_id` já existente.
  CT-012         — regressão de compatibilidade das construções existentes.
  CT-013         — leitura sem chamada de rede.
"""

import sys
from pathlib import Path
from dataclasses import fields
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.agent import AgentParams


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_params(**overrides) -> AgentParams:
    """Cria AgentParams minimal válido com campos opcionais defaults."""
    defaults = dict(
        platform="kiro-cli",
        agent_id="engineering",
        agent_name="Sofia Carvalho - Engenheira de Software PL",
        model="claude-sonnet-4.6",
        issue_id="25",
        board_id="task",
        col_id="desenvolvimento",
        prompt="Execute a tarefa.",
        work_dir="/home/user/repo/main",
    )
    defaults.update(overrides)
    return AgentParams(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# CT-001/002/003 — AgentParams: campo opcional participation_intent
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentParamsParticipationIntent:

    def test_ct001_default_none(self):
        """CT-001 — sem informar o campo, default é None e não lança erro."""
        params = _make_params()
        assert params.participation_intent is None

    def test_ct002_valor_preenchido(self):
        """CT-002 — aceita valor preenchido."""
        params = _make_params(participation_intent="origin")
        assert params.participation_intent == "origin"

    def test_ct003_campo_existe_na_dataclass(self):
        """CT-003 — campo `participation_intent` existe em AgentParams."""
        field_names = {f.name for f in fields(AgentParams)}
        assert "participation_intent" in field_names


# ─────────────────────────────────────────────────────────────────────────────
# CT-004/005/013 — call_agent propaga participation_intent (sem rede)
# ─────────────────────────────────────────────────────────────────────────────

class TestCallAgentPropagaParticipationIntent:

    def _run_call_agent(self, issue_extra: dict) -> AgentParams:
        """Executa call_agent com uma task simulada e captura o AgentParams
        passado ao adapter.execute. `issue_extra` compõe o dict da issue."""
        import src.__main__ as main_module

        captured_params = []

        config = {
            "git": {
                "repo": {"main": "git@github.com:user/repo.git"},
                "flow": {
                    "base": "main",
                    "feature": {
                        "prefix": "feature/",
                        "create": "main",
                        "merge": "main",
                    },
                },
            },
            "boards": {
                "platform": "github",
                "task": {
                    "flow": "feature",
                    "columns": {
                        "doing": {
                            "name": "Desenvolvimento",
                            "agent": "dev",
                            "gitevents": "no-branch",
                            "change": {"advance": "done"},
                        },
                    },
                },
            },
            "agents": {
                "kiro-cli": {
                    "dev": {
                        "name": "Sofia Carvalho - Engenheira de Software PL",
                        "model": "claude-sonnet-4.6",
                    },
                },
            },
        }

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            body_path = tmp_path / "25-slug-body.md"
            body_path.write_text("# Título da issue\nConteúdo.", encoding="utf-8")

            issue = {
                "id": "25",
                "column": "doing",
                "status": "ok",
                "labels": [],
                "body_path": str(body_path),
            }
            issue.update(issue_extra)

            task = {
                "board_id": "task",
                "issue": issue,
                "column": config["boards"]["task"]["columns"]["doing"],
                "col_id": "doing",
                "board": config["boards"]["task"],
            }

            def fake_execute(params: AgentParams) -> None:
                captured_params.append(params)

            mock_adapter = MagicMock()
            mock_adapter.execute.side_effect = fake_execute

            with patch("src.__main__.KiroCliAgent", return_value=mock_adapter), \
                 patch("src.adapters.kiro_cli_agent.KiroCliAgent", return_value=mock_adapter), \
                 patch("src.core.agent_guard.AgentGuard.__enter__", return_value=MagicMock()), \
                 patch("src.core.agent_guard.AgentGuard.__exit__", return_value=False), \
                 patch("src.__main__.resolve_work_dir", return_value=tmp_path):
                main_module.call_agent(config, task)

        return captured_params[0] if captured_params else None

    def test_ct004_propaga_valor_presente(self):
        """CT-004 — chave presente no dict da issue é propagada."""
        params = self._run_call_agent({"participation_intent": "origin"})
        assert params is not None, "call_agent não chamou adapter.execute"
        assert params.participation_intent == "origin"

    def test_ct005_none_quando_chave_ausente(self):
        """CT-005 — chave ausente resulta em None, sem exceção."""
        params = self._run_call_agent({})
        assert params is not None, "call_agent não chamou adapter.execute"
        assert params.participation_intent is None

    def test_ct013_leitura_sem_chamada_de_rede(self):
        """CT-013 — a leitura é apenas issue.get(...) sobre o dict em memória.

        Nenhum adapter de board real é usado no caminho exercitado — o único
        adapter (KiroCliAgent) está mockado; portanto não há chamada de rede
        (gh api / GraphQL) como efeito da leitura de participation_intent.
        """
        import src.__main__ as main_module
        # GitHubBoardAdapter não deve ser instanciado no caminho de call_agent.
        with patch("src.adapters.github_board.GitHubBoardAdapter") as gh_mock:
            params = self._run_call_agent({"participation_intent": "authorized"})
            assert params is not None
            assert params.participation_intent == "authorized"
            gh_mock.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# CT-006..CT-011 — _build_log
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildLogParticipationIntent:

    def _build(self, **overrides) -> str:
        from src.adapters.kiro_cli_agent import KiroCliAgent
        return KiroCliAgent()._build_log(_make_params(**overrides))

    def test_ct006_linha_com_valor(self):
        """CT-006 — valor preenchido produz a linha correspondente."""
        content = self._build(participation_intent="authorized")
        assert "- **participation_intent**: authorized" in content

    def test_ct007_placeholder_ausente(self):
        """CT-007 — None produz placeholder `(ausente)`, linha não omitida."""
        content = self._build(participation_intent=None)
        assert "- **participation_intent**: (ausente)" in content

    def test_ct008_posicao_entre_coluna_e_issue(self):
        """CT-008 — ordem coluna → participation_intent → issue."""
        content = self._build(
            col_id="desenvolvimento",
            issue_id="25",
            participation_intent="origin",
        )
        lines = content.split("\n")
        idx_col = next(i for i, l in enumerate(lines) if l.startswith("- **coluna**:"))
        idx_pi = next(i for i, l in enumerate(lines) if l.startswith("- **participation_intent**:"))
        idx_issue = next(i for i, l in enumerate(lines) if l.startswith("- **issue**:"))
        assert idx_col < idx_pi < idx_issue

    def test_ct009_ordem_relativa_demais_linhas(self):
        """CT-009 — demais linhas presentes e na mesma ordem relativa."""
        content = self._build(
            repo_id="main",
            work_dir="/home/user/repo/main",
            participation_intent="origin",
        )
        lines = content.split("\n")

        def idx(prefix):
            return next(i for i, l in enumerate(lines) if l.startswith(prefix))

        ordem = [
            idx("- **plataforma**:"),
            idx("- **agente**:"),
            idx("- **model**:"),
            idx("- **board**:"),
            idx("- **coluna**:"),
            idx("- **issue**:"),
            idx("- **repo**:"),
            idx("- **work_dir**:"),
        ]
        assert ordem == sorted(ordem), "ordem relativa das demais linhas mudou"

    def test_ct010_condicional_repo_workdir_preservado(self):
        """CT-010 — repo/work_dir ausentes seguem omitidos; a nova linha aparece."""
        content = self._build(
            repo_id=None,
            work_dir="",
            participation_intent="origin",
        )
        assert "- **repo**:" not in content
        assert "- **work_dir**:" not in content
        assert "- **participation_intent**: origin" in content

    def test_ct011_board_de_origem_e_board_id(self):
        """CT-011 — board de origem é o board_id já existente (sem campo novo)."""
        content = self._build(board_id="task", participation_intent="origin")
        assert "- **board**: task" in content
        field_names = {f.name for f in fields(AgentParams)}
        # Não há campo separado de "board de origem".
        assert not any("origin_board" in n or "board_origem" in n for n in field_names)


# ─────────────────────────────────────────────────────────────────────────────
# CT-012 — regressão de compatibilidade
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressaoCompatibilidade:

    def test_ct012_construcao_antiga_sem_novo_campo(self):
        """CT-012 — construção antiga (sem participation_intent) não quebra."""
        params = AgentParams(
            platform="kiro-cli",
            agent_id="engineering",
            agent_name="Sofia",
            model="claude-sonnet-4.6",
            issue_id="1",
            board_id="task",
            col_id="doing",
            prompt="prompt",
            work_dir="/repo",
        )
        assert params.participation_intent is None
        assert params.col_name == ""
        assert params.title == ""
