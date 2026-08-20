"""Testes de `boards.rerun_cooldown` — cooldown de reexecução no keep_task.

Contexto (perda no merge `c27f813`): o commit `28fea7e` de `main` introduziu a
chave opcional `boards.rerun_cooldown`, que impede a esteira de reexecutar a
mesma issue (mesmo board + coluna + id) em intervalo menor que o configurado.
Sem ela, uma issue que falha repetidamente é reentregue ao agente em loop
apertado, queimando quota do modelo sem progresso.

O merge de `epic` em `main` adotou o lado `epic` em `src/__main__.py` e removeu
todo o comportamento — mas manteve a validação em `src/core/config.py`. O
resultado era o pior cenário: `pipe.yml` aceitava `rerun_cooldown` sem erro e a
chave não tinha efeito nenhum.

Contratos travados aqui:
- issue selecionada não é reentregue enquanto dentro do cooldown;
- a chave inclui a coluna: mudar de coluna torna a issue elegível na hora;
- entradas expiradas são purgadas (o cache não cresce sem limite);
- `cooldown <= 0` / ausente desabilita e esvazia o cache;
- a validação em `config.py` segue coerente com o comportamento.
"""

import json
import time
from pathlib import Path

import pytest

import src.__main__ as pipe
from src.__main__ import (
    _cooldown_seconds,
    _in_rerun_cooldown,
    _mark_rerun,
    _purge_expired_rerun,
    keep_task,
)


@pytest.fixture(autouse=True)
def cache_limpo():
    """Isola o cache de módulo entre testes."""
    pipe._rerun_cache.clear()
    yield
    pipe._rerun_cache.clear()


def _snapshot(board_dir: Path, col: str, stem: str, issue_id: str = "42"):
    snapshot = {
        "board": {"backlog": "Backlog", "doing": "Doing", "done": "Done"},
        "issues": [
            {
                "id": issue_id,
                "column": col,
                "body_path": f"{board_dir}/{col}/{stem}-body.md",
                "body_mtime": "1.0",
                "created_at": "2026-08-01T10:00:00Z",
                "updated_at": "2026-08-01T10:00:00Z",
                "status": "ok",
                "labels": [],
                "parent": None,
                "children": [],
                "blocked_by": [],
                "blocks": [],
                "archived": False,
                "state": "open",
            }
        ],
        "last_sync": None,
        "last_board_update": "2026-08-01T10:00:00Z",
    }
    (board_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=2))


def _config(cooldown=None):
    boards = {
        "platform": "github",
        "task": {
            "name": "Task",
            "priority": 0,
            "columns": {
                "backlog": {"name": "Backlog"},
                "doing": {
                    "name": "Doing",
                    "agent": "dev",
                    "change": {"advance": "done"},
                },
                "done": {"name": "Done", "archive": True},
            },
        },
    }
    if cooldown is not None:
        boards["rerun_cooldown"] = cooldown
    return {"boards": boards, "sleep": 60}


@pytest.fixture
def board_doing(tmp_path, monkeypatch):
    """Board 'task' com a issue #42 elegível na coluna 'doing'."""
    monkeypatch.chdir(tmp_path)
    board_dir = Path(".pipe/boards/task")
    for col in ("backlog", "doing", "done"):
        (board_dir / col).mkdir(parents=True)

    stem = "42-uma_tarefa"
    (board_dir / "doing" / f"{stem}-body.md").write_text("# Uma tarefa\n\nbody\n")
    _snapshot(board_dir, "doing", stem)
    return board_dir, stem


# ─── Helpers de baixo nível ───────────────────────────────────────────────────

class TestCooldownSeconds:
    """Leitura da chave boards.rerun_cooldown."""

    def test_ausente_e_zero(self):
        assert _cooldown_seconds(_config()) == 0

    def test_le_valor_configurado(self):
        assert _cooldown_seconds(_config(300)) == 300

    def test_zero_explicito_e_zero(self):
        assert _cooldown_seconds(_config(0)) == 0

    def test_config_sem_boards_nao_explode(self):
        assert _cooldown_seconds({}) == 0


