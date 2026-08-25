"""Regressão: detecção da falha real do kiro-cli no log de execução.

Contexto (perda no merge `c27f813`): o commit `3a1196a` de `main` introduziu
`_detect_failure`/`_last_meaningful_line` no adapter do kiro-cli. O merge de
`epic` em `main` resolveu o conflito adotando o lado `epic`, que logava sempre
"execução concluída" — inclusive quando o kiro-cli havia falhado.

O problema é que o kiro-cli **não** sinaliza toda falha pelo exit-code: erros de
modelo/servidor voltam como texto no output com exit 0. Sem a análise do output,
uma execução quebrada era registrada como sucesso e a causa ficava escondida.

Estes testes travam:
- a classificação sucesso × falha a partir do conteúdo do output;
- a extração da causa real (não apenas a última linha, que costuma ser
  'Request ID: ...');
- a preservação do formato da linha de início, que é contrato de
  `test_agent_log_descritivo.py` (lado `epic`, igualmente legítimo).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.kiro_cli_agent import KiroCliAgent


@pytest.fixture
def adapter():
    return KiroCliAgent()


# ─── _last_meaningful_line ────────────────────────────────────────────────────

class TestLastMeaningfulLine:
    """A última linha significativa resume a execução no log de terminal."""

    def test_retorna_ultima_linha_nao_vazia(self, adapter):
        output = "primeira\n\nsegunda\n\n\n"
        assert adapter._last_meaningful_line(output) == "segunda"

    def test_ignora_espacos_em_branco(self, adapter):
        output = "alfa\n   \n  beta  \n   \n"
        assert adapter._last_meaningful_line(output) == "beta"

    def test_output_vazio_tem_placeholder(self, adapter):
        assert adapter._last_meaningful_line("") == "(sem output)"
        assert adapter._last_meaningful_line("   \n\n  ") == "(sem output)"

    def test_remove_ansi(self, adapter):
        output = "\x1b[32mconcluido em 12s\x1b[0m\n"
        assert adapter._last_meaningful_line(output) == "concluido em 12s"


# ─── _detect_failure: sucesso ─────────────────────────────────────────────────

class TestDetectFailureSucesso:
    """Sem marcador de falha, a execução é considerada bem-sucedida."""

    def test_output_normal_nao_e_falha(self, adapter):
        output = (
            "Analisando a issue #42\n"
            "Editando src/core/sync.py\n"
            "Pronto. 3 arquivos alterados.\n"
        )
        assert adapter._detect_failure(output) is None

    def test_output_vazio_nao_e_falha(self, adapter):
        assert adapter._detect_failure("") is None
        assert adapter._detect_failure("  \n \n") is None

    def test_palavra_error_sem_marcador_nao_e_falha(self, adapter):
        """Menção a 'error' no conteúdo não basta: exige marcador de falha.

        Um agente pode legitimamente escrever sobre tratamento de erro. Sem esta
        condição, toda execução que discutisse erros seria falso-positivo — o
        mesmo tipo de bug já corrigido na detecção de rate limit.
        """
        output = (
            "Implementando o tratamento de error handling do adapter.\n"
            "Error: era a mensagem antiga; agora usamos ConfigError.\n"
            "Concluido.\n"
        )
        assert adapter._detect_failure(output) is None


# ─── _detect_failure: falha ───────────────────────────────────────────────────

class TestDetectFailureFalha:
    """Com marcador de falha, a causa real é extraída do output."""

    @pytest.mark.parametrize("marker", [
        "[exit-code: 1]",
        "[TIMEOUT]",
        "[ERRO]",
        "Kiro is having trouble responding",
    ])
    def test_cada_marcador_dispara_falha(self, adapter, marker):
        assert adapter._detect_failure(f"saida qualquer\n{marker}\n") is not None

    def test_extrai_erro_de_modelo_indisponivel(self, adapter):
        output = (
            "Iniciando tarefa\n"
            "Kiro is having trouble responding right now:\n"
            "   0: The model you've selected is temporarily unavailable\n"
            "Request ID: abc-123\n"
        )
        error = adapter._detect_failure(output)
        assert error is not None
        assert "temporarily unavailable" in error, (
            f"a causa real deve aparecer, nao apenas o Request ID: {error}"
        )

    def test_nao_reduz_a_ultima_linha(self, adapter):
        """A causa real não pode ser ofuscada pela última linha do output.

        Era exatamente o bug: o log mostrava 'Request ID: ...' como se fosse o
        resultado, sem dizer o que falhou.
        """
        output = (
            "Kiro is having trouble responding right now:\n"
            "   0: InternalServerError\n"
            "Request ID: zzz-999\n"
        )
        error = adapter._detect_failure(output)
        assert "InternalServerError" in error
        assert error != adapter._last_meaningful_line(output)

    def test_une_linhas_relevantes_com_pipe(self, adapter):
        output = (
            "Kiro is having trouble responding right now:\n"
            "InternalServerError\n"
            "Request ID: 1\n"
        )
        assert " | " in adapter._detect_failure(output)

    def test_retorna_uma_unica_linha(self, adapter):
        """O log de terminal é uma linha por evento; a mensagem não quebra."""
        output = "[exit-code: 2]\nerror: falhou\nLocation: src/x.py\n"
        assert "\n" not in adapter._detect_failure(output)

    def test_falha_sem_padrao_conhecido_usa_ultimas_linhas(self, adapter):
        """Marcador presente mas sem dica reconhecida: usa contexto final."""
        output = "linha a\nlinha b\nlinha c\nlinha d\n[exit-code: 9]\n"
        error = adapter._detect_failure(output)
        assert error is not None
        assert "linha d" in error or "exit-code" in error

    def test_remove_ansi_antes_de_analisar(self, adapter):
        output = "\x1b[31m[exit-code: 1]\x1b[0m\n\x1b[31merror: quebrou\x1b[0m\n"
        error = adapter._detect_failure(output)
        assert error is not None
        assert "\x1b" not in error


# ─── Integração com execute() ─────────────────────────────────────────────────

class TestExecuteUsaDeteccao:
    """execute() deve classificar a execução pelo resultado da detecção."""

    def _params(self):
        from src.core.agent import AgentParams
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="engineering",
            model="claude", issue_id="42", board_id="task", col_id="doing",
            prompt="faca", work_dir=".", repo_id="main",
            col_name="Doing", title="Uma issue",
        )

    def _execute_capturando_logs(self, monkeypatch, tmp_path, output, returncode=0):
        registros = []

        from src.adapters import kiro_cli_agent as mod

        monkeypatch.setattr(mod.KiroCliAgent, "_create_log",
                            lambda self, params: tmp_path / "exec.md")
        monkeypatch.setattr(mod.KiroCliAgent, "_run",
                            lambda self, params, work_dir: (output, returncode))
        monkeypatch.setattr(mod.log, "info",
                            lambda *a, **k: registros.append(("info", a, k)))
        monkeypatch.setattr(mod.log, "error",
                            lambda *a, **k: registros.append(("error", a, k)))

        KiroCliAgent().execute(self._params())
        return registros

    def test_sucesso_loga_info_com_resumo(self, monkeypatch, tmp_path):
        registros = self._execute_capturando_logs(
            monkeypatch, tmp_path, "trabalhando\nPronto em 12s\n"
        )
        finais = [r for r in registros if "concluída" in r[1][1]]
        assert len(finais) == 1, f"esperado 1 log de conclusao: {registros}"
        assert finais[0][0] == "info"
        assert "Pronto em 12s" in finais[0][1][1]

    def test_falha_loga_error_com_causa(self, monkeypatch, tmp_path):
        output = (
            "Kiro is having trouble responding right now:\n"
            "   0: The model you've selected is temporarily unavailable\n"
            "Request ID: abc-123\n"
        )
        registros = self._execute_capturando_logs(monkeypatch, tmp_path, output)

        assert not any("concluída" in r[1][1] for r in registros), (
            f"falha nao pode ser logada como conclusao: {registros}"
        )
        falhas = [r for r in registros if r[0] == "error"]
        assert len(falhas) == 1, f"esperado 1 log de erro: {registros}"
        assert "falhou:" in falhas[0][1][1]
        assert "temporarily unavailable" in falhas[0][1][1]

    def test_linha_de_inicio_preserva_formato_do_epic(self, monkeypatch, tmp_path):
        """Contrato de test_agent_log_descritivo.py: não pode regredir.

        A restauração da detecção de falha atua nas linhas de conclusão/erro; a
        linha de início mantém o formato mais informativo trazido pelo `epic`.
        """
        registros = self._execute_capturando_logs(monkeypatch, tmp_path, "ok\n")
        inicio = registros[0][1][1]
        assert '"Uma issue"' in inicio
        assert "@ Doing" in inicio
        assert "agent='engineering'" in inicio
        assert inicio.index('"Uma issue"') < inicio.index("@ Doing") < inicio.index("agent=")
