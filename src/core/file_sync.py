import hashlib
import mimetypes
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from src.core.board import Board, Issue
from src.core.commands import NEED_HUMAN_LABEL
from src.core.config import (ON_REJECT_BLOCK, ON_REJECT_SILENT,
                             resolve_file_sync_policy)
from src.core.log import log
from src.core.snapshot import BOARDS_DIR

FILES_DIR_SUFFIX = "-files"
REJECT_MARKER_PREFIX = "file-sync-rejected:"

_MD_LINK = re.compile(r"!?\[([^\]]*)\]\(\s*<?(https?://[^\s)>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_HTML_SRC = re.compile(r"<(?:img|a)\b[^>]*?\b(?:src|href)\s*=\s*[\"'](https?://[^\"']+)[\"']",
                       re.IGNORECASE)
_EXT = re.compile(r"\.([A-Za-z0-9]{1,10})$")
_UNSAFE = re.compile(r"[^\w.-]+")

_CONTENT_TYPE_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "application/json": "json",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
}

REASON_TYPE = "tipo não permitido"
REASON_SIZE = "tamanho acima do limite"


@dataclass(frozen=True)
class FileRef:
    url: str
    name: str


@dataclass(frozen=True)
class Rejection:
    ref: FileRef
    reason: str


def extract_links(text: str) -> list[FileRef]:
    refs: list[FileRef] = []
    seen: set[str] = set()
    for match in _MD_LINK.finditer(text or ""):
        url = match.group(2)
        if url not in seen:
            seen.add(url)
            refs.append(FileRef(url=url, name=match.group(1).strip()))
    for match in _HTML_SRC.finditer(text or ""):
        url = match.group(1)
        if url not in seen:
            seen.add(url)
            refs.append(FileRef(url=url, name=""))
    return refs


def extract_file_refs(board_obj: Board, texts: list[str]) -> list[FileRef]:
    refs: list[FileRef] = []
    seen: set[str] = set()
    for text in texts:
        for ref in extract_links(text):
            if ref.url in seen or not board_obj.is_attachment(ref.url):
                continue
            seen.add(ref.url)
            refs.append(ref)
    return refs


def _url_basename(url: str) -> str:
    return unquote(Path(urlparse(url).path).name)


def _ext_of(name: str) -> str | None:
    match = _EXT.search(name or "")
    return match.group(1).lower() if match else None


def _ext_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime in _CONTENT_TYPE_EXT:
        return _CONTENT_TYPE_EXT[mime]
    guessed = mimetypes.guess_extension(mime)
    return guessed.lstrip(".").lower() if guessed else None


def _url_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]


def _stem_of(ref: FileRef) -> str:
    base = _url_basename(ref.url)
    raw = base if _ext_of(base) else (ref.name or base)
    raw = _EXT.sub("", raw)
    stem = _UNSAFE.sub("_", raw).strip("._")[:60]
    return stem or "arquivo"


def display_name(ref: FileRef) -> str:
    base = _url_basename(ref.url)
    if _ext_of(base):
        return base
    return ref.name or base or ref.url


def files_dir(body_path: Path) -> Path:
    prefix = body_path.name.removesuffix("-body.md")
    return body_path.parent / f"{prefix}{FILES_DIR_SUFFIX}"


def _existing(target_dir: Path, ref: FileRef) -> Path | None:
    if not target_dir.is_dir():
        return None
    return next(iter(sorted(target_dir.glob(f"*-{_url_hash(ref.url)}.*"))), None)


def _local_path(target_dir: Path, ref: FileRef, ext: str) -> Path:
    return target_dir / f"{_stem_of(ref)}-{_url_hash(ref.url)}.{ext}"


def _sync_one(board_obj: Board, ref: FileRef, target_dir: Path, policy) -> Rejection | None:
    if _existing(target_dir, ref):
        return None

    ext = _ext_of(_url_basename(ref.url)) or _ext_of(ref.name)
    meta = None
    if ext is None:
        meta = board_obj.attachment_metadata(ref.url) or {}
        ext = _ext_from_content_type(meta.get("content_type"))
    if ext is None or ext not in policy.allowed_types:
        return Rejection(ref, REASON_TYPE)

    if policy.max_size is not None:
        if meta is None:
            meta = board_obj.attachment_metadata(ref.url) or {}
        size = meta.get("size")
        if size is not None and size > policy.max_size:
            return Rejection(ref, REASON_SIZE)

    content = board_obj.download_attachment(ref.url)
    if policy.max_size is not None and len(content) > policy.max_size:
        return Rejection(ref, REASON_SIZE)

    target_dir.mkdir(parents=True, exist_ok=True)
    _local_path(target_dir, ref, ext).write_bytes(content)
    return None


