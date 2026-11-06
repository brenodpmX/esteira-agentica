"""Limitador opcional de consumo de IA por plataforma (issue #311).

Política declarada em `agents.<plataforma>.limits` (chave irmã dos agentes da
plataforma). Sem o bloco, nada é verificado nem acumulado (RN-01).

- Acumulado por plataforma e período (diário/semanal/mensal) no estado local da
  instância (`.pipe/consumptionLimit.json`); cada instância tem o seu `.pipe/`,
  então o acumulado nunca é compartilhado entre instâncias (RN-04).
- Decisão ANTES do acionamento: bloqueia quando o acumulado de qualquer período
  configurado for >= ao limite (RN-02). Execução já iniciada nunca é
  interrompida; só a próxima é impedida (RN-03/RN-11).
- O limite é lido a cada avaliação, então aumentar/remover o limite retoma o
  acionamento sem reinício (RN-10).
- Falha aberta: consumo indisponível não soma nada e é registrado à parte
  (RN-06); estado corrompido é zerado com registro de recuperação, sem bloquear.
- A unidade nativa é preservada; unidades divergentes nunca são somadas (RN-05).
"""

from __future__ import annotations

import calendar
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.core.log import log

STATE_FILE = Path(".pipe/consumptionLimit.json")
STATE_VERSION = 1

LIMITS_KEY = "limits"

DAILY = "daily"
WEEKLY = "weekly"
MONTHLY = "monthly"
PERIODS = (DAILY, WEEKLY, MONTHLY)

PERIOD_LABEL = {DAILY: "diario", WEEKLY: "semanal", MONTHLY: "mensal"}

EVENT_BLOCK = "consumo_limite_bloqueio"
EVENT_UNAVAILABLE = "consumo_indisponivel"
EVENT_ACCUMULATED = "consumo_limite_acumulado"
EVENT_RESUMED = "consumo_limite_retomada"
EVENT_RECOVERY = "consumo_limite_recuperacao"
EVENT_TZ_FALLBACK = "consumo_limite_fuso_fallback"
EVENT_PERSIST_ERROR = "consumo_limite_persistencia_falha"
EVENT_UNIT_MISMATCH = "consumo_limite_unidade_divergente"

RESUME_BY_CHANGE = "aumento/desativacao do limite"


# ══════════════════════════════════════════════════════════════════════════════
# Configuração
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PeriodPolicy:
    period: str
    limit: int
    reset_weekday: int | None = None
    reset_day: int | str | None = None


@dataclass
class LimitPolicy:
    active: bool
    timezone: str | None = None
    periods: dict[str, PeriodPolicy] = field(default_factory=dict)


def _is_positive_int(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 1


def _validate_tz_name(path: str, value) -> None:
    from src.core.config import ConfigError

    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            f"{path}: deve ser um identificador de fuso (valor recebido: {value!r})"
        )
    try:
        ZoneInfo(value)
    except Exception:
        raise ConfigError(
            f"{path}: fuso inexistente (valor recebido: {value!r})"
        ) from None


def _validate_period(path: str, period: str, block) -> None:
    from src.core.config import ConfigError

    if not isinstance(block, dict):
        raise ConfigError(f"{path}: deve ser um mapa (valor recebido: {block!r})")

    required = {DAILY: ("limit",), WEEKLY: ("limit", "reset_weekday"),
                MONTHLY: ("limit", "reset_day")}[period]
    for key in block:
        if key not in required:
            raise ConfigError(
                f"{path}.{key}: campo desconhecido (permitidos: "
                f"{', '.join(repr(k) for k in required)})"
            )
    for key in required:
        if key not in block:
            raise ConfigError(
                f"{path}.{key}: campo obrigatório quando '{period}' está presente"
            )

    if not _is_positive_int(block["limit"]):
        raise ConfigError(
            f"{path}.limit: deve ser inteiro >= 1 (valor recebido: {block['limit']!r})"
        )

    if period == WEEKLY:
        wd = block["reset_weekday"]
        if isinstance(wd, bool) or not isinstance(wd, int) or not 0 <= wd <= 6:
            raise ConfigError(
                f"{path}.reset_weekday: deve ser inteiro de 0 (segunda) a 6 "
                f"(domingo) (valor recebido: {wd!r})"
            )

    if period == MONTHLY:
        rd = block["reset_day"]
        valid = rd == "last" or (
            not isinstance(rd, bool) and isinstance(rd, int) and 1 <= rd <= 28
        )
        if not valid:
            raise ConfigError(
                f"{path}.reset_day: deve ser inteiro de 1 a 28 ou 'last' "
                f"(valor recebido: {rd!r})"
            )


