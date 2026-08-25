"""Política fail-closed para abort transitório do kiro-cli — issue #208.

Implementa os casos de teste CT-001..CT-009 de
`doc/quality/problemas-execucao-kiro/test-cases-retry-backoff-abort-transitorio-kiro-cli.md`,
derivados da ADR normativa `doc/architecture/retry-kiro-cli/idempotencia.md`
(decisão do débito #217).

Contrato provado aqui:

- `dispatch failure`, `InternalServerError` e timeout são resultados
  **ambíguos** (`UNKNOWN_OUTCOME`): o abort acontece no meio do turno, sem
  rollback, e pode ocorrer depois de `git commit`, `git push` ou movimentação
  de coluna já aplicados (evidência: execução de #175 no incidente #203);
- cada entrega invoca o subprocesso `kiro-cli chat` **exatamente uma vez** —
  nenhum retry/backoff inline, nenhuma chamada a `time.sleep` seguida de nova
  invocação;
- output integral, `request_id`, erro real e `session_id` permanecem
  disponíveis para auditoria e retomada posterior;
- a reentrega ocorre pelo loop normal, retomando a sessão com `--resume-id`;
- somente evidência positiva de não-inicialização (kiro-cli ausente do PATH)
  permite `DEFINITE_NOT_STARTED` — o único estado que admitiria retry;
- o caminho de sucesso permanece inalterado.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters import kiro_cli_agent as mod
from src.adapters.kiro_cli_agent import KiroCliAgent, Outcome, SingleInvocationViolation
from src.core.agent import AgentParams
from src.core.session import SessionIndex

# ══════════════════════════════════════════════════════════════════════════════
# Outputs reais capturados no incidente #203
# ══════════════════════════════════════════════════════════════════════════════

REQUEST_ID = "6c8d0b0e-1f2a-4a3b-9c7d-5e1f2a3b4c5d"

# Padrão literal do abort de #203 (bug upstream kirodotdev/Kiro#6065).
DISPATCH_FAILURE = (
    "Kiro is having trouble responding right now:\n"
    f"   0: Failed to receive the next message: request_id: {REQUEST_ID},\n"
    "      error: dispatch failure (io error): request or response body error\n"
)

# Abort de servidor após o agente já ter progredido no turno.
PARTIAL_THEN_INTERNAL_ERROR = (
    "Analisando a issue #175\n"
    "> Executando: git commit -m 'Desenvolvimento: ...'\n"
    "> Executando: git push -u origin feature175-175-circuit_brack_de_agente\n"
    "Kiro is having trouble responding right now:\n"
    "   0: InternalServerError\n"
    f"Request ID: {REQUEST_ID}\n"
)

SUCCESS_OUTPUT = (
    "Analisando a issue #42\n"
    "Editando src/core/sync.py\n"
    "Pronto. 3 arquivos alterados.\n"
    "\u25b8 Credits: 0.42\n"
)

SESSION_ID = "11111111-2222-3333-4444-555555555555"


# ══════════════════════════════════════════════════════════════════════════════
# Infraestrutura de teste
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _isola_estado(tmp_path, monkeypatch):
    """Isola `.pipe/` e `logs/` do teste (incidente #182: nunca tocar o real)."""
    monkeypatch.chdir(tmp_path)
    yield


class SubprocessSpy:
    """Substitui `subprocess.run` contando invocações do `kiro-cli chat`.

    Separa as chamadas de `chat` (a execução do agente, sujeita à política de
    invocação única) das chamadas auxiliares `chat --list-sessions`, que apenas
    consultam o índice de sessões do kiro-cli.
    """

    def __init__(self, output="", returncode=0, session_ids=(), raises=None):
        self.output = output
        self.returncode = returncode
        self.session_ids = list(session_ids)
        self.raises = raises
        self.chat_calls: list[list[str]] = []
        self.list_calls = 0

    def __call__(self, cmd, **kwargs):
        if "--list-sessions" in cmd:
            self.list_calls += 1
            return subprocess.CompletedProcess(
                cmd, 0, "\n".join(self.session_ids), ""
            )
        self.chat_calls.append(list(cmd))
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(cmd, self.returncode, self.output, "")

    @property
    def calls(self) -> int:
        return len(self.chat_calls)


class SleepSpy:
    """Registra chamadas de espera para provar a ausência de backoff inline."""

    def __init__(self):
        self.durations: list[float] = []

    def __call__(self, seconds):
        self.durations.append(seconds)


def params(**over) -> AgentParams:
    base = dict(
        platform="kiro-cli", agent_id="dev", agent_name="engineering",
        model="claude-sonnet-4.5", issue_id="175", board_id="task",
        col_id="desenvolvimento", prompt="Execute a tarefa", work_dir=".",
        repo_id="main", col_name="Desenvolvimento", title="Uma issue",
    )
    base.update(over)
    return AgentParams(**base)


@pytest.fixture
def spy_factory(monkeypatch):
    """Instala um `SubprocessSpy` e um `SleepSpy` (global) para o adapter.

    `time.sleep` é interceptado na própria stdlib: qualquer backoff introduzido
    em qualquer camada do caminho de execução é capturado, não só um alias
    importado no módulo do adapter.
    """
    def _install(**kw):
        spy = SubprocessSpy(**kw)
        sleep = SleepSpy()
        monkeypatch.setattr(mod.subprocess, "run", spy)
        monkeypatch.setattr(time, "sleep", sleep)
        return spy, sleep
    return _install


def run_adapter(spy_factory, tmp_path, **spy_kw):
    """Executa `_run` isolado e devolve (adapter, output, returncode, spy, sleep)."""
    spy, sleep = spy_factory(**spy_kw)
    agent = KiroCliAgent()
    output, returncode = agent._run(params(), tmp_path)
    return agent, output, returncode, spy, sleep


def execute_adapter(monkeypatch, tmp_path, spy_factory, **spy_kw):
    """Executa `execute()` capturando os logs de terminal e o log de execução."""
    spy, sleep = spy_factory(**spy_kw)
    registros: list[tuple] = []
    log_file = tmp_path / "exec.md"

    monkeypatch.setattr(mod.KiroCliAgent, "_create_log",
                        lambda self, p: log_file)
    monkeypatch.setattr(mod.log, "info",
                        lambda *a, **k: registros.append(("info", a, k)))
    monkeypatch.setattr(mod.log, "error",
                        lambda *a, **k: registros.append(("error", a, k)))

    agent = KiroCliAgent()
    agent.execute(params(work_dir=str(tmp_path)))
    return agent, registros, log_file, spy, sleep


# ══════════════════════════════════════════════════════════════════════════════
# CT-001 — dispatch failure real gera exatamente uma invocação
# ══════════════════════════════════════════════════════════════════════════════

class TestCT001DispatchFailureInvocacaoUnica:
    """O abort real de #203 não dispara segunda chamada ao subprocesso."""

    def test_uma_unica_invocacao_do_subprocesso(self, spy_factory, tmp_path):
        _, output, returncode, spy, _ = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE, returncode=1
        )
        assert spy.calls == 1, (
            f"a política fail-closed permite 1 invocação por entrega: {spy.calls}"
        )
        assert returncode == 1
        assert "dispatch failure" in output

    def test_classifica_como_unknown_outcome(self, spy_factory, tmp_path):
        agent, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE, returncode=1
        )
        error = agent._detect_failure(output, returncode)
        assert agent._classify(output, returncode, error) is Outcome.UNKNOWN_OUTCOME

    def test_marcador_ambiguo_identificado(self, spy_factory, tmp_path):
        agent, output, _, _, _ = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE, returncode=1
        )
        assert agent._ambiguous_marker(output) == "dispatch failure"

    def test_execute_registra_classificacao(self, monkeypatch, tmp_path,
                                            spy_factory):
        _, registros, log_file, spy, _ = execute_adapter(
            monkeypatch, tmp_path, spy_factory,
            output=DISPATCH_FAILURE, returncode=1,
        )
        assert spy.calls == 1
        erros = [r for r in registros if r[0] == "error"]
        assert len(erros) == 1, f"esperado 1 log de erro: {registros}"
        assert erros[0][2]["outcome"] == Outcome.UNKNOWN_OUTCOME.value
        assert "UNKNOWN_OUTCOME" in log_file.read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# CT-002 — InternalServerError após output parcial
