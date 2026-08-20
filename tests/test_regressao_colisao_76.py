"""Casos de Teste — Regressão composta da colisão #76 (issue #148).

Contexto: o incidente #76/#97 nasceu do fallback "primeiro resultado do
rglob" em `_find_issue_files`/`detect_local_changes`, que escolhia
arbitrariamente entre candidatos com o mesmo prefixo numérico e sobrescrevia
o conteúdo de uma issue com o de um arquivo não relacionado (órfão).

As duas tasks anteriores da story #140 (US-03) já corrigiram os mecanismos
isoladamente e têm suítes próprias:

- `tests/test_find_issue_files_resolution.py` — resolução determinística de
  `_find_issue_files` (issue #146 / ADR-01, RN-005/RN-006).
- `tests/test_orphan_detection.py` — isolamento de arquivos órfãos via
  `record_orphan` dentro de `detect_local_changes` (issue #147).

Esta suíte é exclusivamente de INTEGRAÇÃO e REGRESSÃO: não reimplementa nem
duplica a lógica de resolução/detecção testada nas suítes acima. Ela compõe
os dois mecanismos no fluxo real e completo:

    detect_local_changes(board_id, queue)
        -> fila (ChangeQueue)
        -> apply_changes(board_obj, queue, config)
        -> _apply_change_up (via board_obj.update_issue / apply_commands)

usando um fake `BoardPort` (mesmo padrão de `tests/test_sync_optimization.py`)
para capturar exatamente o que seria enviado ao board real, e confirmando
que o conteúdo do arquivo órfão nunca alcança o board.

Cenário-base reproduzido (fixture `colisao_76_env` + variações):

- issue `76` conhecida no snapshot, com `body_path` **obsoleto** (arquivo que
  não existe mais no caminho registrado — foi movido/renomeado);
- o body **legítimo** da issue `76`, já movido para outra coluna, com nome de
  arquivo diferente do registrado no snapshot;
- um arquivo **órfão** com o mesmo prefixo numérico `76-` em outra coluna, não
  relacionado à issue `76` (o artefato que, no incidente real, foi escolhido
  por engano).

Dois sub-cenários são cobertos como testes separados (item 1 dos critérios de
aceite do body de #148):

- **resolução inequívoca**: o body legítimo movido é localizável por nome
  completo (único candidato) -> `_find_issue_files` o resolve e o fluxo
  completo aplica a atualização usando o conteúdo do arquivo legítimo;
- **resolução ambígua**: dois candidatos disputam o mesmo prefixo numérico
  sem nenhum deles ser o path exato registrado no snapshot -> nenhum evento é
  enfileirado para a issue 76 e o(s) candidato(s) são isolados via
  `record_orphan` (verificado via `.pipe/orphanFiles.json`, mesmo mecanismo
  já validado em `tests/test_orphan_detection.py` — não duplicamos a
  asserção de conteúdo do registro, apenas confirmamos a integração ponta a
  ponta).
"""

import json
import time
from pathlib import Path

import pytest

from src.core.board import Board, BoardPort, Issue, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.sync import apply_changes, detect_local_changes

BOARD_ID = "task"
ISSUE_ID = "76"
ORPHAN_FILE_NAME = "orphanFiles.json"


# ══════════════════════════════════════════════════════════════════════════════
# Fake BoardPort (mesmo padrão de tests/test_sync_optimization.py)
# ══════════════════════════════════════════════════════════════════════════════

