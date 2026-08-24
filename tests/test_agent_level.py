"""Testes do comando /agent-hub-<valor> e do roteamento de agente (agent-hub).

Regra atual:
    - O `agent_hub` é armazenado como label `agent-hub-<valor>` no GitHub.
    - `agent_hub()` lê `issue["labels"]` (não o arquivo body).
    - `resolve_agent_id()` usa o valor extraído das labels para selecionar o
      agente via mapa `agent-hub` da coluna; sem match, usa o `agent` default.
    - O sufixo é livre (ex.: low, senior, deep), não apenas níveis.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.commands import split_body, serialize_commands, parse_commands
from src.core.agent import agent_hub, resolve_agent_id


# ── parse / serialize ─────────────────────────────────────────────────────────

def test_parse_agent_hub():
    cmds = parse_commands("/agent-hub-high")
    assert cmds.agent_hub == "high"


def test_parse_agent_hub_valor_livre():
    """O sufixo é livre — não se limita a low/medium/high."""
    cmds = parse_commands("/agent-hub-senior")
    assert cmds.agent_hub == "senior"


def test_parse_effort_nao_e_reconhecido():
    """O token /effort não deve preencher agent_hub."""
    cmds = parse_commands("/effort high")
    assert cmds.agent_hub is None


def test_serialize_agent_hub():
    cmds = parse_commands("/agent-hub-medium")
    assert "/agent-hub-medium" in serialize_commands(cmds)


def test_roundtrip_agent_hub():
    _, cmds = split_body("corpo\n\n@---\n/agent-hub-low\n/labels x")
    assert cmds.agent_hub == "low"
    assert cmds.labels == ["x"]


# ── resolução de agente ───────────────────────────────────────────────────────

def _issue_with_labels(labels: list) -> dict:
    """Cria um dict de issue (formato snapshot) com as labels fornecidas."""
    return {"labels": list(labels), "body_path": ""}


def test_agent_hub_le_de_labels():
    """agent_hub() lê issue['labels'], não o arquivo body."""
    issue = _issue_with_labels(["agent-hub-high"])
    assert agent_hub(issue) == "high"


def test_agent_hub_retorna_none_sem_label():
    """Sem label agent-hub-*, agent_hub retorna None (mesmo com /agent-hub no body)."""
    issue = _issue_with_labels([])
    assert agent_hub(issue) is None


def test_agent_hub_ignora_body_quando_sem_label(tmp_path):
    """Body com /agent-hub-<valor> não alimenta agent_hub() — só labels do board."""
    body = tmp_path / "1-x-body.md"
    body.write_text("# titulo\n\n@---\n/agent-hub-high\n", encoding="utf-8")
    issue = {"labels": [], "body_path": str(body)}
    # Sem a label no board, retorna None (não lê o body)
    assert agent_hub(issue) is None


def test_resolve_usa_hub_quando_valor_mapeado():
    col = {"agent": "engineering", "agent-hub": {"high": "senior", "low": "generic"}}
    issue = _issue_with_labels(["agent-hub-high"])
    assert resolve_agent_id(col, issue) == "senior"


def test_resolve_cai_no_default_sem_label_de_hub():
    """Sem label agent-hub-*, resolve_agent_id retorna o agente default."""
    col = {"agent": "engineering", "agent-hub": {"high": "senior"}}
    issue = _issue_with_labels(["backend", "security"])
    assert resolve_agent_id(col, issue) == "engineering"


def test_resolve_cai_no_default_quando_valor_nao_mapeado():
    """Label agent-hub-medium sem entrada no mapa agent-hub → default."""
    col = {"agent": "engineering", "agent-hub": {"high": "senior"}}
    issue = _issue_with_labels(["agent-hub-medium"])
    assert resolve_agent_id(col, issue) == "engineering"


def test_resolve_sem_hub_usa_default():
    """Coluna sem mapa agent-hub ignora qualquer valor e retorna o default."""
    col = {"agent": "engineering"}
    issue = _issue_with_labels(["agent-hub-high"])
    assert resolve_agent_id(col, issue) == "engineering"
