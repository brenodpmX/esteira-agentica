import copy
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.github_board import GitHubBoardAdapter
from src.core import sync
from src.core.board import Board, BoardPort, Issue
from src.core.change_queue import ChangeQueue
from src.core.commands import NEED_HUMAN_LABEL
from src.core.config import DEFAULT_ALLOWED_FILE_TYPES
from src.core.file_sync import REJECT_MARKER_PREFIX, extract_links
from src.core.log import log
from src.core.participation import Participation
from src.core.snapshot import BOARDS_DIR, Snapshot

BOARD = "entrega"
DEV = "desenvolvimento"
TESTES = "execucao-testes"

IMG_URL = "https://user-images.githubusercontent.com/0/img.png"
LOG_URL = "https://github.com/org/repo/files/1/erro.log"
ASSET_URL = "https://github.com/user-attachments/assets/3f2a9c1e-0000-4b6f-9d1e-1234567890ab"


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log._log_dir = Path("logs")
    log._setup()
    yield


def _log_text():
    path = Path("logs") / f"{date.today().strftime('%Y-%m-%d')}.json"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _config(file_sync=None):
    board = {"name": "Entrega", "columns": {DEV: {"name": "Dev"}, TESTES: {"name": "Testes"}}}
    if file_sync is not None:
        board["file-sync"] = file_sync
    return {"boards": {"platform": "github", BOARD: board}}


class FakePort(BoardPort):
    def __init__(self):
        self.issues: dict[str, Issue] = {}
        self.comments: dict[str, list[dict]] = {}
        self.files: dict[str, bytes] = {}
        self.meta: dict[str, dict] = {}
        self.downloads: list[str] = []
        self.metadata_calls: list[str] = []
        self.added_comments: list[tuple[str, str]] = []
        self.add_label_calls: list[tuple[str, str]] = []
        self.download_error: Exception | None = None

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return list(self.issues.values())

    def get_issue(self, board_id, issue_id, fullsync=False):
        issue = self.issues.get(str(issue_id))
        return copy.deepcopy(issue) if issue else None

    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)

    def move_issue(self, board_id, issue_id, column, from_column=None):
        self.issues[str(issue_id)].column = column

    def update_issue(self, board_id, issue_id, title=None, body=None): pass

    def add_comment(self, board_id, issue_id, comment):
        self.added_comments.append((str(issue_id), comment))
        self.comments.setdefault(str(issue_id), []).append(
            {"author": "pipe", "date": "2026-11-09T10:00:00Z", "body": comment})

    def list_comments(self, board_id, issue_id):
        return [dict(c) for c in self.comments.get(str(issue_id), [])]

    def close_issue(self, board_id, issue_id): pass
    def set_labels(self, board_id, issue_id, labels): pass

    def add_label(self, board_id, issue_id, label):
        self.add_label_calls.append((str(issue_id), label))
        issue = self.issues[str(issue_id)]
        if label not in (issue.labels or []):
            issue.labels = list(issue.labels or []) + [label]

    def remove_label(self, board_id, issue_id, label):
        issue = self.issues[str(issue_id)]
        issue.labels = [l for l in (issue.labels or []) if l != label]

    def set_parent(self, board_id, issue_id, parent_id, known_current=None): pass
    def set_children(self, board_id, issue_id, children_ids, known_current=None): pass
    def set_blocked_by(self, board_id, issue_id, blocker_ids, known_current=None): pass
    def set_blocks(self, board_id, issue_id, blocked_ids, known_current=None): pass

    def list_participations(self, issue_id):
        issue = self.issues[str(issue_id)]
        return [Participation(f"I{issue_id}", BOARD, "P", issue.column)]

    def is_attachment(self, url):
        return GitHubBoardAdapter.is_attachment(self, url)

    def attachment_metadata(self, url):
        self.metadata_calls.append(url)
        if url in self.meta:
            return dict(self.meta[url])
        return {"size": len(self.files.get(url, b"")), "content_type": None}

    def download_attachment(self, url):
        self.downloads.append(url)
        if self.download_error:
            raise self.download_error
        return self.files[url]

    def comments_with_marker(self, issue_id):
        return [b for i, b in self.added_comments
                if i == str(issue_id) and REJECT_MARKER_PREFIX in b]


