"""Integração do limitador de consumo com `call_agent`/`keep_task` (#311).

Casos CT-E1..CT-E3 e CT-F1 de
doc/quality/limitador-opcional-consumo-ia-plataforma/test-cases.md. O dispatch é
um espião (nunca chama kiro-cli); o gate de consumo roda de verdade.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

import src.__main__ as m
from src.core import consumption_limit as cl
from src.core import execution
from src.core import execution_record as er
from src.core.execution import ExecutionResult
from src.core.execution_record import Consumo

from tests._consumo_helpers import Clock, at, capture_log, events

BOARD_ID = "entrega"
COL_ID = "desenvolvimento"
DAILY_100 = {"timezone": "America/Sao_Paulo", "daily": {"limit": 100}}


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pipe").mkdir()
    capture_log(monkeypatch)
    cl._disk_cache.clear()
    clock = Clock(at(2026, 11, 6, 12))
    real = cl.ConsumptionLimiter
    monkeypatch.setattr(cl, "ConsumptionLimiter",
                        lambda instance, clock=clock: real(instance, clock=clock))
    monkeypatch.setattr(m, "board", MagicMock())
    return clock


def _config(limits=DAILY_100, other_limits=None):
    kiro = {"dev": {"name": "engineering", "model": "m"}}
    if limits is not None:
        kiro["limits"] = limits
    outra = {"qa": {"name": "quality"}}
    if other_limits is not None:
        outra["limits"] = other_limits
    return {
        "git": {
            "repo": {"main": "git@github.com:org/repo.git"},
            "flow": {"base": "main",
                     "feature": {"prefix": "feature/", "create": "main", "merge": "main",
                                 "branch_pattern": "feature/{id}-{slug}"}},
        },
        "agents": {"kiro": kiro, "outra": outra},
        "boards": {
            "platform": "github",
            BOARD_ID: {
                "name": "Entrega", "flow": "feature", "repo": "main",
                "columns": {
                    COL_ID: {"name": "Desenvolvimento", "agent": "dev",
                             "change": {"advance": "done"}},
                    "qa": {"name": "QA", "agent": "qa", "change": {"advance": "done"}},
                    "done": {"name": "Done", "archive": True},
                },
            },
        },
        "sleep": 60,
    }


def _task(tmp_path, config, issue_id="42", col_id=COL_ID):
    issue_dir = tmp_path / ".pipe" / "boards" / BOARD_ID / col_id
    issue_dir.mkdir(parents=True, exist_ok=True)
    body = issue_dir / f"{issue_id}-feat-body.md"
    body.write_text("# Feat\n\ncorpo\n", encoding="utf-8")
    return {
        "board_id": BOARD_ID,
        "board": config["boards"][BOARD_ID],
        "col_id": col_id,
        "column": config["boards"][BOARD_ID]["columns"][col_id],
        "issue": {"id": issue_id, "body_path": str(body)},
    }


def _run(config, task, result):
    spy = MagicMock(return_value=result)
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record",
                      return_value={"instrucoes_obrigatorias_carregadas": True}), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery", spy):
        m.call_agent(config, task)
    return spy


def _ok(valor):
    return ExecutionResult(classe=execution.SUCEDIDO,
                           consumo=Consumo.reportado(valor, "credit", "kiro"))


class TestCTE1Bloqueada:
    def test_agente_nao_despachado(self, tmp_path):
        config = _config()
        assert _run(config, _task(tmp_path, config), _ok(100)).call_count == 1
        records_before = len(er.records_for_issue("42"))

        spy = _run(config, _task(tmp_path, config), _ok(1))
        assert spy.call_count == 0
        assert len(er.records_for_issue("42")) == records_before
        rec = events(cl.EVENT_BLOCK)[0]
        assert rec["instancia"] == "git@github.com:org/repo.git"
        assert rec["board"] == BOARD_ID and rec["issue"] == "42"


class TestCTE2Liberada:
    def test_despacho_normal_sem_rede(self, tmp_path):
        config = _config()
        spy = _run(config, _task(tmp_path, config), _ok(10))
        assert spy.call_count == 1
        assert m.board.method_calls == []
        state = cl.load_state()["platforms"]["kiro"]
        assert state["periods"]["daily"]["consumo"] == 10

    def test_sem_limits_nao_cria_estado(self, tmp_path):
        config = _config(limits=None)
        for _ in range(3):
            assert _run(config, _task(tmp_path, config), _ok(1000)).call_count == 1
        assert not (tmp_path / ".pipe" / "consumptionLimit.json").exists()
        assert events(cl.EVENT_BLOCK) == []


class TestCTE3TodasImpedidas:
    def test_n_tentativas_nenhuma_despacha(self, tmp_path):
        config = _config()
        _run(config, _task(tmp_path, config), _ok(150))
        calls = sum(_run(config, _task(tmp_path, config), _ok(1)).call_count
                    for _ in range(10))
        assert calls == 0
        assert len(events(cl.EVENT_BLOCK)) == 10


class TestIndisponivelNaIntegracao:
    def test_resultado_sem_consumo(self, tmp_path):
        config = _config()
        _run(config, _task(tmp_path, config), ExecutionResult(classe=execution.SUCEDIDO))
        _run(config, _task(tmp_path, config), None)
        motivos = [e["motivo"] for e in events(cl.EVENT_UNAVAILABLE)]
        assert motivos == ["plataforma não reportou consumo",
                           "execução sem resultado do adapter"]


def _seed_snapshot(issues):
    board_dir = Path(".pipe/boards") / BOARD_ID
    for issue in issues:
        (board_dir / issue["column"]).mkdir(parents=True, exist_ok=True)
        body = board_dir / issue["column"] / f"{issue['id']}-t-body.md"
        body.write_text("# T\n\ncorpo\n", encoding="utf-8")
        issue.update(body_path=str(body), body_mtime=str(body.stat().st_mtime),
                     created_at="2026-08-01T10:00:00Z", updated_at="2026-08-01T10:00:00Z",
                     status="ok")
    snap = {"board": {COL_ID: "Desenvolvimento", "qa": "QA", "done": "Done"},
            "issues": issues, "last_sync": None}
    (board_dir / "snapshot.json").write_text(json.dumps(snap))


class TestKeepTaskIsolamento:
    def test_issue_da_plataforma_bloqueada_e_pulada(self, tmp_path):
        config = _config()
        _run(config, _task(tmp_path, config, "1"), _ok(100))
        _seed_snapshot([
            {"id": "42", "column": COL_ID},
            {"id": "43", "column": "qa"},
        ])
        task = m.keep_task(BOARD_ID, config)
        assert task is not None and task["issue"]["id"] == "43"

    def test_sem_outra_elegivel_retorna_none(self, tmp_path):
        config = _config()
        _run(config, _task(tmp_path, config, "1"), _ok(100))
        _seed_snapshot([{"id": "42", "column": COL_ID}])
        assert m.keep_task(BOARD_ID, config) is None


class TestRetomadaSemReinicio:
    def _write_pipe(self, tmp_path, config, stamp):
        path = tmp_path / "pipe.yml"
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        os.utime(path, ns=(stamp, stamp))

    def test_aumento_no_pipe_yml_retoma(self, tmp_path):
        config = _config()
        self._write_pipe(tmp_path, config, 1_000_000_000)
        _run(config, _task(tmp_path, config), _ok(100))
        assert _run(config, _task(tmp_path, config), _ok(1)).call_count == 0

        disk = _config({"timezone": "America/Sao_Paulo", "daily": {"limit": 500}})
        self._write_pipe(tmp_path, disk, 2_000_000_000)
        assert _run(config, _task(tmp_path, config), _ok(1)).call_count == 1

    def test_remocao_no_pipe_yml_retoma(self, tmp_path):
        config = _config()
        self._write_pipe(tmp_path, config, 1_000_000_000)
        _run(config, _task(tmp_path, config), _ok(100))
        self._write_pipe(tmp_path, _config(limits=None), 2_000_000_000)
        assert _run(config, _task(tmp_path, config), _ok(1)).call_count == 1

    def test_limite_invalido_em_runtime_mantem_config_inicial(self, tmp_path):
        config = _config()
        _run(config, _task(tmp_path, config), _ok(100))
        self._write_pipe(tmp_path, _config({"daily": {"limit": 0}}), 2_000_000_000)
        assert _run(config, _task(tmp_path, config), _ok(1)).call_count == 0
        assert _run(config, _task(tmp_path, config), _ok(1)).call_count == 0
        assert len(events("consumo_limite_config_runtime_invalida")) == 1


class TestCTF1Baseline:
    def test_registros_suficientes(self, tmp_path, _isolate):
        clock = _isolate
        config = _config()
        _run(config, _task(tmp_path, config), ExecutionResult(classe=execution.SUCEDIDO))
        _run(config, _task(tmp_path, config), _ok(80))
        _run(config, _task(tmp_path, config), _ok(50))
        _run(config, _task(tmp_path, config), _ok(1))
        clock.ts = at(2026, 11, 7, 0, 30)
        assert _run(config, _task(tmp_path, config), _ok(5)).call_count == 1

        acumulados = events(cl.EVENT_ACCUMULATED)
        assert acumulados[1]["periodos"]["diario"]["excedente"] == 30

        assert len(events(cl.EVENT_UNAVAILABLE)) == 1

        bloqueios = events(cl.EVENT_BLOCK)
        assert len(bloqueios) == 1
        assert bloqueios[0]["consumo_periodo"] == 130

        retomadas = events(cl.EVENT_RESUMED)
        assert len(retomadas) == 1
        assert retomadas[0]["tempo_bloqueado_seg"] == at(2026, 11, 7, 0, 30) - at(2026, 11, 6, 12)

        for key in ("board", "coluna", "issue", "agente"):
            assert bloqueios[0][key]
