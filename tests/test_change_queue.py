"""Testes de ChangeQueue.getNext(now=...) e ChangeQueue.defer() — rotação sem
bloqueio via next_attempt_at (issue #251).

Escopo desta issue: apenas o mecanismo genérico no ChangeItem/ChangeQueue.
Não testa aqui apply_changes(), classificação de participação nem
persistência de participation_intent — fora de escopo (ver #251).
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.core.board import ChangeItem, SyncEvent
from src.core.change_queue import ChangeQueue


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola o .pipe/changeQueue.json de cada teste em um diretório temporário
    (mesmo padrão de tests/test_sync_optimization.py), evitando vazamento de
    estado entre testes e uso do estado real da esteira."""
    monkeypatch.chdir(tmp_path)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _future(seconds: int = 3600) -> str:
    return _iso(datetime.now(timezone.utc) + timedelta(seconds=seconds))


def _past(seconds: int = 3600) -> str:
    return _iso(datetime.now(timezone.utc) - timedelta(seconds=seconds))


# ══════════════════════════════════════════════════════════════════════════
# CT01 — ChangeItem.next_attempt_at (campo novo, independente de attempts)
# ══════════════════════════════════════════════════════════════════════════

class TestChangeItemNextAttemptAt:
    """CT01 — campo next_attempt_at existe, default None, não afeta
    same_target nem attempts."""

    def test_default_next_attempt_at_is_none(self):
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        assert item.next_attempt_at is None

    def test_next_attempt_at_settable(self):
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        item.next_attempt_at = _future()
        assert item.next_attempt_at is not None

    def test_same_target_ignores_next_attempt_at(self):
        a = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        b = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        b.next_attempt_at = _future()
        assert a.same_target(b)

    def test_setting_next_attempt_at_does_not_increment_attempts(self):
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        item.next_attempt_at = _future()
        assert item.attempts == 0

    def test_legacy_persisted_item_without_next_attempt_at_defaults_none(self):
        """ChangeQueue._read ignora campos desconhecidos ao carregar; itens
        antigos (sem 'next_attempt_at' no JSON) devem carregar None —
        elegíveis imediatamente (compatibilidade)."""
        import json
        from src.core.change_queue import QUEUE_FILE, PIPE_DIR

        PIPE_DIR.mkdir(parents=True, exist_ok=True)
        legacy_item = {
            "timestamp": ChangeItem.now(),
            "event": SyncEvent.CHANGE_UP.value,
            "id": "1",
            "identifier": None,
            "board": "b",
            "uuid": "11111111-1111-1111-1111-111111111111",
            "fullsync": False,
            "attempts": 0,
            # sem "next_attempt_at" — simula persistência anterior a esta mudança
        }
        QUEUE_FILE.write_text(json.dumps([legacy_item]), encoding="utf-8")

        q = ChangeQueue()
        item = q.getNext()
        assert item is not None
        assert item.next_attempt_at is None


# ══════════════════════════════════════════════════════════════════════════
# CT02 — getNext() pula item pendente no futuro sem removê-lo (rotação)
# ══════════════════════════════════════════════════════════════════════════

class TestGetNextRotacaoSemBloqueio:
    """CT02 — item com next_attempt_at no futuro não bloqueia os demais."""

    def test_getnext_pula_primeiro_pendente_retorna_segundo_elegivel(self):
        q = ChangeQueue()
        first = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        first.next_attempt_at = _future()
        second = ChangeItem.of(SyncEvent.CHANGE_UP, id="2", board="b")
        third = ChangeItem.of(SyncEvent.CHANGE_UP, id="3", board="b")
        q.addAll([first, second, third])

        result = q.getNext()

        assert result is not None
        assert result.id == "2"

    def test_getnext_nao_remove_item_pendente_pulado(self):
        q = ChangeQueue()
        first = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        first.next_attempt_at = _future()
        second = ChangeItem.of(SyncEvent.CHANGE_UP, id="2", board="b")
        q.addAll([first, second])

        q.getNext()

        assert q.size() == 2

    def test_getnext_repetido_sem_remover_retorna_mesmo_item_elegivel(self):
        q = ChangeQueue()
        first = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        first.next_attempt_at = _future()
        second = ChangeItem.of(SyncEvent.CHANGE_UP, id="2", board="b")
        q.addAll([first, second])

        r1 = q.getNext()
        r2 = q.getNext()

        assert r1.id == r2.id == "2"
        assert r1.uuid == r2.uuid

    def test_getnext_com_now_apos_vencimento_retorna_item_antes_pendente(self):
        q = ChangeQueue()
        first = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        first.next_attempt_at = _past(60)  # já venceu
        second = ChangeItem.of(SyncEvent.CHANGE_UP, id="2", board="b")
        q.addAll([first, second])

        result = q.getNext(now=ChangeItem.now())

        assert result is not None
        assert result.id == "1"

    def test_getnext_now_explicito_antes_do_vencimento_ainda_pula(self):
        q = ChangeQueue()
        first = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        first.next_attempt_at = _future(3600)
        second = ChangeItem.of(SyncEvent.CHANGE_UP, id="2", board="b")
        q.addAll([first, second])

        result = q.getNext(now=ChangeItem.now())

        assert result is not None
        assert result.id == "2"

    def test_getnext_fila_toda_pendente_no_futuro_retorna_none(self):
        q = ChangeQueue()
        first = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        first.next_attempt_at = _future()
        second = ChangeItem.of(SyncEvent.CHANGE_UP, id="2", board="b")
        second.next_attempt_at = _future()
        q.addAll([first, second])

        result = q.getNext()

        assert result is None

    def test_getnext_fila_vazia_retorna_none(self):
        q = ChangeQueue()
        assert q.getNext() is None

    def test_getnext_sem_argumento_continua_funcionando_regressao(self):
        """Compatibilidade: chamadas existentes (ex.: src/core/sync.py) usam
        getNext() sem argumento — itens sem next_attempt_at (caso legado)
        devem continuar sendo retornados normalmente."""
        q = ChangeQueue()
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        q.add(item)

        result = q.getNext()

        assert result is not None
        assert result.id == "1"


