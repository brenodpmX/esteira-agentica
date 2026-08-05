"""
Casos de Teste — Resolução determinística do body da issue por identidade

Contexto: no incidente #97, o fallback "primeiro resultado do rglob" em
`_find_issue_files` (src/core/sync.py) escolheu um arquivo órfão e sobrescreveu
o conteúdo da issue #76. Esta suíte especifica e valida a nova ordem de
resolução (ADR-01 / RN-005 / RN-006), que nunca escolhe arbitrariamente entre
candidatos ambíguos — recusa (retorna None) sempre que a identidade não é
inequívoca.

Ordem de resolução esperada (ver issue #146):
  1. body_path do snapshot, se válido (existe, dentro do board, sufixo
     -body.md, prefixo do id correto, não reivindicado por outra issue) →
     aceito imediatamente, sem varrer o filesystem.
  2. Se o body_path registrado não for aceito: buscar pelo NOME COMPLETO do
     arquivo (Path(body_path).name) em todas as colunas do board.
  3. Aceitar somente se exatamente 1 candidato for encontrado no passo 2 e
     esse candidato não pertencer (via body_path) a outra issue do snapshot.
  4. Sem body_path registrado (issue legada): fallback por prefixo numérico
     ({issue_id}-*-body.md), aceito somente se houver exatamente 1 candidato.

Qualquer recusa (passos 3 ou 4 com zero ou múltiplos candidatos) deve:
  - retornar None;
  - emitir log.warning identificando board, issue_id e motivo;
  - NUNCA lançar exceção;
  - NUNCA fazer chamada de rede/board (função puramente local).

Estratégia: os testes chamam `_find_issue_files(board_id, issue_id)` diretamente
sobre uma estrutura de diretórios/snapshot construída em tmp_path, seguindo o
padrão de fixture já estabelecido em test_orphan_file_collision.py e
test_correcao3_erro_irrecuperavel_sync.py (monkeypatch de BOARDS_DIR).
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.core import sync as sync_module
from src.core.sync import _find_issue_files

BOARD_ID = "task"
ISSUE_ID = "76"


def _write_snapshot(board_dir: Path, issues: list[dict]) -> Path:
    snap_path = board_dir / "snapshot.json"
    data = {
        "board": {"backlog": "Backlog", "doing": "Doing", "done": "Done"},
        "issues": issues,
        "last_sync": None,
        "last_board_update": None,
    }
    snap_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return snap_path


class _BaseFindIssueFilesTest(unittest.TestCase):
    """Base comum: cria tmp_path com estrutura .pipe/boards/task/<col>/."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.boards_dir = self.tmp_path  # BOARDS_DIR aponta direto pra base
        self.board_dir = self.boards_dir / BOARD_ID
        self.board_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _col(self, col_id: str) -> Path:
        col_dir = self.board_dir / col_id
        col_dir.mkdir(parents=True, exist_ok=True)
        return col_dir

    def _call(self, issue_id: str = ISSUE_ID):
        with patch.object(sync_module, "BOARDS_DIR", self.boards_dir), \
             patch("src.core.snapshot.BOARDS_DIR", self.boards_dir):
            return _find_issue_files(BOARD_ID, issue_id)


# ─────────────────────────────────────────────────────────────────────────────
# CT-146-01: Passo 1 — body_path do snapshot válido é aceito imediatamente
# ─────────────────────────────────────────────────────────────────────────────

class TestBodyPathRegistradoValido(_BaseFindIssueFilesTest):
    """CT-146-01: path registrado, existente, dentro do board, sufixo/prefixo
    corretos e não reivindicado por outra issue → aceito sem varrer o fs."""

    def test_aceita_body_path_valido_imediatamente(self):
        body = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        body.write_text("# Corrigir bug\n")
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(body)},
        ])

        result = self._call()

        self.assertEqual(result, body)

    def test_nao_varre_filesystem_quando_path_registrado_e_valido(self):
        """Cria um segundo arquivo com o mesmo prefixo que seria escolhido por
        um rglob ingênuo, para provar que o path do snapshot tem prioridade."""
        body = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        body.write_text("# Corrigir bug\n")
        # "Armadilha": outro arquivo com o mesmo prefixo numérico em outra coluna.
        trap = self._col("backlog") / f"{ISSUE_ID}-outro_nome-body.md"
        trap.write_text("# Armadilha\n")

        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(body)},
        ])

        result = self._call()

        self.assertEqual(
            result, body,
            "Deveria retornar o path registrado no snapshot, ignorando a armadilha",
        )


