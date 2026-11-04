"""Casos de teste da issue #339 — Duplicidade ao criar sub-issue.

Cobre os 3 critérios de aceitação da issue #339 (investigação e documentação
da causa raiz, sem correção de código nesta entrega):

- CA-1: reproduz e confirma a triplicação de sub-issues (Tasks) via
  `create-up`, a partir de uma Story.
- CA-2: documenta a causa citando arquivo/função/variável/chamada exatos —
  `src/core/sync.py::_apply_create_up`, chamada a
  `_filter_suspended_cross_board_parent(board_id, created.id, cmds, config)`,
  onde `config` não é parâmetro nem está definido na função.
- CA-3: confirma, sem chamada de rede, que o mecanismo `participation_intent`
  (issue #310) não participa da causa quando a Story e as Tasks estão no
  mesmo board.

Nota sobre o estado destes testes: a issue #339 é de investigação e
documentação — a correção do bug (`config` não propagado) é entrega futura,
fora de escopo aqui. Os testes abaixo reproduzem e confirmam o comportamento
ATUAL do motor (o bug está presente no código hoje). Eles continuam válidos
como documentação executável da causa raiz após a correção futura: nesse
momento, quem alterar `_apply_create_up` deve también revisar
deliberadamente estes casos (ex.: trocar `pytest.raises(NameError)` pela
asserção do comportamento correto), nunca apenas silenciar a falha.

Também documenta (CT-05) um achado sobre
`tests/test_sanitize_relations.py::test_apply_create_up_self_reference_not_sent_to_adapter`:
esse teste não exercita `_apply_create_up` de fato, por usar `id=` em vez de
`identifier=` na construção do `ChangeItem.of` — achado desta etapa de QA, a
ser corrigido pelo desenvolvimento junto da correção do bug principal.
"""

import sys
from pathlib import Path

import pytest

