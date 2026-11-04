import io
import json
from pathlib import Path

import pytest

from src.core.board import Board, BoardPort, ChangeItem, Issue, PenaltyException, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.log import log
from src.core.snapshot import Snapshot
from src.core import sync_circuit_breaker as scb
from src.core.sync import apply_changes
from src.core.sync_circuit_breaker import (
    SyncCircuitBreaker, SyncCircuitBreakerFatal, SyncEscalation,
)

BOARD = "entrega"
ISSUE = "42"


class Clock:
    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakePort(BoardPort):
    def __init__(self):
        self.error = None
        self.calls = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def get_issue(self, board_id, issue_id):
        self.calls.append(issue_id)
        if self.error is not None:
            raise self.error
        return None
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass
    def reopen_issue(self, board_id, issue_id): pass
    def set_labels(self, board_id, issue_id, labels): pass
    def add_label(self, board_id, issue_id, label): pass
    def remove_label(self, board_id, issue_id, label): pass
    def set_parent(self, board_id, issue_id, parent_id, known_current=None): pass
    def set_children(self, board_id, issue_id, children_ids, known_current=None): pass
    def set_blocked_by(self, board_id, issue_id, blocker_ids, known_current=None): pass
    def set_blocks(self, board_id, issue_id, blocked_ids, known_current=None): pass
    def archive_issue(self, board_id, issue_id): pass
    def unarchive_issue(self, board_id, issue_id): pass


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scb.reset_memory_state()
    yield
    scb.reset_memory_state()


@pytest.fixture(autouse=True)
def log_buffer():
    original = log._file
    buffer = io.StringIO()
    log._file = buffer
    yield buffer
    log._file = original


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def port():
    return FakePort()


def make_config(**overrides) -> dict:
    cb = {
        "persistence": "file",
        "issue": {"max_failures": 3, "block_duration": 300, "max_blocks": 3},
        "platform": {"max_blocked_issues": 5, "block_window": 600,
                     "block_duration": 900},
        "half_open": {"success_threshold": 2},
    }
    cb.update(overrides)
    return {"boards": {"platform": "github"}, "sync": {"circuit_breaker": cb}}


def seed(issue_ids=(ISSUE,)):
    snap = Snapshot(BOARD).load()
    for issue_id in issue_ids:
        snap.issues.append({"id": issue_id, "column": "x", "status": "ok"})
    snap.save()


def enqueue(issue_id=ISSUE):
    ChangeQueue().add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id=issue_id, board=BOARD))


def cycle(port, config, clock, issue_ids=(ISSUE,), breaker=None):
    breaker = breaker or SyncCircuitBreaker(config, clock=clock)
    for issue_id in issue_ids:
        enqueue(issue_id)
    return apply_changes(Board(port), ChangeQueue(), config, breaker=breaker)


def read_events(name: str) -> list[str]:
    return [l for l in log._file.getvalue().splitlines() if name in l]


def block_issue(port, config, clock, issue_ids=(ISSUE,), failures=3):
    port.error = Exception("timeout de rede")
    for _ in range(failures):
        cycle(port, config, clock, issue_ids)


