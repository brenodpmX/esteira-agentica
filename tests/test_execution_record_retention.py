"""Testes de retenção própria dos registros de execução (issue #307) — Grupo C.

Cobre CT-11 (retenção configurada expira) e CT-12 (sem retenção, nenhum
expurgo). Relógio controlável via o parâmetro `now` de `purge_expired` e o
`inicio` dos registros — nunca `sleep` real. A retenção é PRÓPRIA e desacoplada
do `log.ttl` (RN-09/RNF-06).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import execution  # noqa: E402
from src.core import execution_record as er  # noqa: E402
from src.core.execution import ExecutionResult  # noqa: E402

DIA = 86400.0


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pipe").mkdir(exist_ok=True)
    yield


def _rec(issue_id, inicio):
    return er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id=issue_id, board="entrega", etapa="desenvolvimento",
        avancou=False, inicio=inicio, fim=inicio + 1,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CT-11 — Retenção configurada torna o registro elegível a expurgo
# ══════════════════════════════════════════════════════════════════════════════

def test_ct11_borda_menor_que_n_permanece():
    t0 = 1_000_000.0
    _rec("42", t0)
    # Idade < N dias → permanece (não elegível). N=7.
    removidos = er.purge_expired(7, now=t0 + 6 * DIA)
    assert removidos == 0
    assert len(er.records_for_issue("42")) == 1


def test_ct11_borda_igual_a_n_elegivel():
    t0 = 1_000_000.0
    _rec("42", t0)
    # Idade == N dias → elegível (contrato `>= retencao_dias`).
    removidos = er.purge_expired(7, now=t0 + 7 * DIA)
    assert removidos == 1
    assert er.records_for_issue("42") == []


def test_ct11_borda_maior_que_n_elegivel():
    t0 = 1_000_000.0
    _rec("42", t0)
    removidos = er.purge_expired(7, now=t0 + 8 * DIA)
    assert removidos == 1
    assert er.records_for_issue("42") == []


def test_ct11_retencao_independe_do_log_ttl():
    """A retenção própria não depende de `log.ttl`: só `retencao_dias` decide."""
    t0 = 1_000_000.0
    _rec("42", t0)
    # Mesmo com um log.ttl hipotético diferente, só retencao_dias rege o expurgo.
    assert er.purge_expired(10, now=t0 + 9 * DIA) == 0   # idade 9 < 10
    assert er.purge_expired(10, now=t0 + 10 * DIA) == 1  # idade 10 >= 10


# ══════════════════════════════════════════════════════════════════════════════
# CT-12 — Retenção não configurada: nenhum expurgo automático
# ══════════════════════════════════════════════════════════════════════════════

def test_ct12_sem_retencao_nenhum_expurgo():
    t0 = 1_000_000.0
    _rec("42", t0)
    _rec("43", t0 - 10_000 * DIA)   # arbitrariamente antigo
    # retencao_dias None → NENHUM registro removido (estado seguro por padrão).
    removidos = er.purge_expired(None, now=t0 + 10_000 * DIA)
    assert removidos == 0
    assert len(er.records_for_issue("42")) == 1
    assert len(er.records_for_issue("43")) == 1


def test_registro_sem_inicio_nao_expurgado():
    """Registro sem `inicio` conhecido não tem idade segura → preservado."""
    er.record_execution(
        issue_id="99", board="entrega", etapa="desenvolvimento",
        resultado=er.CONCLUIDA, avancou=False, inicio=None,
    )
    removidos = er.purge_expired(1, now=1_000_000.0 + 10 * DIA)
    assert removidos == 0
    assert len(er.records_for_issue("99")) == 1
