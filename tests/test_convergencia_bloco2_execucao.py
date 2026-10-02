"""Convergência do bloco 2 (#315 / CT-04): #306 × #307 no MESMO `call_agent`.

Fecha a lacuna registrada na verificação do bloco 2 (CT-02): a suíte existente
exercita cada entrega isoladamente com o boundary da outra mockado —
`tests/test_execution_record_integration.py` sempre força
`_admit_circuit_break -> True`, e os testes de `tests/test_agent_circuit_break.py`
que chegam ao fluxo não verificam a gravação do registro (#307). Nenhum teste
hoje exercita as DUAS políticas reais, juntas, dentro do mesmo `call_agent`.

Este é o ÚNICO artefato de código desta verificação (CA-6 da issue #315). É um
teste de regressão da convergência: comprova que o limitador de reexecuções
(#306, via `_admit_circuit_break`) e o registro de execução (#307, via
`_write_execution_record`) permanecem efetivos EM CONJUNTO no ponto de decisão
`src/__main__.py::call_agent`, sem que um mascare o efeito do outro. Não amplia
o escopo de #306 nem de #307.

Isolamento (lição do incidente #106): é PROIBIDO fazer `monkeypatch` dos
símbolos sob teste (`_admit_circuit_break`, `_write_execution_record`, o núcleo
de `CircuitBreaker.admit` ou de `record_from_execution_result`). Os patches são
permitidos APENAS nas fronteiras reais de ambiente/execução:

- `KiroCliAgent`    — adapter de subprocesso (não instanciar o real);
- `ensure_steering_integrity` — guarda de ambiente (retorna False);
- `compose_execution_record`  — pré-condição de #308, já coberta por seus
  próprios testes; aqui neutralizada como ambiente (o objeto é a dupla
  #306×#307, não a composição);
- `_dispatch_with_recovery`   — espião do subprocesso, devolve um
  `ExecutionResult` controlado e registra se foi chamado.

O estado real do limitador (`.pipe/agentCircuitBreak.json`) e do registro de
execução (`.pipe/executionRecords.json`) é exercitado de verdade sobre o
`tmp_path` isolado. O relógio é o `time.time` real: a janela usada (3600s) é
muito maior que a duração do teste, então todas as ocorrências ficam dentro da
janela sem necessidade de `sleep`.
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
ISSUE_ID = "42"


# ══════════════════════════════════════════════════════════════════════════════
# Board fake espião com capacidade REAL de label (o limitador precisa aplicar
# need_human no caminho de bloqueio). Mesmo contrato de `FakeBoard` em
# tests/test_agent_circuit_break.py, para o `trip` do #306 ter efeito real.
# ══════════════════════════════════════════════════════════════════════════════

class FakeBoard:
    def __init__(self):
        self.labels: dict[tuple[str, str], set[str]] = {}
        self.added_comments: list[dict] = []
        self._comments: dict[tuple[str, str], list[dict]] = {}

    def _key(self, board_id, issue_id):
        return (str(board_id), str(issue_id))

    def add_label(self, board_id, issue_id, label):
        self.labels.setdefault(self._key(board_id, issue_id), set()).add(label)

    def set_labels(self, board_id, issue_id, labels):
        self.labels[self._key(board_id, issue_id)] = set(labels)

    def remove_label(self, board_id, issue_id, label):
        self.labels.get(self._key(board_id, issue_id), set()).discard(label)

    def add_comment(self, board_id, issue_id, comment):
        key = self._key(board_id, issue_id)
        self.added_comments.append({"key": key, "body": comment})
        self._comments.setdefault(key, []).append({"body": comment})

    def list_comments(self, board_id, issue_id):
        return list(self._comments.get(self._key(board_id, issue_id), []))

    def has_need_human(self, board_id, issue_id) -> bool:
        return "need_human" in self.labels.get(self._key(board_id, issue_id), set())


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Isola `.pipe/` por teste (chdir) e injeta o board fake no módulo.

    O `board` é o global de `src/__main__.py` que `_admit_circuit_break` usa ao
    construir o `CircuitBreaker`; sem capacidade real de label, o caminho de
    bloqueio do #306 não teria efeito. Restaura o valor original ao final.
    """
    import src.__main__ as pipe
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pipe").mkdir(exist_ok=True)
    original_board = pipe.board
    pipe.board = FakeBoard()
    yield
    pipe.board = original_board


