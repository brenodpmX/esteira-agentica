"""Casos de Teste — Integrar InstanceLock ao ciclo de vida de main() (issue #151)

Contexto: a task anterior da mesma story (issue #150) entregou a primitiva
isolada `InstanceLock`/`LockHeldError` em `src/core/lock.py` (ver
tests/test_instance_lock.py). Esta suíte cobre a INTEGRAÇÃO dessa primitiva
com `main()`/`startup()` em `src/__main__.py` — ainda não implementada no
momento da escrita destes testes.

Incidente de referência (#97): uma segunda instância que chega a rodar
`startup()` remove a fila de mudanças (`QUEUE_FILE.unlink()`) da instância já
ativa. A recusa por lock precisa ocorrer ANTES dessa linha ser alcançada.

Referência: doc/architecture/confiabilidade-parent-recursivo/arquitetura.md
(ADR-06, seção "5.4 Inicialização" e seção 7 "Observabilidade operacional") e
doc/requirements/confiabilidade-parent-recursivo/business-rules.md (RN-009).

Origem/migração (issue #166, #104 → #142): esta suíte foi originalmente
escrita na branch `feature151-...`, nascida de `epic`, junto do delta de
implementação (`46948aa`/`085a383`). A doc/architecture/instance-lock/
sequenciamento-epic-main.md determina que `epic` deixa de ser veículo de
entrega do InstanceLock e que a promoção correta é
#150 → #151 → story #142 → epic #104 → `main`, proibindo cherry-pick cego do
commit de implementação porque ele mistura lógica de sincronização (hoje já
coberta por `SnapshotGuard`/`SnapshotIntegrityError` em `main`) fora do escopo
do lock. Esta especificação, porém, não depende dessa estrutura interna: os
fixtures isolam `main()` via monkeypatch e interrompem o loop na primeira
iteração (antes de `call_agent`/`SnapshotGuard`), por isso permanece válida
sem alteração como critério de aceite para a reaplicação do delta mínimo da
#151 sobre a branch canônica da story #142. Validado nesta migração: os 7
testes que não dependem da integração ainda ausente (liberação em
encerramento normal, em exceção não tratada e não regressão do SIGTERM)
passam já hoje; os 8 que documentam a integração pendente falham como
esperado (spec executável, não regressão) até o desenvolvimento reaplicar o
delta da #151 na story #142.

ESTADO: `main()` ainda não adquire/libera `InstanceLock` (task de
desenvolvimento subsequente, a ser reaplicada sobre a branch da story #142).
Os testes desta suíte documentam os critérios de aceite 1–7 da issue #151
como especificação executável — falham até a implementação, e passam a ser
regressão depois. Seguem o padrão condicional já usado em
tests/test_build_prompt_protected_paths.py (getattr direto no código-fonte,
sem exigir símbolos que a issue não pede) e o padrão de isolamento de main()
via monkeypatch já usado em tests/test_sigterm_shutdown.py e
tests/test_loop_guard.py.

Cobertura (critérios de aceite da issue #151):
  1. Lock adquirido antes de startup(); QUEUE_FILE de uma 1ª instância ativa
     não é tocado quando a 2ª é recusada.
  2. 2ª instância recusada sai com SystemExit(1) sem chamar startup(),
     board.connect() nem qualquer função do loop.
  3. Mensagem de log da recusa contém o path do lock e dados do detentor
     (pid, started_at, host).
  4. Encerramento normal (KeyboardInterrupt/_Shutdown) libera o lock antes
     do processo terminar.
  5. Exceção não tratada que escapa do loop (falha em startup(),
     board.connect() ou board.check_access()) ainda libera o lock via
     finally.
  6. Regressão do incidente #97: com uma 1ª instância "ativa" (lock
     adquirido + fila populada), uma 2ª chamada é recusada e a fila da 1ª
     permanece intacta (mesmo conteúdo, mesmo arquivo, sem truncamento).
  7. Sem regressão em tests/test_sigterm_shutdown.py.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from src.core.lock import InstanceLock, LockHeldError
except ModuleNotFoundError:
    InstanceLock = None
    LockHeldError = None

import src.__main__ as m


def _skip_if_lock_module_ausente():
    if InstanceLock is None:
        pytest.skip("src.core.lock ainda não existe (dependência: issue #150)")


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola .pipe/ (lock + fila) em um diretório temporário por teste.

    Cria .pipe/ de antemão: InstanceLock.acquire() não cria diretórios pais
    (apenas o arquivo do lock em si), refletindo o ambiente real onde
    startup()/check_config() já teriam preparado .pipe/ antes da aquisição.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pipe").mkdir(exist_ok=True)
    yield


def _minimal_config():
    return {"sleep": 1, "boards": {"platform": "github"}}


def _patch_main_collaborators(monkeypatch, *, startup_side_effect=None,
                               connect_side_effect=None,
                               check_access_side_effect=None,
                               loop_side_effect=None):
    """Isola main() do restante do sistema (padrão de test_sigterm_shutdown.py).

    Faz a primeira iteração do loop levantar _Shutdown por padrão, a menos
    que loop_side_effect seja fornecido (para simular exceção não tratada).
    """
    monkeypatch.setattr(m, "check_config", lambda: _minimal_config())
    monkeypatch.setattr(
        m, "startup",
        MagicMock(side_effect=startup_side_effect) if startup_side_effect
        else MagicMock(),
    )
    monkeypatch.setattr(m, "board_full_sync", MagicMock())
    monkeypatch.setattr(m, "get_board_ids", lambda cfg: ["b1"])

    def _stop(*_a, **_k):
        raise m._Shutdown()

    monkeypatch.setattr(m, "sync_board", loop_side_effect or _stop)
    monkeypatch.setattr(m, "ADAPTERS", {"github": lambda: object()})

    class _FakeBoard:
        def __init__(self, adapter):
            pass

        def connect(self, cfg):
            if connect_side_effect:
                raise connect_side_effect

        def check_access(self, cfg):
            if check_access_side_effect:
                raise check_access_side_effect

    monkeypatch.setattr(m, "Board", _FakeBoard)


# ══════════════════════════════════════════════════════════════════════════════
# Critério 1 — lock adquirido antes de startup(); fila da 1ª instância intacta
# ══════════════════════════════════════════════════════════════════════════════

class TestAquisicaoAntesDoStartup:
    """O lock deve ser adquirido em main() antes de startup() ser chamado."""

    def test_startup_nao_chamado_quando_lock_ocupado(self, monkeypatch):
        """Com o lock já detido por outra instância, main() não chama startup().

        Reproduz o cenário do incidente #97: a 2ª instância nunca deve
        alcançar startup() (e portanto nunca QUEUE_FILE.unlink()).
        """
        _skip_if_lock_module_ausente()

        holder = InstanceLock()
        holder.acquire()
        try:
            _patch_main_collaborators(monkeypatch)

            with pytest.raises(SystemExit) as exc_info:
                m.main()

            assert exc_info.value.code == 1
            m.startup.assert_not_called()
        finally:
            holder.release()

    def test_queue_file_da_primeira_instancia_nao_e_alterado(self, monkeypatch):
        """QUEUE_FILE de uma 1ª instância ativa não é tocado quando a 2ª é
        recusada — verificação direta da causa-raiz do incidente #97
        (startup() faz QUEUE_FILE.unlink() antes da correção)."""
        _skip_if_lock_module_ausente()

        from src.core.change_queue import QUEUE_FILE

        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        conteudo_original = '[{"uuid": "abc", "event": "change-up", "id": "1"}]'
        QUEUE_FILE.write_text(conteudo_original, encoding="utf-8")

        holder = InstanceLock()
        holder.acquire()
        try:
            _patch_main_collaborators(monkeypatch)

            with pytest.raises(SystemExit):
                m.main()

            assert QUEUE_FILE.read_text(encoding="utf-8") == conteudo_original, (
                "QUEUE_FILE foi alterado por uma instância recusada — "
                "regressão do incidente #97 (Issue Fantasma)."
            )
        finally:
            holder.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 2 — SystemExit(1) sem chamar startup/connect/loop
# ══════════════════════════════════════════════════════════════════════════════

class TestRecusaPorLockOcupado:
    """Instância recusada sai com SystemExit(1) sem tocar startup/board/loop."""

    def test_systemexit_1_ao_recusar(self, monkeypatch):
        _skip_if_lock_module_ausente()

        holder = InstanceLock()
        holder.acquire()
        try:
            _patch_main_collaborators(monkeypatch)
            with pytest.raises(SystemExit) as exc_info:
                m.main()
            assert exc_info.value.code == 1
        finally:
            holder.release()

    def test_board_connect_nao_chamado_ao_recusar(self, monkeypatch):
        _skip_if_lock_module_ausente()

        holder = InstanceLock()
        holder.acquire()
        try:
            connect_spy = MagicMock()
            _patch_main_collaborators(monkeypatch)

            class _SpyBoard:
                def __init__(self, adapter):
                    pass

                def connect(self, cfg):
                    connect_spy()

                def check_access(self, cfg):
                    pass

            monkeypatch.setattr(m, "Board", _SpyBoard)

            with pytest.raises(SystemExit):
                m.main()

            connect_spy.assert_not_called()
        finally:
            holder.release()

    def test_loop_nao_executa_ao_recusar(self, monkeypatch):
        """sync_board (representando o corpo do loop) nunca é chamado."""
        _skip_if_lock_module_ausente()

        holder = InstanceLock()
        holder.acquire()
        try:
            loop_spy = MagicMock(side_effect=m._Shutdown())
            _patch_main_collaborators(monkeypatch, loop_side_effect=loop_spy)

            with pytest.raises(SystemExit):
                m.main()

            loop_spy.assert_not_called()
        finally:
            holder.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 3 — mensagem de recusa contém path do lock e dados do detentor
# ══════════════════════════════════════════════════════════════════════════════

class TestMensagemDeRecusa:
    """A mensagem logada na recusa deve conter path do lock + dados do detentor."""

    def test_mensagem_contem_path_e_pid_do_detentor(self, monkeypatch):
        _skip_if_lock_module_ausente()

        holder = InstanceLock()
        holder.acquire()
        try:
            _patch_main_collaborators(monkeypatch)

            chamadas = []
            monkeypatch.setattr(
                m.log, "error",
                lambda module, msg, *a, **kw: chamadas.append((module, msg, kw)),
            )

            with pytest.raises(SystemExit):
                m.main()

            assert chamadas, "Nenhum log.error foi emitido na recusa por lock"
            _, msg, kw = chamadas[0]
            texto = msg + str(kw)
            assert str(holder.path) in texto, (
                "A mensagem de recusa deve conter o caminho do lock"
            )
            import os
            assert str(os.getpid()) in texto, (
                "A mensagem de recusa deve conter o pid do processo detentor "
                "(o próprio processo de teste, que detém o lock)"
            )
        finally:
            holder.release()

    def test_evento_observabilidade_instance_lock_refused(self, monkeypatch):
        """Critério de aceite + ADR-06 seção 7: evento com nome estável
        `instance_lock_refused` e campos lock_path/holder_pid/holder_started_at."""
        _skip_if_lock_module_ausente()

        holder = InstanceLock()
        holder.acquire()
        try:
            _patch_main_collaborators(monkeypatch)

            chamadas = []
            monkeypatch.setattr(
                m.log, "error",
                lambda module, msg, *a, **kw: chamadas.append(kw),
            )

            with pytest.raises(SystemExit):
                m.main()

            eventos = [kw for kw in chamadas if kw.get("event") == "instance_lock_refused"]
            assert eventos, (
                "Nenhum log.error com event='instance_lock_refused' foi emitido. "
                "Ver ADR-06 seção 7 (Observabilidade operacional)."
            )
            campos = eventos[0]
            for campo in ("lock_path", "holder_pid", "holder_started_at"):
                assert campo in campos, (
                    f"Evento instance_lock_refused deve conter o campo '{campo}'"
                )
        finally:
            holder.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 4 — encerramento normal libera o lock
# ══════════════════════════════════════════════════════════════════════════════

class TestLiberacaoNoEncerramentoNormal:
    """KeyboardInterrupt/_Shutdown deve liberar o lock antes de main() retornar."""

    def test_libera_lock_apos_shutdown_sigterm(self, monkeypatch):
        _skip_if_lock_module_ausente()

        _patch_main_collaborators(monkeypatch)  # loop levanta _Shutdown na 1ª iteração

        m.main()  # não deve levantar

        novo_lock = InstanceLock()
        try:
            novo_lock.acquire()  # deve suceder: lock foi liberado no finally
        except LockHeldError:
            pytest.fail(
                "Lock não foi liberado após encerramento normal (_Shutdown)"
            )
        else:
            novo_lock.release()

    def test_libera_lock_apos_keyboardinterrupt(self, monkeypatch):
        _skip_if_lock_module_ausente()

        def _stop_com_interrupt(*_a, **_k):
            raise KeyboardInterrupt()

        _patch_main_collaborators(monkeypatch, loop_side_effect=_stop_com_interrupt)

        m.main()

        novo_lock = InstanceLock()
        try:
            novo_lock.acquire()
        except LockHeldError:
            pytest.fail(
                "Lock não foi liberado após encerramento normal (KeyboardInterrupt)"
            )
        else:
            novo_lock.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 5 — exceção não tratada em startup/connect/check_access libera o lock
# ══════════════════════════════════════════════════════════════════════════════

class TestLiberacaoEmExcecaoNaoTratada:
    """finally deve liberar o lock mesmo se startup()/connect()/check_access()
    levantar exceção que escapa (não capturada pelos handlers do loop, pois
    ocorre antes dele)."""

    def test_libera_lock_apos_falha_em_startup(self, monkeypatch):
        _skip_if_lock_module_ausente()

        _patch_main_collaborators(
            monkeypatch, startup_side_effect=RuntimeError("falha simulada em startup")
        )

        with pytest.raises(RuntimeError):
            m.main()

        novo_lock = InstanceLock()
        try:
            novo_lock.acquire()
        except LockHeldError:
            pytest.fail("Lock não foi liberado após exceção em startup()")
        else:
            novo_lock.release()

    def test_libera_lock_apos_falha_em_board_connect(self, monkeypatch):
        _skip_if_lock_module_ausente()

        _patch_main_collaborators(
            monkeypatch, connect_side_effect=RuntimeError("falha simulada em connect")
        )

        with pytest.raises(RuntimeError):
            m.main()

        novo_lock = InstanceLock()
        try:
            novo_lock.acquire()
        except LockHeldError:
            pytest.fail("Lock não foi liberado após exceção em board.connect()")
        else:
            novo_lock.release()

    def test_libera_lock_apos_falha_em_check_access(self, monkeypatch):
        """board.check_access() levanta BoardAccessError → main() sai via
        SystemExit(1) (já tratado hoje), mas o lock ainda deve ser liberado."""
        _skip_if_lock_module_ausente()

        from src.core.board import BoardAccessError

        _patch_main_collaborators(
            monkeypatch, check_access_side_effect=BoardAccessError("sem permissão")
        )

        with pytest.raises(SystemExit):
            m.main()

        novo_lock = InstanceLock()
        try:
            novo_lock.acquire()
        except LockHeldError:
            pytest.fail("Lock não foi liberado após exceção em board.check_access()")
        else:
            novo_lock.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 6 — regressão do incidente #97 (fila intacta na instância recusada)
# ══════════════════════════════════════════════════════════════════════════════

class TestRegressaoIncidente97:
    """Com uma 1ª instância ativa (lock + fila populada), uma 2ª chamada é
    recusada e a fila da 1ª permanece intacta (mesmo conteúdo, mesmo arquivo,
    sem truncamento)."""

    def test_fila_populada_permanece_intacta_apos_recusa(self, monkeypatch):
        _skip_if_lock_module_ausente()

        from src.core.change_queue import ChangeQueue, QUEUE_FILE
        from src.core.board import ChangeItem, SyncEvent

        holder = InstanceLock()
        holder.acquire()
        try:
            queue = ChangeQueue()
            queue.add(ChangeItem.of(SyncEvent.CHANGE_UP, id="10", board="task"))
            queue.add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id="11", board="task"))

            conteudo_antes = QUEUE_FILE.read_text(encoding="utf-8")
            assert conteudo_antes.strip(), "Pré-condição: fila deveria estar populada"

            _patch_main_collaborators(monkeypatch)

            with pytest.raises(SystemExit):
                m.main()

            conteudo_depois = QUEUE_FILE.read_text(encoding="utf-8")
            assert conteudo_depois == conteudo_antes, (
                "A fila de mudanças da 1ª instância foi alterada por uma "
                "2ª instância recusada — regressão do incidente #97 "
                "(Issue Fantasma: startup() da 2ª instância removeu/truncou "
                "QUEUE_FILE da 1ª instância ativa)."
            )
            assert QUEUE_FILE.exists(), "QUEUE_FILE não deveria ter sido removido"
        finally:
            holder.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 7 — sem regressão em test_sigterm_shutdown.py
# ══════════════════════════════════════════════════════════════════════════════

class TestSemRegressaoShutdown:
    """A introdução do try/finally do lock não deve alterar o comportamento já
    coberto por tests/test_sigterm_shutdown.py. Reexecuta os cenários chave
    daquele módulo dentro desta suíte para deixar a dependência explícita
    (o módulo original permanece a fonte de verdade e continua rodando
    normalmente na suíte completa)."""

    def test_handler_sigterm_ainda_registrado_com_lock_livre(self, monkeypatch):
        """main() deve continuar registrando o handler de SIGTERM mesmo com a
        aquisição do lock adicionada no início."""
        import signal

        registrados = {}

        def fake_signal(signum, handler):
            registrados[signum] = handler

        monkeypatch.setattr(m.signal, "signal", fake_signal)
        _patch_main_collaborators(monkeypatch)

        m.main()

        assert signal.SIGTERM in registrados, (
            "main() deixou de registrar o handler de SIGTERM após a "
            "integração do InstanceLock (regressão do #70)."
        )
        assert registrados[signal.SIGTERM] is m._handle_sigterm

    def test_shutdown_limpo_nao_e_bloqueado_pelo_finally_do_lock(self, monkeypatch):
        """O finally de liberação do lock não deve impedir nem mascarar o
        encerramento limpo por _Shutdown (SIGTERM)."""
        _patch_main_collaborators(monkeypatch)  # loop levanta _Shutdown

        # Não deve levantar nem SystemExit nem qualquer outra exceção: o
        # encerramento por _Shutdown é tratado dentro do loop e main() retorna
        # normalmente.
        m.main()
