"""Regressão: _detect_failure avalia apenas canais estruturados do kiro-cli.

Issue #206 — `_detect_failure` não deve avaliar a narrativa do agente, só os
canais estruturados do kiro-cli (defeito D5 do incidente #203).

Casos de teste derivados de:
  doc/quality/problemas-execucao-kiro/test-cases-detect-failure-canais-estruturados.md

Reproduz o falso positivo real: a execução da triagem da issue #203
(logs/203/2026-08-24_21-39-38.md) terminou com sucesso (exit 0, linha final
`▸ Credits: 4.52 • Time: 4m 2s`) e foi classificada como falha porque o
agente citou `"Kiro is having trouble responding right now"` na narrativa ao
analisar o próprio incidente.

A correção faz `_detect_failure` usar canais estruturados (returncode + tail
do output) em vez de varrer o texto completo da narrativa.
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


# ─── CT-001 — Marcador na narrativa com returncode=0 não é falha ─────────────

class TestNarrativaCitandoMarcadorNaoEFalha:
    """CT-001: marcador de falha citado só na narrativa do agente, execução
    bem-sucedida (returncode=0, sem bloco de erro no tail), não dispara falha.

    Reproduz o caso real de logs/203/2026-08-24_21-39-38.md.
    """

    def test_citacao_kiro_trouble_na_narrativa_com_exit_0(self, adapter):
        """Caso exato do incidente: agente cita a frase ao analisar um log."""
        output = (
            "Analisando o incidente #203...\n"
            "Encontrei no log a mensagem:\n"
            '> Note the error text itself is odd: it comes wrapped inside '
            '"Kiro is having trouble responding right now" / "dispatch failure '
            '(io error)" — with "Tool approval required..." appearing as '
            'trailing text after "Location:". This looks like two concatenated/'
            "garbled messages.\n"
            "\n"
            "Conclusão da análise: o agente citou a frase de erro mas a "
            "execução completou normalmente.\n"
            "\n"
            "Resumo da triagem:\n"
            "- Problema confirmado.\n"
            "- Issue avançada para analise-tecnica.\n"
            "\n"
            " ▸ Credits: 4.52 • Time: 4m 2s\n"
        )
        assert adapter._detect_failure(output, returncode=0) is None

    def test_citacao_kiro_trouble_longa_narrativa(self, adapter):
        """Narrativa com mais de _TAIL_LINES linhas antes do epilogo."""
        # Gera narrativa longa com citação no meio
        linhas_narrativa = [f"Analisando linha {i}..." for i in range(50)]
        linhas_narrativa[25] = (
            'O log original mostrava "Kiro is having trouble responding right '
            'now" antes de dispatch failure.'
        )
        linhas_narrativa.append("")
        linhas_narrativa.append(" ▸ Credits: 2.10 • Time: 1m 30s")
        linhas_narrativa.append("")
        output = "\n".join(linhas_narrativa)
        assert adapter._detect_failure(output, returncode=0) is None


# ─── CT-002 — Múltiplos marcadores na narrativa, todos ignorados ─────────────

class TestMultiplosMarcadoresNaNarrativa:
    """CT-002: múltiplas citações a marcadores diferentes na narrativa do
    agente, todas com returncode=0 e sem bloco de erro no tail.
    """

    @pytest.mark.parametrize("citacao", [
        'O log antigo mostrava "[TIMEOUT]" antes da correção do agente X.',
        'Encontramos "[ERRO] kiro-cli não encontrado no PATH" no histórico.',
        'A frase "Kiro is having trouble responding" indicava o problema.',
        'O output tinha "[exit-code: 1]" no log de referência analisado.',
    ])
    def test_cada_marcador_citado_na_narrativa_nao_e_falha(self, adapter, citacao):
        output = (
            "Trabalhando na issue #42...\n"
            f"{citacao}\n"
            "Implementação concluída com sucesso.\n"
            "\n"
            " ▸ Credits: 3.00 • Time: 2m 0s\n"
        )
        assert adapter._detect_failure(output, returncode=0) is None

    def test_todos_marcadores_juntos_na_narrativa(self, adapter):
        """Agente cita todos os marcadores no mesmo output — ainda sucesso."""
        output = (
            "Analisando os padrões de falha do kiro-cli:\n"
            '- "[exit-code:" indica processo com returncode != 0\n'
            '- "[TIMEOUT]" indica que o agente excedeu o tempo limite\n'
            '- "[ERRO]" indica kiro-cli não encontrado\n'
            '- "Kiro is having trouble responding" indica erro de servidor\n'
            "\n"
            "Documentação atualizada.\n"
            "\n"
            " ▸ Credits: 1.50 • Time: 45s\n"
        )
        assert adapter._detect_failure(output, returncode=0) is None


# ─── CT-003 — returncode != 0 continua detectado como falha ──────────────────

class TestReturnCodeNaoZeroEFalha:
    """CT-003: returncode != 0 é falha real (não regressão)."""

    def test_exit_code_1_com_marcador_detecta_falha(self, adapter):
        output = (
            "Trabalhando...\n"
            "error: algo falhou gravemente\n"
            "[exit-code: 1]\n"
        )
        error = adapter._detect_failure(output, returncode=1)
        assert error is not None
        assert "exit-code" in error or "error" in error.lower()

    def test_exit_code_2_sem_hints_usa_ultimas_linhas(self, adapter):
        output = "linha a\nlinha b\nlinha c\n[exit-code: 2]\n"
        error = adapter._detect_failure(output, returncode=2)
        assert error is not None


# ─── CT-004 — Bloco real de erro do kiro-cli no tail é detectado ─────────────

class TestBlocoRealDeErroDetectado:
    """CT-004: bloco de erro real do kiro-cli no encerramento do output
    (com ou sem exit-code != 0) é detectado corretamente.
    """

    def test_dispatch_failure_com_exit_code_1(self, adapter):
        """Padrão real de logs/175/2026-08-24_20-38-06.md."""
        output = (
            "Trabalhando na issue...\n"
            "Tool validation failed:\n"
            "Kiro is having trouble responding right now:\n"
            "   0: Failed to receive the next message: request_id: fd2356c2, "
            "error: dispatch failure (io error): request or response body error\n"
            "\n"
            "Location:\n"
            "   crates/chat-cli/src/cli/chat/mod.rs:2213\n"
            "\n"
            "error: Tool approval required but --no-interactive was specified. "
            "Use --trust-all-tools to automatically approve tools.\n"
            "\n"
            "[exit-code: 1]\n"
        )
        error = adapter._detect_failure(output, returncode=1)
        assert error is not None
        assert "dispatch failure" in error or "Tool approval" in error

    def test_kiro_trouble_com_exit_0_no_tail(self, adapter):
        """Padrão real de logs/177/2026-08-22_21-31-32.md: kiro-cli reporta
        erro mas encerra com exit 0."""
        output = (
            "Trabalhando...\n"
            "Tool validation failed:\n"
            "Kiro is having trouble responding right now:\n"
            "   0: Failed to receive the next message: request_id: 0b5ba885, "
            "error: dispatch failure (io error): request or response body error\n"
            "\n"
            "Location:\n"
            "   crates/chat-cli/src/cli/chat/mod.rs:2213\n"
        )
        error = adapter._detect_failure(output, returncode=0)
        assert error is not None
        assert "Kiro is having trouble responding" in error

    def test_modelo_indisponivel_com_exit_0(self, adapter):
        """kiro-cli reporta modelo indisponível e sai com exit 0."""
        output = (
            "Iniciando tarefa...\n"
            "Kiro is having trouble responding right now:\n"
            "   0: The model you've selected is temporarily unavailable\n"
            "Request ID: abc-123\n"
        )
        error = adapter._detect_failure(output, returncode=0)
        assert error is not None
        assert "temporarily unavailable" in error


# ─── CT-005 — "error" na narrativa sem marcador não é falha ──────────────────

class TestPalavraErrorSemMarcadorNaoEFalha:
    """CT-005: menção a 'error'/'Error:' na narrativa sem canal estruturado
    de falha não é falha (não regressão do comportamento existente)."""

    def test_narrativa_sobre_error_handling(self, adapter):
        output = (
            "Implementando o tratamento de error handling do adapter.\n"
            "Error: era a mensagem antiga; agora usamos ConfigError.\n"
            "Concluído.\n"
        )
        assert adapter._detect_failure(output, returncode=0) is None


# ─── CT-006 — Timeout e kiro-cli não encontrado continuam detectados ─────────

class TestSaidasSinteticasDoAdapter:
    """CT-006: saídas sintéticas do adapter (processo não completou)
    continuam sendo detectadas como falha."""

    def test_timeout(self, adapter):
        output = "[TIMEOUT] Agente excedeu 3600s"
        error = adapter._detect_failure(output, returncode=None)
        assert error is not None
        assert "TIMEOUT" in error

    def test_kiro_cli_nao_encontrado(self, adapter):
        output = "[ERRO] kiro-cli não encontrado no PATH"
        error = adapter._detect_failure(output, returncode=None)
        assert error is not None
        assert "ERRO" in error


# ─── CT-007 — Contrato: decisão depende do canal estruturado ─────────────────

class TestContratoDecisaoPorCanalEstruturado:
    """CT-007: a mesma narrativa com marcadores produz resultados diferentes
    dependendo do canal estruturado (returncode), provando que a decisão não
    é mais baseada apenas em correspondência textual sobre o output inteiro.
    """

    def test_mesma_narrativa_resultados_diferentes_por_returncode(self, adapter):
        """Texto idêntico, variando apenas returncode: prova de que a decisão
        usa canal estruturado."""
        # Narrativa longa que cita marcador (> _TAIL_LINES acima do final)
        linhas = [f"Linha de trabalho {i}" for i in range(40)]
        linhas[10] = "Kiro is having trouble responding right now (citação do log)"
        linhas.append(" ▸ Credits: 2.00 • Time: 1m 0s")
        output = "\n".join(linhas)

        # Com returncode=0: marcador está no corpo, não no tail → sucesso
        resultado_sucesso = adapter._detect_failure(output, returncode=0)

        # Com returncode=1: processo falhou, tail é consultado para extrair
        # causa (e o [exit-code:] seria apendado por _run, mas aqui testamos
        # apenas o critério de decisão do returncode)
        output_com_exit = output + "\n[exit-code: 1]\n"
        resultado_falha = adapter._detect_failure(output_com_exit, returncode=1)

        assert resultado_sucesso is None, (
            f"Com returncode=0, narrativa não deveria causar falha: {resultado_sucesso}"
        )
        assert resultado_falha is not None, (
            "Com returncode=1, deve ser detectado como falha"
        )

    def test_assinatura_aceita_returncode(self, adapter):
        """A função aceita o parâmetro returncode (canal estruturado)."""
        import inspect
        sig = inspect.signature(adapter._detect_failure)
        params = list(sig.parameters.keys())
        assert "returncode" in params, (
            f"_detect_failure deve aceitar 'returncode' como parâmetro: {params}"
        )


# ─── CT-008 — Integração com execute() (não regressão) ───────────────────────

class TestIntegracaoExecute:
    """CT-008: execute() repassa returncode a _detect_failure corretamente."""

    def _params(self):
        from src.core.agent import AgentParams
        return AgentParams(
            platform="kiro-cli", agent_id="dev", agent_name="engineering",
            model="claude", issue_id="42", board_id="task", col_id="doing",
            prompt="faca", work_dir=".", repo_id="main",
            col_name="Doing", title="Uma issue",
        )

    def test_narrativa_com_marcador_nao_falha_via_execute(self, monkeypatch, tmp_path):
        """Falso positivo do incidente: execute() classifica como sucesso."""
        from src.adapters import kiro_cli_agent as mod

        output = (
            "Analisando o incidente #203...\n"
            'O log mostrava "Kiro is having trouble responding right now"\n'
            "Conclusão: problema resolvido.\n"
            " ▸ Credits: 4.52 • Time: 4m 2s\n"
        )

        registros = []
        monkeypatch.setattr(mod.KiroCliAgent, "_create_log",
                            lambda self, params: tmp_path / "exec.md")
        monkeypatch.setattr(mod.KiroCliAgent, "_run",
                            lambda self, params, work_dir: (output, 0))
        monkeypatch.setattr(mod.log, "info",
                            lambda *a, **k: registros.append(("info", a, k)))
        monkeypatch.setattr(mod.log, "error",
                            lambda *a, **k: registros.append(("error", a, k)))

        KiroCliAgent().execute(self._params())

        # Deve ser logado como sucesso, não falha
        assert not any("falhou" in r[1][1] for r in registros), (
            f"Não deveria haver log de falha: {registros}"
        )
        conclusoes = [r for r in registros if "concluída" in r[1][1]]
        assert len(conclusoes) == 1

    def test_falha_real_via_execute(self, monkeypatch, tmp_path):
        """Falha real (exit 0, erro de modelo no tail) ainda detectada."""
        from src.adapters import kiro_cli_agent as mod

        output = (
            "Iniciando tarefa\n"
            "Kiro is having trouble responding right now:\n"
            "   0: The model you've selected is temporarily unavailable\n"
            "Request ID: abc-123\n"
        )

        registros = []
        monkeypatch.setattr(mod.KiroCliAgent, "_create_log",
                            lambda self, params: tmp_path / "exec.md")
        monkeypatch.setattr(mod.KiroCliAgent, "_run",
                            lambda self, params, work_dir: (output, 0))
        monkeypatch.setattr(mod.log, "info",
                            lambda *a, **k: registros.append(("info", a, k)))
        monkeypatch.setattr(mod.log, "error",
                            lambda *a, **k: registros.append(("error", a, k)))

        KiroCliAgent().execute(self._params())

        falhas = [r for r in registros if r[0] == "error"]
        assert len(falhas) == 1
        assert "temporarily unavailable" in falhas[0][1][1]
