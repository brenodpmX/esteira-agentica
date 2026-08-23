"""Casos de teste para: persistir agent_hub via label
agent-hub-<valor> no GitHub.

Refatoração: Persistir `agent_hub` via label `agent-hub-<valor>` no GitHub.
O sufixo é livre (nível, função, profundidade etc.), não apenas low/medium/high.

Estes testes cobrem o comportamento esperado:

1. `from_issue()` extrai agent_hub a partir de labels `agent-hub-*`.
2. Labels `agent-hub-*` são excluídas do conjunto gerenciado por `/labels`
   (não sobrescritas pela semântica SET, análogo ao `need_human`).
3. `all_labels()` inclui a label `agent-hub-*` na lista gerenciada.
4. `agent_hub()` em `agent.py` lê diretamente `issue["labels"]` (campo do
   snapshot/dict) em vez de parsear o arquivo body.
5. `resolve_agent_id()` usa o valor extraído de labels para escolher o agente.
6. Round-trip board → `from_issue` → arquivo preserva agent_hub via label.
7. Múltiplas labels `agent-hub-*` → apenas o último/único valor é considerado
   (comportamento defensivo).
8. Label `agent-hub-*` não aparece em `/labels` no `serialize_commands`.
9. A lógica de `all_labels()` emite a label `agent-hub-<valor>` para o board
   (necessário para o sync-up gravar a label corretamente).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.commands import (
    IssueCommands,
    from_issue,
    parse_commands,
    serialize_commands,
    split_body,
    compose_body,
)
from src.core.agent import agent_hub, resolve_agent_id

# ══════════════════════════════════════════════════════════════════════════════
# Prefixo canônico
# ══════════════════════════════════════════════════════════════════════════════

AGENT_HUB_PREFIX = "agent-hub-"


def _make_issue(labels: list[str], **kwargs):
    """Cria um objeto Issue-like mínimo com as labels fornecidas."""
    issue = MagicMock()
    issue.labels = list(labels)
    issue.parent = kwargs.get("parent", None)
    issue.children = kwargs.get("children", [])
    issue.blocked_by = kwargs.get("blocked_by", [])
    issue.blocks = kwargs.get("blocks", [])
    return issue


def _make_issue_dict(labels: list[str], body_path: str = "") -> dict:
    """Cria um dict de issue (formato snapshot) com as labels fornecidas."""
    return {
        "labels": list(labels),
        "body_path": body_path,
        "id": "99",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 1. from_issue() extrai agent_hub a partir de labels agent-hub-*
# ══════════════════════════════════════════════════════════════════════════════

def test_from_issue_extrai_agent_hub_high():
    """from_issue deve popular agent_hub quando a label agent-hub-high existe."""
    issue = _make_issue(["backend", "agent-hub-high", "security"])
    cmds = from_issue(issue)
    assert cmds.agent_hub == "high"


def test_from_issue_extrai_agent_hub_low():
    issue = _make_issue(["agent-hub-low"])
    cmds = from_issue(issue)
    assert cmds.agent_hub == "low"


def test_from_issue_extrai_agent_hub_valor_livre():
    """O sufixo é livre — ex.: agent-hub-senior."""
    issue = _make_issue(["agent-hub-senior", "backend"])
    cmds = from_issue(issue)
    assert cmds.agent_hub == "senior"


def test_from_issue_sem_label_agent_hub_retorna_none():
    """Sem label agent-hub-*, agent_hub deve ser None."""
    issue = _make_issue(["backend", "security"])
    cmds = from_issue(issue)
    assert cmds.agent_hub is None


def test_from_issue_label_agent_hub_nao_aparece_em_labels():
    """A label agent-hub-* não deve aparecer em cmds.labels após from_issue."""
    issue = _make_issue(["backend", "agent-hub-high", "security"])
    cmds = from_issue(issue)
    for lbl in cmds.labels:
        assert not lbl.startswith(AGENT_HUB_PREFIX), (
            f"Label '{lbl}' não deve aparecer em cmds.labels"
        )


def test_from_issue_labels_normais_preservadas():
    """Labels comuns não devem ser afetadas pelo filtro de agent-hub-*."""
    issue = _make_issue(["backend", "agent-hub-senior", "security"])
    cmds = from_issue(issue)
    assert "backend" in cmds.labels
    assert "security" in cmds.labels
    assert len([l for l in cmds.labels if not l.startswith(AGENT_HUB_PREFIX)]) == 2


# ══════════════════════════════════════════════════════════════════════════════
# 2. all_labels() inclui a label agent-hub-<valor> para sync-up com o board
# ══════════════════════════════════════════════════════════════════════════════

def test_all_labels_inclui_agent_hub_label():
    """all_labels() deve emitir a label agent-hub-<valor> para o board."""
    cmds = IssueCommands(labels=["backend"], agent_hub="high")
    all_lbs = cmds.all_labels()
    assert "agent-hub-high" in all_lbs


def test_all_labels_sem_agent_hub_nao_emite_prefixo():
    """Sem agent_hub definido, all_labels não emite nenhuma label agent-hub-*."""
    cmds = IssueCommands(labels=["backend"])
    all_lbs = cmds.all_labels()
    for lbl in all_lbs:
        assert not lbl.startswith(AGENT_HUB_PREFIX)


def test_all_labels_agent_hub_e_need_human_juntos():
    """all_labels deve emitir tanto need_human quanto agent-hub-<valor>."""
    cmds = IssueCommands(labels=["backend"], agent_hub="low", need_human=True)
    all_lbs = cmds.all_labels()
    assert "need_human" in all_lbs
    assert "agent-hub-low" in all_lbs
    assert "backend" in all_lbs


def test_all_labels_nao_duplica_agent_hub_label():
    """Se o usuário já colocou agent-hub-X em labels, não deve duplicar."""
    cmds = IssueCommands(labels=["agent-hub-high"], agent_hub="high")
    all_lbs = cmds.all_labels()
    assert all_lbs.count("agent-hub-high") == 1


# ══════════════════════════════════════════════════════════════════════════════
# 3. /labels não sobrescreve a label agent-hub-*
# ══════════════════════════════════════════════════════════════════════════════

def test_labels_cmd_nao_remove_agent_hub_via_set():
    """/labels não pode remover a label agent-hub-* (semântica SET limitada).

    O sync-up usa all_labels() para calcular o conjunto final. A label
    agent-hub-* deriva de agent_hub, não de cmds.labels. Portanto, se o
    usuário escrever /labels backend, a label agent-hub-high deve sobreviver
    caso agent_hub == 'high'.
    """
    cmds = IssueCommands(labels=["backend"], agent_hub="high")
    all_lbs = cmds.all_labels()
    # Mesmo com /labels definindo apenas 'backend', agent-hub-high persiste.
    assert "agent-hub-high" in all_lbs
    assert "backend" in all_lbs


def test_parse_labels_nao_popula_agent_hub_diretamente():
    """/labels agent-hub-high não deve preencher cmds.agent_hub.

    A label agent-hub-* só deve ser populada via from_issue (fluxo down)
    ou via /agent-hub-<valor> (fluxo up); não via /labels.
    """
    cmds = parse_commands("/labels agent-hub-high, backend")
    # agent_hub não deve ser preenchido por /labels
    assert cmds.agent_hub is None
    # A label vai para cmds.labels (será filtrada pelo all_labels no momento certo)
    assert "agent-hub-high" in cmds.labels


# ══════════════════════════════════════════════════════════════════════════════
# 4. agent_hub() em agent.py lê de issue["labels"] (não do arquivo body)
# ══════════════════════════════════════════════════════════════════════════════

def test_agent_hub_le_de_labels_no_dict():
    """agent_hub() deve ler issue['labels'] e não o arquivo body."""
    issue = _make_issue_dict(labels=["backend", "agent-hub-high"])
    assert agent_hub(issue) == "high"


def test_agent_hub_le_senior_de_labels():
    issue = _make_issue_dict(labels=["agent-hub-senior"])
    assert agent_hub(issue) == "senior"


def test_agent_hub_retorna_none_sem_label():
    """Sem label agent-hub-*, agent_hub retorna None (não lê mais do body)."""
    issue = _make_issue_dict(labels=["backend", "security"])
    assert agent_hub(issue) is None


def test_agent_hub_ignora_body_path_quando_label_presente(tmp_path):
    """Mesmo que o body tenha /agent-hub-low, se a label diz high, usa high."""
    body = tmp_path / "1-x-body.md"
    body.write_text("# titulo\n\n@---\n/agent-hub-low\n", encoding="utf-8")
    issue = _make_issue_dict(labels=["agent-hub-high"], body_path=str(body))
    # Após refatoração: lê label, não body
    assert agent_hub(issue) == "high"


def test_agent_hub_sem_labels_retorna_none(tmp_path):
    """issue sem labels retorna None."""
    issue = _make_issue_dict(labels=[])
    assert agent_hub(issue) is None


# ══════════════════════════════════════════════════════════════════════════════
# 5. resolve_agent_id() usa valor via label
# ══════════════════════════════════════════════════════════════════════════════

def test_resolve_agent_id_via_label_high():
    col = {"agent": "engineering", "agent-hub": {"high": "senior", "low": "generic"}}
    issue = _make_issue_dict(labels=["agent-hub-high"])
    assert resolve_agent_id(col, issue) == "senior"


def test_resolve_agent_id_via_label_low():
    col = {"agent": "engineering", "agent-hub": {"high": "senior", "low": "generic"}}
    issue = _make_issue_dict(labels=["agent-hub-low"])
    assert resolve_agent_id(col, issue) == "generic"


def test_resolve_agent_id_sem_label_usa_default():
    col = {"agent": "engineering", "agent-hub": {"high": "senior"}}
    issue = _make_issue_dict(labels=["backend"])
    assert resolve_agent_id(col, issue) == "engineering"


def test_resolve_agent_id_valor_nao_mapeado_usa_default():
    col = {"agent": "engineering", "agent-hub": {"high": "senior"}}
    issue = _make_issue_dict(labels=["agent-hub-medium"])
    assert resolve_agent_id(col, issue) == "engineering"


def test_resolve_agent_id_sem_hub_usa_default():
    col = {"agent": "engineering"}
    issue = _make_issue_dict(labels=["agent-hub-high"])
    assert resolve_agent_id(col, issue) == "engineering"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Round-trip board → from_issue → serialize_commands
# ══════════════════════════════════════════════════════════════════════════════

def test_roundtrip_board_to_file_preserva_agent_hub():
    """from_issue → serialize_commands preserva o agent_hub como /agent-hub-<valor>."""
    issue = _make_issue(["backend", "agent-hub-high"])
    cmds = from_issue(issue)
    serialized = serialize_commands(cmds)
    assert "/agent-hub-high" in serialized


def test_roundtrip_nao_serializa_agent_hub_label_em_labels():
    """serialize_commands não deve emitir agent-hub-high em /labels."""
    issue = _make_issue(["backend", "agent-hub-high"])
    cmds = from_issue(issue)
    serialized = serialize_commands(cmds)
    # /labels não deve conter agent-hub-high
    for line in serialized.splitlines():
        if line.startswith("/labels"):
            assert "agent-hub" not in line, (
                f"label agent-hub-* não deve aparecer em /labels: '{line}'"
            )


def test_roundtrip_completo_body_preserva_valor():
    """Ciclo completo: from_issue → compose_body → split_body retorna agent_hub."""
    issue = _make_issue(["backend", "agent-hub-senior", "security"])
    cmds = from_issue(issue)
    body = compose_body("Conteúdo da issue.", cmds)
    _, parsed = split_body(body)
    assert parsed.agent_hub == "senior"


# ══════════════════════════════════════════════════════════════════════════════
# 7. Comportamento defensivo: múltiplas labels agent-hub-*
# ══════════════════════════════════════════════════════════════════════════════

def test_multiplas_labels_agent_hub_usa_primeira_encontrada():
    """Com múltiplas labels agent-hub-*, deve usar uma delas sem crash."""
    issue = _make_issue(["agent-hub-low", "agent-hub-high"])
    cmds = from_issue(issue)
    # Não deve falhar; deve retornar um valor válido
    assert cmds.agent_hub in ("low", "high")


def test_multiplas_labels_agent_hub_dict_usa_uma():
    issue = _make_issue_dict(labels=["agent-hub-low", "agent-hub-medium"])
    value = agent_hub(issue)
    assert value in ("low", "medium")


# ══════════════════════════════════════════════════════════════════════════════
# 8. serialize_commands: /agent-hub-<valor> não gera label em /labels
# ══════════════════════════════════════════════════════════════════════════════

def test_serialize_agent_hub_gera_campo_proprio():
    """serialize_commands emite /agent-hub-<valor> separado, não em /labels."""
    cmds = IssueCommands(labels=["backend"], agent_hub="high")
    serialized = serialize_commands(cmds)
    assert "/agent-hub-high" in serialized
    # /labels deve conter apenas 'backend'
    for line in serialized.splitlines():
        if line.startswith("/labels"):
            assert "agent-hub" not in line


def test_serialize_sem_agent_hub_nao_emite_campo():
    cmds = IssueCommands(labels=["backend"])
    serialized = serialize_commands(cmds)
    assert "/agent-hub" not in serialized


# ══════════════════════════════════════════════════════════════════════════════
# 9. Regressão: need_human não é afetado pela refatoração
# ══════════════════════════════════════════════════════════════════════════════

def test_need_human_nao_interfere_com_agent_hub():
    """need_human e agent_hub coexistem sem interferência."""
    issue = _make_issue(["need_human", "agent-hub-high", "backend"])
    cmds = from_issue(issue)
    assert cmds.need_human is True
    assert cmds.agent_hub == "high"
    assert "backend" in cmds.labels
    # need_human não aparece em cmds.labels
    assert "need_human" not in cmds.labels
    # agent-hub-high não aparece em cmds.labels
    assert "agent-hub-high" not in cmds.labels


def test_all_labels_com_need_human_e_agent_hub():
    """all_labels emite need_human e agent-hub-* corretamente."""
    cmds = IssueCommands(labels=["backend"], agent_hub="medium", need_human=True)
    all_lbs = cmds.all_labels()
    assert "need_human" in all_lbs
    assert "agent-hub-medium" in all_lbs
    assert "backend" in all_lbs
    # agent-hub não aparece também como label normal (não duplicar)
    assert all_lbs.count("agent-hub-medium") == 1


# ══════════════════════════════════════════════════════════════════════════════
# 10. IssueCommands.is_empty(): garante que agent_hub conta como não-vazio
# ══════════════════════════════════════════════════════════════════════════════

def test_is_empty_verdadeiro_sem_campos():
    """IssueCommands sem nenhum campo preenchido deve ser considerado vazio."""
    assert IssueCommands().is_empty() is True


def test_is_empty_falso_quando_agent_hub_definido():
    """IssueCommands cujo único campo é agent_hub NÃO deve ser vazio.

    Protege o caminho de produção em sync.py (create-up): se o único comando
    declarado for /agent-hub-high, is_empty() deve retornar False para que
    apply_commands seja chamado e a label agent-hub-high seja aplicada na
    criação da issue. Sem essa garantia, a feature de roteamento agent-hub
    silenciosamente não funcionaria em issues recém-criadas.
    """
    assert IssueCommands(agent_hub="low").is_empty() is False


# ══════════════════════════════════════════════════════════════════════════════
# 11. serialize_commands: ordem canônica com agent_hub e outros campos
# ══════════════════════════════════════════════════════════════════════════════

def test_serialize_ordem_canonica_agent_hub_apos_labels():
    """/agent-hub-<valor> deve aparecer depois de /labels na serialização canônica."""
    cmds = IssueCommands(labels=["backend"], agent_hub="high", need_human=True)
    serialized = serialize_commands(cmds)
    lines = [l for l in serialized.splitlines() if l.startswith("/")]
    idx_labels = next((i for i, l in enumerate(lines) if l.startswith("/labels")), -1)
    idx_hub = next((i for i, l in enumerate(lines) if l.startswith("/agent-hub-")), -1)
    idx_need_human = next((i for i, l in enumerate(lines) if l.startswith("/need_human")), -1)
    assert idx_labels != -1, "/labels deve estar presente"
    assert idx_hub != -1, "/agent-hub-<valor> deve estar presente"
    assert idx_need_human != -1, "/need_human deve estar presente"
    # Ordem: /labels < /agent-hub < /need_human
    assert idx_labels < idx_hub < idx_need_human, (
        f"Ordem esperada /labels < /agent-hub < /need_human, "
        f"mas foi labels={idx_labels}, hub={idx_hub}, need_human={idx_need_human}"
    )


def test_serialize_com_todos_os_campos():
    """serialize_commands funciona corretamente com todos os campos preenchidos."""
    cmds = IssueCommands(
        parent="10",
        children=["11", "12"],
        blocked_by=["5"],
        blocks=["20"],
        labels=["backend", "security"],
        agent_hub="medium",
        close="completed",
        need_human=True,
    )
    serialized = serialize_commands(cmds)
    assert "/parent #10" in serialized
    assert "/children #11, #12" in serialized
    assert "/blocked_by #5" in serialized
    assert "/blocks #20" in serialized
    assert "/labels backend, security" in serialized
    assert "/agent-hub-medium" in serialized
    assert "/need_human" in serialized
    assert "/close completed" in serialized
    # agent-hub-* não deve aparecer em /labels
    for line in serialized.splitlines():
        if line.startswith("/labels"):
            assert "agent-hub" not in line


# ══════════════════════════════════════════════════════════════════════════════
# 12. all_labels: colisão entre labels[] com agent-hub-X e agent_hub=Y
# ══════════════════════════════════════════════════════════════════════════════

def test_all_labels_colisao_label_x_e_valor_y_nao_duplica_e_nao_perde():
    """Se labels tem agent-hub-low e agent_hub='high', all_labels emite ambas sem duplicar.

    Esse cenário não deveria ocorrer no fluxo normal (from_issue filtra labels),
    mas all_labels deve se comportar de forma defensiva: emite a label derivada
    de agent_hub e preserva o que está em labels sem deduplicar por semântica.
    """
    cmds = IssueCommands(labels=["agent-hub-low"], agent_hub="high")
    all_lbs = cmds.all_labels()
    # agent-hub-high deve aparecer (derivado de agent_hub)
    assert "agent-hub-high" in all_lbs
    # agent-hub-low veio de labels (não filtrado aqui, pois from_issue é quem filtra)
    assert "agent-hub-low" in all_lbs


def test_all_labels_labels_vazio_e_agent_hub_definido():
    """labels vazio + agent_hub definido emite apenas a label de hub."""
    cmds = IssueCommands(labels=[], agent_hub="low")
    all_lbs = cmds.all_labels()
    assert all_lbs == ["agent-hub-low"]


# ══════════════════════════════════════════════════════════════════════════════
# 13. apply_events_to_commands: eventos de coluna não afetam agent_hub
# ══════════════════════════════════════════════════════════════════════════════

def test_eventos_coluna_need_human_nao_zera_agent_hub():
    """Evento 'need_human' de on_in/on_out não deve alterar agent_hub."""
    from src.core.commands import apply_events_to_commands
    cmds = IssueCommands(labels=["backend"], agent_hub="high")
    apply_events_to_commands(cmds, ["need_human"])
    assert cmds.agent_hub == "high"
    assert cmds.need_human is True


def test_eventos_coluna_close_nao_zera_agent_hub():
    """Evento 'close' de on_in/on_out não deve alterar agent_hub."""
    from src.core.commands import apply_events_to_commands
    cmds = IssueCommands(labels=["backend"], agent_hub="medium")
    apply_events_to_commands(cmds, ["close"])
    assert cmds.agent_hub == "medium"
    assert cmds.close == "completed"


def test_eventos_coluna_label_normal_nao_toca_agent_hub():
    """Adicionar label comum via evento não afeta agent_hub."""
    from src.core.commands import apply_events_to_commands
    cmds = IssueCommands(labels=[], agent_hub="low")
    apply_events_to_commands(cmds, ["security"])
    assert cmds.agent_hub == "low"
    assert "security" in cmds.labels


def test_eventos_coluna_remover_label_normal_nao_toca_agent_hub():
    """Remover label comum via evento não afeta agent_hub."""
    from src.core.commands import apply_events_to_commands
    cmds = IssueCommands(labels=["backend", "security"], agent_hub="high")
    apply_events_to_commands(cmds, ["-backend"])
    assert cmds.agent_hub == "high"
    assert "backend" not in cmds.labels
    assert "security" in cmds.labels


# ══════════════════════════════════════════════════════════════════════════════
# 14. from_issue: robustez com labels None e lista vazia
# ══════════════════════════════════════════════════════════════════════════════

def test_from_issue_labels_none_nao_levanta_excecao():
    """from_issue não deve levantar exceção quando issue.labels é None."""
    issue = _make_issue([])
    issue.labels = None
    cmds = from_issue(issue)
    assert cmds.agent_hub is None
    assert cmds.labels == []


def test_from_issue_labels_vazias_retorna_estado_vazio():
    """from_issue com lista de labels vazia retorna IssueCommands sem valor."""
    issue = _make_issue([])
    cmds = from_issue(issue)
    assert cmds.agent_hub is None
    assert cmds.need_human is False
    assert cmds.labels == []


# ══════════════════════════════════════════════════════════════════════════════
# 15. agent_hub(): robustez com labels None
# ══════════════════════════════════════════════════════════════════════════════

def test_agent_hub_labels_none_retorna_none():
    """agent_hub() não deve falhar quando issue['labels'] é None."""
    issue = {"labels": None, "body_path": ""}
    assert agent_hub(issue) is None


def test_agent_hub_sem_chave_labels_retorna_none():
    """agent_hub() não deve falhar quando 'labels' não está no dict."""
    issue = {"body_path": ""}
    assert agent_hub(issue) is None
