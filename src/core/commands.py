"""Commands core - comandos anotados no final do body das issues.

O body de uma issue pode conter um bloco de comandos no final, separado do
conteúdo real por uma linha contendo apenas o separador `@---`.

Exemplo de body completo:

    Implementar o endpoint de login.

    Deve validar credenciais e retornar JWT.

    @---
    /parent #10
    /blocked_by #42, #58
    /labels backend, security
    /agent-hub-high
    /need_human

Regras:
- O separador é `@---` (linha contendo apenas isso, ignorando espaços).
- Se houver mais de um separador, o ÚLTIMO vence; os anteriores são removidos
  do body (desambiguação).
- Cada comando ocupa uma linha iniciada por `/`. Linhas sem `/` no bloco são
  ignoradas (permite comentários livres).
- Filosofia presença/ausência: o estado do comando reflete exatamente o que
  está escrito. Se o comando existe, a relação/atributo é garantido; se não
  existe, é removido. Não há comandos de "remover".

Comandos suportados:
- /parent #N            issue pai (sub-issue de N)
- /children #N, #M      filhos (N e M são sub-issues desta)
- /blocked_by #N, #M    esta issue está bloqueada por N e M
- /blocks #N, #M        esta issue bloqueia N e M
- /labels a, b, c       labels da issue (SET completo)
- /agent-hub-<valor>    roteamento de agente (hub); <valor> é livre (ex.: low, senior, deep)
- /archive
- /need_human           label especial (não entra em /labels)

Fechamento (E9): o agente NÃO fecha issues. A coluna terminal adiciona uma
label (`completed`/`not_planned`) via `on_in`; o adapter do board interpreta
essa label e fecha a issue com o motivo. O core é agnóstico (só adiciona/remove
a label). Reabrir não existe na esteira (ação humana).
"""

import re
from dataclasses import dataclass, field, replace

from src.core.log import log

# Separador entre o body real e o bloco de comandos.
SEP = "@---"

# Label especial: no GitHub é apenas mais uma label, mas no domínio é tratada
# separadamente (não aparece na lista de /labels).
NEED_HUMAN_LABEL = "need_human"

# Prefixo das labels de roteamento de agente (hub). O sufixo é livre
# (ex.: agent-hub-low, agent-hub-senior, agent-hub-deep) e é mapeado no board
# como uma label comum.
AGENT_HUB_PREFIX = "agent-hub-"


@dataclass
class IssueCommands:
    """Estado declarativo dos comandos anotados no body de uma issue."""
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    agent_hub: str | None = None
    archive: bool = False
    need_human: bool = False

    def is_empty(self) -> bool:
        """True se nenhum comando foi declarado."""
        return not (
            self.parent or self.children or self.blocked_by or self.blocks
            or self.labels or self.agent_hub or self.archive or self.need_human
        )

    def all_labels(self) -> list[str]:
        """Labels efetivas no board, incluindo as especiais need_human e agent-hub-*."""
        result = list(self.labels)
        if self.need_human and NEED_HUMAN_LABEL not in result:
            result.append(NEED_HUMAN_LABEL)
        if self.agent_hub:
            agent_hub_label = f"{AGENT_HUB_PREFIX}{self.agent_hub}"
            if agent_hub_label not in result:
                result.append(agent_hub_label)
        return result


# ══════════════════════════════════════════════════════════════════════════════
# Construção a partir de uma Issue (fluxo down)
# ══════════════════════════════════════════════════════════════════════════════