def _config(*, executions=3, window=3600, circuit_break=True):
    config = {
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
    if circuit_break:
        config["agent_circuit_break"] = {"executions": executions, "window": window}
    return config


def _task(tmp_path, *, col_id=COL_ID, need_human=False):
    issue_dir = tmp_path / ".pipe" / "boards" / BOARD_ID / col_id
    issue_dir.mkdir(parents=True, exist_ok=True)
    body_path = issue_dir / f"{ISSUE_ID}-my-feature-body.md"
    body = "# My Feature\n\nDescrição.\n"
    if need_human:
        body += "\n@---\n/need_human\n"
    body_path.write_text(body, encoding="utf-8")
    return {
        "board_id": BOARD_ID,
        "board": {"flow": "feature", "repo": "main"},
        "col_id": col_id,
        "column": {
            "name": "Desenvolvimento", "agent": "dev", "gitevents": "no-branch",
            "target-prompt": "Execute", "change": {"advance": "execucao-testes"},
        },
        "issue": {"id": ISSUE_ID, "body_path": str(body_path), "parent": None},
    }


def _run_call_agent(pipe, config, task, result, *, compose_ok=True):
    """Executa `call_agent` com SÓ as fronteiras de ambiente controladas.

    `_admit_circuit_break` (#306) e `_write_execution_record` (#307) NÃO são
    mockados — rodam de verdade. O espião é apenas o dispatch do subprocesso.
    Retorna (ret, spy) para inspeção de "o agente foi despachado?".
    """
    spy = MagicMock(return_value=result)
    compose_ret = {"instrucoes_obrigatorias_carregadas": compose_ok}
    if not compose_ok:
        compose_ret["motivo"] = "steering ausente (simulado)"
    with patch.object(pipe, "KiroCliAgent", return_value=MagicMock()), \
         patch.object(pipe, "ensure_steering_integrity", return_value=False), \
         patch.object(pipe, "compose_execution_record", return_value=compose_ret), \
         patch.object(pipe, "_dispatch_with_recovery", spy):
        ret = pipe.call_agent(config, task)
    return ret, spy


# ══════════════════════════════════════════════════════════════════════════════
# CT-04a — Dentro do limite: admissão real conta a entrega E o registro de
# execução real é gravado (as duas fontes avançam juntas).
# ══════════════════════════════════════════════════════════════════════════════

def test_ct04a_dentro_do_limite_admite_e_grava_registro(tmp_path):
    import src.__main__ as pipe
    from src.core import agent_circuit_break as acb

    config = _config(executions=3, window=3600)
    task = _task(tmp_path)

    _, spy = _run_call_agent(pipe, config, task,
                             ExecutionResult(classe=execution.SUCEDIDO))

    # (#306) a entrega foi despachada (admissão passou) ...
    assert spy.called, "dentro do limite o dispatch deve ocorrer"
    # ... e contada pelo limitador (uma ocorrência no contexto).
    state = acb.load_state()
    ctx = state["active_contexts"][f"{BOARD_ID}/{ISSUE_ID}"]
    assert len(ctx["occurrences"]) == 1, "a admissão conta exatamente uma entrega"
    assert ctx["trip"] is None, "sem bloqueio dentro do limite"

    # (#307) exatamente um registro de execução foi gravado, coerente.
    registros = er.records_for_issue(ISSUE_ID)
    assert len(registros) == 1
    assert registros[0].resultado == er.CONCLUIDA
    assert registros[0].board == BOARD_ID
    assert registros[0].etapa == COL_ID
    # Nenhum bloqueio: need_human NÃO aplicado.
    assert not pipe.board.has_need_human(BOARD_ID, ISSUE_ID)


# ══════════════════════════════════════════════════════════════════════════════
# CT-04b — Limite atingido: admissão real BLOQUEIA e nenhum registro de execução
# é gravado para a tentativa excedente (o limitador não é mascarado por #307).
# ══════════════════════════════════════════════════════════════════════════════

def test_ct04b_limite_bloqueia_e_nao_grava_registro_excedente(tmp_path):
    import src.__main__ as pipe
    from src.core import agent_circuit_break as acb

    config = _config(executions=3, window=3600)

    # Semeia 3 ocorrências REAIS via 3 chamadas prévias de call_agent (mesmo
    # contexto, dentro da janela). Cada uma admite, despacha e grava um registro.
    for _ in range(3):
        task = _task(tmp_path)
        _, spy = _run_call_agent(pipe, config, task,
                                 ExecutionResult(classe=execution.SUCEDIDO))
        assert spy.called

    assert len(er.records_for_issue(ISSUE_ID)) == 3
    state = acb.load_state()
    assert len(state["active_contexts"][f"{BOARD_ID}/{ISSUE_ID}"]["occurrences"]) == 3

    # 4ª chamada: EXCEDENTE. A admissão (#306) deve bloquear ANTES do dispatch.
    task = _task(tmp_path)
    ret, spy = _run_call_agent(pipe, config, task,
                               ExecutionResult(classe=execution.SUCEDIDO))

    # (#306) dispatch NÃO ocorre; issue marcada need_human (bloqueio real).
    assert ret is None
    assert not spy.called, "a tentativa excedente não pode despachar o agente"
    assert pipe.board.has_need_human(BOARD_ID, ISSUE_ID)

    # (#307) NENHUM registro novo para a tentativa bloqueada — nada "vaza".
    assert len(er.records_for_issue(ISSUE_ID)) == 3, \
        "tentativa bloqueada não deve gerar registro de execução fantasma"


# ══════════════════════════════════════════════════════════════════════════════
# CT-04c — Falha de composição (#308) bloqueia ANTES do limitador: nem admissão
# (#306) nem registro (#307) ocorrem (ordem de gates preservada).
# ══════════════════════════════════════════════════════════════════════════════

def test_ct04c_falha_composicao_bloqueia_antes_do_limitador_e_do_registro(tmp_path):
    import src.__main__ as pipe
    from src.core import agent_circuit_break as acb

    config = _config(executions=3, window=3600)
    task = _task(tmp_path)

    ret, spy = _run_call_agent(pipe, config, task,
                               ExecutionResult(classe=execution.SUCEDIDO),
                               compose_ok=False)

    # Retorna no gate de #308, antes de tudo.
    assert ret is None
    assert not spy.called, "dispatch não ocorre quando a composição recusa"

    # (#306) o limitador NÃO contou a tentativa (estado não criado).
    state = acb.load_state()
    assert f"{BOARD_ID}/{ISSUE_ID}" not in state["active_contexts"], \
        "o limitador não deve contar quando a composição recusa antes dele"
    assert not pipe.board.has_need_human(BOARD_ID, ISSUE_ID)

    # (#307) nenhum registro de execução gravado.
    assert er.records_for_issue(ISSUE_ID) == []


# ══════════════════════════════════════════════════════════════════════════════
# CT-04d — Classificação (#307) reflete fielmente o desfecho mesmo com o
# limitador (#306) ativo e dentro do limite (uma entrega não distorce a outra).
# ══════════════════════════════════════════════════════════════════════════════

def test_ct04d_classificacao_fiel_com_limitador_ativo_dentro_do_limite(tmp_path):
    import src.__main__ as pipe
    from src.core import agent_circuit_break as acb

    # Janela ampla e N alto para as três entregas ficarem SEMPRE dentro do limite.
    config = _config(executions=5, window=3600)

    casos = [
        (ExecutionResult(classe=execution.SUCEDIDO), er.CONCLUIDA),
        (ExecutionResult(classe=execution.UNKNOWN_OUTCOME,
                         origem="dispatch failure"), er.INTERROMPIDA),
        (ExecutionResult(classe=execution.FALHA, origem="exit-code"),
         er.FALHA_TERMINAL),
    ]

    for i, (result, _esperado) in enumerate(casos, start=1):
        task = _task(tmp_path)
        _, spy = _run_call_agent(pipe, config, task, result)
        assert spy.called, "cada entrega dentro do limite deve despachar"
        # Cada entrega é contada pelo limitador (dentro do limite, sem bloqueio).
        state = acb.load_state()
        ctx = state["active_contexts"][f"{BOARD_ID}/{ISSUE_ID}"]
        assert len(ctx["occurrences"]) == i
        assert ctx["trip"] is None

    # (#307) cada registro reflete fielmente a classificação do seu desfecho —
    # a presença do limitador ativo não altera nem atrasa a classificação.
    registros = er.records_for_issue(ISSUE_ID)
    assert len(registros) == 3
    assert [r.resultado for r in registros] == [c[1] for c in casos]
