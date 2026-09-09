"""
Casos de Teste — Steering de sistema gerado no startup a partir do pipe.yml

Contexto: o contexto de SISTEMA (antes `.pipe/CONTEXT.md` injetado via
`--agent pipe_context`) foi migrado para `.kiro/steering/esteira.md`, carregado
automaticamente pelo default agent do kiro-cli via `KIRO_HOME` (Caminho B —
P1.1(b)). NÃO geramos mais `.kiro/agents/pipe_context.json` nem passamos
`--agent`.

Esta suíte valida que:
  - generate_context() cria .kiro/steering/esteira.md a partir do config
  - Regenera quando pipe.yml é mais novo que o steering
  - Não sobrescreve se o steering já está atualizado
  - O steering tem frontmatter `inclusion: always`
  - O steering lista arquivos protegidos (incl. .kiro/steering/**/*.md)
  - O steering descreve a estrutura do -body.md (5 partes) e os comandos @---
  - O steering instrui nomeação de issues SEM prefixo numérico
  - O steering documenta boards, colunas e branches do pipe.yml
  - O adapter NÃO passa `--agent` e define KIRO_HOME apontando para .kiro
  - O conteúdo NÃO é embutido inline no prompt

Estratégia: testes unitários com diretório temporário simulando o cwd da
esteira. Nenhuma chamada real ao GitHub ou ao kiro-cli.
"""

import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# Config de exemplo
# ─────────────────────────────────────────────────────────────────────────────

def _make_config(boards=None, flows=None):
    """Retorna config mínima representativa para testes."""
    if flows is None:
        flows = {
            "base": "main",
            "feature": {"prefix": "feature/", "create": "main", "merge": "main"},
            "hotfix": {"prefix": "hotfix/", "create": "main", "merge": "main"},
        }
    if boards is None:
        boards = {
            "platform": "github",
            "task": {
                "name": "Task Board",
                "flow": "feature",
                "columns": {
                    "todo": {"name": "To Do"},
                    "doing": {"name": "Doing", "agent": "dev"},
                    "done": {"name": "Done"},
                },
            },
        }
    return {
        "sleep": 60,
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": flows,
        },
        "agents": {
            "kiro-cli": {
                "dev": {"name": "engineering", "model": "claude-sonnet-4"},
            }
        },
        "boards": boards,
    }


def _steering_path(cwd: Path) -> Path:
    return cwd / ".kiro" / "steering" / "esteira.md"


# ─────────────────────────────────────────────────────────────────────────────
# Grupo 1 — Ciclo de vida do arquivo
# ─────────────────────────────────────────────────────────────────────────────

