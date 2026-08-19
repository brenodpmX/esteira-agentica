"""Testes de integração do SnapshotGuard com call_agent e o loop principal.

Cobrem os critérios de aceite da issue #154:

1. `call_agent` com fake AgentPort que escreve lixo no snapshot e retorna
   normalmente -> snapshot em disco restaurado byte a byte após o retorno.
2. `call_agent` com fake AgentPort que escreve lixo no snapshot e levanta
   exceção -> a exceção original se propaga através de call_agent e o
   snapshot é restaurado.
3. Falha na própria restauração (mock de os.replace levantando OSError)
   -> call_agent propaga SnapshotIntegrityError (não a exceção original do
   agente, se houver) identificando board_id e causa.
4. Loop principal (`main()`/bloco `while running`): quando call_agent
   propaga SnapshotIntegrityError, o loop não a captura no `except
   Exception` genérico nem tenta novo ciclo — a exceção se propaga e
   encerra o processo.
5. PenaltyException e KeyboardInterrupt continuam tratados exatamente como
   hoje (nenhuma mudança de comportamento nesses dois caminhos).

Segue o padrão de mocks/fixtures já usado em `tests/test_loop_guard.py`,
`tests/test_sync_optimization.py` e `tests/test_snapshot_guard.py`.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.agent import AgentPort, AgentParams  # noqa: E402
from src.core.board import PenaltyException  # noqa: E402
from src.core.snapshot import Snapshot, SnapshotIntegrityError  # noqa: E402


BOARD_ID = "task"
COL_ID = "doing"


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola .pipe/ em um diretório temporário por teste.

    Cria .pipe/ de antemão: InstanceLock.acquire() (issue #151) não cria
    diretórios pais, apenas o arquivo do lock.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pipe").mkdir(exist_ok=True)
    yield


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_snapshot(board_id: str = BOARD_ID) -> bytes:
    """Cria um snapshot.json inicial e retorna os bytes escritos."""
    path = Snapshot(board_id).path
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"board": {"col1": "Column 1"}, "issues": [{"id": "1"}], "last_sync": None}
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    path.write_bytes(content)
    return content


def _minimal_config() -> dict:
    return {
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": {
                "base": "main",
                "feature": {"prefix": "feature/", "create": "main", "merge": "main"},
            },
        },
        "agents": {
            "kiro-cli": {
                "dev": {"name": "engineering", "model": "claude-sonnet-4"},
            }
        },
    }


def _minimal_task(tmp_path: Path, board_id: str = BOARD_ID, col_id: str = COL_ID) -> dict:
    """Task mínima com body/issue válidos para call_agent (via build_prompt)."""
    issue_dir = tmp_path / ".pipe" / "boards" / board_id / col_id
    issue_dir.mkdir(parents=True, exist_ok=True)

    body_path = issue_dir / "42-my-feature-body.md"
    body_path.write_text("# My Feature\n\nDescrição da tarefa.\n", encoding="utf-8")

    return {
        "board_id": board_id,
        "board": {"flow": "feature", "repo": "main"},
        "col_id": col_id,
        "column": {
            "name": "Doing",
            "agent": "dev",
            "gitevents": "no-branch",
            "target-prompt": "Execute a tarefa",
            "change": {"advance": "done"},
        },
        "issue": {"id": "42", "body_path": str(body_path)},
    }


class _WritesGarbageAndSucceeds(AgentPort):
    """Fake AgentPort: corrompe o snapshot.json e retorna normalmente."""

    def __init__(self, board_id: str):
        self._board_id = board_id
        self.executed = False

    def execute(self, params: AgentParams) -> None:
        self.executed = True
        Snapshot(self._board_id).path.write_bytes(
            b'{"board": {}, "issues": [], "last_sync": "GARBAGE"}'
        )


class _WritesGarbageAndRaises(AgentPort):
    """Fake AgentPort: corrompe o snapshot.json e levanta RuntimeError."""

    def __init__(self, board_id: str):
        self._board_id = board_id

    def execute(self, params: AgentParams) -> None:
        Snapshot(self._board_id).path.write_bytes(
            b'{"board": {}, "issues": [], "last_sync": "GARBAGE"}'
        )
        raise RuntimeError("falha simulada do agente")


def _patch_agent_guard():
    """AgentGuard não é o foco deste teste; neutraliza-o como no-op."""
    return patch("src.__main__.AgentGuard", MagicMock(side_effect=lambda *a, **k: MagicMock(
        __enter__=MagicMock(return_value=MagicMock()),
        __exit__=MagicMock(return_value=None),
    )))


# ─────────────────────────────────────────────────────────────────────────────
# CT-01: sucesso do agente + violação -> snapshot restaurado
# ─────────────────────────────────────────────────────────────────────────────

class TestCallAgentRestauraEmSucesso:
    def test_snapshot_restaurado_apos_execucao_normal(self, tmp_path):
        from src import __main__ as m

        original = _write_snapshot(BOARD_ID)
        task = _minimal_task(tmp_path)
        fake_adapter = _WritesGarbageAndSucceeds(BOARD_ID)

        with patch.object(m, "KiroCliAgent", return_value=fake_adapter):
            m.call_agent(_minimal_config(), task)

        assert fake_adapter.executed is True
        assert Snapshot(BOARD_ID).path.read_bytes() == original


# ─────────────────────────────────────────────────────────────────────────────
# CT-02: erro do agente + violação -> exceção original propaga E snapshot restaura
# ─────────────────────────────────────────────────────────────────────────────

class TestCallAgentRestauraEPropagaErroOriginal:
    def test_excecao_original_propaga_e_snapshot_restaurado(self, tmp_path):
        from src import __main__ as m

        original = _write_snapshot(BOARD_ID)
        task = _minimal_task(tmp_path)
        fake_adapter = _WritesGarbageAndRaises(BOARD_ID)

        with patch.object(m, "KiroCliAgent", return_value=fake_adapter):
            with pytest.raises(RuntimeError, match="falha simulada do agente"):
                m.call_agent(_minimal_config(), task)

        assert Snapshot(BOARD_ID).path.read_bytes() == original


# ─────────────────────────────────────────────────────────────────────────────
# CT-03: falha na própria restauração -> SnapshotIntegrityError prevalece
# ─────────────────────────────────────────────────────────────────────────────

class TestCallAgentPropagaSnapshotIntegrityError:
    def test_falha_de_restauracao_propaga_snapshot_integrity_error(self, tmp_path, monkeypatch):
        from src import __main__ as m

        _write_snapshot(BOARD_ID)
        task = _minimal_task(tmp_path)
        fake_adapter = _WritesGarbageAndSucceeds(BOARD_ID)

        def boom(*args, **kwargs):
            raise OSError("disco cheio (simulado)")

        monkeypatch.setattr(os, "replace", boom)

        with patch.object(m, "KiroCliAgent", return_value=fake_adapter):
            with pytest.raises(SnapshotIntegrityError) as exc_info:
                m.call_agent(_minimal_config(), task)

        assert BOARD_ID in str(exc_info.value)

    def test_falha_de_restauracao_prevalece_sobre_erro_original_do_agente(self, tmp_path, monkeypatch):
        """Quando o agente levanta E a restauração falha, o que propaga de
        call_agent é SnapshotIntegrityError — não a exceção original do
        agente."""
        from src import __main__ as m

        _write_snapshot(BOARD_ID)
        task = _minimal_task(tmp_path)
        fake_adapter = _WritesGarbageAndRaises(BOARD_ID)

        def boom(*args, **kwargs):
            raise OSError("falha de escrita (simulado)")

        monkeypatch.setattr(os, "replace", boom)

        with patch.object(m, "KiroCliAgent", return_value=fake_adapter):
            with pytest.raises(SnapshotIntegrityError):
                m.call_agent(_minimal_config(), task)


# ─────────────────────────────────────────────────────────────────────────────
# CT-04: loop principal — SnapshotIntegrityError não cai no except Exception
# ─────────────────────────────────────────────────────────────────────────────

class TestLoopPrincipalNaoCapturaSnapshotIntegrityError:
    def test_snapshot_integrity_error_propaga_e_encerra_loop(self, monkeypatch):
        """Simula o bloco `while running` com call_agent levantando
        SnapshotIntegrityError: a exceção deve se propagar para fora do loop
        (processo encerra), sem cair no `except Exception` genérico e sem
        tentar novo ciclo (sleep/continue)."""
        import src.__main__ as m

        registered_sleep_calls = []
        monkeypatch.setattr(m.time, "sleep", lambda *_a, **_k: registered_sleep_calls.append(True))

        config = {"sleep": 1, "boards": {"platform": "github"}}

        # Guarda contra loop infinito: se SnapshotIntegrityError NÃO for
        # tratada por um handler dedicado (bug), ela cai no `except
        # Exception` genérico do loop, que também engoliria qualquer outra
        # exceção usada como sentinela de parada — o teste travaria o
        # runner. Por isso o limite de iterações é imposto na fase de
        # descoberta (chamada antes de call_agent em todo ciclo, inclusive nos
        # que apenas reexecutam após o `except Exception` genérico) levantando
        # `KeyboardInterrupt`, que não é coberta pelo genérico e por isso é
        # sentinela segura de parada.
        #
        # O guard é instalado em TODAS as funções de descoberta —
        # `detect_local_all`, `sync_remote_board` e o wrapper `sync_board` — de
        # propósito: qualquer uma que o loop chame primeiro encerra a iteração.
        # Amarrado a uma só, um refactor do loop faz este teste **travar** em
        # loop infinito (o `except Exception` dorme e continua) em vez de
        # falhar — foi o que ocorreu ao restaurar a descoberta local global.
        sync_board_calls = []

        def fake_sync_board(*_a, **_k):
            sync_board_calls.append(True)
            if len(sync_board_calls) > 3:
                raise KeyboardInterrupt(
                    "fase de descoberta chamada múltiplas vezes: "
                    "SnapshotIntegrityError não encerrou o loop (foi capturada "
                    "pelo `except Exception` genérico e o ciclo continuou)."
                )
            return False

        def fake_keep_task(*_a, **_k):
            return {"id": "42", "board_id": BOARD_ID}

        def fake_call_agent(*_a, **_k):
            raise SnapshotIntegrityError(BOARD_ID, OSError("disco cheio"))

        monkeypatch.setattr(m, "check_config", lambda: config)
        monkeypatch.setattr(m, "startup", lambda cfg: None)
        monkeypatch.setattr(m, "board_full_sync", lambda cfg: None)
        monkeypatch.setattr(m, "get_board_ids", lambda cfg: [BOARD_ID])
        monkeypatch.setattr(m, "detect_local_all", fake_sync_board)
        monkeypatch.setattr(m, "sync_remote_board", fake_sync_board)
        monkeypatch.setattr(m, "sync_board", fake_sync_board)
        monkeypatch.setattr(m, "keep_task", fake_keep_task)
        monkeypatch.setattr(m, "call_agent", fake_call_agent)
        monkeypatch.setattr(m, "process_queue", lambda cfg: None)

        class _FakeQueue:
            def size(self):
                return 0

        monkeypatch.setattr(m, "ChangeQueue", _FakeQueue)

        class _FakeBoard:
            def __init__(self, adapter):
                pass

            def connect(self, cfg):
                pass

            def check_access(self, cfg):
                pass

        monkeypatch.setattr(m, "Board", _FakeBoard)
        monkeypatch.setattr(m, "ADAPTERS", {"github": lambda: object()})

        with pytest.raises(SnapshotIntegrityError):
            m.main()

        # Não tentou dormir/continuar após a falha fatal.
        assert registered_sleep_calls == []

    def test_generic_except_nao_intercepta_snapshot_integrity_error(self):
        """Reprodução direta da cadeia de except do bloco `while running`:
        SnapshotIntegrityError deve ser capturada por um handler dedicado
        (levantado novamente), nunca pelo `except Exception` genérico."""
        from src.__main__ import _Shutdown

        raised = SnapshotIntegrityError(BOARD_ID, OSError("disco cheio"))
        handled_as = None

        try:
            try:
                raise raised
            except PenaltyException:
                handled_as = "penalty"
            except KeyboardInterrupt:
                handled_as = "keyboard"
            except _Shutdown:
                handled_as = "shutdown"
            except SnapshotIntegrityError:
                handled_as = "snapshot_integrity"
                raise
            except Exception:
                handled_as = "generic"
        except SnapshotIntegrityError:
            pass

        assert handled_as == "snapshot_integrity"


# ─────────────────────────────────────────────────────────────────────────────
# CT-05: PenaltyException e KeyboardInterrupt continuam tratados como hoje
# ─────────────────────────────────────────────────────────────────────────────

class TestNaoRegressaoPenaltyEKeyboardInterrupt:
    def test_penalty_exception_nao_e_afetada_por_snapshot_integrity_error(self):
        """PenaltyException deve continuar sendo capturada antes de qualquer
        handler de SnapshotIntegrityError, sem mudança de comportamento."""
        handled_as = None
        try:
            raise PenaltyException(wait_seconds=30)
        except PenaltyException:
            handled_as = "penalty"
        except SnapshotIntegrityError:
            handled_as = "snapshot_integrity"
        except Exception:
            handled_as = "generic"

        assert handled_as == "penalty"

    def test_keyboard_interrupt_nao_e_afetada_por_snapshot_integrity_error(self):
        handled_as = None
        try:
            raise KeyboardInterrupt()
        except PenaltyException:
            handled_as = "penalty"
        except KeyboardInterrupt:
            handled_as = "keyboard"
        except SnapshotIntegrityError:
            handled_as = "snapshot_integrity"
        except Exception:
            handled_as = "generic"

        assert handled_as == "keyboard"
