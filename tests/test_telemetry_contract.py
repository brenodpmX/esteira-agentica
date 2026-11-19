import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("opentelemetry.sdk")

from src.core import composition, execution, execution_record, telemetry  # noqa: E402
from src.core.board import Board, BoardPort, ChangeItem, PenaltyException  # noqa: E402
from src.core.change_queue import ChangeQueue  # noqa: E402
from src.core.execution import ExecutionResult  # noqa: E402
from tests._telemetria_helpers import (BOARD_ID, COL_ID, config_base,  # noqa: E402,F401
                                       escrever_issue, escrever_snapshot, instalar,
                                       isolamento, issue_snapshot)

EXECUCAO_ATTRS = (
    "esteira.execucao.id", "esteira.ia.plataforma", "gen_ai.agent.id",
    "gen_ai.agent.name", "gen_ai.request.model", "esteira.board", "esteira.coluna",
    "esteira.issue", "esteira.issue.pai", "esteira.coluna.destino",
    "esteira.execucao.resultado", "esteira.execucao.avancou",
    "esteira.execucao.repeticao_sem_avanco", "esteira.execucao.classe",
    "esteira.execucao.origem", "esteira.execucao.tentativas", "esteira.execucao.sessao",
    "esteira.execucao.inicio", "esteira.execucao.fim", "esteira.execucao.duracao_s",
    "esteira.execucao.timeout_s", "esteira.consumo.disponivel", "esteira.consumo.valor",
    "esteira.consumo.unidade", "esteira.consumo.origem",
    "esteira.composicao.tokens_entrada", "esteira.composicao.caracteres_sempre_carregado",
    "esteira.board.plataforma",
)

OBSERVADOS: set = set()


@pytest.fixture(autouse=True)
def _registra_nomes(request):
    yield
    coletor = getattr(request.node, "_coletor", None)
    if coletor is not None:
        OBSERVADOS.update(coletor.nomes_eventos())


def _instalar(request):
    coletor = instalar(config_base())
    request.node._coletor = coletor
    return coletor


def _task(body, parent="7"):
    return {
        "board_id": BOARD_ID, "board": {"flow": "feature", "repo": "main"},
        "col_id": COL_ID,
        "column": {"name": "Desenvolvimento", "agent": "dev", "gitevents": "no-branch",
                   "target-prompt": "Execute", "change": {"advance": "execucao-testes"}},
        "issue": {"id": "42", "body_path": str(body), "parent": parent},
    }


def _medicao(prompt="PROMPT", tokens=1234):
    return composition.compose_measurement(
        execucao="42", adapter="fake", prompt_dinamico=prompt,
        contexto_sempre_carregado="steering " * 10,
        instrucoes_obrigatorias_carregadas=True, tokens_entrada=tokens,
    )


def _run(m, config, task, dispatch, medicao=None):
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record", return_value=medicao or _medicao()), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery", side_effect=dispatch):
        return m.call_agent(config, task)


def _dispatch_avanca(tmp_path, body, consumo):
    def _spy(config, adapter, params, board_id, col_id):
        dest = tmp_path / ".pipe" / "boards" / BOARD_ID / "execucao-testes"
        dest.mkdir(parents=True, exist_ok=True)
        Path(body).rename(dest / Path(body).name)
        return ExecutionResult(classe=execution.SUCEDIDO, origem="exit-code",
                               tentativas=1, consumo=consumo, sessao="retomada")
    return _spy