def rejection_key(rejections: list[Rejection]) -> str:
    lines = sorted(f"{r.ref.url}|{r.reason}" for r in rejections)
    return hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest()[:12]


def _is_own_comment(body: str) -> bool:
    return f"<!-- {REJECT_MARKER_PREFIX}" in (body or "")


def _warning_comment(rejections: list[Rejection], key: str, blocking: bool) -> str:
    lines = [
        "⚠️ **Sincronização de arquivos impedida pelas regras de sincronização.**",
        "",
        "Os arquivos abaixo não foram baixados para o ambiente local:",
        "",
    ]
    for r in rejections:
        lines.append(f"- `{display_name(r.ref)}` — {r.reason} (`{r.ref.url}`)")
    if blocking:
        lines += ["", "Remova os arquivos não permitidos do corpo/comentários da issue "
                      f"para liberar a label `{NEED_HUMAN_LABEL}`."]
    lines += ["", f"<!-- {REJECT_MARKER_PREFIX}{key} -->"]
    return "\n".join(lines)


def sync_issue_files(board_id: str, issue: Issue, comments: list[dict],
                     body_path: Path, board_obj: Board, config: dict) -> bool:
    texts = [issue.body or ""]
    texts += [c.get("body", "") for c in comments or [] if not _is_own_comment(c.get("body", ""))]
    refs = extract_file_refs(board_obj, texts)
    if not refs:
        return False

    policy = resolve_file_sync_policy(config, board_id)
    target_dir = files_dir(body_path)
    rejections: list[Rejection] = []
    for ref in refs:
        try:
            rejection = _sync_one(board_obj, ref, target_dir, policy)
        except Exception as exc:
            log.warning("FileSync", f"[{board_id}] #{issue.id} falha ao baixar "
                        f"'{display_name(ref)}': {exc}",
                        board_id=board_id, issue_id=issue.id, url=ref.url)
            continue
        if rejection:
            rejections.append(rejection)
            log.trace("FileSync", f"[{board_id}] #{issue.id} arquivo recusado "
                      f"'{display_name(ref)}': {rejection.reason}",
                      board_id=board_id, issue_id=issue.id, file=display_name(ref),
                      url=ref.url, reason=rejection.reason, on_reject=policy.on_reject)
        else:
            log.trace("FileSync", f"[{board_id}] #{issue.id} arquivo sincronizado "
                      f"'{display_name(ref)}'", board_id=board_id, issue_id=issue.id,
                      url=ref.url)

    if not rejections or policy.on_reject == ON_REJECT_SILENT:
        return False

    blocking = policy.on_reject == ON_REJECT_BLOCK
    key = rejection_key(rejections)
    marker = f"{REJECT_MARKER_PREFIX}{key}"
    if not any(marker in (c.get("body") or "") for c in comments or []):
        board_obj.add_comment(board_id, issue.id, _warning_comment(rejections, key, blocking))
        log.info("FileSync", f"[{board_id}] #{issue.id} aviso de arquivos recusados publicado",
                 board_id=board_id, issue_id=issue.id, rejected=len(rejections))

    labels = list(issue.labels or [])
    if blocking and NEED_HUMAN_LABEL not in labels:
        board_obj.add_label(board_id, issue.id, NEED_HUMAN_LABEL)
        issue.labels = labels + [NEED_HUMAN_LABEL]
        log.info("FileSync", f"[{board_id}] #{issue.id} {NEED_HUMAN_LABEL} aplicada "
                 f"por arquivos recusados", board_id=board_id, issue_id=issue.id)
        return True
    return False


def relocate_files_dir(board_id: str, body_path: Path) -> None:
    target = files_dir(body_path)
    board_dir = BOARDS_DIR / board_id
    for source in sorted(board_dir.glob(f"*/{target.name}")):
        if not source.is_dir() or source.resolve() == target.resolve():
            continue
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
            continue
        for item in source.iterdir():
            dest = target / item.name
            if dest.exists():
                item.unlink()
            else:
                item.rename(dest)
        source.rmdir()


def remove_files_dir(body_path: Path) -> None:
    target = files_dir(body_path)
    if target.is_dir():
        shutil.rmtree(target)