# ══════════════════════════════════════════════════════════════════════════════

class TestCT002InternalServerErrorAposOutputParcial:
    """Progresso parcial (commit/push já feitos) não autoriza retry."""

    def test_uma_unica_invocacao(self, spy_factory, tmp_path):
        _, _, _, spy, _ = run_adapter(
            spy_factory, tmp_path, output=PARTIAL_THEN_INTERNAL_ERROR, returncode=1
        )
        assert spy.calls == 1

    def test_classifica_como_unknown_outcome(self, spy_factory, tmp_path):
        agent, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path, output=PARTIAL_THEN_INTERNAL_ERROR, returncode=1
        )
        error = agent._detect_failure(output, returncode)
        outcome = agent._classify(output, returncode, error)
        assert outcome is Outcome.UNKNOWN_OUTCOME
        assert outcome is not Outcome.SUCCEEDED
        assert outcome is not Outcome.DEFINITE_NOT_STARTED

    def test_abort_com_exit_code_zero_tambem_e_ambiguo(self, spy_factory, tmp_path):
        """O kiro-cli reporta erro de servidor com exit 0 (ver #206)."""
        agent, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path, output=PARTIAL_THEN_INTERNAL_ERROR, returncode=0
        )
        error = agent._detect_failure(output, returncode)
        assert error is not None, "erro de servidor com exit 0 deve ser falha"
        assert agent._classify(output, returncode, error) is Outcome.UNKNOWN_OUTCOME


