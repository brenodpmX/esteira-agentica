"""Testes do shutdown limpo por SIGTERM e do empacotamento Docker (issue #70).

Contexto do bug: com `CMD ["python", "-m", "src"]` o interpretador vira PID 1.
O kernel não aplica ação *default* de sinais para PID 1, então sem handler
instalado o SIGTERM enviado por `docker compose down` era ignorado; o processo
seguia no `time.sleep` do loop ocioso, o grace period estourava e o Docker
escalava para SIGKILL → `Exited (137)`.

Duas frentes cobertas aqui:
- Causa 1 (logs não aparecem em tempo real): `PYTHONUNBUFFERED=1` no Dockerfile.
- Causa 2 (shutdown sujo): handler de SIGTERM + `init: true` no compose.
"""

import ast
import signal
import sys
import threading
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.__main__ as pipe_main

COMPOSE_FILE = ROOT / "docker-compose.yml"
DOCKERFILE = ROOT / "Dockerfile"
MAIN_FILE = ROOT / "src" / "__main__.py"


# ── Contrato do _Shutdown ─────────────────────────────────────────────────────

class TestHandlerSigterm:

    def test_shutdown_e_subclasse_de_exception(self):
        assert issubclass(pipe_main._Shutdown, Exception)

    def test_shutdown_nao_e_keyboardinterrupt(self):
        """Precisa ser distinguível do SIGINT para logar mensagem própria."""
        assert not issubclass(pipe_main._Shutdown, KeyboardInterrupt)

    def test_handler_ergue_shutdown(self):
        """Erguer (e não só marcar flag) é o que interrompe o time.sleep (PEP 475)."""
        with pytest.raises(pipe_main._Shutdown):
            pipe_main._handle_sigterm(signal.SIGTERM, None)


# ── Registro do handler em main() ─────────────────────────────────────────────

class TestRegistroDoHandler:
    """Valida por AST (sem executar main(), que sobe a esteira inteira)."""

    @staticmethod
    def _main_func():
        tree = ast.parse(MAIN_FILE.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                return node
        pytest.fail("função main() não encontrada em src/__main__.py")

    def test_main_registra_handler_sigterm(self):
        chamadas = [
            n for n in ast.walk(self._main_func())
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "signal"
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "signal"
        ]
        assert chamadas, "main() não chama signal.signal(...)"

        alvos = []
        for c in chamadas:
            if len(c.args) == 2:
                alvos.append((ast.unparse(c.args[0]), ast.unparse(c.args[1])))
        assert ("signal.SIGTERM", "_handle_sigterm") in alvos, (
            f"SIGTERM não registrado com _handle_sigterm; encontrado: {alvos}"
        )

    def test_loop_trata_shutdown(self):
        """O loop precisa capturar _Shutdown antes do except Exception genérico."""
        loop = next(
            n for n in ast.walk(self._main_func()) if isinstance(n, ast.While)
        )
        handlers = [
            h for n in ast.walk(loop) if isinstance(n, ast.Try) for h in n.handlers
        ]
        nomes = [ast.unparse(h.type) if h.type else None for h in handlers]
        assert "_Shutdown" in nomes, f"_Shutdown não tratado no loop: {nomes}"
        assert nomes.index("_Shutdown") < nomes.index("Exception"), (
            "_Shutdown precisa vir antes do except Exception genérico"
        )


# ── Comportamento: SIGTERM interrompe o sleep ─────────────────────────────────

@pytest.mark.skipif(
    threading.current_thread() is not threading.main_thread(),
    reason="signal.signal só pode ser instalado na thread principal",
)
class TestSigtermInterrompeSleep:

    def test_sigterm_interrompe_time_sleep(self):
        """Regressão do incidente: SIGTERM durante o sleep ocioso deve abortá-lo."""
        anterior = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, pipe_main._handle_sigterm)
        try:
            import os

            threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()
            inicio = time.monotonic()
            with pytest.raises(pipe_main._Shutdown):
                time.sleep(5)
            assert time.monotonic() - inicio < 2, "sleep não foi interrompido pelo SIGTERM"
        finally:
            signal.signal(signal.SIGTERM, anterior)


# ── Empacotamento Docker ──────────────────────────────────────────────────────

class TestDockerPackaging:

    def test_dockerfile_define_pythonunbuffered(self):
        """Causa 1: sem isso, o print() bufferiza fora de TTY e nada chega ao docker logs."""
        conteudo = DOCKERFILE.read_text(encoding="utf-8")
        assert "PYTHONUNBUFFERED=1" in conteudo

    def test_compose_declara_init_true(self):
        """Causa 2: tini como PID 1 repassa o SIGTERM e reapa zumbis."""
        compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
        assert compose["services"]["pipe"].get("init") is True
