from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("opentelemetry.sdk")

from src.core import execution, telemetry  # noqa: E402
from src.core.execution import ExecutionResult  # noqa: E402
from tests._telemetria_helpers import config_base, escrever_issue, instalar, isolamento  # noqa: E402,F401
from tests.test_telemetry_contract import (EXECUCAO_ATTRS, FakePort, _apply,  # noqa: E402
                                           _fila, _medicao, _task)


def test_ct_trace_01_span_invoke_agent(isolamento, tmp_path):
    import src.__main__ as m

    coletor = instalar(config_base())
    body = escrever_issue(tmp_path)
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record", return_value=_medicao()), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery",
                      return_value=ExecutionResult(classe=execution.SUCEDIDO, origem="exit-code",
                                                   consumo=None)):
        m.call_agent(config_base(), _task(body))

    spans = coletor.spans("invoke_agent")
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "invoke_agent engineering"
    attrs = dict(span.attributes)
    assert attrs["gen_ai.operation.name"] == "invoke_agent"
    evento = coletor.eventos(telemetry.EV_EXECUCAO)[0]
    esperados = [a for a in EXECUCAO_ATTRS if a in evento]
    assert [a for a in esperados if a not in attrs] == []
    registro = coletor.registros_de(telemetry.EV_EXECUCAO)[0].log_record
    assert registro.trace_id == span.context.trace_id
    assert registro.span_id == span.context.span_id


def test_ct_trace_02_span_item_com_filho_board_api(isolamento):
    coletor = instalar(config_base())
    _apply(_fila(), FakePort())
    item = coletor.spans("esteira.sync.item")
    api = coletor.spans("esteira.board.api")
    assert [s.name for s in item] == ["esteira.sync.item change-up"]
    assert [s.name for s in api] == ["esteira.board.api move_issue"]
    assert api[0].parent.span_id == item[0].context.span_id
    assert api[0].context.trace_id == item[0].context.trace_id
    item_attrs = dict(item[0].attributes)
    evento = coletor.eventos(telemetry.EV_SYNC_ITEM)[0]
    assert {k: item_attrs.get(k) for k in evento if k != "event.name"} == {
        k: v for k, v in evento.items() if k != "event.name"}
    assert dict(api[0].attributes)["esteira.board.status"] == "ok"


def test_ct_trace_02_span_com_erro_marca_status_sem_mensagem(isolamento):
    from opentelemetry.trace import StatusCode

    coletor = instalar(config_base())
    _apply(_fila(), FakePort(RuntimeError("segredo ghp_ABCDEFGHIJKLMNOPQRSTUVWX")))
    for span in coletor.spans():
        assert span.status.status_code == StatusCode.ERROR
        assert not span.status.description
        assert not span.events
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWX" not in str(dict(span.attributes))


def test_ct_trace_03_evento_carrega_trace_e_span(isolamento):
    coletor = instalar(config_base())
    _apply(_fila(), FakePort())
    item = coletor.spans("esteira.sync.item")[0]
    api = coletor.spans("esteira.board.api")[0]
    rec_item = coletor.registros_de(telemetry.EV_SYNC_ITEM)[0].log_record
    rec_api = coletor.registros_de(telemetry.EV_BOARD_API)[0].log_record
    assert (rec_item.trace_id, rec_item.span_id) == (item.context.trace_id, item.context.span_id)
    assert (rec_api.trace_id, rec_api.span_id) == (api.context.trace_id, api.context.span_id)
