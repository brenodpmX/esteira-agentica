"""Testes do handler de SIGTERM (#70 — shutdown limpo do container).

Bug #70: com Python como PID 1 (CMD ["python", "-m", "src"]) e sem handler de
SIGTERM, o sinal enviado por `docker compose down`/Ctrl+C era ignorado. O
processo seguia preso no `time.sleep(60)` do loop ocioso, o grace period do
Docker (10s) estourava e o daemon escalava para SIGKILL → `Exited (137)`.

Correção: instalar um handler de SIGTERM que ergue `_Shutdown`. Erguer uma
exceção é essencial — desde a PEP 475 o `time.sleep` é reiniciado após o
retorno de um handler que NÃO levanta exceção; levantando `_Shutdown`, o sleep
é interrompido e o loop encerra de forma limpa (simétrico ao KeyboardInterrupt
/ SIGINT já tratado).
"""

import signal
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestHandlerSigterm:
    """O handler de SIGTERM deve erguer _Shutdown para interromper o sleep."""

    def test_shutdown_e_subclasse_de_exception(self):
        """_Shutdown deve ser uma exceção capturável no loop principal."""
        from src.__main__ import _Shutdown

        assert issubclass(_Shutdown, Exception)

    def test_handler_ergue_shutdown(self):
        """_handle_sigterm deve erguer _Shutdown (interrompe o time.sleep)."""
        from src.__main__ import _handle_sigterm, _Shutdown

        with pytest.raises(_Shutdown):
            _handle_sigterm(signal.SIGTERM, None)

    def test_shutdown_nao_e_keyboardinterrupt(self):
        """_Shutdown é distinto de KeyboardInterrupt (mensagens de log diferentes)."""
        from src.__main__ import _Shutdown

        assert not issubclass(_Shutdown, KeyboardInterrupt)


class TestRegistroDoHandler:
    """main() deve registrar o handler de SIGTERM antes de entrar no loop."""

    def test_main_registra_handler_sigterm(self, monkeypatch):
        """Ao chegar no loop, signal.signal(SIGTERM, _handle_sigterm) foi chamado.

        Forçamos a saída imediata do loop erguendo _Shutdown na primeira
        iteração (via sync_board), e verificamos que o handler de SIGTERM foi
        registrado logo antes.
        """
        import src.__main__ as m

        registrados = {}

        def fake_signal(signum, handler):
            registrados[signum] = handler

        # Faz a primeira iteração do loop encerrar imediatamente.
        def stop(*_a, **_k):
            raise m._Shutdown()

        monkeypatch.setattr(m.signal, "signal", fake_signal)
        monkeypatch.setattr(m, "check_config", lambda: {"sleep": 1, "boards": {"platform": "github"}})
        monkeypatch.setattr(m, "startup", lambda cfg: None)
        monkeypatch.setattr(m, "board_full_sync", lambda cfg: None)
        monkeypatch.setattr(m, "get_board_ids", lambda cfg: ["b1"])
        monkeypatch.setattr(m, "sync_board", stop)
        monkeypatch.setattr(m, "ADAPTERS", {"github": lambda: object()})

        class _FakeBoard:
            def __init__(self, adapter):
                pass

            def connect(self, cfg):
                pass

            def check_access(self, cfg):
                pass

        monkeypatch.setattr(m, "Board", _FakeBoard)

        m.main()

        assert signal.SIGTERM in registrados, (
            "main() não registrou handler para SIGTERM. "
            "#70: sem handler, o SIGTERM de `docker compose down` é ignorado."
        )
        assert registrados[signal.SIGTERM] is m._handle_sigterm, (
            "Handler de SIGTERM registrado não é _handle_sigterm."
        )
