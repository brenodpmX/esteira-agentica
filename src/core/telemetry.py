from __future__ import annotations

import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

SERVICE_NAME = "esteira-agentica"
CONTRATO = "1"

TITULO_ENV = "ESTEIRA_TELEMETRIA_TITULO"
ENVIRONMENT_ENV = "PIPE_ENVIRONMENT"
RESOURCE_ATTRIBUTES_ENV = "OTEL_RESOURCE_ATTRIBUTES"
ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"

INSTANCE_ATTR = "service.instance.id"
PIPE_NOME_ATTR = "esteira.pipe.nome"
ENVIRONMENT_ATTR = "deployment.environment.name"

EV_EXECUCAO = "esteira.agente.execucao"
EV_ADMISSAO_NEGADA = "esteira.agente.admissao_negada"
EV_CIRCUIT_BREAK = "esteira.agente.circuit_break"
EV_CONSUMO_LIMITE = "esteira.consumo.limite"
EV_SYNC_ITEM = "esteira.sync.item"
EV_BOARD_API = "esteira.board.api"
EV_BOARD_THROTTLE = "esteira.board.throttle"
EV_BOARD_PENALTY = "esteira.board.penalty"
EV_SYNC_BREAKER = "esteira.sync.circuit_breaker"
EV_SYNC_ESCALACAO = "esteira.sync.escalacao"
EV_ISSUE_UPSERT = "esteira.issue.upsert"
EV_ISSUE_TRANSICAO = "esteira.issue.transicao"
EV_PIPE_CICLO = "esteira.pipe.ciclo"
EV_PIPE_CICLO_VIDA = "esteira.pipe.ciclo_vida"
EV_PIPE_INCIDENTE = "esteira.pipe.incidente"

EVENTOS = (
    EV_EXECUCAO, EV_ADMISSAO_NEGADA, EV_CIRCUIT_BREAK, EV_CONSUMO_LIMITE,
    EV_SYNC_ITEM, EV_BOARD_API, EV_BOARD_THROTTLE, EV_BOARD_PENALTY,
    EV_SYNC_BREAKER, EV_SYNC_ESCALACAO, EV_ISSUE_UPSERT, EV_ISSUE_TRANSICAO,
    EV_PIPE_CICLO, EV_PIPE_CICLO_VIDA, EV_PIPE_INCIDENTE,
)

INCIDENTES = (
    "instance_lock_recusado", "preflight_falha", "steering_reescrito",
    "snapshot_restaurado", "arquivo_fantasma", "cross_board_bloqueado",
    "registro_execucao_falha",
)


class TelemetrySpan:
    def set_attributes(self, attributes: dict) -> None:
        return None

    def set_error(self, error_type: str) -> None:
        return None


class TelemetryPort(ABC):
    enabled: bool = False

    @abstractmethod
    def emit_event(self, name: str, attributes: dict) -> None:
        pass

    @abstractmethod
    def start_span(self, name: str, attributes: dict):
        pass

    @abstractmethod
    def register_gauge(self, name: str, unit: str, description: str, callback) -> None:
        pass

    @abstractmethod
    def shutdown(self, timeout_s: float = 2.0) -> None:
        pass


_NOOP_SPAN = TelemetrySpan()


class NoopTelemetry(TelemetryPort):
    enabled = False

    def emit_event(self, name: str, attributes: dict) -> None:
        return None

    @contextmanager
    def start_span(self, name: str, attributes: dict):
        yield _NOOP_SPAN

    def register_gauge(self, name: str, unit: str, description: str, callback) -> None:
        return None

    def shutdown(self, timeout_s: float = 2.0) -> None:
        return None


_port: TelemetryPort = NoopTelemetry()
_board_platform: str | None = None


def configure(port: TelemetryPort | None, board_platform: str | None = None) -> None:
    global _port, _board_platform
    _port = port or NoopTelemetry()
    _board_platform = board_platform


def current() -> TelemetryPort:
    return _port


def enabled() -> bool:
    return bool(getattr(_port, "enabled", False))


def board_platform() -> str | None:
    return _board_platform


def clean(attributes: dict | None) -> dict:
    out = {}
    for key, value in (attributes or {}).items():
        if value is None:
            continue
        if isinstance(value, (bool, int, float, str)):
            out[key] = value
        elif isinstance(value, (list, tuple, set, frozenset)):
            items = sorted(value, key=str) if isinstance(value, (set, frozenset)) else value
            out[key] = [str(v) for v in items if v is not None]
        else:
            out[key] = str(value)
    return out


def emit(name: str, attributes: dict | None = None) -> None:
    if not enabled():
        return
    try:
        _port.emit_event(name, clean(attributes))
    except Exception:
        return