# ══════════════════════════════════════════════════════════════════════════════
# CT-003 — timeout é UNKNOWN_OUTCOME, não falha definitiva
# ══════════════════════════════════════════════════════════════════════════════

class TestCT003TimeoutAmbiguo:
    """O processo pode ter produzido efeitos antes de exceder o limite."""

    def test_marcador_timeout_preservado(self, spy_factory, tmp_path):
        _, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path,
            raises=subprocess.TimeoutExpired(cmd="kiro-cli", timeout=mod._TIMEOUT),
        )
        assert "[TIMEOUT]" in output
        assert returncode is None

    def test_classifica_como_unknown_outcome(self, spy_factory, tmp_path):
        agent, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path,
            raises=subprocess.TimeoutExpired(cmd="kiro-cli", timeout=mod._TIMEOUT),
        )
        error = agent._detect_failure(output, returncode)
        outcome = agent._classify(output, returncode, error)
        assert outcome is Outcome.UNKNOWN_OUTCOME
        assert outcome is not Outcome.DEFINITE_NOT_STARTED

    def test_nenhuma_segunda_invocacao_apos_timeout(self, spy_factory, tmp_path):
        _, _, _, spy, sleep = run_adapter(
            spy_factory, tmp_path,
            raises=subprocess.TimeoutExpired(cmd="kiro-cli", timeout=mod._TIMEOUT),
        )
        assert spy.calls == 1
        assert sleep.durations == []

    def test_sessao_preservada_apos_timeout(self, spy_factory, tmp_path):
        """Continuidade: o timeout é ambíguo e a sessão precisa sobreviver."""
        run_adapter(
            spy_factory, tmp_path, session_ids=[SESSION_ID],
            raises=subprocess.TimeoutExpired(cmd="kiro-cli", timeout=mod._TIMEOUT),
        )
        assert SessionIndex().get("task", "175", "dev") == SESSION_ID


# ══════════════════════════════════════════════════════════════════════════════
# CT-004 — output integral, request ID e erro disponíveis
# ══════════════════════════════════════════════════════════════════════════════