def test_ct_exec_01_evento_execucao_completo(isolamento, tmp_path, request):
    import src.__main__ as m

    coletor = _instalar(request)
    body = escrever_issue(tmp_path)
    consumo = execution_record.Consumo.reportado(3.5, "credit", "kiro-cli")
    _run(m, config_base(), _task(body), _dispatch_avanca(tmp_path, body, consumo))

    eventos = coletor.eventos(telemetry.EV_EXECUCAO)
    assert len(eventos) == 1
    ev = eventos[0]
    ausentes = [a for a in EXECUCAO_ATTRS if a not in ev]
    assert ausentes == []
    assert ev["esteira.execucao.resultado"] in execution_record.RESULTADOS
    assert ev["esteira.execucao.resultado"] == execution_record.CONCLUIDA
    assert ev["esteira.execucao.avancou"] is True
    assert ev["esteira.coluna.destino"] == "execucao-testes"
    assert ev["esteira.coluna"] == COL_ID
    assert ev["esteira.issue"] == "42"
    assert ev["esteira.issue.pai"] == "7"
    assert ev["esteira.execucao.sessao"] in ("nova", "retomada")
    assert ev["esteira.consumo.valor"] == 3.5
    assert ev["esteira.consumo.disponivel"] is True
    assert ev["esteira.composicao.tokens_entrada"] == 1234
    assert ev["esteira.composicao.caracteres_sempre_carregado"] == len("steering " * 10)
    assert ev["gen_ai.agent.id"] == "dev"
    assert ev["gen_ai.agent.name"] == "engineering"
    assert ev["gen_ai.request.model"] == "claude-sonnet-4"
    assert ev["esteira.ia.plataforma"] == "kiro-cli"
    assert ev["esteira.board.plataforma"] == "github"
    assert ev["esteira.execucao.duracao_s"] >= 0
    registros = execution_record.records_for_issue("42")
    assert ev["esteira.execucao.id"] == registros[0].execucao_id


def test_ct_exec_02_valor_ausente_com_consumo_indisponivel(isolamento, tmp_path, request):
    import src.__main__ as m

    coletor = _instalar(request)
    body = escrever_issue(tmp_path)
    consumo = execution_record.Consumo.indisponivel(origem="kiro-cli")
    _run(m, config_base(), _task(body), _dispatch_avanca(tmp_path, body, consumo))

    ev = coletor.eventos(telemetry.EV_EXECUCAO)[0]
    assert ev["esteira.consumo.disponivel"] is False
    assert "esteira.consumo.valor" not in ev
    assert ev["esteira.consumo.origem"] == "kiro-cli"


def test_ct_exec_execucao_com_excecao_ainda_emite(isolamento, tmp_path, request):
    import src.__main__ as m

    coletor = _instalar(request)
    body = escrever_issue(tmp_path)

    def _boom(*_a, **_k):
        raise RuntimeError("falha inesperada")

    with pytest.raises(RuntimeError):
        _run(m, config_base(), _task(body), _boom)
    ev = coletor.eventos(telemetry.EV_EXECUCAO)[0]
    assert ev["esteira.execucao.resultado"] == execution_record.DESCONHECIDA
    assert ev["error.type"] == "RuntimeError"


@pytest.mark.parametrize("opt_in", [None, "false", "true"])
def test_ct_exec_03_titulo_so_com_opt_in(isolamento, tmp_path, request, monkeypatch, opt_in):
    import src.__main__ as m

    if opt_in is not None:
        monkeypatch.setenv("ESTEIRA_TELEMETRIA_TITULO", opt_in)
    coletor = _instalar(request)
    body = escrever_issue(tmp_path, titulo="Titulo Secreto")
    _run(m, config_base(), _task(body),
         lambda *a, **k: ExecutionResult(classe=execution.SUCEDIDO))

    todos = coletor.eventos() + [dict(s.attributes) for s in coletor.spans()]
    if opt_in == "true":
        ev = coletor.eventos(telemetry.EV_EXECUCAO)[0]
        assert ev["esteira.issue.titulo"] == "Titulo Secreto"
    else:
        assert all("esteira.issue.titulo" not in a for a in todos)
        assert all("Titulo Secreto" not in str(v) for a in todos for v in a.values())


def _keep_task_cooldown(m, tmp_path):
    body = escrever_issue(tmp_path)
    escrever_snapshot(BOARD_ID, [issue_snapshot(body_path=body)])
    config = config_base()
    config["boards"]["rerun_cooldown"] = 300
    m._rerun_cache.clear()
    m._mark_rerun(BOARD_ID, COL_ID, "42")
    try:
        assert m.keep_task(BOARD_ID, config) is None
    finally:
        m._rerun_cache.clear()


def _limite_consumo(m, tmp_path):
    from src.core import consumption_limit as cl

    body = escrever_issue(tmp_path)
    config = config_base()
    config["agents"]["kiro-cli"]["limits"] = {"daily": {"limit": 1}}
    state = {"version": 1, "platforms": {"kiro-cli": {"unidade": "credit", "periods": {}}}}
    ts = time.time()
    start, _ = cl.period_bounds(cl.PeriodPolicy("daily", 1), cl._now_in(ts, None), None)
    state["platforms"]["kiro-cli"]["periods"]["daily"] = {"inicio": start.isoformat(),
                                                          "consumo": 5}
    Path(".pipe/consumptionLimit.json").write_text(json.dumps(state), encoding="utf-8")
    issue = {"id": "42", "body_path": str(body)}
    with patch.object(cl, "read_policy_from_disk",
                      side_effect=lambda c, p: cl.resolve_policy(config, p)):
        assert m._consumption_allows(config, {"repo": "main"}, BOARD_ID, COL_ID, issue,
                                     "dev") is False


