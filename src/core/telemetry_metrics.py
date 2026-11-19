from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.core import telemetry

SYNC_EVENTS = ("create-up", "create-down", "change-up", "change-down",
               "delete-up", "delete-down")
DEAD_LETTER_CATEGORIES = ("definitivo", "definitivo_cli", "transitorio_esgotado",
                          "corrigivel_pelo_agente")
BREAKER_VALUE = {"closed": 0, "half_open": 1, "open": 2}

METRICAS = (
    "esteira.board.throttle",
    "esteira.board.penalty",
    "esteira.sync.circuit_breaker.estado",
    "esteira.sync.circuit_breaker.issues_abertas",
    "esteira.consumo.acumulado",
    "esteira.consumo.limite",
    "esteira.consumo.bloqueado",
    "esteira.sync.fila.profundidade",
    "esteira.sync.fila.idade_maxima",
    "esteira.sync.dead_letter.total",
    "esteira.sync.orfaos.total",
)


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _board_ids(config: dict) -> list[str]:
    boards = (config or {}).get("boards") or {}
    return [bid for bid, cfg in boards.items() if bid != "platform" and isinstance(cfg, dict)]


def _parse_ts(value) -> float | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


class MetricReaders:
    def __init__(self, config: dict, board_port=None, clock=time.time):
        self._config = config or {}
        self._board_port = board_port
        self._clock = clock

    def _platform(self) -> str:
        from src.core.sync_circuit_breaker import platform_of

        return platform_of(self._config)

    def _plat_attr(self) -> dict:
        return {"esteira.board.plataforma": self._platform()}

    def _rate_state(self) -> dict:
        port = self._board_port
        state = port.rate_state() if port is not None and hasattr(port, "rate_state") else None
        return state or {}

    def throttle(self):
        state = self._rate_state()
        if "throttle_s" not in state:
            return []
        return [(state["throttle_s"], self._plat_attr())]

    def penalty(self):
        state = self._rate_state()
        if "penalty_h" not in state:
            return []
        return [(state["penalty_h"], self._plat_attr())]

    def _breaker_state(self) -> dict:
        from src.core import sync_circuit_breaker as scb

        cfg = scb.resolve_config(self._config)
        if cfg.persistence == scb.PERSISTENCE_MEMORY:
            state = scb._memory_state
        else:
            state = _read_json(scb.STATE_FILE)
        return state if isinstance(state, dict) else {}

    def breaker_estado(self):
        platform = self._platform()
        entry = (self._breaker_state().get("platforms") or {}).get(platform) or {}
        value = BREAKER_VALUE.get(entry.get("state") or "closed", 0)
        return [(value, self._plat_attr())]

    def breaker_issues_abertas(self):
        issues = self._breaker_state().get("issues") or {}
        count = sum(1 for e in issues.values()
                    if isinstance(e, dict) and (e.get("state") or "closed") != "closed")
        return [(count, self._plat_attr())]

    def _consumo(self):
        from src.core import consumption_limit as cl

        state = _read_json(cl.STATE_FILE)
        platforms_state = (state or {}).get("platforms") if isinstance(state, dict) else None
        platforms_state = platforms_state if isinstance(platforms_state, dict) else {}
        agents = self._config.get("agents") or {}
        rows = []
        for platform_id in agents:
            policy = cl.resolve_policy(self._config, platform_id)
            if not policy.active:
                continue
            plat = platforms_state.get(platform_id) or {}
            rows.append((platform_id, policy, plat))
        return rows

    def _period_rows(self):
        from zoneinfo import ZoneInfo

        from src.core import consumption_limit as cl

        ts = self._clock()
        out = []
        for platform_id, policy, plat in self._consumo():
            try:
                tz = ZoneInfo(policy.timezone) if policy.timezone else None
            except Exception:
                tz = None
            now = cl._now_in(ts, tz)
            unidade = plat.get("unidade") or "desconhecida"
            for period, pp in policy.periods.items():
                start, _ = cl.period_bounds(pp, now, tz)
                entry = (plat.get("periods") or {}).get(period) or {}
                acumulado = entry.get("consumo", 0) if entry.get("inicio") == start.isoformat() else 0
                attrs = {
                    "esteira.ia.plataforma": platform_id,
                    "esteira.consumo.periodo": cl.PERIOD_LABEL[period],
                    "esteira.consumo.unidade": unidade,
                }
                out.append((acumulado, pp.limit, attrs))
        return out

    def consumo_acumulado(self):
        return [(acumulado, attrs) for acumulado, _, attrs in self._period_rows()]

    def consumo_limite(self):
        return [(limite, attrs) for _, limite, attrs in self._period_rows()]

    def consumo_bloqueado(self):
        return [(1 if plat.get("bloqueado_desde") else 0, {"esteira.ia.plataforma": platform_id})
                for platform_id, _, plat in self._consumo()]

    def _queue_items(self) -> list[dict]:
        from src.core.change_queue import QUEUE_FILE

        raw = _read_json(QUEUE_FILE)
        return [i for i in raw if isinstance(i, dict)] if isinstance(raw, list) else []

    def fila_profundidade(self):
        counts = Counter((i.get("board"), i.get("event")) for i in self._queue_items())
        boards = set(_board_ids(self._config)) | {b for b, _ in counts}
        out = []
        for board in sorted(b for b in boards if b):
            for event in SYNC_EVENTS:
                out.append((counts.get((board, event), 0),
                            {"esteira.board": board, "esteira.sync.evento": event}))
        return out

    def fila_idade_maxima(self):
        now = self._clock()
        oldest: dict[str, float] = {}
        for item in self._queue_items():
            ts = _parse_ts(item.get("timestamp"))
            board = item.get("board")
            if ts is None or not board:
                continue
            oldest[board] = min(ts, oldest.get(board, ts))
        boards = set(_board_ids(self._config)) | set(oldest)
        return [(max(0.0, now - oldest[b]) if b in oldest else 0.0, {"esteira.board": b})
                for b in sorted(boards)]

    def dead_letter_total(self):
        from src.core.dead_letter import DEAD_LETTER_FILE

        raw = _read_json(DEAD_LETTER_FILE)
        entries = [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []
        counts = Counter(e.get("category") for e in entries if e.get("category"))
        categories = list(DEAD_LETTER_CATEGORIES) + sorted(
            c for c in counts if c not in DEAD_LETTER_CATEGORIES)
        return [(counts.get(c, 0), {"esteira.sync.dead_letter.categoria": c})
                for c in categories]

    def orfaos_total(self):
        from src.core.sync import ORPHAN_FILE

        raw = _read_json(ORPHAN_FILE)
        entries = [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []
        counts = Counter(e.get("board") for e in entries if e.get("board"))
        boards = set(_board_ids(self._config)) | set(counts)
        return [(counts.get(b, 0), {"esteira.board": b}) for b in sorted(boards)]

    def specs(self):
        return (
            ("esteira.board.throttle", "s", "segundos de espera atuais entre chamadas ao board", self.throttle),
            ("esteira.board.penalty", "h", "horas do penalty ativo; 0 inativo", self.penalty),
            ("esteira.sync.circuit_breaker.estado", "1", "0 closed, 1 half_open, 2 open (escopo plataforma)", self.breaker_estado),
            ("esteira.sync.circuit_breaker.issues_abertas", "{issue}", "issues com breaker diferente de closed", self.breaker_issues_abertas),
            ("esteira.consumo.acumulado", "{consumo}", "acumulado do período corrente na unidade nativa", self.consumo_acumulado),
            ("esteira.consumo.limite", "{consumo}", "limite configurado na unidade nativa", self.consumo_limite),
            ("esteira.consumo.bloqueado", "1", "1 bloqueado pelo limite de consumo", self.consumo_bloqueado),
            ("esteira.sync.fila.profundidade", "{item}", "itens na fila de sincronismo", self.fila_profundidade),
            ("esteira.sync.fila.idade_maxima", "s", "idade do item mais antigo da fila", self.fila_idade_maxima),
            ("esteira.sync.dead_letter.total", "{item}", "entradas no dead-letter", self.dead_letter_total),
            ("esteira.sync.orfaos.total", "{arquivo}", "arquivos órfãos registrados", self.orfaos_total),
        )


def register(config: dict, board_port=None, clock=time.time) -> MetricReaders:
    readers = MetricReaders(config, board_port, clock)
    if telemetry.enabled():
        for name, unit, description, callback in readers.specs():
            telemetry.register_gauge(name, unit, description, callback)
    return readers