# Permite importar o pacote src quando rodado de qualquer lugar.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.board import Board, BoardPort, ChangeItem, Issue, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.snapshot import Snapshot


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola .pipe/ em um diretório temporário por teste."""
    monkeypatch.chdir(tmp_path)
    yield


# ══════════════════════════════════════════════════════════════════════════
# Fake adapter que registra chamadas em vez de bater na rede
# ══════════════════════════════════════════════════════════════════════════

class FakePort(BoardPort):
    """BoardPort fake: cria issues com ids sequenciais e registra chamadas."""

    def __init__(self, start_id: int = 100):
        self.calls = []
        self._next_id = start_id

    def connect(self, config): pass
    def sync_boards(self, boards): pass
    def list_issues(self, board_id): return []
    def list_issues_since(self, board_id, since): return []

    def get_issue(self, board_id, issue_id, fullsync=False):
        return Issue(id=issue_id, title="", body="", column="")

    def create_issue(self, board_id, title, body, column):
        self._next_id += 1
        new_id = str(self._next_id)
        self.calls.append(("create_issue", board_id, title, new_id))
        return Issue(id=new_id, title=title, body=body, column=column)

    def move_issue(self, board_id, issue_id, column, from_column=None): pass
    def update_issue(self, board_id, issue_id, title=None, body=None): pass
    def add_comment(self, board_id, issue_id, comment): pass
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): pass
    def reopen_issue(self, board_id, issue_id): pass

    def set_labels(self, board_id, issue_id, labels):
        self.calls.append(("set_labels", issue_id, sorted(labels)))

    def add_label(self, board_id, issue_id, label): pass
    def remove_label(self, board_id, issue_id, label): pass

    def set_parent(self, board_id, issue_id, parent_id, known_current=None):
        self.calls.append(("set_parent", issue_id, parent_id))

    def set_children(self, board_id, issue_id, children_ids, known_current=None):
        self.calls.append(("set_children", issue_id, sorted(children_ids)))

    def set_blocked_by(self, board_id, issue_id, blocker_ids, known_current=None):
        self.calls.append(("set_blocked_by", issue_id, sorted(blocker_ids)))

    def set_blocks(self, board_id, issue_id, blocked_ids, known_current=None):
        self.calls.append(("set_blocks", issue_id, sorted(blocked_ids)))

    def archive_issue(self, board_id, issue_id): pass
    def unarchive_issue(self, board_id, issue_id): pass


def _new_body_file(tmp_path: Path, board_id: str, column: str, filename: str,
                    title: str, commands_block: str | None) -> Path:
    """Cria um -body.md novo (sem ID) e o registra no snapshot como
    'pending-create', simulando uma issue local recém-criada pelo agente."""
    col_dir = tmp_path / board_id / column
    col_dir.mkdir(parents=True, exist_ok=True)
    body_path = col_dir / filename

    content = f"# {title}\n\nConteudo de teste.\n"
    if commands_block:
        content += f"\n@---\n{commands_block}\n"
    body_path.write_text(content, encoding="utf-8")

    snap = Snapshot(board_id).load()
    snap.issues.append({
        "body_path": str(body_path),
        "column": column,
        "status": "pending-create",
    })
    snap.save()
    return body_path


def _create_up_item(body_path: Path, board_id: str) -> ChangeItem:
    """Constrói o ChangeItem correto para create-up: a busca em
    _apply_create_up usa item.identifier, nunca item.id."""
    return ChangeItem.of(SyncEvent.CREATE_UP, identifier=str(body_path), board=board_id)


# ══════════════════════════════════════════════════════════════════════════
# Grupo A — Reprodução determinística do bug (CA-1, CA-2)
# ══════════════════════════════════════════════════════════════════════════

class TestCT01NameErrorAoCriarComParent:
    """CT-01 — NameError ao criar sub-issue com /parent no create-up."""

    def test_name_error_e_levantado_com_parent(self, tmp_path):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        board_obj = Board(port)
        item = _create_up_item(body_path, board_id)
        queue = ChangeQueue()

        with pytest.raises(NameError, match="config"):
            sync._apply_create_up(board_id, item, board_obj, queue=queue)

    def test_issue_ja_foi_criada_no_board_antes_do_erro(self, tmp_path):
        """A issue já existe no board remoto quando o erro ocorre — é o fato
        que torna o retry (recriação) perigoso."""
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        board_obj = Board(port)
        item = _create_up_item(body_path, board_id)
        queue = ChangeQueue()

        with pytest.raises(NameError):
            sync._apply_create_up(board_id, item, board_obj, queue=queue)

        create_calls = [c for c in port.calls if c[0] == "create_issue"]
        assert len(create_calls) == 1, (
            "create_issue deveria ter sido chamado exatamente uma vez antes do erro"
        )

    def test_arquivo_local_nao_e_renomeado_apos_o_erro(self, tmp_path):
        """A função é interrompida antes de atualizar o arquivo local com o
        ID atribuído — prova de que a atualização local fica incompleta."""
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        board_obj = Board(port)
        item = _create_up_item(body_path, board_id)
        queue = ChangeQueue()

        with pytest.raises(NameError):
            sync._apply_create_up(board_id, item, board_obj, queue=queue)

        assert body_path.exists(), "o -body.md original deveria permanecer intacto (sem rename)"
        col_dir = tmp_path / board_id / "backlog"
        remaining_files = sorted(p.name for p in col_dir.glob("*"))
        assert remaining_files == ["nova-tarefa-body.md"], (
            "nenhum arquivo com ID deveria ter sido criado por rename"
        )


class TestCT02CicloCompletoRecriaAcadaTentativa:
    """CT-02 — apply_changes recria a issue a cada tentativa (triplicação)."""

    @pytest.mark.parametrize("max_attempts", [1, 3, 5])
    def test_create_issue_chamado_n_vezes_para_max_attempts_n(self, tmp_path, max_attempts):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        board_obj = Board(port)
        queue = ChangeQueue()
        queue.add(_create_up_item(body_path, board_id))

        config = {"sync": {"max_attempts": max_attempts}}
        for _ in range(max_attempts):
            sync.apply_changes(board_obj, queue, config=config)

        create_calls = [c for c in port.calls if c[0] == "create_issue"]
        assert len(create_calls) == max_attempts, (
            f"esperado {max_attempts} issues criadas (1 por tentativa), "
            f"obtido {len(create_calls)}"
        )
        # IDs distintos: cada tentativa cria uma issue NOVA, não reaproveita.
        ids = [c[3] for c in create_calls]
        assert len(set(ids)) == max_attempts

    def test_item_sai_da_fila_apos_esgotar_tentativas(self, tmp_path):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        board_obj = Board(port)
        queue = ChangeQueue()
        queue.add(_create_up_item(body_path, board_id))

        config = {"sync": {"max_attempts": 3}}
        for _ in range(3):
            sync.apply_changes(board_obj, queue, config=config)

        assert queue.getNext() is None, "item deveria ter saído da fila ao esgotar tentativas"


class TestCT03GatilhoNaoDependeDeParent:
    """CT-03 — qualquer comando não vazio dispara o mesmo erro; sem
    nenhum comando, não há erro."""

    @pytest.mark.parametrize("commands_block", [
        "/parent #81",
        "/labels bug",
        "/need_human",
        "/blocked_by #10",
    ])
    def test_qualquer_comando_nao_vazio_dispara_nameerror(self, tmp_path, commands_block):
        from src.core import sync

        board_id = "task"
        safe_name = commands_block.strip("/").replace(" ", "_").replace("#", "")
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", f"tarefa-{safe_name}-body.md",
            "Tarefa", commands_block,
        )

        port = FakePort()
        board_obj = Board(port)
        item = _create_up_item(body_path, board_id)
        queue = ChangeQueue()

        with pytest.raises(NameError, match="config"):
            sync._apply_create_up(board_id, item, board_obj, queue=queue)

    def test_sem_bloco_de_comandos_nao_dispara_erro(self, tmp_path):
        """Caso de controle: -body.md sem bloco @--- (cmds vazio) completa o
        fluxo normal, sem erro."""
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "tarefa-sem-comando-body.md",
            "Tarefa sem comando", None,
        )

        port = FakePort()
        board_obj = Board(port)
        item = _create_up_item(body_path, board_id)
        queue = ChangeQueue()

        # Não deve levantar nenhuma exceção.
        sync._apply_create_up(board_id, item, board_obj, queue=queue)

        create_calls = [c for c in port.calls if c[0] == "create_issue"]
        assert len(create_calls) == 1

        col_dir = tmp_path / board_id / "backlog"
        remaining = sorted(p.name for p in col_dir.glob("*"))
        # O arquivo original foi renomeado (fluxo completo, sem interrupção).
        assert "tarefa-sem-comando-body.md" not in remaining


# ══════════════════════════════════════════════════════════════════════════
# Grupo B — Confirmação de que participation_intent (#310) não participa (CA-3)
# ══════════════════════════════════════════════════════════════════════════

class TestCT04ParticipationIntentNaoParticipa:
    """CT-04 — vínculo /parent no mesmo board não aciona nenhum caminho de
    participation_intent."""

    def test_nenhum_evento_de_participation_e_emitido(self, tmp_path, monkeypatch):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "backlog", "nova-tarefa-body.md",
            "Nova tarefa", "/parent #81",
        )

        port = FakePort()
        board_obj = Board(port)
        item = _create_up_item(body_path, board_id)
        queue = ChangeQueue()

        logged_events = []

        def _capture(module, msg, *args, **kwargs):
            logged_events.append((module, msg, kwargs))

        monkeypatch.setattr(sync.log, "info", _capture)
        monkeypatch.setattr(sync.log, "warning", _capture)

        with pytest.raises(NameError):
            sync._apply_create_up(board_id, item, board_obj, queue=queue)

        participation_markers = (
            "participation_classified", "participation_reconciled",
            "participation_reconcile_failed", "dispatch_blocked_unconfirmed_intent",
        )
        for module, msg, kwargs in logged_events:
            combined = f"{module} {msg} {kwargs}"
            for marker in participation_markers:
                assert marker not in combined, (
                    f"evento de participation_intent inesperado: {combined}"
                )

    def test_board_of_issue_resolve_mesmo_board_ou_none_sem_config_boards(self):
        """Sem nenhum outro board configurado contendo a issue #81, o
        resolvedor usado pelo guard de contingência cross-board não encontra
        um board PAI distinto — o vínculo nunca é tratado como cross-board,
        e o guard de participation_intent nunca é alcançado (RN-03/RN-01).
        """
        from src.core.sync import _board_of_issue

        config = {"boards": {"task": {}, "platform": "github"}}
        resolved = _board_of_issue("81", config)
        assert resolved is None, (
            "sem presença conhecida em outro board configurado, "
            "_board_of_issue não deve inventar um board de origem"
        )


# ══════════════════════════════════════════════════════════════════════════
# Grupo C — Débito identificado na suíte existente (CT-05)
# ══════════════════════════════════════════════════════════════════════════

class TestCT05TesteExistenteNaoExerceCodigo:
    """CT-05 — test_apply_create_up_self_reference_not_sent_to_adapter não
    exercita _apply_create_up (usa id= em vez de identifier=)."""

    def test_construcao_com_id_em_vez_de_identifier_nao_encontra_issue_data(self, tmp_path):
        from src.core import sync

        board_id = "task"
        body_path = _new_body_file(
            tmp_path, board_id, "todo", "nova-tarefa-body.md",
            "Nova tarefa", "/blocked_by #76, #10",
        )

        port = FakePort()
        board_obj = Board(port)
        # Reproduz exatamente a construção usada no teste existente:
        # ChangeItem.of(SyncEvent.CREATE_UP, id=str(body_path), board=board_id)
        item = ChangeItem.of(SyncEvent.CREATE_UP, id=str(body_path), board=board_id)
        queue = ChangeQueue()

        sync._apply_create_up(board_id, item, board_obj, queue=queue)

        assert port.calls == [], (
            "com id= (não identifier=), item.identifier fica None e "
            "_apply_create_up retorna na guarda inicial (issue_data não "
            "encontrado) — nenhuma chamada ao adapter deveria ocorrer, "
            "confirmando que o teste original em test_sanitize_relations.py "
            "nunca exerceu a sanitização de auto-referência que afirma cobrir"
        )
        # O arquivo original permanece intocado (prova adicional do early return).
        assert body_path.exists()
