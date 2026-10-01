"""CT-12 — Validação de FORMA do mapa `boards.<board>.column-migrations` (#305).

Padrão de `validate_retry`: ConfigError citando o caminho da chave e a entrada
que falhou; ausência da chave é válida; validação semântica NÃO é feita aqui.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import validate_column_migrations, ConfigError, _validate_boards


def _board(columns=("backlog", "done"), migrations=None):
    cfg = {"name": "Entrega", "columns": {c: {"name": c} for c in columns}}
    if migrations is not None:
        cfg["column-migrations"] = migrations
    return cfg


# ── CT-12a — Mapa válido é aceito ─────────────────────────────────────────────

def test_ct12a_valid_map_accepted():
    validate_column_migrations("entrega", _board(migrations={"revisao": "done"}))
    # não levanta — forma não exige que as colunas existam (isso é semântica)


def test_ct12a_valid_map_multiple_entries():
    validate_column_migrations(
        "entrega", _board(migrations={"revisao": "done", "espera": "backlog"}))


# ── CT-12b — Ausência do mapa é válida ────────────────────────────────────────

def test_ct12b_absent_map_valid():
    validate_column_migrations("entrega", _board())  # sem a chave: ok


def test_ct12b_absent_map_in_full_boards_validation():
    boards = {"platform": "github", "entrega": _board()}
    _validate_boards(boards)  # não levanta


# ── CT-12c — Tipos/valores inválidos rejeitados com ConfigError citando caminho

@pytest.mark.parametrize("migrations", [
    ["revisao", "done"],          # lista, não mapa
    "revisao:done",               # string, não mapa
    {"revisao": "   "},           # valor vazio após strip
    {"revisao": None},            # valor nulo
    {"revisao": 10},              # valor não-string
    {"  ": "done"},               # chave vazia após strip
    {"revisao": True},            # bool não é string
])
def test_ct12c_invalid_rejected(migrations):
    with pytest.raises(ConfigError) as exc:
        validate_column_migrations("entrega", _board(migrations=migrations))
    msg = str(exc.value)
    assert "boards.entrega.column-migrations" in msg


def test_ct12c_invalid_cites_entry():
    """A mensagem cita a entrada específica que falhou."""
    with pytest.raises(ConfigError) as exc:
        validate_column_migrations("entrega", _board(migrations={"revisao": None}))
    assert "revisao" in str(exc.value)


def test_ct12c_invalid_propagates_through_validate_boards():
    boards = {"platform": "github",
              "entrega": _board(migrations={"revisao": 10})}
    with pytest.raises(ConfigError) as exc:
        _validate_boards(boards)
    assert "boards.entrega.column-migrations" in str(exc.value)