# ══════════════════════════════════════════════════════════════════════════
# CT03 — defer() atualiza next_attempt_at sem alterar uuid/posição/attempts
# ══════════════════════════════════════════════════════════════════════════

class TestDefer:
    """CT03 — defer() é idempotente por uuid, não muda posição FIFO nem uuid,
    e não incrementa attempts."""

    def test_defer_atualiza_next_attempt_at(self):
        q = ChangeQueue()
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        q.add(item)
        deadline = _future()

        q.defer(item, deadline)

        stored = q.getNext(now=ChangeItem.now())
        # item ainda pendente no futuro -> não deve ser retornado
        assert stored is None

    def test_defer_nao_altera_uuid(self):
        q = ChangeQueue()
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        q.add(item)
        original_uuid = item.uuid

        q.defer(item, _future())

        # remove pelo uuid original ainda deve funcionar
        assert q.remove(original_uuid) is True

    def test_defer_nao_altera_posicao_fifo(self):
        q = ChangeQueue()
        first = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        second = ChangeItem.of(SyncEvent.CHANGE_UP, id="2", board="b")
        third = ChangeItem.of(SyncEvent.CHANGE_UP, id="3", board="b")
        q.addAll([first, second, third])

        # defere o do meio (id=2) para o futuro
        q.defer(second, _future())

        # ordem relativa dos itens elegíveis (1 e 3) é preservada
        r1 = q.getNext()
        assert r1.id == "1"
        q.remove(r1.uuid)
        r2 = q.getNext()
        assert r2.id == "3"

    def test_defer_nao_incrementa_attempts(self):
        q = ChangeQueue()
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        q.add(item)
        assert item.attempts == 0

        q.defer(item, _future())

        items = q._read()
        stored = next(i for i in items if i.id == "1")
        assert stored.attempts == 0

    def test_defer_idempotente_atualiza_apenas_instante(self):
        q = ChangeQueue()
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        q.add(item)

        first_deadline = _future(100)
        second_deadline = _future(200)
        q.defer(item, first_deadline)
        q.defer(item, second_deadline)

        items = q._read()
        stored = next(i for i in items if i.id == "1")
        assert stored.next_attempt_at == second_deadline
        assert q.size() == 1

    def test_defer_uuid_inexistente_nao_faz_nada(self):
        """Mesmo padrão de tolerância de remove(): uuid não encontrado não
        levanta erro nem altera a fila."""
        q = ChangeQueue()
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        q.add(item)

        ghost = ChangeItem.of(SyncEvent.CHANGE_UP, id="999", board="b")
        ghost.uuid = "00000000-0000-0000-0000-000000000000"

        q.defer(ghost, _future())  # não deve levantar

        assert q.size() == 1
        items = q._read()
        assert items[0].id == "1"
        assert items[0].next_attempt_at is None

    def test_defer_remove_ainda_funciona_pelo_mesmo_uuid(self):
        q = ChangeQueue()
        item = ChangeItem.of(SyncEvent.CHANGE_UP, id="1", board="b")
        q.add(item)
        q.defer(item, _future())

        assert q.remove(item.uuid) is True
        assert q.size() == 0
