import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("opentelemetry.sdk")

from src.core import telemetry_metrics  # noqa: E402
from tests._telemetria_helpers import (BOARD_ID, config_base, instalar,  # noqa: E402,F401
                                       isolamento)

ISSUE_KEYS = ("esteira.issue", "esteira.issue.pai", "issue", "issue_id")


def _registrar(config=None, port=None, clock=time.time):
    config = config or config_base()
    coletor = instalar(config)
    telemetry_metrics.register(config, port, clock=clock)
    return coletor


def _port(throttle=4, penalty=0):
    port = MagicMock()
    port.rate_state.return_value = {"throttle_s": throttle, "penalty_h": penalty}
    return port


def _write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data), encoding="utf-8")


def _ts(seconds_ago, now):
    return datetime.fromtimestamp(now - seconds_ago, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_todas_as_metricas_do_contrato_registradas(isolamento):
    coletor = _registrar(port=_port())
    nomes = set(coletor.metricas())
    assert set(telemetry_metrics.METRICAS) - nomes <= {"esteira.consumo.acumulado",
                                                       "esteira.consumo.limite",
                                                       "esteira.consumo.bloqueado"}
    assert len(telemetry_metrics.METRICAS) == 11


def test_ct_met_01_throttle(isolamento):
    from src.adapters.github_board import GitHubBoardAdapter

    adapter = GitHubBoardAdapter()
    adapter._throttle_value = 8
    coletor = _registrar(port=adapter)
    assert coletor.metricas()["esteira.board.throttle"] == [
        (8, {"esteira.board.plataforma": "github"})]


def test_ct_met_02_penalty_ativo_e_inativo(isolamento):
    from src.adapters.github_board import GitHubBoardAdapter

    adapter = GitHubBoardAdapter()
    adapter._in_penalty = False
    coletor = _registrar(port=adapter)
    assert coletor.metricas()["esteira.board.penalty"][0][0] == 0
    adapter._in_penalty = True
    adapter._penalty_value = 4
    adapter._penalty_ttl = datetime.now() + timedelta(hours=2)
    assert coletor.metricas()["esteira.board.penalty"][0][0] == 2
    adapter._in_penalty = False


@pytest.mark.parametrize("estado,valor", [("closed", 0), ("half_open", 1), ("open", 2)])
def test_ct_met_03_breaker_estado(isolamento, estado, valor):
    from src.core.sync_circuit_breaker import STATE_FILE

    _write(STATE_FILE, {"issues": {}, "platforms": {"github": {"state": estado}}})
    coletor = _registrar()
    assert coletor.metricas()["esteira.sync.circuit_breaker.estado"] == [
        (valor, {"esteira.board.plataforma": "github"})]


@pytest.mark.parametrize("estados,esperado", [
    ([], 0), (["open"], 1), (["open", "half_open", "closed"], 2)])
def test_ct_met_04_issues_abertas(isolamento, estados, esperado):
    from src.core.sync_circuit_breaker import STATE_FILE

    issues = {f"{BOARD_ID}/{i}": {"state": s} for i, s in enumerate(estados)}
    _write(STATE_FILE, {"issues": issues, "platforms": {}})
    coletor = _registrar()
    pts = coletor.metricas()["esteira.sync.circuit_breaker.issues_abertas"]
    assert pts == [(esperado, {"esteira.board.plataforma": "github"})]


def _config_limite():
    config = config_base()
    config["agents"]["kiro-cli"]["limits"] = {"daily": {"limit": 100}}
    return config


def _estado_consumo(consumo, bloqueado=None):
    from src.core import consumption_limit as cl

    start, _ = cl.period_bounds(cl.PeriodPolicy("daily", 100), cl._now_in(time.time(), None), None)
    _write(cl.STATE_FILE, {"version": 1, "platforms": {"kiro-cli": {
        "unidade": "credit", "bloqueado_desde": bloqueado,
        "periods": {"daily": {"inicio": start.isoformat(), "consumo": consumo}}}}})


ATTRS_CONSUMO = {"esteira.ia.plataforma": "kiro-cli", "esteira.consumo.periodo": "diario",
                 "esteira.consumo.unidade": "credit"}


def test_ct_met_05_consumo_acumulado(isolamento):
    _estado_consumo(42.5)
    coletor = _registrar(_config_limite())
    assert coletor.metricas()["esteira.consumo.acumulado"] == [(42.5, ATTRS_CONSUMO)]


def test_ct_met_05_periodo_antigo_vale_zero(isolamento):
    from src.core import consumption_limit as cl

    _write(cl.STATE_FILE, {"version": 1, "platforms": {"kiro-cli": {
        "unidade": "credit", "periods": {"daily": {"inicio": "2000-01-01T00:00:00+00:00",
                                                    "consumo": 999}}}}})
    coletor = _registrar(_config_limite())
    assert coletor.metricas()["esteira.consumo.acumulado"][0][0] == 0


def test_ct_met_06_limite_configurado_e_ausente(isolamento):
    _estado_consumo(1)
    coletor = _registrar(_config_limite())
    assert coletor.metricas()["esteira.consumo.limite"] == [(100, ATTRS_CONSUMO)]


def test_ct_met_06_sem_limite_metrica_ausente(isolamento):
    coletor = _registrar(config_base())
    metricas = coletor.metricas()
    assert "esteira.consumo.limite" not in metricas
    assert "esteira.consumo.acumulado" not in metricas


@pytest.mark.parametrize("bloqueado,valor", [(None, 0), (1700000000.0, 1)])
def test_ct_met_07_consumo_bloqueado(isolamento, bloqueado, valor):
    _estado_consumo(1, bloqueado)
    coletor = _registrar(_config_limite())
    assert coletor.metricas()["esteira.consumo.bloqueado"] == [
        (valor, {"esteira.ia.plataforma": "kiro-cli"})]


def test_ct_met_08_fila_profundidade(isolamento):
    from src.core.change_queue import QUEUE_FILE

    now = time.time()
    _write(QUEUE_FILE, [
        {"timestamp": _ts(10, now), "event": "change-up", "id": "1", "board": BOARD_ID},
        {"timestamp": _ts(5, now), "event": "change-up", "id": "2", "board": BOARD_ID},
        {"timestamp": _ts(1, now), "event": "create-down", "id": "3", "board": BOARD_ID},
    ])
    coletor = _registrar()
    pts = {(a["esteira.board"], a["esteira.sync.evento"]): v
           for v, a in coletor.metricas()["esteira.sync.fila.profundidade"]}
    assert pts[(BOARD_ID, "change-up")] == 2
    assert pts[(BOARD_ID, "create-down")] == 1
    assert pts[(BOARD_ID, "delete-up")] == 0


def test_ct_met_09_fila_idade_maxima(isolamento):
    from src.core.change_queue import QUEUE_FILE

    now = 1_800_000_000.0
    _write(QUEUE_FILE, [
        {"timestamp": _ts(120, now), "event": "change-up", "id": "1", "board": BOARD_ID},
        {"timestamp": _ts(30, now), "event": "change-up", "id": "2", "board": BOARD_ID},
    ])
    coletor = _registrar(clock=lambda: now)
    assert coletor.metricas()["esteira.sync.fila.idade_maxima"] == [
        (120.0, {"esteira.board": BOARD_ID})]


def test_ct_met_10_dead_letter_por_categoria(isolamento):
    from src.core.dead_letter import DEAD_LETTER_FILE

    _write(DEAD_LETTER_FILE, [
        {"uuid": "a", "board": BOARD_ID, "id": "1", "category": "definitivo"},
        {"uuid": "b", "board": BOARD_ID, "id": "2", "category": "definitivo"},
        {"uuid": "c", "board": BOARD_ID, "id": "3", "category": "transitorio_esgotado"},
    ])
    coletor = _registrar()
    pts = {a["esteira.sync.dead_letter.categoria"]: v
           for v, a in coletor.metricas()["esteira.sync.dead_letter.total"]}
    assert pts["definitivo"] == 2
    assert pts["transitorio_esgotado"] == 1
    assert pts["corrigivel_pelo_agente"] == 0


@pytest.mark.parametrize("n", [0, 3])
def test_ct_met_11_orfaos(isolamento, n):
    from src.core.sync import ORPHAN_FILE

    if n:
        _write(ORPHAN_FILE, [{"board": BOARD_ID, "apparent_id": str(i)} for i in range(n)])
    coletor = _registrar()
    assert coletor.metricas()["esteira.sync.orfaos.total"] == [(n, {"esteira.board": BOARD_ID})]


def test_metrica_com_arquivo_corrompido_nao_falha(isolamento):
    from src.core.change_queue import QUEUE_FILE

    Path(QUEUE_FILE).write_text("{corrompido", encoding="utf-8")
    coletor = _registrar()
    pts = coletor.metricas()["esteira.sync.fila.profundidade"]
    assert all(v == 0 for v, _ in pts)


def test_ct_met_card_nenhuma_metrica_tem_id_de_issue(isolamento):
    from src.core.change_queue import QUEUE_FILE
    from src.core.dead_letter import DEAD_LETTER_FILE
    from src.core.sync import ORPHAN_FILE
    from src.core.sync_circuit_breaker import STATE_FILE

    now = time.time()
    _estado_consumo(3)
    _write(STATE_FILE, {"issues": {f"{BOARD_ID}/42": {"state": "open"}},
                        "platforms": {"github": {"state": "open"}}})
    _write(QUEUE_FILE, [{"timestamp": _ts(3, now), "event": "change-up", "id": "42",
                         "board": BOARD_ID}])
    _write(DEAD_LETTER_FILE, [{"uuid": "a", "board": BOARD_ID, "id": "42",
                               "category": "definitivo"}])
    _write(ORPHAN_FILE, [{"board": BOARD_ID, "apparent_id": "42"}])
    coletor = _registrar(_config_limite(), port=_port())
    metricas = coletor.metricas()
    assert set(telemetry_metrics.METRICAS) == set(metricas)
    infratores = [(nome, chave) for nome, pts in metricas.items() for _, attrs in pts
                  for chave, valor in attrs.items()
                  if chave in ISSUE_KEYS or "issue" in chave.split(".")[-1]
                  or str(valor) == "42"]
    assert infratores == []
