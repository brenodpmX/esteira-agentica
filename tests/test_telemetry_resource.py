import pytest

from src.core import telemetry
from src.core.consumption_limit import instance_id
from src.core.version import VERSION
from tests._telemetria_helpers import REPO_URL, config_base, instalar, isolamento  # noqa: F401


def _sinais(coletor):
    telemetry.emit(telemetry.EV_PIPE_CICLO, {"esteira.ciclo.duracao_s": 0.1})
    with telemetry.span("esteira.sync.item change-up", {"esteira.sync.evento": "change-up"}):
        pass
    telemetry.register_gauge("esteira.sync.orfaos.total", "{arquivo}", "",
                             lambda: [(0, {"esteira.board": "entrega"})])
    logs = [dict(r.resource.attributes) for r in coletor.registros()]
    spans = [dict(s.resource.attributes) for s in coletor.spans()]
    metricas = coletor.recursos_metricas()
    return logs, spans, metricas


def test_ct_res_attr_01_atributos_fixos_em_todo_sinal(isolamento):
    pytest.importorskip("opentelemetry.sdk")
    coletor = instalar(config_base())
    logs, spans, metricas = _sinais(coletor)
    assert logs and spans and metricas
    for attrs in logs + spans + metricas:
        assert attrs["service.name"] == "esteira-agentica"
        assert attrs["service.version"] == VERSION
        assert attrs["esteira.contrato"] == "1"
        assert attrs["service.instance.id"] == instance_id(config_base())
        assert attrs["esteira.pipe.nome"] == "esteira-demo"


def test_ct_res_attr_02_instance_id_env_ou_default(isolamento, monkeypatch):
    assert telemetry.resource_attributes(config_base())["service.instance.id"] == REPO_URL
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "service.instance.id=pipe-a,team=x")
    attrs = telemetry.resource_attributes(config_base())
    assert attrs["service.instance.id"] == "pipe-a"
    assert attrs["team"] == "x"


def test_ct_res_attr_03_pipe_nome_env_ou_repositorio(isolamento, monkeypatch):
    assert telemetry.resource_attributes(config_base())["esteira.pipe.nome"] == "esteira-demo"
    ssh = config_base(git={"repo": {"main": "git@github.com:acme/outra.git"}})
    assert telemetry.resource_attributes(ssh)["esteira.pipe.nome"] == "outra"
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "esteira.pipe.nome=Pipe%20Produ%C3%A7%C3%A3o")
    assert telemetry.resource_attributes(config_base())["esteira.pipe.nome"] == "Pipe Produção"


def test_ct_res_attr_04_environment(isolamento, monkeypatch):
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "deployment.environment.name=forjado")
    assert "deployment.environment.name" not in telemetry.resource_attributes(config_base())
    monkeypatch.setenv("PIPE_ENVIRONMENT", "producao")
    assert telemetry.resource_attributes(config_base())["deployment.environment.name"] == "producao"


def test_atributos_fixos_nao_sao_sobrescritos_por_env(isolamento, monkeypatch):
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "service.name=x,esteira.contrato=9")
    attrs = telemetry.resource_attributes(config_base())
    assert attrs["service.name"] == "esteira-agentica"
    assert attrs["esteira.contrato"] == "1"


def test_ct_dist_01_duas_pipes_distinguiveis(isolamento):
    pytest.importorskip("opentelemetry.sdk")
    resultados = {}
    for nome in ("pipe-a", "pipe-b"):
        attrs = telemetry.resource_attributes(config_base())
        attrs["service.instance.id"] = nome
        coletor = instalar(resource=attrs)
        resultados[nome] = _sinais(coletor)
        telemetry.configure(None)
        coletor.port.shutdown(0.5)
    for nome, (logs, spans, metricas) in resultados.items():
        ids = {a["service.instance.id"] for a in logs + spans + metricas}
        assert ids == {nome}
