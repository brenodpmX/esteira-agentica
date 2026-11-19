import json
import os
from pathlib import Path

import pytest

from src.core import telemetry

ENV_VARS = (
    "OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_PROTOCOL", "OTEL_SDK_DISABLED",
    "OTEL_RESOURCE_ATTRIBUTES", "OTEL_SERVICE_NAME", "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_TIMEOUT", "OTEL_METRIC_EXPORT_INTERVAL",
    "PIPE_ENVIRONMENT", "ESTEIRA_TELEMETRIA_TITULO",
)

BOARD_ID = "entrega"
COL_ID = "desenvolvimento"
REPO_URL = "https://github.com/acme/esteira-demo.git"


def limpar_ambiente(monkeypatch):
    for name in list(os.environ):
        if name.startswith("OTEL_") or name in ENV_VARS:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def isolamento(monkeypatch, tmp_path):
    limpar_ambiente(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pipe").mkdir(exist_ok=True)
    telemetry.configure(None)
    from src.core import sync_circuit_breaker
    sync_circuit_breaker.reset_memory_state()
    yield tmp_path
    port = telemetry.current()
    telemetry.configure(None)
    try:
        port.shutdown(0.5)
    except Exception:
        pass


def config_base(**extra):
    config = {
        "git": {
            "repo": {"main": REPO_URL},
            "flow": {
                "base": "main",
                "feature": {"prefix": "feature/", "create": "main",
                            "merge": "main", "branch_pattern": "feature/{id}-{slug}"},
            },
        },
        "boards": {
            "platform": "github",
            BOARD_ID: {
                "name": "Entrega", "priority": 0, "flow": "feature", "repo": "main",
                "columns": {
                    "backlog": {"name": "Backlog"},
                    COL_ID: {"name": "Desenvolvimento", "agent": "dev",
                             "change": {"advance": "execucao-testes"}},
                    "execucao-testes": {"name": "Execução de Testes"},
                },
            },
        },
        "agents": {
            "kiro-cli": {"dev": {"name": "engineering", "model": "claude-sonnet-4"}},
        },
        "sleep": 60,
    }
    config.update(extra)
    return config


class Coletor:
    def __init__(self, port, spans, logs, reader):
        self.port = port
        self.span_exporter = spans
        self.log_exporter = logs
        self.reader = reader

    def registros(self):
        return [r for r in self.log_exporter.get_finished_logs()]

    def eventos(self, name=None):
        out = []
        for r in self.registros():
            attrs = dict(r.log_record.attributes or {})
            if name is None or attrs.get("event.name") == name:
                out.append(attrs)
        return out

    def registros_de(self, name):
        return [r for r in self.registros()
                if (r.log_record.attributes or {}).get("event.name") == name]

    def nomes_eventos(self):
        return {(r.log_record.attributes or {}).get("event.name") for r in self.registros()}

    def spans(self, prefix=None):
        return [s for s in self.span_exporter.get_finished_spans()
                if prefix is None or s.name.startswith(prefix)]

    def metricas(self):
        data = self.reader.get_metrics_data()
        out = {}
        if data is None:
            return out
        for rm in data.resource_metrics:
            for sm in rm.scope_metrics:
                for metric in sm.metrics:
                    pts = out.setdefault(metric.name, [])
                    for p in metric.data.data_points:
                        pts.append((p.value, dict(p.attributes or {})))
        return out

    def recursos_metricas(self):
        data = self.reader.get_metrics_data()
        return [dict(rm.resource.attributes) for rm in data.resource_metrics] if data else []


def instalar(config=None, resource=None, board_platform="github", batch=False):
    pytest.importorskip("opentelemetry.sdk")
    from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from src.adapters.otel_telemetry import OtelTelemetry

    spans = InMemorySpanExporter()
    logs = InMemoryLogRecordExporter()
    reader = InMemoryMetricReader()
    attrs = resource or telemetry.resource_attributes(config or config_base())
    port = OtelTelemetry(attrs, span_exporter=spans, log_exporter=logs,
                         metric_readers=[reader], batch=batch)
    telemetry.configure(port, board_platform=board_platform)
    return Coletor(port, spans, logs, reader)


def escrever_issue(tmp_path, issue_id="42", col_id=COL_ID, titulo="Envio telemetria",
                   board_id=BOARD_ID, body="Corpo da issue.\n"):
    issue_dir = Path(tmp_path) / ".pipe" / "boards" / board_id / col_id
    issue_dir.mkdir(parents=True, exist_ok=True)
    body_path = issue_dir / f"{issue_id}-envio_telemetria-body.md"
    body_path.write_text(f"# {titulo}\n\n{body}", encoding="utf-8")
    return body_path


def escrever_snapshot(board_id, issues, columns=None):
    board_dir = Path(".pipe/boards") / board_id
    board_dir.mkdir(parents=True, exist_ok=True)
    data = {"board": columns or {}, "issues": issues, "last_sync": None}
    (board_dir / "snapshot.json").write_text(json.dumps(data), encoding="utf-8")


def issue_snapshot(issue_id="42", col_id=COL_ID, body_path="", **extra):
    data = {
        "id": issue_id, "column": col_id, "body_path": str(body_path),
        "body_mtime": "1.0", "created_at": "2026-11-01T10:00:00Z",
        "updated_at": "2026-11-01T10:00:00Z", "status": "ok", "labels": [],
        "parent": None, "children": [], "blocked_by": [], "blocks": [],
        "archived": False, "state": "open",
    }
    data.update(extra)
    return data


def todos_os_valores(coletor):
    valores = []
    for r in coletor.registros():
        valores.extend(str(v) for v in (r.log_record.attributes or {}).values())
        valores.append(str(r.log_record.body))
    for s in coletor.spans():
        valores.append(s.name)
        valores.extend(str(v) for v in (s.attributes or {}).values())
    for pts in coletor.metricas().values():
        for _, attrs in pts:
            valores.extend(str(v) for v in attrs.values())
    for attrs in [dict(coletor.port.resource_attributes)]:
        valores.extend(str(v) for v in attrs.values())
    return valores
