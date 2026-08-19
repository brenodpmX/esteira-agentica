"""Script auxiliar de teste — NÃO é um módulo de teste em si.

Executado como subprocesso por tests/test_instance_lock_concurrent.py
(cenário 4 — reinicialização legítima após crash, validada no nível de
main()/processo completo, não apenas da primitiva InstanceLock isolada).

Diferente de tests/_lock_holder_helper.py (que chama `InstanceLock.acquire()`
diretamente), este helper invoca `src.__main__.main()` de fato — mockando
apenas as colaborações externas de rede/board (padrão já usado em
tests/test_instance_lock_integration.py) para não depender de config real,
credenciais ou acesso ao GitHub. A aquisição do lock em si é a real, feita
por main() antes de startup().

Fica parado (preso no loop, aguardando _Shutdown que nunca chega) até ser
encerrado externamente (o teste mata este processo com SIGKILL para simular
crash do processo completo da esteira).

Uso:
    python tests/_main_lock_holder_helper.py <path_do_lock>
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    lock_path = Path(sys.argv[1])

    import src.__main__ as m
    from src.core.lock import InstanceLock

    # Aponta o path do lock usado por main() para o path recebido via argv,
    # sem alterar a assinatura de main()/InstanceLock() (que usa o default
    # .pipe/pipe.lock). Isolamos via monkeypatch manual da classe.
    _original_init = InstanceLock.__init__

    def _patched_init(self, path=lock_path):
        _original_init(self, lock_path)

    InstanceLock.__init__ = _patched_init

    m.check_config = lambda: {"sleep": 3600, "boards": {"platform": "github"}}
    m.startup = MagicMock()
    m.board_full_sync = MagicMock()
    m.get_board_ids = lambda cfg: ["b1"]
    m.ADAPTERS = {"github": lambda: object()}

    class _FakeBoard:
        def __init__(self, adapter):
            pass

        def connect(self, cfg):
            pass

        def check_access(self, cfg):
            pass

    m.Board = _FakeBoard

    # Bloqueia indefinidamente na fase de descoberta em vez de encerrar via
    # _Shutdown — o objetivo deste helper é permanecer "vivo" detendo o lock
    # real até ser morto externamente (SIGKILL), não completar um ciclo.
    def _bloqueia(*_a, **_k):
        print("LOCK_ACQUIRED", flush=True)
        while True:
            time.sleep(1)

    m.detect_local_all = _bloqueia
    m.sync_remote_board = lambda *_a, **_k: False
    m.sync_board = lambda *_a, **_k: False

    m.main()


if __name__ == "__main__":
    main()