class TestInRerunCooldown:
    """Decisão de pular a issue por cooldown."""

    def test_issue_nunca_executada_e_elegivel(self):
        assert _in_rerun_cooldown("task", "doing", "42", 300) is False

    def test_issue_recem_executada_esta_em_cooldown(self):
        _mark_rerun("task", "doing", "42")
        assert _in_rerun_cooldown("task", "doing", "42", 300) is True

    def test_cooldown_desabilitado_nunca_bloqueia(self):
        _mark_rerun("task", "doing", "42")
        assert _in_rerun_cooldown("task", "doing", "42", 0) is False
        assert _in_rerun_cooldown("task", "doing", "42", -1) is False

    def test_entrada_expirada_libera_e_e_removida(self):
        _mark_rerun("task", "doing", "42")
        pipe._rerun_cache[("task", "doing", "42")] = time.time() - 400

        assert _in_rerun_cooldown("task", "doing", "42", 300) is False
        assert ("task", "doing", "42") not in pipe._rerun_cache, (
            "entrada expirada deve ser removida ao ser consultada"
        )

    def test_outra_coluna_e_elegivel_imediatamente(self):
        """Mudar de coluna torna a issue elegível na hora (chave inclui coluna).

        Intenção do desenho: o cooldown existe para conter loop de reexecução na
        MESMA etapa. Se a issue avançou no board, é trabalho novo.
        """
        _mark_rerun("task", "doing", "42")
        assert _in_rerun_cooldown("task", "review", "42", 300) is False

    def test_outro_board_e_elegivel_imediatamente(self):
        _mark_rerun("task", "doing", "42")
        assert _in_rerun_cooldown("story", "doing", "42", 300) is False

    def test_outra_issue_e_elegivel_imediatamente(self):
        _mark_rerun("task", "doing", "42")
        assert _in_rerun_cooldown("task", "doing", "43", 300) is False

    def test_id_int_e_str_sao_a_mesma_chave(self):
        """O snapshot pode trazer o id como int ou str; a chave normaliza."""
        _mark_rerun("task", "doing", 42)
        assert _in_rerun_cooldown("task", "doing", "42", 300) is True


class TestPurgeExpiredRerun:
    """Purga de entradas expiradas — impede crescimento ilimitado do cache."""

    def test_remove_todas_as_expiradas(self):
        agora = time.time()
        pipe._rerun_cache[("task", "doing", "1")] = agora - 400
        pipe._rerun_cache[("task", "doing", "2")] = agora - 400
        pipe._rerun_cache[("task", "doing", "3")] = agora

        _purge_expired_rerun(300)

        assert ("task", "doing", "1") not in pipe._rerun_cache
        assert ("task", "doing", "2") not in pipe._rerun_cache
        assert ("task", "doing", "3") in pipe._rerun_cache, \
            "entrada dentro do cooldown deve permanecer"

    def test_purga_issues_que_sairam_do_board(self):
        """Sem a purga, issues fechadas/arquivadas ficariam no cache pra sempre.

        Elas nunca voltam ao keep_task, logo nunca seriam consultadas — e a
        remoção preguiçosa de _in_rerun_cooldown jamais aconteceria.
        """
        for i in range(500):
            pipe._rerun_cache[("task", "doing", str(i))] = time.time() - 999

        _purge_expired_rerun(300)

        assert len(pipe._rerun_cache) == 0

    def test_cooldown_desabilitado_esvazia_o_cache(self):
        pipe._rerun_cache[("task", "doing", "1")] = time.time()
        _purge_expired_rerun(0)
        assert len(pipe._rerun_cache) == 0

    def test_cache_vazio_nao_explode(self):
        _purge_expired_rerun(300)
        assert len(pipe._rerun_cache) == 0


