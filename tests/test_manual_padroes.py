import re

import pytest

from tests import _editorial_helpers as e

README_CONFORME = """# Esteira Agêntica

Texto de abertura.

## Configuração

Veja [a referência](doc/configuracao/referencia.md) e [exemplos](exemplos/minimalista/USO.md).

## Uso

### Primeira execução local (Python)

python -m src

### Alternativa: container (Docker Compose)

Veja [o runbook](doc/runbook/docker.md).
"""


@pytest.fixture(scope="module")
def manual():
    assert e.MANUAL.exists(), f"CA-10: {e.MANUAL} ausente"
    return e.ler(e.MANUAL)


@pytest.fixture(scope="module")
def regras(manual):
    return e.regras_do_manual(manual)


def test_regras_tem_criterio_verificavel(regras):
    assert len(regras) >= 9, f"CA-10: manual com {len(regras)} regras"
    ids = [rid for rid, _ in regras]
    assert len(ids) == len(set(ids)), "CA-10: ids de regra duplicados"
    vagas = [rid for rid, texto in regras
             if not re.search(r"\b(deve|não deve|sempre|nunca)\b", texto, re.IGNORECASE)]
    assert not vagas, f"CA-10: regras sem critério objetivo: {vagas}"
    sugestoes = [rid for rid, texto in regras
                 if re.search(r"\b(recomenda-se|sugere-se|preferencialmente|se possível)\b",
                              texto, re.IGNORECASE)]
    assert not sugestoes, f"CA-10: regras redigidas como sugestão: {sugestoes}"


def test_coerente_com_regras_de_negocio_da_issue(regras):
    texto = " ".join(t for _, t in regras).lower()
    assert re.search(r"execução local.{0,120}antes.{0,60}container", texto), "RN-08"
    assert re.search(r"nunca.{0,40}lista tecnicista", texto), "RN-07"
    assert re.search(r"porta de entrada.{0,200}desenvolvimento", texto), "RNF-05/RN-04"
    assert re.search(r"fonte canônica única", texto), "RN-09"


def test_validador_cita_apenas_regras_do_manual(regras):
    ids = {rid for rid, _ in regras}
    usados = set(re.findall(r"MP-\d{2}", e.ler(e.RAIZ / "tests" / "_editorial_helpers.py")))
    assert usados <= ids, f"CA-10: validador usa regras inexistentes no manual: {usados - ids}"


def test_checklist_aplicado_ao_readme():
    divergencias = e.avaliar_conformidade_manual(e.ler(e.README))
    assert divergencias == [], "CA-10: README diverge do manual:\n" + "\n".join(divergencias)


def test_alteracao_fora_do_padrao_e_recusada():
    assert e.avaliar_conformidade_manual(README_CONFORME) == []
    alterado = README_CONFORME + "\n## Loop Principal\n\nDetalhes do laço.\n"
    divergencias = e.avaliar_conformidade_manual(alterado)
    assert divergencias and all(d.startswith("MP-06") for d in divergencias), divergencias
    invertido = README_CONFORME.replace(
        "### Primeira execução local (Python)\n\npython -m src\n\n", "") + (
        "\n### Primeira execução local (Python)\n\npython -m src\n")
    assert any(d.startswith("MP-08") for d in e.avaliar_conformidade_manual(invertido))
    com_id = README_CONFORME + "\nCorrigido na #123.\n"
    assert any(d.startswith("MP-04") for d in e.avaliar_conformidade_manual(com_id))