def validate_platform_limits(platform_id: str, block) -> None:
    from src.core.config import ConfigError

    path = f"agents.{platform_id}.{LIMITS_KEY}"
    if not isinstance(block, dict):
        raise ConfigError(
            f"{path}: deve ser um mapa com 'timezone', 'daily', 'weekly' e/ou "
            f"'monthly' (valor recebido: {block!r})"
        )
    known = ("timezone",) + PERIODS
    for key in block:
        if key not in known:
            raise ConfigError(
                f"{path}.{key}: campo desconhecido (permitidos: "
                f"{', '.join(repr(k) for k in known)})"
            )
    if "timezone" in block and block["timezone"] is not None:
        _validate_tz_name(f"{path}.timezone", block["timezone"])
    for period in PERIODS:
        if period in block:
            _validate_period(f"{path}.{period}", period, block[period])


def validate_consumption_limits(config: dict) -> None:
    agents = config.get("agents") or {}
    if not isinstance(agents, dict):
        return
    for platform_id, platform in agents.items():
        if isinstance(platform, dict) and LIMITS_KEY in platform:
            validate_platform_limits(platform_id, platform[LIMITS_KEY])


def resolve_policy(config: dict, platform_id: str) -> LimitPolicy:
    platform = ((config.get("agents") or {}).get(platform_id)) or {}
    block = platform.get(LIMITS_KEY) if isinstance(platform, dict) else None
    if not isinstance(block, dict):
        return LimitPolicy(active=False)
    periods = {}
    for period in PERIODS:
        cfg = block.get(period)
        if isinstance(cfg, dict):
            periods[period] = PeriodPolicy(
                period=period,
                limit=cfg["limit"],
                reset_weekday=cfg.get("reset_weekday"),
                reset_day=cfg.get("reset_day"),
            )
    return LimitPolicy(active=bool(periods), timezone=block.get("timezone"),
                       periods=periods)


_disk_cache: dict = {}


def _load_disk_config(pipe_file: Path):
    import yaml

    stamp = pipe_file.stat().st_mtime_ns
    if _disk_cache.get("stamp") != stamp:
        _disk_cache.clear()
        _disk_cache.update(stamp=stamp, data=None, invalid={})
        with open(pipe_file, encoding="utf-8") as f:
            _disk_cache["data"] = yaml.safe_load(f) or {}
    return _disk_cache["data"], _disk_cache["invalid"]


def read_policy_from_disk(config: dict, platform_id: str) -> LimitPolicy:
    """Relê `agents.<plataforma>.limits` do `pipe.yml` em disco a cada avaliação.

    Permite aumentar/remover o limite sem reiniciar o processo (RN-10). Se o
    arquivo não existe ou não pode ser lido, usa a config em memória. Bloco
    inválido no disco também mantém a config em memória, com aviso.
    """
    import yaml
    from src.core.config import PIPE_FILE, ConfigError

    if not PIPE_FILE.exists():
        return resolve_policy(config, platform_id)
    try:
        data, invalid = _load_disk_config(PIPE_FILE)
    except (OSError, yaml.YAMLError) as exc:
        return _fallback_policy(config, platform_id, exc)
    if data is None or platform_id in invalid:
        return resolve_policy(config, platform_id)
    try:
        if not isinstance(data, dict):
            raise ConfigError("pipe.yml não é um mapa")
        platform = ((data.get("agents") or {}).get(platform_id)) or {}
        if isinstance(platform, dict) and LIMITS_KEY in platform:
            validate_platform_limits(platform_id, platform[LIMITS_KEY])
        return resolve_policy(data, platform_id)
    except (AttributeError, ConfigError) as exc:
        invalid[platform_id] = True
        return _fallback_policy(config, platform_id, exc)


