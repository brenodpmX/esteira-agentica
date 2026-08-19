"""Script auxiliar de teste — NÃO é um módulo de teste em si.

Executado como subprocesso por tests/test_instance_lock.py (critério de
aceite 4 — lock órfão). Adquire o lock no path recebido via argv[1] e trava
indefinidamente, sem chamar release(), até ser encerrado externamente
(o teste mata este processo com SIGKILL para simular crash).

Uso:
    python tests/_lock_holder_helper.py <path_do_lock>
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    from src.core.lock import InstanceLock

    lock_path = Path(sys.argv[1])
    lock = InstanceLock(lock_path)
    lock.acquire()
    # Sinaliza no stdout que o lock foi adquirido, para o processo de teste
    # saber quando é seguro proceder (evita race condition de timing).
    print("LOCK_ACQUIRED", flush=True)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
