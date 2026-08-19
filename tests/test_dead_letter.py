"""
Casos de Teste — Persistir dead-letter e registrar evidência acionável ao
isolar item da fila

Contexto: a task predecessora #144 (mergeada em `epic`, PR #157) introduziu
`classify_error`, `ChangeItem.attempts` e a remoção do item da fila ativa em
`apply_changes` (`src/core/sync.py`) quando a classificação é "definitivo" ou
quando as tentativas transitórias se esgotam — mas sem persistir esse item em
nenhum lugar além do log. Esta é a etapa de Casos de Teste, anterior à
implementação: nenhuma das peças abaixo existe ainda no repositório
(`src/core/dead_letter.py`, `DeadLetterQueue`, `DeadLetterEntry`,
`sanitize_reason`, a integração em `apply_changes`, as entradas em
`PROTECTED_PATHS`/`context_generator.py`). Os testes são escritos test-first,
seguindo o mesmo padrão já usado nas issues #143/#144: falham agora por
ImportError/AttributeError/asserção e devem passar após a implementação.

Mapeamento por critério de aceite (AC) da issue:
  - AC1 (CT01-CT04): add() gera exatamente uma entrada com todos os campos.
  - AC2 (CT05-CT06): idempotência por board+id(/identifier)+event.
  - AC3 (CT07-CT08): sobrevive a reinício (nova instância / novo processo).
  - AC4 (CT09-CT13): sanitize_reason mascara PROTECTED_PATHS e tokens.
  - AC5 (CT14-CT16): log de isolamento contém todos os campos nomeados.
  - AC6 (CT17-CT18): .pipe/deadLetter.json em PROTECTED_PATHS + guard.
  - AC7 (CT19): CONTEXT.md gerado lista .pipe/deadLetter.json.
  - AC8 (CT20-CT23): integração em apply_changes (ambos os ramos) sem
    regressão nos testes existentes de sync/config.

Estratégia: diretório temporário simulando .pipe/, sem I/O real de rede.
"""

import json
import sys
import unittest
from dataclasses import fields as dataclass_fields, is_dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Importações condicionais: existem apenas após a implementação desta issue.
try:
    from src.core import dead_letter as _dead_letter_module
except ImportError:
    _dead_letter_module = None

DeadLetterQueue = getattr(_dead_letter_module, "DeadLetterQueue", None)
DeadLetterEntry = getattr(_dead_letter_module, "DeadLetterEntry", None)
sanitize_reason = getattr(_dead_letter_module, "sanitize_reason", None)

BOARD_ID = "task"
ISSUE_ID = "42"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _entry_kwargs(**overrides) -> dict:
    """kwargs mínimos válidos para construir um DeadLetterEntry de teste."""
    base = dict(
        uuid="11111111-1111-1111-1111-111111111111",
        board=BOARD_ID,
        id=ISSUE_ID,
        identifier=None,
        event="change-up",
        category="definitivo",
        reason="Could not resolve to an issue or pull request",
        attempts=1,
        isolated_at="2026-08-05T12:00:00Z",
        next_step="item não será retentado; revisar manualmente e, se aplicável, recriar a entrada",
    )
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# AC1 — add() gera entrada completa
# ══════════════════════════════════════════════════════════════════════════════

