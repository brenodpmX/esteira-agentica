"""Acumulador, decisão de bloqueio e observabilidade do limitador de consumo (#311).

Casos CT-B1..CT-B15 e CT-D1..CT-D4 de
doc/quality/limitador-opcional-consumo-ia-plataforma/test-cases.md. Só o relógio
e a escrita em disco são substituídos; a decisão roda de verdade.
"""

import json
import os
from datetime import datetime

import pytest

from src.core import consumption_limit as cl
from src.core.execution_record import Consumo

from tests._consumo_helpers import (
    Clock, at, capture_log, consumed, events, policy,
)

DAILY_100 = {"timezone": "America/Sao_Paulo", "daily": {"limit": 100}}


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    capture_log(monkeypatch)
    cl._disk_cache.clear()


@pytest.fixture
def clock():
    return Clock(at(2026, 11, 6, 12, 0))


def _limiter(clock, instance="inst-1"):
    return cl.ConsumptionLimiter(instance, clock=clock)


def _consume(limiter, pol, *values, platform="kiro"):
    for v in values:
        limiter.record(platform, pol, consumed(v))


class TestFronteiraDoLimite:
    @pytest.mark.parametrize("values,admitted", [
        ((60, 40), False),
        ((100, 50), False),
        ((50, 49), True),
    ], ids=["CT-B1-igual", "CT-B2-acima", "CT-B3-abaixo"])
    def test_decisao(self, clock, values, admitted):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        _consume(lim, pol, *values)
        assert lim.admit("kiro", pol).admitted is admitted

    def test_fracionado_soma_exata(self, clock):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        _consume(lim, pol, 99.5, 0.5)
        assert lim.admit("kiro", pol).admitted is False


class TestCTB4SemPolitica:
    def test_sempre_admite_sem_estado_nem_log(self, clock, tmp_path):
        lim = _limiter(clock)
        pol = policy(None)
        for _ in range(5):
            lim.record("kiro", pol, consumed(10_000))
            assert lim.admit("kiro", pol).admitted is True
        assert not (tmp_path / ".pipe").exists()
        assert events(cl.EVENT_BLOCK) == []
        assert events(cl.EVENT_UNAVAILABLE) == []

    def test_limits_vazio_inativo(self):
        assert policy({}).active is False


class TestCTB5ExecucaoEmAndamento:
    def test_so_a_proxima_e_impedida(self, clock):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        _consume(lim, pol, 90)
        assert lim.admit("kiro", pol).admitted is True
        lim.record("kiro", pol, consumed(50))
        assert cl.load_state()["platforms"]["kiro"]["periods"]["daily"]["consumo"] == 140
        assert lim.admit("kiro", pol).admitted is False


class TestCTB6IsolamentoPlataformas:
    def test_outra_plataforma_segue(self, clock):
        lim = _limiter(clock)
        pol_a = policy(DAILY_100, "kiro")
        pol_b = policy({"daily": {"limit": 100}}, "outra")
        _consume(lim, pol_a, 100)
        _consume(lim, pol_b, 10, platform="outra")
        assert lim.admit("kiro", pol_a).admitted is False
        assert lim.admit("outra", pol_b).admitted is True
        assert lim.admit("sem-limite", policy(None, "sem-limite")).admitted is True


class TestCTB7IsolamentoInstancias:
    def test_outra_instancia_nao_herda(self, clock, tmp_path, monkeypatch):
        inst1 = tmp_path / "inst1"
        inst2 = tmp_path / "inst2"
        inst1.mkdir()
        inst2.mkdir()
        pol = policy(DAILY_100)

        monkeypatch.chdir(inst1)
        lim1 = _limiter(clock, "repo-1")
        _consume(lim1, pol, 100)
        assert lim1.admit("kiro", pol).admitted is False

        monkeypatch.chdir(inst2)
        assert _limiter(clock, "repo-2").admit("kiro", pol).admitted is True


