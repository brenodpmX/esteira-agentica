"""Configuração `agents.<plataforma>.limits` do limitador de consumo (#311).

Casos CT-A1..CT-A10 de doc/quality/limitador-opcional-consumo-ia-plataforma/test-cases.md.
"""

import copy

import pytest

from src.core import config as cfg
from src.core.config import ConfigError, _validate_agents
from src.core.consumption_limit import (
    DAILY, MONTHLY, WEEKLY, resolve_policy, validate_consumption_limits,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = tmp_path / "contexts" / "kiro"
    ctx.mkdir(parents=True)
    (ctx / "dev.md").write_text("persona", encoding="utf-8")


def _config(limits=None):
    platform = {"dev": {"name": "Dev"}}
    if limits is not None:
        platform["limits"] = limits
    return {"agents": {"kiro": platform}}


def _full_config(limits=None):
    c = _config(limits)
    c.update({
        "sleep": 10,
        "project": {"name": "P", "summary": "S"},
        "git": {"repo": {"main": "git@github.com:u/r.git"},
                "flow": {"base": "main",
                         "feature": {"prefix": "feature", "branch_pattern": "feature/{id}-{slug}"}}},
        "boards": {"platform": "github",
                   "entrega": {"name": "Entrega",
                               "columns": {"dev": {"name": "Dev", "agent": "dev"}}}},
    })
    return c


def _check_config(tmp_path, monkeypatch, config):
    import yaml
    key = tmp_path / "key"
    key.write_text("k", encoding="utf-8")
    monkeypatch.setenv(cfg.SSH_KEY_ENV, str(key))
    (tmp_path / "pipe.yml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return cfg.check_config()


class TestCTA1Ausente:
    def test_sem_limits_valida_e_politica_inativa(self):
        config = _config()
        validate_consumption_limits(config)
        assert resolve_policy(config, "kiro").active is False

    def test_plataforma_inexistente_inativa(self):
        assert resolve_policy(_config(), "outra").active is False


class TestCTA2PeriodosCombinados:
    @pytest.mark.parametrize("limits", [
        {"daily": {"limit": 10}},
        {"weekly": {"limit": 20, "reset_weekday": 0}},
        {"monthly": {"limit": 30, "reset_day": 1}},
        {"monthly": {"limit": 30, "reset_day": "last"}, "timezone": "UTC",
         "weekly": {"limit": 20, "reset_weekday": 6}, "daily": {"limit": 10}},
    ])
    def test_aceito_e_resolvido(self, limits):
        config = _config(limits)
        validate_consumption_limits(config)
        policy = resolve_policy(config, "kiro")
        assert policy.active is True
        assert set(policy.periods) == set(limits) - {"timezone"}
        for period, pp in policy.periods.items():
            assert pp.limit == limits[period]["limit"]


class TestCTA3LimitsNaoEhAgente:
    def test_validate_agents_ignora_limits(self):
        _validate_agents(_config({"daily": {"limit": 100}})["agents"])

    def test_check_config_completo_aceita(self, tmp_path, monkeypatch):
        config = _check_config(tmp_path, monkeypatch,
                               _full_config({"daily": {"limit": 100}}))
        assert config["agents"]["kiro"]["limits"] == {"daily": {"limit": 100}}

    def test_limits_nao_vira_agente_conhecido(self, tmp_path, monkeypatch):
        config = _full_config({"daily": {"limit": 100}})
        config["boards"]["entrega"]["columns"]["dev"]["agent"] = "limits"
        with pytest.raises(ConfigError, match="agente 'limits' não definido"):
            _check_config(tmp_path, monkeypatch, config)


class TestCTA4Timezone:
    @pytest.mark.parametrize("tz", [None, "America/Sao_Paulo"])
    def test_valido(self, tz):
        limits = {"daily": {"limit": 1}}
        if tz:
            limits["timezone"] = tz
        validate_consumption_limits(_config(limits))

    @pytest.mark.parametrize("tz", ["Nao/Existe", "", 3])
    def test_invalido(self, tz):
        with pytest.raises(ConfigError, match=r"agents\.kiro\.limits\.timezone") as exc:
            validate_consumption_limits(_config({"timezone": tz, "daily": {"limit": 1}}))
        assert repr(tz) in str(exc.value)


_PERIOD_BASE = {
    DAILY: {},
    WEEKLY: {"reset_weekday": 0},
    MONTHLY: {"reset_day": 1},
}


class TestCTA5LimitePositivo:
    @pytest.mark.parametrize("period", [DAILY, WEEKLY, MONTHLY])
    @pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "10"])
    def test_rejeitado(self, period, value):
        limits = {period: {"limit": value, **_PERIOD_BASE[period]}}
        with pytest.raises(ConfigError, match=rf"agents\.kiro\.limits\.{period}\.limit") as exc:
            validate_consumption_limits(_config(limits))
        assert repr(value) in str(exc.value)

    @pytest.mark.parametrize("period", [DAILY, WEEKLY, MONTHLY])
    def test_limit_ausente(self, period):
        with pytest.raises(ConfigError, match=rf"limits\.{period}\.limit: campo obrigatório"):
            validate_consumption_limits(_config({period: dict(_PERIOD_BASE[period])}))


