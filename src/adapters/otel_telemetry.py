from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager

from src.core import telemetry
from src.core.log import log

MAX_QUEUE_SIZE = 2048
MAX_EXPORT_BATCH_SIZE = 512
SCHEDULE_DELAY_MS = 5000
EXPORT_TIMEOUT_MS = 2000
EXPORT_TIMEOUT_S = EXPORT_TIMEOUT_MS / 1000
METRIC_INTERVAL_MS = 60000
WARN_WINDOW_S = 600
SHUTDOWN_TIMEOUT_S = 2.0

PROTOCOL_ENV = "OTEL_EXPORTER_OTLP_PROTOCOL"
DISABLED_ENV = "OTEL_SDK_DISABLED"
METRIC_INTERVAL_ENV = "OTEL_METRIC_EXPORT_INTERVAL"
SCOPE = "esteira-agentica"
SEMCONV_VERSION = "1.44.0"
SEMCONV_SCHEMA_URL = f"https://opentelemetry.io/schemas/{SEMCONV_VERSION}"

_SDK_LOGGER = "opentelemetry"


def disabled(environ=None) -> bool:
    env = os.environ if environ is None else environ
    if (env.get(DISABLED_ENV) or "").strip().lower() == "true":
        return True
    return not (env.get(telemetry.ENDPOINT_ENV) or "").strip()


def protocol(environ=None) -> str:
    env = os.environ if environ is None else environ
    value = (env.get(PROTOCOL_ENV) or "http/protobuf").strip().lower()
    return "grpc" if value == "grpc" else "http/protobuf"


def _metric_interval_ms(environ) -> int:
    try:
        value = int((environ.get(METRIC_INTERVAL_ENV) or "").strip())
        return value if value > 0 else METRIC_INTERVAL_MS
    except ValueError:
        return METRIC_INTERVAL_MS


class ExportWarningHandler(logging.Handler):
    def __init__(self, clock=time.monotonic, window_s: float = WARN_WINDOW_S):
        super().__init__(level=logging.WARNING)
        self._clock = clock
        self._window_s = window_s
        self._last: float | None = None
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            now = self._clock()
            with self._lock:
                if self._last is not None and now - self._last < self._window_s:
                    return
                self._last = now
            detail = telemetry.sanitize_message(record.getMessage()).splitlines()
            log.warning(
                "Telemetria",
                "falha ao exportar telemetria - sinais descartados, processamento "
                "segue normalmente (próximo aviso em até 10 min)",
                event="telemetria_export_falha",
                detalhe=(detail[0][:200] if detail else ""),
            )
        except Exception:
            return


def install_warning_handler(handler: logging.Handler) -> None:
    sdk_logger = logging.getLogger(_SDK_LOGGER)
    for existing in list(sdk_logger.handlers):
        if isinstance(existing, ExportWarningHandler):
            sdk_logger.removeHandler(existing)
    sdk_logger.addHandler(handler)
    sdk_logger.setLevel(logging.WARNING)
    sdk_logger.propagate = False


class _OtelSpan(telemetry.TelemetrySpan):
    def __init__(self, span):
        self._span = span

    def set_attributes(self, attributes: dict) -> None:
        self._span.set_attributes(attributes)

    def set_error(self, error_type: str) -> None:
        from opentelemetry.trace import Status, StatusCode

        self._span.set_attribute("error.type", error_type)
        self._span.set_status(Status(StatusCode.ERROR))