class TestCTB8CombinacaoDePeriodos:
    LIMITS = {
        "timezone": "America/Sao_Paulo",
        "daily": {"limit": 1000},
        "weekly": {"limit": 100, "reset_weekday": 0},
        "monthly": {"limit": 5000, "reset_day": 1},
    }

    def test_bloqueia_pelo_semanal(self, clock):
        lim = _limiter(clock)
        pol = policy(self.LIMITS)
        _consume(lim, pol, 100)
        decision = lim.admit("kiro", pol)
        assert decision.admitted is False
        assert decision.record["periodo"] == "semanal"
        assert events(cl.EVENT_BLOCK)[0]["periodo"] == "semanal"

    @pytest.mark.parametrize("hit,label", [("daily", "diario"), ("monthly", "mensal")])
    def test_cada_periodo_bloqueia_isolado(self, clock, hit, label):
        limits = json.loads(json.dumps(self.LIMITS))
        for period in ("daily", "weekly", "monthly"):
            limits[period]["limit"] = 50 if period == hit else 10_000
        lim = _limiter(clock)
        pol = policy(limits)
        _consume(lim, pol, 50)
        decision = lim.admit("kiro", pol)
        assert decision.admitted is False
        assert decision.record["periodo"] == label

    def test_varios_atingidos_reporta_retomada_mais_tardia(self, clock):
        limits = json.loads(json.dumps(self.LIMITS))
        limits["daily"]["limit"] = 10
        limits["monthly"]["limit"] = 10
        lim = _limiter(clock)
        pol = policy(limits)
        _consume(lim, pol, 100)
        assert lim.admit("kiro", pol).record["periodo"] == "mensal"


class TestRetomadaPorMudancaDeLimite:
    def test_ctb9_aumento(self, clock):
        lim = _limiter(clock)
        _consume(lim, policy(DAILY_100), 100)
        assert lim.admit("kiro", policy(DAILY_100)).admitted is False
        maior = {"timezone": "America/Sao_Paulo", "daily": {"limit": 200}}
        assert lim.admit("kiro", policy(maior)).admitted is True
        assert cl.load_state()["platforms"]["kiro"]["periods"]["daily"]["consumo"] == 100

    @pytest.mark.parametrize("limits", [None, {"timezone": "America/Sao_Paulo"}])
    def test_ctb10_desativacao(self, clock, limits):
        lim = _limiter(clock)
        _consume(lim, policy(DAILY_100), 100)
        assert lim.admit("kiro", policy(DAILY_100)).admitted is False
        assert lim.admit("kiro", policy(limits)).admitted is True

    def test_retomada_registra_tempo_bloqueado(self, clock):
        lim = _limiter(clock)
        _consume(lim, policy(DAILY_100), 100)
        lim.admit("kiro", policy(DAILY_100))
        clock.ts += 120
        maior = {"timezone": "America/Sao_Paulo", "daily": {"limit": 200}}
        assert lim.admit("kiro", policy(maior)).admitted is True
        resumed = events(cl.EVENT_RESUMED)
        assert len(resumed) == 1
        assert resumed[0]["tempo_bloqueado_seg"] == 120
        lim.admit("kiro", policy(maior))
        assert len(events(cl.EVENT_RESUMED)) == 1


class TestCTB11Indisponibilidade:
    @pytest.mark.parametrize("consumo", [Consumo.indisponivel(origem="kiro"), None])
    def test_falha_aberta_sem_somar(self, clock, consumo):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        _consume(lim, pol, 40)
        assert lim.admit("kiro", pol).admitted is True
        lim.record("kiro", pol, consumo, motivo="sem medição")
        assert cl.load_state()["platforms"]["kiro"]["periods"]["daily"]["consumo"] == 40
        assert lim.admit("kiro", pol).admitted is True
        assert len(events(cl.EVENT_UNAVAILABLE)) == 1

    def test_zero_reportado_nao_e_indisponivel(self, clock):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        lim.record("kiro", pol, consumed(0))
        assert events(cl.EVENT_UNAVAILABLE) == []
        assert len(events(cl.EVENT_ACCUMULATED)) == 1


class TestCTB12Persistencia:
    def test_acumulado_sobrevive_a_novo_limiter(self, clock):
        pol = policy(DAILY_100)
        _consume(_limiter(clock), pol, 70)
        _consume(_limiter(clock), pol, 30)
        clock.ts += 3600
        assert _limiter(clock).admit("kiro", pol).admitted is False


class TestCTB13Unidade:
    def test_soma_sem_conversao(self, clock):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        _consume(lim, pol, 1.25, 2.5, 3)
        plat = cl.load_state()["platforms"]["kiro"]
        assert plat["periods"]["daily"]["consumo"] == 6.75
        assert plat["unidade"] == "credit"

    def test_unidade_divergente_nao_soma(self, clock):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        _consume(lim, pol, 10)
        lim.record("kiro", pol, consumed(500, unidade="tokens"))
        plat = cl.load_state()["platforms"]["kiro"]
        assert plat["periods"]["daily"]["consumo"] == 10
        mismatch = events(cl.EVENT_UNIT_MISMATCH)
        assert mismatch and mismatch[0]["unidade"] == "tokens"