def from_issue(issue) -> IssueCommands:
    """Constrói IssueCommands a partir de uma Issue do board (fluxo down).

    Labels especiais são extraídas para campos próprios e não aparecem na
    lista de labels:
    - need_human → campo need_human
    - agent-hub-<valor> → campo agent_hub
    """
    labels = list(issue.labels or [])
    need_human = NEED_HUMAN_LABEL in labels
    labels = [l for l in labels if l != NEED_HUMAN_LABEL]

    # Extrai agent_hub a partir de labels com prefixo agent-hub-
    agent_hub_value = None
    filtered_labels = []
    for lbl in labels:
        if lbl.startswith(AGENT_HUB_PREFIX):
            if agent_hub_value is None:  # usa a primeira encontrada
                agent_hub_value = lbl[len(AGENT_HUB_PREFIX):]
        else:
            filtered_labels.append(lbl)

    return IssueCommands(
        parent=getattr(issue, "parent", None),
        children=list(getattr(issue, "children", None) or []),
        blocked_by=list(getattr(issue, "blocked_by", None) or []),
        blocks=list(getattr(issue, "blocks", None) or []),
        labels=filtered_labels,
        need_human=need_human,
        agent_hub=agent_hub_value,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sanitização de auto-referência (parent/children/blocked_by/blocks)
# ══════════════════════════════════════════════════════════════════════════════

def sanitize_relations(issue_id, cmds: IssueCommands) -> IssueCommands:
    """Remove auto-referência de parent/children/blocked_by/blocks.

    Impede que uma issue seja registrada como sua própria `parent`,
    `children`, `blocked_by` ou `blocks` antes de qualquer chamada ao board.
    Normaliza `issue_id` e os IDs das relações para `str` antes de comparar,
    preservando os demais IDs válidos (não descarta a lista inteira ao
    encontrar a auto-referência).

    Função pura: não muta `cmds` (retorna uma nova instância), não recebe
    `board_id` e não faz nenhuma chamada de rede nem importa `Board`/adapters.
    """
    result, discards, contradictions = _sanitize_relations_with_discards(issue_id, cmds)
    self_id = str(issue_id)
    for attr_name in discards:
        log.warning("Commands", f"auto-referência descartada em {attr_name}: #{self_id}",
                    issue_id=self_id)
    for cid in contradictions:
        log.warning("Commands",
                    f"contradição blocks/blocked_by descartada: #{cid} (backstop #242)",
                    issue_id=self_id)
    return result


def _sanitize_relations_with_discards(issue_id, cmds: IssueCommands):
    """Implementação pura (sem log): retorna (novo IssueCommands, discards, contradictions).

    - `discards`: nomes de atributos ('parent'/'children'/'blocked_by'/'blocks')
      onde uma auto-referência foi removida.
    - `contradictions`: IDs presentes SIMULTANEAMENTE em `blocks` e `blocked_by`
      (contradição/ciclo — backstop #242), descartados de AMBOS os lados.
    """
    self_id = str(issue_id)
    result = replace(cmds)
    discards = []

    if result.parent is not None and str(result.parent) == self_id:
        result.parent = None
        discards.append("parent")

    for attr_name in ("children", "blocked_by", "blocks"):
        values = getattr(result, attr_name)
        normalized = [str(v) for v in values]
        filtered = [v for v in normalized if v != self_id]
        if filtered != normalized:
            setattr(result, attr_name, filtered)
            discards.append(attr_name)
        elif normalized != values:
            setattr(result, attr_name, normalized)

    # Backstop #242: um mesmo ID em `blocks` E `blocked_by` é contradição
    # (esta issue trava N e é travada por N → ciclo). Descarta o ID dos DOIS
    # lados para não propagar um bloqueio recíproco impossível ao board.
    bb = [str(v) for v in result.blocked_by]
    bk = [str(v) for v in result.blocks]
    contradictions = sorted(set(bb) & set(bk))
    if contradictions:
        contra = set(contradictions)
        result.blocked_by = [v for v in bb if v not in contra]
        result.blocks = [v for v in bk if v not in contra]

    return result, discards, contradictions


# ══════════════════════════════════════════════════════════════════════════════
# Parsing
# ══════════════════════════════════════════════════════════════════════════════

def _parse_refs(arg: str) -> list[str]:
    """Extrai referências de issue (#N, owner/repo#N) de um argumento.

    Aceita separação por vírgula e/ou espaço. Remove o prefixo '#'.
    """
    refs = []
    for part in re.split(r"[,\s]+", arg.strip()):
        part = part.strip()
        if not part:
            continue
        # Mantém owner/repo#N inteiro; remove apenas '#' isolado de '#N'
        if part.startswith("#"):
            part = part[1:]
        if part:
            refs.append(part)
    return refs


def _parse_labels(arg: str) -> list[str]:
    """Extrai labels separadas por vírgula (labels podem conter espaços)."""
    labels = []
    for part in arg.split(","):
        part = part.strip()
        if part and part not in labels:
            labels.append(part)
    return labels


def parse_commands(text: str) -> IssueCommands:
    """Faz o parse de um bloco de comandos (já separado do body)."""
    cmds = IssueCommands()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("/"):
            continue
        parts = line[1:].split(None, 1)
        if not parts:
            continue
        name = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if name == "parent":
            refs = _parse_refs(arg)
            cmds.parent = refs[0] if refs else None
        elif name == "children":
            cmds.children = _parse_refs(arg)
        elif name == "blocked_by":
            cmds.blocked_by = _parse_refs(arg)
        elif name == "blocks":
            cmds.blocks = _parse_refs(arg)
        elif name == "labels":
            cmds.labels = _parse_labels(arg)
        elif name.startswith(AGENT_HUB_PREFIX):
            # Token único no formato do label, ex.: /agent-hub-low.
            # O sufixo (após "agent-hub-") é o valor do hub, livre.
            value = name[len(AGENT_HUB_PREFIX):]
            cmds.agent_hub = value or None
        elif name == "archive":
            cmds.archive = True
        elif name == "need_human":
            cmds.need_human = True

    return cmds


def split_body(raw: str) -> tuple[str, IssueCommands]:
    """Separa o body limpo dos comandos.

    Retorna (body_limpo, IssueCommands). Se houver múltiplos separadores, o
    último vence e os anteriores são removidos do body.
    """
    raw = raw or ""
    lines = raw.splitlines()
    sep_idx = [i for i, l in enumerate(lines) if l.strip() == SEP]

    if not sep_idx:
        return raw.rstrip("\n"), IssueCommands()

    last = sep_idx[-1]
    body_lines = [l for l in lines[:last] if l.strip() != SEP]
    cmd_text = "\n".join(lines[last + 1:])

    body = "\n".join(body_lines).rstrip("\n")
    return body, parse_commands(cmd_text)


# ══════════════════════════════════════════════════════════════════════════════
# Anotações (E2 / F0.4) — região entre `📝` e `@---`
# ══════════════════════════════════════════════════════════════════════════════
#
# Estrutura do -body.md (5 partes):
#   1. Corpo — conteúdo que rege a execução
#   2. `📝`   — separador das anotações
#   3. Anotações — memória da issue (pai, branch pai, branch, boards)
#   4. `@---` — separador dos comandos
#   5. Comandos — um por linha (parseados por split_body/parse_commands)
#
# Tudo ACIMA de `@---` (corpo + 📝 + anotações) é o corpo da issue no board;
# tudo ABAIXO são atributos (comandos). A esteira NUNCA escreve no -body.md:
# apenas INTERPRETA as anotações (o agente é quem as mantém).

# Separador das anotações (emoji "memo").
ANNOT_SEP = "📝"

# Placeholder de branch ainda inexistente (não vira branch real ao parsear).
_BRANCH_PLACEHOLDER_PREFIX = "("


@dataclass
class IssueAnnotations:
    """Anotações declaradas pelo agente no body (acima de `@---`, abaixo de `📝`)."""
    parent: str | None = None         # id do pai (sem '#'), se houver mãe
    parent_name: str | None = None    # nome do pai (opcional, informativo)
    parent_branch: str | None = None  # branch pai (origem)
    branch: str | None = None         # branch de trabalho (None se "(ainda não criada)")
    boards: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.parent or self.parent_branch or self.branch or self.boards)


