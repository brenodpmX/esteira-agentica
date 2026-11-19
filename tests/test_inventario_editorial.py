import pytest

from tests import _editorial_helpers as e

PUBLICOS_PRIORIZADOS = (
    "README.md",
    "doc/configuracao/referencia.md",
    "doc/governanca-editorial/manual-padroes-documentacao.md",
    "doc/governanca-editorial/gate-revisao.md",
    "NOVIDADES.md",
    "doc/runbook/docker.md",
    "exemplos/minimalista/USO.md",
    "exemplos/referencia-hipotetica/USO.md",
)


def _item_completo(**extra):
    item = {
        "documento": "doc/runbook/docker.md",
        "audiencia": "publico",
        "sensibilidade": "baixa",
        "fonte_canonica": "doc/runbook/docker.md",
        "responsavel": "Tech Lead",
        "gatilho_atualizacao": "mudança em docker-compose.yml",
    }
    item.update(extra)
    return item


@pytest.fixture(scope="module")
def itens():
    assert e.INVENTARIO.exists(), f"CA-8: {e.INVENTARIO} ausente"
    return e.parse_blocos(e.ler(e.INVENTARIO), "documento")


def test_itens_tem_seis_campos(itens):
    assert itens, "CA-8: inventário vazio"
    for item in itens:
        for campo in e.CAMPOS_INVENTARIO:
            assert item.get(campo), f"CA-8: {item.get('documento')} sem '{campo}'"
        assert item["audiencia"] in e.AUDIENCIAS
        assert item["sensibilidade"] in e.SENSIBILIDADES


def test_cobertura_documentos_publicos(itens):
    por_documento = {i["documento"]: i for i in itens}
    ausentes = [d for d in PUBLICOS_PRIORIZADOS if d not in por_documento]
    assert not ausentes, f"RN-09: documentos públicos fora do inventário: {ausentes}"
    nao_publicos = [
        d for d in PUBLICOS_PRIORIZADOS
        if por_documento[d]["audiencia"] != "publico" and not por_documento[d].get("decisao")
    ]
    assert not nao_publicos, f"RN-09: públicos priorizados sem audiência pública: {nao_publicos}"


def test_documentos_do_inventario_existem(itens):
    inexistentes = [i["documento"] for i in itens if not (e.RAIZ / i["documento"]).exists()]
    assert not inexistentes, f"RN-09: inventário cita documentos inexistentes: {inexistentes}"


def test_item_sem_fonte_responsavel_gatilho_e_reportado(itens):
    assert e.validar_item_inventario(_item_completo()) == []
    for campo in ("fonte_canonica", "responsavel", "gatilho_atualizacao"):
        item = _item_completo()
        del item[campo]
        erros = e.validar_item_inventario(item)
        assert len(erros) == 1 and f"'{campo}'" in erros[0], erros
    erros_reais = [erro for item in itens for erro in e.validar_item_inventario(item)]
    assert not erros_reais, "CA-8: itens reais inválidos:\n" + "\n".join(erros_reais)


def test_misto_exige_decisao():
    sem = _item_completo(documento="CHANGELOG.md", audiencia="misto")
    erros = e.validar_item_inventario(sem)
    assert any("misto" in erro and "decisao" in erro for erro in erros), erros
    com = _item_completo(
        documento="CHANGELOG.md",
        audiencia="misto",
        decisao="registro técnico detalhado; a comunicação pública vive em NOVIDADES.md",
    )
    assert e.validar_item_inventario(com) == []


def test_classificacao_por_finalidade_nao_localizacao(itens):
    publico_em_pasta_interna = _item_completo(
        documento="doc/architecture/x.md", audiencia="publico")
    assert e.validar_item_inventario(publico_em_pasta_interna)
    interno_em_pasta_publica = _item_completo(
        documento="doc/runbook/x.md", audiencia="interno")
    assert e.validar_item_inventario(interno_em_pasta_publica)
    justificado = _item_completo(
        documento="doc/runbook/x.md",
        audiencia="interno",
        decisao="roteiro de homologação de uma correção, finalidade de desenvolvimento",
    )
    assert e.validar_item_inventario(justificado) == []
    excecoes_sem_decisao = [
        i["documento"] for i in itens
        if e._excecao_de_pasta(i["documento"], i["audiencia"]) and not i.get("decisao")
    ]
    assert not excecoes_sem_decisao, (
        f"RN-02: classificação herdada da pasta sem decisão: {excecoes_sem_decisao}"
    )