class _SafeSpan(TelemetrySpan):
    def __init__(self, inner):
        self._inner = inner

    def set_attributes(self, attributes: dict) -> None:
        try:
            self._inner.set_attributes(clean(attributes))
        except Exception:
            return

    def set_error(self, error_type: str) -> None:
        try:
            self._inner.set_error(error_type)
        except Exception:
            return


@contextmanager
def span(name: str, attributes: dict | None = None):
    if not enabled():
        yield _NOOP_SPAN
        return
    cm = None
    handle = _NOOP_SPAN
    try:
        cm = _port.start_span(name, clean(attributes))
        handle = _SafeSpan(cm.__enter__())
    except Exception:
        cm = None
        handle = _NOOP_SPAN
    try:
        yield handle
    except BaseException as exc:
        if cm is not None:
            try:
                cm.__exit__(type(exc), exc, exc.__traceback__)
            except Exception:
                pass
        raise
    else:
        if cm is not None:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass


def register_gauge(name: str, unit: str, description: str, callback) -> None:
    if not enabled():
        return

    def _safe():
        try:
            return list(callback() or [])
        except Exception:
            return []

    try:
        _port.register_gauge(name, unit, description, _safe)
    except Exception:
        return


def shutdown(timeout_s: float = 2.0) -> None:
    try:
        _port.shutdown(timeout_s)
    except Exception:
        return


def titulo_habilitado() -> bool:
    return os.environ.get(TITULO_ENV, "").strip().lower() == "true"


def _titulo(body_path) -> str | None:
    if not body_path:
        return None
    try:
        path = Path(body_path)
        if not path.exists():
            return None
        first = path.read_text(encoding="utf-8").split("\n", 1)[0]
        return first.lstrip("# ").strip() or None
    except OSError:
        return None


def contexto(board=None, coluna=None, issue=None, pai=None, body_path=None,
             titulo: str | None = None) -> dict:
    attrs = {
        "esteira.board.plataforma": _board_platform,
        "esteira.board": board,
        "esteira.coluna": coluna,
        "esteira.issue": str(issue) if issue is not None else None,
        "esteira.issue.pai": str(pai) if pai not in (None, "") else None,
    }
    if titulo_habilitado():
        attrs["esteira.issue.titulo"] = titulo or _titulo(body_path)
    return attrs


def sanitize_url(value: str) -> str:
    from src.core.consumption_limit import _URL_USERINFO

    return _URL_USERINFO.sub("", str(value))


def sanitize_message(message) -> str:
    from src.core.dead_letter import sanitize_reason

    return sanitize_url(sanitize_reason(str(message)))


def endpoint_for_log(environ=None) -> str | None:
    env = os.environ if environ is None else environ
    raw = (env.get(ENDPOINT_ENV) or "").strip()
    if not raw:
        return None
    try:
        parts = urlsplit(raw)
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        return urlunsplit((parts.scheme, host, parts.path, "", ""))
    except ValueError:
        return sanitize_url(raw.split("?", 1)[0])


def parse_resource_attributes(raw: str | None) -> dict:
    out = {}
    for pair in (raw or "").split(","):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        key = unquote(key.strip())
        if key:
            out[key] = unquote(value.strip())
    return out


def repo_name(config: dict) -> str:
    repos = ((config or {}).get("git") or {}).get("repo") or {}
    if not isinstance(repos, dict) or not repos:
        return "desconhecida"
    key = next(iter(repos))
    url = str(repos[key]).rstrip("/")
    tail = url.rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    return tail or str(key)


def resource_attributes(config: dict, environ=None) -> dict:
    from src.core.consumption_limit import instance_id
    from src.core.version import VERSION

    env = os.environ if environ is None else environ
    from_env = parse_resource_attributes(env.get(RESOURCE_ATTRIBUTES_ENV))
    attrs = dict(from_env)
    attrs["service.name"] = SERVICE_NAME
    attrs["service.version"] = VERSION
    attrs["esteira.contrato"] = CONTRATO
    attrs[INSTANCE_ATTR] = sanitize_url(from_env.get(INSTANCE_ATTR) or instance_id(config or {}))
    attrs[PIPE_NOME_ATTR] = from_env.get(PIPE_NOME_ATTR) or repo_name(config)
    environment = (env.get(ENVIRONMENT_ENV) or "").strip()
    if environment:
        attrs[ENVIRONMENT_ATTR] = environment
    else:
        attrs.pop(ENVIRONMENT_ATTR, None)
    return attrs


def incidente(tipo: str, board=None, issue=None) -> None:
    if not enabled():
        return
    emit(EV_PIPE_INCIDENTE, {
        "esteira.incidente.tipo": tipo,
        **contexto(board=board, issue=issue),
    })