class FakePort(BoardPort):
    """Fake de BoardPort que apenas registra chamadas, nunca bate na rede."""

    def __init__(self):
        self.calls = []

    def connect(self, config):
        pass

    def sync_boards(self, boards):
        pass

    def list_issues(self, board_id):
        return []

    def list_issues_since(self, board_id, since):
        return []

    def get_issue(self, board_id, issue_id, fullsync=False):
        self.calls.append(("get_issue", issue_id, fullsync))
        return Issue(id=issue_id, title="", body="", column="")

    def create_issue(self, board_id, title, body, column):
        return Issue(id="1", title=title, body=body, column=column)

    def move_issue(self, board_id, issue_id, column, from_column=None):
        self.calls.append(("move_issue", issue_id, column, from_column))

    def update_issue(self, board_id, issue_id, title=None, body=None):
        self.calls.append(("update_issue", issue_id, title, body))

    def add_comment(self, board_id, issue_id, comment):
        self.calls.append(("add_comment", issue_id, comment))

    def list_comments(self, board_id, issue_id):
        return []

    def close_issue(self, board_id, issue_id):
        self.calls.append(("close", issue_id))

    def reopen_issue(self, board_id, issue_id):
        self.calls.append(("reopen", issue_id))

    def set_labels(self, board_id, issue_id, labels):
        self.calls.append(("set_labels", issue_id, sorted(labels)))

    def add_label(self, board_id, issue_id, label):
        pass

    def remove_label(self, board_id, issue_id, label):
        pass

    def set_parent(self, board_id, issue_id, parent_id, known_current=None):
        self.calls.append(("set_parent", issue_id, parent_id))

    def set_children(self, board_id, issue_id, children_ids, known_current=None):
        self.calls.append(("set_children", issue_id, sorted(children_ids)))

    def set_blocked_by(self, board_id, issue_id, blocker_ids, known_current=None):
        self.calls.append(("set_blocked_by", issue_id, sorted(blocker_ids)))

    def set_blocks(self, board_id, issue_id, blocked_ids, known_current=None):
        self.calls.append(("set_blocks", issue_id, sorted(blocked_ids)))

    def archive_issue(self, board_id, issue_id):
        self.calls.append(("archive", issue_id))

    def unarchive_issue(self, board_id, issue_id):
        self.calls.append(("unarchive", issue_id))

    def update_issue_calls(self):
        return [c for c in self.calls if c[0] == "update_issue"]

    def relation_calls(self):
        return [c for c in self.calls
                if c[0] in ("set_parent", "set_children", "set_blocked_by", "set_blocks")]


# ══════════════════════════════════════════════════════════════════════════════
# Fixture base: estrutura de board + snapshot com body_path obsoleto da #76
# ══════════════════════════════════════════════════════════════════════════════

ORPHAN_TITLE = "Órfão nada a ver com a 76"
ORPHAN_BODY = "Conteúdo do arquivo órfão que NUNCA deve alcançar o board."

LEGIT_TITLE = "Corrigir bug real da issue 76"
LEGIT_BODY = "Conteúdo legítimo da issue 76, já movido de coluna."


@pytest.fixture
def colisao_76_env(tmp_path, monkeypatch):
    """Monta o cenário-base do incidente #76: snapshot com body_path obsoleto
    + colunas reais, sem ainda criar os arquivos body em disco (cada teste
    decide o sub-cenário: resolução inequívoca vs ambígua)."""
    monkeypatch.chdir(tmp_path)

    boards_base = tmp_path / ".pipe" / "boards"
    board_dir = boards_base / BOARD_ID
    backlog = board_dir / "backlog"
    doing = board_dir / "doing"
    done = board_dir / "done"
    for col in (backlog, doing, done):
        col.mkdir(parents=True)

    # body_path obsoleto: registrado no snapshot, mas o arquivo não existe
    # mais nesse caminho (foi "movido"/renomeado).
    obsolete_path = backlog / f"{ISSUE_ID}-corrigir_bug-body.md"

    snapshot = {
        "board": {"backlog": "Backlog", "doing": "Doing", "done": "Done"},
        "issues": [
            {
                "id": ISSUE_ID,
                "column": "backlog",
                "body_path": str(obsolete_path),
                "body_mtime": "100.0",
                "updated_at": "2026-07-01T10:00:00Z",
                "status": "ok",
                "labels": ["incidente"],
                "parent": None,
                "children": [],
                "blocked_by": [],
                "blocks": [],
                "archived": False,
                "state": "open",
            }
        ],
        "last_sync": "2026-07-01T10:00:00Z",
        "last_board_update": "2026-07-01T10:00:00Z",
    }
    snap_file = board_dir / "snapshot.json"
    snap_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    monkeypatch.setattr("src.core.sync.BOARDS_DIR", boards_base)
    monkeypatch.setattr("src.core.snapshot.BOARDS_DIR", boards_base)

    pipe_dir = tmp_path / ".pipe"
    queue_file = pipe_dir / "changeQueue.json"
    monkeypatch.setattr("src.core.change_queue.PIPE_DIR", pipe_dir)
    monkeypatch.setattr("src.core.change_queue.QUEUE_FILE", queue_file)
    monkeypatch.setattr("src.core.sync.PIPE_DIR", pipe_dir)
    monkeypatch.setattr("src.core.sync.ORPHAN_FILE", pipe_dir / ORPHAN_FILE_NAME)

    return {
        "tmp_path": tmp_path,
        "board_dir": board_dir,
        "backlog": backlog,
        "doing": doing,
        "done": done,
        "obsolete_path": obsolete_path,
        "snap_file": snap_file,
        "orphan_file": pipe_dir / ORPHAN_FILE_NAME,
    }


