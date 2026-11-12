import re

import pytest

from src.core.version import VERSION
from tests import _editorial_helpers as e

NOTA_BOA = (
    "versao: 9.9.9\n"
    "data: 2026-01-01\n"
    "destaques: Agora a esteira avisa na própria issue quando um anexo foi recusado, "
    "então você descobre o motivo sem abrir log nenhum.\n"
    "acao: nenhuma"
)


@pytest.fixture(scope="module")
def processo():
    assert e.COMUNICACAO.exists(), f"CA-6: {e.COMUNICACAO} ausente"
    return e.ler(e.COMUNICACAO)


@pytest.fixture(scope="module")
def notas():
    assert e.NOVIDADES.exists(), f"CA-6: {e.NOVIDADES} ausente"
    return e.parse_blocos(e.ler(e.NOVIDADES), "versao")


def test_processo_documenta_campos(processo):
    for campo in e.CAMPOS_NOTA:
        assert re.search(rf"^{campo}:", processo, re.MULTILINE), f"RF-09: campo '{campo}' ausente"
    assert re.search(r"NOVIDADES\.md.{0,80}canal único|canal único.{0,80}NOVIDADES\.md",
                     processo, re.IGNORECASE | re.DOTALL), "RF-09: canal único não declarado"
    assert re.search(r"linguagem\s+de\s+benefício", processo, re.IGNORECASE)
    assert re.search(r"nunca\s+(é\s+)?(uma\s+)?lista\s+tecnicista", processo, re.IGNORECASE), "RN-07 ausente"


def test_publicacao_mesmo_momento_declarada(processo):
    assert re.search(r"mesmo\s+pull\s+request", processo, re.IGNORECASE), (
        "RF-10: o processo não declara a nota no mesmo pull request da mudança"
    )
    assert re.search(r"mesmo\s+momento", processo, re.IGNORECASE)


def test_notas_reais_tem_quatro_campos(notas):
    assert notas, "CA-6: NOVIDADES.md sem nenhuma nota"
    for nota in notas:
        for campo in e.CAMPOS_NOTA:
            assert nota.get(campo), f"CA-6: nota {nota.get('versao')} sem '{campo}'"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", nota["data"]), nota["data"]


def test_validador_estilo_nota(notas):
    assert e.avaliar_gate_revisao(NOTA_BOA, tipo="nota_versao") == []
    tecnicista = (
        "versao: 9.9.9\ndata: 2026-01-01\ndestaques:\n"
        "- Corrigido: NullPointerException em sync.apply_changes\n"
        "- Refatorado: _apply_create_up recebe config\nacao: nenhuma"
    )
    motivos = e.avaliar_gate_revisao(tecnicista, tipo="nota_versao")
    assert any("registro editorial inadequado" in m and "lista tecnicista" in m for m in motivos)
    longa = NOTA_BOA.replace("acao: nenhuma", "acao: " + "texto " * 170)
    motivos = e.avaliar_gate_revisao(longa, tipo="nota_versao")
    assert any("longa demais" in m for m in motivos), motivos
    for nota in notas:
        assert e.avaliar_gate_revisao(e.texto_nota(nota), tipo="nota_versao") == [], nota["versao"]


def test_validador_rejeita_artefato_interno(notas):
    for citacao in ("resolve a #313", "fecha o épico de sincronização", "conforme história #12"):
        texto = NOTA_BOA.replace("acao: nenhuma", f"acao: {citacao}")
        motivos = e.avaliar_gate_revisao(texto, tipo="nota_versao")
        assert any(m.startswith("artefato interno citado") for m in motivos), (citacao, motivos)
    assert not [m for m in e.avaliar_gate_revisao(NOTA_BOA, tipo="nota_versao")
                if m.startswith("artefato interno")]
    for nota in notas:
        assert not e.artefatos_internos(e.texto_nota(nota)), nota["versao"]


def test_versao_corrente_tem_nota(notas):
    assert VERSION in {n["versao"] for n in notas}, (
        f"RNF-04: versão corrente {VERSION} sem nota em NOVIDADES.md"
    )


def test_auditoria_mudancas_sintetica():
    mudancas = [
        {"versao": "1.0.0", "data": "2026-01-01", "elegivel": True},
        {"versao": "1.1.0", "data": "2026-01-02", "elegivel": True},
        {"versao": "1.1.1", "data": "2026-01-03", "elegivel": False},
        {"versao": "1.2.0", "data": "2026-01-04", "elegivel": True},
    ]
    notas = [
        {"versao": "1.1.0", "data": "2026-01-02"},
        {"versao": "1.2.0", "data": "2026-01-05"},
    ]
    relatos = e.auditar_mudancas_elegiveis(mudancas, notas)
    assert len(relatos) == 2
    assert "1.0.0" in relatos[0] and "sem nota correspondente" in relatos[0]
    assert "1.2.0" in relatos[1] and "fora do mesmo momento" in relatos[1]
