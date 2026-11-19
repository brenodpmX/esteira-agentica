import re

import pytest

from tests import _editorial_helpers as e


@pytest.fixture(scope="module")
def registro():
    assert e.BASELINE.exists(), f"CA-12: {e.BASELINE} ausente"
    texto = e.ler(e.BASELINE)
    return texto, e.parse_blocos(texto, "participantes_confirmados")


def _confirmados(blocos):
    return bool(blocos) and blocos[0].get("participantes_confirmados") == "sim"


def test_decisao_sem_participantes(registro):
    texto, blocos = registro
    assert blocos, "CA-12: campo 'participantes_confirmados' ausente"
    assert blocos[0]["participantes_confirmados"] in ("sim", "nao")
    if _confirmados(blocos):
        pytest.skip("ramo com participantes confirmados (ver test_registro_baseline_pos_teste)")
    assert blocos[0].get("decisao_continuidade") == "sem baseline disponível"
    assert re.search(r"entrega mínima", texto, re.IGNORECASE), "RN-11: entrega mínima não declarada"


def test_registro_baseline_pos_teste(registro):
    texto, blocos = registro
    if not _confirmados(blocos):
        pytest.skip("RN-11: sem participantes confirmados, o baseline não se aplica")
    dados = blocos[0]
    for campo in ("baseline_sucesso", "baseline_tempo_mediano",
                  "pos_teste_sucesso", "pos_teste_tempo_mediano", "decisao_continuidade"):
        assert dados.get(campo), f"RF-13: campo '{campo}' ausente"
    assert dados["decisao_continuidade"] in ("continuar", "interromper")
    assert re.search(r"4 de 5", texto), "RNF-01: regra de decisão ausente"
