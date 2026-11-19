from unittest.mock import patch

import pytest

from src.core import telemetry
from tests._telemetria_helpers import config_base, isolamento  # noqa: F401


def _linhas_info(m, config):
    linhas = []
    original = m.log.info

    def _spy(module, msg, *a, **k):
        linhas.append((module, msg, k))
        return original(module, msg, *a, **k)

    with patch.object(m.log, "info", _spy), patch.object(m.log, "trace") as trace:
        m.setup_telemetry(config)
    return linhas, trace


def test_ct_infra_03_startup_loga_identidade_e_endpoint_sem_credencial(isolamento, monkeypatch):
    pytest.importorskip("opentelemetry.sdk")
    import src.__main__ as m

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT",
                       "https://coletor:SENHA-XYZ@esteira-otlp:4318/otlp?token=QUERY-XYZ")
    config = config_base()
    config["git"]["repo"] = {"main": "https://u:TOKEN-XYZ@github.com/acme/esteira-demo.git"}
    linhas, _ = _linhas_info(m, config)
    assert telemetry.enabled() is True
    tele = [msg for module, msg, _ in linhas if module == "Telemetria"]
    assert len(tele) == 1
    linha = tele[0]
    assert "service.instance.id=https://github.com/acme/esteira-demo.git" in linha
    assert "esteira.pipe.nome=esteira-demo" in linha
    assert "endpoint=https://esteira-otlp:4318/otlp" in linha
    for segredo in ("SENHA-XYZ", "QUERY-XYZ", "TOKEN-XYZ", "coletor:"):
        assert segredo not in linha


def test_startup_sem_endpoint_nao_loga_no_terminal(isolamento):
    import src.__main__ as m

    linhas, trace = _linhas_info(m, config_base())
    assert [x for x in linhas if x[0] == "Telemetria"] == []
    assert trace.called
    assert telemetry.enabled() is False


def test_endpoint_for_log_remove_credencial():
    env = {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://user:pass@host:4317/?k=v#f"}
    assert telemetry.endpoint_for_log(env) == "http://host:4317/"
    assert telemetry.endpoint_for_log({}) is None


def test_protocolo_grpc_e_http():
    from src.adapters import otel_telemetry

    assert otel_telemetry.protocol({}) == "http/protobuf"
    assert otel_telemetry.protocol({"OTEL_EXPORTER_OTLP_PROTOCOL": "grpc"}) == "grpc"
    assert otel_telemetry.protocol({"OTEL_EXPORTER_OTLP_PROTOCOL": "http/json"}) == "http/protobuf"


@pytest.mark.parametrize("proto", ["grpc", "http/protobuf"])
def test_build_cria_exportadores_do_protocolo(isolamento, monkeypatch, proto):
    pytest.importorskip("opentelemetry.exporter.otlp")
    from src.adapters import otel_telemetry

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:1")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", proto)
    exporters = otel_telemetry._otlp_exporters(proto, {})
    modulo = "grpc" if proto == "grpc" else "http"
    assert all(f".proto.{modulo}." in type(e).__module__ for e in exporters)
    port = otel_telemetry.build(config_base())
    assert port is not None
    port.shutdown(0.5)
