"""Integração: gravação do registro ao FIM de `call_agent` (issue #307).

Prova que o registro de negócio nasce no ponto de execução do motor, em QUALQUER
desfecho (CA-1), com o avanço observado de forma independente do resultado
(RN-01) e aderindo à fonte única de contagem (CT-17: não há contador paralelo de
contexto — há um registro por execução).

Convenções (test-cases.md): offline; `monkeypatch.chdir(tmp_path)` autouse;
dispatch espião substitui `_dispatch_with_recovery` para devolver um
`ExecutionResult` controlado SEM executar kiro-cli. O símbolo sob teste (a
gravação do registro em `call_agent`) NÃO é mockado — roda de verdade. Os
guardas de composição/steering e o adapter são neutralizados por serem
pré-condições de ambiente, não o objeto do teste.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import execution  # noqa: E402
from src.core import execution_record as er  # noqa: E402
from src.core.execution import ExecutionResult  # noqa: E402


BOARD_ID = "entrega"
COL_ID = "desenvolvimento"


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pipe").mkdir(exist_ok=True)
    yield


def _config():
    return {
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": {
                "base": "main",
                "feature": {"prefix": "feature/", "create": "main",
                            "merge": "main", "branch_pattern": "feature/{id}-{slug}"},
            },
        },
        "agents": {
            "kiro-cli": {"dev": {"name": "engineering", "model": "claude-sonnet-4"}},
        },
    }


def _task(tmp_path, *, parent=None, col_id=COL_ID):
    issue_dir = tmp_path / ".pipe" / "boards" / BOARD_ID / col_id
    issue_dir.mkdir(parents=True, exist_ok=True)
    body_path = issue_dir / "42-my-feature-body.md"
    body_path.write_text("# My Feature\n\nDescrição.\n", encoding="utf-8")
    return {
        "board_id": BOARD_ID,
        "board": {"flow": "feature", "repo": "main"},
        "col_id": col_id,
        "column": {
            "name": "Desenvolvimento", "agent": "dev", "gitevents": "no-branch",
            "target-prompt": "Execute", "change": {"advance": "execucao-testes"},
        },
        "issue": {"id": "42", "body_path": str(body_path), "parent": parent},
    }


def _run_call_agent(m, config, task, result):
    """Executa call_agent com dispatch espião devolvendo `result`.

    Neutraliza as pré-condições de ambiente (compose/steering/circuit-break) que
    não são o objeto do teste; o ESPIÃO é apenas o dispatch, e a gravação do
    registro roda de verdade.
    """
    spy = MagicMock(return_value=result)
    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record",
                      return_value={"instrucoes_obrigatorias_carregadas": True}), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery", spy):
        ret = m.call_agent(config, task)
    return ret, spy


# ══════════════════════════════════════════════════════════════════════════════
# CT-01 (orquestrador) — concluída sem avanço: body permanece na coluna
# ══════════════════════════════════════════════════════════════════════════════

def test_call_agent_grava_concluida_sem_avanco(tmp_path):
    import src.__main__ as m
    task = _task(tmp_path)
    # body_path CONTINUA existindo (agente não moveu) → avancou=False.
    _run_call_agent(m, _config(), task,
                    ExecutionResult(classe=execution.SUCEDIDO))

    registros = er.records_for_issue("42")
    assert len(registros) == 1              # exatamente um registro (CA-1)
    assert registros[0].resultado == er.CONCLUIDA
    assert registros[0].avancou is False
    assert registros[0].board == BOARD_ID
    assert registros[0].etapa == COL_ID
    # Consumo indisponível (kiro-cli não expõe tokens) — comportamento correto.
    assert registros[0].consumo.disponibilidade == er.INDISPONIVEL


# ══════════════════════════════════════════════════════════════════════════════
# CT-02 (orquestrador) — interrompida com avanço prévio: body foi movido
# ══════════════════════════════════════════════════════════════════════════════

def test_call_agent_grava_interrompida_com_avanco(tmp_path):
    import src.__main__ as m
    task = _task(tmp_path)

    # Dispatch espião que SIMULA o avanço: move o body para a coluna de destino
    # (como o agente faria ao concluir a etapa), e devolve um desfecho ambíguo.
    def _spy(config, adapter, params, board_id, col_id):
        body = Path(task["issue"]["body_path"])
        dest = tmp_path / ".pipe" / "boards" / BOARD_ID / "execucao-testes"
        dest.mkdir(parents=True, exist_ok=True)
        body.rename(dest / body.name)   # avança de etapa
        return ExecutionResult(classe=execution.UNKNOWN_OUTCOME,
                               origem="dispatch failure")

    with patch.object(m, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(m, "ensure_steering_integrity", return_value=False), \
         patch.object(m, "compose_execution_record",
                      return_value={"instrucoes_obrigatorias_carregadas": True}), \
         patch.object(m, "_admit_circuit_break", return_value=True), \
         patch.object(m, "_dispatch_with_recovery", side_effect=_spy):
        m.call_agent(_config(), task)

    registros = er.records_for_issue("42")
    assert len(registros) == 1
    assert registros[0].resultado == er.INTERROMPIDA
    assert registros[0].avancou is True     # independente do resultado (RN-01)


# ══════════════════════════════════════════════════════════════════════════════
# CA-1 — registro criado em QUALQUER desfecho (falha terminal)
# ══════════════════════════════════════════════════════════════════════════════

def test_call_agent_grava_em_falha_terminal(tmp_path):
    import src.__main__ as m
    task = _task(tmp_path)
    _run_call_agent(m, _config(), task,
                    ExecutionResult(classe=execution.FALHA, origem="exit-code"))
    registros = er.records_for_issue("42")
    assert len(registros) == 1
    assert registros[0].resultado == er.FALHA_TERMINAL


def test_call_agent_grava_mesmo_com_result_none(tmp_path):
    """Adapter honrando o contrato antigo (execute->None): registro concluído."""
    import src.__main__ as m
    task = _task(tmp_path)
    _run_call_agent(m, _config(), task, None)
    registros = er.records_for_issue("42")
    assert len(registros) == 1
    assert registros[0].resultado == er.CONCLUIDA


# ══════════════════════════════════════════════════════════════════════════════
# issue_parent capturado NA execução (base durável da linhagem — RN-06)
# ══════════════════════════════════════════════════════════════════════════════

def test_call_agent_captura_issue_parent(tmp_path):
    import src.__main__ as m
    task = _task(tmp_path, parent="100")
    _run_call_agent(m, _config(), task,
                    ExecutionResult(classe=execution.SUCEDIDO))
    registros = er.records_for_issue("42")
    assert registros[0].issue_parent == "100"


# ══════════════════════════════════════════════════════════════════════════════
# CT-16 — registro não replica prompt/conversa (isolamento)
# ══════════════════════════════════════════════════════════════════════════════

def test_call_agent_registro_sem_prompt_nem_conversa(tmp_path):
    import src.__main__ as m
    task = _task(tmp_path)
    _run_call_agent(
        m, _config(), task,
        ExecutionResult(classe=execution.SUCEDIDO,
                        output="CONVERSA_SECRETA_456 ..."),
    )
    registros = er.records_for_issue("42")
    serial = str(registros[0].to_dict())
    assert "CONVERSA_SECRETA_456" not in serial
    # No máximo uma referência lógica ao log detalhado.
    assert registros[0].log_ref == "logs/42"


# ══════════════════════════════════════════════════════════════════════════════
# CT-17 — fonte única: um registro por execução, sem contador paralelo
# ══════════════════════════════════════════════════════════════════════════════

def test_call_agent_um_registro_por_execucao(tmp_path):
    import src.__main__ as m
    config = _config()
    # 3 entregas no mesmo contexto → 3 registros (artefato por execução), NÃO um
    # contador paralelo de "execuções por contexto" (essa métrica é do
    # agent_circuit_break).
    for _ in range(3):
        task = _task(tmp_path)
        _run_call_agent(m, config, task,
                        ExecutionResult(classe=execution.SUCEDIDO))
    assert len(er.records_for_issue("42")) == 3


# ══════════════════════════════════════════════════════════════════════════════
# Consumo medido (stream-json) é gravado no registro — RN-04
# ══════════════════════════════════════════════════════════════════════════════

def test_call_agent_grava_consumo_reportado_do_result(tmp_path):
    """O consumo medido pelo adapter (ExecutionResult.consumo) chega ao registro.

    Prova o wiring de `_write_execution_record`: quando o result carrega um
    consumo disponível (meteringUsage parseado do stream-json), o registro o
    preserva com valor/unidade/origem — em vez do antigo `indisponível` fixo.
    """
    import src.__main__ as m
    task = _task(tmp_path)
    result = ExecutionResult(classe=execution.SUCEDIDO)
    result.consumo = er.Consumo.reportado(1.23, "credit", "kiro-cli")
    _run_call_agent(m, _config(), task, result)

    registros = er.records_for_issue("42")
    assert len(registros) == 1
    consumo = registros[0].consumo
    assert consumo.disponibilidade == er.DISPONIVEL
    assert consumo.valor == 1.23
    assert consumo.unidade == "credit"
    assert consumo.origem == "kiro-cli"
