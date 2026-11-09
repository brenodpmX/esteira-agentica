import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import (DEFAULT_ALLOWED_FILE_TYPES, ConfigError,
                             _validate_boards, resolve_file_sync_policy,
                             validate_file_sync)


def _boards(file_sync=None):
    board = {"name": "Entrega", "columns": {"desenvolvimento": {"name": "Dev"}}}
    if file_sync is not None:
        board["file-sync"] = file_sync
    return {"platform": "github", "entrega": board}


def _config(file_sync=None):
    return {"boards": _boards(file_sync)}


def test_ct_a_file_sync_valido_aceito():
    validate_file_sync("entrega", {"file-sync": {
        "allowed-types": ["png", ".PDF"], "max-size": 1_000_000, "on-reject": "bloqueante",
    }})
    _validate_boards(_boards({"allowed-types": ["png"], "on-reject": "silencioso"}))


def test_ct_b_ausencia_e_valida():
    validate_file_sync("entrega", {})
    _validate_boards(_boards())
    validate_file_sync("entrega", {"file-sync": {}})


@pytest.mark.parametrize("file_sync, fragment", [
    ("png", "boards.entrega.file-sync"),
    (["png"], "boards.entrega.file-sync"),
    ({"allowed-types": "png"}, "boards.entrega.file-sync.allowed-types"),
    ({"allowed-types": []}, "boards.entrega.file-sync.allowed-types"),
    ({"allowed-types": [""]}, "boards.entrega.file-sync.allowed-types"),
    ({"allowed-types": [None]}, "boards.entrega.file-sync.allowed-types"),
    ({"allowed-types": [3]}, "boards.entrega.file-sync.allowed-types"),
    ({"max-size": 0}, "boards.entrega.file-sync.max-size"),
    ({"max-size": -1}, "boards.entrega.file-sync.max-size"),
    ({"max-size": "10MB"}, "boards.entrega.file-sync.max-size"),
    ({"max-size": True}, "boards.entrega.file-sync.max-size"),
    ({"max-size": 1.5}, "boards.entrega.file-sync.max-size"),
    ({"on-reject": "avisar"}, "boards.entrega.file-sync.on-reject"),
    ({"on-reject": None}, "boards.entrega.file-sync.on-reject"),
])
def test_ct_c_forma_invalida_rejeitada(file_sync, fragment):
    with pytest.raises(ConfigError, match=fragment.replace(".", r"\.")):
        _validate_boards(_boards(file_sync))


def test_ct10_sem_lista_declarada_usa_default_do_motor():
    policy = resolve_file_sync_policy(_config(), "entrega")
    assert policy.allowed_types == frozenset(
        ["png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "md", "csv", "json", "log", "zip"])
    assert policy.allowed_types == frozenset(DEFAULT_ALLOWED_FILE_TYPES)


def test_ct11_lista_declarada_substitui_default():
    policy = resolve_file_sync_policy(_config({"allowed-types": ["png", "MP4", ".txt"]}), "entrega")
    assert policy.allowed_types == frozenset(["png", "mp4", "txt"])
    assert "zip" not in policy.allowed_types


def test_ct12_sem_limite_declarado():
    assert resolve_file_sync_policy(_config(), "entrega").max_size is None


def test_ct13_limite_declarado():
    assert resolve_file_sync_policy(_config({"max-size": 1000}), "entrega").max_size == 1000


def test_ct15_ausencia_equivale_a_aviso_explicito():
    implicit = resolve_file_sync_policy(_config(), "entrega")
    explicit = resolve_file_sync_policy(_config({"on-reject": "aviso"}), "entrega")
    assert implicit.on_reject == explicit.on_reject == "aviso"


def test_board_inexistente_ou_config_vazia_usa_defaults():
    for config in ({}, None, _config()):
        policy = resolve_file_sync_policy(config, "outro")
        assert policy.on_reject == "aviso"
        assert policy.max_size is None
        assert policy.allowed_types == frozenset(DEFAULT_ALLOWED_FILE_TYPES)
