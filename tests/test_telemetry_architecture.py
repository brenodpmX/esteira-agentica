import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core import telemetry
from src.core.execution import ExecutionResult, SUCEDIDO
from tests._telemetria_helpers import config_base, escrever_issue, isolamento  # noqa: F401

CORE = Path(__file__).resolve().parents[1] / "src" / "core"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_ct_arch_01_core_nao_importa_opentelemetry():
    infratores = [
        (str(p.relative_to(CORE)), name)
        for p in sorted(CORE.rglob("*.py"))
        for name in _imports(p)
        if name.split(".")[0] == "opentelemetry"
    ]
    assert infratores == []


def test_ct_arch_01_port_e_abstrato_e_noop_e_o_default(isolamento):
    assert issubclass(telemetry.NoopTelemetry, telemetry.TelemetryPort)
    assert isinstance(telemetry.current(), telemetry.NoopTelemetry)
    assert telemetry.enabled() is False


def test_ct_arch_02_core_funciona_com_port_noop(isolamento, tmp_path):
    import src.__main__ as m

    body = escrever_issue(tmp_path)
    task = {
        "board_id": "entrega", "board": {"flow": "feature", "repo": "main"},
        "col_id": "desenvolvimento",
        "column": {"name": "Desenvolvimento", "agent": "dev", "gitevents": "no-branch",
                   "target-prompt": "Execute", "change": {"advance": "execucao-testes"}},
        "issue": {"id": "42", "body_path": str(body)},
    }
    resultado = ExecutionResult(classe=SUCEDIDO)
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record",
                      return_value={"instrucoes_obrigatorias_carregadas": True}), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery", return_value=resultado):
        assert m.call_agent(config_base(), task) is resultado

    with telemetry.span("qualquer", {"a": 1}) as span:
        span.set_attributes({"b": 2})
        span.set_error("X")
    telemetry.emit(telemetry.EV_PIPE_CICLO, {"esteira.ciclo.duracao_s": 1.0})
    telemetry.register_gauge("x", "1", "", lambda: [(1, {})])
    telemetry.shutdown(0.1)


def test_falha_do_port_nunca_propaga(isolamento):
    class Quebrado(telemetry.TelemetryPort):
        enabled = True

        def emit_event(self, name, attributes):
            raise RuntimeError("boom")

        def start_span(self, name, attributes):
            raise RuntimeError("boom")

        def register_gauge(self, name, unit, description, callback):
            raise RuntimeError("boom")

        def shutdown(self, timeout_s=2.0):
            raise RuntimeError("boom")

    telemetry.configure(Quebrado())
    telemetry.emit("x", {"a": 1})
    with telemetry.span("x") as span:
        span.set_attributes({"a": 1})
    telemetry.register_gauge("x", "1", "", lambda: [])
    telemetry.shutdown()


def test_excecao_de_negocio_dentro_do_span_propaga(isolamento):
    import pytest

    class Spy(telemetry.NoopTelemetry):
        enabled = True

    telemetry.configure(Spy())
    with pytest.raises(ValueError):
        with telemetry.span("x"):
            raise ValueError("negócio")
