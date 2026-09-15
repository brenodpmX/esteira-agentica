"""Testes do gate de `participation_intent` em `keep_task` (task #258 / story #245).

Contrato travado aqui (falha fechada — RN-B01 / ADR-001):
- `keep_task` só seleciona ou faz auto-advance de issues cujo
  `participation_intent` no snapshot é `"origin"` ou `"authorized"`.
- Campo ausente, `None`, `""`, `"propagated"`, `"unresolved"` ou qualquer outro
  valor bloqueia auto-advance e despacho (fail-closed).
- Ao bloquear, emite o evento `dispatch_blocked_unconfirmed_intent` de forma
  deduplicada por `(board, coluna, issue)`.
- O gate roda ANTES do cooldown (`_in_rerun_cooldown`), sem consumir/reiniciar
  o cooldown de uma issue que nunca é despachada.
- O gate NÃO faz chamada de rede: opera apenas sobre `Snapshot`/dados locais.

Cobre CT-01..CT-13 do documento de casos de teste da QA.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import src.__main__ as pipe
from src.__main__ import _has_confirmed_intent, keep_task, AUTO_ADVANCED


@pytest.fixture(autouse=True)
def caches_limpos():
    """Isola os caches de módulo entre testes (cooldown e dedup do evento)."""
    pipe._rerun_cache.clear()
    pipe._unconfirmed_intent_logged.clear()
    yield
    pipe._rerun_cache.clear()
    pipe._unconfirmed_intent_logged.clear()


# ─── Montagem de snapshot/config locais (sem rede) ────────────────────────────

def _issue(issue_id, column, body_path, *, created_at="2026-08-01T10:00:00Z",
           participation_intent="__omit__"):
    issue = {
        "id": issue_id,
        "column": column,
        "body_path": body_path,
        "body_mtime": "1.0",
        "created_at": created_at,
        "updated_at": created_at,
        "status": "ok",
        "labels": [],
        "parent": None,
        "children": [],
        "blocked_by": [],
        "blocks": [],
        "archived": False,
        "state": "open",
    }
    if participation_intent != "__omit__":
        issue["participation_intent"] = participation_intent
    return issue


def _write_snapshot(board_dir: Path, issues: list[dict]):
    snapshot = {
        "board": {"backlog": "Backlog", "doing": "Doing", "done": "Done"},
        "issues": issues,
        "last_sync": None,
        "last_board_update": "2026-08-01T10:00:00Z",
    }
    (board_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=2))


def _config(*, cooldown=None, todo=False):
    task = {
        "name": "Task",
        "priority": 0,
        "columns": {
            "backlog": {"name": "Backlog", "change": {"advance": "doing"}},
            "doing": {
                "name": "Doing",
                "agent": "dev",
                "change": {"advance": "done"},
            },
            "done": {"name": "Done", "archive": True},
        },
    }
    if todo:
        task["todo"] = "backlog"
    boards = {"platform": "github", "task": task}
    if cooldown is not None:
        boards["rerun_cooldown"] = cooldown
    return {"boards": boards, "sleep": 60}


@pytest.fixture
def board_dir(tmp_path, monkeypatch):
    """Board 'task' vazio em tmp_path (cwd isolado, sem rede)."""
    monkeypatch.chdir(tmp_path)
    bdir = Path(".pipe/boards/task")
    for col in ("backlog", "doing", "done"):
        (bdir / col).mkdir(parents=True)
    return bdir


def _place(board_dir: Path, col: str, stem: str):
    """Cria os arquivos da issue na coluna e devolve o body_path."""
    body = board_dir / col / f"{stem}-body.md"
    body.write_text(f"# {stem}\n\nsem comandos de bloqueio\n")
    (board_dir / col / f"{stem}-history.md").write_text("hist\n")
    (board_dir / col / f"{stem}-addcomment.md").write_text("")
    return str(body)


# ─── CT-06 — helper puro _has_confirmed_intent (tabela-verdade) ───────────────

class TestHasConfirmedIntent:
    @pytest.mark.parametrize("issue,esperado", [
        ({"participation_intent": "origin"}, True),
        ({"participation_intent": "authorized"}, True),
        ({"participation_intent": "propagated"}, False),
        ({"participation_intent": "unresolved"}, False),
        ({"participation_intent": None}, False),
        ({"participation_intent": ""}, False),
        ({}, False),
        ({"participation_intent": "ORIGIN"}, False),
    ])
    def test_tabela_verdade(self, issue, esperado):
        assert _has_confirmed_intent(issue) is esperado


# ─── CT-01/CT-02 — intenção confirmada seleciona normalmente ──────────────────

class TestSelecaoConfirmada:
    @pytest.mark.parametrize("intent", ["origin", "authorized"])
    def test_intencao_confirmada_e_selecionada(self, board_dir, intent):
        stem = "42-uma_task"
        body = _place(board_dir, "doing", stem)
        _write_snapshot(board_dir, [
            _issue("42", "doing", body, participation_intent=intent),
        ])

        task = keep_task("task", _config())

        assert task is not None and task is not AUTO_ADVANCED
        assert task["issue"]["id"] == "42"
        assert task["col_id"] == "doing"


# ─── CT-03/CT-04/CT-05 — falha fechada na seleção ─────────────────────────────

class TestSelecaoFalhaFechada:
    @pytest.mark.parametrize("intent", ["propagated", "unresolved", None, ""])
    def test_intencao_nao_confirmada_e_ignorada(self, board_dir, intent):
        stem = "42-uma_task"
        body = _place(board_dir, "doing", stem)
        _write_snapshot(board_dir, [
            _issue("42", "doing", body, participation_intent=intent),
        ])

        assert keep_task("task", _config()) is None

    def test_campo_ausente_e_ignorado(self, board_dir):
        stem = "42-uma_task"
        body = _place(board_dir, "doing", stem)
        _write_snapshot(board_dir, [
            _issue("42", "doing", body),  # sem participation_intent
        ])

        assert keep_task("task", _config()) is None


# ─── CT-07/CT-08 — auto-advance do todo condicionado à intenção ───────────────

class TestAutoAdvanceGate:
    @pytest.mark.parametrize("intent", ["propagated", "__omit__"])
    def test_sem_intencao_nao_faz_auto_advance(self, board_dir, intent):
        stem = "39-todo_task"
        body = _place(board_dir, "backlog", stem)
        _write_snapshot(board_dir, [
            _issue("39", "backlog", body, participation_intent=intent),
        ])

        with patch.object(pipe, "_auto_advance") as spy:
            result = keep_task("task", _config(todo=True))

        spy.assert_not_called()
        assert result is None  # única issue, não avança nem seleciona

        # Nenhum arquivo movido: continuam no backlog, ausentes em doing.
        for suffix in ("-body.md", "-history.md", "-addcomment.md"):
            assert (board_dir / "backlog" / f"{stem}{suffix}").exists()
            assert not (board_dir / "doing" / f"{stem}{suffix}").exists()

        # Snapshot intacto (mesma coluna, mesmo status).
        reloaded = json.loads((board_dir / "snapshot.json").read_text())
        issue = reloaded["issues"][0]
        assert issue["column"] == "backlog"
        assert issue["status"] == "ok"

    def test_com_intencao_confirmada_auto_advance_ocorre(self, board_dir):
        stem = "39-todo_task"
        body = _place(board_dir, "backlog", stem)
        _write_snapshot(board_dir, [
            _issue("39", "backlog", body, participation_intent="origin"),
        ])

        result = keep_task("task", _config(todo=True))

        assert result is AUTO_ADVANCED
        for suffix in ("-body.md", "-history.md", "-addcomment.md"):
            assert (board_dir / "doing" / f"{stem}{suffix}").exists()
        reloaded = json.loads((board_dir / "snapshot.json").read_text())
        assert reloaded["issues"][0]["status"] == "change-up"


# ─── CT-09 — convivência: só a confirmada é candidata ─────────────────────────

class TestConvivenciaIssues:
    def test_apenas_confirmada_e_candidata(self, board_dir):
        # A (mais antiga) sem intenção; B (mais recente) confirmada.
        stem_a = "41-bloqueada"
        stem_b = "42-confirmada"
        body_a = _place(board_dir, "doing", stem_a)
        body_b = _place(board_dir, "doing", stem_b)
        _write_snapshot(board_dir, [
            _issue("41", "doing", body_a, created_at="2026-08-01T09:00:00Z",
                   participation_intent="propagated"),
            _issue("42", "doing", body_b, created_at="2026-08-01T10:00:00Z",
                   participation_intent="origin"),
        ])

        task = keep_task("task", _config())

        assert task is not None and task is not AUTO_ADVANCED
        assert task["issue"]["id"] == "42"


# ─── CT-10/CT-11 — evento deduplicado ─────────────────────────────────────────

class TestEventoDeduplicado:
    def _warnings_do_evento(self, spy):
        return [
            c for c in spy.call_args_list
            if c.kwargs.get("event_type") == "dispatch_blocked_unconfirmed_intent"
        ]

    def test_evento_emitido_uma_unica_vez(self, board_dir):
        stem = "42-bloqueada"
        body = _place(board_dir, "doing", stem)
        _write_snapshot(board_dir, [
            _issue("42", "doing", body, participation_intent="propagated"),
        ])

        with patch("src.core.log.log.warning") as spy:
            assert keep_task("task", _config()) is None
            assert keep_task("task", _config()) is None

        eventos = self._warnings_do_evento(spy)
        assert len(eventos) == 1
        kwargs = eventos[0].kwargs
        assert kwargs["board_id"] == "task"
        assert kwargs["issue_id"] == "42"
        assert kwargs["col_id"] == "doing"
        assert kwargs["participation_intent"] == "propagated"

    def test_evento_reemitido_ao_mudar_de_coluna(self, board_dir):
        stem = "42-bloqueada"
        # Começa em 'doing'.
        body = _place(board_dir, "doing", stem)
        _write_snapshot(board_dir, [
            _issue("42", "doing", body, participation_intent="propagated"),
        ])

        with patch("src.core.log.log.warning") as spy:
            assert keep_task("task", _config()) is None

            # Move a issue para outra coluna elegível (adiciona 'review').
            config = _config()
            config["boards"]["task"]["columns"]["review"] = {
                "name": "Review", "agent": "dev", "change": {"advance": "done"},
            }
            (board_dir / "review").mkdir(exist_ok=True)
            new_body = _place(board_dir, "review", stem)
            _write_snapshot(board_dir, [
                _issue("42", "review", new_body, participation_intent="propagated"),
            ])

            assert keep_task("task", config) is None

        assert len(self._warnings_do_evento(spy)) == 2


# ─── CT-12 — gate não consome/reinicia o cooldown ─────────────────────────────

class TestGateAntesDoCooldown:
    def test_nao_grava_cooldown_para_issue_bloqueada(self, board_dir):
        stem = "42-bloqueada"
        body = _place(board_dir, "doing", stem)
        _write_snapshot(board_dir, [
            _issue("42", "doing", body, participation_intent="propagated"),
        ])

        assert keep_task("task", _config(cooldown=300)) is None
        assert ("task", "doing", "42") not in pipe._rerun_cache
        assert len(pipe._rerun_cache) == 0


# ─── CT-13 — gate não realiza chamada de rede (fake BoardPort) ────────────────

class _ExplodingBoardPort:
    """BoardPort falso: qualquer método invocado levanta erro (prova sem rede)."""

    def __getattr__(self, name):
        def _boom(*args, **kwargs):
            raise AssertionError(
                f"gate tocou o BoardPort ({name}) — violação de camada / rede"
            )
        return _boom


class TestSemRede:
    def test_gate_nao_toca_board_port(self, board_dir, monkeypatch):
        monkeypatch.setattr(pipe, "board", _ExplodingBoardPort())

        stem_ok = "42-confirmada"
        stem_block = "43-bloqueada"
        stem_todo = "44-todo_bloqueada"
        body_ok = _place(board_dir, "doing", stem_ok)
        body_block = _place(board_dir, "doing", stem_block)
        body_todo = _place(board_dir, "backlog", stem_todo)

        # Caminho de seleção confirmada.
        _write_snapshot(board_dir, [
            _issue("42", "doing", body_ok, participation_intent="origin"),
        ])
        assert keep_task("task", _config())["issue"]["id"] == "42"

        # Caminho de bloqueio + evento.
        _write_snapshot(board_dir, [
            _issue("43", "doing", body_block, participation_intent="propagated"),
        ])
        assert keep_task("task", _config()) is None

        # Caminho do todo não confirmado (sem auto-advance).
        _write_snapshot(board_dir, [
            _issue("44", "backlog", body_todo, participation_intent="propagated"),
        ])
        assert keep_task("task", _config(todo=True)) is None
        # Nenhuma exceção do fake BoardPort: o gate não tocou a rede.