def _snapshot_issues(snap_file: Path) -> list[dict]:
    return json.loads(snap_file.read_text(encoding="utf-8"))["issues"]


def _run_full_cycle(env, config=None):
    """Executa o fluxo completo detect_local_changes -> apply_changes."""
    queue = ChangeQueue()
    detect_local_changes(BOARD_ID, queue)

    port = FakePort()
    board_obj = Board(port)
    apply_changes(board_obj, queue, config or {})

    return port, queue


# ══════════════════════════════════════════════════════════════════════════════
# Sub-cenário 1: resolução INEQUÍVOCA — body legítimo movido, único candidato
# ══════════════════════════════════════════════════════════════════════════════

class TestResolucaoInequivocaFluxoCompleto:
    """Body legítimo da 76 foi movido para `doing`, mantendo o MESMO nome de
    arquivo (`Path(body_path).name`) registrado no snapshot — apenas em outra
    coluna. Como nenhum outro arquivo no board compartilha esse nome completo
    nem esse prefixo numérico, `_find_issue_files` resolve pelo passo 2/3
    (nome completo, único candidato) e `detect_local_changes` também aceita
    (grupo de candidatos por prefixo numérico "76-" com exatamente 1 item).
    Um órfão não relacionado com prefixo numérico DIFERENTE em `done` deve
    ser ignorado durante todo o fluxo (nunca alcança o board nem interfere
    na resolução da 76)."""

    ORPHAN_ID = "999"

    def _build(self, env):
        # Body legítimo: MESMO nome do registrado no snapshot
        # ("76-corrigir_bug-body.md"), só que movido para "doing".
        legit_name = env["obsolete_path"].name
        legit = env["doing"] / legit_name
        legit.write_text(f"# {LEGIT_TITLE}\n\n{LEGIT_BODY}\n", encoding="utf-8")
        legit_slug = legit.stem.removesuffix("-body")
        (env["doing"] / f"{legit_slug}-addcomment.md").write_text("", encoding="utf-8")

        # Arquivo órfão: prefixo numérico DIFERENTE (não relacionado à issue
        # 76), em outra coluna — não interfere na resolução da 76 em nenhum
        # nível (nem por nome completo, nem por prefixo numérico).
        orphan = env["done"] / f"{self.ORPHAN_ID}-artefato_nao_relacionado-body.md"
        orphan.write_text(f"# {ORPHAN_TITLE}\n\n{ORPHAN_BODY}\n", encoding="utf-8")
        (env["done"] / f"{self.ORPHAN_ID}-artefato_nao_relacionado-addcomment.md").write_text(
            "", encoding="utf-8"
        )

        return legit, orphan

    def test_apply_changes_usa_conteudo_legitimo_nao_orfao(self, colisao_76_env):
        env = colisao_76_env
        legit, orphan = self._build(env)

        port, queue = _run_full_cycle(env)

        update_calls = port.update_issue_calls()
        assert update_calls, (
            "Esperava exatamente uma chamada update_issue para a issue 76 "
            "(resolução inequívoca do body legítimo movido)"
        )
        assert len(update_calls) == 1
        _, issue_id, title, body = update_calls[0]
        assert issue_id == ISSUE_ID
        assert title == LEGIT_TITLE
        assert LEGIT_BODY in body
        assert ORPHAN_TITLE not in title
        assert ORPHAN_BODY not in body

    def test_zero_chamadas_usam_conteudo_do_orfao(self, colisao_76_env):
        env = colisao_76_env
        self._build(env)

        port, queue = _run_full_cycle(env)

        for call in port.calls:
            call_repr = " ".join(str(part) for part in call)
            assert ORPHAN_TITLE not in call_repr, (
                f"Chamada ao board usou conteúdo do arquivo órfão: {call}"
            )
            assert ORPHAN_BODY not in call_repr, (
                f"Chamada ao board usou conteúdo do arquivo órfão: {call}"
            )

    def test_fila_fica_vazia_apos_apply_changes(self, colisao_76_env):
        env = colisao_76_env
        self._build(env)

        _, queue = _run_full_cycle(env)

        assert queue.getNext() is None

    def test_snapshot_da_76_reflete_arquivo_legitimo_nao_orfao(self, colisao_76_env):
        env = colisao_76_env
        legit, _ = self._build(env)

        _run_full_cycle(env)

        issues = _snapshot_issues(env["snap_file"])
        assert len(issues) == 1
        issue_76 = issues[0]
        assert issue_76["id"] == ISSUE_ID
        assert Path(issue_76["body_path"]).resolve() == legit.resolve()
        assert issue_76["column"] == "doing"