def _seed_snapshot():
    snap = Snapshot(BOARD).load()
    snap.board = {DEV: "Dev", TESTES: "Testes"}
    snap.save()


def _remote(port, body, issue_id="77", title="Exemplo", column=DEV, labels=None):
    port.issues[issue_id] = Issue(id=issue_id, title=title, body=body, column=column,
                                  labels=list(labels or []), updated_at="2026-11-09T09:00:00Z")
    port.comments.setdefault(issue_id, [])


def _create_down(port, config=None, issue_id="77"):
    _seed_snapshot()
    item = sync.ChangeItem.of(sync.SyncEvent.CREATE_DOWN, id=issue_id, board=BOARD)
    sync._apply_create_down(BOARD, item, Board(port), ChangeQueue(), config or _config())


def _change_down(port, config=None, issue_id="77"):
    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_DOWN, id=issue_id, board=BOARD)
    sync._apply_change_down(BOARD, item, Board(port), ChangeQueue(), config or _config())


def _files_dir(column=DEV, prefix="77-exemplo"):
    return BOARDS_DIR / BOARD / column / f"{prefix}-files"


def _local_files(column=DEV, prefix="77-exemplo"):
    d = _files_dir(column, prefix)
    return sorted(d.iterdir()) if d.is_dir() else []


def _body_file(column=DEV, prefix="77-exemplo"):
    return BOARDS_DIR / BOARD / column / f"{prefix}-body.md"


def _contents(column=DEV):
    return sorted(p.read_bytes() for p in _local_files(column))


# ── Grupo A ──────────────────────────────────────────────────────────────────

def test_ct01_ct08_imagem_embutida_no_corpo_baixada_no_diretorio_da_issue():
    port = FakePort()
    port.files[IMG_URL] = b"\x89PNG-bytes"
    _remote(port, f"Veja o print: ![print]({IMG_URL})")

    _create_down(port)

    files = _local_files()
    assert len(files) == 1
    assert files[0].parent == BOARDS_DIR / BOARD / DEV / "77-exemplo-files"
    assert files[0].suffix == ".png"
    assert files[0].read_bytes() == b"\x89PNG-bytes"
    assert f"![print]({IMG_URL})" in _body_file().read_text(encoding="utf-8")


def test_ct02_arquivo_anexado_no_corpo_baixado():
    port = FakePort()
    port.files[LOG_URL] = b"stacktrace"
    _remote(port, f"Logs em anexo: [erro.log]({LOG_URL})")

    _create_down(port)

    files = _local_files()
    assert [f.suffix for f in files] == [".log"]
    assert files[0].name.startswith("erro-")
    assert files[0].read_bytes() == b"stacktrace"


def test_ct03_corpo_com_embutido_e_anexado_baixa_ambos():
    port = FakePort()
    port.files[IMG_URL] = b"A"
    port.files[LOG_URL] = b"B"
    _remote(port, f"![p]({IMG_URL})\n\n[erro.log]({LOG_URL})")

    _create_down(port)

    assert len(_local_files()) == 2
    assert _contents() == [b"A", b"B"]


@pytest.mark.parametrize("body", [
    "Só texto, sem nenhum link.",
    "[veja a doc](https://example.com/guia)",
    "[codigo](https://github.com/org/repo/blob/main/src/core/sync.py) e ![x](https://example.com/a.png)",
])
def test_ct04_corpo_sem_arquivo_comportamento_identico(body):
    port = FakePort()
    _remote(port, body)

    _create_down(port)

    expected = sync._compose_down_body(port.issues["77"])
    assert _body_file().read_text(encoding="utf-8") == expected
    assert port.downloads == []
    assert port.metadata_calls == []
    assert port.added_comments == []
    assert not _files_dir().exists()


