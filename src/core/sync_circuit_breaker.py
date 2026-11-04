from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from src.core.log import log

STATE_FILE = Path(".pipe/syncCircuitBreaker.json")

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"

PERSISTENCE_FILE = "file"
PERSISTENCE_MEMORY = "memory"

DEFAULT_PERSISTENCE = PERSISTENCE_FILE
DEFAULT_ESCALATION_AGENT = "correcao-esteira"

_ISSUE_DEFAULTS = {"max_failures": 3, "block_duration": 300, "max_blocks": 3}
_PLATFORM_DEFAULTS = {"max_blocked_issues": 5, "block_window": 600, "block_duration": 900}
_HALF_OPEN_DEFAULTS = {"success_threshold": 2}

_SECTIONS = {
    "issue": _ISSUE_DEFAULTS,
    "platform": _PLATFORM_DEFAULTS,
    "half_open": _HALF_OPEN_DEFAULTS,
}

_memory_state: dict = {}


@dataclass(frozen=True)
class SyncCircuitBreakerConfig:
    persistence: str = DEFAULT_PERSISTENCE
    escalation_agent: str = DEFAULT_ESCALATION_AGENT
    issue_max_failures: int = 3
    issue_block_duration: int = 300
    issue_max_blocks: int = 3
    platform_max_blocked_issues: int = 5
    platform_block_window: int = 600
    platform_block_duration: int = 900
    half_open_success_threshold: int = 2


@dataclass
class SyncEscalation:
    board_id: str
    issue_id: str
    error_log: str
    blocks: int
    agent_id: str


class SyncCircuitBreakerFatal(Exception):
    def __init__(self, board_id: str, issue_id: str, error: str,
                 attempts: int, agent_id: str):
        self.board_id = board_id
        self.issue_id = issue_id
        self.error = error
        self.attempts = attempts
        self.agent_id = agent_id
        super().__init__(
            f"[{board_id}] #{issue_id} sync falhou após a correção do agente "
            f"'{agent_id}' ({attempts} tentativas): {error}"
        )