class TestBodyPathRegistradoInvalido(_BaseFindIssueFilesTest):
    """Condições que tornam o body_path registrado INVÁLIDO para o passo 1
    (deve então cair para o passo 2, e não ser aceito diretamente)."""

    def test_rejeita_body_path_sem_sufixo_body_md(self):
        """Arquivo que não termina em '-body.md' não deve ser aceito no passo 1."""
        wrong = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-history.md"
        wrong.write_text("# não é um body\n")
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(wrong)},
        ])

        result = self._call()

        self.assertIsNone(
            result,
            "Path sem sufixo -body.md não deve ser aceito, e não há outro "
            "candidato válido pelo nome completo",
        )

    def test_rejeita_body_path_com_prefixo_de_id_errado(self):
        """Arquivo que não começa com '<issue_id>-' não deve ser aceito no passo 1."""
        wrong = self._col("doing") / "999-nome_errado-body.md"
        wrong.write_text("# id errado\n")
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(wrong)},
        ])

        result = self._call()

        self.assertIsNone(result)

    def test_rejeita_body_path_reivindicado_por_outra_issue(self):
        """Mesmo existindo e com nome correto, se outra issue do snapshot
        também registra esse body_path, não é aceito no passo 1 (nem pelo
        passo 2/3, pois o candidato pertence a outra issue)."""
        shared = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        shared.write_text("# Compartilhado\n")
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(shared)},
            {"id": "77", "column": "doing", "body_path": str(shared)},
        ])

        result = self._call()

        self.assertIsNone(
            result,
            "Path reivindicado por outra issue não deve ser retornado para #76",
        )

    def test_rejeita_body_path_fora_do_diretorio_do_board(self):
        """Path registrado que escapa da árvore do board (BOARDS_DIR/board_id)
        não deve ser aceito no passo 1, mesmo existindo e com nome correto."""
        outside_dir = self.tmp_path / "outside"
        outside_dir.mkdir()
        outside = outside_dir / f"{ISSUE_ID}-corrigir_bug-body.md"
        outside.write_text("# Fora da árvore do board\n")

        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(outside)},
        ])

        result = self._call()

        self.assertIsNone(
            result,
            "Path fora do diretório do board não deve ser aceito, mesmo existindo",
        )


# ─────────────────────────────────────────────────────────────────────────────
# CT-146-02: Passo 2/3 — body_path não existe mais (arquivo movido)
# ─────────────────────────────────────────────────────────────────────────────

class TestBodyPathMovido(_BaseFindIssueFilesTest):
    """CT-146-02: path registrado não existe mais → busca por nome completo
    em todas as colunas; aceita se exatamente 1 candidato."""

    def test_encontra_arquivo_movido_por_nome_completo(self):
        old_path = self.board_dir / "backlog" / f"{ISSUE_ID}-corrigir_bug-body.md"
        # Arquivo real está em "doing" (foi movido); snapshot ainda aponta pro antigo.
        new_path = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        new_path.write_text("# Corrigir bug (movido)\n")

        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(old_path)},
        ])

        result = self._call()

        self.assertEqual(result, new_path)

    def test_rejeita_candidato_movido_reivindicado_por_outra_issue(self):
        """CT-146-06: candidato encontrado pelo nome completo, mas cujo
        body_path pertence a outra issue no snapshot → não aceito."""
        old_path = self.board_dir / "backlog" / f"{ISSUE_ID}-corrigir_bug-body.md"
        new_path = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        new_path.write_text("# Corrigir bug\n")

        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(old_path)},
            # Outra issue já reivindica exatamente esse arquivo encontrado.
            {"id": "77", "column": "doing", "body_path": str(new_path)},
        ])

        result = self._call()

        self.assertIsNone(
            result,
            "Candidato encontrado por nome não deve ser aceito se já "
            "pertence a outra issue via body_path",
        )


# ─────────────────────────────────────────────────────────────────────────────
# CT-146-03: Passo 2/3 — múltiplos candidatos com mesmo nome completo
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiplosCandidatosMesmoNome(_BaseFindIssueFilesTest):
    """CT-146-03: dois arquivos com o MESMO nome completo em colunas
    diferentes → None, sem escolher arbitrariamente."""

    def test_retorna_none_com_dois_candidatos_mesmo_nome(self):
        old_path = self.board_dir / "backlog" / f"{ISSUE_ID}-corrigir_bug-body.md"
        dup1 = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        dup2 = self._col("done") / f"{ISSUE_ID}-corrigir_bug-body.md"
        dup1.write_text("# Versão em doing\n")
        dup2.write_text("# Versão em done\n")

        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(old_path)},
        ])

        result = self._call()

        self.assertIsNone(result)

    def test_loga_warning_com_multiplos_candidatos(self):
        old_path = self.board_dir / "backlog" / f"{ISSUE_ID}-corrigir_bug-body.md"
        dup1 = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        dup2 = self._col("done") / f"{ISSUE_ID}-corrigir_bug-body.md"
        dup1.write_text("# Versão em doing\n")
        dup2.write_text("# Versão em done\n")

        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(old_path)},
        ])

        warning_calls = []
        original_warning = sync_module.log.warning

        def capture(module, msg, *args, **kwargs):
            warning_calls.append(msg)
            original_warning(module, msg, *args, **kwargs)

        with patch.object(sync_module.log, "warning", side_effect=capture):
            self._call()

        self.assertTrue(warning_calls, "Esperava log.warning para múltiplos candidatos")
        full_msg = " ".join(warning_calls)
        self.assertIn(ISSUE_ID, full_msg)


# ─────────────────────────────────────────────────────────────────────────────
# CT-146-04: Passo 2/3 — zero candidatos
# ─────────────────────────────────────────────────────────────────────────────