def _circuit_break(m, tmp_path):
    body = escrever_issue(tmp_path)
    config = config_base(agent_circuit_break={"executions": 1, "window": 3600})
    m.board = MagicMock()
    m.board.list_comments.return_value = []
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record", return_value=_medicao()), \
         patch.object(m, "_dispatch_with_recovery",
                      return_value=ExecutionResult(classe=execution.SUCEDIDO)):
        m.call_agent(config, _task(body))
        assert m.call_agent(config, _task(body)) is None


def _composicao(m, tmp_path):
    body = escrever_issue(tmp_path)
    medicao = composition.compose_measurement(
        execucao="42", adapter="fake", prompt_dinamico="p", contexto_sempre_carregado="",
        instrucoes_obrigatorias_carregadas=False, motivo="steering ausente")
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record", return_value=medicao):
        assert m.call_agent(config_base(), _task(body)) is None


@pytest.mark.parametrize("motivo,provocar", [
    ("cooldown", _keep_task_cooldown),
    ("limite_consumo", _limite_consumo),
    ("circuit_break", _circuit_break),
    ("composicao_recusada", _composicao),
])
def test_ct_evt_01_admissao_negada(isolamento, tmp_path, request, motivo, provocar):
    import src.__main__ as m

    coletor = _instalar(request)
    provocar(m, tmp_path)
    eventos = coletor.eventos(telemetry.EV_ADMISSAO_NEGADA)
    assert eventos, motivo
    ev = eventos[-1]
    assert ev["esteira.admissao.motivo"] == motivo
    assert ev["esteira.board"] == BOARD_ID
    assert ev["esteira.coluna"] == COL_ID
    assert ev["esteira.issue"] == "42"
    assert ev["esteira.ia.plataforma"] == "kiro-cli"
    if motivo == "limite_consumo":
        assert ev["esteira.consumo.periodo"] == "diario"
    else:
        assert "esteira.consumo.periodo" not in ev


def test_ct_evt_02_circuit_break_passos(isolamento, request):
    from src.core.agent_circuit_break import CircuitBreaker, CircuitBreakPolicy

    coletor = _instalar(request)
    board = MagicMock()
    board.list_comments.return_value = []
    breaker = CircuitBreaker(CircuitBreakPolicy(active=True, executions=2, window=600), board)
    for _ in range(3):
        breaker.admit(BOARD_ID, COL_ID, "42", need_human_present=False)

    eventos = coletor.eventos(telemetry.EV_CIRCUIT_BREAK)
    assert [e["esteira.circuit_break.passo"] for e in eventos] == [
        "persisted", "labeled", "signaled"]
    for ev in eventos:
        assert ev["esteira.circuit_break.contagem"] == 2
        assert ev["esteira.circuit_break.limite"] == 2
        assert ev["esteira.circuit_break.janela_s"] == 600
        assert ev["esteira.coluna"] == COL_ID
        assert ev["esteira.issue"] == "42"


CONSUMO_ATTRS = ("esteira.ia.plataforma", "esteira.consumo.periodo", "esteira.consumo.tipo",
                 "esteira.consumo.acumulado", "esteira.consumo.limite",
                 "esteira.consumo.unidade", "esteira.consumo.periodo_inicio",
                 "esteira.consumo.periodo_fim")


