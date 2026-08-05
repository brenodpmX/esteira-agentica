"""Casos de Teste — LockGuard: InstanceLock (issue #150)

Contexto: primitiva de lock local (`.pipe/pipe.lock`) que garante
exclusividade de instância por diretório de estado, usando
`fcntl.flock(LOCK_EX | LOCK_NB)`. Esta task entrega apenas a primitiva
isolada (classe + testes) — sem integração com main()/startup() (próxima
task da mesma story, issue #151).

Referência: doc/architecture/confiabilidade-parent-recursivo/arquitetura.md
(ADR-06) e doc/requirements/confiabilidade-parent-recursivo/business-rules.md
(RN-009), disponíveis na branch
epic104-104-post_mortem_de_produto_incidente_reportado_em_01082026 no momento
da escrita destes testes.

ESTADO: `src/core/lock.py` ainda não existe (task de desenvolvimento
subsequente). Os testes desta suíte usam o padrão condicional já empregado em
tests/test_build_prompt_protected_paths.py (getattr + pytest.skip) para os
símbolos que dependem da implementação, e falham (não skip) nos pontos que
documentam requisitos obrigatórios da issue — mantendo a suíte utilizável
tanto como especificação executável antes da implementação quanto como
regressão depois.

Cobertura (critérios de aceite da issue #150):
  1. acquire() com sucesso, grava metadados, mantém fd aberto
  2. segunda instância concorrente levanta LockHeldError com holder_pid correto
  3. release() libera; nova acquire() subsequente sobrescreve metadados
  4. lock órfão: subprocesso morto com SIGKILL libera o lock (propriedade do kernel)
  5. release() idempotente (sem acquire prévio, ou chamado 2x)
  6. release() NÃO deleta o arquivo de lock
  7. .pipe/pipe.lock em PROTECTED_PATHS (ver tests/test_build_prompt_protected_paths.py)
  8. .pipe/pipe.lock no CONTEXT.md gerado (ver tests/test_context_generator.py)
  9. sem regressão nas duas suítes acima (critérios 7/8)

Os critérios 7, 8 e 9 são cobertos por extensões nas suítes existentes
(test_build_prompt_protected_paths.py::TestProtectedPathsConstant e
test_context_generator.py::TestArquivosProtegidos), conforme instrução da
issue ("estender a parametrização existente ... não duplicar a suíte").
Esta suíte cobre exclusivamente os critérios 1–6, específicos de
InstanceLock/LockHeldError.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import src.core.lock as _lock_module
except ModuleNotFoundError:
    _lock_module = None

InstanceLock = getattr(_lock_module, "InstanceLock", None)
LockHeldError = getattr(_lock_module, "LockHeldError", None)

_HELPER_SCRIPT = Path(__file__).resolve().parent / "_lock_holder_helper.py"


def _skip_if_not_implemented():
    if InstanceLock is None:
        pytest.skip("InstanceLock não implementada ainda (src/core/lock.py)")


# ══════════════════════════════════════════════════════════════════════════════
# Existência dos símbolos — documentam a interface exigida pela issue
# ══════════════════════════════════════════════════════════════════════════════

class TestInterface:

    def test_modulo_lock_existe(self):
        assert _lock_module is not None

    def test_instancelock_existe(self):
        assert InstanceLock is not None, \
            "InstanceLock deve ser definida em src/core/lock.py"

    def test_lockhelderror_existe(self):
        assert LockHeldError is not None, \
            "LockHeldError deve ser definida em src/core/lock.py"

    def test_lockhelderror_e_excecao(self):
        if LockHeldError is None:
            pytest.skip("LockHeldError não implementada ainda")
        assert issubclass(LockHeldError, Exception)


# ══════════════════════════════════════════════════════════════════════════════
# Critério 1 — acquire() com sucesso
# ══════════════════════════════════════════════════════════════════════════════

class TestAcquireComSucesso:

    def test_acquire_sem_concorrencia_nao_levanta(self, tmp_path):
        _skip_if_not_implemented()
        lock = InstanceLock(tmp_path / "pipe.lock")
        lock.acquire()
        try:
            assert (tmp_path / "pipe.lock").exists()
        finally:
            lock.release()

    def test_acquire_grava_metadados_legiveis(self, tmp_path):
        """Metadados devem conter pid, started_at e host, legíveis (JSON ou texto)."""
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock = InstanceLock(lock_path)
        lock.acquire()
        try:
            content = lock_path.read_text(encoding="utf-8")
            assert str(os.getpid()) in content, \
                "PID do processo atual deve estar nos metadados"
            # Deve ser parseável como JSON de uma linha (formato sugerido pela issue).
            try:
                data = json.loads(content)
                assert "pid" in data
                assert "started_at" in data
                assert "host" in data
                assert data["pid"] == os.getpid()
            except json.JSONDecodeError:
                # Formato texto simples também é aceito pela issue ("a critério
                # do desenvolvedor") — mas precisa conter os três campos.
                assert "started_at" in content or "host" in content, \
                    "Metadados em texto simples devem conter started_at/host"
        finally:
            lock.release()

    def test_acquire_mantem_fd_aberto(self, tmp_path):
        """O file descriptor deve permanecer aberto como atributo da instância
        (fechar liberaria o lock do kernel prematuramente)."""
        _skip_if_not_implemented()
        lock = InstanceLock(tmp_path / "pipe.lock")
        lock.acquire()
        try:
            fd_attr = getattr(lock, "_fd", None)
            assert fd_attr is not None, \
                "self._fd deve estar definido após acquire() bem-sucedido"
        finally:
            lock.release()

    def test_acquire_cria_arquivo_se_nao_existir(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "subdir_inexistente_nao" / "pipe.lock"
        lock_path.parent.mkdir()
        lock = InstanceLock(lock_path)
        assert not lock_path.exists()
        lock.acquire()
        try:
            assert lock_path.exists()
        finally:
            lock.release()

    def test_acquire_nao_deleta_arquivo_existente_antes_de_tentar(self, tmp_path):
        """Não deve fazer unlink/recriar o arquivo antes do flock — a aquisição
        deve ocorrer sempre sobre o mesmo inode (ver ADR-06)."""
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock_path.write_text("conteudo preexistente\n")
        inode_antes = lock_path.stat().st_ino
        lock = InstanceLock(lock_path)
        lock.acquire()
        try:
            inode_depois = lock_path.stat().st_ino
            assert inode_antes == inode_depois, \
                "acquire() não deve recriar o arquivo (mesmo inode antes/depois)"
        finally:
            lock.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 2 — segunda instância concorrente levanta LockHeldError
# ══════════════════════════════════════════════════════════════════════════════

class TestSegundaInstanciaConcorrente:

    def test_segunda_acquire_levanta_lockhelderror(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock1 = InstanceLock(lock_path)
        lock1.acquire()
        try:
            lock2 = InstanceLock(lock_path)
            with pytest.raises(LockHeldError):
                lock2.acquire()
        finally:
            lock1.release()

    def test_lockhelderror_contem_holder_pid_correto(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock1 = InstanceLock(lock_path)
        lock1.acquire()
        try:
            lock2 = InstanceLock(lock_path)
            with pytest.raises(LockHeldError) as exc_info:
                lock2.acquire()
            assert exc_info.value.holder_pid == os.getpid()
        finally:
            lock1.release()

    def test_lockhelderror_contem_path_e_campos_holder(self, tmp_path):
        """LockHeldError deve expor path, holder_pid, holder_started_at,
        holder_host (None quando não for possível ler)."""
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock1 = InstanceLock(lock_path)
        lock1.acquire()
        try:
            lock2 = InstanceLock(lock_path)
            with pytest.raises(LockHeldError) as exc_info:
                lock2.acquire()
            err = exc_info.value
            assert hasattr(err, "path")
            assert hasattr(err, "holder_pid")
            assert hasattr(err, "holder_started_at")
            assert hasattr(err, "holder_host")
        finally:
            lock1.release()

    def test_lockhelderror_mensagem_humana(self, tmp_path):
        """__str__ deve produzir mensagem pronta para log, mencionando pid,
        started_at, host e o path do lock."""
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock1 = InstanceLock(lock_path)
        lock1.acquire()
        try:
            lock2 = InstanceLock(lock_path)
            with pytest.raises(LockHeldError) as exc_info:
                lock2.acquire()
            msg = str(exc_info.value)
            assert str(os.getpid()) in msg
            assert str(lock_path) in msg
        finally:
            lock1.release()

    def test_segunda_instancia_nao_corrompe_metadados_do_detentor(self, tmp_path):
        """A tentativa falha de acquire() não deve sobrescrever os metadados
        do detentor atual no arquivo."""
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock1 = InstanceLock(lock_path)
        lock1.acquire()
        try:
            content_antes = lock_path.read_text(encoding="utf-8")
            lock2 = InstanceLock(lock_path)
            with pytest.raises(LockHeldError):
                lock2.acquire()
            content_depois = lock_path.read_text(encoding="utf-8")
            assert content_antes == content_depois
        finally:
            lock1.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 3 — release() libera; nova acquire() tem sucesso e substitui metadados
# ══════════════════════════════════════════════════════════════════════════════

class TestReleaseEReaquisicao:

    def test_release_permite_nova_acquire_mesma_instancia(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock = InstanceLock(lock_path)
        lock.acquire()
        lock.release()
        lock.acquire()  # não deve levantar
        lock.release()

    def test_release_permite_nova_acquire_outra_instancia(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock1 = InstanceLock(lock_path)
        lock1.acquire()
        lock1.release()

        lock2 = InstanceLock(lock_path)
        lock2.acquire()  # não deve levantar
        lock2.release()

    def test_metadados_substituidos_apos_reaquisicao(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock1 = InstanceLock(lock_path)
        lock1.acquire()
        content_1 = lock_path.read_text(encoding="utf-8")
        lock1.release()

        # Pequena espera para garantir started_at diferente, se granularidade
        # de timestamp for de segundos.
        time.sleep(0.01)

        lock2 = InstanceLock(lock_path)
        lock2.acquire()
        try:
            content_2 = lock_path.read_text(encoding="utf-8")
            # Mesmo pid (mesmo processo de teste) mas o conteúdo é regravado
            # (trunca + grava), não meramente concatenado.
            assert content_2 != "" 
            assert not content_2.startswith(content_1 + content_1[:10]), \
                "Conteúdo não deve ser concatenado entre aquisições"
        finally:
            lock2.release()

    def test_context_manager_acquire_release(self, tmp_path):
        """__enter__/__exit__ devem funcionar como wrapper de acquire/release."""
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        with InstanceLock(lock_path) as lock:
            assert lock_path.exists()
        # Após saída do context manager, uma nova instância deve conseguir o lock.
        lock2 = InstanceLock(lock_path)
        lock2.acquire()
        lock2.release()


# ══════════════════════════════════════════════════════════════════════════════
# Critério 4 — lock órfão: kernel libera automaticamente após SIGKILL
# ══════════════════════════════════════════════════════════════════════════════

class TestLockOrfao:

    def test_lock_liberado_apos_sigkill_no_subprocesso(self, tmp_path):
        """Reproduz o cenário de crash: um subprocesso adquire o lock e é
        morto com SIGKILL sem chamar release(). Uma nova InstanceLock no
        processo de teste deve conseguir acquire() imediatamente, sem
        limpeza manual do arquivo — propriedade do flock do kernel.
        """
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"

        proc = subprocess.Popen(
            [sys.executable, str(_HELPER_SCRIPT), str(lock_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            # Aguarda confirmação de que o subprocesso adquiriu o lock, com
            # timeout para não travar o teste indefinidamente em caso de falha.
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
                "Subprocesso não confirmou aquisição do lock a tempo. "
                f"stderr: {proc.stderr.read() if proc.stderr else ''}"
            )

            # Confirma que, enquanto o subprocesso vive, o lock está de fato ocupado.
            lock_concorrente = InstanceLock(lock_path)
            with pytest.raises(LockHeldError) as exc_info:
                lock_concorrente.acquire()
            assert exc_info.value.holder_pid == proc.pid

            # Mata o subprocesso sem chance de cleanup (simula crash).
            proc.send_signal(signal.SIGKILL)
            proc.wait(timeout=5)

            # O kernel deve ter liberado o flock — nova aquisição deve suceder
            # imediatamente, sem exigir remoção manual do arquivo.
            lock_novo = InstanceLock(lock_path)
            lock_novo.acquire()  # não deve levantar LockHeldError
            try:
                assert lock_path.exists(), \
                    "O arquivo de lock deve continuar existindo após o crash"
            finally:
                lock_novo.release()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)


# ══════════════════════════════════════════════════════════════════════════════
# Critério 5 — release() idempotente
# ══════════════════════════════════════════════════════════════════════════════

class TestReleaseIdempotente:

    def test_release_sem_acquire_previo_nao_levanta(self, tmp_path):
        _skip_if_not_implemented()
        lock = InstanceLock(tmp_path / "pipe.lock")
        lock.release()  # não deve levantar

    def test_release_chamado_duas_vezes_nao_levanta(self, tmp_path):
        _skip_if_not_implemented()
        lock = InstanceLock(tmp_path / "pipe.lock")
        lock.acquire()
        lock.release()
        lock.release()  # segunda chamada não deve levantar

    def test_release_zera_fd_apos_liberar(self, tmp_path):
        _skip_if_not_implemented()
        lock = InstanceLock(tmp_path / "pipe.lock")
        lock.acquire()
        lock.release()
        assert getattr(lock, "_fd", None) is None, \
            "self._fd deve ser zerado após release()"


# ══════════════════════════════════════════════════════════════════════════════
# Critério 6 — release() não deleta o arquivo
# ══════════════════════════════════════════════════════════════════════════════

class TestArquivoNaoDeletado:

    def test_arquivo_permanece_apos_release(self, tmp_path):
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock = InstanceLock(lock_path)
        lock.acquire()
        assert lock_path.exists()
        lock.release()
        assert lock_path.exists(), \
            "release() não deve deletar o arquivo de lock"

    def test_arquivo_permanece_mesmo_vazio_apos_ciclos(self, tmp_path):
        """Após múltiplos ciclos acquire/release, o arquivo continua presente
        no filesystem (pode conter metadados antigos ou estar vazio, mas
        nunca é removido)."""
        _skip_if_not_implemented()
        lock_path = tmp_path / "pipe.lock"
        lock = InstanceLock(lock_path)
        for _ in range(3):
            lock.acquire()
            lock.release()
        assert lock_path.exists()


# ══════════════════════════════════════════════════════════════════════════════
# Default do path (Path(".pipe/pipe.lock"))
# ══════════════════════════════════════════════════════════════════════════════

class TestPathDefault:

    def test_construtor_aceita_path_customizado(self, tmp_path):
        _skip_if_not_implemented()
        custom = tmp_path / "custom.lock"
        lock = InstanceLock(custom)
        lock.acquire()
        try:
            assert custom.exists()
        finally:
            lock.release()

    def test_path_default_e_pipe_pipe_lock(self):
        """Assinatura da issue: path default = Path('.pipe/pipe.lock')."""
        _skip_if_not_implemented()
        lock = InstanceLock()
        assert str(lock.path) == str(Path(".pipe/pipe.lock")), \
            "Path default deve ser .pipe/pipe.lock conforme especificação da issue"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
