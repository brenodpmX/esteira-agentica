"""Reset por período e fuso do limitador de consumo (#311).

Casos CT-C1..CT-C7 de doc/quality/limitador-opcional-consumo-ia-plataforma/test-cases.md.
Relógio injetado; o fuso local é controlado por `TZ` + `time.tzset()`.
"""

import time
from datetime import date, datetime, timedelta, timezone

import pytest

from src.core import consumption_limit as cl

from tests._consumo_helpers import Clock, at, capture_log, consumed, events, policy

SP = "America/Sao_Paulo"


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    capture_log(monkeypatch)
    cl._disk_cache.clear()


@pytest.fixture
def local_tz(monkeypatch):
    def _set(name):
        monkeypatch.setenv("TZ", name)
        time.tzset()
    yield _set
    monkeypatch.undo()
    time.tzset()


def _blocked_then(limits, start_ts, later_ts):
    clock = Clock(start_ts)
    lim = cl.ConsumptionLimiter("inst", clock=clock)
    pol = policy(limits)
    lim.record("kiro", pol, consumed(100))
    before = lim.admit("kiro", pol).admitted
    clock.ts = later_ts
    return before, lim.admit("kiro", pol).admitted


class TestCTC1Diario:
    LIMITS = {"timezone": SP, "daily": {"limit": 100}}

    def test_ainda_bloqueado_antes_da_virada(self):
        before, after = _blocked_then(self.LIMITS, at(2026, 11, 6, 10),
                                      at(2026, 11, 6, 23, 59, 59))
        assert (before, after) == (False, False)

    def test_retoma_na_virada(self):
        before, after = _blocked_then(self.LIMITS, at(2026, 11, 6, 10),
                                      at(2026, 11, 7, 0, 0, 0))
        assert (before, after) == (False, True)


class TestCTC2Semanal:
    @pytest.mark.parametrize("weekday", range(7))
    def test_reset_exatamente_no_dia(self, weekday):
        limits = {"timezone": SP, "weekly": {"limit": 100, "reset_weekday": weekday}}
        start = date(2026, 11, 2) + timedelta(days=weekday)
        start_ts = at(start.year, start.month, start.day, 1)
        nxt = start + timedelta(days=7)
        eve = nxt - timedelta(days=1)

        before, after_eve = _blocked_then(limits, start_ts,
                                          at(eve.year, eve.month, eve.day, 23, 59))
        assert (before, after_eve) == (False, False)
        cl.STATE_FILE.unlink()
        _, after = _blocked_then(limits, start_ts, at(nxt.year, nxt.month, nxt.day, 0, 0))
        assert after is True

    def test_period_bounds_semana(self):
        pp = cl.PeriodPolicy(cl.WEEKLY, 1, reset_weekday=0)
        now = datetime(2026, 11, 6, 12, tzinfo=cl.ZoneInfo(SP))
        start, nxt = cl.period_bounds(pp, now, cl.ZoneInfo(SP))
        assert start.date() == date(2026, 11, 2)
        assert nxt.date() == date(2026, 11, 9)


class TestCTC3Mensal:
    LIMITS = {"timezone": SP, "monthly": {"limit": 100, "reset_day": 15}}

    def test_bloqueado_ate_dia_15_seguinte(self):
        before, after = _blocked_then(self.LIMITS, at(2026, 11, 20),
                                      at(2026, 12, 14, 23, 59))
        assert (before, after) == (False, False)

    def test_retoma_no_dia_15(self):
        before, after = _blocked_then(self.LIMITS, at(2026, 11, 20), at(2026, 12, 15, 0, 0))
        assert (before, after) == (False, True)

    def test_antes_do_dia_de_reset_pertence_ao_mes_anterior(self):
        pp = cl.PeriodPolicy(cl.MONTHLY, 1, reset_day=15)
        tz = cl.ZoneInfo(SP)
        start, nxt = cl.period_bounds(pp, datetime(2026, 1, 10, tzinfo=tz), tz)
        assert start.date() == date(2025, 12, 15)
        assert nxt.date() == date(2026, 1, 15)