class TestCT004Observabilidade:
    """Evidência preservada: o turno abortado é auditável."""

    def test_extrai_request_id_do_padrao_real(self, spy_factory, tmp_path):
        agent, output, _, _, _ = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE, returncode=1
        )
        assert agent._extract_request_id(output) == REQUEST_ID

    def test_extrai_request_id_do_formato_maiusculo(self, spy_factory, tmp_path):
        agent = KiroCliAgent()
        assert agent._extract_request_id(PARTIAL_THEN_INTERNAL_ERROR) == REQUEST_ID

    def test_sem_request_id_retorna_none(self):
        assert KiroCliAgent()._extract_request_id("nada aqui\n") is None

    def test_erro_identifica_a_causa_real(self, spy_factory, tmp_path):
        agent, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE, returncode=1
        )
        error = agent._detect_failure(output, returncode)
        assert "dispatch failure" in error
        assert error != agent._last_meaningful_line(output)

    def test_log_de_execucao_preserva_output_integral(self, monkeypatch, tmp_path,
                                                     spy_factory):
        _, _, log_file, _, _ = execute_adapter(
            monkeypatch, tmp_path, spy_factory,
            output=DISPATCH_FAILURE, returncode=1,
        )
        conteudo = log_file.read_text(encoding="utf-8")
        for linha in DISPATCH_FAILURE.strip().splitlines():
            assert linha in conteudo, f"output truncado, falta: {linha!r}"

    def test_log_de_execucao_registra_request_id_e_erro(self, monkeypatch, tmp_path,
                                                        spy_factory):
        _, registros, log_file, _, _ = execute_adapter(
            monkeypatch, tmp_path, spy_factory,
            output=DISPATCH_FAILURE, returncode=1,
        )
        conteudo = log_file.read_text(encoding="utf-8")
        assert REQUEST_ID in conteudo
        assert "dispatch failure" in conteudo

        erro = [r for r in registros if r[0] == "error"][0]
        assert "falhou:" in erro[1][1], "formato da linha de falha não pode mudar"
        assert erro[2]["request_id"] == REQUEST_ID
        assert erro[2]["invocations"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# CT-005 — session_id preservado após o abort
# ══════════════════════════════════════════════════════════════════════════════

class TestCT005SessaoPreservadaNoAbort:
    """A sessão descoberta após a chamada sobrevive ao abort (não regressão)."""

    def test_session_id_persistido_no_indice(self, spy_factory, tmp_path):
        run_adapter(spy_factory, tmp_path, output=DISPATCH_FAILURE,
                    returncode=1, session_ids=[SESSION_ID])
        assert SessionIndex().get("task", "175", "dev") == SESSION_ID

    def test_session_id_exposto_para_observabilidade(self, spy_factory, tmp_path):
        agent, _, _, _, _ = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE,
            returncode=1, session_ids=[SESSION_ID],
        )
        assert agent._last_session_id == SESSION_ID

    def test_sessao_no_log_de_execucao(self, monkeypatch, tmp_path, spy_factory):
        _, registros, log_file, _, _ = execute_adapter(
            monkeypatch, tmp_path, spy_factory,
            output=DISPATCH_FAILURE, returncode=1, session_ids=[SESSION_ID],
        )
        assert SESSION_ID in log_file.read_text(encoding="utf-8")
        erro = [r for r in registros if r[0] == "error"][0]
        assert erro[2]["session_id"] == SESSION_ID

    def test_sem_sessao_disponivel_nao_quebra(self, spy_factory, tmp_path):
        agent, _, _, _, _ = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE,
            returncode=1, session_ids=[],
        )
        assert agent._last_session_id is None
        assert SessionIndex().get("task", "175", "dev") is None


# ══════════════════════════════════════════════════════════════════════════════
# CT-006 — entrega posterior retoma via --resume-id
# ══════════════════════════════════════════════════════════════════════════════

class TestCT006RetomadaEmEntregaPosterior:
    """A nova tentativa é uma entrega distinta do loop, não retry inline."""

    def test_comando_usa_resume_id_conhecido(self, spy_factory, tmp_path):
        SessionIndex().set("task", "175", "dev", SESSION_ID)
        _, _, _, spy, _ = run_adapter(
            spy_factory, tmp_path, output=SUCCESS_OUTPUT,
            session_ids=[SESSION_ID],
        )
        cmd = spy.chat_calls[0]
        assert "--resume-id" in cmd
        assert cmd[cmd.index("--resume-id") + 1] == SESSION_ID

    def test_retomada_nao_soma_invocacoes(self, spy_factory, tmp_path):
        SessionIndex().set("task", "175", "dev", SESSION_ID)
        _, _, _, spy, sleep = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE, returncode=1,
            session_ids=[SESSION_ID],
        )
        assert spy.calls == 1
        assert sleep.durations == []

    def test_sessao_inexistente_nao_usa_resume_id(self, spy_factory, tmp_path):
        SessionIndex().set("task", "175", "dev", SESSION_ID)
        _, _, _, spy, _ = run_adapter(
            spy_factory, tmp_path, output=SUCCESS_OUTPUT, session_ids=[],
        )
        assert "--resume-id" not in spy.chat_calls[0]


# ══════════════════════════════════════════════════════════════════════════════
# CT-007 — ausência de retry inline
# ══════════════════════════════════════════════════════════════════════════════