class TestZeroCandidatos(_BaseFindIssueFilesTest):
    """CT-146-04: nenhum arquivo com o nome buscado → None, sem exceção."""

    def test_retorna_none_sem_candidatos(self):
        old_path = self.board_dir / "backlog" / f"{ISSUE_ID}-corrigir_bug-body.md"
        # Nenhum arquivo real existe em disco.
        self._col("doing")

        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(old_path)},
        ])

        result = self._call()

        self.assertIsNone(result)

    def test_nao_lanca_excecao_sem_candidatos(self):
        old_path = self.board_dir / "backlog" / f"{ISSUE_ID}-corrigir_bug-body.md"
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(old_path)},
        ])

        try:
            self._call()
        except Exception as exc:
            self.fail(f"_find_issue_files não deveria lançar exceção: {exc}")

    def test_loga_warning_com_zero_candidatos(self):
        old_path = self.board_dir / "backlog" / f"{ISSUE_ID}-corrigir_bug-body.md"
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(old_path)},
        ])

        warning_calls = []
        original_warning = sync_module.log.warning

        def capture(module, msg, *args, **kwargs):
            warning_calls.append(msg)
            original_warning(module, msg, *args, **kwargs)

        with patch.object(sync_module.log, "warning", side_effect=capture):
            self._call()

        self.assertTrue(warning_calls, "Esperava log.warning para zero candidatos")


# ─────────────────────────────────────────────────────────────────────────────
# CT-146-05: Passo 4 — sem body_path registrado (issue legada)
# ─────────────────────────────────────────────────────────────────────────────

class TestFallbackLegadoSemBodyPath(_BaseFindIssueFilesTest):
    """CT-146-05: issue sem body_path no snapshot → fallback por prefixo
    numérico, aceito somente com exatamente 1 candidato."""

    def test_aceita_unico_candidato_por_prefixo_numerico(self):
        body = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        body.write_text("# Legado\n")
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing"},  # sem body_path
        ])

        result = self._call()

        self.assertEqual(result, body)

    def test_rejeita_colisao_de_prefixo_numerico_cenario_incidente_76(self):
        """Reprodução do padrão do incidente #76/#97: dois arquivos com o
        mesmo prefixo numérico em colunas diferentes, sem body_path
        registrado → None, em vez de escolher o primeiro do rglob."""
        dup1 = self._col("backlog") / f"{ISSUE_ID}-nome_a-body.md"
        dup2 = self._col("doing") / f"{ISSUE_ID}-nome_b-body.md"
        dup1.write_text("# Nome A\n")
        dup2.write_text("# Nome B\n")

        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing"},  # sem body_path
        ])

        result = self._call()

        self.assertIsNone(
            result,
            "Colisão de prefixo numérico sem body_path deve recusar (None), "
            "nunca escolher arbitrariamente o primeiro resultado do rglob",
        )

    def test_zero_candidatos_por_prefixo_numerico_retorna_none(self):
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing"},
        ])
        self._col("doing")

        result = self._call()

        self.assertIsNone(result)

    def test_issue_ausente_do_snapshot_usa_fallback_legado(self):
        """Issue completamente ausente do snapshot (snap.issue() retorna None)
        deve se comportar como o caso legado: fallback por prefixo numérico."""
        body = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        body.write_text("# Sem entrada no snapshot\n")
        _write_snapshot(self.board_dir, [])  # snapshot vazio

        result = self._call()

        self.assertEqual(result, body)


# ─────────────────────────────────────────────────────────────────────────────
# CT-146-07: Função é puramente local (sem chamada de rede/board)
# ─────────────────────────────────────────────────────────────────────────────

class TestSemChamadaDeRede(_BaseFindIssueFilesTest):
    """CT-146-07: nenhuma dependência de rede é exercida pela função —
    validado indiretamente por não haver mocks de board_obj/API em nenhum
    teste desta suíte e pela função aceitar apenas board_id/issue_id."""

    def test_funciona_totalmente_offline_sem_mocks_de_rede(self):
        body = self._col("doing") / f"{ISSUE_ID}-corrigir_bug-body.md"
        body.write_text("# Offline\n")
        _write_snapshot(self.board_dir, [
            {"id": ISSUE_ID, "column": "doing", "body_path": str(body)},
        ])

        # Nenhum patch de rede/board é necessário — só filesystem + snapshot.
        result = self._call()

        self.assertEqual(result, body)


# ─────────────────────────────────────────────────────────────────────────────
# CT-146-08: Board inexistente
# ─────────────────────────────────────────────────────────────────────────────

class TestBoardInexistente(_BaseFindIssueFilesTest):
    """Board sem diretório criado ainda → None, sem exceção (edge case não
    listado explicitamente na issue, mas coberto pelo comportamento atual)."""

    def test_board_sem_diretorio_retorna_none(self):
        with patch.object(sync_module, "BOARDS_DIR", self.tmp_path), \
             patch("src.core.snapshot.BOARDS_DIR", self.tmp_path):
            result = _find_issue_files("board_que_nao_existe", ISSUE_ID)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
