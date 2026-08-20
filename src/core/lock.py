"""Lock local de instância (`InstanceLock`).

Garante exclusividade de instância por diretório de estado usando
``fcntl.flock(LOCK_EX | LOCK_NB)`` sobre um arquivo dedicado (padrão:
``.pipe/pipe.lock``).

Referência: doc/architecture/confiabilidade-parent-recursivo/arquitetura.md
(ADR-06) e doc/requirements/confiabilidade-parent-recursivo/business-rules.md
(RN-009).

Escopo desta primitiva (issue #150): apenas a classe isolada + tratamento do
lock em si. A integração com ``main()``/``startup()`` é responsabilidade da
próxima task da mesma story (issue #151).

Comportamento de lock órfão (processo detentor morto sem cleanup, ex.:
SIGKILL) não exige código adicional aqui: é uma propriedade do próprio
``flock`` do kernel — ao morrer o processo, todos os file descriptors são
fechados pelo SO e o lock é liberado automaticamente, mesmo com o arquivo
intacto no disco.
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path


class LockHeldError(Exception):
    """Levantada quando `InstanceLock.acquire()` não consegue adquirir o lock
    porque outro processo já o detém.

    Os campos `holder_pid`, `holder_started_at` e `holder_host` são lidos a
    partir dos metadados gravados no arquivo pelo detentor atual. A leitura é
    best-effort: o arquivo pode estar sendo escrito concorrentemente pelo
    detentor, então qualquer erro de leitura/parse resulta em `None` nesses
    campos, sem propagar exceção.
    """

    def __init__(
        self,
        path: Path,
        holder_pid: int | None = None,
        holder_started_at: str | None = None,
        holder_host: str | None = None,
    ) -> None:
        self.path = path
        self.holder_pid = holder_pid
        self.holder_started_at = holder_started_at
        self.holder_host = holder_host
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return (
            f"lock ocupado em {self.path} — detentor: pid={self.holder_pid}, "
            f"iniciado em {self.holder_started_at} (host={self.holder_host}). "
            f"Encerre a instância detentora ou aguarde; não edite {self.path} "
            f"manualmente."
        )


def _read_holder_metadata(path: Path) -> tuple[int | None, str | None, str | None]:
    """Lê best-effort os metadados do detentor atual do lock.

    Nunca propaga exceção: qualquer falha de leitura/parse resulta em
    ``(None, None, None)``.
    """
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        return data.get("pid"), data.get("started_at"), data.get("host")
    except (OSError, ValueError):
        return None, None, None


class InstanceLock:
    """Lock exclusivo de instância via `fcntl.flock`, com metadados no arquivo.

    Uso principal (fora de testes): chamada direta de `acquire`/`release` em
    `try/finally` — não `with` — porque o lock precisa sobreviver a exceções
    tratadas dentro do loop sem ser liberado. O suporte a context manager
    (`__enter__`/`__exit__`) existe para uso opcional em testes ou scripts
    pontuais.
    """

    def __init__(self, path: Path = Path(".pipe/pipe.lock")) -> None:
        self.path = Path(path)
        self._fd: int | None = None

    def acquire(self) -> None:
        """Adquire o lock exclusivo, não-bloqueante.

        Abre (cria se não existir) o arquivo em modo leitura/escrita e tenta
        `fcntl.flock(fd, LOCK_EX | LOCK_NB)`. Nunca faz `unlink`/recria o
        arquivo antes de tentar — a aquisição do flock deve ocorrer sempre
        sobre o mesmo inode (ver ADR-06).

        Em caso de sucesso: trunca o conteúdo anterior, grava metadados
        (pid, started_at, host) como JSON de uma linha, `flush()` +
        `os.fsync(fd)`. Mantém o file descriptor aberto em `self._fd`.

        Em caso de falha (lock já detido por outro processo): lê os
        metadados do detentor atual (best-effort) e levanta `LockHeldError`.
        """
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                os.close(fd)
                holder_pid, holder_started_at, holder_host = _read_holder_metadata(
                    self.path
                )
                raise LockHeldError(
                    path=self.path,
                    holder_pid=holder_pid,
                    holder_started_at=holder_started_at,
                    holder_host=holder_host,
                ) from exc
            os.close(fd)
            raise

        metadata = {
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "host": socket.gethostname(),
        }
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, (json.dumps(metadata) + "\n").encode("utf-8"))
        os.fsync(fd)
        self._fd = fd

    def release(self) -> None:
        """Libera o lock. Idempotente: chamar sem lock ativo não levanta erro.

        Não deleta o arquivo — apenas libera o lock do kernel. O arquivo pode
        permanecer no disco (vazio ou com metadados antigos) até a próxima
        aquisição sobrescrevê-lo.
        """
        if self._fd is None:
            return
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None

    def __enter__(self) -> "InstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
