"""Testes de classificação de erro de sincronismo e requeue sem
head-of-line blocking — issue #144 (story #139).

Cobre a issue #144: classificar erros de sincronismo em três categorias
estáveis (`"definitivo"`, `"transitorio"`, `"rate_limit"`) e usar essa
classificação em `apply_changes` para que um item com falha nunca impeça o
processamento dos demais itens da fila no mesmo ciclo — eliminando o
head-of-line blocking do incidente #97.

Escopo:
- `classify_error(exc) -> str` (função pura; local ainda a definir pela
  implementação — `src/core/sync.py` ou `src/core/error_classifier.py`).
- Campo `attempts: int = 0` em `ChangeItem` (`src/core/board.py`).
- Chave opcional `sync.max_attempts` em `pipe.yml` (`src/core/config.py`),
  default `3`, validada como `int >= 1`.
- Requeue sem head-of-line blocking em `apply_changes` (`src/core/sync.py`).
- Caminho de `PenaltyException` preservado bit-a-bit (return imediato,
  `attempts` inalterado, nenhum outro item processado na mesma chamada).

Nota: estes testes foram escritos ANTES da implementação (etapa "Casos de
Teste" antecede/acompanha a implementação, mesmo padrão usado na issue #143
— ver `tests/test_sanitize_relations.py`). No momento da escrita, nenhuma das
mudanças acima existe no repositório: `classify_error` não existe,
`ChangeItem` não tem `attempts`, `config.py` não tem `sync.max_attempts` e
`apply_changes` interrompe a fila em qualquer exceção não-`PenaltyException`.
Os testes que dependem dessas mudanças devem falhar (ImportError/
AttributeError/asserção) até a implementação da issue ser feita, e passar
depois — sem alterações nesta task além dos próprios testes.

Os testes que já podem ser exercidos contra o código atual (ex.: mensagens
estáveis reconhecidas via `_apply_change_up`/`_apply_delete_up`, que já
tratam a issue fantasma) NÃO são duplicados aqui — já estão cobertos em
`tests/test_correcao3_erro_irrecuperavel_sync.py`.
"""

import sys
from pathlib import Path

import pytest