class TestIssueBlock:
    def test_ct01_bloqueia_apos_max_failures(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")

        cycle(port, config, clock, breaker=breaker)
        cycle(port, config, clock, breaker=breaker)
        assert not breaker.issue_blocked(BOARD, ISSUE)
        cycle(port, config, clock, breaker=breaker)

        assert breaker.issue_blocked(BOARD, ISSUE)
        assert ChangeQueue().size() == 1

    def test_ct02_issue_bloqueada_retem_item_sem_reprocessar(self, port, clock):
        config = make_config()
        seed((ISSUE, "43"))
        breaker = SyncCircuitBreaker(config, clock=clock)
        block_issue(port, config, clock)
        calls_before = len(port.calls)

        port.error = None
        cycle(port, config, clock, issue_ids=(ISSUE, "43"), breaker=breaker)

        assert port.calls[calls_before:] == ["43"]
        items = ChangeQueue().items()
        assert [i.id for i in items] == [ISSUE]

    def test_ct19_borda_da_duracao_do_bloqueio(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        block_issue(port, config, clock)
        clock.advance(299)
        assert breaker.issue_blocked(BOARD, ISSUE)
        clock.advance(1)
        assert not breaker.issue_blocked(BOARD, ISSUE)

    def test_duracao_vem_da_configuracao(self, port, clock):
        config = make_config(issue={"max_failures": 1, "block_duration": 10,
                                    "max_blocks": 9})
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        cycle(port, config, clock, breaker=breaker)
        assert breaker.issue_blocked(BOARD, ISSUE)
        clock.advance(10)
        assert not breaker.issue_blocked(BOARD, ISSUE)

    def test_log_de_bloqueio_tem_campos_minimos(self, port, clock):
        config = make_config()
        seed()
        block_issue(port, config, clock)
        events = read_events("sync_circuit_breaker_issue_blocked")
        assert events
        for field in ("board", "issue", "falhas_consecutivas", "bloqueado_ate"):
            assert field in events[-1]


class TestHalfOpen:
    def test_ct03_expiracao_leva_a_meio_aberto_e_retenta(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        block_issue(port, config, clock)
        clock.advance(300)
        port.error = None
        calls_before = len(port.calls)

        cycle(port, config, clock, breaker=breaker)

        assert len(port.calls) == calls_before + 1
        events = read_events("sync_circuit_breaker_transition")
        assert any("half_open" in e for e in events)

    def test_ct04_amostra_de_sucessos_fecha_o_circuito(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        block_issue(port, config, clock)
        clock.advance(300)
        port.error = None

        cycle(port, config, clock, breaker=breaker)
        state = json.loads(scb.STATE_FILE.read_text(encoding="utf-8"))
        assert state["issues"][f"{BOARD}/{ISSUE}"]["state"] == scb.HALF_OPEN

        cycle(port, config, clock, breaker=breaker)
        state = json.loads(scb.STATE_FILE.read_text(encoding="utf-8"))
        assert f"{BOARD}/{ISSUE}" not in state["issues"]

    def test_success_threshold_vem_da_configuracao(self, port, clock):
        config = make_config(half_open={"success_threshold": 1})
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        block_issue(port, config, clock)
        clock.advance(300)
        port.error = None
        cycle(port, config, clock, breaker=breaker)
        state = json.loads(scb.STATE_FILE.read_text(encoding="utf-8"))
        assert f"{BOARD}/{ISSUE}" not in state["issues"]

    def test_ct05_falha_em_meio_aberto_reabre_o_bloqueio(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        block_issue(port, config, clock)
        clock.advance(300)

        cycle(port, config, clock, breaker=breaker)

        assert breaker.issue_blocked(BOARD, ISSUE)
        clock.advance(299)
        assert breaker.issue_blocked(BOARD, ISSUE)
        clock.advance(1)
        assert not breaker.issue_blocked(BOARD, ISSUE)


class TestPlatformBlock:
    def test_ct06_bloqueia_plataforma_com_issues_distintas(self, port, clock):
        config = make_config(platform={"max_blocked_issues": 3, "block_window": 600,
                                       "block_duration": 900})
        ids = ("1", "2", "3")
        seed(ids)
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        for _ in range(3):
            cycle(port, config, clock, issue_ids=ids, breaker=breaker)

        assert breaker.platform_blocked("github")
        events = read_events("sync_circuit_breaker_platform_blocked")
        assert events
        for field in ("issues_bloqueadas", "janela", "bloqueado_ate"):
            assert field in events[-1]

    def test_mesma_issue_reaberta_conta_como_uma(self, port, clock):
        config = make_config(
            issue={"max_failures": 1, "block_duration": 10, "max_blocks": 99},
            platform={"max_blocked_issues": 2, "block_window": 600,
                      "block_duration": 900},
        )
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        for _ in range(3):
            cycle(port, config, clock, breaker=breaker)
            clock.advance(10)
        assert not breaker.platform_blocked("github")

    def test_issues_fora_da_janela_nao_contam(self, port, clock):
        config = make_config(
            issue={"max_failures": 1, "block_duration": 1000, "max_blocks": 99},
            platform={"max_blocked_issues": 2, "block_window": 60,
                      "block_duration": 900},
        )
        seed(("1", "2"))
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        cycle(port, config, clock, issue_ids=("1",), breaker=breaker)
        clock.advance(60)
        cycle(port, config, clock, issue_ids=("2",), breaker=breaker)
        assert not breaker.platform_blocked("github")

    def test_ct07_plataforma_bloqueada_nao_processa_fila(self, port, clock):
        config = make_config(platform={"max_blocked_issues": 1, "block_window": 600,
                                       "block_duration": 900})
        seed(("1", "2"))
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        for _ in range(3):
            cycle(port, config, clock, issue_ids=("1",), breaker=breaker)
        assert breaker.platform_blocked("github")
        calls_before = len(port.calls)

        port.error = None
        cycle(port, config, clock, issue_ids=("2",), breaker=breaker)

        assert len(port.calls) == calls_before
        assert ChangeQueue().size() == 2

    def test_plataforma_meio_aberta_fecha_com_sucessos(self, port, clock):
        config = make_config(platform={"max_blocked_issues": 1, "block_window": 600,
                                       "block_duration": 900})
        seed(("1", "2"))
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        for _ in range(3):
            cycle(port, config, clock, issue_ids=("1",), breaker=breaker)
        clock.advance(900)
        port.error = None
        assert not breaker.platform_blocked("github")
        cycle(port, config, clock, issue_ids=("2",), breaker=breaker)
        cycle(port, config, clock, issue_ids=("2",), breaker=breaker)
        state = json.loads(scb.STATE_FILE.read_text(encoding="utf-8"))
        assert state["platforms"]["github"]["state"] == scb.CLOSED

    def test_ct20_plataformas_distintas_sao_independentes(self, clock):
        config = make_config(platform={"max_blocked_issues": 1, "block_window": 600,
                                       "block_duration": 900})
        breaker = SyncCircuitBreaker(config, clock=clock)
        for _ in range(3):
            breaker.record_failure(BOARD, ISSUE, "erro", platform="A")
        assert breaker.platform_blocked("A")
        assert not breaker.platform_blocked("B")


class TestEscalation:
    def escalate(self, port, config, clock, breaker):
        port.error = Exception("timeout de rede")
        escalations = []
        for _ in range(9):
            escalations += cycle(port, config, clock, breaker=breaker)
            clock.advance(300)
        return escalations

    def test_ct08_escala_uma_vez_apos_max_blocks(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        escalations = []
        for _ in range(9):
            result = cycle(port, config, clock, breaker=breaker)
            escalations += result
            if result:
                break
            clock.advance(300)

        assert len(escalations) == 1
        esc = escalations[0]
        assert isinstance(esc, SyncEscalation)
        assert (esc.board_id, esc.issue_id, esc.blocks) == (BOARD, ISSUE, 3)
        assert esc.agent_id == scb.DEFAULT_ESCALATION_AGENT
        assert "timeout de rede" in esc.error_log
        events = read_events("sync_circuit_breaker_escalation")
        assert len(events) == 1
        for field in ("board", "issue", "agente_dedicado", "bloqueios_consecutivos"):
            assert field in events[0]

    def test_agente_dedicado_vem_da_configuracao(self, port, clock):
        config = make_config(escalation_agent="corretor")
        breaker = SyncCircuitBreaker(config, clock=clock)
        esc = breaker.record_failure(BOARD, ISSUE, "422", correctable=True)
        assert esc.agent_id == "corretor"

    def test_ct09_sync_e_retentado_no_ciclo_seguinte(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        for _ in range(9):
            if cycle(port, config, clock, breaker=breaker):
                break
            clock.advance(300)
        assert not breaker.issue_blocked(BOARD, ISSUE)
        port.error = None
        calls_before = len(port.calls)

        result = apply_changes(Board(port), ChangeQueue(), config, breaker=breaker)

        assert result == []
        assert len(port.calls) == calls_before + 1

    def test_ct10_falha_apos_correcao_encerra(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        for _ in range(9):
            if cycle(port, config, clock, breaker=breaker):
                break
            clock.advance(300)

        with pytest.raises(SyncCircuitBreakerFatal) as info:
            apply_changes(Board(port), ChangeQueue(), config, breaker=breaker)

        assert info.value.board_id == BOARD
        assert info.value.issue_id == ISSUE
        assert info.value.agent_id == scb.DEFAULT_ESCALATION_AGENT

    def test_ct11_registro_do_encerramento_completo(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        for _ in range(9):
            if cycle(port, config, clock, breaker=breaker):
                break
            clock.advance(300)
        with pytest.raises(SyncCircuitBreakerFatal):
            apply_changes(Board(port), ChangeQueue(), config, breaker=breaker)

        line = read_events("sync_circuit_breaker_fatal")[-1]
        for field in ("board", "issue", "erro", "tentativas", "agente_que_corrigiu"):
            assert field in line
        assert scb.DEFAULT_ESCALATION_AGENT in line

    def test_ct08b_sem_segunda_escalacao_no_mesmo_episodio(self, clock):
        breaker = SyncCircuitBreaker(make_config(), clock=clock)
        assert breaker.record_failure(BOARD, ISSUE, "422", correctable=True)
        with pytest.raises(SyncCircuitBreakerFatal):
            breaker.record_failure(BOARD, ISSUE, "422", correctable=True)

    def test_sucesso_apos_correcao_fecha_e_zera_episodio(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        breaker.record_failure(BOARD, ISSUE, "422", correctable=True)
        breaker.record_success(BOARD, ISSUE)
        breaker.record_success(BOARD, ISSUE)
        assert breaker.record_failure(BOARD, ISSUE, "422", correctable=True)


class TestRateLimit:
    def test_ct15_rate_limit_nao_incrementa_contadores(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = PenaltyException(10)
        for _ in range(5):
            cycle(port, config, clock, breaker=breaker)

        assert not breaker.issue_blocked(BOARD, ISSUE)
        assert not scb.STATE_FILE.exists()

    def test_ct16_rate_limit_intercalado_nao_acelera_bloqueio(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        sequence = [Exception("timeout"), PenaltyException(1), Exception("timeout"),
                    PenaltyException(1), Exception("timeout")]
        blocked_after = []
        for exc in sequence:
            port.error = exc
            cycle(port, config, clock, breaker=breaker)
            blocked_after.append(breaker.issue_blocked(BOARD, ISSUE))
        assert blocked_after == [False, False, False, False, True]


class TestE4Absorbed:
    def test_ct18_erro_corrigivel_escala_pelo_circuit_breaker(self, port, clock):
        config = make_config()
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("HTTP 422: Validation Failed")

        first = cycle(port, config, clock, breaker=breaker)

        assert len(first) == 1
        assert first[0].agent_id == scb.DEFAULT_ESCALATION_AGENT
        assert "Validation Failed" in first[0].error_log
        assert ChangeQueue().size() == 1
        with pytest.raises(SyncCircuitBreakerFatal):
            cycle(port, config, clock, breaker=breaker)

    def test_mecanismo_antigo_foi_removido(self):
        import src.__main__ as main
        from src.core import sync
        for name in ("RemediationSignal", "RemediationFailStop"):
            assert not hasattr(sync, name)
        for name in ("remediate_pending", "_remediated_targets",
                     "_remediation_fail_stop"):
            assert not hasattr(main, name)


class TestMaxAttemptsInteraction:
    def test_dead_letter_por_max_attempts_libera_o_contador(self, port, clock):
        config = make_config()
        config["sync"]["max_attempts"] = 2
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        cycle(port, config, clock, breaker=breaker)
        cycle(port, config, clock, breaker=breaker)

        assert ChangeQueue().size() == 0
        state = json.loads(scb.STATE_FILE.read_text(encoding="utf-8"))
        assert f"{BOARD}/{ISSUE}" not in state["issues"]

    def test_bloqueio_reinicia_tentativas_do_item(self, port, clock):
        config = make_config()
        seed()
        block_issue(port, config, clock)
        assert ChangeQueue().getNext().attempts == 0


class TestPersistence:
    def test_ct22_memory_nao_sobrevive_a_reinicio(self, port, clock):
        config = make_config(persistence="memory")
        seed()
        breaker = SyncCircuitBreaker(config, clock=clock)
        port.error = Exception("timeout de rede")
        cycle(port, config, clock, breaker=breaker)
        cycle(port, config, clock, breaker=breaker)
        assert not scb.STATE_FILE.exists()

        scb.reset_memory_state()
        cycle(port, config, clock, breaker=SyncCircuitBreaker(config, clock=clock))
        assert not SyncCircuitBreaker(config, clock=clock).issue_blocked(BOARD, ISSUE)

    def test_ct22_file_sobrevive_a_reinicio(self, port, clock):
        config = make_config(persistence="file")
        seed()
        port.error = Exception("timeout de rede")
        cycle(port, config, clock, breaker=SyncCircuitBreaker(config, clock=clock))
        cycle(port, config, clock, breaker=SyncCircuitBreaker(config, clock=clock))
        cycle(port, config, clock, breaker=SyncCircuitBreaker(config, clock=clock))
        assert SyncCircuitBreaker(config, clock=clock).issue_blocked(BOARD, ISSUE)

    def test_estado_corrompido_reinicia_sem_derrubar(self, clock):
        scb.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        scb.STATE_FILE.write_text("{nao e json", encoding="utf-8")
        breaker = SyncCircuitBreaker(make_config(), clock=clock)
        assert not breaker.issue_blocked(BOARD, ISSUE)

    def test_ct21_estado_nao_expoe_conteudo_e_arquivo_e_protegido(self, port, clock):
        from src.core.agent import PROTECTED_PATHS, build_sync_escalation_prompt
        config = make_config()
        seed()
        port.error = Exception("falha CORPO_SECRETO_456")
        for _ in range(3):
            cycle(port, config, clock)
        assert "CORPO_SECRETO_456" not in scb.STATE_FILE.read_text(encoding="utf-8")
        assert ".pipe/syncCircuitBreaker.json" in PROTECTED_PATHS

        task = {"board_id": BOARD, "issue": {"id": ISSUE, "body_path": "x-body.md"}}
        prompt = build_sync_escalation_prompt(
            config, task, "erro lendo .pipe/syncCircuitBreaker.json agora")
        assert "syncCircuitBreaker.json" not in prompt


class TestEscalationPrompt:
    def test_contem_fato_log_e_instrucao(self):
        from src.core.agent import build_sync_escalation_prompt
        task = {"board_id": BOARD, "issue": {"id": ISSUE, "body_path": "a-body.md"}}
        prompt = build_sync_escalation_prompt({}, task, "Traceback LOG_COMPLETO_XYZ")
        assert "falhou" in prompt
        assert "LOG_COMPLETO_XYZ" in prompt
        assert "Corrija a issue para que ela consiga sincronizar" in prompt
        assert "a-body.md" in prompt


class TestProgressoGravadoEmFalha:
    def test_ct14_body_mtime_gravado_antes_de_propagar(self, tmp_path):
        from src.core.sync import _apply_change_up

        body = Path(".pipe/boards/entrega/x/42-titulo-body.md")
        body.parent.mkdir(parents=True)
        body.write_text("# Titulo\n\ncorpo\n", encoding="utf-8")
        snap = Snapshot(BOARD).load()
        snap.issues.append({"id": ISSUE, "column": "x", "status": "ok",
                            "body_path": str(body), "body_mtime": "0"})
        snap.save()

        board = Board(FakePort())

        def boom(*a, **k):
            raise Exception("falha ao aplicar comando")

        board.apply_commands = boom
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id=ISSUE, board=BOARD)

        with pytest.raises(Exception, match="falha ao aplicar comando"):
            _apply_change_up(BOARD, item, board, None, {})

        saved = Snapshot(BOARD).load().issue(ISSUE)
        assert saved["body_mtime"] == str(body.stat().st_mtime)


class TestDescidaCompleta:
    def test_ct12_get_issue_nao_tem_modo_parcial(self):
        import inspect
        from src.adapters.github_board import GitHubBoardAdapter
        for cls in (BoardPort, GitHubBoardAdapter, Board):
            assert "fullsync" not in inspect.signature(cls.get_issue).parameters

    def test_ct12_apply_down_busca_issue_sem_flag(self, port):
        seed()
        item = ChangeItem.of(SyncEvent.CHANGE_DOWN, id=ISSUE, board=BOARD,
                             fullsync=False)
        ChangeQueue().add(item)
        apply_changes(Board(port), ChangeQueue(), {})
        assert port.calls == [ISSUE]


class TestRelacaoExistente:
    def adapter(self):
        from src.adapters.github_board import GitHubBoardAdapter
        adapter = GitHubBoardAdapter.__new__(GitHubBoardAdapter)
        adapter._repo = "o/r"
        adapter._throttle_value = 0
        adapter._penalty_check = lambda: None
        adapter._get_issue_db_id = lambda n: int(n) + 1000
        return adapter

    def test_ct13_relacao_existente_e_sucesso_e_continua(self):
        adapter = self.adapter()
        posted = []

        def api(method, path, **fields):
            posted.append(fields["issue_id"])
            if fields["issue_id"] == 1010:
                raise Exception("HTTP 422: Issue already has this dependency")
            return ""

        adapter._api = api
        adapter.set_blocked_by("b", "5", ["10", "20"], known_current=[])

        assert sorted(posted) == [1010, 1020]

    def test_outros_erros_continuam_propagando(self):
        adapter = self.adapter()

        def api(method, path, **fields):
            raise Exception("HTTP 500: server error")

        adapter._api = api
        with pytest.raises(Exception, match="500"):
            adapter.set_blocked_by("b", "5", ["10"], known_current=[])

    def test_set_blocks_relacao_existente_e_sucesso(self):
        adapter = self.adapter()
        posted = []

        def api(method, path, **fields):
            posted.append(path)
            if "/issues/10/" in path:
                raise Exception("422 Validation Failed: dependency already exists")
            return ""

        adapter._api = api
        adapter.set_blocks("b", "5", ["10", "20"], known_current=[])
        assert len(posted) == 2


class TestFatalNoMain:
    def test_fatal_encerra_com_codigo_diferente_de_zero(self, monkeypatch):
        import src.__main__ as m

        config = {"sleep": 1, "boards": {"platform": "github"}}

        def fatal(cfg):
            raise SyncCircuitBreakerFatal(BOARD, ISSUE, "erro", 4, "agente")

        monkeypatch.setattr(m, "check_config", lambda: config)
        monkeypatch.setattr(m, "startup", lambda cfg: None)
        monkeypatch.setattr(m, "board_startup_sync", lambda cfg: None)
        monkeypatch.setattr(m, "get_board_ids", lambda cfg: [BOARD])
        monkeypatch.setattr(m, "detect_local_all", lambda cfg: False)
        monkeypatch.setattr(m, "sync_remote_board", lambda b, c=None: False)
        monkeypatch.setattr(m, "process_queue", fatal)
        monkeypatch.setattr(m.time, "sleep", lambda *_: None)
        Path(".pipe").mkdir()

        class FakeBoard:
            def __init__(self, adapter): pass
            def connect(self, cfg): pass
            def check_access(self, cfg): pass

        monkeypatch.setattr(m, "Board", FakeBoard)
        monkeypatch.setattr(m, "ADAPTERS", {"github": lambda: object()})

        with pytest.raises(SystemExit) as info:
            m.main()
        assert info.value.code not in (0, None)


class TestEscalatePending:
    def test_aciona_agente_dedicado_com_erro_completo(self, monkeypatch, tmp_path):
        import src.__main__ as m
        calls = []
        config = {"agents": {"kiro-cli": {"correcao-esteira": {}}}}
        monkeypatch.setattr(m, "_build_task_for_target", lambda c, b, i: {"t": 1})
        monkeypatch.setattr(m, "call_agent",
                            lambda c, t, escalation_errors=None, agent_id=None:
                            calls.append((escalation_errors, agent_id)))
        esc = SyncEscalation(BOARD, ISSUE, "LOG COMPLETO", 3, "correcao-esteira")

        m.escalate_pending(config, [esc])

        assert calls == [("LOG COMPLETO", "correcao-esteira")]

    def test_agente_nao_configurado_encerra(self):
        import src.__main__ as m
        esc = SyncEscalation(BOARD, ISSUE, "LOG", 3, "correcao-esteira")
        with pytest.raises(SyncCircuitBreakerFatal):
            m.escalate_pending({"agents": {"kiro-cli": {}}}, [esc])

    def test_issue_nao_resolvivel_encerra(self, monkeypatch):
        import src.__main__ as m
        monkeypatch.setattr(m, "_build_task_for_target", lambda c, b, i: None)
        esc = SyncEscalation(BOARD, ISSUE, "LOG", 3, "correcao-esteira")
        config = {"agents": {"kiro-cli": {"correcao-esteira": {}}}}
        with pytest.raises(SyncCircuitBreakerFatal):
            m.escalate_pending(config, [esc])


class TestQueueActionable:
    def test_fila_so_com_itens_bloqueados_nao_e_acionavel(self, port, clock, monkeypatch):
        import src.__main__ as m
        monkeypatch.setattr(scb.time, "time", clock)
        config = make_config()
        seed()
        block_issue(port, config, clock)
        assert ChangeQueue().size() == 1
        assert m.queue_has_actionable(config, ChangeQueue()) is False

    def test_fila_com_item_livre_e_acionavel(self):
        import src.__main__ as m
        enqueue("7")
        assert m.queue_has_actionable(make_config(), ChangeQueue()) is True