def _fallback_policy(config: dict, platform_id: str, exc: Exception) -> LimitPolicy:
    from src.core.config import PIPE_FILE

    log.warning(
        "ConsumoLimite",
        f"[{platform_id}] limites em {PIPE_FILE} ilegíveis ou inválidos — "
        f"mantida a configuração carregada no início: {exc}",
        event="consumo_limite_config_runtime_invalida", plataforma=platform_id,
    )
    return resolve_policy(config, platform_id)


# ══════════════════════════════════════════════════════════════════════════════
# Identidade da instância
# ══════════════════════════════════════════════════════════════════════════════

_URL_USERINFO = re.compile(r"(?<=://)[^/@\s]+@")


def instance_id(config: dict, repo_id: str | None = None) -> str:
    """Identificador estável da instância: URL do repositório de trabalho.

    Credenciais embutidas na URL (`https://user:token@host/...`) são removidas
    (RNF-06).
    """
    repos = ((config.get("git") or {}).get("repo")) or {}
    if not isinstance(repos, dict) or not repos:
        return repo_id or "desconhecida"
    key = repo_id if repo_id in repos else next(iter(repos))
    return _URL_USERINFO.sub("", str(repos[key]))


# ══════════════════════════════════════════════════════════════════════════════
# Calendário de reset
# ══════════════════════════════════════════════════════════════════════════════

def resolve_tz(name: str | None, platform_id: str = ""):
    """ZoneInfo do fuso configurado; None = fuso local da máquina.

    Falha ao carregar o fuso em runtime cai para o fuso local, com registro.
    """
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except Exception as exc:
        log.warning(
            "ConsumoLimite",
            f"[{platform_id}] fuso '{name}' indisponível em runtime — usando o "
            f"fuso local da máquina: {exc.__class__.__name__}",
            event=EVENT_TZ_FALLBACK, plataforma=platform_id, fuso=name,
        )
        return None


def _now_in(ts: float, tz) -> datetime:
    if tz is None:
        return datetime.fromtimestamp(ts).astimezone()
    return datetime.fromtimestamp(ts, tz)


def _midnight(d: date, tz) -> datetime:
    if tz is None:
        return datetime(d.year, d.month, d.day).astimezone()
    return datetime(d.year, d.month, d.day, tzinfo=tz)


def _month_reset_date(year: int, month: int, reset_day) -> date:
    last = calendar.monthrange(year, month)[1]
    day = last if reset_day == "last" else min(int(reset_day), last)
    return date(year, month, day)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def period_bounds(policy: PeriodPolicy, now: datetime, tz) -> tuple[datetime, datetime]:
    """(início do período corrente, próximo reset) no fuso informado."""
    today = now.date()
    if policy.period == DAILY:
        start = today
        nxt = today + timedelta(days=1)
    elif policy.period == WEEKLY:
        start = today - timedelta(days=(today.weekday() - policy.reset_weekday) % 7)
        nxt = start + timedelta(days=7)
    else:
        this_month = _month_reset_date(today.year, today.month, policy.reset_day)
        if today >= this_month:
            start = this_month
        else:
            y, m = _shift_month(today.year, today.month, -1)
            start = _month_reset_date(y, m, policy.reset_day)
        y, m = _shift_month(start.year, start.month, 1)
        nxt = _month_reset_date(y, m, policy.reset_day)
    return _midnight(start, tz), _midnight(nxt, tz)


# ══════════════════════════════════════════════════════════════════════════════
# Persistência
# ══════════════════════════════════════════════════════════════════════════════

class ConsumptionStateError(Exception):
    pass


def _empty_state() -> dict:
    return {"version": STATE_VERSION, "platforms": {}}


