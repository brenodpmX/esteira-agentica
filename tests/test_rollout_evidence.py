"""Testes do evento `rollout_evidence` no startup (task #259 / story #246).

Cobre `resolve_commit()` e `resolve_environment()` (src/core/version.py) e
`emit_rollout_evidence()` (src/__main__.py), seguindo os casos CT-001..CT-010
descritos em
`doc/quality/observabilidade-de-propagacaoreconciliacaodespacho-e-evidencia-de-rollout/test-cases-emitir-rollout-evidence-no-startup.md`.

Nota (CT-010): o evento `rollout_evidence` só carrega
version/commit/environment/started_at (+ marcadores rollout_evidence_complete/
missing_fields). Não há token, chave SSH, body de issue ou conteúdo de arquivo
protegido no payload — logo, a verificação de ausência de dados sensíveis se
resume a confirmar que apenas esses campos são emitidos (CT-006/007/008), sem
asserção extra, conforme o próprio critério de aceite.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.core.version as version
from src.core.version import resolve_commit, resolve_environment


# --------------------------------------------------------------------------
# resolve_commit()
# --------------------------------------------------------------------------

class TestResolveCommit:
    def test_ct001_resolve_via_git_rev_parse_em_checkout_local(self, tmp_path, monkeypatch):
        """CT-001: em repo git válido, retorna o SHA de 40 chars do HEAD."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True, capture_output=True)
        (repo / "f.txt").write_text("x")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "c"], cwd=repo, check=True, capture_output=True)
        monkeypatch.chdir(repo)

        expected = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
        ).stdout.strip()

        result = resolve_commit()

        assert result == expected
        assert len(result) == 40
        assert all(c in "0123456789abcdef" for c in result)

    def test_ct002_git_ausente_e_arquivo_inexistente_retorna_none(self, tmp_path, monkeypatch):
        """CT-002: git não instalado (FileNotFoundError) + arquivo ausente → None."""
        def _raise(*args, **kwargs):
            raise FileNotFoundError("git")

        monkeypatch.setattr(version.subprocess, "run", _raise)
        monkeypatch.setattr(version, "BUILD_COMMIT_FILE", tmp_path / "inexistente")

        assert resolve_commit() is None

    def test_ct003_nao_e_repo_git_cai_para_arquivo_de_build(self, tmp_path, monkeypatch):
        """CT-003: returncode=128 → fonte 2 (arquivo), .strip() remove \\n."""
        def _fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(args, returncode=128, stdout="", stderr="not a git repo")

        build_file = tmp_path / ".build-commit"
        build_file.write_text("abc123\n")
        monkeypatch.setattr(version.subprocess, "run", _fake_run)
        monkeypatch.setattr(version, "BUILD_COMMIT_FILE", build_file)

        assert resolve_commit() == "abc123"

    def test_timeout_do_git_cai_para_arquivo(self, tmp_path, monkeypatch):
        """Reforço da docstring: TimeoutExpired é tratado como fonte 1 indisponível."""
        def _raise(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        build_file = tmp_path / ".build-commit"
        build_file.write_text("deadbeef")
        monkeypatch.setattr(version.subprocess, "run", _raise)
        monkeypatch.setattr(version, "BUILD_COMMIT_FILE", build_file)

        assert resolve_commit() == "deadbeef"


# --------------------------------------------------------------------------
# resolve_environment()
# --------------------------------------------------------------------------

class TestResolveEnvironment:
    def test_ct004_ausente_retorna_none(self, monkeypatch):
        """CT-004: PIPE_ENVIRONMENT ausente → None."""
        monkeypatch.delenv("PIPE_ENVIRONMENT", raising=False)
        assert resolve_environment() is None

    def test_ct005_a_valor_definido(self, monkeypatch):
        """CT-005 (A): PIPE_ENVIRONMENT=production → 'production'."""
        monkeypatch.setenv("PIPE_ENVIRONMENT", "production")
        assert resolve_environment() == "production"

    def test_ct005_b_apenas_espacos_normaliza_para_none(self, monkeypatch):
        """CT-005 (B): PIPE_ENVIRONMENT só com espaços → None."""
        monkeypatch.setenv("PIPE_ENVIRONMENT", "   ")
        assert resolve_environment() is None


# --------------------------------------------------------------------------
# emit_rollout_evidence()
# --------------------------------------------------------------------------

class TestEmitRolloutEvidence:
    def test_ct006_evento_completo(self, monkeypatch):
        """CT-006: commit+environment disponíveis → um único log.info completo."""
        import src.__main__ as m

        monkeypatch.setattr("src.core.version.resolve_commit", lambda: "a" * 40)
        monkeypatch.setattr("src.core.version.resolve_environment", lambda: "production")

        info_calls = []
        warning_calls = []
        monkeypatch.setattr(m.log, "info", lambda *a, **k: info_calls.append((a, k)))
        monkeypatch.setattr(m.log, "warning", lambda *a, **k: warning_calls.append((a, k)))

        m.emit_rollout_evidence()

        evento = [(a, k) for a, k in info_calls if k.get("event_type") == "rollout_evidence"]
        assert len(evento) == 1
        _, kwargs = evento[0]
        assert kwargs["rollout_evidence_complete"] is True
        assert kwargs["version"]
        assert kwargs["commit"]
        assert kwargs["environment"]
        assert kwargs["started_at"]
        assert not warning_calls
        # CT-010: apenas version/commit/environment/started_at + marcador —
        # nenhum token, chave SSH, body de issue ou arquivo protegido.
        assert set(kwargs) == {
            "event_type", "version", "commit", "environment",
            "started_at", "rollout_evidence_complete",
        }

    def test_ct007_falta_apenas_commit(self, monkeypatch):
        """CT-007: commit=None, environment ok → warning incompleto, sem info."""
        import src.__main__ as m

        monkeypatch.setattr("src.core.version.resolve_commit", lambda: None)
        monkeypatch.setattr("src.core.version.resolve_environment", lambda: "production")

        info_calls = []
        warning_calls = []
        monkeypatch.setattr(m.log, "info", lambda *a, **k: info_calls.append((a, k)))
        monkeypatch.setattr(m.log, "warning", lambda *a, **k: warning_calls.append((a, k)))

        m.emit_rollout_evidence()

        eventos_warn = [(a, k) for a, k in warning_calls if k.get("event_type") == "rollout_evidence"]
        assert len(eventos_warn) == 1
        _, kwargs = eventos_warn[0]
        assert kwargs["rollout_evidence_complete"] is False
        assert kwargs["missing_fields"] == ["commit"]

        eventos_info = [(a, k) for a, k in info_calls if k.get("event_type") == "rollout_evidence"]
        assert eventos_info == []

    def test_ct008_falta_commit_e_environment(self, monkeypatch):
        """CT-008: ambos None → missing_fields=['commit', 'environment']."""
        import src.__main__ as m

        monkeypatch.setattr("src.core.version.resolve_commit", lambda: None)
        monkeypatch.setattr("src.core.version.resolve_environment", lambda: None)

        warning_calls = []
        monkeypatch.setattr(m.log, "warning", lambda *a, **k: warning_calls.append((a, k)))
        monkeypatch.setattr(m.log, "info", lambda *a, **k: None)

        m.emit_rollout_evidence()

        eventos_warn = [(a, k) for a, k in warning_calls if k.get("event_type") == "rollout_evidence"]
        assert len(eventos_warn) == 1
        _, kwargs = eventos_warn[0]
        assert kwargs["rollout_evidence_complete"] is False
        assert kwargs["missing_fields"] == ["commit", "environment"]

    def test_ct009_nunca_levanta_excecao(self, monkeypatch):
        """CT-009: mesmo sem evidência, não propaga exceção (startup continua)."""
        import src.__main__ as m

        monkeypatch.setattr("src.core.version.resolve_commit", lambda: None)
        monkeypatch.setattr("src.core.version.resolve_environment", lambda: None)
        monkeypatch.setattr(m.log, "warning", lambda *a, **k: None)
        monkeypatch.setattr(m.log, "info", lambda *a, **k: None)

        try:
            result = m.emit_rollout_evidence()
        except Exception as e:
            pytest.fail(f"emit_rollout_evidence não deveria propagar exceção: {e!r}")

        assert result is None
