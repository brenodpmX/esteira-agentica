"""Validação de forma de `registro.retencao_dias` (issue #307) — CT-11b.

Segue o padrão da casa (`validate_retry`/`validate_agent_circuit_break`): bloco
opcional de raiz, `ConfigError` citando o caminho do campo, `bool` rejeitado
ANTES de `int`. A validação ocorre na verificação de configuração, antes de
qualquer alteração de estado.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import validate_registro, ConfigError  # noqa: E402


# ── Sub-casos aceitos ─────────────────────────────────────────────────────────

def test_ausente_aceito():
    # Ausente ⇒ política de expurgo inativa (estado seguro por padrão).
    validate_registro({})  # não levanta


def test_inteiro_positivo_aceito():
    validate_registro({"registro": {"retencao_dias": 7}})  # não levanta


# ── Sub-casos rejeitados (ConfigError citando o caminho) ──────────────────────

@pytest.mark.parametrize("valor", [0, -1, True, False, 7.5, "7"])
def test_valores_invalidos_rejeitados(valor):
    with pytest.raises(ConfigError) as exc:
        validate_registro({"registro": {"retencao_dias": valor}})
    assert "registro.retencao_dias" in str(exc.value)


def test_bool_rejeitado_antes_de_int():
    # True é instância de int em Python; deve ser rejeitado como inválido.
    with pytest.raises(ConfigError) as exc:
        validate_registro({"registro": {"retencao_dias": True}})
    assert "registro.retencao_dias" in str(exc.value)


def test_bloco_nao_mapa_rejeitado():
    with pytest.raises(ConfigError) as exc:
        validate_registro({"registro": [1, 2, 3]})
    assert "registro" in str(exc.value)


def test_campo_desconhecido_rejeitado():
    with pytest.raises(ConfigError) as exc:
        validate_registro({"registro": {"retencao_dias": 7, "foo": 1}})
    assert "registro.foo" in str(exc.value)


# ── Resolução do valor configurado ────────────────────────────────────────────

def test_resolve_retencao_dias():
    from src.core import execution_record as er
    assert er.resolve_retencao_dias({}) is None
    assert er.resolve_retencao_dias({"registro": {}}) is None
    assert er.resolve_retencao_dias({"registro": {"retencao_dias": 30}}) == 30