# ══════════════════════════════════════════════════════════════════════════════
# Sub-cenário 2: resolução AMBÍGUA — dois candidatos, nenhum é o path exato
# ══════════════════════════════════════════════════════════════════════════════

class TestResolucaoAmbiguaFluxoCompleto:
    """Nenhum arquivo existe mais no body_path registrado no snapshot, e dois
    candidatos disputam o mesmo prefixo numérico "76-" com nomes diferentes
    entre si (nenhum é o nome exato do registrado) -> ambíguo. O fluxo
    completo não deve gerar nenhuma chamada ao board para a issue 76, e o
    isolamento via record_orphan deve ser acionado."""

    def _build(self, env):
        candidate_a = env["doing"] / f"{ISSUE_ID}-versao_a-body.md"
        candidate_b = env["done"] / f"{ISSUE_ID}-versao_b-body.md"
        candidate_a.write_text("# Versão A\n\nconteúdo A\n", encoding="utf-8")
        candidate_b.write_text(f"# {ORPHAN_TITLE}\n\n{ORPHAN_BODY}\n", encoding="utf-8")
        return candidate_a, candidate_b

    def test_nenhuma_chamada_update_issue_para_76(self, colisao_76_env):
        env = colisao_76_env
        self._build(env)

        port, queue = _run_full_cycle(env)

        update_calls = [c for c in port.update_issue_calls() if c[1] == ISSUE_ID]
        assert update_calls == [], (
            f"Esperava zero chamadas update_issue para #76 em cenário ambíguo, "
            f"mas obteve: {update_calls}"
        )

    def test_nenhuma_chamada_de_relacao_usa_bloco_at_do_candidato(self, colisao_76_env):
        env = colisao_76_env
        candidate_a, candidate_b = self._build(env)
        # Injeta comandos de relação no candidato que, se resolvido por
        # engano, tentaria alterar parent/blocked_by da issue 76.
        candidate_b.write_text(
            f"# {ORPHAN_TITLE}\n\n{ORPHAN_BODY}\n\n@---\n/parent #999\n/blocked_by #888\n",
            encoding="utf-8",
        )

        port, queue = _run_full_cycle(env)

        relation_calls = [c for c in port.relation_calls() if c[1] == ISSUE_ID]
        assert relation_calls == [], (
            f"Nenhuma chamada de relação para #76 deveria ocorrer a partir "
            f"de um candidato ambíguo, mas obteve: {relation_calls}"
        )

    def test_fila_vazia_para_issue_76_apos_ciclo_completo(self, colisao_76_env):
        env = colisao_76_env
        self._build(env)

        _, queue = _run_full_cycle(env)

        assert queue.getNext() is None

    def test_snapshot_da_76_nao_e_corrompido_com_dados_do_candidato(self, colisao_76_env):
        env = colisao_76_env
        self._build(env)
        before = _snapshot_issues(env["snap_file"])

        _run_full_cycle(env)

        after = _snapshot_issues(env["snap_file"])
        assert after == before, (
            "O snapshot da issue 76 não deve mudar quando a resolução é "
            "ambígua (nenhum candidato inequívoco)"
        )

    def test_isolamento_via_record_orphan_e_acionado(self, colisao_76_env):
        env = colisao_76_env
        self._build(env)

        _run_full_cycle(env)

        assert env["orphan_file"].exists(), (
            "Esperava que o mecanismo de isolamento (record_orphan) fosse "
            "acionado para os candidatos ambíguos da issue 76 — verificação "
            "de integração ponta a ponta com o mecanismo da task anterior "
            "(#147), sem duplicar a asserção de conteúdo do registro."
        )
        entries = json.loads(env["orphan_file"].read_text(encoding="utf-8"))
        assert any(e["apparent_id"] == ISSUE_ID for e in entries)