def parse_annotations(text: str) -> IssueAnnotations:
    """Faz o parse do bloco de anotações (já separado do corpo e dos comandos).

    Chaves reconhecidas (uma por linha, `chave: valor`):
      - `pai: #<id> - <nome>`   → parent (+ parent_name se houver ' - <nome>')
      - `branch pai: <branch>`  → parent_branch
      - `branch: <branch>`      → branch ("(ainda não criada)" ⇒ None)
      - `boards: b1, b2`        → boards (lista)
    Linhas sem `:` ou com chave desconhecida são ignoradas.
    """
    annot = IssueAnnotations()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "pai":
            if " - " in value:
                id_part, name_part = value.split(" - ", 1)
            else:
                id_part, name_part = value, ""
            refs = _parse_refs(id_part)
            annot.parent = refs[0] if refs else None
            annot.parent_name = name_part.strip() or None
        elif key == "branch pai":
            annot.parent_branch = value or None
        elif key == "branch":
            # "(ainda não criada)" ou vazio ⇒ branch ainda não existe.
            annot.branch = None if (not value or value.startswith(_BRANCH_PLACEHOLDER_PREFIX)) else value
        elif key == "boards":
            annot.boards = [b.strip() for b in value.split(",") if b.strip()]

    return annot


def split_annotations(body: str) -> tuple[str, IssueAnnotations]:
    """Separa o corpo real das anotações dentro do body (acima de `@---`).

    Recebe o texto ACIMA de `@---` (corpo + 📝 + anotações) e o divide no
    ÚLTIMO separador `📝`: acima ⇒ corpo; abaixo ⇒ anotações. Sem `📝`,
    retorna o body inteiro como corpo e anotações vazias.
    """
    body = body or ""
    lines = body.splitlines()
    sep_idx = [i for i, l in enumerate(lines) if l.strip() == ANNOT_SEP]
    if not sep_idx:
        return body.rstrip("\n"), IssueAnnotations()

    last = sep_idx[-1]
    corpo_lines = [l for l in lines[:last] if l.strip() != ANNOT_SEP]
    annot_text = "\n".join(lines[last + 1:])
    corpo = "\n".join(corpo_lines).rstrip("\n")
    return corpo, parse_annotations(annot_text)