# ── Grupo B ──────────────────────────────────────────────────────────────────

def test_ct05_comentario_novo_com_imagem_embutida_sincronizado():
    port = FakePort()
    _remote(port, "corpo sem arquivo")
    _create_down(port)
    assert _local_files() == []

    url = "https://user-images.githubusercontent.com/0/novo.png"
    port.files[url] = b"novo"
    port.comments["77"].append({"author": "breno", "date": "2026-11-09T11:00:00Z",
                                "body": f"olha ![novo]({url})"})
    _change_down(port)

    assert _contents() == [b"novo"]
    history = (BOARDS_DIR / BOARD / DEV / "77-exemplo-history.md").read_text(encoding="utf-8")
    assert f"![novo]({url})" in history


def test_ct06_comentario_novo_com_upload_sincronizado():
    port = FakePort()
    _remote(port, "corpo sem arquivo")
    _create_down(port)

    port.files[LOG_URL] = b"log"
    port.comments["77"].append({"author": "breno", "date": "2026-11-09T11:00:00Z",
                                "body": f"[erro.log]({LOG_URL})"})
    _change_down(port)

    assert _contents() == [b"log"]


def test_ct07_novo_comentario_nao_refaz_download_ja_sincronizado():
    port = FakePort()
    port.files[IMG_URL] = b"corpo"
    _remote(port, f"![p]({IMG_URL})")
    _create_down(port)
    assert port.downloads == [IMG_URL]

    port.files[LOG_URL] = b"comentario"
    port.comments["77"].append({"author": "b", "date": "", "body": f"[erro.log]({LOG_URL})"})
    _change_down(port)
    _change_down(port)

    assert port.downloads == [IMG_URL, LOG_URL]
    assert _contents() == [b"comentario", b"corpo"]


# ── Grupo C ──────────────────────────────────────────────────────────────────

def test_ct09_diretorio_move_com_os_3_arquivos_no_change_down():
    port = FakePort()
    port.files[IMG_URL] = b"bytes"
    _remote(port, f"![p]({IMG_URL})")
    _create_down(port)

    port.issues["77"].column = TESTES
    _change_down(port)

    assert not _files_dir(DEV).exists()
    assert not _body_file(DEV).exists()
    assert _body_file(TESTES).exists()
    assert (BOARDS_DIR / BOARD / TESTES / "77-exemplo-history.md").exists()
    assert (BOARDS_DIR / BOARD / TESTES / "77-exemplo-addcomment.md").exists()
    assert _contents(TESTES) == [b"bytes"]
    assert port.downloads == [IMG_URL]


def test_ct09_diretorio_move_quando_agente_move_os_3_arquivos_change_up():
    port = FakePort()
    port.files[IMG_URL] = b"bytes"
    _remote(port, f"![p]({IMG_URL})")
    _create_down(port)

    dest = BOARDS_DIR / BOARD / TESTES
    dest.mkdir(parents=True, exist_ok=True)
    for suffix in ("-body.md", "-history.md", "-addcomment.md"):
        (BOARDS_DIR / BOARD / DEV / f"77-exemplo{suffix}").rename(dest / f"77-exemplo{suffix}")

    item = sync.ChangeItem.of(sync.SyncEvent.CHANGE_UP, id="77", board=BOARD)
    sync._apply_change_up(BOARD, item, Board(port), ChangeQueue(), _config())

    assert not _files_dir(DEV).exists()
    assert _contents(TESTES) == [b"bytes"]


def test_delete_down_remove_diretorio_de_arquivos():
    port = FakePort()
    port.files[IMG_URL] = b"bytes"
    _remote(port, f"![p]({IMG_URL})")
    _create_down(port)
    assert _files_dir().exists()

    item = sync.ChangeItem.of(sync.SyncEvent.DELETE_DOWN, id="77", board=BOARD)
    sync._apply_delete_down(BOARD, item, Board(port), ChangeQueue())

    assert not _files_dir().exists()
    assert not _body_file().exists()