class TestCTC4MensalUltimoDia:
    @pytest.mark.parametrize("year,month,last", [
        (2027, 2, 28), (2028, 2, 29), (2026, 4, 30), (2026, 5, 31),
    ])
    def test_reset_no_ultimo_dia_real(self, year, month, last):
        tz = cl.ZoneInfo(SP)
        pp = cl.PeriodPolicy(cl.MONTHLY, 1, reset_day="last")
        start, _ = cl.period_bounds(pp, datetime(year, month, last, 0, 0, tzinfo=tz), tz)
        assert start.date() == date(year, month, last)
        start_prev, nxt = cl.period_bounds(
            pp, datetime(year, month, last - 1, 23, 59, tzinfo=tz), tz)
        assert nxt.date() == date(year, month, last)
        assert start_prev.date() < date(year, month, 1)

    def test_bloqueio_libera_no_ultimo_dia(self):
        limits = {"timezone": SP, "monthly": {"limit": 100, "reset_day": "last"}}
        before, after = _blocked_then(limits, at(2027, 2, 10), at(2027, 2, 28, 0, 0))
        assert (before, after) == (False, True)


class TestCTC5FusoConfigurado:
    LIMITS = {"timezone": SP, "daily": {"limit": 100}}

    def test_virada_em_sao_paulo_nao_em_utc(self):
        start = datetime(2026, 11, 7, 1, 0, tzinfo=timezone.utc).timestamp()
        meia_noite_utc_passada = datetime(2026, 11, 7, 2, 59, tzinfo=timezone.utc).timestamp()
        before, after = _blocked_then(self.LIMITS, start, meia_noite_utc_passada)
        assert (before, after) == (False, False)

        cl.STATE_FILE.unlink()
        virada_sp = datetime(2026, 11, 7, 3, 0, tzinfo=timezone.utc).timestamp()
        _, after = _blocked_then(self.LIMITS, start, virada_sp)
        assert after is True

    def test_independe_do_fuso_local(self, local_tz):
        local_tz("Asia/Tokyo")
        start = datetime(2026, 11, 7, 1, 0, tzinfo=timezone.utc).timestamp()
        virada_sp = datetime(2026, 11, 7, 3, 0, tzinfo=timezone.utc).timestamp()
        before, after = _blocked_then(self.LIMITS, start, virada_sp - 1)
        assert (before, after) == (False, False)


class TestCTC6FusoLocal:
    LIMITS = {"daily": {"limit": 100}}

    @pytest.mark.parametrize("tz_name,reset_utc_hour", [
        ("America/Sao_Paulo", 3), ("Asia/Tokyo", 15),
    ])
    def test_virada_acompanha_tz_da_maquina(self, local_tz, tz_name, reset_utc_hour):
        local_tz(tz_name)
        reset = datetime(2026, 11, 7, reset_utc_hour, 0, tzinfo=timezone.utc).timestamp()
        before, after = _blocked_then(self.LIMITS, reset - 3600, reset - 1)
        assert (before, after) == (False, False)
        cl.STATE_FILE.unlink()
        _, after = _blocked_then(self.LIMITS, reset - 3600, reset)
        assert after is True

    def test_dst_local_new_york(self, local_tz):
        local_tz("America/New_York")
        pp = cl.PeriodPolicy(cl.DAILY, 1)
        now = datetime(2026, 11, 1, 12).astimezone()
        start, nxt = cl.period_bounds(pp, now, None)
        assert start.utcoffset() == timedelta(hours=-4)
        assert nxt.utcoffset() == timedelta(hours=-5)
        assert (nxt - start) == timedelta(hours=25)

    def test_dst_zona_configurada(self):
        tz = cl.ZoneInfo("America/New_York")
        pp = cl.PeriodPolicy(cl.DAILY, 1)
        start, nxt = cl.period_bounds(pp, datetime(2026, 3, 8, 12, tzinfo=tz), tz)
        assert nxt.timestamp() - start.timestamp() == 23 * 3600


class TestCTC7FallbackDeFuso:
    def test_fuso_indisponivel_em_runtime(self, monkeypatch, local_tz):
        local_tz("Asia/Tokyo")

        def _boom(name):
            raise OSError("tzdata ausente")

        monkeypatch.setattr(cl, "ZoneInfo", _boom)
        assert cl.resolve_tz(SP, "kiro") is None
        fallback = events(cl.EVENT_TZ_FALLBACK)
        assert fallback and fallback[0]["fuso"] == SP

        clock = Clock(datetime(2026, 11, 7, 14, 0, tzinfo=timezone.utc).timestamp())
        lim = cl.ConsumptionLimiter("inst", clock=clock)
        pol = policy({"timezone": SP, "daily": {"limit": 100}})
        lim.record("kiro", pol, consumed(100))
        assert lim.admit("kiro", pol).admitted is False
        clock.ts = datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc).timestamp()
        assert lim.admit("kiro", pol).admitted is True