def test_ct_evt_03_consumo_limite_quatro_fatos(isolamento, request):
    from src.core import consumption_limit as cl

    coletor = _instalar(request)
    policy = cl.LimitPolicy(active=True, periods={"daily": cl.PeriodPolicy("daily", 2)})
    clock = {"t": time.time()}
    limiter = cl.ConsumptionLimiter("inst", clock=lambda: clock["t"])

    limiter.record("kiro-cli", policy, execution_record.Consumo.reportado(3, "credit", "k"))
    assert limiter.admit("kiro-cli", policy).admitted is False
    limiter.record("kiro-cli", policy, execution_record.Consumo.reportado(1, "token", "k"))
    clock["t"] += 2 * 86400
    assert limiter.admit("kiro-cli", policy).admitted is True

    tipos = [e["esteira.consumo.tipo"] for e in coletor.eventos(telemetry.EV_CONSUMO_LIMITE)]
    assert set(tipos) == {"bloqueio", "unidade_divergente", "virada_periodo", "retomada"}
    for ev in coletor.eventos(telemetry.EV_CONSUMO_LIMITE):
        assert [a for a in CONSUMO_ATTRS if a not in ev] == []
        assert ev["esteira.consumo.periodo"] in ("diario", "semanal", "mensal")
    bloqueio = next(e for e in coletor.eventos(telemetry.EV_CONSUMO_LIMITE)
                    if e["esteira.consumo.tipo"] == "bloqueio")
    assert bloqueio["esteira.consumo.acumulado"] == 3
    assert bloqueio["esteira.consumo.limite"] == 2


class FakePort(BoardPort):
    def __init__(self, fail=None):
        self.fail = fail
        self.calls = []

    def connect(self, config):
        pass

    def sync_boards(self, boards):
        pass

    def list_issues(self, board_id):
        return []

    def get_issue(self, board_id, issue_id):
        return None

    def create_issue(self, board_id, title, body, column):
        return None

    def move_issue(self, board_id, issue_id, column, from_column=None):
        self.calls.append(("move_issue", issue_id, column))
        if self.fail:
            raise self.fail

    def update_issue(self, board_id, issue_id, title=None, body=None):
        pass

    def add_comment(self, board_id, issue_id, comment):
        pass

    def list_comments(self, board_id, issue_id):
        return []

    def close_issue(self, board_id, issue_id):
        pass


def _fila(event="change-up", issue_id="42", attempts=0):
    queue = ChangeQueue()
    item = ChangeItem.of(event, id=issue_id, board=BOARD_ID)
    item.attempts = attempts
    queue.add(item)
    return queue


def _apply(queue, port, config=None, max_attempts=3):
    from src.core import sync

    board = Board(port)

    def _change_up(board_id, item, board_obj, queue=None, config=None):
        board_obj.move_issue(board_id, item.id, "execucao-testes", from_column=COL_ID)

    config = config or {"boards": {"platform": "github"}, "sync": {"max_attempts": max_attempts}}
    with patch.object(sync, "_apply_change_up", side_effect=_change_up):
        return sync.apply_changes(board, queue, config)


SYNC_ATTRS = ("esteira.sync.uuid", "esteira.sync.evento", "esteira.sync.fullsync",
              "esteira.board", "esteira.issue", "esteira.sync.tentativa",
              "esteira.sync.desfecho", "esteira.sync.lag_s", "esteira.sync.duracao_s")


@pytest.mark.parametrize("fail,attempts,desfecho", [
    (None, 0, "aplicado"),
    (RuntimeError("timeout de rede ghp_ABCDEFGHIJKLMNOPQRSTUVWX"), 0, "reenfileirado"),
    (RuntimeError("Could not resolve to an issue or pull request"), 0, "dead_letter"),
])
def test_ct_evt_04_sync_item_desfechos(isolamento, request, fail, attempts, desfecho):
    from src.core.dead_letter import sanitize_reason

    coletor = _instalar(request)
    _apply(_fila(attempts=attempts), FakePort(fail))

    eventos = coletor.eventos(telemetry.EV_SYNC_ITEM)
    assert len(eventos) == 1
    ev = eventos[0]
    assert [a for a in SYNC_ATTRS if a not in ev] == []
    assert ev["esteira.sync.desfecho"] == desfecho
    assert ev["esteira.sync.evento"] == "change-up"
    assert ev["esteira.sync.tentativa"] == 1
    assert ev["esteira.sync.lag_s"] >= 0 and ev["esteira.sync.duracao_s"] >= 0
    if desfecho == "dead_letter":
        assert ev["esteira.sync.dead_letter.categoria"] == "definitivo"
    else:
        assert "esteira.sync.dead_letter.categoria" not in ev
    if fail is None:
        assert "error.type" not in ev and "esteira.erro.mensagem" not in ev
    else:
        assert ev["error.type"] == "RuntimeError"
        assert ev["esteira.erro.mensagem"] == sanitize_reason(str(fail))
        assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWX" not in ev["esteira.erro.mensagem"]