def load_state() -> dict:
    """Carrega o estado; ausente/corrompido vira estado vazio com registro
    de recuperação (falha aberta — nunca bloqueia por falta de dado)."""
    if not STATE_FILE.exists():
        return _empty_state()
    motivo = None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != STATE_VERSION \
                or not isinstance(data.get("platforms"), dict):
            motivo = "corrompido: formato ou versão inválidos"
    except (OSError, ValueError) as exc:
        motivo = f"corrompido: {exc.__class__.__name__}"
    if motivo is None:
        return data
    log.warning(
        "ConsumoLimite",
        f"estado do acumulado de consumo {motivo} — zerado com segurança",
        event=EVENT_RECOVERY, motivo=motivo,
    )
    return _empty_state()


def save_state(data: dict) -> None:
    directory = STATE_FILE.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=directory, prefix=".consumptionLimit-", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, STATE_FILE)
        except OSError:
            tmp_path.unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise ConsumptionStateError(
            f"falha ao persistir o acumulado de consumo em {STATE_FILE.name}: "
            f"{exc.__class__.__name__}"
        ) from exc


def ensure_state_initialized(policy: LimitPolicy) -> None:
    """Na primeira avaliação com política ativa, materializa o estado vazio e
    registra a recuperação por ausência (estado nunca criado ou removido)."""
    if not policy.active or STATE_FILE.exists():
        return
    log.warning(
        "ConsumoLimite",
        "estado do acumulado de consumo ausente — iniciado zerado",
        event=EVENT_RECOVERY, motivo="ausente",
    )
    try:
        save_state(_empty_state())
    except ConsumptionStateError as exc:
        log.error("ConsumoLimite", str(exc), event=EVENT_PERSIST_ERROR)


def _period_entry(plat: dict, period: str, start: datetime) -> dict:
    periods = plat.setdefault("periods", {})
    entry = periods.get(period)
    if not isinstance(entry, dict) or entry.get("inicio") != start.isoformat():
        entry = {"inicio": start.isoformat(), "consumo": 0}
        periods[period] = entry
    return entry


# ══════════════════════════════════════════════════════════════════════════════
# Núcleo: admissão e acumulação
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Decision:
    admitted: bool
    period: str | None = None
    record: dict | None = None


def _iso_now(ts: float, tz) -> str:
    return _now_in(ts, tz).isoformat()