def _positive_int(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 1


def validate_sync_circuit_breaker(config: dict) -> None:
    from src.core.config import ConfigError

    sync_cfg = config.get("sync")
    if not isinstance(sync_cfg, dict) or "circuit_breaker" not in sync_cfg:
        return
    block = sync_cfg["circuit_breaker"]
    root = "sync.circuit_breaker"
    if not isinstance(block, dict):
        raise ConfigError(f"{root}: deve ser um mapa (valor recebido: {block!r})")

    known = {"persistence", "escalation_agent", *_SECTIONS}
    for key in block:
        if key not in known:
            raise ConfigError(f"{root}.{key}: campo desconhecido")

    if "persistence" in block and block["persistence"] not in (
            PERSISTENCE_FILE, PERSISTENCE_MEMORY):
        raise ConfigError(
            f"{root}.persistence: deve ser 'file' ou 'memory' "
            f"(valor recebido: {block['persistence']!r})"
        )

    if "escalation_agent" in block:
        agent = block["escalation_agent"]
        if not isinstance(agent, str) or not agent.strip():
            raise ConfigError(
                f"{root}.escalation_agent: deve ser string não-vazia "
                f"(valor recebido: {agent!r})"
            )

    for section, defaults in _SECTIONS.items():
        if section not in block:
            continue
        values = block[section]
        if not isinstance(values, dict):
            raise ConfigError(
                f"{root}.{section}: deve ser um mapa (valor recebido: {values!r})"
            )
        for key, value in values.items():
            if key not in defaults:
                raise ConfigError(f"{root}.{section}.{key}: campo desconhecido")
            if not _positive_int(value):
                raise ConfigError(
                    f"{root}.{section}.{key}: deve ser inteiro >= 1 "
                    f"(valor recebido: {value!r})"
                )


def resolve_config(config: dict) -> SyncCircuitBreakerConfig:
    sync_cfg = (config or {}).get("sync") or {}
    block = sync_cfg.get("circuit_breaker") or {}

    def pick(section: str, key: str) -> int:
        return (block.get(section) or {}).get(key, _SECTIONS[section][key])

    return SyncCircuitBreakerConfig(
        persistence=block.get("persistence", DEFAULT_PERSISTENCE),
        escalation_agent=block.get("escalation_agent", DEFAULT_ESCALATION_AGENT),
        issue_max_failures=pick("issue", "max_failures"),
        issue_block_duration=pick("issue", "block_duration"),
        issue_max_blocks=pick("issue", "max_blocks"),
        platform_max_blocked_issues=pick("platform", "max_blocked_issues"),
        platform_block_window=pick("platform", "block_window"),
        platform_block_duration=pick("platform", "block_duration"),
        half_open_success_threshold=pick("half_open", "success_threshold"),
    )


def reset_memory_state() -> None:
    _memory_state.clear()


def platform_of(config: dict, board_id: str | None = None) -> str:
    boards = (config or {}).get("boards") or {}
    return str(boards.get("platform") or "default")


def _key(board_id: str, issue_id) -> str:
    return f"{board_id}/{issue_id}"


def _new_issue_entry() -> dict:
    return {
        "state": CLOSED,
        "failures": 0,
        "blocks": 0,
        "attempts": 0,
        "blocked_until": 0.0,
        "half_open_successes": 0,
        "escalated": False,
        "agent": None,
    }


def _new_platform_entry() -> dict:
    return {
        "state": CLOSED,
        "blocked_until": 0.0,
        "half_open_successes": 0,
        "blocked": {},
    }


class SyncCircuitBreaker:
    def __init__(self, config: dict | None = None, clock=None):
        self._config = config or {}
        self._cfg = resolve_config(self._config)
        self._clock = clock or (lambda: time.time())

    @property
    def settings(self) -> SyncCircuitBreakerConfig:
        return self._cfg

    def platform_of(self, board_id: str | None = None) -> str:
        return platform_of(self._config, board_id)

    def _load(self) -> dict:
        if self._cfg.persistence == PERSISTENCE_MEMORY:
            state = _memory_state
        elif STATE_FILE.exists():
            try:
                state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                log.error("SyncCircuitBreaker",
                          f"estado ilegível - reiniciando contadores: {exc}",
                          event="sync_circuit_breaker_state_reset")
                state = {}
        else:
            state = {}
        state.setdefault("issues", {})
        state.setdefault("platforms", {})
        return state

    def _save(self, state: dict) -> None:
        if self._cfg.persistence == PERSISTENCE_MEMORY:
            return
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(STATE_FILE.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(state, fh, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, STATE_FILE)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def platform_blocked(self, platform: str) -> bool:
        state = self._load()
        entry = state["platforms"].get(platform)
        if not entry or entry["state"] != OPEN:
            return False
        if self._clock() < entry["blocked_until"]:
            return True
        entry["state"] = HALF_OPEN
        entry["half_open_successes"] = 0
        entry["blocked"] = {}
        self._save(state)
        log.info("SyncCircuitBreaker", f"plataforma {platform} meio-aberta",
                 event="sync_circuit_breaker_transition", plataforma=platform,
                 estado_anterior=OPEN, estado_novo=HALF_OPEN)
        return False

    def issue_blocked(self, board_id: str, issue_id) -> bool:
        state = self._load()
        key = _key(board_id, issue_id)
        entry = state["issues"].get(key)
        if not entry or entry["state"] != OPEN:
            return False
        if self._clock() < entry["blocked_until"]:
            return True
        entry["state"] = HALF_OPEN
        entry["half_open_successes"] = 0
        self._save(state)
        log.info("SyncCircuitBreaker", f"[{board_id}] #{issue_id} meio-aberto",
                 event="sync_circuit_breaker_transition", board=board_id,
                 issue=str(issue_id), estado_anterior=OPEN, estado_novo=HALF_OPEN)
        return False

    def record_success(self, board_id: str, issue_id, platform: str | None = None) -> None:
        platform = platform or self.platform_of(board_id)
        state = self._load()
        key = _key(board_id, issue_id)
        dirty = False

        entry = state["issues"].get(key)
        if entry:
            if entry["state"] == HALF_OPEN:
                entry["half_open_successes"] += 1
                if entry["half_open_successes"] >= self._cfg.half_open_success_threshold:
                    del state["issues"][key]
                    log.info("SyncCircuitBreaker",
                             f"[{board_id}] #{issue_id} circuito fechado",
                             event="sync_circuit_breaker_transition",
                             board=board_id, issue=str(issue_id),
                             estado_anterior=HALF_OPEN, estado_novo=CLOSED)
                dirty = True
            elif entry["state"] == CLOSED and entry["failures"]:
                entry["failures"] = 0
                dirty = True

        pentry = state["platforms"].get(platform)
        if pentry and pentry["state"] == HALF_OPEN:
            pentry["half_open_successes"] += 1
            if pentry["half_open_successes"] >= self._cfg.half_open_success_threshold:
                state["platforms"][platform] = _new_platform_entry()
                log.info("SyncCircuitBreaker", f"plataforma {platform} circuito fechado",
                         event="sync_circuit_breaker_transition", plataforma=platform,
                         estado_anterior=HALF_OPEN, estado_novo=CLOSED)
            dirty = True

        if dirty:
            self._save(state)

    def release(self, board_id: str, issue_id) -> None:
        state = self._load()
        if state["issues"].pop(_key(board_id, issue_id), None) is not None:
            self._save(state)

    def record_failure(self, board_id: str, issue_id, error: str,
                       correctable: bool = False,
                       platform: str | None = None,
                       error_log: str | None = None) -> SyncEscalation | None:
        platform = platform or self.platform_of(board_id)
        state = self._load()
        key = _key(board_id, issue_id)
        entry = state["issues"].setdefault(key, _new_issue_entry())
        entry["attempts"] += 1

        if entry["escalated"]:
            self._save(state)
            log.error(
                "SyncCircuitBreaker",
                f"[{board_id}] #{issue_id} sync falhou após a correção do agente "
                f"'{entry['agent']}' - encerrando a esteira: {error}",
                event="sync_circuit_breaker_fatal", board=board_id,
                issue=str(issue_id), erro=error, tentativas=entry["attempts"],
                agente_que_corrigiu=entry["agent"],
            )
            raise SyncCircuitBreakerFatal(
                board_id, str(issue_id), error, entry["attempts"], entry["agent"]
            )

        self._reopen_platform_if_half_open(state, platform)

        if correctable:
            return self._escalate(state, entry, board_id, issue_id, error_log or error)

        if entry["state"] == HALF_OPEN:
            self._block_issue(state, entry, board_id, issue_id, platform, reopened=True)
        else:
            entry["failures"] += 1
            log.warning(
                "SyncCircuitBreaker",
                f"[{board_id}] #{issue_id} falha de sync "
                f"{entry['failures']}/{self._cfg.issue_max_failures}",
                event="sync_circuit_breaker_failure", board=board_id,
                issue=str(issue_id), falhas_consecutivas=entry["failures"],
            )
            if entry["failures"] >= self._cfg.issue_max_failures:
                self._block_issue(state, entry, board_id, issue_id, platform)

        if entry["state"] == OPEN and entry["blocks"] >= self._cfg.issue_max_blocks:
            return self._escalate(state, entry, board_id, issue_id, error_log or error)

        self._save(state)
        return None

    def _reopen_platform_if_half_open(self, state: dict, platform: str) -> None:
        pentry = state["platforms"].get(platform)
        if pentry and pentry["state"] == HALF_OPEN:
            self._block_platform(pentry, platform, reopened=True)

    def _block_issue(self, state: dict, entry: dict, board_id: str, issue_id,
                     platform: str, reopened: bool = False) -> None:
        now = self._clock()
        failures = entry["failures"] if not reopened else 1
        entry["state"] = OPEN
        entry["failures"] = 0
        entry["half_open_successes"] = 0
        entry["blocks"] += 1
        entry["blocked_until"] = now + self._cfg.issue_block_duration
        log.warning(
            "SyncCircuitBreaker",
            f"[{board_id}] #{issue_id} sync bloqueado por "
            f"{self._cfg.issue_block_duration}s"
            + (" (reaberto em meio-aberto)" if reopened else ""),
            event="sync_circuit_breaker_issue_blocked", board=board_id,
            issue=str(issue_id), falhas_consecutivas=failures,
            bloqueios_consecutivos=entry["blocks"],
            bloqueado_ate=entry["blocked_until"], reaberto=reopened,
        )
        pentry = state["platforms"].setdefault(platform, _new_platform_entry())
        window = self._cfg.platform_block_window
        pentry["blocked"] = {
            k: ts for k, ts in pentry["blocked"].items() if now - ts < window
        }
        pentry["blocked"][_key(board_id, issue_id)] = now
        if (pentry["state"] != OPEN
                and len(pentry["blocked"]) >= self._cfg.platform_max_blocked_issues):
            self._block_platform(pentry, platform)

    def _block_platform(self, pentry: dict, platform: str, reopened: bool = False) -> None:
        now = self._clock()
        pentry["state"] = OPEN
        pentry["half_open_successes"] = 0
        pentry["blocked_until"] = now + self._cfg.platform_block_duration
        log.warning(
            "SyncCircuitBreaker",
            f"plataforma {platform} bloqueada por {self._cfg.platform_block_duration}s",
            event="sync_circuit_breaker_platform_blocked", board=platform,
            issues_bloqueadas=sorted(pentry["blocked"]),
            janela=self._cfg.platform_block_window,
            bloqueado_ate=pentry["blocked_until"], reaberto=reopened,
        )

    def _escalate(self, state: dict, entry: dict, board_id: str, issue_id,
                  error: str) -> SyncEscalation:
        agent_id = self._cfg.escalation_agent
        entry["escalated"] = True
        entry["agent"] = agent_id
        entry["state"] = HALF_OPEN
        entry["blocked_until"] = 0.0
        entry["half_open_successes"] = 0
        self._save(state)
        log.warning(
            "SyncCircuitBreaker",
            f"[{board_id}] #{issue_id} escalando ao agente '{agent_id}'",
            event="sync_circuit_breaker_escalation", board=board_id,
            issue=str(issue_id), agente_dedicado=agent_id,
            bloqueios_consecutivos=entry["blocks"],
        )
        return SyncEscalation(
            board_id=board_id, issue_id=str(issue_id), error_log=error,
            blocks=entry["blocks"], agent_id=agent_id,
        )