def test_ct_evt_04_dead_letter_por_tentativas_esgotadas(isolamento, request):
    coletor = _instalar(request)
    _apply(_fila(attempts=2), FakePort(RuntimeError("falha transitória")), max_attempts=3)
    ev = coletor.eventos(telemetry.EV_SYNC_ITEM)[0]
    assert ev["esteira.sync.desfecho"] == "dead_letter"
    assert ev["esteira.sync.dead_letter.categoria"] == "transitorio_esgotado"
    assert ev["esteira.sync.tentativa"] == 3


@pytest.mark.parametrize("fail,status", [
    (None, "ok"),
    (RuntimeError("erro"), "erro"),
    (PenaltyException(30), "rate_limit"),
])
def test_ct_evt_05_board_api(isolamento, request, fail, status):
    coletor = _instalar(request)
    _apply(_fila(), FakePort(fail))
    ev = coletor.eventos(telemetry.EV_BOARD_API)[0]
    assert ev["esteira.board.plataforma"] == "github"
    assert ev["esteira.board.operacao"] == "move_issue"
    assert ev["esteira.board"] == BOARD_ID
    assert ev["esteira.issue"] == "42"
    assert ev["esteira.board.duracao_s"] >= 0
    assert ev["esteira.board.status"] == status
    if fail is None:
        assert "error.type" not in ev
    else:
        assert ev["error.type"] == type(fail).__name__


def _github(tmp_path):
    from src.adapters.github_board import GitHubBoardAdapter

    adapter = GitHubBoardAdapter()
    adapter._throttle_file = str(tmp_path / "throttle")
    adapter._throttle_value = 2
    adapter._penalty_value = 1
    adapter._in_penalty = False
    adapter._penalty_ttl = None
    return adapter


def test_ct_evt_06_throttle_aumento_e_cooldown(isolamento, tmp_path, request):
    from datetime import datetime, timedelta

    coletor = _instalar(request)
    adapter = _github(tmp_path)
    adapter._throttle_hit()
    adapter._throttle_cooldown = datetime.now() - timedelta(seconds=1)
    with patch("src.adapters.github_board.time.sleep"):
        adapter._throttle()

    eventos = coletor.eventos(telemetry.EV_BOARD_THROTTLE)
    assert [(e["esteira.board.throttle.valor_anterior_s"],
             e["esteira.board.throttle.valor_novo_s"],
             e["esteira.board.throttle.motivo"]) for e in eventos] == [
        (2, 4, "aumento"), (4, 2, "cooldown")]
    assert all(e["esteira.board.plataforma"] == "github" for e in eventos)


def test_ct_evt_07_penalty_ativo_e_inativo(isolamento, tmp_path, request):
    from datetime import datetime, timedelta

    coletor = _instalar(request)
    adapter = _github(tmp_path)
    adapter._penalty_hit()
    adapter._penalty_ttl = datetime.now() - timedelta(seconds=1)
    adapter._penalty_check()

    ativo, inativo = coletor.eventos(telemetry.EV_BOARD_PENALTY)
    assert ativo["esteira.board.penalty.estado"] == "ativo"
    assert ativo["esteira.board.penalty.horas"] == 1
    assert "esteira.board.penalty.retorno_em" in ativo
    assert inativo["esteira.board.penalty.estado"] == "inativo"
    assert "esteira.board.penalty.horas" not in inativo
    assert "esteira.board.penalty.retorno_em" not in inativo


def test_ct_evt_08_sync_circuit_breaker_transicoes(isolamento, request):
    from src.core.sync_circuit_breaker import SyncCircuitBreaker

    coletor = _instalar(request)
    clock = {"t": 1000.0}
    config = {"boards": {"platform": "github"}, "sync": {"circuit_breaker": {
        "persistence": "memory",
        "issue": {"max_failures": 1, "block_duration": 10, "max_blocks": 5},
        "platform": {"max_blocked_issues": 1, "block_window": 600, "block_duration": 10},
        "half_open": {"success_threshold": 1},
    }}}
    breaker = SyncCircuitBreaker(config, clock=lambda: clock["t"])
    breaker.record_failure(BOARD_ID, "42", "erro")
    clock["t"] += 11
    assert breaker.platform_blocked("github") is False
    assert breaker.issue_blocked(BOARD_ID, "42") is False
    breaker.record_success(BOARD_ID, "42")

    eventos = coletor.eventos(telemetry.EV_SYNC_BREAKER)
    pares = {(e["esteira.breaker.escopo"], e["esteira.breaker.estado_anterior"],
              e["esteira.breaker.estado_novo"]) for e in eventos}
    for escopo in ("plataforma", "issue"):
        assert (escopo, "closed", "open") in pares
        assert (escopo, "open", "half_open") in pares
        assert (escopo, "half_open", "closed") in pares
    for ev in eventos:
        assert ev["esteira.board.plataforma"] == "github"
        if ev["esteira.breaker.escopo"] == "issue":
            assert ev["esteira.board"] == BOARD_ID and ev["esteira.issue"] == "42"
        else:
            assert "esteira.issue" not in ev and "esteira.board" not in ev


