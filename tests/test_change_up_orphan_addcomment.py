"""Regressão: loop infinito de change-up por addcomment órfão em coluna antiga.

Quando uma issue muda de coluna, sidecars (`-addcomment`/`-history`) podiam
ficar para trás na coluna antiga. A detecção local (`detect_local_changes`)
varre `rglob(slug-addcomment)` em TODAS as colunas e marcava change-up enquanto
houvesse um addcomment não-vazio em qualquer lugar; mas `_apply_change_up` só
lia/limpava o addcomment ao lado do body (coluna atual). Resultado: o addcomment
órfão era detectado todo ciclo e nunca processado -> change-up em loop infinito
(observado em produção com o bug #327: addcomment de 5k em analise-tecnica/
enquanto o body já estava em correcao/).

Correção: `_apply_change_up` processa o addcomment de QUALQUER coluna (posta uma
vez) e remove os sidecars órfãos fora da coluna atual, encerrando o loop.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import sync
from src.core.board import Board, BoardPort, ChangeItem, Issue, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


class RecordingPort(BoardPort):
    def __init__(self):
        self.comments = []

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def list_issues_since(self, board_id, since): return []
    def get_issue(self, board_id, issue_id, fullsync=False):
        return Issue(id=issue_id, title="", body="", column="")
    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)
    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment):
        self.comments.append((issue_id, comment))
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass
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


def _mk(board_id, column, issue_id, slug, body_text):
    d = Path(".pipe/boards") / board_id / column
    d.mkdir(parents=True, exist_ok=True)
    body = d / f"{issue_id}-{slug}-body.md"
    body.write_text(body_text, encoding="utf-8")
    return body, d


def _snap(board_id, issue_id, column, body_path):
    snap = Snapshot(board_id).load()
    snap.issues.append({
        "id": issue_id, "column": column, "status": "ok",
        "labels": [], "parent": None, "children": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
        "body_path": str(body_path),
        "body_mtime": str(body_path.stat().st_mtime),
    })
    snap.save()


def _drain_change_up(queue):
    ids = []
    while True:
        it = queue.getNext()
        if it is None:
            break
        if it.event == SyncEvent.CHANGE_UP.value:
            ids.append(it.id)
        queue.remove(it.uuid)
    return ids


def test_stale_addcomment_in_old_column_posted_once_and_cleaned():
    slug = "login-bug"
    body, correcao_dir = _mk("bug", "correcao", "327", slug,
                             "# Login bug\n\ncorpo\n")
    # Sidecar órfão: addcomment NÃO-vazio numa coluna antiga.
    old_dir = Path(".pipe/boards/bug/analise-tecnica")
    old_dir.mkdir(parents=True, exist_ok=True)
    stale_ac = old_dir / f"327-{slug}-addcomment.md"
    stale_ac.write_text("## Análise técnica\n\nconteúdo relevante\n",
                        encoding="utf-8")
    (old_dir / f"327-{slug}-history.md").write_text("velho\n", encoding="utf-8")
    # addcomment da coluna atual vazio.
    (correcao_dir / f"327-{slug}-addcomment.md").write_text("", encoding="utf-8")

    _snap("bug", "327", "correcao", body)

    port = RecordingPort()
    sync._apply_change_up(
        "bug", ChangeItem.of(SyncEvent.CHANGE_UP, id="327", board="bug"),
        Board(port), ChangeQueue(), config=None)

    # Postou o comentário órfão exatamente uma vez.
    assert port.comments == [("327", "## Análise técnica\n\nconteúdo relevante")]
    # Sidecar órfão removido (não re-dispara detecção).
    assert not stale_ac.exists()
    assert not (old_dir / f"327-{slug}-history.md").exists()


def test_no_change_up_loop_after_apply():
    slug = "login-bug"
    body, correcao_dir = _mk("bug", "correcao", "327", slug,
                             "# Login bug\n\ncorpo\n")
    old_dir = Path(".pipe/boards/bug/analise-tecnica")
    old_dir.mkdir(parents=True, exist_ok=True)
    (old_dir / f"327-{slug}-addcomment.md").write_text(
        "texto\n", encoding="utf-8")
    (correcao_dir / f"327-{slug}-addcomment.md").write_text("", encoding="utf-8")
    _snap("bug", "327", "correcao", body)

    port = RecordingPort()
    sync._apply_change_up(
        "bug", ChangeItem.of(SyncEvent.CHANGE_UP, id="327", board="bug"),
        Board(port), ChangeQueue(), config=None)

    # Após processar, uma nova detecção NÃO deve re-enfileirar change-up.
    q2 = ChangeQueue()
    sync.detect_local_changes("bug", q2)
    assert "327" not in _drain_change_up(q2)
