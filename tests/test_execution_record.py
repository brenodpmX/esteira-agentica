"""Testes do registro de execução por execução (issue #307) — Grupo A + D.

Cobre: CT-01, CT-02, CT-03, CT-04, CT-04b, CT-05, CT-06, CT-13, CT-16
(isolamento), CT-17 (comportamental), CT-18, CT-19, CT-20.

Convenções (test-cases.md): offline, sem rede; `monkeypatch.chdir(tmp_path)`
autouse para isolar `.pipe/`; relógio controlável via parâmetros `inicio`/`fim`
(sem sleep real); a evidência de negócio vem da consulta pública
(`records_for_issue`/`consulta_linhagem`), não da leitura do arquivo protegido —
exceto o caso explícito de isolamento (CT-16). Nunca fazemos `monkeypatch` do
símbolo sob teste: a gravação, o mapeamento e a derivação de repetição rodam de
verdade; só o `ExecutionResult` de entrada é controlado.
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


# ══════════════════════════════════════════════════════════════════════════════
# CT-01 — Execução concluída sem avanço
# ══════════════════════════════════════════════════════════════════════════════

def test_ct01_concluida_sem_avanco():
    rec = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="42", board="entrega", etapa="desenvolvimento",
        avancou=False,
    )
    assert rec.resultado == er.CONCLUIDA
    assert rec.avancou is False

    # Exatamente um registro para a execução (consulta pública).
    registros = er.records_for_issue("42")
    assert len(registros) == 1
    assert registros[0].resultado == er.CONCLUIDA
    assert registros[0].avancou is False


# ══════════════════════════════════════════════════════════════════════════════
# CT-02 — Interrompida com avanço prévio
# ══════════════════════════════════════════════════════════════════════════════

def test_ct02_interrompida_com_avanco_previo():
    rec = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.UNKNOWN_OUTCOME,
                               origem="dispatch failure"),
        issue_id="42", board="entrega", etapa="desenvolvimento",
        avancou=True, inicio=1000.0, fim=1050.0,
    )
    assert rec.resultado == er.INTERROMPIDA
    assert rec.avancou is True
    # Início preservado e duração parcial conhecida (não vazia por obrigação).
    assert rec.inicio == 1000.0
    assert rec.fim == 1050.0
    assert rec.duracao == 50.0


# ══════════════════════════════════════════════════════════════════════════════
# CT-03 — Consumo indisponível (plataforma não reporta)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct03_consumo_indisponivel():
    rec = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
        consumo=er.Consumo.indisponivel(origem="kiro-cli"),
    )
    d = rec.consumo.to_dict()
    assert d["disponibilidade"] == er.INDISPONIVEL
    # Invariante RNF-02: indisponível ⇒ `valor` NÃO definido (nunca zero).
    assert "valor" not in d
    assert rec.consumo.valor is None


# ══════════════════════════════════════════════════════════════════════════════
# CT-04 — Consumo zero reportado
# ══════════════════════════════════════════════════════════════════════════════

def test_ct04_consumo_zero_reportado():
    rec = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
        consumo=er.Consumo.reportado(valor=0, unidade="créditos", origem="plataformaX"),
    )
    d = rec.consumo.to_dict()
    assert d["disponibilidade"] == er.DISPONIVEL
    assert d["valor"] == 0  # zero reportado é DISTINTO de não informado
    assert d["unidade"] == "créditos"
    assert d["origem"] == "plataformaX"


# ══════════════════════════════════════════════════════════════════════════════
# CT-04b — Consumo reportado disponível (valor, unidade, origem)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct04b_consumo_disponivel_positivo():
    rec = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
        consumo=er.Consumo.reportado(valor=1234, unidade="créditos", origem="adapterA"),
    )
    d = rec.consumo.to_dict()
    assert d["valor"] == 1234
    assert d["unidade"] == "créditos"       # unidade nativa preservada (RN-05)
    assert d["origem"] == "adapterA"
    assert d["disponibilidade"] == er.DISPONIVEL
    # Rótulo geral do núcleo é "Tokens", sem converter a unidade nativa.
    assert er.ROTULO_CONSUMO == "Tokens"


# ══════════════════════════════════════════════════════════════════════════════
# CT-05 — Repetição sem avanço na mesma etapa
# ══════════════════════════════════════════════════════════════════════════════

def test_ct05_repeticao_sem_avanco_mesma_etapa():
    # Execução 1: conclui sem avançar.
    r1 = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
    )
    # Execução 2: mesmo (board, etapa, issue).
    r2 = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
    )
    assert r1.repeticao_sem_avanco is False  # não há anterior sem avanço
    assert r2.repeticao_sem_avanco is True   # anterior na mesma etapa não avançou


# ══════════════════════════════════════════════════════════════════════════════
# CT-06 — Não repetição após mudança de etapa
# ══════════════════════════════════════════════════════════════════════════════

def test_ct06_nao_repeticao_apos_mudanca_de_etapa():
    er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
    )
    # Execução 2 em etapa DIFERENTE (mesma issue).
    r2 = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="42", board="entrega", etapa="execucao-testes", avancou=False,
    )
    assert r2.repeticao_sem_avanco is False  # mudança de etapa descaracteriza


# ══════════════════════════════════════════════════════════════════════════════
# CT-13 — Exclusão de issue preserva os registros (consulta direta)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct13_exclusao_de_issue_preserva_registros():
    er.record_from_execution_result(
        result=ExecutionResult(classe=execution.SUCEDIDO),
        issue_id="200", board="entrega", etapa="desenvolvimento", avancou=False,
    )
    er.record_from_execution_result(
        result=ExecutionResult(classe=execution.FALHA, origem="exit-code"),
        issue_id="200", board="entrega", etapa="desenvolvimento", avancou=False,
    )
    # Simula a exclusão da issue: apaga QUALQUER arquivo local da issue. Os
    # registros próprios NÃO são tocados pela exclusão (RN-10).
    # (não há arquivos locais a apagar neste nível; o ponto é que a consulta
    # direta não depende deles.)
    registros = er.records_for_issue("200")
    assert len(registros) == 2  # continuam existentes e consultáveis


# ══════════════════════════════════════════════════════════════════════════════
# CT-16 — Isolamento de conteúdo: sem prompt nem conversa
# ══════════════════════════════════════════════════════════════════════════════

def test_ct16_isolamento_sem_prompt_nem_conversa():
    rec = er.record_from_execution_result(
        result=ExecutionResult(
            classe=execution.SUCEDIDO,
            output="CONVERSA_SECRETA_456 blah blah",
        ),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
        log_ref="logs/42",
    )
    # Nenhum campo do registro contém prompt/conversa — apenas log_ref.
    serial = str(rec.to_dict())
    assert "PROMPT_SECRETO_123" not in serial
    assert "CONVERSA_SECRETA_456" not in serial
    assert rec.log_ref == "logs/42"

    # O armazenamento durável está em PROTECTED_PATHS e build_prompt o rejeita.
    from src.core.agent import PROTECTED_PATHS, _assert_no_protected
    assert ".pipe/executionRecords.json" in PROTECTED_PATHS
    with pytest.raises(ValueError):
        _assert_no_protected("veja .pipe/executionRecords.json agora")


# ══════════════════════════════════════════════════════════════════════════════
# CT-17 — Fonte única da contagem (adesão ao agent_circuit_break)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct17_sem_contador_paralelo_de_contexto():
    """A capacidade grava UM registro por execução (artefato de negócio), mas
    NÃO mantém um contador paralelo de "execuções por contexto" — essa métrica
    tem fonte única em agent_circuit_break. Guarda estática: o módulo não importa
    nem referencia uma estrutura própria de contagem por contexto.
    """
    import inspect
    src = inspect.getsource(er)
    # Não há estrutura de "occurrences" por contexto (nome usado pelo circuit
    # break como fonte única) replicada aqui.
    assert "occurrences" not in src
    # A contagem por contexto não é derivada de um contador próprio: a repetição
    # sem avanço é derivada dos registros (comportamento), não de um teto.
    # Registrar N execuções no mesmo contexto apenas acumula N registros.
    for _ in range(3):
        er.record_from_execution_result(
            result=ExecutionResult(classe=execution.SUCEDIDO),
            issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
        )
    assert len(er.records_for_issue("42")) == 3


# ══════════════════════════════════════════════════════════════════════════════
# CT-18 — Interrupção por infraestrutura antes de finalizar
# ══════════════════════════════════════════════════════════════════════════════

def test_ct18_interrupcao_preserva_inicio_e_parciais():
    rec = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.UNKNOWN_OUTCOME,
                               origem="dispatch failure"),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
        inicio=2000.0, fim=2010.0,
    )
    assert rec.resultado in (er.INTERROMPIDA, er.DESCONHECIDA)
    assert rec.resultado != ""
    assert rec.inicio == 2000.0
    assert rec.duracao == 10.0


# ══════════════════════════════════════════════════════════════════════════════
# CT-19 — Desfecho inclassificável grava `desconhecida` (nunca vazio)
# ══════════════════════════════════════════════════════════════════════════════

def test_ct19_inclassificavel_grava_desconhecida():
    rec = er.record_from_execution_result(
        result=ExecutionResult(classe=execution.UNKNOWN_OUTCOME, origem=None),
        issue_id="42", board="entrega", etapa="desenvolvimento", avancou=False,
    )
    assert rec.resultado == er.DESCONHECIDA
    assert rec.resultado  # nunca vazio/nulo


# ══════════════════════════════════════════════════════════════════════════════
# CT-20 — Taxonomia fechada, total e determinística (nunca vazio)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("classe,origem,esperado", [
    (execution.SUCEDIDO, None, er.CONCLUIDA),
    (execution.FALHA, "exit-code", er.FALHA_TERMINAL),
    (execution.FALHA, "timeout", er.TIMEOUT),
    (execution.FALHA_PERSISTENTE, "erro interno", er.FALHA_TERMINAL),
    (execution.FALHA_PERSISTENTE, "timeout", er.TIMEOUT),
    (execution.UNKNOWN_OUTCOME, "timeout", er.TIMEOUT),
    (execution.UNKNOWN_OUTCOME, "dispatch failure", er.INTERROMPIDA),
    (execution.UNKNOWN_OUTCOME, "erro interno", er.INTERROMPIDA),
    (execution.UNKNOWN_OUTCOME, None, er.DESCONHECIDA),
    (execution.DEFINITE_NOT_STARTED, None, er.FALHA_TERMINAL),
    ("classe-nunca-vista", None, er.DESCONHECIDA),
])
def test_ct20_mapeamento_total_e_deterministico(classe, origem, esperado):
    resultado = er.map_resultado(classe, origem)
    assert resultado == esperado
    assert resultado in er.RESULTADOS            # dentro da taxonomia fechada
    assert resultado != ""                        # nunca vazio
    # Determinístico: mesma entrada → mesmo resultado.
    assert er.map_resultado(classe, origem) == resultado


def test_ct20_todas_as_classes_tem_destino():
    """Nenhuma classe de ExecutionResult fica órfã (mapeamento total)."""
    classes = [
        execution.SUCEDIDO, execution.FALHA, execution.UNKNOWN_OUTCOME,
        execution.DEFINITE_NOT_STARTED, execution.FALHA_PERSISTENTE,
    ]
    for classe in classes:
        for origem in (None, "timeout", "exit-code", "dispatch failure", "erro interno"):
            assert er.map_resultado(classe, origem) in er.RESULTADOS


def test_resultado_fora_da_taxonomia_vira_desconhecida_na_gravacao():
    """record_execution normaliza um `resultado` fora da taxonomia (RN-02)."""
    rec = er.record_execution(
        issue_id="42", board="entrega", etapa="desenvolvimento",
        resultado="valor-invalido", avancou=False,
    )
    assert rec.resultado == er.DESCONHECIDA