def test_ct_evt_09_escalacao(isolamento, request):
    coletor = _instalar(request)
    escalations = _apply(_fila(), FakePort(RuntimeError("HTTP 422: Validation Failed")))
    assert escalations
    ev = coletor.eventos(telemetry.EV_SYNC_ESCALACAO)[0]
    assert ev["esteira.board"] == BOARD_ID
    assert ev["esteira.issue"] == "42"
    assert ev["error.type"] == "RuntimeError"


UPSERT_ATTRS = ("esteira.board", "esteira.issue", "esteira.coluna", "esteira.issue.filhos",
                "esteira.issue.bloqueada_por", "esteira.issue.bloqueia",
                "esteira.issue.labels", "esteira.issue.estado", "esteira.issue.arquivada",
                "esteira.issue.origem")


def test_ct_evt_10_upsert_aplicado(isolamento, tmp_path, request):
    coletor = _instalar(request)
    escrever_snapshot(BOARD_ID, [issue_snapshot(parent="7", children=["8"],
                                                blocked_by=["9"], labels=["bug"])])
    _apply(_fila(), FakePort())
    ev = coletor.eventos(telemetry.EV_ISSUE_UPSERT)[0]
    assert [a for a in UPSERT_ATTRS if a not in ev] == []
    assert ev["esteira.issue.origem"] == "incremental"
    assert ev["esteira.issue.pai"] == "7"
    assert list(ev["esteira.issue.filhos"]) == ["8"]
    assert list(ev["esteira.issue.bloqueada_por"]) == ["9"]
    assert list(ev["esteira.issue.bloqueia"]) == []
    assert list(ev["esteira.issue.labels"]) == ["bug"]
    assert ev["esteira.issue.estado"] in ("open", "closed")
    assert ev["esteira.issue.arquivada"] is False


def test_ct_evt_10_upsert_snapshot_completo_diario(isolamento, request):
    import datetime as dt

    import src.__main__ as m

    coletor = _instalar(request)
    escrever_snapshot(BOARD_ID, [issue_snapshot("42"), issue_snapshot("43", state="closed")])
    m._telemetry_state["snapshot_day"] = None
    hoje = dt.date(2026, 11, 20)
    assert m.emit_daily_snapshot(config_base(), today=hoje) is True
    assert m.emit_daily_snapshot(config_base(), today=hoje) is False
    assert m.emit_daily_snapshot(config_base(), today=hoje + dt.timedelta(days=1)) is True
    eventos = coletor.eventos(telemetry.EV_ISSUE_UPSERT)
    assert len(eventos) == 4
    assert {e["esteira.issue.origem"] for e in eventos} == {"full_sync"}
    assert {e["esteira.issue"] for e in eventos} == {"42", "43"}
    m._telemetry_state["snapshot_day"] = None


def test_ct_evt_11_transicao(isolamento, request):
    from src.core import sync

    coletor = _instalar(request)
    sync._emit_transicao(BOARD_ID, "42", COL_ID, "execucao-testes")
    sync._emit_transicao(BOARD_ID, "42", COL_ID, COL_ID)
    eventos = coletor.eventos(telemetry.EV_ISSUE_TRANSICAO)
    assert len(eventos) == 1
    assert eventos[0]["esteira.coluna.de"] == COL_ID
    assert eventos[0]["esteira.coluna.para"] == "execucao-testes"
    assert eventos[0]["esteira.board"] == BOARD_ID and eventos[0]["esteira.issue"] == "42"