class TestCT007SemRetryInline:
    """Trava explícita contra retry ingênuo (risco central da ADR)."""

    @pytest.mark.parametrize("output,returncode", [
        (DISPATCH_FAILURE, 1),
        (PARTIAL_THEN_INTERNAL_ERROR, 1),
        (PARTIAL_THEN_INTERNAL_ERROR, 0),
    ])
    def test_sem_sleep_e_sem_segunda_chamada(self, spy_factory, tmp_path,
                                             output, returncode):
        _, _, _, spy, sleep = run_adapter(
            spy_factory, tmp_path, output=output, returncode=returncode
        )
        assert spy.calls == 1
        assert sleep.durations == [], (
            f"backoff inline é proibido pela ADR: {sleep.durations}"
        )

    def test_orcamento_da_entrega_e_de_uma_invocacao(self):
        assert mod._MAX_INVOCATIONS == 1

    def test_segunda_invocacao_falha_explicitamente(self):
        """Um retry introduzido por engano quebra em vez de duplicar efeitos."""
        budget = mod._DeliveryBudget()
        budget.spend()
        with pytest.raises(SingleInvocationViolation):
            budget.spend()

    def test_execute_nao_dorme_no_abort(self, monkeypatch, tmp_path, spy_factory):
        _, _, _, spy, sleep = execute_adapter(
            monkeypatch, tmp_path, spy_factory,
            output=DISPATCH_FAILURE, returncode=1,
        )
        assert spy.calls == 1
        assert sleep.durations == []


# ══════════════════════════════════════════════════════════════════════════════
# CT-008 — caminho de sucesso inalterado
# ══════════════════════════════════════════════════════════════════════════════

class TestCT008SucessoInalterado:
    def test_classifica_como_succeeded(self, spy_factory, tmp_path):
        agent, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path, output=SUCCESS_OUTPUT, returncode=0
        )
        error = agent._detect_failure(output, returncode)
        assert error is None
        assert agent._classify(output, returncode, error) is Outcome.SUCCEEDED

    def test_log_de_conclusao_mantem_formato(self, monkeypatch, tmp_path,
                                            spy_factory):
        _, registros, log_file, spy, sleep = execute_adapter(
            monkeypatch, tmp_path, spy_factory,
            output=SUCCESS_OUTPUT, returncode=0,
        )
        finais = [r for r in registros if "concluída" in r[1][1]]
        assert len(finais) == 1, f"esperado 1 log de conclusão: {registros}"
        assert finais[0][0] == "info"
        assert "Credits" in finais[0][1][1]
        assert not any(r[0] == "error" for r in registros)
        assert spy.calls == 1
        assert sleep.durations == []
        assert "SUCCEEDED" in log_file.read_text(encoding="utf-8")

    def test_sucesso_nao_e_marcado_como_ambiguo(self, spy_factory, tmp_path):
        agent, output, _, _, _ = run_adapter(
            spy_factory, tmp_path, output=SUCCESS_OUTPUT, returncode=0
        )
        assert agent._ambiguous_marker(output) is None

    def test_narrativa_sobre_o_abort_nao_vira_unknown_outcome(self, spy_factory,
                                                              tmp_path):
        """Um agente que escreve *sobre* o abort não pode ser classificado nele.

        Mesmo falso-positivo já corrigido na detecção de rate limit e em #206:
        a classificação parte de `_detect_failure` (canais estruturados), nunca
        de uma varredura do corpo narrado pelo agente.
        """
        narrativa = (
            "Implementando a política fail-closed para dispatch failure.\n"
            "Também trato InternalServerError como UNKNOWN_OUTCOME.\n"
            "\u25b8 Credits: 0.10\n"
        )
        agent, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path, output=narrativa, returncode=0
        )
        error = agent._detect_failure(output, returncode)
        assert error is None
        assert agent._classify(output, returncode, error) is Outcome.SUCCEEDED


# ══════════════════════════════════════════════════════════════════════════════
# DEFINITE_NOT_STARTED — único estado com evidência de não-inicialização
# ══════════════════════════════════════════════════════════════════════════════

