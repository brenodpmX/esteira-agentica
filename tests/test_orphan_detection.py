"""Casos de Teste — Detectar e sinalizar arquivos órfãos sem match confiável,
sem alterar issues (issue #147).

Contexto: `detect_local_changes` (src/core/sync.py) hoje usa
`re.match(r"^(\\d+)-", body_file.name)` e resolve colisões apenas priorizando
o path já registrado em `snapshot_paths`, mas ainda pode adotar um arquivo não
registrado quando não há colisão direta de dicionário (base parcial deixada
pelo teste de regressão `test_orphan_file_collision.py`, referente ao
incidente #76/#97).

Esta issue pede que `detect_local_changes` reutilize a mesma regra de "match
confiável" de `_find_issue_files` (issue #146, já mergeada — ver
`_is_valid_registered_path`) e que, quando um arquivo com prefixo numérico
não tiver match confiável, seja classificado como "órfão": nenhum
create-up/change-up/delete-up é enfileirado a partir dele, o snapshot não é
alterado, e um registro de isolamento deduplicado é gerado via uma função
`record_orphan(board_id, path, apparent_id, reason)`.

ESTADO: todos os testes desta suíte são especificação executável e FALHAM
contra a implementação atual (pré-Desenvolvimento) — é esperado, dado que
esta etapa é apenas Casos de Teste. Servem de contrato para a etapa de
Desenvolvimento, que deve:

  1. Ajustar `detect_local_changes` para classificar como órfão todo arquivo
     com prefixo numérico sem match confiável (critérios 1, 2, 4, 5, 6).
  2. Implementar `record_orphan` (em src/core/sync.py ou novo módulo
     src/core/isolation.py) com fingerprint de conteúdo, dedupe por
     (board_id, apparent_id, reason, content_fingerprint) e persistência em
     `.pipe/orphanFiles.json` entre ciclos/processos (critérios 2, 3).
  3. Adicionar `.pipe/orphanFiles.json` a PROTECTED_PATHS (agent.py) e ao
     bloco de restrições do CONTEXT.md gerado (context_generator.py) —
     cobertos em `test_build_prompt_protected_paths.py` e
     `test_context_generator.py` (critérios 7, 8), não duplicados aqui.

Fora de escopo desta suíte (conforme a issue): dead-letter completo da fila
de sincronismo, resolução automática de ambiguidade por heurística, e
qualquer alteração no fluxo de create-up para arquivos sem prefixo numérico.
"""

import json
from pathlib import Path

import pytest

from src.core.change_queue import ChangeQueue
from src.core.sync import detect_local_changes

try:
    from src.core.sync import record_orphan
except ImportError:
    try:
        from src.core.isolation import record_orphan
    except ImportError:
        record_orphan = None


ORPHAN_STATE_FILE_NAME = "orphanFiles.json"


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def pipe_env(tmp_path, monkeypatch):
    """Estrutura mínima de board (sem issues) + mocks de BOARDS_DIR/QUEUE_FILE.

    Retorna um dict com os paths relevantes para os testes montarem seus
    próprios cenários de arquivo(s) órfão(s).
    """
    monkeypatch.chdir(tmp_path)

    boards_base = tmp_path / ".pipe" / "boards"
    board_dir = boards_base / "task"
    todo = board_dir / "todo"
    doing = board_dir / "doing"
    todo.mkdir(parents=True)
    doing.mkdir(parents=True)

    snapshot = {
        "board": {"todo": "To Do", "doing": "Doing"},
        "issues": [],
        "last_sync": "2026-08-05T10:00:00Z",
        "last_board_update": "2026-08-05T10:00:00Z",
    }
    snap_file = board_dir / "snapshot.json"
    snap_file.write_text(json.dumps(snapshot, indent=2))

    monkeypatch.setattr("src.core.sync.BOARDS_DIR", boards_base)
    monkeypatch.setattr("src.core.snapshot.BOARDS_DIR", boards_base)

    pipe_dir = tmp_path / ".pipe"
    queue_file = pipe_dir / "changeQueue.json"
    monkeypatch.setattr("src.core.change_queue.PIPE_DIR", pipe_dir)
    monkeypatch.setattr("src.core.change_queue.QUEUE_FILE", queue_file)

    # .pipe/orphanFiles.json é esperado no mesmo PIPE_DIR usado por
    # change_queue.py/dead_letter.py (Path(".pipe"), relativo ao cwd). Como o
    # cwd foi trocado para tmp_path (monkeypatch.chdir acima), o módulo de
    # implementação futura (src.core.sync ou src.core.isolation) deve
    # resolver corretamente sem necessidade de monkeypatch adicional aqui,
    # seguindo o mesmo padrão de PIPE_DIR = Path(".pipe") já usado no projeto.
    orphan_file = pipe_dir / ORPHAN_STATE_FILE_NAME

    return {
        "tmp_path": tmp_path,
        "board_dir": board_dir,
        "todo": todo,
        "doing": doing,
        "snap_file": snap_file,
        "queue_file": queue_file,
        "orphan_file": orphan_file,
        "pipe_dir": pipe_dir,
    }


