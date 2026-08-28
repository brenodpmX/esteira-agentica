"""Testes de conformidade — eventos estruturados nunca expõem segredo, body
ou arquivo protegido.

Task #263 (story #246). Duas frentes:

1. `assert_no_sensitive_kwargs` (helper em `src/core/log.py`): rejeita, por
   NOME de chave (case-insensitive), kwargs sensíveis passados a um log
   estruturado. CT-001..CT-005.

2. Inspeção estática dos call sites dos eventos estruturados desta story
   (`rollout_evidence`, `participation_classified`, `participation_reconciled`,
   `participation_reconcile_failed`, `participation_removed_externally`,
   `dispatch_blocked_unconfirmed_intent`, `cross_board_link_blocked`) nos
   arquivos-fonte `src/__main__.py`, `src/core/board.py`, `src/core/sync.py`
   e `src/core/log.py`, confirmando que nenhuma chamada de log passa os campos
   proibidos (`body=`, `token=`, `ssh_key=`, `gh_token=`, `kiro_api_key=`).
   CT-006..CT-008.

A verificação estática é textual (substring/regex), seguindo o padrão de
simplicidade da base — não é necessário AST completo. `event_type` ainda não
implementado por outra task é PULADO, não falha o teste (a suíte só falha por
PRESENÇA de campo proibido, nunca por ausência de evento).

Referência: RN-B09 (último item) e critério de aceitação final da story #246.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.log import FORBIDDEN_LOG_KWARGS, assert_no_sensitive_kwargs

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Arquivos-fonte auditados (item 4 de "Como testar").
_SOURCE_FILES = [
    _REPO_ROOT / "src" / "__main__.py",
    _REPO_ROOT / "src" / "core" / "board.py",
    _REPO_ROOT / "src" / "core" / "sync.py",
    _REPO_ROOT / "src" / "core" / "log.py",
]

# Os sete event_type estruturados desta story / épico.
_EVENT_TYPES = [
    "rollout_evidence",
    "participation_classified",
    "participation_reconciled",
    "participation_reconcile_failed",
    "participation_removed_externally",
    "dispatch_blocked_unconfirmed_intent",
    "cross_board_link_blocked",
]

# Substrings de campo proibido dentro do trecho de chamada de log.
_FORBIDDEN_FIELD_SUBSTRINGS = ["body=", "token=", "ssh_key=", "gh_token=", "kiro_api_key="]

# Nomes das funções de log cuja chamada envolve um dos event_type.
_LOG_METHODS = ["log.info", "log.warning", "log.error"]


# --------------------------------------------------------------------------- #
# Helpers de inspeção estática (textual, sem AST completo).
# --------------------------------------------------------------------------- #

def _extract_log_call(source: str, event_pos: int) -> str:
    """Extrai a chamada de `log.info/warning/error(...)` que contém a ocorrência
    de `event_type` na posição `event_pos`.

    Localiza o início da chamada (a última ocorrência de um dos métodos de log
    antes de `event_pos`) e casa o parêntese de abertura com seu fechamento
    correspondente, retornando o texto da chamada completa. Retorna string
    vazia se não encontrar uma chamada de log envolvente.
    """
    start = -1
    for method in _LOG_METHODS:
        idx = source.rfind(method, 0, event_pos)
        if idx > start:
            start = idx
    if start == -1:
        return ""

    open_paren = source.find("(", start)
    if open_paren == -1 or open_paren > event_pos:
        return ""

    depth = 0
    i = open_paren
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                # O event_pos precisa estar dentro desta chamada.
                if open_paren < event_pos < i:
                    return source[start:i + 1]
                return ""
        i += 1
    return ""


def _find_event_log_calls(event_type: str):
    """Retorna lista de (arquivo, trecho_da_chamada) para todas as ocorrências
    do `event_type` nos arquivos-fonte auditados que estão dentro de uma
    chamada de log."""
    literal = f'event_type="{event_type}"'
    calls = []
    for path in _SOURCE_FILES:
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        for match in re.finditer(re.escape(literal), source):
            call = _extract_log_call(source, match.start())
            if call:
                calls.append((path.name, call))
    return calls


# --------------------------------------------------------------------------- #
# CT-001..CT-005 — assert_no_sensitive_kwargs
# --------------------------------------------------------------------------- #

class TestAssertNoSensitiveKwargs:
    def test_ct001_kwargs_neutros_nao_levantam(self):
        # CT-001: kwargs neutros retornam None sem exceção.
        assert assert_no_sensitive_kwargs({"issue_id": "1", "board_id": "task"}) is None

    def test_ct002_token_levanta_valueerror_mencionando_token(self):
        # CT-002: chave `token` levanta ValueError mencionando "token".
        with pytest.raises(ValueError) as exc:
            assert_no_sensitive_kwargs({"issue_id": "1", "token": "ghp_x"})
        assert "token" in str(exc.value)

    def test_ct003_case_insensitive(self):
        # CT-003: comparação de chaves é case-insensitive ("BODY").
        with pytest.raises(ValueError):
            assert_no_sensitive_kwargs({"BODY": "..."})

    @pytest.mark.parametrize("key", ["ssh_key", "gh_token", "kiro_api_key"])
    def test_ct004_demais_chaves_proibidas(self, key):
        # CT-004: cada chave proibida restante é detectada isoladamente.
        with pytest.raises(ValueError) as exc:
            assert_no_sensitive_kwargs({key: "valor"})
        assert key in str(exc.value)

    def test_ct005_reporta_todas_as_chaves_proibidas(self):
        # CT-005: reporta todas as chaves proibidas presentes, não só a primeira.
        with pytest.raises(ValueError) as exc:
            assert_no_sensitive_kwargs({"token": "x", "body": "y", "issue_id": "1"})
        msg = str(exc.value)
        assert "token" in msg
        assert "body" in msg

    def test_forbidden_set_conteudo(self):
        # Garante o conjunto exato especificado na task (segunda linha de defesa
        # contra alteração acidental do superconjunto conservador).
        assert FORBIDDEN_LOG_KWARGS == {"token", "ssh_key", "body", "gh_token", "kiro_api_key"}


# --------------------------------------------------------------------------- #
# CT-006/CT-007 — inspeção estática dos call sites
# --------------------------------------------------------------------------- #

class TestStaticInspection:
    def test_ct006_nenhum_campo_proibido_nas_chamadas_de_evento(self):
        # CT-006: para cada event_type existente, nenhuma substring de campo
        # proibido aparece no trecho da chamada de log.
        for event_type in _EVENT_TYPES:
            for filename, call in _find_event_log_calls(event_type):
                for forbidden in _FORBIDDEN_FIELD_SUBSTRINGS:
                    assert forbidden not in call, (
                        f"event_type={event_type!r} em {filename}: chamada de log "
                        f"contém campo proibido {forbidden!r}:\n{call}"
                    )

    def test_ct006_rollout_evidence_encontrado_e_validado(self):
        # CT-006: rollout_evidence já está implementado — deve ser encontrado
        # e validado positivamente (verdadeiro-positivo, não apenas pulo).
        calls = _find_event_log_calls("rollout_evidence")
        assert calls, "rollout_evidence deveria estar implementado e ser encontrado"
        for _filename, call in calls:
            for forbidden in _FORBIDDEN_FIELD_SUBSTRINGS:
                assert forbidden not in call

    def test_ct007_event_type_ausente_nao_falha(self):
        # CT-007: os event_type ainda não implementados não fazem o teste falhar
        # por ausência — a busca simplesmente retorna lista vazia (nada a validar).
        implemented = {et for et in _EVENT_TYPES if _find_event_log_calls(et)}
        # rollout_evidence está implementado; os demais podem ou não estar.
        # O contrato é: ausência => pula, sem asserção de presença obrigatória.
        for event_type in _EVENT_TYPES:
            if event_type not in implemented:
                # Não há trechos; a verificação de CT-006 é naturalmente pulada.
                assert _find_event_log_calls(event_type) == []


# --------------------------------------------------------------------------- #
# CT-008 — participation_classified: segunda linha de defesa textual
# --------------------------------------------------------------------------- #

class TestParticipationClassifiedDefenseInDepth:
    def test_ct008_evidence_nao_expoe_body_nem_labels_completo(self):
        # CT-008: quando participation_classified existir, o trecho de evidence=
        # (quando presente) não deve referenciar `.body` nem `labels=` (lista
        # completa de labels). Pulado sem falha enquanto o evento não existir.
        calls = _find_event_log_calls("participation_classified")
        if not calls:
            pytest.skip("participation_classified ainda não implementado — CT-008 pulado")
        for filename, call in calls:
            assert ".body" not in call, (
                f"participation_classified em {filename}: evidência referencia "
                f".body:\n{call}"
            )
            assert "labels=" not in call, (
                f"participation_classified em {filename}: chamada referencia "
                f"labels= (lista completa):\n{call}"
            )