def test_arquivo_md_sincronizado_nao_e_confundido_com_issue_local():
    port = FakePort()
    url = "https://github.com/user-attachments/files/9/notas-body.md"
    port.files[url] = b"# nao sou issue"
    _remote(port, f"[notas-body.md]({url})")
    _create_down(port)

    queue = ChangeQueue()
    sync.detect_local_changes(BOARD, queue)

    assert len(_local_files()) == 1
    assert not _local_files()[0].name.endswith("-body.md")
    assert all(i.event != sync.SyncEvent.CREATE_UP.value for i in queue.items())


# ── Grupo D ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ext", DEFAULT_ALLOWED_FILE_TYPES)
def test_ct10_default_aceita_cada_tipo_da_lista(ext):
    port = FakePort()
    url = f"https://github.com/user-attachments/files/1/arquivo.{ext}"
    port.files[url] = b"ok"
    _remote(port, f"[arquivo.{ext}]({url})")

    _create_down(port)

    assert [f.suffix for f in _local_files()] == [f".{ext}"]
    assert port.added_comments == []


@pytest.mark.parametrize("ext", ["sh", "exe", "bat", "html"])
def test_ct10_default_recusa_tipo_fora_da_lista(ext):
    port = FakePort()
    pdf = "https://github.com/user-attachments/files/1/relatorio.pdf"
    other = f"https://github.com/user-attachments/files/2/script.{ext}"
    port.files[pdf] = b"pdf"
    port.files[other] = b"x"
    _remote(port, f"[relatorio.pdf]({pdf}) [script.{ext}]({other})")

    _create_down(port)

    assert [f.suffix for f in _local_files()] == [".pdf"]
    assert other not in port.downloads


def test_ct11_lista_declarada_substitui_default():
    port = FakePort()
    urls = {e: f"https://github.com/user-attachments/files/1/a.{e}" for e in ("zip", "mp4", "png")}
    for url in urls.values():
        port.files[url] = b"x"
    _remote(port, " ".join(f"[a.{e}]({u})" for e, u in urls.items()))

    _create_down(port, _config({"allowed-types": ["png", "mp4"]}))

    assert sorted(f.suffix for f in _local_files()) == [".mp4", ".png"]
    assert urls["zip"] not in port.downloads


def test_tipo_de_anexo_sem_extensao_resolvido_pelo_content_type():
    port = FakePort()
    exe = "https://github.com/user-attachments/assets/0000-exe"
    port.files[ASSET_URL] = b"png"
    port.files[exe] = b"MZ"
    port.meta[ASSET_URL] = {"size": 3, "content_type": "image/png"}
    port.meta[exe] = {"size": 2, "content_type": "application/x-msdownload"}
    _remote(port, f"![image]({ASSET_URL})\n<img width=\"10\" src=\"{exe}\">")

    _create_down(port)

    files = _local_files()
    assert [f.suffix for f in files] == [".png"]
    assert files[0].name.startswith("image-")
    assert exe not in port.downloads
    assert len(port.comments_with_marker("77")) == 1


# ── Grupo E ──────────────────────────────────────────────────────────────────

def test_ct12_sem_limite_nenhuma_recusa_por_tamanho():
    port = FakePort()
    port.files[IMG_URL] = b"grande"
    port.meta[IMG_URL] = {"size": 50 * 1024 * 1024, "content_type": "image/png"}
    _remote(port, f"![p]({IMG_URL})")

    _create_down(port)

    assert _contents() == [b"grande"]
    assert port.metadata_calls == []


def test_ct13_limite_declarado_recusa_excedente_mesmo_de_tipo_permitido():
    port = FakePort()
    small = "https://user-images.githubusercontent.com/0/small.png"
    big = "https://user-images.githubusercontent.com/0/big.png"
    port.files[small] = b"s"
    port.files[big] = b"b"
    port.meta[small] = {"size": 999_999, "content_type": "image/png"}
    port.meta[big] = {"size": 1_000_001, "content_type": "image/png"}
    _remote(port, f"![s]({small}) ![b]({big})")

    _create_down(port, _config({"max-size": 1_000_000}))

    assert _contents() == [b"s"]
    assert big not in port.downloads
    [comment] = port.comments_with_marker("77")
    assert "big.png" in comment and "tamanho acima do limite" in comment