class ConsumptionLimiter:
    """Avalia/acumula consumo de uma plataforma na instância corrente.

    `clock` injetável (epoch seconds) para testes de calendário.
    """

    def __init__(self, instance: str, clock=time.time):
        self._instance = instance
        self._clock = clock

    def admit(self, platform_id: str, policy: LimitPolicy, **context) -> Decision:
        if not policy.active:
            return Decision(admitted=True)

        ensure_state_initialized(policy)
        ts = self._clock()
        tz = resolve_tz(policy.timezone, platform_id)
        now = _now_in(ts, tz)
        data = load_state()
        plat = data["platforms"].setdefault(platform_id, {})

        hits = []
        for period, pp in policy.periods.items():
            start, nxt = period_bounds(pp, now, tz)
            entry = _period_entry(plat, period, start)
            if entry["consumo"] >= pp.limit:
                hits.append((nxt, period, pp, entry))

        if not hits:
            self._log_resumed(data, plat, platform_id, ts, tz)
            return Decision(admitted=True)

        nxt, period, pp, entry = max(hits, key=lambda h: h[0])
        tz_label = policy.timezone if tz is not None else (now.tzname() or "local")
        record = {
            "event": EVENT_BLOCK,
            "instancia": self._instance,
            "plataforma": platform_id,
            "unidade": plat.get("unidade") or "desconhecida",
            "consumo_periodo": entry["consumo"],
            "limite": pp.limit,
            "periodo": PERIOD_LABEL[period],
            "condicao_retomada": (
                f"reinicio em {nxt.strftime('%Y-%m-%d %H:%M')} {tz_label} "
                f"ou {RESUME_BY_CHANGE}"
            ),
            "timestamp": _iso_now(ts, tz),
            **{k: str(v) for k, v in context.items() if v is not None},
        }
        log.warning(
            "ConsumoLimite",
            f"[{platform_id}] acionamento impedido — consumo {PERIOD_LABEL[period]} "
            f"{entry['consumo']} {record['unidade']} >= limite {pp.limit}; "
            f"retomada: {record['condicao_retomada']}",
            **record,
        )
        if not plat.get("bloqueado_desde"):
            plat["bloqueado_desde"] = ts
        self._save(data, platform_id)
        return Decision(admitted=False, period=period, record=record)

    def record(self, platform_id: str, policy: LimitPolicy, consumo, motivo: str = "",
               **context) -> None:
        """Acumula o consumo de uma execução concluída (nunca interrompe nada)."""
        if not policy.active:
            return
        ts = self._clock()
        tz = resolve_tz(policy.timezone, platform_id)

        if consumo is None or not getattr(consumo, "disponivel", False):
            log.warning(
                "ConsumoLimite",
                f"[{platform_id}] consumo indisponível — execução não contabilizada "
                f"(falha aberta): {motivo or 'plataforma não reportou consumo'}",
                event=EVENT_UNAVAILABLE,
                instancia=self._instance,
                plataforma=platform_id,
                motivo=motivo or "plataforma não reportou consumo",
                timestamp=_iso_now(ts, tz),
                **{k: str(v) for k, v in context.items() if v is not None},
            )
            return

        now = _now_in(ts, tz)
        data = load_state()
        plat = data["platforms"].setdefault(platform_id, {})
        unidade = consumo.unidade
        known_unit = plat.get("unidade")
        if known_unit and unidade != known_unit:
            log.error(
                "ConsumoLimite",
                f"[{platform_id}] unidade divergente ({unidade!r} ≠ {known_unit!r}) "
                f"— valor {consumo.valor} não somado ao acumulado",
                event=EVENT_UNIT_MISMATCH, instancia=self._instance,
                plataforma=platform_id, unidade=unidade, unidade_acumulada=known_unit,
                valor=consumo.valor, timestamp=_iso_now(ts, tz),
            )
            return
        plat["unidade"] = unidade

        periodos = {}
        for period, pp in policy.periods.items():
            start, _ = period_bounds(pp, now, tz)
            entry = _period_entry(plat, period, start)
            entry["consumo"] = entry["consumo"] + consumo.valor
            periodos[PERIOD_LABEL[period]] = {
                "consumo_periodo": entry["consumo"],
                "limite": pp.limit,
                "excedente": max(0, entry["consumo"] - pp.limit),
            }

        log.trace(
            "ConsumoLimite",
            f"[{platform_id}] consumo de {consumo.valor} {unidade} acumulado",
            event=EVENT_ACCUMULATED, instancia=self._instance, plataforma=platform_id,
            unidade=unidade, valor=consumo.valor, periodos=periodos,
            timestamp=_iso_now(ts, tz),
            **{k: str(v) for k, v in context.items() if v is not None},
        )
        self._save(data, platform_id, valor=consumo.valor, unidade=unidade)

    def _log_resumed(self, data: dict, plat: dict, platform_id: str, ts: float, tz):
        since = plat.get("bloqueado_desde")
        if not since:
            return
        plat["bloqueado_desde"] = None
        log.info(
            "ConsumoLimite",
            f"[{platform_id}] acionamento retomado após {int(ts - since)}s bloqueado",
            event=EVENT_RESUMED, instancia=self._instance, plataforma=platform_id,
            tempo_bloqueado_seg=ts - since, timestamp=_iso_now(ts, tz),
        )
        self._save(data, platform_id)

    def _save(self, data: dict, platform_id: str, **extra) -> None:
        try:
            save_state(data)
        except ConsumptionStateError as exc:
            log.error(
                "ConsumoLimite",
                f"[{platform_id}] {exc}",
                event=EVENT_PERSIST_ERROR, instancia=self._instance,
                plataforma=platform_id, **extra,
            )
