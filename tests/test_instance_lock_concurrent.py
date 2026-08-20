"""Casos de Teste — Concorrência real de instância única + regressão composta
do incidente #97, frente de instância única (issue #152)

Contexto: as duas tasks anteriores da mesma story (#150, #151) cobriram,
respectivamente, a primitiva isolada `InstanceLock`/`LockHeldError`
(`tests/test_instance_lock.py`) e a integração com `main()`
(`tests/test_instance_lock_integration.py`), incluindo testes de
unidade/integração ponto-a-ponto (dentro do processo de teste, com no máximo
um subprocesso auxiliar). Esta suíte **não repete** esses testes: foca
exclusivamente em cenários de concorrência real entre múltiplos processos
(`flock` é por processo/descriptor — não é possível reproduzir a disputa real
com threads) e no cenário composto do épico #104 (item 6 do critério de
encerramento — ver ADR-06, seção 10, subseção "Regressão do incidente #97").

Documentação de referência (já aprovada, não repetida aqui):
- doc/requirements/confiabilidade-parent-recursivo/business-rules.md (RN-009, RN-010)
- doc/architecture/confiabilidade-parent-recursivo/arquitetura.md (ADR-06,
  seção 10 "Estratégia de testes", subseção "Regressão do incidente #97")
  — disponível na branch epic104-104-post_mortem_de_produto_incidente_...

Pré-requisito confirmado antes da escrita destes testes: `src/core/lock.py`
(issue #150) e a integração de `InstanceLock` em `main()` (issue #151) já
estão presentes em `origin/epic` — branch de trabalho desta issue, conforme
`pipe.yml` (`boards.task.flow: feature`, `create/merge: epic`).

Cobertura (critérios de aceite da issue #152):
  1. Duas instâncias reais disputando o mesmo diretório de estado.
  2. Rajada de N (>=5) instâncias reais contra o mesmo estado.
  3. Reinicialização legítima após encerramento normal (release explícito).
  4. Reinicialização legítima após crash (SIGKILL), no nível de main()/processo
     completo — não apenas da primitiva isolada (já coberto em
     test_instance_lock.py, critério 4).
  5. Regressão composta do incidente #97 — frente de instância única (item 6
     da subseção "Regressão do incidente #97" do ADR-06).
  6. Nenhuma regressão nas suítes test_instance_lock.py e
     test_instance_lock_integration.py (verificada por execução completa; não
     duplicada nesta suíte).
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from src.core.lock import InstanceLock, LockHeldError
except ModuleNotFoundError:
    InstanceLock = None
    LockHeldError = None

_HELPER_SCRIPT = Path(__file__).resolve().parent / "_lock_holder_helper.py"

# Script auxiliar mínimo que exercita o ciclo de vida real de main() (issue
# #151): adquire o InstanceLock, sinaliza no stdout e trava — usado nos
# cenários 4 e 5, que exigem passar pelo ponto de entrada real (ou o trecho
# mínimo equivalente), não apenas pela primitiva InstanceLock isolada.
_MAIN_LOCK_HELPER_SCRIPT = Path(__file__).resolve().parent / "_main_lock_holder_helper.py"


def _skip_if_not_implemented():
    if InstanceLock is None:
        pytest.skip("InstanceLock não implementada ainda (src/core/lock.py)")


def _kill_if_alive(proc: subprocess.Popen) -> None:
    """Finaliza o subprocesso se ainda estiver vivo (cleanup de segurança)."""
    if proc.poll() is None:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _spawn_lock_attempt(lock_path: Path) -> subprocess.Popen:
    """Dispara um subprocesso que tenta adquirir o lock uma única vez e sai.

    Usa o mesmo `_lock_holder_helper.py` das suítes anteriores, mas aqui
    apenas para gerar concorrência real de aquisição — o subprocesso trava
    após imprimir "LOCK_ACQUIRED" (ou sai com código de erro se recusado);
    quem sai sem essa linha e com código != 0 foi recusado via
    `LockHeldError` propagada (o helper não trata a exceção, então o
    traceback + código de saída != 0 do Python é o sinal).
    """
    return subprocess.Popen(
        [sys.executable, str(_HELPER_SCRIPT), str(lock_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _wait_outcome(proc: subprocess.Popen, timeout: float = 10.0) -> str:
    """Aguarda o subprocesso sinalizar sucesso ("LOCK_ACQUIRED" no stdout) ou
    término (recusado). Retorna "acquired" ou "refused"."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if "LOCK_ACQUIRED" in line:
            return "acquired"
        if proc.poll() is not None:
            return "refused"
    return "refused" if proc.poll() is not None else "timeout"


