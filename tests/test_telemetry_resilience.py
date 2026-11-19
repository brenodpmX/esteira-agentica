import logging
import socket
import statistics
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("opentelemetry.sdk")

from opentelemetry.sdk._logs.export import LogRecordExporter, LogRecordExportResult  # noqa: E402
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult  # noqa: E402

from src.adapters import otel_telemetry  # noqa: E402
from src.core import telemetry  # noqa: E402
from src.core.board import Board, BoardPort, ChangeItem  # noqa: E402
from src.core.change_queue import ChangeQueue  # noqa: E402
from tests._telemetria_helpers import config_base, isolamento  # noqa: E402,F401


def _porta_fechada() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _PortaLenta(BoardPort):
    def __init__(self, latencia):
        self.latencia = latencia

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def get_issue(self, board_id, issue_id): return None
    def create_issue(self, board_id, title, body, column): return None
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass

    def move_issue(self, board_id, issue_id, column, from_column=None):
        time.sleep(self.latencia)


def _ciclo(itens=5, latencia=0.02):
    from src.core import sync

    queue = ChangeQueue()
    for i in range(itens):
        queue.add(ChangeItem.of("change-up", id=str(i), board="entrega"))
    with patch.object(sync, "_apply_change_up",
                      side_effect=lambda b, i, bo, q=None, c=None: bo.move_issue(b, i.id, "x")):
        started = time.perf_counter()
        sync.apply_changes(Board(_PortaLenta(latencia)), queue, config_base())
        return time.perf_counter() - started


def _ligar_coletor_fora_do_ar(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", f"http://127.0.0.1:{_porta_fechada()}")
    port = otel_telemetry.build(config_base())
    assert port is not None
    telemetry.configure(port, board_platform="github")
    return port


def test_ct_res_01_coletor_inacessivel_nao_trava_o_ciclo(isolamento, monkeypatch):
    port = _ligar_coletor_fora_do_ar(monkeypatch)
    duracao = _ciclo(itens=5, latencia=0.0)
    for _ in range(500):
        telemetry.emit(telemetry.EV_PIPE_CICLO, {"esteira.ciclo.duracao_s": 0.1})
    port.force_flush(100)
    assert duracao < otel_telemetry.EXPORT_TIMEOUT_S
    assert ChangeQueue().size() == 0
    started = time.perf_counter()
    port.shutdown()
    assert time.perf_counter() - started <= otel_telemetry.SHUTDOWN_TIMEOUT_S + 0.5


def test_ct_res_02_variacao_media_de_ciclo_ate_5_por_cento(isolamento, monkeypatch):
    def _media():
        return statistics.mean(_ciclo(itens=5, latencia=0.02) for _ in range(4))

    sem = min(_media() for _ in range(2))
    port = _ligar_coletor_fora_do_ar(monkeypatch)
    com = min(_media() for _ in range(2))
    telemetry.configure(None)
    port.shutdown(0.5)
    assert com <= sem * 1.05


class _ExportadorTravado(SpanExporter, LogRecordExporter):
    def __init__(self):
        self.liberar = threading.Event()
        self.recebidos = 0

    def export(self, batch):
        self.recebidos += len(batch)
        self.liberar.wait(10)
        return SpanExportResult.FAILURE

    def shutdown(self):
        self.liberar.set()

    def force_flush(self, timeout_millis=30000):
        return False


def test_ct_res_03_fila_cheia_descarta_sem_bloquear(isolamento):
    exportador = _ExportadorTravado()
    port = otel_telemetry.OtelTelemetry(
        telemetry.resource_attributes(config_base()), span_exporter=exportador,
        log_exporter=exportador, max_queue_size=8, schedule_delay_ms=10,
    )
    telemetry.configure(port)
    try:
        started = time.perf_counter()
        for i in range(2000):
            telemetry.emit(telemetry.EV_PIPE_CICLO, {"esteira.ciclo.duracao_s": float(i)})
            with telemetry.span("esteira.sync.item change-up"):
                pass
        assert time.perf_counter() - started < 2.0
        assert exportador.recebidos <= 2 * 16
        assert otel_telemetry.MAX_QUEUE_SIZE <= 2048
        assert otel_telemetry.EXPORT_TIMEOUT_MS <= 2000
        assert otel_telemetry.SCHEDULE_DELAY_MS == 5000
        started = time.perf_counter()
        port.shutdown(0.5)
        assert time.perf_counter() - started < 1.0
    finally:
        exportador.liberar.set()


def test_ct_res_04_um_aviso_por_janela_de_10_minutos(isolamento, monkeypatch):
    clock = {"t": 1000.0}
    avisos = []
    monkeypatch.setattr(otel_telemetry.log, "warning",
                        lambda *a, **k: avisos.append((a, k)))
    handler = otel_telemetry.ExportWarningHandler(clock=lambda: clock["t"])
    otel_telemetry.install_warning_handler(handler)
    sdk = logging.getLogger("opentelemetry.exporter.otlp.proto.http.trace_exporter")
    for _ in range(5):
        sdk.warning("Failed to export span batch to http://u:segredo@host:4318")
        clock["t"] += 60
    assert len(avisos) == 1
    assert "segredo" not in str(avisos[0])
    clock["t"] += 600
    sdk.error("Failed to export logs batch")
    sdk.warning("Failed again")
    assert len(avisos) == 2
    assert logging.getLogger("opentelemetry").propagate is False


def test_ct_res_04_falha_real_de_export_gera_aviso_unico(isolamento, monkeypatch):
    avisos = []
    monkeypatch.setattr(otel_telemetry.log, "warning",
                        lambda *a, **k: avisos.append((a, k)))
    port = _ligar_coletor_fora_do_ar(monkeypatch)
    for _ in range(3):
        telemetry.emit(telemetry.EV_PIPE_CICLO, {"esteira.ciclo.duracao_s": 0.1})
        port.force_flush(3000)
    port.shutdown()
    assert len([a for a in avisos if a[1].get("event") == "telemetria_export_falha"]) == 1


def test_ct_res_05_shutdown_com_teto_de_2s(isolamento):
    exportador = _ExportadorTravado()
    port = otel_telemetry.OtelTelemetry(
        telemetry.resource_attributes(config_base()), span_exporter=exportador,
        log_exporter=exportador,
    )
    telemetry.configure(port)
    try:
        for _ in range(50):
            telemetry.emit(telemetry.EV_PIPE_CICLO, {"esteira.ciclo.duracao_s": 0.1})
        started = time.perf_counter()
        telemetry.shutdown(10)
        assert time.perf_counter() - started <= otel_telemetry.SHUTDOWN_TIMEOUT_S + 0.3
    finally:
        exportador.liberar.set()


def test_ct_res_05_main_encerra_telemetria_no_sigterm(isolamento):
    import src.__main__ as m

    port = MagicMock()
    port.enabled = False
    with patch.object(m, "check_config", return_value=config_base()), \
         patch.object(m, "setup_telemetry"), patch.object(m, "InstanceLock"), \
         patch.object(m, "startup"), patch.dict(m.ADAPTERS, {"github": MagicMock()}), \
         patch.object(m, "Board"), patch("src.core.agent_circuit_break.check_label_capability"), \
         patch.object(m, "board_startup_sync"), \
         patch.object(m, "detect_local_all", side_effect=m._Shutdown()), \
         patch.object(m, "shutdown_telemetry") as encerrar, \
         patch("signal.signal"), patch("builtins.print"):
        m.main()
    encerrar.assert_called_once()
