"""Snapshot core - estado conhecido de um board entre execuções.

Persiste em .pipe/boards/<board_id>/snapshot.json.

Estrutura:
{
  "board": {"<col_id>": "<col_name>", ...},
  "issues": [{"id": "...", "updated_at": "...", ...}],
  "last_sync": "<ISO 8601>"
}
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from src.core.log import log

BOARDS_DIR = Path(".pipe/boards")


class Snapshot:
    """Estado conhecido de um board, persistido entre execuções."""

    def __init__(self, board_id: str):
        self._board_id = board_id
        self._path = BOARDS_DIR / board_id / "snapshot.json"
        self._data: dict = {"board": {}, "issues": [], "last_sync": None}

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> "Snapshot":
        """Carrega do disco (vazio se não existir)."""
        if self._path.exists():
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
            self._data.setdefault("board", {})
            self._data.setdefault("issues", [])
            self._data.setdefault("last_sync", None)
            self._data.setdefault("last_board_update", None)
        return self

    def save(self) -> None:
        """Persiste no disco."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @property
    def board(self) -> dict:
        """Mapa col_id -> col_name."""
        return self._data["board"]

    @board.setter
    def board(self, columns: dict):
        self._data["board"] = columns

    @property
    def issues(self) -> list[dict]:
        return self._data["issues"]

    @issues.setter
    def issues(self, value: list[dict]):
        self._data["issues"] = value

    @property
    def last_sync(self) -> str | None:
        return self._data.get("last_sync")

    @last_sync.setter
    def last_sync(self, value: str):
        self._data["last_sync"] = value

    @property
    def last_board_update(self) -> str | None:
        return self._data.get("last_board_update")

    @last_board_update.setter
    def last_board_update(self, value: str):
        self._data["last_board_update"] = value

    def issue(self, issue_id: str) -> dict | None:
        """Busca uma issue pelo id."""
        for issue in self.issues:
            if str(issue.get("id")) == str(issue_id):
                return issue
        return None


class SnapshotIntegrityError(Exception):
    """Levantada quando a restauração de um snapshot violado falha.

    Identifica o ``board_id`` afetado e guarda a exceção original (``cause``)
    que impediu a restauração — nunca é levantada quando a violação é apenas
    detectada e corrigida com sucesso.
    """

    def __init__(self, board_id: str, cause: Exception):
        self.board_id = board_id
        self.cause = cause
        super().__init__(
            f"[{board_id}] falha ao restaurar integridade do snapshot: {cause}"
        )


class SnapshotGuard:
    """Captura, compara e restaura atomicamente o snapshot.json de um board.

    Uso::

        with SnapshotGuard(board_id):
            adapter.execute(params)
        # — qualquer alteração/criação/remoção indevida já foi restaurada

    A comparação de integridade é sempre feita por conteúdo (bytes/hash),
    nunca por metadado do filesystem (mtime, tamanho etc.). Ao detectar uma
    violação, restaura por escrita atômica (arquivo temporário no mesmo
    diretório + ``os.replace()``) e emite exatamente um ``log.warning`` — sem
    nunca logar o conteúdo dos bytes. A restauração devolve também o modo
    (permissões) original do arquivo: o temporário de ``mkstemp`` nasce ``0600``
    e, sem isso, a própria guarda alteraria o estado que deve preservar.

    Se a própria restauração falhar (ex.: ``OSError``), levanta
    ``SnapshotIntegrityError`` — que precede/substitui qualquer exceção que
    estivesse se propagando do bloco protegido.
    """

    def __init__(self, board_id: str):
        self._board_id = board_id
        self._path: Path = Snapshot(board_id).path

        self._existed_before: bool = False
        self._content_before: bytes | None = None
        self._hash_before: str | None = None
        self._mode_before: int | None = None

    def __enter__(self) -> "SnapshotGuard":
        self._existed_before = self._path.exists()
        self._content_before = (
            self._path.read_bytes() if self._existed_before else None
        )
        self._hash_before = (
            hashlib.sha256(self._content_before).hexdigest()
            if self._content_before is not None
            else None
        )
        self._mode_before = (
            self._path.stat().st_mode & 0o777 if self._existed_before else None
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool | None:
        self._restore_if_violated()
        return None  # não suprime exceção original do bloco

    # ── internos ─────────────────────────────────────────────────────────────

    def _restore_if_violated(self) -> None:
        exists_after = self._path.exists()
        content_after = self._path.read_bytes() if exists_after else None
        hash_after = (
            hashlib.sha256(content_after).hexdigest()
            if content_after is not None
            else None
        )

        if hash_after == self._hash_before:
            return  # nenhuma diferença, nenhuma escrita

        log.warning(
            "SnapshotGuard",
            f"[{self._board_id}] violação de integridade detectada — "
            f"hash_antes={self._hash_before} hash_depois={hash_after} — restaurando",
        )

        try:
            if self._existed_before:
                self._atomic_write(self._content_before)
            else:
                self._path.unlink()
        except OSError as exc:
            raise SnapshotIntegrityError(self._board_id, exc) from exc

    def _atomic_write(self, content: bytes) -> None:
        """Escreve `content` atomicamente no path do snapshot.

        Usa arquivo temporário no mesmo diretório + os.replace() para
        garantir atomicidade (mesmo filesystem). O modo capturado na entrada
        do escopo é aplicado ao temporário ANTES do replace, para que o
        arquivo final já apareça com as permissões originais (o default de
        mkstemp é 0600).
        """
        directory = self._path.parent
        directory.mkdir(parents=True, exist_ok=True)

        fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=".snapshot-", suffix=".tmp")
        tmp_path = directory / Path(tmp_name).name
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            if self._mode_before is not None:
                os.chmod(tmp_path, self._mode_before)
            os.replace(tmp_path, self._path)
        except OSError:
            tmp_path.unlink(missing_ok=True)
            raise