def test_ct13_limite_aplicado_quando_tamanho_desconhecido_antes_do_download():
    port = FakePort()
    port.files[IMG_URL] = b"0123456789"
    port.meta[IMG_URL] = {"size": None, "content_type": None}
    _remote(port, f"![p]({IMG_URL})")

    _create_down(port, _config({"max-size": 5}))

    assert _local_files() == []
    assert len(port.comments_with_marker("77")) == 1


# ── Grupo F ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("file_sync", [None, {"on-reject": "aviso"}])
def test_ct14_primeira_recusa_aviso_comentario_unico(file_sync):
    port = FakePort()
    url = "https://github.com/user-attachments/files/3/script.exe"
    port.files[url] = b"MZ"
    body = f"Texto antes [script.exe]({url}) texto depois"
    _remote(port, body)

    _create_down(port, _config(file_sync))

    assert url not in port.downloads
    assert _local_files() == []
    assert body in _body_file().read_text(encoding="utf-8")
    assert len(port.added_comments) == 1
    comment = port.added_comments[0][1]
    assert "script.exe" in comment and "tipo não permitido" in comment
    assert NEED_HUMAN_LABEL not in port.issues["77"].labels


def test_ct16_mesmo_conjunto_recusado_sem_comentario_duplicado():
    port = FakePort()
    url = "https://github.com/user-attachments/files/3/script.exe"
    _remote(port, f"[script.exe]({url})")
    _create_down(port)

    _change_down(port)
    _change_down(port)

    assert len(port.comments_with_marker("77")) == 1


def test_ct17_conjunto_recusado_muda_novo_aviso():
    port = FakePort()
    exe = "https://github.com/user-attachments/files/3/script.exe"
    binf = "https://github.com/user-attachments/files/4/binario.bin"
    _remote(port, f"[script.exe]({exe})")
    _create_down(port)

    port.issues["77"].body = f"[binario.bin]({binf})"
    _change_down(port)

    comments = port.comments_with_marker("77")
    assert len(comments) == 2
    assert "binario.bin" in comments[1] and "script.exe" not in comments[1]


def test_aviso_publicado_nao_e_reprocessado_como_referencia():
    port = FakePort()
    exe = "https://github.com/user-attachments/files/3/script.exe"
    _remote(port, f"[script.exe]({exe})")
    _create_down(port)
    port.issues["77"].body = "removido"

    _change_down(port)

    assert len(port.comments_with_marker("77")) == 1
    assert port.downloads == []


# ── Grupo G ──────────────────────────────────────────────────────────────────

def test_ct18_silencioso_sem_mensagem_com_trace():
    port = FakePort()
    url = "https://github.com/user-attachments/files/3/script.exe"
    _remote(port, f"[script.exe]({url})")

    _create_down(port, _config({"on-reject": "silencioso"}))

    assert port.added_comments == []
    assert port.add_label_calls == []
    assert _local_files() == []
    lines = [l for l in _log_text().splitlines() if "TRACE - FileSync" in l and "recusado" in l]
    assert lines
    assert "script.exe" in lines[-1] and "tipo não permitido" in lines[-1]


# ── Grupo H ──────────────────────────────────────────────────────────────────

def _blocking_setup():
    port = FakePort()
    url = "https://github.com/user-attachments/files/3/script.exe"
    _remote(port, f"[script.exe]({url})", labels=["enhancement"])
    return port, url


def test_ct19_bloqueante_aviso_e_need_human():
    port, _ = _blocking_setup()

    _create_down(port, _config({"on-reject": "bloqueante"}))

    [comment] = port.comments_with_marker("77")
    assert "script.exe" in comment and "tipo não permitido" in comment
    assert NEED_HUMAN_LABEL in port.issues["77"].labels
    assert "/need_human" in _body_file().read_text(encoding="utf-8")


