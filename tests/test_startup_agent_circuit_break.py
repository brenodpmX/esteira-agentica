"""CT-18: política ativa + adaptador sem capacidade de label → falha na init.

Com `agent_circuit_break` ativo, aplicar `need_human` precisa ter efeito real.
Um adaptador que herda a implementação padrão no-op de `BoardPort.add_label`/
`set_labels` faria a sinalização de bloqueio parecer aplicada sem efeito — isso
deve provocar falha na inicialização, nunca aparentar que sinalizou.

A QA fixa o COMPORTAMENTO (falha vs. passa), não o mecanismo. A detecção compara
os métodos da instância com os de `BoardPort` (default herdado = sem capacidade).
"""

import pytest

from src.core.board import BoardPort
from src.core.agent_circuit_break import (
    adapter_can_apply_label,
    check_label_capability,
    CircuitBreakStateError,
)


# ─── Adaptadores de teste ─────────────────────────────────────────────────────

class _NoLabelAdapter(BoardPort):
    """Herda os defaults no-op de add_label/set_labels (sem capacidade real)."""

    def connect(self, config): ...
    def sync_boards(self, boards): ...
    def list_issues(self, board_id): return []
    def get_issue(self, board_id, issue_id, fullsync=False): return None
    def create_issue(self, board_id, title, body, column): ...
    def move_issue(self, board_id, issue_id, column, from_column=None): ...
    def update_issue(self, board_id, issue_id, title=None, body=None): ...
    def add_comment(self, board_id, issue_id, comment): ...
    def list_comments(self, board_id, issue_id): return []
    def close_issue(self, board_id, issue_id): ...


class _WithLabelAdapter(_NoLabelAdapter):
    """Sobrescreve a aplicação de label (capacidade real)."""

    def add_label(self, board_id, issue_id, label):  # noqa: D401
        pass

    def set_labels(self, board_id, issue_id, labels):
        pass


def _config(active: bool) -> dict:
    if active:
        return {"agent_circuit_break": {"executions": 3, "window": 3600}}
    return {"sleep": 60}


# ─── adapter_can_apply_label ──────────────────────────────────────────────────

class TestAdapterCapability:
    def test_sem_capacidade_detectado(self):
        assert adapter_can_apply_label(_NoLabelAdapter()) is False

    def test_com_capacidade_detectado(self):
        assert adapter_can_apply_label(_WithLabelAdapter()) is True

    def test_adaptador_real_github_tem_capacidade(self):
        from src.adapters.github_board import GitHubBoardAdapter
        assert adapter_can_apply_label(GitHubBoardAdapter()) is True


# ─── check_label_capability (gate de init) ────────────────────────────────────

class TestCheckLabelCapability:
    def test_politica_ativa_sem_label_falha(self):
        with pytest.raises(CircuitBreakStateError, match="capacidade real de aplicar label"):
            check_label_capability(_config(active=True), _NoLabelAdapter())

    def test_politica_ativa_com_label_passa(self):
        check_label_capability(_config(active=True), _WithLabelAdapter())  # no-op

    def test_politica_ativa_adaptador_real_passa(self):
        from src.adapters.github_board import GitHubBoardAdapter
        check_label_capability(_config(active=True), GitHubBoardAdapter())

    def test_sem_politica_nao_falha_mesmo_sem_label(self):
        # Mecanismo desligado: a ausência de capacidade de label não falha a init.
        check_label_capability(_config(active=False), _NoLabelAdapter())  # no-op