def test_ct_evt_11_transicao_no_change_up_real(isolamento, tmp_path, request):
    from src.core import sync

    coletor = _instalar(request)
    dest = escrever_issue(tmp_path, col_id="execucao-testes")
    escrever_snapshot(BOARD_ID, [issue_snapshot(body_path=dest)])
    port = MagicMock(spec=BoardPort)
    port.list_comments.return_value = []
    config = config_base()
    config["boards"][BOARD_ID]["columns"]["execucao-testes"]["on_in"] = []
    item = ChangeItem.of("change-up", id="42", board=BOARD_ID)
    with patch.object(Board, "apply_commands", return_value={}):
        sync._apply_change_up(BOARD_ID, item, Board(port), None, config)
    ev = coletor.eventos(telemetry.EV_ISSUE_TRANSICAO)[0]
    assert (ev["esteira.coluna.de"], ev["esteira.coluna.para"]) == (COL_ID, "execucao-testes")


def test_ct_evt_12_ciclo(isolamento, request):
    import src.__main__ as m

    coletor = _instalar(request)
    m.emit_cycle(time.monotonic() - 0.5, True, 0.2)
    ev = coletor.eventos(telemetry.EV_PIPE_CICLO)[0]
    assert ev["esteira.ciclo.duracao_s"] >= 0
    assert ev["esteira.ciclo.houve_mudanca"] is True
    assert ev["esteira.ciclo.dormiu_s"] == 0.2


def test_ct_evt_12_ciclo_no_loop_real(isolamento, request):
    import src.__main__ as m

    coletor = _instalar(request)
    config = config_base()
    calls = {"n": 0}

    def _keep(board_id, cfg):
        calls["n"] += 1
        if calls["n"] > 1:
            raise KeyboardInterrupt
        return None

    with patch.object(m, "check_config", return_value=config), \
         patch.object(m, "setup_telemetry"), \
         patch.object(m, "InstanceLock"), patch.object(m, "startup"), \
         patch.dict(m.ADAPTERS, {"github": MagicMock()}), patch.object(m, "Board"), \
         patch("src.core.agent_circuit_break.check_label_capability"), \
         patch.object(m, "board_startup_sync"), \
         patch.object(m, "detect_local_all", return_value=False), \
         patch.object(m, "sync_remote_board", return_value=False), \
         patch.object(m, "process_queue", return_value=[]), \
         patch.object(m, "keep_task", side_effect=_keep), \
         patch.object(m, "sleep_time", return_value=60), \
         patch.object(m, "shutdown_telemetry"), \
         patch("signal.signal"), patch("builtins.print"):
        m.main()
    ciclos = coletor.eventos(telemetry.EV_PIPE_CICLO)
    assert len(ciclos) == 2
    assert ciclos[0]["esteira.ciclo.dormiu_s"] == 60
    assert ciclos[0]["esteira.ciclo.houve_mudanca"] is False


def test_ct_evt_13_ciclo_vida(isolamento, request):
    import src.__main__ as m

    coletor = _instalar(request)
    m._telemetry_state["revision"] = None
    with patch.object(m.participation, "_resolve_commit", return_value="abc123"):
        m.emit_lifecycle("startup")
        m.emit_lifecycle("shutdown")
    eventos = coletor.eventos(telemetry.EV_PIPE_CICLO_VIDA)
    assert [e["esteira.pipe.fase"] for e in eventos] == ["startup", "shutdown"]
    assert {e["vcs.ref.head.revision"] for e in eventos} == {"abc123"}
    m._telemetry_state["revision"] = None


def test_ct_evt_14_incidente_lock_recusado(isolamento, request):
    import src.__main__ as m
    from src.core.lock import LockHeldError

    coletor = _instalar(request)
    lock = MagicMock()
    lock.acquire.side_effect = LockHeldError(Path(".pipe/pipe.lock"), 123, "agora")
    with patch.object(m, "check_config", return_value=config_base()), \
         patch.object(m, "setup_telemetry"), patch.object(m, "shutdown_telemetry"), \
         patch.object(m, "InstanceLock", return_value=lock), patch("builtins.print"):
        with pytest.raises(SystemExit):
            m.main()
    ev = coletor.eventos(telemetry.EV_PIPE_INCIDENTE)[0]
    assert ev["esteira.incidente.tipo"] == "instance_lock_recusado"
    assert "esteira.issue" not in ev