# ══════════════════════════════════════════════════════════════════════════════
# Cenário 1 — duas instâncias reais disputando o mesmo diretório de estado
# ══════════════════════════════════════════════════════════════════════════════

class TestDuasInstanciasReais:
    """Dois subprocessos reais disputam o mesmo path de lock: exatamente um
    obtém sucesso, o outro é recusado com código de saída não-zero e sem
    alterar nenhum arquivo do diretório de estado compartilhado."""

    def test_exatamente_um_dos_dois_obtem_o_lock(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"

        # Arquivo de estado compartilhado adicional, para confirmar que o
        # perdedor não escreve nada no diretório além de tentar o lock.
        estado_path = tmp_path / "changeQueue.json"
        estado_path.write_text('[{"id": "1"}]', encoding="utf-8")
        conteudo_antes = estado_path.read_text(encoding="utf-8")

        proc_a = _spawn_lock_attempt(lock_path)
        try:
            outcome_a = _wait_outcome(proc_a)
            assert outcome_a == "acquired", (
                "1º subprocesso deveria adquirir o lock sem concorrência"
            )

            proc_b = _spawn_lock_attempt(lock_path)
            try:
                outcome_b = _wait_outcome(proc_b)
                assert outcome_b == "refused", (
                    "2º subprocesso deveria ser recusado (lock já detido pelo 1º)"
                )
                proc_b.wait(timeout=5)
                assert proc_b.returncode != 0, (
                    "Subprocesso recusado deve terminar com código de saída "
                    "não-zero (LockHeldError não tratada propaga traceback)"
                )
                assert "LockHeldError" in proc_b.stderr.read()
            finally:
                _kill_if_alive(proc_b)

            # Estado compartilhado não foi tocado pelo perdedor.
            assert estado_path.read_text(encoding="utf-8") == conteudo_antes, (
                "O subprocesso recusado não deveria alterar nenhum arquivo "
                "do diretório de estado compartilhado"
            )
        finally:
            _kill_if_alive(proc_a)


# ══════════════════════════════════════════════════════════════════════════════
# Cenário 2 — rajada de N (>=5) instâncias reais contra o mesmo estado
# ══════════════════════════════════════════════════════════════════════════════

class TestRajadaDeInstancias:
    """N subprocessos disparados o mais simultaneamente possível contra o
    mesmo path de lock: exatamente 1 obtém sucesso, os demais N-1 são
    recusados — sem corrida que permita dois vencedores."""

    N = 8

    def test_exatamente_um_vencedor_entre_n_instancias(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"

        procs = [_spawn_lock_attempt(lock_path) for _ in range(self.N)]
        try:
            outcomes = [_wait_outcome(p) for p in procs]

            assert outcomes.count("timeout") == 0, (
                f"Algum subprocesso não sinalizou desfecho a tempo: {outcomes}"
            )
            assert outcomes.count("acquired") == 1, (
                f"Esperado exatamente 1 vencedor entre {self.N} instâncias, "
                f"obtidos {outcomes.count('acquired')}. Desfechos: {outcomes}"
            )
            assert outcomes.count("refused") == self.N - 1, (
                f"Esperado {self.N - 1} recusados, obtidos "
                f"{outcomes.count('refused')}. Desfechos: {outcomes}"
            )

            # Confirma que todos os recusados de fato saíram com erro (nenhum
            # "recusado" apenas por não ter tentado ainda).
            for proc, outcome in zip(procs, outcomes):
                if outcome == "refused":
                    proc.wait(timeout=5)
                    assert proc.returncode != 0, (
                        "Todo subprocesso recusado deve terminar com código "
                        "de saída não-zero"
                    )
        finally:
            for proc in procs:
                _kill_if_alive(proc)


# ══════════════════════════════════════════════════════════════════════════════
# Cenário 3 — reinicialização legítima após encerramento normal
# ══════════════════════════════════════════════════════════════════════════════

class TestReinicializacaoAposEncerramentoNormal:
    """Um subprocesso adquire e libera o lock (shutdown normal); imediatamente
    depois, uma nova aquisição sobre o mesmo path sucede sem limpeza manual."""

    def test_nova_aquisicao_sucede_apos_liberacao_normal(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"

        proc = _spawn_lock_attempt(lock_path)
        try:
            outcome = _wait_outcome(proc)
            assert outcome == "acquired"

            # Encerramento normal: SIGTERM é ignorado pelo helper (sem
            # handler instalado) e mataria o processo sem executar
            # release(); para simular shutdown "normal" (com release()
            # explícito) usamos o próprio processo de teste como segunda
            # instância, mas primeiro finalizamos o subprocesso de forma
            # limpa como um detentor concorrente que sai de cena.
            proc.terminate()
            proc.wait(timeout=5)
        finally:
            _kill_if_alive(proc)

        # Adquire e libera no processo de teste, simulando shutdown normal
        # explícito (acquire -> release), e confirma reaquisição imediata
        # subsequente sem qualquer limpeza manual do arquivo.
        lock = InstanceLock(lock_path)
        lock.acquire()
        lock.release()

        lock_novo = InstanceLock(lock_path)
        lock_novo.acquire()  # não deve levantar LockHeldError
        try:
            assert lock_path.exists()
        finally:
            lock_novo.release()

    def test_novo_subprocesso_adquire_apos_terminate_do_anterior(self, tmp_path):
        """Variante com dois subprocessos reais: o 1º sai por terminate()
        (SIGTERM) sem detentor concorrente disputando; o 2º adquire em
        seguida sobre o mesmo path."""
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"

        proc_a = _spawn_lock_attempt(lock_path)
        try:
            assert _wait_outcome(proc_a) == "acquired"
            proc_a.terminate()
            proc_a.wait(timeout=5)
        finally:
            _kill_if_alive(proc_a)

        proc_b = _spawn_lock_attempt(lock_path)
        try:
            assert _wait_outcome(proc_b) == "acquired", (
                "Novo subprocesso deveria adquirir o lock livremente após o "
                "encerramento (mesmo que não normal/limpo) do anterior — o "
                "kernel libera o flock ao fechar os descritores do processo"
            )
        finally:
            _kill_if_alive(proc_b)


# ══════════════════════════════════════════════════════════════════════════════
# Cenário 4 — reinicialização legítima após crash (SIGKILL), nível de main()
# ══════════════════════════════════════════════════════════════════════════════

class TestReinicializacaoAposCrashNoProcessoCompleto:
    """Equivalente ao critério de aceite 4 de test_instance_lock.py, mas
    validado no nível de main()/processo completo da esteira (issue #151),
    reaproveitando o helper que exercita o ciclo de vida real via
    `src.__main__` (ponto de entrada), não apenas InstanceLock isolada."""

    def test_lock_liberado_apos_sigkill_do_processo_completo(self, tmp_path):
        _skip_if_not_implemented()
        if not _MAIN_LOCK_HELPER_SCRIPT.exists():
            pytest.skip(
                "_main_lock_holder_helper.py ausente — helper do ciclo de "
                "vida real de main() (issue #151) não encontrado"
            )

        lock_path = tmp_path / "pipe.lock"

        proc = subprocess.Popen(
            [sys.executable, str(_MAIN_LOCK_HELPER_SCRIPT), str(lock_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.time() + 10
            acquired = False
            while time.time() < deadline:
                line = proc.stdout.readline()
                if "LOCK_ACQUIRED" in line:
                    acquired = True
                    break
                if proc.poll() is not None:
                    break
            assert acquired, (
                "Processo completo (via main()) não confirmou aquisição do "
                f"lock a tempo. stderr: {proc.stderr.read() if proc.stderr else ''}"
            )

            # Confirma que, enquanto o processo completo vive, o lock está
            # de fato ocupado.
            lock_concorrente = InstanceLock(lock_path)
            with pytest.raises(LockHeldError) as exc_info:
                lock_concorrente.acquire()
            assert exc_info.value.holder_pid == proc.pid

            # Crash: mata sem chance de cleanup (sem executar o finally do
            # main() que chamaria lock.release()).
            proc.send_signal(signal.SIGKILL)
            proc.wait(timeout=5)

            # O kernel libera o flock ao fechar os fds do processo morto —
            # nova aquisição deve suceder imediatamente, sem intervenção manual.
            lock_novo = InstanceLock(lock_path)
            lock_novo.acquire()
            try:
                assert lock_path.exists()
            finally:
                lock_novo.release()
        finally:
            _kill_if_alive(proc)


# ══════════════════════════════════════════════════════════════════════════════
# Cenário 5 — regressão composta do incidente #97 (frente de instância única)
# ══════════════════════════════════════════════════════════════════════════════

class TestRegressaoCompostaInstanciaUnica:
    """Regressão composta do incidente #97 (ADR-06, seção 10, subseção
    "Regressão do incidente #97", item 6: "somente uma instância operando no
    mesmo estado").

    Monta o cenário mínimo relevante a esta frente: uma instância "ativa"
    (lock adquirido + fila de mudanças populada com trabalho em andamento) e
    uma segunda tentativa de inicialização completa via main(). Confirma:
      a) a fila de mudanças da 1ª instância não é alterada (byte a byte);
      b) a 2ª tentativa não invoca startup()/sync/board (mocks não chamados);
      c) exatamente uma instância permanece operando ao final.
    """

    @pytest.fixture(autouse=True)
    def _chdir_tmp(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".pipe").mkdir(exist_ok=True)
        yield

    def _minimal_config(self):
        return {"sleep": 1, "boards": {"platform": "github"}}

    def _patch_main_collaborators(self, monkeypatch, m):
        """Isola main() do restante do sistema (mesmo padrão de
        test_instance_lock_integration.py / test_sigterm_shutdown.py).

        A 2ª tentativa, se chegar a passar pelo lock (o que não deveria
        ocorrer), teria toda a colaboração externa mockada/espiada — usado
        aqui para provar, via assert_not_called, que nada disso é acionado.
        """
        from unittest.mock import MagicMock

        monkeypatch.setattr(m, "check_config", lambda: self._minimal_config())
        monkeypatch.setattr(m, "startup", MagicMock())
        monkeypatch.setattr(m, "board_full_sync", MagicMock())
        monkeypatch.setattr(m, "get_board_ids", lambda cfg: ["b1"])

        def _stop(*_a, **_k):
            raise m._Shutdown()

        monkeypatch.setattr(m, "detect_local_all", _stop)
        monkeypatch.setattr(m, "sync_remote_board", _stop)
        monkeypatch.setattr(m, "sync_board", _stop)
        monkeypatch.setattr(m, "ADAPTERS", {"github": lambda: object()})

        connect_spy = MagicMock()
        check_access_spy = MagicMock()

        class _SpyBoard:
            def __init__(self, adapter):
                pass

            def connect(self, cfg):
                connect_spy()

            def check_access(self, cfg):
                check_access_spy()

        monkeypatch.setattr(m, "Board", _SpyBoard)
        return connect_spy, check_access_spy

    def test_segunda_tentativa_nao_altera_fila_nem_invoca_startup_ou_board(
        self, monkeypatch
    ):
        _skip_if_not_implemented()

        import src.__main__ as m
        from src.core.change_queue import ChangeQueue, QUEUE_FILE
        from src.core.board import ChangeItem, SyncEvent

        # Item 6, ADR-06 seção 10: "somente uma instância operando no mesmo
        # estado" — instância "ativa" com lock detido e trabalho em andamento
        # na fila de mudanças.
        holder = InstanceLock()
        holder.acquire()
        try:
            queue = ChangeQueue()
            queue.add(ChangeItem.of(SyncEvent.CHANGE_UP, id="200", board="task"))
            queue.add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id="201", board="task"))

            conteudo_antes = QUEUE_FILE.read_bytes()
            assert conteudo_antes.strip(), "Pré-condição: fila deveria estar populada"

            connect_spy, check_access_spy = self._patch_main_collaborators(
                monkeypatch, m
            )

            # (b) Segunda tentativa de inicialização completa.
            with pytest.raises(SystemExit) as exc_info:
                m.main()
            assert exc_info.value.code == 1, (
                "2ª tentativa deveria ser recusada com SystemExit(1)"
            )

            m.startup.assert_not_called()
            m.board_full_sync.assert_not_called()
            connect_spy.assert_not_called()
            check_access_spy.assert_not_called()

            # (a) Fila de mudanças da 1ª instância idêntica byte a byte.
            conteudo_depois = QUEUE_FILE.read_bytes()
            assert conteudo_depois == conteudo_antes, (
                "A fila de mudanças da 1ª instância (ativa, com trabalho em "
                "andamento) foi alterada pela 2ª tentativa de inicialização "
                "— regressão do incidente #97, frente de instância única "
                "(ADR-06, seção 10, item 6: 'somente uma instância operando "
                "no mesmo estado')."
            )
            assert QUEUE_FILE.exists(), (
                "QUEUE_FILE não deveria ter sido removido/truncado pela 2ª "
                "tentativa recusada."
            )

            # (c) Exatamente uma instância permanece operando: a 1ª ainda
            # detém o lock; uma terceira tentativa também deve ser recusada.
            terceira = InstanceLock()
            with pytest.raises(LockHeldError):
                terceira.acquire()
        finally:
            holder.release()

        # Após a liberação da 1ª instância, uma nova aquisição sucede —
        # confirma que o lock nunca ficou "duplamente" detido nem corrompido
        # pela tentativa recusada.
        pos_check = InstanceLock()
        pos_check.acquire()
        pos_check.release()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
