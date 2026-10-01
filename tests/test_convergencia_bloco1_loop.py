"""CT-04 — Convergência #303 × #304 no loop principal (coexistência sem sombreamento).

Issue #314 (verificação do bloco 1). Critério de aceitação CA-6:

    Dado que #303 (classificação de resultado de execução do agente) e #304
    (modelo único de sincronização) convergem no loop principal — onde o
    resultado da execução e o resultado da sincronização alimentam juntos a
    seleção de tarefa e o controle de ociosidade —, quando a verificação ocorre,
    então há evidência registrada de que ambas permanecem efetivas em conjunto,
    sem que uma anule ou sombreie a outra nesse ponto.

Este arquivo fecha a lacuna registrada em CT-02: a suíte existente
(`tests/test_loop_guard.py`) **reimplementa a lógica do loop inline no próprio
teste** (`had_changes = True; if not had_changes: ...`), o mesmo anti-padrão do
incidente #106 — não exercita o código real de `src/__main__.py`.

Aqui o teste dirige o **loop real** de `src.__main__.main()`. Os patches são
feitos **apenas nas fronteiras** (adapter kiro-cli, board, descoberta local/
remota do provider, `time.sleep`, lock, startup); a decisão sob verificação
— como o resultado da sincronização (#304, via `detect_local_all`/
`sync_remote_board`) e o resultado da execução classificado (#303, via
`call_agent`/`_dispatch_with_recovery`) co-alimentam `keep_task` + `sleep_time`
— roda com o código de produção, sem cópia.

Determinismo: um contador conta os ciclos do `while running` (um incremento por
chamada do boundary `detect_local_changes`, invocado uma vez por ciclo via
`detect_local_all`) e ergue `_Shutdown` após o número de ciclos desejado —
exatamente o mesmo mecanismo de parada limpa do SIGTERM (o `main` trata
`_Shutdown` encerrando o loop). Nenhuma lógica do loop é reimplementada.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import ChangeItem, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot
from src.core import execution


# ──────────────────────────────────────────────────────────────────────────────
# Ambiente de board isolado em tmp_path (offline — sem rede/subprocesso real)
# ──────────────────────────────────────────────────────────────────────────────

BOARD_ID = "entrega"
COL_DEV = "desenvolvimento"
COL_DONE = "concluido"
COL_TODO = "backlog"


def _write_body(path: Path, title: str) -> None:
    path.write_text(f"# {title}\n\n{title} body.\n", encoding="utf-8")


def _base_config() -> dict:
    """Config mínima e completa para o loop/`call_agent`/`build_prompt` reais.

    `desenvolvimento` tem agente e `change.advance` (coluna executável).
    `backlog` é o 'todo' com auto-advance para `desenvolvimento`.
    """
    return {
        "sleep": 60,
        "boards": {
            "platform": "github",
            BOARD_ID: {
                "priority": 0,
                "todo": COL_TODO,
                "columns": {
                    COL_TODO: {
                        "name": "Backlog",
                        "change": {"advance": COL_DEV},
                    },
                    COL_DEV: {
                        "name": "Desenvolvimento",
                        "agent": "engineering",
                        "gitevents": "no-branch",
                        "target-prompt": "Execute a tarefa",
                        "change": {"advance": COL_DONE},
                    },
                    COL_DONE: {"name": "Concluído", "archive": True},
                },
            },
        },
        "agents": {
            "github": {
                "engineering": {"name": "Eng", "model": "claude-sonnet"},
            },
        },
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": {"base": "main", "feature": {"create": "main", "merge": "main"}},
        },
    }


class _Env:
    """Ambiente de teste: diretórios .pipe isolados + helpers de snapshot/fila."""

    def __init__(self, tmp_path: Path):
        self.root = tmp_path
        self.boards_base = tmp_path / ".pipe" / "boards"
        self.pipe_dir = tmp_path / ".pipe"
        for col in (COL_TODO, COL_DEV, COL_DONE):
            (self.boards_base / BOARD_ID / col).mkdir(parents=True, exist_ok=True)

    def set_snapshot(self, issues: list[dict]) -> None:
        snap = Snapshot(BOARD_ID)
        snap.load()
        snap.board = {COL_TODO: "Backlog", COL_DEV: "Desenvolvimento", COL_DONE: "Concluído"}
        snap.issues = issues
        snap.save()

    def dev_issue(self, issue_id: str = "100") -> dict:
        """Cria o body e devolve o dict de issue na coluna de desenvolvimento."""
        body = self.boards_base / BOARD_ID / COL_DEV / f"issue-{issue_id}-body.md"
        _write_body(body, f"Issue {issue_id}")
        return {
            "id": issue_id,
            "column": COL_DEV,
            "status": "ok",
            "body_path": str(body),
            "body_mtime": str(body.stat().st_mtime),
            "created_at": "2026-01-01T00:00:00Z",
        }

    def todo_issue(self, issue_id: str = "200") -> dict:
        body = self.boards_base / BOARD_ID / COL_TODO / f"issue-{issue_id}-body.md"
        _write_body(body, f"Todo {issue_id}")
        return {
            "id": issue_id,
            "column": COL_TODO,
            "status": "ok",
            "body_path": str(body),
            "body_mtime": str(body.stat().st_mtime),
            "created_at": "2026-01-01T00:00:00Z",
        }


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    e = _Env(tmp_path)
    monkeypatch.setattr("src.core.sync.BOARDS_DIR", e.boards_base)
    monkeypatch.setattr("src.core.snapshot.BOARDS_DIR", e.boards_base)
    monkeypatch.setattr("src.core.agent.BOARDS_DIR", e.boards_base)
    monkeypatch.setattr("src.core.change_queue.PIPE_DIR", e.pipe_dir)
    monkeypatch.setattr("src.core.change_queue.QUEUE_FILE", e.pipe_dir / "changeQueue.json")
    return e


# ──────────────────────────────────────────────────────────────────────────────
# Driver do loop REAL
# ──────────────────────────────────────────────────────────────────────────────

class _Recorder:
    """Registra as invocações reais nas fronteiras do loop.

    - `remote_results`: fila de resultados (bool) do sync remoto por ciclo.
      Cada valor True é materializado enfileirando um change-down REAL no board,
      para que o `sync_remote_board` real compute `queue.has_board()` de verdade.
    - `local_each_cycle`: se True em um ciclo, enfileira um change local REAL
      (via o boundary `detect_local_changes`), para `detect_local_all` real
      retornar True a partir do tamanho real da fila.
    - `exec_results`: fila de ExecutionResult que o adapter fake devolve.
    """

    def __init__(self, max_cycles: int):
        self.max_cycles = max_cycles
        self.cycle = 0
        self.sleep_calls: list[float] = []
        self.execute_calls: list = []  # AgentParams recebidos
        self.execute_returns: list = []  # ExecutionResult devolvidos ao loop
        self.keep_task_results: list = []  # retornos reais de keep_task
        self.remote_true_cycles: set[int] = set()
        self.local_true_cycles: set[int] = set()
        self.exec_results: list = []


def _drive_main(env: _Env, config: dict, rec: _Recorder,
                exec_results=None, remote_true_cycles=None, local_true_cycles=None):
    """Executa o `main()` real por `rec.max_cycles` ciclos e então erge _Shutdown.

    Patches SOMENTE em fronteiras:
      - check_config/startup/board_startup_sync/InstanceLock/Board/ADAPTERS
      - detect_local_changes (local discovery do provider) — enfileira ou não
      - sync_remote (remote discovery do provider) — enfileira change-down ou não
      - KiroCliAgent.execute — devolve ExecutionResult classificado
      - time.sleep — registrado; nunca espera de verdade
    O resto (detect_local_all, sync_remote_board, process_queue, keep_task,
    call_agent, _dispatch_with_recovery, sleep_time, loop `while running`) é
    código REAL de src/__main__.py.
    """
    import src.__main__ as m

    rec.exec_results = list(exec_results or [])
    rec.remote_true_cycles = set(remote_true_cycles or ())
    rec.local_true_cycles = set(local_true_cycles or ())

    # --- Fakes de descoberta (provider), mas usando a fila/estado REAL ---
    def fake_detect_local_changes(board_id, queue):
        # Primeira chamada de detect_local_all em cada ciclo marca o início do
        # ciclo. Conta ciclos e, atingido o limite, encerra limpo (_Shutdown).
        rec.cycle += 1
        if rec.cycle > rec.max_cycles:
            raise m._Shutdown()
        if rec.cycle in rec.local_true_cycles:
            queue.add(ChangeItem.of(SyncEvent.CREATE_UP,
                                    identifier=f"local-{rec.cycle}", board=board_id))

    def fake_sync_remote(board_id, board_obj, queue):
        if rec.cycle in rec.remote_true_cycles:
            queue.add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id=f"r{rec.cycle}",
                                    board=board_id, fullsync=True))

    # --- Fake do adapter kiro-cli (fronteira do subprocesso) ---
    class _FakeAdapter:
        def execute(self, params):
            rec.execute_calls.append(params)
            if rec.exec_results:
                result = rec.exec_results.pop(0)
            else:
                result = execution.ExecutionResult(classe=execution.SUCEDIDO)
            return result

    # --- Fakes estruturais (não participam da decisão sob verificação) ---
    class _FakeLock:
        def acquire(self):
            return None

        def release(self):
            return None

    class _FakeBoard:
        def __init__(self, *a, **k):
            pass

        def connect(self, config):
            return None

        def check_access(self, config):
            return None

    # Envolve keep_task real para registrar os retornos (sem alterar a decisão).
    real_keep_task = m.keep_task

    def recording_keep_task(board_id, config):
        result = real_keep_task(board_id, config)
        rec.keep_task_results.append(result)
        return result

    # Envolve _dispatch_with_recovery real para registrar o resultado propagado.
    real_dispatch = m._dispatch_with_recovery

    def recording_dispatch(*args, **kwargs):
        result = real_dispatch(*args, **kwargs)
        rec.execute_returns.append(result)
        return result

    def fake_sleep(seconds):
        rec.sleep_calls.append(seconds)

    with patch.object(m, "check_config", return_value=config), \
         patch.object(m, "startup"), \
         patch.object(m, "board_startup_sync"), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "InstanceLock", _FakeLock), \
         patch.object(m, "Board", _FakeBoard), \
         patch.object(m, "ADAPTERS", {"github": _FakeBoard}), \
         patch.object(m, "KiroCliAgent", _FakeAdapter), \
         patch.object(m, "detect_local_changes", fake_detect_local_changes), \
         patch.object(m, "sync_remote", fake_sync_remote), \
         patch.object(m, "keep_task", recording_keep_task), \
         patch.object(m, "_dispatch_with_recovery", recording_dispatch), \
         patch("src.__main__.time.sleep", fake_sleep), \
         patch("signal.signal"):
        m.main()


# ──────────────────────────────────────────────────────────────────────────────
# CT-04a — Sync com mudança sombreia a execução (down vence; sem sleep)
# ──────────────────────────────────────────────────────────────────────────────

def test_ct04a_sync_change_shadows_execution_no_sleep(env):
    """had_changes=True ⇒ ciclo volta ao início: NÃO chama call_agent nem sleep.

    Prova que o resultado da SINCRONIZAÇÃO (#304) tem efeito real no fluxo e não
    é sombreado pela existência de uma tarefa elegível no board.
    """
    config = _base_config()
    env.set_snapshot([env.dev_issue("100")])  # tarefa elegível existe

    rec = _Recorder(max_cycles=1)
    # Ciclo 1: sync remoto traz mudança (change-down real na fila).
    _drive_main(env, config, rec, remote_true_cycles={1})

    # keep_task NÃO foi chamado (o guard de had_changes volta ao início antes).
    assert rec.keep_task_results == []
    # Agente NÃO executou.
    assert rec.execute_calls == []
    # Ociosidade NÃO disparada: a mudança impede o sleep.
    assert rec.sleep_calls == []


# ──────────────────────────────────────────────────────────────────────────────
# CT-04b — Sem mudança + tarefa ⇒ executa e propaga a classificação (#303)
# ──────────────────────────────────────────────────────────────────────────────

def test_ct04b_execution_classification_propagates_sucedido(env):
    """Sem mudança + tarefa elegível ⇒ call_agent→_dispatch_with_recovery roda e
    devolve o ExecutionResult SUCEDIDO ao loop. #303 efetiva no ponto de
    convergência; sem sleep quando havia tarefa."""
    config = _base_config()
    env.set_snapshot([env.dev_issue("100")])

    rec = _Recorder(max_cycles=1)
    _drive_main(env, config, rec,
                exec_results=[execution.ExecutionResult(classe=execution.SUCEDIDO)])

    # keep_task real selecionou a tarefa de desenvolvimento.
    assert len(rec.keep_task_results) == 1
    assert isinstance(rec.keep_task_results[0], dict)
    assert rec.keep_task_results[0]["col_id"] == COL_DEV
    # O agente executou exatamente uma vez.
    assert len(rec.execute_calls) == 1
    # A classificação foi propagada ao loop pelo _dispatch_with_recovery real.
    assert len(rec.execute_returns) == 1
    assert rec.execute_returns[0].classe == execution.SUCEDIDO
    # Havia tarefa ⇒ não houve ociosidade.
    assert rec.sleep_calls == []


def test_ct04b_unknown_outcome_fail_closed_single_invocation_no_backoff(env):
    """UNKNOWN_OUTCOME (#303 fail-closed): UMA única invocação do subprocesso e
    NENHUM time.sleep de backoff; a classe ambígua é propagada ao loop."""
    config = _base_config()
    env.set_snapshot([env.dev_issue("100")])

    rec = _Recorder(max_cycles=1)
    _drive_main(env, config, rec, exec_results=[
        execution.ExecutionResult(classe=execution.UNKNOWN_OUTCOME,
                                  causa="InternalServerError após output parcial",
                                  origem="dispatch failure"),
    ])

    # Fail-closed: exatamente uma invocação do adapter (sem retry inline).
    assert len(rec.execute_calls) == 1
    assert len(rec.execute_returns) == 1
    assert rec.execute_returns[0].classe == execution.UNKNOWN_OUTCOME
    # Nenhum backoff: o único sleep possível seria o de backoff — não há.
    assert rec.sleep_calls == []


def test_ct04b_definite_not_started_retries_inline_with_backoff(env):
    """DEFINITE_NOT_STARTED (#303): único caso de retry inline, com backoff
    crescente conforme retry.* — exercitado pelo _dispatch_with_recovery real."""
    config = _base_config()
    config["retry"] = {"max_tentativas": 3, "backoff_inicial_seg": 5, "backoff_fator": 2.0}
    env.set_snapshot([env.dev_issue("100")])

    rec = _Recorder(max_cycles=1)
    # Três DEFINITE_NOT_STARTED ⇒ esgota as tentativas ⇒ FALHA_PERSISTENTE.
    dns = lambda: execution.ExecutionResult(
        classe=execution.DEFINITE_NOT_STARTED, causa="kiro-cli ausente no PATH",
        origem="erro interno")
    _drive_main(env, config, rec, exec_results=[dns(), dns(), dns()])

    # 3 invocações (max_tentativas) do adapter via retry inline real.
    assert len(rec.execute_calls) == 3
    # backoff real: 5 * 2^0 e 5 * 2^1 = 5 e 10 (2 esperas entre 3 tentativas).
    assert rec.sleep_calls == [5, 10]
    # Resultado final propagado ao loop é FALHA_PERSISTENTE.
    assert rec.execute_returns[-1].classe == execution.FALHA_PERSISTENTE
    assert rec.execute_returns[-1].tentativas == 3


# ──────────────────────────────────────────────────────────────────────────────
# CT-04c — Sem mudança + sem tarefa ⇒ ociosidade (sleep conjunto)
# ──────────────────────────────────────────────────────────────────────────────

def test_ct04c_idle_sleep_requires_no_change_and_no_task(env):
    """had_changes=False E keep_task=None em todos os boards ⇒ sleep_time UMA vez.

    Prova que o controle de ociosidade depende CONJUNTAMENTE do resultado de
    sincronização (#304) e da seleção de tarefa (#303/loop)."""
    config = _base_config()
    # Snapshot sem issue elegível (keep_task retorna None).
    env.set_snapshot([])

    rec = _Recorder(max_cycles=1)
    _drive_main(env, config, rec)

    # keep_task real foi chamado e retornou None.
    assert rec.keep_task_results == [None]
    # Nenhuma execução de agente.
    assert rec.execute_calls == []
    # Ociosidade: sleep exatamente uma vez, pelo tempo configurado.
    assert rec.sleep_calls == [config["sleep"]]


def test_ct04c_contraprova_change_suppresses_sleep(env):
    """Contraprova (anti-sombreamento): com had_changes=True, mesmo sem tarefa,
    sleep_time NÃO é chamado — o sleep não é disparado por uma só das entregas."""
    config = _base_config()
    env.set_snapshot([])  # sem tarefa

    rec = _Recorder(max_cycles=1)
    _drive_main(env, config, rec, remote_true_cycles={1})  # mas há mudança

    assert rec.keep_task_results == []  # guard de had_changes impede keep_task
    assert rec.execute_calls == []
    assert rec.sleep_calls == []  # mudança suprime a ociosidade


def test_ct04c_contraprova_task_suppresses_sleep(env):
    """Contraprova (anti-sombreamento): com tarefa elegível e sem mudança,
    sleep_time NÃO é chamado — a existência de tarefa suprime a ociosidade."""
    config = _base_config()
    env.set_snapshot([env.dev_issue("100")])  # tarefa elegível

    rec = _Recorder(max_cycles=1)
    _drive_main(env, config, rec,
                exec_results=[execution.ExecutionResult(classe=execution.SUCEDIDO)])

    assert len(rec.execute_calls) == 1  # executou
    assert rec.sleep_calls == []        # não dormiu


# ──────────────────────────────────────────────────────────────────────────────
# CT-04d — AUTO_ADVANCED mantém o board e força novo sync (sem sleep, sem exec)
# ──────────────────────────────────────────────────────────────────────────────

def test_ct04d_auto_advanced_keeps_board_no_sleep_no_exec(env):
    """keep_task=AUTO_ADVANCED ⇒ loop reinicia mantendo o board, sem call_agent
    nem sleep nesse ciclo. Comprova encadeamento seleção(#303/loop) ↔ re-sync
    (#304) sem conflito.

    Dois ciclos: no ciclo 1, a issue está no 'todo' e keep_task real faz o
    auto-advance (move os arquivos p/ desenvolvimento, enfileira change-up) e
    retorna AUTO_ADVANCED; o loop NÃO executa agente nem dorme. O ciclo 2 existe
    só para encerrar limpo após o re-sync forçado.
    """
    config = _base_config()
    env.set_snapshot([env.todo_issue("200")])  # issue no 'todo'

    rec = _Recorder(max_cycles=2)
    _drive_main(env, config, rec)

    # keep_task real retornou AUTO_ADVANCED no primeiro acionamento.
    assert rec.keep_task_results[0] is __import__("src.__main__", fromlist=["AUTO_ADVANCED"]).AUTO_ADVANCED
    # Nenhuma execução de agente e nenhum sleep nos ciclos observados.
    assert rec.execute_calls == []
    assert rec.sleep_calls == []
    # Efeito real do auto-advance: a issue foi movida para desenvolvimento e há
    # change-up enfileirado (o re-sync forçado consome no ciclo seguinte).
    moved = env.boards_base / BOARD_ID / COL_DEV / "issue-200-body.md"
    assert moved.exists()
