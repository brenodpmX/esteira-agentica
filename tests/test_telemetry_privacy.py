from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("opentelemetry.sdk")

from src.core import execution, telemetry  # noqa: E402
from src.core.dead_letter import sanitize_reason  # noqa: E402
from src.core.execution import ExecutionResult  # noqa: E402
from tests._telemetria_helpers import (COL_ID, config_base, escrever_issue,  # noqa: E402,F401
                                       instalar, isolamento, todos_os_valores)
from tests.test_telemetry_contract import FakePort, _fila, _medicao, _task  # noqa: E402

MARCADOR = "PROMPT-MARCADOR-XYZ"
TOKEN = "TOKEN-MARCADOR-123"
URL_CRED = f"https://usuario:{TOKEN}@github.com/acme/esteira-demo.git"


def _config_cred():
    config = config_base()
    config["git"]["repo"] = {"main": URL_CRED}
    return config


def _execucao(m, config, task):
    resultado = ExecutionResult(classe=execution.FALHA, output=f"conversa {MARCADOR}",
                                causa=f"erro {MARCADOR}", origem="exit-code")
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record",
                      return_value=_medicao(prompt=f"prompt {MARCADOR}")), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery", return_value=resultado):
        m.call_agent(config, task)


def _sync_com_comentario():
    from src.core import sync
    from src.core.board import Board

    def _change_up(board_id, item, board_obj, queue=None, config=None):
        board_obj.add_comment(board_id, item.id, f"comentário {MARCADOR}")
        board_obj.update_issue(board_id, item.id, title="t", body=f"body {MARCADOR}")

    with patch.object(sync, "_apply_change_up", side_effect=_change_up):
        sync.apply_changes(Board(FakePort()), _fila(), {"boards": {"platform": "github"}})


def test_ct_priv_01_sem_prompt_conversa_body_ou_comentario(isolamento, tmp_path):
    import src.__main__ as m

    coletor = instalar(config_base())
    body = escrever_issue(tmp_path, body=f"Descrição com {MARCADOR}\n")
    _execucao(m, config_base(), _task(body))
    _sync_com_comentario()
    valores = todos_os_valores(coletor)
    assert coletor.eventos(telemetry.EV_EXECUCAO) and coletor.eventos(telemetry.EV_SYNC_ITEM)
    assert [v for v in valores if MARCADOR in v] == []


def test_ct_priv_02_sem_tokens_ou_credenciais(isolamento, tmp_path):
    import src.__main__ as m

    config = _config_cred()
    coletor = instalar(config)
    body = escrever_issue(tmp_path)
    _execucao(m, config, _task(body))
    valores = todos_os_valores(coletor)
    assert [v for v in valores if TOKEN in v or "usuario" in v] == []
    assert coletor.port.resource_attributes["service.instance.id"] == \
        "https://github.com/acme/esteira-demo.git"


def test_ct_priv_03_userinfo_removido_do_instance_id(isolamento, monkeypatch):
    attrs = telemetry.resource_attributes(_config_cred())
    assert TOKEN not in attrs["service.instance.id"]
    assert attrs["service.instance.id"] == "https://github.com/acme/esteira-demo.git"
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES",
                       f"service.instance.id=https://u:{TOKEN}@host/x")
    assert TOKEN not in telemetry.resource_attributes(config_base())["service.instance.id"]


def test_ct_priv_04_mensagem_de_erro_sempre_sanitizada(isolamento):
    from src.core import sync
    from src.core.board import Board

    bruta = ("falha em .pipe/changeQueue.json com ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ "
             "Authorization: Bearer abc.def")
    coletor = instalar(config_base())

    def _boom(*_a, **_k):
        raise RuntimeError(bruta)

    with patch.object(sync, "_apply_change_up", side_effect=_boom):
        sync.apply_changes(Board(FakePort()), _fila(), {"boards": {"platform": "github"}})
    ev = coletor.eventos(telemetry.EV_SYNC_ITEM)[0]
    assert ev["esteira.erro.mensagem"] == sanitize_reason(bruta)
    assert "<arquivo interno>" in ev["esteira.erro.mensagem"]
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in ev["esteira.erro.mensagem"]
    assert [v for v in todos_os_valores(coletor) if "ghp_ABCDEFGHIJ" in v or "abc.def" in v] == []


def test_ct_priv_05_titulo_ausente_sem_opt_in(isolamento, tmp_path):
    import src.__main__ as m

    coletor = instalar(config_base())
    body = escrever_issue(tmp_path, titulo="Titulo Confidencial")
    _execucao(m, config_base(), _task(body))
    assert [v for v in todos_os_valores(coletor) if "Titulo Confidencial" in v] == []
    assert all("esteira.issue.titulo" not in e for e in coletor.eventos())