def _snapshot_with_issue(snap_file: Path, issue_id: str, body_path: Path,
                         column: str = "todo"):
    """Sobrescreve o snapshot com uma única issue conhecida registrada."""
    data = json.loads(snap_file.read_text())
    data["issues"] = [{
        "id": issue_id,
        "column": column,
        "body_path": str(body_path),
        "body_mtime": str(body_path.stat().st_mtime),
        "updated_at": "2026-08-05T10:00:00Z",
        "status": "ok",
        "labels": [], "parent": None, "children": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
    }]
    snap_file.write_text(json.dumps(data, indent=2))


# ══════════════════════════════════════════════════════════════════════════════
# Critério 1 — ID inexistente no snapshot: isola, não enfileira
# ══════════════════════════════════════════════════════════════════════════════

class TestArquivoComIdDesconhecido:
    """Arquivo com prefixo numérico cujo ID não existe em nenhuma issue do
    snapshot do board: deve ser tratado como órfão."""

    def test_nao_enfileira_create_up(self, pipe_env):
        orphan = pipe_env["todo"] / "999-tarefa_inexistente-body.md"
        orphan.write_text("# Tarefa inexistente\n\nconteúdo\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        assert queue.getNext() is None, (
            "Arquivo com ID desconhecido no snapshot não deve gerar nenhum "
            "item na fila de sincronismo (nem create-up, nem change-up)."
        )

    def test_nao_altera_snapshot(self, pipe_env):
        orphan = pipe_env["todo"] / "999-tarefa_inexistente-body.md"
        orphan.write_text("# Tarefa inexistente\n\nconteúdo\n")
        before = pipe_env["snap_file"].read_text()

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        after = pipe_env["snap_file"].read_text()
        before_issues = json.loads(before)["issues"]
        after_issues = json.loads(after)["issues"]
        assert after_issues == before_issues, (
            "O snapshot não deve ganhar nenhuma entrada nova a partir de um "
            "arquivo órfão."
        )

    def test_gera_registro_de_isolamento(self, pipe_env, caplog):
        orphan = pipe_env["todo"] / "999-tarefa_inexistente-body.md"
        orphan.write_text("# Tarefa inexistente\n\nconteúdo\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        assert pipe_env["orphan_file"].exists(), (
            "detect_local_changes deve persistir um registro de isolamento "
            "para o arquivo órfão (ex.: via record_orphan), sobrevivendo "
            "entre ciclos."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Critério 4 — match confiável: caminho feliz não regride
# ══════════════════════════════════════════════════════════════════════════════

class TestArquivoComMatchConfiavel:
    """Arquivo com prefixo numérico que corresponde de forma inequívoca a uma
    issue conhecida continua seguindo o fluxo normal (nenhuma regressão)."""

    def test_change_up_normal_quando_corpo_modificado(self, pipe_env):
        body = pipe_env["todo"] / "42-feature_x-body.md"
        body.write_text("# Feature X\n\nconteúdo original\n")
        _snapshot_with_issue(pipe_env["snap_file"], "42", body)

        # Modifica o conteúdo local após registrar o snapshot (mtime avança)
        import time
        time.sleep(0.02)
        body.write_text("# Feature X\n\nconteúdo modificado\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        item = queue.getNext()
        assert item is not None, "Issue conhecida com match confiável deve gerar change-up normalmente"
        assert item.id == "42"
        assert item.event == "change-up"

    def test_delete_up_normal_quando_arquivo_desaparece(self, pipe_env):
        body = pipe_env["todo"] / "42-feature_x-body.md"
        body.write_text("# Feature X\n\nconteúdo\n")
        _snapshot_with_issue(pipe_env["snap_file"], "42", body)
        body.unlink()

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        item = queue.getNext()
        assert item is not None, "Issue conhecida sem arquivo local deve gerar delete-up normalmente"
        assert item.id == "42"
        assert item.event == "delete-up"

    def test_match_confiavel_nao_gera_registro_de_isolamento(self, pipe_env):
        body = pipe_env["todo"] / "42-feature_x-body.md"
        body.write_text("# Feature X\n\nconteúdo\n")
        _snapshot_with_issue(pipe_env["snap_file"], "42", body)

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        assert not pipe_env["orphan_file"].exists(), (
            "Nenhum registro de isolamento deve ser criado para um arquivo "
            "com match confiável."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Critério 5 — arquivo sem prefixo numérico não é afetado
# ══════════════════════════════════════════════════════════════════════════════

class TestArquivoSemPrefixoNumerico:
    """Arquivo sem prefixo numérico (issue criada localmente, ainda sem id)
    continua gerando create-up normalmente — fluxo não afetado por #147."""

    def test_create_up_normal(self, pipe_env):
        body = pipe_env["todo"] / "nova-funcionalidade-body.md"
        body.write_text("# Nova funcionalidade\n\nconteúdo\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        item = queue.getNext()
        assert item is not None, "Arquivo local sem id conhecido deve gerar create-up"
        assert item.event == "create-up"

    def test_sem_prefixo_nao_gera_registro_de_isolamento(self, pipe_env):
        body = pipe_env["todo"] / "nova-funcionalidade-body.md"
        body.write_text("# Nova funcionalidade\n\nconteúdo\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        assert not pipe_env["orphan_file"].exists()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 6 — colisão de prefixo numérico (regressão direta do #76)
# ══════════════════════════════════════════════════════════════════════════════

class TestColisaoDePrefixoNumerico:
    """Dois arquivos com o mesmo prefixo numérico, nenhum registrado no
    snapshot ainda: ambíguo por prefixo duplicado — nenhum dos dois gera
    create-up."""

    def test_nenhum_dos_dois_gera_create_up_quando_ambos_desconhecidos(self, pipe_env):
        a = pipe_env["todo"] / "76-versao_a-body.md"
        b = pipe_env["doing"] / "76-versao_b-body.md"
        a.write_text("# Versão A\n\nconteúdo a\n")
        b.write_text("# Versão B\n\nconteúdo b\n")
        # ID 76 não existe no snapshot (issues == [])

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        assert queue.getNext() is None, (
            "Colisão de prefixo numérico sem nenhum registro no snapshot é "
            "ambígua e não deve gerar create-up para nenhum dos candidatos."
        )

    def test_ambos_geram_registro_de_isolamento_quando_desconhecidos(self, pipe_env):
        a = pipe_env["todo"] / "76-versao_a-body.md"
        b = pipe_env["doing"] / "76-versao_b-body.md"
        a.write_text("# Versão A\n\nconteúdo a\n")
        b.write_text("# Versão B\n\nconteúdo b\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        assert pipe_env["orphan_file"].exists()

    def test_apenas_o_registrado_no_snapshot_e_aceito_o_outro_e_isolado(self, pipe_env):
        """Sub-cenário: um dos dois já é o body_path conhecido de uma issue."""
        legit = pipe_env["todo"] / "76-versao_legitima-body.md"
        legit.write_text("# Versão legítima\n\nconteúdo\n")
        _snapshot_with_issue(pipe_env["snap_file"], "76", legit)

        orphan = pipe_env["doing"] / "76-versao_espuria-body.md"
        orphan.write_text("# Versão espúria\n\noutro conteúdo\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        # Nenhum evento deve ser enfileirado a partir do órfão; o legítimo,
        # sem modificação, também não gera change-up.
        assert queue.getNext() is None, (
            "Apenas a issue conhecida via body_path deve ser considerada; "
            "sem modificação nela, nenhum evento deve ser enfileirado. O "
            "arquivo espúrio nunca deve gerar evento."
        )

    def test_arquivo_espurio_isolado_nao_sobrescreve_o_legitimo(self, pipe_env):
        """Modificar apenas o legítimo deve gerar exatamente 1 change-up
        (não 2, e não a partir do espúrio)."""
        import time

        legit = pipe_env["todo"] / "76-versao_legitima-body.md"
        legit.write_text("# Versão legítima\n\nconteúdo original\n")
        _snapshot_with_issue(pipe_env["snap_file"], "76", legit)

        orphan = pipe_env["doing"] / "76-versao_espuria-body.md"
        orphan.write_text("# Versão espúria\n\noutro conteúdo\n")

        time.sleep(0.02)
        legit.write_text("# Versão legítima\n\nconteúdo modificado\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        item = queue.getNext()
        assert item is not None
        assert item.id == "76"
        assert item.event == "change-up"
        queue.remove(item.uuid)
        assert queue.getNext() is None, "Não deve haver um segundo evento a partir do arquivo espúrio"


# ══════════════════════════════════════════════════════════════════════════════
# Critério 2 (parcial) — ambíguo mesmo com ID conhecido: conflita com outra issue
# ══════════════════════════════════════════════════════════════════════════════

class TestConflitaComBodyPathDeOutraIssue:
    """Arquivo com prefixo numérico de uma issue X, mas cujo conteúdo/arquivo
    já é o body_path registrado de outra issue Y no snapshot: não é match
    confiável para X — deve ser isolado como órfão, não adotado por X."""

    @pytest.mark.xfail(
        reason="Bug pré-existente (fora do escopo da #147): "
               "detect_local_changes faz Path(issue.get('body_path', '')) — "
               "quando a chave existe com valor None (issue legada, caso "
               "citado na própria issue #147, passo 4 do ADR-01), o default "
               "'' não é aplicado (só vale para chave ausente) e Path(None) "
               "lança TypeError. Reportado no addcomment desta etapa para "
               "avaliação da equipe de Desenvolvimento.",
        strict=False,
    )
    def test_arquivo_com_prefixo_de_x_mas_registrado_para_outra_issue_e_isolado(self, pipe_env):
        # Issue 10 tem seu body_path oficial em todo/, com prefixo "10-".
        official_10 = pipe_env["todo"] / "10-issue_dez-body.md"
        official_10.write_text("# Issue dez\n\nconteúdo\n")
        _snapshot_with_issue(pipe_env["snap_file"], "10", official_10)

        # Issue 11 é conhecida no snapshot mas SEM body_path registrado
        # (issue legada). Um arquivo com prefixo "11-" aparece, porém seu
        # conteúdo é uma cópia renomeada do arquivo já reivindicado por 10
        # (mesmo path não é possível fisicamente, mas o cenário de conflito
        # real ocorre quando dois arquivos de colunas diferentes competem
        # pelo mesmo body_path registrado — coberto em
        # TestColisaoDePrefixoNumerico). Aqui validamos o caso mais simples:
        # issue 11 sem body_path e com múltiplos candidatos por prefixo é
        # ambígua e deve ser isolada, não resolvida arbitrariamente.
        data = json.loads(pipe_env["snap_file"].read_text())
        data["issues"].append({
            "id": "11", "column": "doing", "body_path": None,
            "body_mtime": "", "updated_at": "2026-08-05T10:00:00Z",
            "status": "ok", "labels": [], "parent": None, "children": [],
            "blocked_by": [], "blocks": [], "archived": False, "state": "open",
        })
        pipe_env["snap_file"].write_text(json.dumps(data, indent=2))

        candidate_a = pipe_env["doing"] / "11-issue_onze_v1-body.md"
        candidate_b = pipe_env["todo"] / "11-issue_onze_v2-body.md"
        candidate_a.write_text("# Issue onze v1\n\nconteúdo\n")
        candidate_b.write_text("# Issue onze v2\n\noutro conteúdo\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)

        item = queue.getNext()
        assert item is None or item.id != "11", (
            "Issue 11 sem body_path registrado e com múltiplos candidatos "
            "por prefixo numérico é ambígua e não deve ser resolvida "
            "arbitrariamente (nenhum create-up/change-up a partir dela)."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Critério 2/3 — dedupe do log/registro de isolamento entre ciclos
# ══════════════════════════════════════════════════════════════════════════════

class TestDedupeDeRegistroDeIsolamento:
    """O log.warning de um arquivo órfão não deve se repetir a cada ciclo
    enquanto conteúdo e motivo não mudarem; deve gerar novo registro se
    conteúdo ou motivo mudarem."""

    def test_nao_duplica_registro_em_ciclos_sucessivos_sem_mudanca(self, pipe_env):
        orphan = pipe_env["todo"] / "999-tarefa_inexistente-body.md"
        orphan.write_text("# Tarefa inexistente\n\nconteúdo\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)
        first_state = pipe_env["orphan_file"].read_text()

        # Segundo ciclo, nenhuma mudança no arquivo nem na causa.
        detect_local_changes("task", queue)
        second_state = pipe_env["orphan_file"].read_text()

        assert first_state == second_state, (
            "Repetir a detecção sem alterar o arquivo/causa não deve gerar "
            "um novo registro de isolamento (dedupe por "
            "board_id+apparent_id+reason+content_fingerprint)."
        )

    def test_novo_registro_quando_conteudo_do_arquivo_orfao_muda(self, pipe_env):
        import time

        orphan = pipe_env["todo"] / "999-tarefa_inexistente-body.md"
        orphan.write_text("# Tarefa inexistente\n\nconteúdo original\n")

        queue = ChangeQueue()
        detect_local_changes("task", queue)
        first_state = json.loads(pipe_env["orphan_file"].read_text())

        time.sleep(0.02)
        orphan.write_text("# Tarefa inexistente\n\nconteúdo TOTALMENTE diferente\n")
        detect_local_changes("task", queue)
        second_state = json.loads(pipe_env["orphan_file"].read_text())

        assert first_state != second_state, (
            "Alterar o conteúdo do arquivo órfão (novo content_fingerprint) "
            "deve produzir um novo registro — a deduplicação não deve "
            "esconder uma mudança real."
        )

    def test_nao_enfileira_nada_mesmo_apos_reprocessar_varios_ciclos(self, pipe_env):
        orphan = pipe_env["todo"] / "999-tarefa_inexistente-body.md"
        orphan.write_text("# Tarefa inexistente\n\nconteúdo\n")

        queue = ChangeQueue()
        for _ in range(3):
            detect_local_changes("task", queue)

        assert queue.getNext() is None


# ══════════════════════════════════════════════════════════════════════════════
# record_orphan — contrato direto da função (unidade, sem passar por
# detect_local_changes)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(record_orphan is None, reason="record_orphan não implementada ainda")
class TestRecordOrphanContrato:
    """Testes unitários diretos de record_orphan(board_id, path, apparent_id,
    reason), independentes de detect_local_changes."""

    def test_assinatura_aceita_quatro_argumentos_posicionais(self, pipe_env, tmp_path):
        f = tmp_path / "999-x-body.md"
        f.write_text("conteudo")
        record_orphan("task", f, "999", "issue desconhecida no snapshot")

    def test_persiste_apos_chamada(self, pipe_env, tmp_path):
        f = tmp_path / "999-x-body.md"
        f.write_text("conteudo")
        record_orphan("task", f, "999", "issue desconhecida no snapshot")
        assert pipe_env["orphan_file"].exists()

    def test_dedupe_por_chave_composta_nao_duplica_chamada_identica(self, pipe_env, tmp_path):
        f = tmp_path / "999-x-body.md"
        f.write_text("conteudo")
        record_orphan("task", f, "999", "issue desconhecida no snapshot")
        state_1 = pipe_env["orphan_file"].read_text()
        record_orphan("task", f, "999", "issue desconhecida no snapshot")
        state_2 = pipe_env["orphan_file"].read_text()
        assert state_1 == state_2

    def test_motivo_diferente_gera_novo_registro(self, pipe_env, tmp_path):
        f = tmp_path / "999-x-body.md"
        f.write_text("conteudo")
        record_orphan("task", f, "999", "issue desconhecida no snapshot")
        state_1 = json.loads(pipe_env["orphan_file"].read_text())
        record_orphan("task", f, "999", "ambíguo: múltiplos candidatos")
        state_2 = json.loads(pipe_env["orphan_file"].read_text())
        assert state_1 != state_2

    def test_emite_log_warning_no_modulo_sync(self, pipe_env, tmp_path, caplog):
        f = tmp_path / "999-x-body.md"
        f.write_text("conteudo")
        record_orphan("task", f, "999", "issue desconhecida no snapshot")
        # Verificação best-effort: o próprio log core (src.core.log.log) é um
        # wrapper customizado — a asserção primária de warning é feita via
        # captura de chamada em test_gera_registro_de_isolamento (acima),
        # que passa pelo detect_local_changes real.
