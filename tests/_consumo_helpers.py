import ast
import io
from datetime import datetime
from zoneinfo import ZoneInfo

from src.core import consumption_limit as cl
from src.core.execution_record import Consumo
from src.core.log import log

SP = "America/Sao_Paulo"


def at(*args, tz=SP) -> float:
    return datetime(*args, tzinfo=ZoneInfo(tz)).timestamp()


class Clock:
    def __init__(self, ts: float):
        self.ts = ts

    def __call__(self) -> float:
        return self.ts


def limits_config(limits: dict | None, platform: str = "kiro", agent: str = "dev",
                  extra_platforms: dict | None = None) -> dict:
    plat = {agent: {"name": "Dev"}}
    if limits is not None:
        plat["limits"] = limits
    agents = {platform: plat}
    agents.update(extra_platforms or {})
    return {
        "git": {"repo": {"main": "https://user:s3cr3t@github.com/org/repo.git"}},
        "agents": agents,
    }


def policy(limits: dict | None, platform: str = "kiro") -> cl.LimitPolicy:
    return cl.resolve_policy(limits_config(limits, platform), platform)


def consumed(valor, unidade="credit", origem="kiro") -> Consumo:
    return Consumo.reportado(valor, unidade, origem)


def capture_log(monkeypatch) -> io.StringIO:
    buf = io.StringIO()
    monkeypatch.setattr(log, "_file", buf)
    return buf


def events(name: str) -> list[dict]:
    out = []
    for line in log._file.getvalue().splitlines():
        if " | " not in line:
            continue
        extra = ast.literal_eval(line.split(" | ", 1)[1])
        if extra.get("event") == name:
            out.append(extra)
    return out
