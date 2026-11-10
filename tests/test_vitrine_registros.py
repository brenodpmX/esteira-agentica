import pytest

from tests import _vitrine_helpers as h

CAMPOS_VALIDACAO = list(h.CAMPOS_VALIDACAO)


def _validos_base():
    return {
        "exemplo": "minimalista",
        "data": "2026-11-09",
        "versao_suportada": "1.29.0",
        "resultado": "sucesso",
        "ponto_da_falha": "n/a",
        "ajuda_necessaria": "nenhuma",
        "tempo_observado": "10 minutos",
        "falhas": "nenhuma",
        "duvidas": "nenhuma",
        "qualidade_vs_objetivo": "atendeu o objetivo",
        "modelo": "modelo-exemplo",
        "tokens": "1000",
        "custo": "n/a",
        "cenario": "cenário hipotético",
    }


def test_processo_validacao_documenta_campos():
    texto = (h.DOC_EXEMPLOS / "validacao-interna.md").read_text(encoding="utf-8")
    for campo in CAMPOS_VALIDACAO:
        assert f"{campo}:" in texto, campo
    baixo = texto.lower()
    assert "somente" in baixo and "uso.md" in baixo
    assert "lacuna" in baixo and "falha do exemplo" in baixo
    assert "com sucesso ou com falha" in baixo


def test_registros_validacao_completos():
    registros = h.carregar_registros(h.REGISTROS / "validacao")
    assert {r["exemplo"] for _, r in registros} == set(h.PACOTES)
    for caminho, reg in registros:
        assert h.validar_registro_validacao(reg) == [], caminho
        assert reg["versao_suportada"] == h.carregar_exemplo(reg["exemplo"])["versao_suportada"]


def test_registro_valido_base():
    assert h.validar_registro_validacao(_validos_base()) == []


@pytest.mark.parametrize("campo", CAMPOS_VALIDACAO)
def test_campo_obrigatorio_ausente_reprova(campo):
    reg = _validos_base()
    del reg[campo]
    erros = h.validar_registro_validacao(reg)
    assert erros and campo in erros[0]


def test_custo_amarrado_e_falha_registrada():
    sem_modelo = dict(_validos_base(), modelo="n/a")
    erros = h.validar_registro_validacao(sem_modelo)
    assert any("modelo" in e for e in erros)

    falha_sem_ponto = dict(_validos_base(), resultado="falha", ponto_da_falha="n/a")
    erros = h.validar_registro_validacao(falha_sem_ponto)
    assert any("ponto_da_falha" in e for e in erros)

    falha_ok = dict(_validos_base(), resultado="falha", ponto_da_falha="pré-requisito ausente")
    assert h.validar_registro_validacao(falha_ok) == []

    generico = dict(_validos_base(), custo="custo típico de 2 dólares")
    erros = h.validar_registro_validacao(generico)
    assert any("custo" in e for e in erros)

    vazio = dict(_validos_base(), ajuda_necessaria="")
    assert any("ajuda_necessaria" in e for e in h.validar_registro_validacao(vazio))


def test_apresentacao_documenta_roteiro_e_formato():
    texto = (h.DOC_EXEMPLOS / "apresentacao.md").read_text(encoding="utf-8")
    roteiro = h.secao(texto, "Roteiro")
    assert roteiro and len(h.linhas_nao_vazias(roteiro)) >= 5
    for campo in ("compreensao_observada", "decisao", "objecoes", "proximo_passo"):
        assert f"{campo}:" in texto, campo
    baixo = texto.lower()
    for termo in ("interesse", "recusa", "pendente", "ao menos uma objeção", "acompanhamento agendado"):
        assert termo in baixo, termo
    assert "visualização genérica não substitui" in baixo
    assert "meta numérica" in baixo
    assert "validação interna com sucesso" in baixo


def test_registro_apresentacao_regras():
    base = {
        "compreensao_observada": "entendeu o fluxo",
        "decisao": "interesse",
        "objecoes": "",
        "proximo_passo": "nova avaliação",
    }
    assert h.validar_registro_apresentacao(base) == []
    recusa_sem = dict(base, decisao="recusa", objecoes="")
    assert any("objecoes" in e for e in h.validar_registro_apresentacao(recusa_sem))
    recusa = dict(base, decisao="recusa", objecoes="custo incerto")
    assert h.validar_registro_apresentacao(recusa) == []
    pendente_sem = dict(base, decisao="pendente", proximo_passo="")
    assert any("proximo_passo" in e for e in h.validar_registro_apresentacao(pendente_sem))
    pendente = dict(base, decisao="pendente", proximo_passo="acompanhamento agendado para a semana seguinte")
    assert h.validar_registro_apresentacao(pendente) == []
    assert any("decisao" in e for e in h.validar_registro_apresentacao(dict(base, decisao="gostou")))
    sem_decisao = {k: v for k, v in base.items() if k != "decisao"}
    assert any("decisao" in e for e in h.validar_registro_apresentacao(sem_decisao))
    assert any(
        "compreensao_observada" in e
        for e in h.validar_registro_apresentacao(dict(base, compreensao_observada=""))
    )
    for caminho, reg in h.carregar_registros(h.REGISTROS / "apresentacao"):
        assert h.validar_registro_apresentacao(reg) == [], caminho


def test_apresentacao_exige_validacao_previa():
    sucesso = {"exemplo": "minimalista", "resultado": "sucesso", "data": "2026-11-01"}
    falha = dict(sucesso, resultado="falha")
    posterior = dict(sucesso, data="2026-11-20")
    outro = dict(sucesso, exemplo="referencia-hipotetica")
    assert not h.validacao_previa_existe("minimalista", "2026-11-10", [])
    assert not h.validacao_previa_existe("minimalista", "2026-11-10", [falha])
    assert not h.validacao_previa_existe("minimalista", "2026-11-10", [posterior])
    assert not h.validacao_previa_existe("minimalista", "2026-11-10", [outro])
    assert h.validacao_previa_existe("minimalista", "2026-11-10", [sucesso])

    validacoes = [r for _, r in h.carregar_registros(h.REGISTROS / "validacao")]
    for caminho, reg in h.carregar_registros(h.REGISTROS / "apresentacao"):
        assert h.validacao_previa_existe(reg["exemplo"], reg["data"], validacoes), caminho