class TestAdicionarEntrada(unittest.TestCase):
    """CT01-CT04: add() persiste uma entrada com todos os campos do item 1."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / ".pipe").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _file(self) -> Path:
        return self.cwd / ".pipe" / "deadLetter.json"

    def test_dead_letter_queue_importavel(self):
        self.assertIsNotNone(
            DeadLetterQueue, "DeadLetterQueue deve ser importável de src.core.dead_letter"
        )

    def test_dead_letter_entry_e_dataclass(self):
        self.assertIsNotNone(
            DeadLetterEntry, "DeadLetterEntry deve ser importável de src.core.dead_letter"
        )
        self.assertTrue(is_dataclass(DeadLetterEntry), "DeadLetterEntry deve ser dataclass")

    @unittest.skipIf(DeadLetterEntry is None, "DeadLetterEntry não implementada ainda")
    def test_dead_letter_entry_tem_todos_os_campos(self):
        campos_esperados = {
            "uuid", "board", "id", "identifier", "event", "category",
            "reason", "attempts", "isolated_at", "next_step",
        }
        campos_reais = {f.name for f in dataclass_fields(DeadLetterEntry)}
        faltando = campos_esperados - campos_reais
        self.assertEqual(faltando, set(), f"Campos ausentes em DeadLetterEntry: {faltando}")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_add_cria_arquivo_deadletter_json(self):
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**_entry_kwargs()))
        self.assertTrue(dl_file.exists(), ".pipe/deadLetter.json não foi criado por add()")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_add_gera_exatamente_uma_entrada(self):
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**_entry_kwargs()))
            entries = q.list()
        self.assertEqual(len(entries), 1)

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_add_persiste_todos_os_campos(self):
        dl_file = self._file()
        kwargs = _entry_kwargs()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**kwargs))
            entry = q.list()[0]
        for key, value in kwargs.items():
            self.assertEqual(
                getattr(entry, key), value,
                f"Campo '{key}' não persistido corretamente"
            )

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_arquivo_e_json_valido_formatado(self):
        """Segue o padrão de change_queue.py: json.dumps(..., indent=2, ensure_ascii=False)."""
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**_entry_kwargs(reason="mensagem com acentuação é")))
        raw = dl_file.read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertIsInstance(data, list)
        # ensure_ascii=False: caracteres acentuados não devem ser escapados
        self.assertIn("é", raw)


# ══════════════════════════════════════════════════════════════════════════════
# AC2 — Idempotência por alvo (board + id/identifier + event)
# ══════════════════════════════════════════════════════════════════════════════

class TestIdempotencia(unittest.TestCase):
    """CT05-CT06: mesmo alvo isolado duas vezes gera uma entrada atualizada."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / ".pipe").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _file(self) -> Path:
        return self.cwd / ".pipe" / "deadLetter.json"

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_mesmo_board_id_event_nao_duplica(self):
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**_entry_kwargs(attempts=1, reason="primeira falha")))
            q.add(DeadLetterEntry(
                **_entry_kwargs(
                    uuid="22222222-2222-2222-2222-222222222222",
                    attempts=3,
                    reason="segunda falha",
                )
            ))
            entries = q.list()
        self.assertEqual(len(entries), 1, "Reprocessamento do mesmo alvo duplicou a entrada")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_reprocessamento_atualiza_motivo_e_tentativas(self):
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**_entry_kwargs(attempts=1, reason="primeira falha")))
            q.add(DeadLetterEntry(
                **_entry_kwargs(
                    uuid="22222222-2222-2222-2222-222222222222",
                    attempts=3,
                    reason="segunda falha",
                )
            ))
            entry = q.list()[0]
        self.assertEqual(entry.attempts, 3)
        self.assertEqual(entry.reason, "segunda falha")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_identifier_usado_quando_id_e_none(self):
        """Deduplicação por identifier quando id é None (issue ainda sem id no board)."""
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**_entry_kwargs(
                id=None, identifier="minha-tarefa-body.md", event="create-up",
            )))
            q.add(DeadLetterEntry(**_entry_kwargs(
                uuid="33333333-3333-3333-3333-333333333333",
                id=None, identifier="minha-tarefa-body.md", event="create-up",
                attempts=5,
            )))
            entries = q.list()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].attempts, 5)

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_alvos_diferentes_nao_colidem(self):
        """board+id+event diferentes devem gerar entradas distintas."""
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**_entry_kwargs(id="42", event="change-up")))
            q.add(DeadLetterEntry(**_entry_kwargs(
                uuid="44444444-4444-4444-4444-444444444444",
                id="43", event="change-up",
            )))
            q.add(DeadLetterEntry(**_entry_kwargs(
                uuid="55555555-5555-5555-5555-555555555555",
                id="42", event="delete-up",
            )))
            entries = q.list()
        self.assertEqual(len(entries), 3)


# ══════════════════════════════════════════════════════════════════════════════
# AC3 — Sobrevivência a reinício
# ══════════════════════════════════════════════════════════════════════════════

