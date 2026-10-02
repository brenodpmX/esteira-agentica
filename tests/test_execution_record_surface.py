"""Guarda de superfície do registro de execução (issue #307) — CT-14 + CT-16.

CT-14: a capacidade NÃO expõe nenhuma operação de exclusão manual de um registro
específico. O único caminho de remoção legítimo é o expurgo por retenção
(`purge_expired`), acionado pela lógica interna do motor (RN-11/RNF-10).

CT-16 (superfície): o armazenamento durável está em `PROTECTED_PATHS` e
`build_prompt` o rejeita se aparecer no prompt (mesmo padrão dos demais
`.pipe/*`).
"""

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import execution_record as er  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
# CT-14 — Ausência de superfície de exclusão manual de registro
# ══════════════════════════════════════════════════════════════════════════════

def test_ct14_sem_funcao_de_exclusao_manual():
    """Nenhuma função pública do módulo exclui/remove um registro específico.

    O único caminho de remoção é `purge_expired` (expurgo por retenção, lógica
    interna). Varredura estática dos símbolos públicos do módulo.
    """
    publicos = [
        name for name, obj in vars(er).items()
        if not name.startswith("_") and inspect.isfunction(obj)
        and obj.__module__ == er.__name__
    ]
    # Nenhum símbolo público sugere exclusão manual de um registro específico.
    proibidos = ("delete", "remove", "excluir", "apagar", "drop", "clear", "purge_one")
    for nome in publicos:
        baixo = nome.lower()
        for termo in proibidos:
            assert termo not in baixo, (
                f"símbolo público '{nome}' sugere exclusão manual de registro "
                f"(apenas purge_expired por retenção é permitido)"
            )
    # O expurgo por retenção existe e é a única remoção.
    assert hasattr(er, "purge_expired")


def test_ct14_purge_expired_so_remove_por_retencao():
    """`purge_expired` não remove um registro por id/seletor arbitrário — só por
    idade/retenção. A assinatura aceita apenas `retencao_dias` e `now`."""
    sig = inspect.signature(er.purge_expired)
    params = list(sig.parameters)
    assert params == ["retencao_dias", "now"]


# ══════════════════════════════════════════════════════════════════════════════
# CT-16 — Armazenamento durável protegido (superfície)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct16_store_em_protected_paths():
    from src.core.agent import PROTECTED_PATHS
    assert str(er.STORE_FILE) in PROTECTED_PATHS
    assert str(er.STORE_FILE) == ".pipe/executionRecords.json"


def test_ct16_build_prompt_rejeita_o_caminho():
    from src.core.agent import _assert_no_protected
    with pytest.raises(ValueError):
        _assert_no_protected("não leia .pipe/executionRecords.json")
