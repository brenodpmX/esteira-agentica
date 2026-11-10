import pytest

from tests import _vitrine_helpers as h


def test_regra_impacto_escrita_e_obrigatoria():
    texto = (h.DOC_EXEMPLOS / "manutencao-por-impacto.md").read_text(encoding="utf-8")
    baixo = texto.lower()
    assert "etapa de documentação" in baixo
    assert "deve" in baixo and "obrigatóri" in baixo
    assert "atualizado e revalidado" in baixo
    assert "ausência de impacto" in baixo
    for campo in ("mudanca", "afeta_exemplo", "exemplos_afetados", "acao", "revalidacao"):
        assert f"{campo}:" in texto, campo
    assert "falha de processo" in baixo
    assert "processo, não automação" in baixo


def test_registro_impacto_regras():
    nao = {"mudanca": "ajuste de log", "afeta_exemplo": "nao", "acao": "nenhum exemplo referencia o log"}
    assert h.validar_registro_impacto(nao) == []
    sim = {
        "mudanca": "novo campo obrigatório no pipe.yml",
        "afeta_exemplo": "sim",
        "exemplos_afetados": "minimalista",
        "acao": "campo adicionado",
        "revalidacao": "doc/exemplos/registros/validacao/minimalista-2026-11-09-2.md",
    }
    assert h.validar_registro_impacto(sim) == []
    sem_reval = {k: v for k, v in sim.items() if k != "revalidacao"}
    assert any("revalidacao" in e for e in h.validar_registro_impacto(sem_reval))
    assert any("afeta_exemplo" in e for e in h.validar_registro_impacto(dict(nao, afeta_exemplo="talvez")))
    sem_afeta = {k: v for k, v in nao.items() if k != "afeta_exemplo"}
    assert any("afeta_exemplo" in e for e in h.validar_registro_impacto(sem_afeta))
    assert any("mudanca" in e for e in h.validar_registro_impacto(dict(nao, mudanca="")))
    for caminho, reg in h.carregar_registros(h.REGISTROS / "impacto"):
        assert h.validar_registro_impacto(reg) == [], caminho


def test_regra_reavaliacao_temas():
    texto = (h.DOC_EXEMPLOS / "reavaliacao-temas.md").read_text(encoding="utf-8")
    baixo = texto.lower()
    assert "em produção" in baixo
    for tema in ("kanban", "scrum", "acadêmico", "xgh", "gestão", "rh", "atendimento"):
        assert tema in baixo, tema
    assert "herança" in baixo
    assert "próprios gates" in baixo
    for campo in ("gatilho", "data", "temas"):
        assert f"{campo}:" in texto, campo
    assert "heranca_de_aprovacao: nenhuma" in texto


def test_registro_reavaliacao_sem_heranca():
    ok = {
        "gatilho": "Em produção da primeira vitrine",
        "data": "2026-12-01",
        "temas": "Kanban, Scrum, RH",
        "heranca_de_aprovacao": "nenhuma",
    }
    assert h.validar_registro_reavaliacao(ok) == []
    assert any(
        "heranca_de_aprovacao" in e
        for e in h.validar_registro_reavaliacao(dict(ok, heranca_de_aprovacao="parcial"))
    )
    assert any(
        "temas" in e for e in h.validar_registro_reavaliacao(dict(ok, temas="Kanban (aprovado)"))
    )
    assert any(
        "temas" in e for e in h.validar_registro_reavaliacao(dict(ok, temas="Scrum priorizado"))
    )
    sem_gatilho = {k: v for k, v in ok.items() if k != "gatilho"}
    assert any("gatilho" in e for e in h.validar_registro_reavaliacao(sem_gatilho))


def test_registro_real_de_reavaliacao_apos_producao():
    registros = h.carregar_registros(h.REGISTROS / "reavaliacao")
    if not registros:
        pytest.skip("solicitação de reavaliação só é exigível após a entrega alcançar Em produção")
    for caminho, reg in registros:
        assert h.validar_registro_reavaliacao(reg) == [], caminho