class TestDefiniteNotStarted:
    """Somente evidência positiva permite afirmar que nada executou."""

    def test_kiro_cli_ausente_do_path(self, spy_factory, tmp_path):
        agent, output, returncode, _, _ = run_adapter(
            spy_factory, tmp_path, raises=FileNotFoundError("kiro-cli"),
        )
        error = agent._detect_failure(output, returncode)
        assert agent._classify(output, returncode, error) is \
            Outcome.DEFINITE_NOT_STARTED

    def test_work_dir_ausente_e_nao_iniciado(self, monkeypatch, tmp_path,
                                             spy_factory):
        spy, _ = spy_factory(output=SUCCESS_OUTPUT)
        registros: list[tuple] = []
        monkeypatch.setattr(mod.KiroCliAgent, "_create_log",
                            lambda self, p: tmp_path / "exec.md")
        monkeypatch.setattr(mod.log, "info",
                            lambda *a, **k: registros.append(("info", a, k)))
        monkeypatch.setattr(mod.log, "error",
                            lambda *a, **k: registros.append(("error", a, k)))

        with pytest.raises(FileNotFoundError):
            KiroCliAgent().execute(params(work_dir=str(tmp_path / "inexistente")))

        assert spy.calls == 0
        erro = [r for r in registros if r[0] == "error"][0]
        assert erro[2]["outcome"] == Outcome.DEFINITE_NOT_STARTED.value

    def test_falha_apos_a_invocacao_e_ambigua(self, monkeypatch, tmp_path,
                                             spy_factory):
        """Exceção depois de o subprocesso rodar não prova ausência de efeito."""
        spy, _ = spy_factory(output=SUCCESS_OUTPUT)
        registros: list[tuple] = []
        monkeypatch.setattr(mod.KiroCliAgent, "_create_log",
                            lambda self, p: tmp_path / "exec.md")
        monkeypatch.setattr(mod.log, "info",
                            lambda *a, **k: registros.append(("info", a, k)))
        monkeypatch.setattr(mod.log, "error",
                            lambda *a, **k: registros.append(("error", a, k)))
        monkeypatch.setattr(mod.KiroCliAgent, "_detect_failure",
                            lambda self, o, rc=None: (_ for _ in ()).throw(
                                RuntimeError("falha ao classificar")))

        with pytest.raises(RuntimeError):
            KiroCliAgent().execute(params(work_dir=str(tmp_path)))

        assert spy.calls == 1
        erro = [r for r in registros if r[0] == "error"][0]
        assert erro[2]["outcome"] == Outcome.UNKNOWN_OUTCOME.value


# ══════════════════════════════════════════════════════════════════════════════
# CT-009 — proteção de estado interno intacta
# ══════════════════════════════════════════════════════════════════════════════

class TestCT009EstadoInternoProtegido:
    """A política não cria acesso novo a estado interno da esteira."""

    def test_sessions_json_e_o_unico_arquivo_escrito_em_pipe(self, spy_factory,
                                                             tmp_path):
        run_adapter(spy_factory, tmp_path, output=DISPATCH_FAILURE,
                    returncode=1, session_ids=[SESSION_ID])
        escritos = sorted(p.name for p in (tmp_path / ".pipe").rglob("*")
                          if p.is_file())
        assert escritos == ["sessions.json"], (
            f"o adapter não pode escrever outro estado interno: {escritos}"
        )

    def test_nenhum_path_protegido_no_prompt_do_subprocesso(self, spy_factory,
                                                            tmp_path):
        from src.core.agent import PROTECTED_PATHS

        _, _, _, spy, _ = run_adapter(
            spy_factory, tmp_path, output=DISPATCH_FAILURE, returncode=1
        )
        comando = " ".join(spy.chat_calls[0])
        for pattern in PROTECTED_PATHS:
            fixo = pattern.split("*")[0]
            assert fixo not in comando, (
                f"path protegido vazou para o comando: {pattern}"
            )

    def test_mensagem_de_resultado_nao_cita_estado_interno(self, monkeypatch,
                                                           tmp_path, spy_factory):
        from src.core.agent import PROTECTED_PATHS

        _, _, log_file, _, _ = execute_adapter(
            monkeypatch, tmp_path, spy_factory,
            output=DISPATCH_FAILURE, returncode=1, session_ids=[SESSION_ID],
        )
        resultado = log_file.read_text(encoding="utf-8").split("## Resultado")[-1]
        for pattern in PROTECTED_PATHS:
            assert pattern not in resultado