class TestSobrevivenciaAReinicio(unittest.TestCase):
    """CT07-CT08: entrada persiste entre instâncias distintas de DeadLetterQueue."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / ".pipe").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _file(self) -> Path:
        return self.cwd / ".pipe" / "deadLetter.json"

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_nova_instancia_le_entrada_do_disco(self):
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q1 = DeadLetterQueue()
            q1.add(DeadLetterEntry(**_entry_kwargs()))
            # "Reinício": nova instância, sem estado em memória compartilhado.
            q2 = DeadLetterQueue()
            entries = q2.list()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].id, ISSUE_ID)

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_list_vazio_quando_arquivo_nao_existe(self):
        dl_file = self._file()
        self.assertFalse(dl_file.exists())
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            entries = DeadLetterQueue().list()
        self.assertEqual(entries, [])

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_remove_por_uuid(self):
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            entry = DeadLetterEntry(**_entry_kwargs())
            q.add(entry)
            removed = q.remove(entry.uuid)
            entries = q.list()
        self.assertTrue(removed)
        self.assertEqual(entries, [])

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_remove_uuid_inexistente_retorna_false(self):
        dl_file = self._file()
        with patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            q = DeadLetterQueue()
            q.add(DeadLetterEntry(**_entry_kwargs()))
            removed = q.remove("uuid-que-nao-existe")
        self.assertFalse(removed)


# ══════════════════════════════════════════════════════════════════════════════
# AC4 — sanitize_reason
# ══════════════════════════════════════════════════════════════════════════════

class TestSanitizeReason(unittest.TestCase):
    """CT09-CT13: mascara caminhos protegidos e padrões de token/credencial."""

    def test_sanitize_reason_importavel(self):
        self.assertIsNotNone(
            sanitize_reason, "sanitize_reason deve ser importável (dead_letter.py ou log.py)"
        )
        self.assertTrue(callable(sanitize_reason))

    @unittest.skipIf(sanitize_reason is None, "sanitize_reason não implementada ainda")
    def test_mascara_caminho_protegido_snapshot(self):
        msg = "Falha ao ler .pipe/boards/task/snapshot.json: permissão negada"
        out = sanitize_reason(msg)
        self.assertNotIn("snapshot.json", out)
        self.assertIn("<arquivo interno>", out)
        # Restante da mensagem permanece legível
        self.assertIn("permissão negada", out)

    @unittest.skipIf(sanitize_reason is None, "sanitize_reason não implementada ainda")
    def test_mascara_caminho_protegido_changequeue(self):
        msg = "Corrupção em .pipe/changeQueue.json detectada"
        out = sanitize_reason(msg)
        self.assertNotIn("changeQueue.json", out)
        self.assertIn("<arquivo interno>", out)

    @unittest.skipIf(sanitize_reason is None, "sanitize_reason não implementada ainda")
    def test_mascara_token_github_ghp(self):
        msg = "Autenticação falhou com token ghp_1234567890abcdefABCDEF1234567890abcd"
        out = sanitize_reason(msg)
        self.assertNotIn("ghp_1234567890abcdefABCDEF1234567890abcd", out)
        self.assertIn("***", out)
        self.assertIn("Autenticação falhou", out)

    @unittest.skipIf(sanitize_reason is None, "sanitize_reason não implementada ainda")
    def test_mascara_token_github_gho(self):
        msg = "erro com token gho_abcdefghijklmnopqrstuvwxyz0123456789AB"
        out = sanitize_reason(msg)
        self.assertNotIn("gho_abcdefghijklmnopqrstuvwxyz0123456789AB", out)
        self.assertIn("***", out)

    @unittest.skipIf(sanitize_reason is None, "sanitize_reason não implementada ainda")
    def test_mascara_header_authorization_bearer(self):
        msg = "Requisição rejeitada: Authorization: Bearer abc123def456ghi789"
        out = sanitize_reason(msg)
        self.assertNotIn("abc123def456ghi789", out)

    @unittest.skipIf(sanitize_reason is None, "sanitize_reason não implementada ainda")
    def test_preserva_mensagem_sem_dados_sensiveis(self):
        msg = "Network timeout: conexão recusada"
        out = sanitize_reason(msg)
        self.assertEqual(out, msg)

    @unittest.skipIf(sanitize_reason is None, "sanitize_reason não implementada ainda")
    def test_mascara_multiplos_padroes_na_mesma_mensagem(self):
        msg = (
            "Falha ao processar .pipe/boards/task/snapshot.json com token "
            "ghp_1234567890abcdefABCDEF1234567890abcd"
        )
        out = sanitize_reason(msg)
        self.assertNotIn("snapshot.json", out)
        self.assertNotIn("ghp_1234567890abcdefABCDEF1234567890abcd", out)

    @unittest.skipIf(sanitize_reason is None, "sanitize_reason não implementada ainda")
    def test_retorna_string(self):
        out = sanitize_reason("mensagem qualquer")
        self.assertIsInstance(out, str)


# ══════════════════════════════════════════════════════════════════════════════
# AC5 — Log de isolamento com campos nomeados
# ══════════════════════════════════════════════════════════════════════════════

class TestLogDeIsolamento(unittest.TestCase):
    """CT14-CT16: log.warning/error emitido com todos os campos nomeados."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / ".pipe").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _run_apply_changes_definitivo(self, dl_file, log_mock):
        """Helper: monta fila com 1 item que falha com erro definitivo."""
        from src.core.board import ChangeItem
        from src.core.change_queue import ChangeQueue
        from src.core import sync as sync_module

        queue = MagicMock(spec=ChangeQueue)
        item = ChangeItem.of(
            "change-up", id=ISSUE_ID, board=BOARD_ID,
        )
        item.uuid = "aaaa-uuid"
        calls = {"n": 0}

        def fake_getNext():
            if calls["n"] == 0:
                calls["n"] += 1
                return item
            return None

        queue.getNext.side_effect = fake_getNext

        board_obj = MagicMock()

        with patch.object(sync_module, "_apply_change_up", side_effect=Exception(
            "Could not resolve to an issue or pull request"
        )), patch.object(sync_module, "log", log_mock), \
             patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            sync_module.apply_changes(board_obj, queue, config={})

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_log_contem_campos_nomeados_para_definitivo(self):
        dl_file = self.cwd / ".pipe" / "deadLetter.json"
        log_mock = MagicMock()
        self._run_apply_changes_definitivo(dl_file, log_mock)

        self.assertTrue(
            log_mock.warning.called or log_mock.error.called,
            "Nenhuma chamada de log.warning/log.error emitida no isolamento",
        )
        _, kwargs = (
            log_mock.warning.call_args if log_mock.warning.called else log_mock.error.call_args
        )
        for campo in ("board_id", "issue_id", "event", "reason", "attempts", "category", "next_step"):
            self.assertIn(campo, kwargs, f"Campo '{campo}' ausente no log de isolamento: {kwargs}")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_log_next_step_definitivo(self):
        dl_file = self.cwd / ".pipe" / "deadLetter.json"
        log_mock = MagicMock()
        self._run_apply_changes_definitivo(dl_file, log_mock)
        _, kwargs = (
            log_mock.warning.call_args if log_mock.warning.called else log_mock.error.call_args
        )
        self.assertIn("revisar manualmente", kwargs.get("next_step", ""))

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_log_category_definitivo(self):
        dl_file = self.cwd / ".pipe" / "deadLetter.json"
        log_mock = MagicMock()
        self._run_apply_changes_definitivo(dl_file, log_mock)
        _, kwargs = (
            log_mock.warning.call_args if log_mock.warning.called else log_mock.error.call_args
        )
        self.assertEqual(kwargs.get("category"), "definitivo")


