"""Testes de SnapshotGuard — captura, comparação e restauração atômica.

Cobrem os 9 critérios de aceite da issue #153:

1. Snapshot inalterado -> nenhuma escrita.
2. Snapshot alterado (mesmo tamanho e/ou mtime forjado) -> restaurado byte a byte.
3. Snapshot removido durante o bloco -> recriado com o conteúdo capturado.
4. Arquivo criado durante o bloco (inexistente antes) -> removido.
5. Cada violação gera exatamente um log.warning com board_id + hashes,
   nunca o conteúdo dos bytes.
6. Restauração ocorre tanto em saída normal quanto por exceção; a exceção
   original continua se propagando após a restauração.
7. Falha na própria restauração (ex.: OSError) -> levanta
   SnapshotIntegrityError identificando board_id e causa, precedendo/
   substituindo a exceção original do bloco.
8. Overhead da guarda é da ordem de milissegundos (sem subprocess/rede).
9. Nenhuma regressão nos testes existentes de snapshot.py.

Os testes importam `SnapshotGuard`/`snapshot_guard` e `SnapshotIntegrityError`
de `src.core.snapshot`, conforme especificado na issue. Isolam o filesystem
via `tmp_path` + `monkeypatch.chdir`, seguindo o padrão já usado em
`tests/test_correcao4_validacao_pos_agente.py`.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.snapshot import Snapshot, SnapshotGuard, SnapshotIntegrityError  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

BOARD_ID = "task"


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    """Isola .pipe/ em diretório temporário por teste."""
    monkeypatch.chdir(tmp_path)
    yield


def _snapshot_path(board_id: str = BOARD_ID) -> Path:
    return Snapshot(board_id).path


def _write_snapshot(board_id: str, issues: list[dict]) -> bytes:
    """Cria um snapshot.json e retorna os bytes escritos."""
    path = _snapshot_path(board_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"board": {"col1": "Column 1"}, "issues": issues, "last_sync": None}
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    path.write_bytes(content)
    return content


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# CT-01: snapshot inalterado -> nenhuma escrita
# ─────────────────────────────────────────────────────────────────────────────

class TestSemViolacao:
    def test_nenhuma_escrita_quando_snapshot_inalterado(self, monkeypatch):
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()
        mtime_before = path.stat().st_mtime

        write_calls = []
        real_replace = os.replace

        def spy_replace(src, dst):
            write_calls.append((src, dst))
            return real_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy_replace)

        with SnapshotGuard(BOARD_ID):
            pass  # nada altera o snapshot

        assert path.read_bytes() == original
        assert path.stat().st_mtime == mtime_before
        assert write_calls == [], "Não deveria ocorrer nenhuma escrita/replace"

    def test_sem_violacao_quando_snapshot_nao_existe_em_nenhum_momento(self):
        path = _snapshot_path()
        assert not path.exists()

        with SnapshotGuard(BOARD_ID):
            pass

        assert not path.exists()


# ─────────────────────────────────────────────────────────────────────────────
# CT-02: snapshot alterado -> restaurado byte a byte
# ─────────────────────────────────────────────────────────────────────────────

class TestAlteracaoRestaurada:
    def test_restaura_conteudo_alterado(self):
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        with SnapshotGuard(BOARD_ID):
            path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "hacked"}')

        assert path.read_bytes() == original

    def test_restaura_quando_mesmo_tamanho_em_bytes(self):
        """Troca bytes preservando o tamanho total do arquivo."""
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()
        assert len(original) > 0

        with SnapshotGuard(BOARD_ID):
            tampered = bytearray(original)
            # Troca alguns bytes por outros ASCII válidos, mesmo tamanho.
            for i in range(min(5, len(tampered))):
                tampered[i] = ord("X")
            tampered_bytes = bytes(tampered)
            assert len(tampered_bytes) == len(original)
            assert tampered_bytes != original
            path.write_bytes(tampered_bytes)

        assert path.read_bytes() == original
        assert len(path.read_bytes()) == len(original)

    def test_restaura_quando_mtime_forjado_idêntico_ao_original(self):
        """Mesmo com mtime idêntico ao original, a alteração deve ser detectada
        (comparação é sempre por bytes/hash, nunca por metadado do FS)."""
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()
        stat_before = path.stat()

        with SnapshotGuard(BOARD_ID):
            path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "tampered"}')
            # Forja mtime/atime para serem idênticos ao capturado antes da alteração.
            os.utime(path, (stat_before.st_atime, stat_before.st_mtime))

        assert path.read_bytes() == original


# ─────────────────────────────────────────────────────────────────────────────
# CT-03: snapshot removido -> recriado
# ─────────────────────────────────────────────────────────────────────────────

class TestRemocaoRestaurada:
    def test_recria_snapshot_removido_durante_o_bloco(self):
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        with SnapshotGuard(BOARD_ID):
            path.unlink()
            assert not path.exists()

        assert path.exists()
        assert path.read_bytes() == original


# ─────────────────────────────────────────────────────────────────────────────
# CT-04: arquivo criado indevidamente -> removido
# ─────────────────────────────────────────────────────────────────────────────

class TestCriacaoIndevidaRemovida:
    def test_remove_arquivo_criado_que_nao_existia_antes(self):
        path = _snapshot_path()
        assert not path.exists()

        with SnapshotGuard(BOARD_ID):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "rogue"}')
            assert path.exists()

        assert not path.exists()


# ─────────────────────────────────────────────────────────────────────────────
# CT-05: warning de violação — board_id + hashes, nunca os bytes
# ─────────────────────────────────────────────────────────────────────────────

class TestLogWarning:
    def test_loga_warning_uma_vez_em_alteracao_com_hashes_e_sem_bytes(self, mocker=None):
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()
        tampered_content = b'{"board": {}, "issues": [], "last_sync": "SECRETPAYLOAD"}'

        from unittest.mock import patch

        with patch("src.core.snapshot.log") as mock_log:
            with SnapshotGuard(BOARD_ID):
                path.write_bytes(tampered_content)

            assert mock_log.warning.call_count == 1

            call = mock_log.warning.call_args
            call_text = " ".join(str(a) for a in call.args) + " " + str(call.kwargs)

            assert BOARD_ID in call_text
            assert _sha256(original) in call_text
            assert _sha256(tampered_content) in call_text
            assert b"SECRETPAYLOAD".decode() not in call_text

    def test_loga_warning_uma_vez_em_remocao(self):
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        from unittest.mock import patch

        with patch("src.core.snapshot.log") as mock_log:
            with SnapshotGuard(BOARD_ID):
                path.unlink()

            assert mock_log.warning.call_count == 1
            call_text = str(mock_log.warning.call_args)
            assert BOARD_ID in call_text
            assert _sha256(original) in call_text
            assert "None" in call_text

    def test_loga_warning_uma_vez_em_criacao_indevida(self):
        path = _snapshot_path()

        from unittest.mock import patch

        with patch("src.core.snapshot.log") as mock_log:
            with SnapshotGuard(BOARD_ID):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "created"}')

            assert mock_log.warning.call_count == 1
            call_text = str(mock_log.warning.call_args)
            assert BOARD_ID in call_text
            assert "None" in call_text

    def test_nenhum_warning_quando_sem_violacao(self):
        _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])

        from unittest.mock import patch

        with patch("src.core.snapshot.log") as mock_log:
            with SnapshotGuard(BOARD_ID):
                pass

            mock_log.warning.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# CT-06: restauração ocorre em saída normal e por exceção; exceção original propaga
# ─────────────────────────────────────────────────────────────────────────────

class TestPropagacaoDeExcecao:
    def test_restaura_e_propaga_excecao_arbitraria(self):
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        with pytest.raises(RuntimeError, match="erro do bloco"):
            with SnapshotGuard(BOARD_ID):
                path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "corrupted"}')
                raise RuntimeError("erro do bloco")

        # Restauração ocorreu mesmo com a exceção.
        assert path.read_bytes() == original

    def test_restaura_em_saida_normal_sem_excecao(self):
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        with SnapshotGuard(BOARD_ID):
            path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "corrupted"}')

        assert path.read_bytes() == original

    def test_nao_mascara_excecao_quando_nao_ha_violacao(self):
        _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])

        with pytest.raises(ValueError, match="sem relação com o snapshot"):
            with SnapshotGuard(BOARD_ID):
                raise ValueError("sem relação com o snapshot")


# ─────────────────────────────────────────────────────────────────────────────
# CT-07: falha na restauração -> SnapshotIntegrityError, precede exceção original
# ─────────────────────────────────────────────────────────────────────────────

class TestFalhaDeRestauracao:
    def test_levanta_snapshot_integrity_error_quando_replace_falha(self, monkeypatch):
        _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        def boom(*args, **kwargs):
            raise OSError("disco cheio (simulado)")

        monkeypatch.setattr(os, "replace", boom)

        with pytest.raises(SnapshotIntegrityError) as exc_info:
            with SnapshotGuard(BOARD_ID):
                path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "corrupted"}')

        err = exc_info.value
        assert BOARD_ID in str(err)
        # A causa original deve estar acessível (atributo dedicado ou __cause__).
        cause = getattr(err, "cause", None) or getattr(err, "__cause__", None)
        assert cause is not None
        assert "disco cheio" in str(cause)

    def test_snapshot_integrity_error_precede_excecao_original_do_bloco(self, monkeypatch):
        """Quando a guarda precisa restaurar E o bloco levantou uma exceção,
        e a própria restauração falha, o que se propaga é
        SnapshotIntegrityError (mais grave), não a exceção original do bloco."""
        _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        def boom(*args, **kwargs):
            raise OSError("falha de escrita (simulado)")

        monkeypatch.setattr(os, "replace", boom)

        with pytest.raises(SnapshotIntegrityError):
            with SnapshotGuard(BOARD_ID):
                path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "corrupted"}')
                raise RuntimeError("erro original do bloco, deve ser preterido")

    def test_levanta_snapshot_integrity_error_ao_recriar_arquivo_removido(self, monkeypatch):
        _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        def boom(*args, **kwargs):
            raise OSError("falha ao recriar (simulado)")

        monkeypatch.setattr(os, "replace", boom)

        with pytest.raises(SnapshotIntegrityError) as exc_info:
            with SnapshotGuard(BOARD_ID):
                path.unlink()

        assert BOARD_ID in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# CT-08: overhead da guarda é da ordem de milissegundos
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    def test_overhead_da_guarda_em_snapshot_tipico_e_baixo(self):
        """Snapshot de algumas dezenas de KB; captura+comparação sem violação
        deve ser rápida (sem subprocess/rede) — ordem de milissegundos."""
        issues = [
            {
                "id": str(i),
                "updated_at": "2026-01-01T00:00:00Z",
                "title": f"Issue número {i} com um título de tamanho razoável para simular dados reais",
                "body": "Corpo de exemplo. " * 20,
                "labels": ["backend", "security", "confiabilidade"],
            }
            for i in range(200)
        ]
        content = _write_snapshot(BOARD_ID, issues)
        assert len(content) >= 20_000  # dezenas de KB

        start = time.perf_counter()
        with SnapshotGuard(BOARD_ID):
            pass
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"Overhead da guarda muito alto: {elapsed:.4f}s"

    def test_nao_usa_subprocess(self, monkeypatch):
        import subprocess as subprocess_module

        def fail_if_called(*args, **kwargs):
            raise AssertionError("SnapshotGuard não deve chamar subprocess")

        monkeypatch.setattr(subprocess_module, "run", fail_if_called)
        monkeypatch.setattr(subprocess_module, "Popen", fail_if_called)

        _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])

        with SnapshotGuard(BOARD_ID):
            pass


# ─────────────────────────────────────────────────────────────────────────────
# CT-09: uso alternativo como contextmanager funcional (snapshot_guard)
# ─────────────────────────────────────────────────────────────────────────────

class TestFuncaoContextManagerOpcional:
    def test_snapshot_guard_function_style_se_disponivel(self):
        """A especificação permite implementar via contextlib.contextmanager
        como `snapshot_guard(board_id)`. Se essa função existir no módulo,
        deve ter o mesmo comportamento de restauração que a classe."""
        try:
            from src.core.snapshot import snapshot_guard
        except ImportError:
            pytest.skip("Projeto optou pelo estilo de classe (SnapshotGuard); "
                        "função `snapshot_guard` não é obrigatória.")

        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()

        with snapshot_guard(BOARD_ID):
            path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "corrupted"}')

        assert path.read_bytes() == original


# ─────────────────────────────────────────────────────────────────────────────
# CT-10: escrita atômica — arquivo temporário no mesmo diretório + os.replace
# ─────────────────────────────────────────────────────────────────────────────

class TestEscritaAtomica:
    def test_restauracao_usa_arquivo_temporario_no_mesmo_diretorio_e_replace(self, monkeypatch):
        """Verifica que a restauração passa por um arquivo temporário no mesmo
        diretório do snapshot e finaliza com os.replace (atomicidade), não
        escrita direta via write_bytes no path final."""
        original = _write_snapshot(BOARD_ID, [{"id": "1", "updated_at": "2026-01-01"}])
        path = _snapshot_path()
        snap_dir = path.parent

        replace_calls = []
        real_replace = os.replace

        def spy_replace(src, dst):
            src_path = Path(src)
            # O arquivo temporário deve estar no mesmo diretório do snapshot
            # (garante que os.replace seja atômico no mesmo filesystem).
            assert src_path.parent == snap_dir
            assert Path(dst) == path
            replace_calls.append((src, dst))
            return real_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy_replace)

        with SnapshotGuard(BOARD_ID):
            path.write_bytes(b'{"board": {}, "issues": [], "last_sync": "corrupted"}')

        assert len(replace_calls) == 1
        assert path.read_bytes() == original