class TestCTB14EstadoCorrompido:
    @pytest.mark.parametrize("content", ["{nao json", json.dumps({"version": 99}), "[]"])
    def test_corrompido_zera_e_admite(self, clock, tmp_path, content):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        _consume(lim, pol, 500)
        (tmp_path / ".pipe" / "consumptionLimit.json").write_text(content, encoding="utf-8")
        assert lim.admit("kiro", pol).admitted is True
        rec = events(cl.EVENT_RECOVERY)
        assert any(r["motivo"].startswith("corrompido") for r in rec)

    def test_ausente_zera_e_admite(self, clock, tmp_path):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        _consume(lim, pol, 500)
        (tmp_path / ".pipe" / "consumptionLimit.json").unlink()
        assert lim.admit("kiro", pol).admitted is True
        assert any(r["motivo"] == "ausente" for r in events(cl.EVENT_RECOVERY))


class TestCTB15FalhaDePersistencia:
    def test_falha_registrada_com_valor(self, clock, monkeypatch):
        lim = _limiter(clock)
        pol = policy(DAILY_100)
        lim.admit("kiro", pol)

        def _boom(*a, **k):
            raise OSError("disco cheio")

        monkeypatch.setattr(os, "replace", _boom)
        lim.record("kiro", pol, consumed(42))
        falhas = events(cl.EVENT_PERSIST_ERROR)
        assert len(falhas) == 1
        assert falhas[0]["valor"] == 42
        assert falhas[0]["unidade"] == "credit"


class TestObservabilidadeBloqueio:
    def _block(self, clock, **context):
        lim = _limiter(clock, "github.com/org/repo.git")
        pol = policy(DAILY_100)
        _consume(lim, pol, 120)
        return lim.admit("kiro", pol, **context)

    def test_ctd1_aviso_no_terminal(self, clock, capsys):
        self._block(clock)
        out = capsys.readouterr().out
        assert "ConsumoLimite" in out
        assert "kiro" in out
        assert "acionamento impedido" in out

    def test_ctd2_evento_no_arquivo(self, clock):
        self._block(clock)
        assert len(events(cl.EVENT_BLOCK)) == 1

    def test_ctd3_campos_completos(self, clock):
        self._block(clock, board="entrega", issue="42")
        rec = events(cl.EVENT_BLOCK)[0]
        for key in ("instancia", "plataforma", "unidade", "consumo_periodo",
                    "limite", "periodo", "condicao_retomada", "timestamp"):
            assert rec.get(key) not in (None, ""), key
        assert rec["instancia"] == "github.com/org/repo.git"
        assert rec["plataforma"] == "kiro"
        assert rec["unidade"] == "credit"
        assert rec["consumo_periodo"] == 120
        assert rec["limite"] == 100
        assert rec["periodo"] == "diario"
        assert rec["condicao_retomada"] == (
            "reinicio em 2026-11-07 00:00 America/Sao_Paulo ou "
            "aumento/desativacao do limite"
        )
        assert datetime.fromisoformat(rec["timestamp"]).utcoffset() is not None
        assert rec["board"] == "entrega" and rec["issue"] == "42"

    def test_ctd4_indisponivel_sem_valor_nem_segredo(self, clock, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "ghp_supersecreto")
        lim = _limiter(clock, cl.instance_id(
            {"git": {"repo": {"main": "https://x:ghp_supersecreto@github.com/o/r.git"}}}))
        lim.record("kiro", policy(DAILY_100), Consumo.indisponivel(origem="kiro"),
                   motivo="plataforma não reportou consumo")
        rec = events(cl.EVENT_UNAVAILABLE)[0]
        for key in ("instancia", "plataforma", "motivo", "timestamp"):
            assert rec[key]
        assert "valor" not in rec
        assert "ghp_supersecreto" not in str(rec)
        assert rec["instancia"] == "https://github.com/o/r.git"


class TestInstanceId:
    def test_usa_repo_do_board(self):
        config = {"git": {"repo": {"a": "git@github.com:o/a.git",
                                   "b": "git@github.com:o/b.git"}}}
        assert cl.instance_id(config, "b") == "git@github.com:o/b.git"
        assert cl.instance_id(config) == "git@github.com:o/a.git"

    def test_sem_git(self):
        assert cl.instance_id({}, "main") == "main"