class OtelTelemetry(telemetry.TelemetryPort):
    enabled = True

    def __init__(self, resource_attributes: dict, *, span_exporter, log_exporter,
                 metric_readers=(), batch: bool = True,
                 max_queue_size: int = MAX_QUEUE_SIZE,
                 schedule_delay_ms: int = SCHEDULE_DELAY_MS,
                 export_timeout_ms: int = EXPORT_TIMEOUT_MS):
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import (BatchLogRecordProcessor,
                                                    SimpleLogRecordProcessor)
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

        from src.core.version import VERSION

        self.resource_attributes = dict(resource_attributes)
        resource = Resource.create(self.resource_attributes)

        self._tracer_provider = TracerProvider(resource=resource)
        self._logger_provider = LoggerProvider(resource=resource)
        if batch:
            self._tracer_provider.add_span_processor(BatchSpanProcessor(
                span_exporter, max_queue_size=max_queue_size,
                schedule_delay_millis=schedule_delay_ms,
                max_export_batch_size=min(MAX_EXPORT_BATCH_SIZE, max_queue_size),
                export_timeout_millis=export_timeout_ms,
            ))
            self._logger_provider.add_log_record_processor(BatchLogRecordProcessor(
                log_exporter, max_queue_size=max_queue_size,
                schedule_delay_millis=schedule_delay_ms,
                max_export_batch_size=min(MAX_EXPORT_BATCH_SIZE, max_queue_size),
                export_timeout_millis=export_timeout_ms,
            ))
        else:
            self._tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
            self._logger_provider.add_log_record_processor(
                SimpleLogRecordProcessor(log_exporter))
        self._meter_provider = MeterProvider(resource=resource,
                                             metric_readers=list(metric_readers))

        self._tracer = self._tracer_provider.get_tracer(SCOPE, VERSION, SEMCONV_SCHEMA_URL)
        self._logger = self._logger_provider.get_logger(SCOPE, VERSION, SEMCONV_SCHEMA_URL)
        self._meter = self._meter_provider.get_meter(SCOPE, VERSION, SEMCONV_SCHEMA_URL)
        self._closed = False

    def emit_event(self, name: str, attributes: dict) -> None:
        from opentelemetry._logs import SeverityNumber

        self._logger.emit(
            timestamp=time.time_ns(),
            severity_number=SeverityNumber.INFO,
            severity_text="INFO",
            body=name,
            event_name=name,
            attributes={**attributes, "event.name": name},
        )

    @contextmanager
    def start_span(self, name: str, attributes: dict):
        with self._tracer.start_as_current_span(
            name, attributes=attributes, record_exception=False,
            set_status_on_exception=False,
        ) as span:
            handle = _OtelSpan(span)
            try:
                yield handle
            except BaseException as exc:
                try:
                    if "error.type" not in (getattr(span, "attributes", None) or {}):
                        handle.set_error(type(exc).__name__)
                except Exception:
                    pass
                raise

    def register_gauge(self, name: str, unit: str, description: str, callback) -> None:
        from opentelemetry.metrics import Observation

        def _observe(_options):
            return [Observation(value, telemetry.clean(attrs))
                    for value, attrs in callback()]

        self._meter.create_observable_gauge(
            name, callbacks=[_observe], unit=unit, description=description,
        )

    def force_flush(self, timeout_ms: int = EXPORT_TIMEOUT_MS) -> None:
        self._tracer_provider.force_flush(timeout_ms)
        self._logger_provider.force_flush(timeout_ms)
        self._meter_provider.force_flush(timeout_ms)

    def shutdown(self, timeout_s: float = SHUTDOWN_TIMEOUT_S) -> None:
        if self._closed:
            return
        self._closed = True
        timeout_s = min(max(timeout_s, 0.0), SHUTDOWN_TIMEOUT_S)
        timeout_ms = int(timeout_s * 1000)

        def _close():
            for action in (
                lambda: self._tracer_provider.force_flush(timeout_ms),
                lambda: self._logger_provider.force_flush(timeout_ms),
                self._tracer_provider.shutdown,
                self._logger_provider.shutdown,
                lambda: self._meter_provider.shutdown(timeout_millis=timeout_ms),
            ):
                try:
                    action()
                except Exception:
                    pass

        worker = threading.Thread(target=_close, name="telemetria-shutdown", daemon=True)
        worker.start()
        worker.join(timeout_s)


def _otlp_exporters(proto: str, environ):
    timeout = EXPORT_TIMEOUT_S
    if proto == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    else:
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    return (OTLPSpanExporter(timeout=timeout), OTLPLogExporter(timeout=timeout),
            OTLPMetricExporter(timeout=timeout))


def build(config: dict, environ=None) -> OtelTelemetry | None:
    env = os.environ if environ is None else environ
    if disabled(env):
        return None
    try:
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        install_warning_handler(ExportWarningHandler())
        span_exporter, log_exporter, metric_exporter = _otlp_exporters(protocol(env), env)
        reader = PeriodicExportingMetricReader(
            metric_exporter, export_interval_millis=_metric_interval_ms(env),
            export_timeout_millis=EXPORT_TIMEOUT_MS,
        )
        return OtelTelemetry(
            telemetry.resource_attributes(config, env),
            span_exporter=span_exporter, log_exporter=log_exporter,
            metric_readers=[reader],
        )
    except Exception as exc:
        log.warning(
            "Telemetria",
            f"telemetria desativada - falha ao inicializar o exportador OTLP: "
            f"{exc.__class__.__name__}",
            event="telemetria_init_falha",
        )
        return None
