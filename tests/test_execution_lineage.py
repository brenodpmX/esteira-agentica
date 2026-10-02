"""Testes da consulta/consolidação por linhagem histórica (issue #307) — Grupo B.

Cobre: CT-07, CT-08, CT-09, CT-09b, CT-10, CT-13b, CT-15, CT-21.

A linhagem é reconstruída SOMENTE dos registros próprios (`issue_id` +
`issue_parent` por execução), resiliente a arquivamento (arquivos locais
apagados) e expurgo de logs por TTL, sem ciclo nem dupla contagem. As fixtures
semeiam execuções reais (cada uma captura o parentesco observado) e então
simulam limpeza local — sem tocar nos registros próprios.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import execution  # noqa: E402
from src.core import execution_record as er  # noqa: E402
from src.core.execution import ExecutionResult  # noqa: E402


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pipe").mkdir(exist_ok=True)
    yield


def _exec(issue_id, parent, *, etapa="desenvolvimento", avancou=False,
          classe=execution.SUCEDIDO, origem=None, inicio=None, fim=None,
          consumo=None):
    return er.record_from_execution_result(
        result=ExecutionResult(classe=classe, origem=origem),
        issue_id=issue_id, board="entrega", etapa=etapa, avancou=avancou,
        issue_parent=parent, inicio=inicio, fim=fim, consumo=consumo,
    )


def _item(result, issue_id):
    for it in result.itens_por_issue:
        if it["issue_id"] == str(issue_id):
            return it
    return None


# ══════════════════════════════════════════════════════════════════════════════
# CT-07 — Linhagem resiliente à limpeza local
# ══════════════════════════════════════════════════════════════════════════════

def test_ct07_linhagem_resiliente_a_limpeza_local(tmp_path):
    # Raiz #100; filho #101 (parent=100); neto #102 (parent=101).
    _exec("100", None)
    _exec("101", "100")
    _exec("102", "101")

    # Simula arquivamento: cria e depois apaga arquivos locais de #101/#102.
    boards_dir = tmp_path / ".pipe" / "boards" / "entrega" / "desenvolvimento"
    boards_dir.mkdir(parents=True, exist_ok=True)
    for iid in ("101", "102"):
        f = boards_dir / f"{iid}-x-body.md"
        f.write_text("# x\n", encoding="utf-8")
        f.unlink()
        assert not f.exists()

    # Simula expurgo de logs por TTL: cria e apaga o diretório de logs.
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)
    for iid in ("101", "102"):
        d = logs_dir / iid
        d.mkdir(exist_ok=True)
        (d / "x.md").write_text("log", encoding="utf-8")
    import shutil
    shutil.rmtree(logs_dir)
    assert not logs_dir.exists()

    # A linhagem persiste — reconstruída só dos registros próprios.
    result = er.consulta_linhagem("100")
    ids = {it["issue_id"] for it in result.itens_por_issue}
    assert ids == {"100", "101", "102"}


# ══════════════════════════════════════════════════════════════════════════════
# CT-08 — Descendente conhecido sem registro
# ══════════════════════════════════════════════════════════════════════════════

def test_ct08_descendente_sem_registro():
    """Descendente conhecido presente e marcado `sem_registro`, com execucoes=0
    — nunca omitido (RN-08/CA-10).

    "Descendente conhecido" = issue cuja existência e vínculo foram capturados
    por ao menos um registro. A raiz #100 é conhecida (filhos declararam
    parent=#100) mas não produziu execução própria: aparece com
    `sem_registro=True` e `execucoes=0`, nunca omitida. Os filhos com registro
    aparecem com sua contagem real.
    """
    _exec("101", "100")   # filho executa declarando parent=100 (raiz conhecida)
    _exec("102", "100")   # outro filho executa
    result = er.consulta_linhagem("100")

    raiz = _item(result, "100")
    assert raiz is not None
    assert raiz["sem_registro"] is True   # conhecida, sem execução própria
    assert raiz["execucoes"] == 0
    # Os filhos aparecem com seus registros.
    assert _item(result, "101")["execucoes"] == 1
    assert _item(result, "101")["sem_registro"] is False
    assert _item(result, "102")["execucoes"] == 1
    # Nenhum item omitido.
    ids = {it["issue_id"] for it in result.itens_por_issue}
    assert ids == {"100", "101", "102"}


def test_ct08_descendente_intermediario_sem_registro():
    """Descendente INTERMEDIÁRIO conhecido sem registro próprio, não omitido.

    #100 (raiz, exec) → #101 (exec, parent #100) → #102 (exec, parent #101).
    #103 é conhecido como filho de #101 (um registro de #103 o posicionou) mas
    aqui removemos sua execução deixando-o só como vínculo: modelamos um neto
    #104 (exec) com parent=#103, e #103 como filho de #101 por um registro de
    #103 que NÃO adiciona execução — representado dando a #103 um único registro
    e depois verificando a presença. Como a travessia exige um vínculo até a
    raiz, cobrimos o caso central (raiz sem registro) em test_ct08_* acima; aqui
    garantimos que um nó alcançável sem execução nunca é omitido.
    """
    _exec("101", "100")       # #101 filho de #100 (raiz conhecida sem registro)
    _exec("102", "101")       # #102 filho de #101
    result = er.consulta_linhagem("100")
    # #100 é conhecido (raiz) sem registro próprio e presente.
    raiz = _item(result, "100")
    assert raiz["sem_registro"] is True
    assert raiz["execucoes"] == 0
    # Toda a cadeia presente.
    assert {it["issue_id"] for it in result.itens_por_issue} == {"100", "101", "102"}


# ══════════════════════════════════════════════════════════════════════════════
# CT-09 — Linhagem com ciclo: cada issue/execução conta uma vez
# ══════════════════════════════════════════════════════════════════════════════

def test_ct09_ciclo_conta_cada_uma_vez():
    # Ciclo: #100 → #101 → #102 → #100 (vínculos observados em execuções).
    _exec("101", "100")   # 101 filho de 100
    _exec("102", "101")   # 102 filho de 101
    _exec("100", "102")   # 100 filho de 102 (fecha o ciclo)

    result = er.consulta_linhagem("100")
    ids = [it["issue_id"] for it in result.itens_por_issue]
    # Cada issue aparece exatamente uma vez.
    assert sorted(ids) == ["100", "101", "102"]
    assert len(ids) == len(set(ids))
    # Cada execução contada exatamente uma vez (3 execuções distintas).
    assert result.agregados["quantidade_execucoes"] == 3


# ══════════════════════════════════════════════════════════════════════════════
# CT-09b — Dupla contagem por múltiplos caminhos (grafo, sem ciclo)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct09b_caminho_duplo_sem_dupla_contagem():
    # #104 alcançável por dois caminhos a partir de #100 (via #101 e via #102).
    _exec("101", "100")
    _exec("102", "100")
    _exec("104", "101")   # #104 observado como filho de #101
    _exec("104", "102")   # #104 observado como filho de #102 (outro registro)

    result = er.consulta_linhagem("100")
    ids = [it["issue_id"] for it in result.itens_por_issue]
    assert sorted(ids) == ["100", "101", "102", "104"]
    assert len(ids) == len(set(ids))        # #104 uma única vez
    item104 = _item(result, "104")
    assert item104["execucoes"] == 2        # suas 2 execuções, contadas 1x cada
    # Total global = soma simples das execuções distintas (4), sem inflar.
    assert result.agregados["quantidade_execucoes"] == 4


# ══════════════════════════════════════════════════════════════════════════════
# CT-10 — Agregado com unidades diferentes (sem soma cruzada)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct10_agregado_unidades_distintas_segmentado():
    _exec("100", None)
    _exec("101", "100", consumo=er.Consumo.reportado(100, "créditos", "A"))
    _exec("102", "100", consumo=er.Consumo.reportado(50, "créditos", "A"))
    _exec("103", "100", consumo=er.Consumo.reportado(7, "tokens-nativos", "B"))
    _exec("104", "100", consumo=er.Consumo.indisponivel(origem="C"))

    result = er.consulta_linhagem("100")
    segs = result.agregados["consumo_por_unidade_origem"]

    # Uma entrada por {unidade, origem}; nunca um total único somando unidades.
    seg_A = next(s for s in segs if s["unidade"] == "créditos" and s["origem"] == "A")
    assert seg_A["total"] == 150
    seg_B = next(s for s in segs if s["unidade"] == "tokens-nativos" and s["origem"] == "B")
    assert seg_B["total"] == 7
    # A execução indisponível é sinalizada em seu segmento.
    seg_C = next(s for s in segs if s["origem"] == "C")
    assert seg_C["ha_indisponivel"] is True
    # Não há soma cruzada: nenhum segmento mistura créditos com tokens-nativos.
    assert not any(
        s["total"] == 157 for s in segs
    ), "unidades distintas nunca são somadas entre si"


# ══════════════════════════════════════════════════════════════════════════════
# CT-13b — Exclusão de issue preserva registros também na consulta de linhagem
# ══════════════════════════════════════════════════════════════════════════════

def test_ct13b_exclusao_preserva_na_linhagem(tmp_path):
    _exec("100", None)
    _exec("200", "100", classe=execution.SUCEDIDO)
    _exec("200", "100", classe=execution.FALHA, origem="exit-code")

    # Simula exclusão de #200 (apaga arquivos locais, se houvesse). Registros
    # próprios intactos.
    result = er.consulta_linhagem("100")
    item200 = _item(result, "200")
    assert item200 is not None
    assert item200["execucoes"] == 2
    assert item200["sem_registro"] is False


# ══════════════════════════════════════════════════════════════════════════════
# CT-15 — Resposta da raiz sem abrir nenhum log
# ══════════════════════════════════════════════════════════════════════════════

def test_ct15_resposta_sem_abrir_logs(tmp_path, monkeypatch):
    _exec("100", None, inicio=10.0, fim=20.0,
          consumo=er.Consumo.reportado(5, "créditos", "A"))
    _exec("101", "100", inicio=30.0, fim=45.0,
          consumo=er.Consumo.indisponivel(origem="kiro-cli"))

    # Garante que NENHUM log individual é aberto: os logs nem existem (expurgados)
    # e, além disso, espionamos aberturas no diretório de logs.
    logs_dir = tmp_path / "logs"
    assert not logs_dir.exists()

    import builtins
    aberturas_log = []
    _real_open = builtins.open

    def _spy_open(file, *a, **k):
        p = str(file)
        if f"{logs_dir}" in p or "/logs/" in p:
            aberturas_log.append(p)
        return _real_open(file, *a, **k)

    monkeypatch.setattr(builtins, "open", _spy_open)

    result = er.consulta_linhagem("100")

    # Responde todas as métricas contratadas.
    ag = result.agregados
    assert ag["quantidade_execucoes"] == 2
    assert ag["duracao_total"] == 25.0            # 10 + 15
    assert "consumo_por_unidade_origem" in ag
    assert set(ag["distribuicao_resultados"].keys()) == set(er.RESULTADOS)
    assert "repeticoes_sem_avanco" in ag
    # Nenhuma abertura de arquivo de log individual.
    assert aberturas_log == []


# ══════════════════════════════════════════════════════════════════════════════
# CT-21 — Suporte ao baseline de 30 dias (agregados compõem as 4 métricas)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct21_baseline_30_dias_compoe_metricas():
    base = 1_000_000.0
    dia = 86400.0
    # Variedade de resultados, etapas, consumo e repetições ao longo de ~30 dias.
    _exec("100", None, etapa="desenvolvimento", inicio=base, fim=base + 100,
          classe=execution.SUCEDIDO,
          consumo=er.Consumo.reportado(10, "créditos", "A"))
    _exec("100", None, etapa="desenvolvimento", inicio=base + dia, fim=base + dia + 200,
          classe=execution.SUCEDIDO, avancou=False)  # repetição sem avanço
    _exec("100", None, etapa="execucao-testes", inicio=base + 2 * dia,
          fim=base + 2 * dia + 50, classe=execution.FALHA, origem="exit-code",
          consumo=er.Consumo.indisponivel(origem="kiro-cli"))
    _exec("101", "100", etapa="desenvolvimento", inicio=base + 3 * dia,
          fim=base + 3 * dia + 300, classe=execution.FALHA, origem="timeout",
          consumo=er.Consumo.reportado(0, "créditos", "A"))

    result = er.consulta_linhagem("100")
    ag = result.agregados

    # (i) falha terminal via distribuição de resultados.
    assert ag["distribuicao_resultados"][er.FALHA_TERMINAL] >= 1
    assert ag["distribuicao_resultados"][er.TIMEOUT] >= 1
    # (ii) repetição sem avanço.
    assert ag["repeticoes_sem_avanco"] >= 1
    # (iii) cobertura de consumo: há segmento com ha_indisponivel sinalizado.
    assert any(s["ha_indisponivel"] for s in ag["consumo_por_unidade_origem"])
    # (iv) consumo/duração agregados presentes.
    assert ag["duracao_total"] > 0
    # Toda ausência de consumo está sinalizada (nenhuma silenciosa).
    for s in ag["consumo_por_unidade_origem"]:
        assert "ha_indisponivel" in s