def parse_body(raw: str) -> tuple[str, IssueAnnotations, IssueCommands]:
    """Parser completo das 5 partes do -body.md.

    Retorna (corpo, anotações, comandos). O corpo é apenas a parte 1 (sem 📝,
    anotações ou @---). As anotações e comandos são interpretados; a esteira
    não reescreve o arquivo.
    """
    body_above, cmds = split_body(raw)
    corpo, annot = split_annotations(body_above)
    return corpo, annot, cmds


# ══════════════════════════════════════════════════════════════════════════════
# Serialization
# ══════════════════════════════════════════════════════════════════════════════

def serialize_commands(cmds: IssueCommands) -> str:
    """Serializa os comandos em texto canônico (ordem fixa)."""
    lines = []
    if cmds.parent:
        lines.append(f"/parent #{cmds.parent}")
    if cmds.children:
        lines.append("/children " + ", ".join(f"#{c}" for c in cmds.children))
    if cmds.blocked_by:
        lines.append("/blocked_by " + ", ".join(f"#{c}" for c in cmds.blocked_by))
    if cmds.blocks:
        lines.append("/blocks " + ", ".join(f"#{c}" for c in cmds.blocks))
    if cmds.labels:
        lines.append("/labels " + ", ".join(cmds.labels))
    if cmds.agent_hub:
        lines.append(f"/{AGENT_HUB_PREFIX}{cmds.agent_hub}")
    if cmds.need_human:
        lines.append("/need_human")
    if cmds.archive:
        lines.append("/archive")
    return "\n".join(lines)


def compose_body(body: str, cmds: IssueCommands) -> str:
    """Reconstrói o body completo: conteúdo + bloco de comandos.

    Se não há comandos, retorna apenas o body (sem separador).
    """
    body = (body or "").rstrip("\n")
    block = serialize_commands(cmds)
    if not block:
        return body
    return f"{body}\n\n{SEP}\n{block}"


# ══════════════════════════════════════════════════════════════════════════════
# Eventos de coluna aplicados sobre IssueCommands (on_in / on_out)
# ══════════════════════════════════════════════════════════════════════════════

def apply_events_to_commands(cmds: IssueCommands, events: list[str]) -> IssueCommands:
    """Aplica tokens de evento de coluna sobre um IssueCommands (in-place).

    Reescreve o estado declarativo dos comandos conforme os tokens:
      'archive'      -> archive = True
      '-archive'     -> archive = False
      'need_human'   -> need_human = True
      '-need_human'  -> need_human = False
      '<label>'      -> adiciona label (ex.: 'completed', 'not_planned')
      '-<label>'     -> remove label

    Fechamento (E9): não há token 'close'/'open'. A coluna terminal adiciona a
    label `completed`/`not_planned` (tokens de label comuns); o adapter do board
    interpreta essa label e fecha a issue. Reabrir não existe.

    Retorna o próprio cmds (mutado) para encadeamento.
    """
    for raw in events or []:
        token = str(raw).strip()
        if not token:
            continue

        if token == "archive":
            cmds.archive = True
        elif token == "-archive":
            cmds.archive = False
        elif token == "need_human":
            cmds.need_human = True
        elif token == "-need_human":
            cmds.need_human = False
        elif token.startswith("-"):
            label = token[1:]
            cmds.labels = [l for l in cmds.labels if l != label]
        else:
            if token not in cmds.labels:
                cmds.labels.append(token)

    return cmds