# Permite importar o pacote src quando rodado de qualquer lugar.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, ChangeItem, Issue, PenaltyException, SyncEvent
from src.core.change_queue import ChangeQueue


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola .pipe/ em um diretório temporário por teste."""
    monkeypatch.chdir(tmp_path)
    yield


# ══════════════════════════════════════════════════════════════════════════
# Fake adapter que registra chamadas em vez de bater na rede
# ══════════════════════════════════════════════════════════════════════════

class FakePort(BoardPort):
    def __init__(self):
        self.calls = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def list_issues_since(self, board_id, since): return []
    def get_issue(self, board_id, issue_id, fullsync=False):
        self.calls.append(("get_issue", board_id, issue_id))
        return Issue(id=issue_id, title="", body="", column="")
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id):
        self.calls.append(("close", board_id, issue_id))
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


def _ops(port):
    return [c[0] for c in port.calls]


# ══════════════════════════════════════════════════════════════════════════
# CT01 — classify_error: rate_limit / definitivo / transitorio (AC1)
# ══════════════════════════════════════════════════════════════════════════

class TestClassifyErrorRateLimit:
    """CT01a — PenaltyException classifica como 'rate_limit'."""

    def test_penalty_exception_is_rate_limit(self):
        from src.core.sync import classify_error
        assert classify_error(PenaltyException(wait_seconds=8)) == "rate_limit"


class TestClassifyErrorDefinitivo:
    """CT01b — mensagens estáveis (issue fantasma / isolamento de board)
    classificam como 'definitivo'."""

    def test_ghost_issue_message_is_definitivo(self):
        from src.core.sync import classify_error
        exc = Exception("Could not resolve to an issue or pull request with the number of 42")
        assert classify_error(exc) == "definitivo"

    def test_board_isolation_message_is_definitivo(self):
        from src.core.sync import classify_error
        exc = Exception("issue #42 não pertence a este board — operação abortada")
        assert classify_error(exc) == "definitivo"

    def test_ghost_issue_message_different_number_is_definitivo(self):
        """O número da issue varia; a substring é o discriminador estável."""
        from src.core.sync import classify_error
        exc = Exception("Could not resolve to an issue or pull request with the number of 999")
        assert classify_error(exc) == "definitivo"


class TestClassifyErrorTransitorio:
    """CT01c — qualquer outra exceção classifica como 'transitorio' (default seguro)."""

    def test_generic_value_error_is_transitorio(self):
        from src.core.sync import classify_error
        assert classify_error(ValueError("algo inesperado")) == "transitorio"

    def test_simulated_network_error_is_transitorio(self):
        from src.core.sync import classify_error
        exc = ConnectionError("Network timeout: conexão recusada")
        assert classify_error(exc) == "transitorio"

    def test_empty_message_exception_is_transitorio(self):
        from src.core.sync import classify_error
        assert classify_error(Exception()) == "transitorio"

    def test_dns_error_without_ghost_substring_is_transitorio(self):
        """'Could not resolve hostname' não é a substring exata da issue fantasma."""
        from src.core.sync import classify_error
        exc = Exception("Could not resolve hostname: api.github.com")
        assert classify_error(exc) == "transitorio"


class TestClassifyErrorPure:
    """classify_error não faz I/O nem loga; apenas classifica (função pura)."""

    def test_does_not_raise_and_returns_str(self):
        from src.core.sync import classify_error
        result = classify_error(Exception("qualquer coisa"))
        assert isinstance(result, str)

    def test_no_logging_side_effect(self, monkeypatch):
        from src.core import sync as sync_module
        calls = []
        monkeypatch.setattr(sync_module.log, "warning", lambda *a, **k: calls.append(a))
        monkeypatch.setattr(sync_module.log, "info", lambda *a, **k: calls.append(a))
        monkeypatch.setattr(sync_module.log, "error", lambda *a, **k: calls.append(a))
        sync_module.classify_error(Exception("Could not resolve to an issue or pull request"))
        assert calls == []


# ══════════════════════════════════════════════════════════════════════════
# CT02 — pipe.yml: sync.max_attempts (AC2)
# ══════════════════════════════════════════════════════════════════════════

def _base_config(**overrides) -> dict:
    """Config mínima válida para check_config (sem os validadores de env/git
    reais — usada apenas para exercitar a validação da chave sync.max_attempts
    isoladamente, se a implementação expuser um validador dedicado; senão,
    construída inline para os testes que chamam check_config via arquivo)."""
    cfg = {
        "sleep": 60,
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": {"base": "main", "feature": {"prefix": "feature/", "create": "main", "merge": "main"}},
        },
        "agents": {},
        "boards": {"platform": "github"},
    }
    cfg.update(overrides)
    return cfg


class TestMaxAttemptsDefault:
    """CT02a — ausência da chave usa default 3."""

    def test_default_is_three_when_key_absent(self):
        from src.core.config import resolve_max_attempts
        assert resolve_max_attempts(_base_config()) == 3

    def test_default_is_three_when_sync_block_absent(self):
        from src.core.config import resolve_max_attempts
        cfg = _base_config()
        assert "sync" not in cfg
        assert resolve_max_attempts(cfg) == 3


class TestMaxAttemptsValid:
    """CT02b — valor presente e válido (int >= 1) é usado."""

    @pytest.mark.parametrize("value", [1, 3, 5, 10])
    def test_valid_value_is_used(self, value):
        from src.core.config import resolve_max_attempts
        cfg = _base_config(sync={"max_attempts": value})
        assert resolve_max_attempts(cfg) == value


class TestMaxAttemptsInvalid:
    """CT02c — valor inválido levanta ConfigError identificando a chave."""

    @pytest.mark.parametrize("value", [0, -1, "abc", 2.5])
    def test_invalid_value_raises_config_error(self, value):
        from src.core.config import ConfigError, validate_max_attempts
        with pytest.raises(ConfigError):
            validate_max_attempts(_base_config(sync={"max_attempts": value}))

    def test_config_error_message_identifies_key(self):
        from src.core.config import ConfigError, validate_max_attempts
        with pytest.raises(ConfigError) as excinfo:
            validate_max_attempts(_base_config(sync={"max_attempts": 0}))
        assert "max_attempts" in str(excinfo.value)


# ══════════════════════════════════════════════════════════════════════════
# CT03 — ChangeItem.attempts (parte do item 2, pré-requisito dos demais)
# ══════════════════════════════════════════════════════════════════════════

class TestChangeItemAttempts:
    """CT03 — campo attempts existe, default 0, e não afeta same_target."""

    def test_default_attempts_is_zero(self):
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        assert item.attempts == 0

    def test_attempts_settable(self):
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        item.attempts = 2
        assert item.attempts == 2

    def test_same_target_ignores_attempts(self):
        a = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        b = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        b.attempts = 5
        assert a.same_target(b)

    def test_legacy_persisted_item_without_attempts_defaults_zero(self):
        """ChangeQueue._read ignora campos desconhecidos ao carregar; itens
        antigos (sem 'attempts' no JSON) devem carregar attempts=0."""
        import json
        from src.core.change_queue import QUEUE_FILE, PIPE_DIR

        PIPE_DIR.mkdir(parents=True, exist_ok=True)
        legacy_item = {
            "timestamp": ChangeItem.now(),
            "event": SyncEvent.CHANGE_UP.value,
            "id": "1",
            "identifier": None,
            "board": "b",
            "uuid": "11111111-1111-1111-1111-111111111111",
            "fullsync": False,
            # sem "attempts" — simula persistência anterior a esta mudança
        }
        QUEUE_FILE.write_text(json.dumps([legacy_item]), encoding="utf-8")

        q = ChangeQueue()
        item = q.getNext()
        assert item is not None
        assert item.attempts == 0


# ══════════════════════════════════════════════════════════════════════════
# CT04 — apply_changes: item transitório não bloqueia os demais (AC3)
# ══════════════════════════════════════════════════════════════════════════

class TestApplyChangesNoHeadOfLineBlocking:
    """CT04 — item transitório no início da fila não impede o processamento
    dos demais itens saudáveis na mesma chamada de apply_changes."""

    def test_healthy_items_processed_despite_leading_transient_failure(self, monkeypatch):
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="1", board="b"))
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="2", board="b"))
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="3", board="b"))

        processed = []

        def fake_delete_up(board_id, item, board_obj, queue=None):
            if item.id == "1":
                raise ValueError("erro transitório simulado")
            processed.append(item.id)

        monkeypatch.setattr(sync_module, "_apply_delete_up", fake_delete_up)

        board_obj = Board(FakePort())
        sync_module.apply_changes(board_obj, q, config={})

        assert processed == ["2", "3"], (
            f"Itens saudáveis deveriam ter sido processados na mesma chamada, "
            f"mas apenas {processed} foram processados"
        )

    def test_call_terminates_without_infinite_loop(self, monkeypatch):
        """Critério de aceite 3: a chamada termina mesmo com o item
        transitório ainda na fila ao final (abaixo do limite de tentativas)."""
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="1", board="b"))

        def always_fails(board_id, item, board_obj, queue=None):
            raise ValueError("sempre falha, mas abaixo do limite")

        monkeypatch.setattr(sync_module, "_apply_delete_up", always_fails)

        board_obj = Board(FakePort())
        # Não deve travar (default max_attempts=3 > 1 tentativa única aqui).
        sync_module.apply_changes(board_obj, q, config={})

        # Item permanece na fila (abaixo do limite), mas a chamada terminou.
        remaining = q.getNext()
        assert remaining is not None
        assert remaining.id == "1"

    def test_never_processes_same_item_twice_in_same_call(self, monkeypatch):
        """Com um único item na fila, o requeue ao fim não deve fazer
        apply_changes reprocessá-lo mais de uma vez na mesma chamada."""
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="1", board="b"))

        call_count = {"n": 0}

        def counting_handler(board_id, item, board_obj, queue=None):
            call_count["n"] += 1
            raise ValueError("erro transitório")

        monkeypatch.setattr(sync_module, "_apply_delete_up", counting_handler)

        board_obj = Board(FakePort())
        sync_module.apply_changes(board_obj, q, config={})

        assert call_count["n"] == 1, (
            f"O item deveria ser tentado uma única vez por chamada de "
            f"apply_changes, mas foi tentado {call_count['n']} vezes"
        )


# ══════════════════════════════════════════════════════════════════════════
# CT05 — item transitório esgota tentativas e é removido (AC4)
# ══════════════════════════════════════════════════════════════════════════

class TestApplyChangesExhaustedAttempts:
    """CT05 — item que atinge o limite de tentativas é removido da fila
    ativa e loga a exaustão."""

    def test_item_removed_after_reaching_max_attempts(self, monkeypatch):
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="1", board="b"))

        def always_fails(board_id, item, board_obj, queue=None):
            raise ValueError("erro transitório persistente")

        monkeypatch.setattr(sync_module, "_apply_delete_up", always_fails)

        board_obj = Board(FakePort())
        config = {"sync": {"max_attempts": 2}}

        # Duas chamadas: cada apply_changes tenta o item uma vez (não deve
        # reprocessar no mesmo ciclo — ver CT04), então após 2 chamadas o
        # limite de 2 tentativas é atingido e o item deve sair da fila.
        sync_module.apply_changes(board_obj, q, config=config)
        sync_module.apply_changes(board_obj, q, config=config)

        assert q.getNext() is None, "Item deveria ter sido removido da fila após esgotar tentativas"

    def test_warning_logged_identifying_board_id_event_and_attempts(self, monkeypatch):
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="99", board="task"))

        def always_fails(board_id, item, board_obj, queue=None):
            raise ValueError("erro transitório persistente")

        monkeypatch.setattr(sync_module, "_apply_delete_up", always_fails)

        warning_calls = []
        monkeypatch.setattr(
            sync_module.log, "warning",
            lambda module, msg, *a, **k: warning_calls.append((module, msg, k)),
        )

        board_obj = Board(FakePort())
        config = {"sync": {"max_attempts": 1}}
        sync_module.apply_changes(board_obj, q, config=config)

        assert warning_calls, "Nenhum log.warning emitido ao esgotar tentativas"
        full_text = " ".join(str(c) for c in warning_calls)
        assert "task" in full_text
        assert "99" in full_text
        assert SyncEvent.DELETE_UP.value in full_text or "delete-up" in full_text


# ══════════════════════════════════════════════════════════════════════════
# CT06 — item definitivo é removido já na primeira falha (AC5)
# ══════════════════════════════════════════════════════════════════════════

class TestApplyChangesDefinitiveError:
    """CT06 — erro classificado como 'definitivo' remove o item já na
    primeira falha, sem acumular tentativas, e loga a classificação."""

    def test_item_removed_on_first_failure_without_accumulating_attempts(self, monkeypatch):
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.CHANGE_UP, id="42", board="b"))

        def raises_board_isolation_error(board_id, item, board_obj, queue=None, config=None):
            raise Exception("issue #42 não pertence a este board — operação abortada")

        monkeypatch.setattr(sync_module, "_apply_change_up", raises_board_isolation_error)

        board_obj = Board(FakePort())
        sync_module.apply_changes(board_obj, q, config={"sync": {"max_attempts": 3}})

        assert q.getNext() is None, "Item com erro definitivo deveria sair da fila já na 1ª falha"

    def test_logs_classification_on_definitive_error(self, monkeypatch):
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="42", board="b"))

        def raises_ghost_error(board_id, item, board_obj, queue=None):
            raise Exception("Could not resolve to an issue or pull request with the number of 42")

        monkeypatch.setattr(sync_module, "_apply_delete_up", raises_ghost_error)

        warning_calls = []
        monkeypatch.setattr(
            sync_module.log, "warning",
            lambda module, msg, *a, **k: warning_calls.append(msg),
        )

        board_obj = Board(FakePort())
        sync_module.apply_changes(board_obj, q, config={})

        assert warning_calls, "Nenhum log emitido para erro definitivo"


# ══════════════════════════════════════════════════════════════════════════
# CT07 — PenaltyException preserva comportamento atual (AC6)
# ══════════════════════════════════════════════════════════════════════════

class TestApplyChangesPenaltyExceptionUnchanged:
    """CT07 — PenaltyException: return imediato, attempts inalterado,
    nenhum outro item processado nesta chamada."""

    def test_returns_immediately_on_penalty(self, monkeypatch):
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="1", board="b"))
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="2", board="b"))

        processed = []

        def raises_penalty_for_first(board_id, item, board_obj, queue=None):
            if item.id == "1":
                raise PenaltyException(wait_seconds=32)
            processed.append(item.id)

        monkeypatch.setattr(sync_module, "_apply_delete_up", raises_penalty_for_first)

        board_obj = Board(FakePort())
        sync_module.apply_changes(board_obj, q, config={})

        assert processed == [], "Nenhum outro item deveria ser processado após PenaltyException"

    def test_item_remains_in_queue_with_unchanged_attempts(self, monkeypatch):
        from src.core import sync as sync_module

        q = ChangeQueue()
        item = ChangeItem.of(SyncEvent.DELETE_UP, id="1", board="b")
        item.attempts = 0
        q.add(item)

        def raises_penalty(board_id, item, board_obj, queue=None):
            raise PenaltyException(wait_seconds=16)

        monkeypatch.setattr(sync_module, "_apply_delete_up", raises_penalty)

        board_obj = Board(FakePort())
        sync_module.apply_changes(board_obj, q, config={})

        remaining = q.getNext()
        assert remaining is not None
        assert remaining.id == "1"
        assert remaining.attempts == 0, "attempts não deve ser incrementado no caminho de PenaltyException"


# ══════════════════════════════════════════════════════════════════════════
# CT08 — itens de boards diferentes avançam na mesma chamada (AC7)
# ══════════════════════════════════════════════════════════════════════════

class TestApplyChangesMultiBoardProgress:
    """CT08 — item saudável de um board avança mesmo com item de outro board
    falhando antes dele na fila."""

    def test_second_board_item_processed_despite_first_board_failure(self, monkeypatch):
        from src.core import sync as sync_module

        q = ChangeQueue()
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="1", board="board-a"))
        q.add(ChangeItem.of(SyncEvent.DELETE_UP, id="2", board="board-b"))

        processed = []

        def fake_delete_up(board_id, item, board_obj, queue=None):
            if board_id == "board-a":
                raise ValueError("erro transitório em board-a")
            processed.append((board_id, item.id))

        monkeypatch.setattr(sync_module, "_apply_delete_up", fake_delete_up)

        board_obj = Board(FakePort())
        sync_module.apply_changes(board_obj, q, config={})

        assert ("board-b", "2") in processed, "Item de board-b deveria ter sido processado"


# ══════════════════════════════════════════════════════════════════════════
# CT09 — não regressão: fantasma/isolamento continuam idênticos (AC8)
# ══════════════════════════════════════════════════════════════════════════

class TestNoRegressionOnExistingSpecificHandling:
    """CT09 — o tratamento específico de issue fantasma em
    _apply_change_up/_apply_delete_up permanece intacto (não modificado por
    esta issue) e a suíte pré-existente de test_sync_optimization.py e
    test_correcao3_erro_irrecuperavel_sync.py não regride.

    Este teste é um guard-rail leve; a verificação completa de não-regressão
    é feita executando `python -m pytest tests/ -v` (ver critério de aceite 8
    da issue) e não duplicada aqui.
    """

    def test_apply_change_up_and_apply_delete_up_still_exist_and_importable(self):
        from src.core.sync import _apply_change_up, _apply_delete_up  # noqa: F401