def test_ct20_bloqueante_reaplica_label_removida_manualmente():
    port, _ = _blocking_setup()
    config = _config({"on-reject": "bloqueante"})
    _create_down(port, config)

    port.remove_label(BOARD, "77", NEED_HUMAN_LABEL)
    _change_down(port, config)

    assert NEED_HUMAN_LABEL in port.issues["77"].labels
    assert len(port.add_label_calls) == 2
    assert "/need_human" in _body_file().read_text(encoding="utf-8")
    assert len(port.comments_with_marker("77")) == 1


def test_ct21_bloqueante_cessa_quando_arquivo_deixa_de_ser_referenciado():
    port, _ = _blocking_setup()
    config = _config({"on-reject": "bloqueante"})
    _create_down(port, config)
    port.remove_label(BOARD, "77", NEED_HUMAN_LABEL)

    port.issues["77"].body = "arquivo removido"
    _change_down(port, config)

    assert len(port.add_label_calls) == 1
    assert NEED_HUMAN_LABEL not in port.issues["77"].labels


# ── Grupo I ──────────────────────────────────────────────────────────────────

def test_ct22_permitido_e_recusado_juntos():
    port = FakePort()
    png = "https://user-images.githubusercontent.com/0/foto.png"
    exe = "https://github.com/user-attachments/files/5/virus.exe"
    port.files[png] = b"foto"
    body = f"![foto]({png}) e [virus.exe]({exe})"
    _remote(port, body)

    _create_down(port)

    assert _contents() == [b"foto"]
    assert exe not in port.downloads
    assert body in _body_file().read_text(encoding="utf-8")
    [comment] = port.comments_with_marker("77")
    assert "virus.exe" in comment and "foto.png" not in comment


def test_ct23_nomes_colidentes_permanecem_distintos():
    port = FakePort()
    a = "https://user-images.githubusercontent.com/1/imagem.png"
    b = "https://user-images.githubusercontent.com/2/imagem.png"
    port.files[a] = b"A"
    port.files[b] = b"B"
    _remote(port, f"![imagem]({a})")
    port.comments["77"].append({"author": "x", "date": "", "body": f"![imagem]({b})"})

    _create_down(port)

    files = _local_files()
    assert len(files) == 2
    assert _contents() == [b"A", b"B"]


def test_falha_de_download_nao_bloqueia_texto():
    port = FakePort()
    port.download_error = OSError("rede indisponível")
    _remote(port, f"![p]({IMG_URL})")

    _create_down(port)

    assert _body_file().exists()
    assert _local_files() == []
    assert port.added_comments == []


# ── Extração e adapter ───────────────────────────────────────────────────────

def test_extract_links_markdown_e_html():
    text = (f"![a]({IMG_URL}) [erro.log](<{LOG_URL}>) [t]({ASSET_URL} \"titulo\") "
            f"<img alt=\"x\" src=\"{ASSET_URL}2\"> ![a]({IMG_URL})")
    urls = [r.url for r in extract_links(text)]
    assert urls == [IMG_URL, LOG_URL, ASSET_URL, ASSET_URL + "2"]


@pytest.mark.parametrize("url, expected", [
    (IMG_URL, True),
    ("https://private-user-images.githubusercontent.com/1/2.png?jwt=x", True),
    (ASSET_URL, True),
    ("https://github.com/user-attachments/files/1/erro.log", True),
    (LOG_URL, True),
    ("https://github.com/org/repo/assets/1/abc", True),
    ("https://github.com/org/repo/blob/main/a.py", False),
    ("https://github.com/org/repo/issues/1", False),
    ("https://example.com/a.png", False),
    ("http://user-images.githubusercontent.com/0/img.png", False),
])
def test_github_adapter_is_attachment(url, expected):
    assert GitHubBoardAdapter().is_attachment(url) is expected