# ─── Integração com keep_task ─────────────────────────────────────────────────

class TestKeepTaskCooldown:
    """O cooldown deve efetivamente conter a reentrega no keep_task."""

    def test_primeira_selecao_ocorre(self, board_doing):
        task = keep_task("task", _config(300))
        assert task is not None and task is not pipe.AUTO_ADVANCED
        assert task["issue"]["id"] == "42"

    def test_segunda_selecao_imediata_e_bloqueada(self, board_doing):
        """Regressão do bug: sem cooldown a issue voltava a cada ciclo."""
        config = _config(300)
        assert keep_task("task", config) is not None
        assert keep_task("task", config) is None, (
            "issue nao deveria ser reentregue dentro do cooldown"
        )

    def test_sem_cooldown_a_issue_e_reentregue(self, board_doing):
        """Comportamento padrão preservado: ausente = desabilitado."""
        config = _config()
        assert keep_task("task", config) is not None
        assert keep_task("task", config) is not None, (
            "sem rerun_cooldown o comportamento historico deve ser mantido"
        )

    def test_apos_expirar_a_issue_volta_a_ser_elegivel(self, board_doing):
        config = _config(300)
        assert keep_task("task", config) is not None

        # Envelhece a marcação além do cooldown.
        pipe._rerun_cache[("task", "doing", "42")] = time.time() - 400

        assert keep_task("task", config) is not None, (
            "passado o cooldown a issue deve voltar a ser elegivel"
        )

    def test_keep_task_nao_marca_quando_desabilitado(self, board_doing):
        keep_task("task", _config())
        assert len(pipe._rerun_cache) == 0, (
            "com cooldown desabilitado nada deve ser gravado no cache"
        )

    def test_issue_movida_de_coluna_e_elegivel_na_hora(self, board_doing, tmp_path):
        """Avançar no board zera o cooldown (trabalho novo, nao reexecucao)."""
        board_dir, stem = board_doing
        config = _config(300)
        config["boards"]["task"]["columns"]["review"] = {
            "name": "Review", "agent": "dev", "change": {"advance": "done"},
        }

        assert keep_task("task", config) is not None

        # Simula a issue avançando de 'doing' para 'review'.
        (board_dir / "review").mkdir(exist_ok=True)
        (board_dir / "doing" / f"{stem}-body.md").rename(
            board_dir / "review" / f"{stem}-body.md"
        )
        _snapshot(board_dir, "review", stem)

        assert keep_task("task", config) is not None, (
            "na nova coluna a issue deve ser elegivel imediatamente"
        )


# ─── Coerência com a validação de config ──────────────────────────────────────

class TestValidacaoConfigCoerente:
    """A validação que sobreviveu ao merge deve casar com o comportamento."""

    def _validar(self, cooldown):
        from src.core.config import _validate_boards
        boards = _config(cooldown)["boards"]
        boards["task"]["columns"]["doing"]["agent"] = "dev"
        _validate_boards(boards, known_agents={"dev"})

    @pytest.mark.parametrize("valor", [0, 1, 300, 86400])
    def test_inteiros_validos_sao_aceitos(self, valor):
        self._validar(valor)

    @pytest.mark.parametrize("valor", [-1, "300", 1.5, True, []])
    def test_valores_invalidos_sao_rejeitados(self, valor):
        from src.core.config import ConfigError
        with pytest.raises(ConfigError, match="rerun_cooldown"):
            self._validar(valor)

    def test_chave_escalar_nao_e_tratada_como_board(self):
        """rerun_cooldown convive com os boards dentro de 'boards'.

        Sem os guards isinstance(cfg, dict), a chave escalar seria iterada como
        se fosse um board e quebraria a validacao e o get_board_ids.
        """
        from src.__main__ import get_board_ids
        assert get_board_ids(_config(300)) == ["task"]
