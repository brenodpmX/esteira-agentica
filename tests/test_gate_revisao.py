import re

import pytest

from tests import _editorial_helpers as e

CRITERIOS = (
    r"fronteira público/interno",
    r"artefatos? internos?",
    r"retorno financeiro",
    r"instruções corretas e seguras",
    r"registro editorial",
)


@pytest.fixture(scope="module")
def contrato():
    assert e.GATE.exists(), f"CA-11: {e.GATE} ausente"
    return e.ler(e.GATE)


def test_contrato_tem_quatro_campos(contrato):
    for campo in ("entrada", "criterios", "saida_aprovado", "saida_reprovado"):
        assert re.search(rf"^{campo}:", contrato, re.MULTILINE), f"RF-12: campo '{campo}' ausente"
    for criterio in CRITERIOS:
        assert re.search(criterio, contrato, re.IGNORECASE), f"RF-12: critério ausente: {criterio}"


def test_reprova_artefato_interno():
    motivos = e.avaliar_gate_revisao("Esta versão entrega a #313 do board.")
    assert motivos == ["artefato interno citado: '#313'"]
    motivos = e.avaliar_gate_revisao("Fechamos o épico de sincronização.")
    assert any("épico" in m for m in motivos), motivos


def test_reprova_registro_tecnicista():
    motivos = e.avaliar_gate_revisao("- Corrigido: KeyError em config.py", tipo="nota_versao")
    assert motivos == ["registro editorial inadequado: lista tecnicista (1 itens de lista)"]
    motivos = e.avaliar_gate_revisao("a" * 801, tipo="nota_versao")
    assert motivos == [
        "registro editorial inadequado: nota longa demais (801 > 800 caracteres)"
    ]
    assert e.avaliar_gate_revisao("- item de lista", tipo="documento") == []


@pytest.mark.parametrize("texto", [
    "Com a esteira você economiza 40% em suporte.",
    "Retorno garantido no primeiro mês.",
    "Reduza custos em 30 mil por trimestre.",
])
def test_reprova_promessa_financeira(texto):
    motivos = e.avaliar_gate_revisao(texto)
    assert any(m.startswith("promessa de retorno financeiro") for m in motivos), motivos


def test_aprova_capacidade_sem_promessa():
    texto = "A esteira executa agentes de IA sobre as issues do board, coluna a coluna."
    assert e.avaliar_gate_revisao(texto) == []


def test_reprova_mecanica_interna_e_dado_sensivel():
    motivos = e.avaliar_gate_revisao("## Loop Principal\n\ntoken ghp_" + "a" * 30)
    assert any(m.startswith("fronteira público/interno") for m in motivos), motivos
    assert any(m.startswith("instrução insegura") for m in motivos), motivos


def test_aprova_conteudo_conforme():
    assert e.avaliar_gate_revisao(e.ler(e.README)) == []
    assert e.avaliar_gate_revisao(e.ler(e.CATALOGO)) == []
    for nota in e.parse_blocos(e.ler(e.NOVIDADES), "versao"):
        assert e.avaliar_gate_revisao(e.texto_nota(nota), tipo="nota_versao") == []
