import re
from pathlib import Path

from src.core.version import VERSION

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "doc" / "runbook" / "telemetria.md"
CONTEXT = ROOT / "CONTEXT.md"


def test_ct_ver_01_bump_minor():
    major, minor, patch = (int(x) for x in VERSION.split("."))
    assert major == 1
    assert minor >= 30


def test_ct_ver_02_runbook_cobre_contrato_operacional():
    texto = RUNBOOK.read_text(encoding="utf-8")
    for termo in ("OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_PROTOCOL",
                  "OTEL_SDK_DISABLED", "grpc", "http/protobuf", "4317", "4318",
                  "compose.telemetria.yml", "esteira-telemetria", "esteira-otlp",
                  "ESTEIRA_TELEMETRIA_TITULO", "deployment.environment.name"):
        assert termo in texto, termo
    assert "http://esteira-otlp:4318" in texto
    m = re.search(r"convenções GenAI:\*\*.*?v(\d+\.\d+\.\d+)", texto, re.DOTALL)
    assert m
    from src.adapters.otel_telemetry import SEMCONV_VERSION
    assert m.group(1) == SEMCONV_VERSION
    assert re.search(r"perda de telemetria é aceitável", texto, re.IGNORECASE)
    assert re.search(r"atraso no processamento.*não é", texto, re.IGNORECASE)


def test_ct_ver_02_runbook_lista_todo_o_contrato():
    from src.core import telemetry, telemetry_metrics

    texto = RUNBOOK.read_text(encoding="utf-8")
    for nome in telemetry.EVENTOS + telemetry_metrics.METRICAS + telemetry.INCIDENTES:
        assert nome in texto, nome


def test_ct_ver_03_context_documenta_a_entrega():
    texto = CONTEXT.read_text(encoding="utf-8")
    m = re.search(r"^### .*[Tt]elemetria.*\(v(\d+\.\d+\.\d+)", texto, re.MULTILINE)
    assert m
    assert m.group(1) == VERSION
    assert "TelemetryPort" in texto