def test_ct_evt_14_incidente_steering_reescrito(isolamento, tmp_path, request):
    import src.__main__ as m

    coletor = _instalar(request)
    body = escrever_issue(tmp_path)
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=True), \
         patch.object(m, "compose_execution_record", return_value=_medicao()), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery",
                      return_value=ExecutionResult(classe=execution.SUCEDIDO)):
        m.call_agent(config_base(), _task(body))
    ev = coletor.eventos(telemetry.EV_PIPE_INCIDENTE)[0]
    assert ev["esteira.incidente.tipo"] == "steering_reescrito"
    assert ev["esteira.board"] == BOARD_ID and ev["esteira.issue"] == "42"


def test_ct_evt_14_incidente_snapshot_restaurado(isolamento, request):
    from src.core.snapshot import SnapshotGuard

    coletor = _instalar(request)
    escrever_snapshot(BOARD_ID, [])
    with SnapshotGuard(BOARD_ID):
        Path(f".pipe/boards/{BOARD_ID}/snapshot.json").write_text("{}", encoding="utf-8")
    ev = coletor.eventos(telemetry.EV_PIPE_INCIDENTE)[0]
    assert ev["esteira.incidente.tipo"] == "snapshot_restaurado"
    assert ev["esteira.board"] == BOARD_ID


def test_ct_evt_14_incidente_arquivo_fantasma(isolamento, request):
    from src.core.agent_guard import fix_phantom_files

    coletor = _instalar(request)
    col = Path(f".pipe/boards/{BOARD_ID}/{COL_ID}")
    col.mkdir(parents=True)
    (col / "99-nova-body.md").write_text("# Nova\n", encoding="utf-8")
    fix_phantom_files(BOARD_ID, COL_ID, set())
    ev = coletor.eventos(telemetry.EV_PIPE_INCIDENTE)[0]
    assert ev["esteira.incidente.tipo"] == "arquivo_fantasma"


def test_ct_evt_14_incidente_registro_execucao_falha(isolamento, tmp_path, request):
    import src.__main__ as m

    coletor = _instalar(request)
    body = escrever_issue(tmp_path)
    with patch.object(execution_record, "record_from_execution_result",
                      side_effect=execution_record.ExecutionRecordStoreError("disco")):
        _run(m, config_base(), _task(body),
             lambda *a, **k: ExecutionResult(classe=execution.SUCEDIDO))
    tipos = [e["esteira.incidente.tipo"] for e in coletor.eventos(telemetry.EV_PIPE_INCIDENTE)]
    assert "registro_execucao_falha" in tipos
    assert coletor.eventos(telemetry.EV_EXECUCAO)


def test_ct_evt_14_incidente_preflight(isolamento, request):
    from src.core import preflight

    coletor = _instalar(request)
    with patch.object(preflight, "_check_ssh", return_value=(False, "x")), \
         patch.object(preflight, "_check_gh", return_value=(True, "y")), \
         patch.object(preflight, "_check_kiro", return_value=(True, "z")):
        with pytest.raises(SystemExit):
            preflight.preflight()
    ev = coletor.eventos(telemetry.EV_PIPE_INCIDENTE)[0]
    assert ev["esteira.incidente.tipo"] == "preflight_falha"


def test_ct_evt_14_incidente_cross_board(isolamento, request):
    from src.core.participation_reconcile import event_cross_board_link_blocked

    coletor = _instalar(request)
    event_cross_board_link_blocked("7", "42", "outro", BOARD_ID, None)
    ev = coletor.eventos(telemetry.EV_PIPE_INCIDENTE)[0]
    assert ev["esteira.incidente.tipo"] == "cross_board_bloqueado"
    assert ev["esteira.board"] == BOARD_ID and ev["esteira.issue"] == "42"


def test_ct_evt_enum_nomes_pertencem_ao_contrato():
    assert len(telemetry.EVENTOS) == 15
    assert len(set(telemetry.EVENTOS)) == 15
    assert all(n.startswith("esteira.") for n in telemetry.EVENTOS)
    assert set(telemetry.INCIDENTES) == {
        "instance_lock_recusado", "preflight_falha", "steering_reescrito",
        "snapshot_restaurado", "arquivo_fantasma", "cross_board_bloqueado",
        "registro_execucao_falha"}
    fora = {n for n in OBSERVADOS if n not in telemetry.EVENTOS}
    assert fora == set()