class TestCicloDeVida(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / ".pipe").mkdir()
        (self.cwd / "pipe.yml").write_text("# pipe.yml de teste\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, config=None):
        from src.core.context_generator import generate_context
        with patch("src.core.context_generator.PIPE_FILE", self.cwd / "pipe.yml"), \
             patch("src.core.context_generator.STEERING_FILE", _steering_path(self.cwd)):
            return generate_context(config or _make_config())

    def test_cria_steering_se_nao_existir(self):
        """Deve criar .kiro/steering/esteira.md quando ele não existe."""
        steering = _steering_path(self.cwd)
        self.assertFalse(steering.exists())
        self._run()
        self.assertTrue(steering.exists())
        self.assertGreater(len(steering.read_text()), 0)

    def test_regenera_quando_pipeyml_modificado(self):
        """Deve regenerar quando pipe.yml é mais novo que o steering."""
        steering = _steering_path(self.cwd)
        self._run()
        time.sleep(0.02)
        (self.cwd / "pipe.yml").write_text("# atualizado\n")
        self._run()
        self.assertTrue(steering.exists())

    def test_nao_sobrescreve_se_atualizado(self):
        """Não deve sobrescrever se o steering já está atualizado."""
        steering = _steering_path(self.cwd)
        self._run()
        mtime_antes = steering.stat().st_mtime
        time.sleep(0.01)
        self._run()
        mtime_depois = steering.stat().st_mtime
        self.assertEqual(mtime_antes, mtime_depois)

    def test_retorna_path_do_steering(self):
        """generate_context deve retornar o Path do steering gerado."""
        result = self._run()
        self.assertIsInstance(result, Path)
        self.assertEqual(result.name, "esteira.md")


# ─────────────────────────────────────────────────────────────────────────────
# Grupo 2 — Frontmatter e localização (steering)
# ─────────────────────────────────────────────────────────────────────────────

class TestSteeringFrontmatter(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / "pipe.yml").write_text("# pipe.yml\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _get_content(self, config=None):
        from src.core.context_generator import generate_context
        steering = _steering_path(self.cwd)
        with patch("src.core.context_generator.PIPE_FILE", self.cwd / "pipe.yml"), \
             patch("src.core.context_generator.STEERING_FILE", steering):
            generate_context(config or _make_config())
        return steering.read_text()

    def test_tem_frontmatter_inclusion_always(self):
        """O steering deve começar com frontmatter `inclusion: always`."""
        content = self._get_content()
        self.assertTrue(content.startswith("---\n"),
                        f"Steering não começa com frontmatter:\n{content[:80]}")
        self.assertIn("inclusion: always", content.splitlines()[1])

    def test_gerado_em_kiro_steering(self):
        """O arquivo gerado deve ficar em .kiro/steering/esteira.md."""
        self._get_content()
        self.assertTrue(_steering_path(self.cwd).exists())

    def test_nao_gera_pipe_context_json(self):
        """Caminho B: NÃO deve mais existir .kiro/agents/pipe_context.json."""
        self._get_content()
        legado = self.cwd / ".kiro" / "agents" / "pipe_context.json"
        self.assertFalse(legado.exists(),
                         "pipe_context.json não deve mais ser gerado (Caminho B)")


# ─────────────────────────────────────────────────────────────────────────────
# Grupo 3 — Arquivos protegidos
# ─────────────────────────────────────────────────────────────────────────────

class TestArquivosProtegidos(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / "pipe.yml").write_text("# pipe.yml\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _get_content(self):
        from src.core.context_generator import generate_context
        steering = _steering_path(self.cwd)
        with patch("src.core.context_generator.PIPE_FILE", self.cwd / "pipe.yml"), \
             patch("src.core.context_generator.STEERING_FILE", steering):
            generate_context(_make_config())
        return steering.read_text()

    def test_lista_snapshot_json(self):
        self.assertIn("snapshot.json", self._get_content())

    def test_lista_changequeue_json(self):
        self.assertIn("changeQueue.json", self._get_content())

    def test_lista_throttle(self):
        self.assertIn("throttle", self._get_content())

    def test_lista_sessions_json(self):
        self.assertIn("sessions.json", self._get_content())

    def test_lista_deadletter_json(self):
        self.assertIn("deadLetter.json", self._get_content())

    def test_lista_orphanfiles_json(self):
        self.assertIn("orphanFiles.json", self._get_content())

    def test_lista_pipe_lock(self):
        self.assertIn("pipe.lock", self._get_content())

    def test_lista_steering_protegido(self):
        """P1.3: o próprio steering (.kiro/steering/**/*.md) é protegido."""
        self.assertIn(".kiro/steering/**/*.md", self._get_content())

    def test_secao_restricoes_presente(self):
        content = self._get_content()
        keywords = ["protegido", "NUNCA", "Nunca", "NÃO acessar", "corrompe"]
        self.assertTrue(
            any(k in content for k in keywords),
            f"Nenhuma palavra-chave de restrição encontrada:\n{content[:300]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Grupo 4 — Estrutura do -body.md (5 partes) + comandos @---
# ─────────────────────────────────────────────────────────────────────────────

class TestEstruturaBody(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / "pipe.yml").write_text("# pipe.yml\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _get_content(self):
        from src.core.context_generator import generate_context
        steering = _steering_path(self.cwd)
        with patch("src.core.context_generator.PIPE_FILE", self.cwd / "pipe.yml"), \
             patch("src.core.context_generator.STEERING_FILE", steering):
            generate_context(_make_config())
        return steering.read_text()

    def test_menciona_separador_comandos(self):
        self.assertIn("@---", self._get_content())

    def test_menciona_separador_anotacoes(self):
        self.assertIn("📝", self._get_content())

    def test_documenta_anotacoes(self):
        content = self._get_content()
        for campo in ["branch pai", "branch:", "boards:"]:
            self.assertIn(campo, content, f"anotação '{campo}' ausente")

    def test_documenta_comandos_relacao(self):
        content = self._get_content()
        for cmd in ["/parent", "/children", "/blocks", "/blocked_by", "/labels",
                    "/need_human", "/archive"]:
            self.assertIn(cmd, content, f"comando '{cmd}' ausente")

    def test_nao_menciona_close_reopen(self):
        """E9: /close e /reopen saem do steering."""
        content = self._get_content()
        self.assertNotIn("/close", content)
        self.assertNotIn("/reopen", content)

    def test_regra_anti_ciclo(self):
        content = self._get_content()
        self.assertIn("ciclos", content.lower())


# ─────────────────────────────────────────────────────────────────────────────
# Grupo 5 — Nomeação de issues (sem prefixo numérico)
# ─────────────────────────────────────────────────────────────────────────────

class TestNomeacaoIssues(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / "pipe.yml").write_text("# pipe.yml\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _get_content(self):
        from src.core.context_generator import generate_context
        steering = _steering_path(self.cwd)
        with patch("src.core.context_generator.PIPE_FILE", self.cwd / "pipe.yml"), \
             patch("src.core.context_generator.STEERING_FILE", steering):
            generate_context(_make_config())
        return steering.read_text()

    def test_instrui_contra_prefixo_numerico(self):
        content = self._get_content()
        keywords = ["prefixo", "numérico", "número", "sem prefixo"]
        self.assertTrue(any(k in content for k in keywords))

    def test_menciona_body_md(self):
        self.assertIn("-body.md", self._get_content())

    def test_nao_solicita_criacao_history(self):
        content = self._get_content()
        lines = [
            l for l in content.splitlines()
            if "-history.md" in l and ("crie" in l.lower() or "criar" in l.lower()
                                       or "opcional" in l.lower() or "- `" in l)
        ]
        self.assertEqual(len(lines), 0)

    def test_exemplo_padrao_errado(self):
        import re
        content = self._get_content()
        self.assertTrue(bool(re.search(r"\d+-\w.*-body\.md", content)))


# ─────────────────────────────────────────────────────────────────────────────
# Grupo 6 — Boards e colunas
# ─────────────────────────────────────────────────────────────────────────────

class TestBoardsEColunas(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / "pipe.yml").write_text("# pipe.yml\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _get_content(self, config=None):
        from src.core.context_generator import generate_context
        steering = _steering_path(self.cwd)
        with patch("src.core.context_generator.PIPE_FILE", self.cwd / "pipe.yml"), \
             patch("src.core.context_generator.STEERING_FILE", steering):
            generate_context(config or _make_config())
        return steering.read_text()

    def test_nome_do_board(self):
        self.assertIn("Task Board", self._get_content())

    def test_nomes_das_colunas(self):
        content = self._get_content()
        self.assertIn("To Do", content)
        self.assertIn("Doing", content)
        self.assertIn("Done", content)

    def test_multiplos_boards(self):
        config = _make_config(boards={
            "platform": "github",
            "task": {
                "name": "Task Board", "flow": "feature",
                "columns": {"todo": {"name": "To Do"}, "doing": {"name": "Doing"}},
            },
            "bug": {
                "name": "Bug Board", "flow": "hotfix",
                "columns": {"open": {"name": "Open"}, "closed": {"name": "Closed"}},
            },
        })
        content = self._get_content(config)
        self.assertIn("Task Board", content)
        self.assertIn("Bug Board", content)

    def test_flow_associado_ao_board(self):
        self.assertIn("feature", self._get_content())

    def test_config_sem_boards_nao_levanta_excecao(self):
        config = _make_config(boards={"platform": "github"})
        try:
            self._get_content(config)
        except Exception as e:
            self.fail(f"Exceção inesperada com boards vazio: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Grupo 7 — Branches e prefixos
# ─────────────────────────────────────────────────────────────────────────────

class TestBranchesEPrefixos(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / "pipe.yml").write_text("# pipe.yml\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _get_content(self, config=None):
        from src.core.context_generator import generate_context
        steering = _steering_path(self.cwd)
        with patch("src.core.context_generator.PIPE_FILE", self.cwd / "pipe.yml"), \
             patch("src.core.context_generator.STEERING_FILE", steering):
            generate_context(config or _make_config())
        return steering.read_text()

    def test_prefixo_feature(self):
        self.assertIn("feature/", self._get_content())

    def test_branch_base(self):
        self.assertIn("main", self._get_content())

    def test_multiplos_flows(self):
        self.assertIn("hotfix/", self._get_content())


# ─────────────────────────────────────────────────────────────────────────────
# Grupo 8 — Integração: steering via default agent (sem --agent, inline)
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegracaoSteering(unittest.TestCase):
    """Valida que o steering é carregado via KIRO_HOME (default agent),
    não via --agent nem inline no prompt."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.esteira_dir = Path(self.tmp.name) / "esteira"
        self.repo_dir = self.esteira_dir / "repo" / "main"
        self.esteira_dir.mkdir(parents=True)
        self.repo_dir.mkdir(parents=True)
        (self.esteira_dir / ".pipe").mkdir()
        (self.esteira_dir / "pipe.yml").write_text("# pipe.yml\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_prompt_nao_contem_conteudo_do_steering(self):
        """build_prompt NÃO deve embutir o conteúdo do steering no prompt."""
        from src.core.agent import build_prompt

        sentinel = "SENTINEL_STEERING_CONTENT_XYZ"
        steering = _steering_path(self.esteira_dir)
        steering.parent.mkdir(parents=True, exist_ok=True)
        steering.write_text(f"---\ninclusion: always\n---\n{sentinel}\n")

        config = _make_config()
        body_path = (self.esteira_dir / ".pipe" / "boards" / "task" / "doing"
                     / "slug-body.md")
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text("# Título da issue\n\nConteúdo.\n")

        task = {
            "board_id": "task",
            "board": config["boards"]["task"],
            "column": config["boards"]["task"]["columns"]["doing"],
            "col_id": "doing",
            "issue": {"id": "1", "body_path": str(body_path)},
        }

        with patch("src.core.context_generator.STEERING_FILE", steering):
            prompt = build_prompt(config, task)

        self.assertNotIn(sentinel, prompt,
                         "Conteúdo do steering embutido inline no prompt — deve "
                         "ser carregado via KIRO_HOME (default agent)")

    def _run_adapter_capture(self):
        """Executa o adapter com subprocess mockado e retorna (cmd, env)."""
        from src.adapters.kiro_cli_agent import KiroCliAgent
        from src.core.agent import AgentParams

        steering = _steering_path(self.esteira_dir)
        steering.parent.mkdir(parents=True, exist_ok=True)
        steering.write_text("---\ninclusion: always\n---\n# Contexto\n")

        params = AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="engineering",
            model="claude-sonnet-4", issue_id="1", board_id="task",
            col_id="doing", prompt="Execute a tarefa.",
            work_dir=str(self.repo_dir),
        )

        captured = {"cmd": [], "env": {}}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["env"] = kwargs.get("env", {})
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r

        agent = KiroCliAgent()
        with patch("subprocess.run", side_effect=fake_run), \
             patch("src.adapters.kiro_cli_agent.SessionIndex") as mock_idx, \
             patch("src.adapters.kiro_cli_agent.STEERING_FILE", steering):
            mock_idx.return_value.get.return_value = None
            mock_idx.return_value.set.return_value = None
            agent._run(params, self.repo_dir)
        return captured["cmd"], captured["env"]

    def test_adapter_nao_passa_agent_flag(self):
        """Caminho B: o adapter NÃO deve passar --agent."""
        cmd, _ = self._run_adapter_capture()
        self.assertNotIn("--agent", cmd,
                         f"--agent não deveria mais ser passado: {cmd}")

    def test_adapter_define_kiro_home_absoluto_no_kiro(self):
        """KIRO_HOME deve apontar (absoluto) para o .kiro que contém o steering."""
        _, env = self._run_adapter_capture()
        kiro_home = env.get("KIRO_HOME", "")
        self.assertTrue(kiro_home, "KIRO_HOME não definido no env do subprocess")
        self.assertTrue(Path(kiro_home).is_absolute(),
                        f"KIRO_HOME='{kiro_home}' não é absoluto")
        steering_esperado = Path(kiro_home) / "steering" / "esteira.md"
        self.assertTrue(steering_esperado.exists(),
                        f"steering não encontrado em KIRO_HOME/steering: "
                        f"{steering_esperado}")


if __name__ == "__main__":
    unittest.main()