# ══════════════════════════════════════════════════════════════════════════════
# Determinismo: resultado não depende de ordem de criação dos candidatos
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterminismoDaResolucao:
    """Critério de aceite 4: o resultado não deve depender da ordem de
    iteração de filesystem. Varia a ordem de criação dos arquivos entre
    execuções e confirma que a conclusão (ambíguo -> zero chamadas) é
    estável."""

    @pytest.mark.parametrize("invert_order", [False, True])
    def test_cenario_ambiguo_e_estavel_independente_da_ordem_de_criacao(
        self, colisao_76_env, invert_order
    ):
        env = colisao_76_env
        pairs = [
            (env["doing"] / f"{ISSUE_ID}-versao_a-body.md", "# Versão A\n\nconteúdo A\n"),
            (env["done"] / f"{ISSUE_ID}-versao_b-body.md", f"# {ORPHAN_TITLE}\n\n{ORPHAN_BODY}\n"),
        ]
        if invert_order:
            pairs = list(reversed(pairs))
        for path, content in pairs:
            path.write_text(content, encoding="utf-8")

        port, queue = _run_full_cycle(env)

        update_calls = [c for c in port.update_issue_calls() if c[1] == ISSUE_ID]
        assert update_calls == [], (
            f"Resultado da resolução ambígua não deve depender da ordem de "
            f"criação dos arquivos (invert_order={invert_order}); "
            f"chamadas obtidas: {update_calls}"
        )
        assert queue.getNext() is None

    @pytest.mark.parametrize("invert_order", [False, True])
    def test_cenario_inequivoco_e_estavel_independente_da_ordem_de_criacao(
        self, colisao_76_env, invert_order
    ):
        env = colisao_76_env
        legit_path = env["doing"] / env["obsolete_path"].name
        orphan_path = env["done"] / "999-artefato_nao_relacionado-body.md"
        pairs = [
            (legit_path, f"# {LEGIT_TITLE}\n\n{LEGIT_BODY}\n"),
            (orphan_path, f"# {ORPHAN_TITLE}\n\n{ORPHAN_BODY}\n"),
        ]
        if invert_order:
            pairs = list(reversed(pairs))
        for path, content in pairs:
            path.write_text(content, encoding="utf-8")

        port, queue = _run_full_cycle(env)

        update_calls = port.update_issue_calls()
        assert len(update_calls) == 1, (
            f"Resolução inequívoca deveria produzir exatamente 1 update_issue "
            f"independente da ordem de criação (invert_order={invert_order})"
        )
        _, issue_id, title, body = update_calls[0]
        assert issue_id == ISSUE_ID
        assert title == LEGIT_TITLE
        assert ORPHAN_BODY not in body


# ══════════════════════════════════════════════════════════════════════════════
# Auto-referência (/parent #76 no próprio body) não interfere na composição
# ══════════════════════════════════════════════════════════════════════════════

class TestAutoReferenciaNaoInterfereNaComposicao:
    """Cobertura opcional citada no body (RN-001, já entregue por outra
    story): um body legítimo com `/parent #76` (auto-referência) não deve
    interferir na composição dos dois mecanismos desta task. Não
    reimplementamos a sanitização aqui — apenas garantimos que ela e a
    resolução determinística/isolamento de órfãos coexistem sem regressão."""

    def test_fluxo_completo_nao_quebra_com_auto_referencia_no_body_legitimo(
        self, colisao_76_env
    ):
        env = colisao_76_env
        legit = env["doing"] / env["obsolete_path"].name
        legit.write_text(
            f"# {LEGIT_TITLE}\n\n{LEGIT_BODY}\n\n@---\n/parent #{ISSUE_ID}\n",
            encoding="utf-8",
        )
        orphan = env["done"] / "999-artefato_nao_relacionado-body.md"
        orphan.write_text(f"# {ORPHAN_TITLE}\n\n{ORPHAN_BODY}\n", encoding="utf-8")

        port, queue = _run_full_cycle(env)

        update_calls = port.update_issue_calls()
        assert len(update_calls) == 1
        assert update_calls[0][1] == ISSUE_ID

        # A auto-referência sanitizada nunca deve resultar em set_parent(76, 76).
        self_ref_calls = [c for c in port.calls if c[0] == "set_parent" and c[2] == ISSUE_ID]
        assert self_ref_calls == [], (
            f"Sanitização de auto-referência regrediu: {self_ref_calls}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