class TestCTA6ResetWeekday:
    @pytest.mark.parametrize("value", [-1, 7, "2", True])
    def test_invalido(self, value):
        with pytest.raises(ConfigError, match=r"limits\.weekly\.reset_weekday"):
            validate_consumption_limits(
                _config({"weekly": {"limit": 1, "reset_weekday": value}}))

    def test_ausente(self):
        with pytest.raises(ConfigError, match=r"limits\.weekly\.reset_weekday"):
            validate_consumption_limits(_config({"weekly": {"limit": 1}}))

    @pytest.mark.parametrize("value", [0, 6])
    def test_extremos_validos(self, value):
        validate_consumption_limits(
            _config({"weekly": {"limit": 1, "reset_weekday": value}}))


class TestCTA7ResetDay:
    @pytest.mark.parametrize("value", [0, 29, 30, 31, "ultimo", True])
    def test_invalido(self, value):
        with pytest.raises(ConfigError, match=r"limits\.monthly\.reset_day"):
            validate_consumption_limits(
                _config({"monthly": {"limit": 1, "reset_day": value}}))

    def test_ausente(self):
        with pytest.raises(ConfigError, match=r"limits\.monthly\.reset_day"):
            validate_consumption_limits(_config({"monthly": {"limit": 1}}))

    @pytest.mark.parametrize("value", ["last", 1, 28])
    def test_validos(self, value):
        validate_consumption_limits(
            _config({"monthly": {"limit": 1, "reset_day": value}}))


class TestCTA8CamposDesconhecidos:
    def test_campo_desconhecido_no_periodo(self):
        with pytest.raises(ConfigError, match=r"limits\.daily\.foo"):
            validate_consumption_limits(_config({"daily": {"limit": 10, "foo": 1}}))

    def test_periodo_desconhecido(self):
        with pytest.raises(ConfigError, match=r"limits\.bar"):
            validate_consumption_limits(_config({"bar": {}}))

    def test_bloco_lista(self):
        with pytest.raises(ConfigError, match=r"agents\.kiro\.limits: deve ser um mapa"):
            validate_consumption_limits(_config([1, 2]))

    def test_periodo_nao_mapa(self):
        with pytest.raises(ConfigError, match=r"limits\.daily: deve ser um mapa"):
            validate_consumption_limits(_config({"daily": 10}))


class TestCTA9ValidacaoAntesDeEstado:
    def test_falha_sem_criar_estado(self, tmp_path):
        with pytest.raises(ConfigError):
            validate_consumption_limits(_config({"daily": {"limit": 0}}))
        assert not (tmp_path / ".pipe").exists()

    def test_check_config_rejeita(self, tmp_path, monkeypatch):
        with pytest.raises(ConfigError, match=r"limits\.daily\.limit"):
            _check_config(tmp_path, monkeypatch, _full_config({"daily": {"limit": 0}}))
        assert not (tmp_path / ".pipe").exists()


class TestCTA10Retrocompatibilidade:
    def test_config_atual_sem_limits(self, tmp_path, monkeypatch):
        original = _full_config()
        config = _check_config(tmp_path, monkeypatch, copy.deepcopy(original))
        assert config["agents"] == original["agents"]
        assert resolve_policy(config, "kiro").active is False
