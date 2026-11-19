import re
import socket
import time
from unittest.mock import MagicMock, patch

import pytest

from src.adapters import otel_telemetry
from src.core import execution, telemetry
from src.core.execution import ExecutionResult
from tests._telemetria_helpers import config_base, escrever_issue, isolamento  # noqa: F401

OTLP_PORTS = {4317, 4318}


@pytest.fixture
def conexoes(monkeypatch):
    tentativas = []
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create = socket.create_connection

    def _port(address):
        return address[1] if isinstance(address, tuple) and len(address) >= 2 else None

    def connect(self, address):
        tentativas.append(_port(address))
        return original_connect(self, address)

    def connect_ex(self, address):
        tentativas.append(_port(address))
        return original_connect_ex(self, address)

    def create_connection(address, *a, **k):
        tentativas.append(_port(address))
        return original_create(address, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    return tentativas


def _ciclo(m, tmp_path):
    from src.core import sync
    from src.core.board import Board, ChangeItem
    from src.core.change_queue import ChangeQueue

    m.setup_telemetry(config_base())
    m.emit_lifecycle("startup")
    body = escrever_issue(tmp_path)
    task = {
        "board_id": "entrega", "board": {"flow": "feature", "repo": "main"},
        "col_id": "desenvolvimento",
        "column": {"name": "Desenvolvimento", "agent": "dev", "gitevents": "no-branch",
                   "target-prompt": "Execute", "change": {"advance": "execucao-testes"}},
        "issue": {"id": "42", "body_path": str(body)},
    }
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record",
                      return_value={"instrucoes_obrigatorias_carregadas": True}), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery",
                      return_value=ExecutionResult(classe=execution.SUCEDIDO)):
        m.call_agent(config_base(), task)
    queue = ChangeQueue()
    queue.add(ChangeItem.of("change-up", id="42", board="entrega"))
    port = MagicMock()
    with patch.object(sync, "_apply_change_up",
                      side_effect=lambda b, i, bo, q=None, c=None: bo.move_issue(b, i.id, "x")):
        sync.apply_changes(Board(port), queue, config_base())
    m.emit_cycle(time.monotonic(), True, 0)
    m.shutdown_telemetry()


def test_ct_noop_01_sem_endpoint_nenhuma_conexao(isolamento, tmp_path, conexoes):
    import src.__main__ as m

    with patch.object(otel_telemetry, "_otlp_exporters",
                      side_effect=AssertionError("exporter instanciado")) as spy:
        assert otel_telemetry.build(config_base()) is None
        _ciclo(m, tmp_path)
    spy.assert_not_called()
    assert telemetry.enabled() is False
    assert [p for p in conexoes if p in OTLP_PORTS] == []


def test_ct_noop_02_sdk_disabled_mesmo_com_endpoint(isolamento, tmp_path, conexoes, monkeypatch):
    import src.__main__ as m

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    with patch.object(otel_telemetry, "_otlp_exporters",
                      side_effect=AssertionError("exporter instanciado")) as spy:
        assert otel_telemetry.build(config_base()) is None
        _ciclo(m, tmp_path)
    spy.assert_not_called()
    assert [p for p in conexoes if p in OTLP_PORTS] == []


def test_disabled_reconhece_variaveis():
    assert otel_telemetry.disabled({}) is True
    assert otel_telemetry.disabled({"OTEL_EXPORTER_OTLP_ENDPOINT": "  "}) is True
    assert otel_telemetry.disabled({"OTEL_EXPORTER_OTLP_ENDPOINT": "http://x:4318"}) is False
    assert otel_telemetry.disabled({"OTEL_EXPORTER_OTLP_ENDPOINT": "http://x:4318",
                                    "OTEL_SDK_DISABLED": "TRUE"}) is True


_HORA = re.compile(r"^\d{2}:\d{2}:\d{2} ", re.MULTILINE)


def test_ct_noop_03_saida_de_terminal_identica(isolamento, tmp_path, capsys):
    import src.__main__ as m

    def _rodar(sem_instrumentacao):
        if sem_instrumentacao:
            with patch.object(m, "setup_telemetry"), \
                 patch.object(telemetry, "emit"), patch.object(telemetry, "span"), \
                 patch.object(telemetry, "incidente"):
                _ciclo(m, tmp_path)
        else:
            _ciclo(m, tmp_path)
        return _HORA.sub("", capsys.readouterr().out)

    baseline = _rodar(True)
    instrumentado = _rodar(False)
    assert instrumentado == baseline
    assert "Telemetria" not in instrumentado


def test_ct_noop_04_custo_do_caminho_noop_desprezivel(isolamento, tmp_path):
    from src.core import sync
    from src.core.board import Board, ChangeItem
    from src.core.change_queue import ChangeQueue

    chamadas = {"n": 0}
    reais = (telemetry.emit, telemetry.span, telemetry.enabled)

    def _contar(fn):
        def wrapper(*a, **k):
            chamadas["n"] += 1
            return fn(*a, **k)
        return wrapper

    queue = ChangeQueue()
    for i in range(20):
        queue.add(ChangeItem.of("change-up", id=str(i), board="entrega"))
    port = MagicMock()
    started = time.perf_counter()
    with patch.object(telemetry, "emit", _contar(reais[0])), \
         patch.object(telemetry, "span", _contar(reais[1])), \
         patch.object(telemetry, "enabled", _contar(reais[2])), \
         patch.object(sync, "_apply_change_up",
                      side_effect=lambda b, i, bo, q=None, c=None: bo.move_issue(b, i.id, "x")):
        sync.apply_changes(Board(port), queue, config_base())
    carga = time.perf_counter() - started

    n = 20000
    t0 = time.perf_counter()
    for _ in range(n):
        telemetry.enabled()
        telemetry.emit("x", {"a": 1})
        with telemetry.span("x", {"a": 1}):
            pass
    custo_unitario = (time.perf_counter() - t0) / (3 * n)

    assert chamadas["n"] > 0
    assert chamadas["n"] * custo_unitario <= 0.05 * carga