# ══════════════════════════════════════════════════════════════════════════════
# AC6 — PROTECTED_PATHS
# ══════════════════════════════════════════════════════════════════════════════

class TestProtectedPaths(unittest.TestCase):
    """CT17-CT18: .pipe/deadLetter.json listado em PROTECTED_PATHS e bloqueado
    pelo guard existente de build_prompt."""

    def test_deadletter_json_em_protected_paths(self):
        import src.core.agent as agent_module
        self.assertIn(
            ".pipe/deadLetter.json", agent_module.PROTECTED_PATHS,
            ".pipe/deadLetter.json deve estar em PROTECTED_PATHS (src/core/agent.py)"
        )

    def test_build_prompt_guard_levanta_para_deadletter_json(self):
        import src.core.agent as agent_module
        assert_no_protected = getattr(agent_module, "_assert_no_protected", None)
        if assert_no_protected is None:
            self.skipTest("_assert_no_protected não implementada ainda")
        prompt = "Consulte .pipe/deadLetter.json para ver os itens isolados."
        with self.assertRaises(ValueError):
            assert_no_protected(prompt)


# ══════════════════════════════════════════════════════════════════════════════
# AC7 — CONTEXT.md gerado
# ══════════════════════════════════════════════════════════════════════════════

class TestContextGeneratorListaDeadLetter(unittest.TestCase):
    """CT19: .pipe/deadLetter.json aparece no CONTEXT.md gerado."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / ".pipe").mkdir()
        (self.cwd / "pipe.yml").write_text("# pipe.yml\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lista_deadletter_json(self):
        from src.core.context_generator import generate_context

        ctx_file = self.cwd / ".pipe" / "CONTEXT.md"
        agent_file = self.cwd / ".kiro" / "agents" / "pipe_context.json"
        with patch("src.core.context_generator.PIPE_FILE", self.cwd / "pipe.yml"), \
             patch("src.core.context_generator.CONTEXT_FILE", ctx_file), \
             patch("src.core.context_generator.AGENT_FILE", agent_file, create=True):
            generate_context({
                "git": {"repo": {"main": "x"}, "flow": {"base": "main"}},
                "boards": {"platform": "github"},
            })
        content = ctx_file.read_text()
        self.assertIn(".pipe/deadLetter.json", content)


# ══════════════════════════════════════════════════════════════════════════════
# AC8 — Integração em apply_changes (ambos os ramos) sem regressão
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegracaoApplyChanges(unittest.TestCase):
    """CT20-CT23: DeadLetterQueue().add() chamado nos dois ramos que removem
    o item da fila ativa (definitivo e transitório esgotado)."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / ".pipe").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, exc, config=None):
        from src.core.board import ChangeItem
        from src.core.change_queue import ChangeQueue
        from src.core import sync as sync_module

        dl_file = self.cwd / ".pipe" / "deadLetter.json"
        queue = MagicMock(spec=ChangeQueue)
        item = ChangeItem.of("change-up", id=ISSUE_ID, board=BOARD_ID)
        item.uuid = "bbbb-uuid"
        calls = {"n": 0}

        def fake_getNext():
            if calls["n"] == 0:
                calls["n"] += 1
                return item
            return None

        queue.getNext.side_effect = fake_getNext
        board_obj = MagicMock()

        with patch.object(sync_module, "_apply_change_up", side_effect=exc), \
             patch.object(_dead_letter_module, "DEAD_LETTER_FILE", dl_file):
            sync_module.apply_changes(board_obj, queue, config=config or {})

        return dl_file, queue

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_erro_definitivo_persiste_em_dead_letter(self):
        dl_file, queue = self._run(Exception("Could not resolve to an issue or pull request"))
        self.assertTrue(dl_file.exists())
        entries = json.loads(dl_file.read_text())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["category"], "definitivo")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_erro_definitivo_ainda_remove_da_fila_ativa(self):
        dl_file, queue = self._run(Exception("Could not resolve to an issue or pull request"))
        queue.remove.assert_called_with("bbbb-uuid")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_transitorio_esgotado_persiste_em_dead_letter(self):
        dl_file, queue = self._run(
            Exception("Network timeout"), config={"sync": {"max_attempts": 1}}
        )
        self.assertTrue(dl_file.exists())
        entries = json.loads(dl_file.read_text())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["category"], "transitorio_esgotado")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_transitorio_esgotado_ainda_remove_da_fila_ativa(self):
        dl_file, queue = self._run(
            Exception("Network timeout"), config={"sync": {"max_attempts": 1}}
        )
        queue.remove.assert_called_with("bbbb-uuid")

    @unittest.skipIf(DeadLetterQueue is None, "DeadLetterQueue não implementada ainda")
    def test_transitorio_nao_esgotado_nao_persiste_em_dead_letter(self):
        """Enquanto não esgota max_attempts, o item é reenfileirado — sem dead-letter."""
        dl_file, queue = self._run(
            Exception("Network timeout"), config={"sync": {"max_attempts": 5}}
        )
        self.assertFalse(dl_file.exists(), "Item ainda transitório não deveria ir para dead-letter")
        queue.remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
