"""Agent core - port para execução de agentes."""

import fnmatch
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from src.core.commands import annotations_doc, parse_body, AGENT_HUB_PREFIX
from src.core.snapshot import BOARDS_DIR

REPO_DIR = Path("repo")

CONTEXTS_DIR = Path("contexts")

# ══════════════════════════════════════════════════════════════════════════════
# Proteção de arquivos de estado interno
# ══════════════════════════════════════════════════════════════════════════════

# Lista centralizada de padrões glob de arquivos de estado interno da esteira.
# Nenhum desses paths deve jamais aparecer em prompts enviados a agentes.
# Padrões seguem a sintaxe fnmatch (glob simples, sem separadores de diretório
# implícitos). Para paths absolutos, a verificação é feita comparando o
# sufixo do path com o padrão sem o prefixo de diretório variável.
#
# Referência: [Incidente Issue Fantasma] Correção 1 — issue #8.
PROTECTED_PATHS: list[str] = [
    ".pipe/boards/*/snapshot.json",
    ".pipe/changeQueue.json",
    ".pipe/throttle.json",
    ".pipe/throttle-*.json",
    ".pipe/deadLetter.json",
    ".pipe/orphanFiles.json",
    ".pipe/pipe.lock",
]


def _matches_protected(token: str, pattern: str) -> bool:
    """Verifica se um token de texto corresponde a um padrão protegido.

    Estratégia:
    - Teste direto com fnmatch (cobre paths relativos exatos).
    - Para padrões com ``*`` interno (ex.: ``boards/*/snapshot.json``), divide
      o padrão em prefixo fixo e sufixo fixo e verifica se o token contém o
      sufixo (cobre paths absolutos e relativos com subdiretórios variáveis).
    - Para padrões simples sem ``*`` no meio, verifica se o token termina com
      o padrão inteiro (cobre paths absolutos).
    """
    # Teste direto (path relativo exato ou com glob no nível de arquivo)
    if fnmatch.fnmatch(token, pattern):
        return True

    # Para cobertura de paths absolutos: verifica se o token contém uma
    # sequência que case com o padrão. Divide em segmentos e testa o sufixo.
    parts = pattern.split("/")
    # Pega a parte do padrão a partir do primeiro segmento com glob ou fixo
    # que identifica o arquivo de forma única (último segmento com extensão).
    # Estratégia: encontra o sufixo mais longo sem '*' no início.
    suffix_parts = []
    for part in reversed(parts):
        suffix_parts.insert(0, part)
        if "*" not in part:
            # Continua acumulando até encontrar um segmento com glob
            candidate = "/".join(suffix_parts)
            if fnmatch.fnmatch(token.split("/")[-len(suffix_parts):][0]
                               if len(token.split("/")) >= len(suffix_parts)
                               else "", suffix_parts[0]):
                # Verifica se o final do token casa com os últimos N segmentos
                token_parts = token.replace("\\", "/").split("/")
                n = len(suffix_parts)
                if len(token_parts) >= n:
                    tail = "/".join(token_parts[-n:])
                    if fnmatch.fnmatch(tail, candidate):
                        return True
            break
        else:
            # Há glob neste segmento; o que importa é o sufixo após o glob
            # Não continua acumulando para trás além desse ponto
            break

    return False


def _assert_no_protected(prompt: str) -> None:
    """Verifica que nenhum path protegido (PROTECTED_PATHS) aparece no prompt.

    Levanta ValueError identificando o arquivo protegido encontrado.

    A verificação tokeniza o prompt palavra a palavra e avalia cada token
    contra os padrões em PROTECTED_PATHS via fnmatch. Para padrões com
    componentes de diretório (ex.: ``.pipe/boards/*/snapshot.json``), o token
    é testado tanto diretamente quanto pela correspondência do sufixo — o que
    cobre tanto paths relativos quanto absolutos.

    Não dispara falsos positivos para substrings sem extensão .json ou nomes
    similares (ex.: ``snapshots/``, ``snap.py``, ``throttle-config.yaml``).
    """
    # Separa o prompt em tokens (palavras, paths, qualquer sequência não-espaço)
    tokens = prompt.split()

    for token in tokens:
        # Remove pontuação final que não faz parte do path (vírgula, ponto final…)
        token = token.rstrip(".,;:\"'`)")

        for pattern in PROTECTED_PATHS:
            if _matches_protected(token, pattern):
                # Extrai o nome do arquivo do padrão para a mensagem de erro.
                filename = pattern.rsplit("/", 1)[-1]
                raise ValueError(
                    f"Prompt contém referência a arquivo de estado protegido "
                    f"'{filename}' (padrão: '{pattern}'). "
                    f"Token encontrado: '{token}'"
                )


def agent_hub(issue: dict) -> str | None:
    """Lê o valor de roteamento de agente (hub) da issue a partir das labels.

    O valor é armazenado como label `agent-hub-<valor>` no GitHub
    (ex.: agent-hub-low, agent-hub-senior, agent-hub-deep). O sufixo é livre —
    pode representar nível, função, profundidade etc.
    Essa label é sincronizada nativamente pelo board, eliminando a
    dependência de estado local que causava o bug de preservação no sync-down.
    """
    for label in issue.get("labels", []) or []:
        if label.startswith(AGENT_HUB_PREFIX):
            return label[len(AGENT_HUB_PREFIX):]
    return None


def resolve_agent_id(col: dict, issue: dict) -> str:
    """Resolve o agente efetivo de uma coluna conforme o hub da issue.

    Usa `agent-hub[<valor>]` quando o valor (tag /agent-hub-<valor>) existe e
    está mapeado; caso contrário, cai no `agent` default da coluna.
    """
    overrides = col.get("agent-hub") or {}
    hub = agent_hub(issue)
    if hub and hub in overrides:
        return overrides[hub]
    return col.get("agent", "")


def resolve_repo_id(config: dict, board_cfg: dict) -> str:
    """Resolve o id do repositório alvo de um board.

    Usa board.repo se definido; caso contrário, o primeiro repo de git.repo.
    """
    repos = config["git"]["repo"]
    return board_cfg.get("repo") or next(iter(repos))


def resolve_work_dir(config: dict, board_cfg: dict) -> Path:
    """Diretório de trabalho (sandbox) do agente: repo/<repo_id> absoluto."""
    return (REPO_DIR / resolve_repo_id(config, board_cfg)).resolve()


@dataclass
class AgentParams:
    """Parâmetros para execução do agente."""
    platform: str
    agent_id: str          # id do agente resolvido (config)
    agent_name: str        # nome amigável (log)
    model: str
    issue_id: str
    board_id: str
    col_id: str
    prompt: str
    work_dir: str          # diretório de trabalho do agente (clone em repo/<repo_id>)
    repo_id: str = None    # id do repositório alvo (chave em git.repo)
    context: str = None
    continuation_prompt: str = None  # prompt de continuação (E10) quando há sessão
    remediation_prompt: str = None   # prompt de remediação (E4) com os erros de sync
    col_name: str = ""     # nome humanizado da coluna/etapa (log de terminal)
    title: str = ""        # título da issue (log de terminal)


class AgentPort(ABC):
    """Port para adapters de agente (kiro-cli, etc)."""

    @abstractmethod
    def execute(self, params: AgentParams) -> None:
        """Executa o agente com os parâmetros fornecidos."""
        pass


# ══════════════════════════════════════════════════════════════════════════════
# build_prompt
# ══════════════════════════════════════════════════════════════════════════════

def build_prompt(config: dict, task: dict) -> str:
    """Monta o prompt completo para o agente executar.

    task: dict com board_id, issue, column, col_id, board (retornado por keep_task).
    """
    board_id = task["board_id"]
    board_cfg = task["board"]
    col = task["column"]
    col_id = task["col_id"]
    issue = task["issue"]
    agent_id = resolve_agent_id(col, issue)
    gitevents = col.get("gitevents")  # create|use|merge|create-merge|no-branch

    # Resolver nome humanizado do agente a partir da config
    agent_display_name = agent_id
    for platform_agents in config.get("agents", {}).values():
        if agent_id in platform_agents:
            agent_display_name = platform_agents[agent_id].get("name", agent_id)
            break

    # Resolver diretório de trabalho (sandbox do agente).
    # O agente SEMPRE opera dentro de repo/<repo_id>; nunca no diretório da esteira.
    work_dir = resolve_work_dir(config, board_cfg)

    # Resolver dados da issue (caminhos ABSOLUTOS: os arquivos vivem em .pipe/,
    # fora do repo, e o agente roda com cwd no repo).
    body_path = Path(issue.get("body_path", "")).resolve()
    slug = body_path.stem.removesuffix("-body")
    issue_dir = body_path.parent
    history_file = issue_dir / f"{slug}-history.md"
    addcomment_file = issue_dir / f"{slug}-addcomment.md"

    # Título da issue
    title = ""
    if body_path.exists():
        first_line = body_path.read_text(encoding="utf-8").split("\n", 1)[0]
        title = first_line.lstrip("# ").strip()
    title = title or slug

    # ── Resolver git (E3): dados para INSTRUÇÕES descritivas ──
    # A esteira NÃO monta mais o nome da branch nem emite script bash: passa o
    # padrão do flow como instrução e o agente cria/reutiliza a branch guiado
    # pelas anotações do `-body.md` (`branch pai` = origem; `branch` = trabalho).
    flow_type = board_cfg.get("flow", "feature")
    flow = config["git"]["flow"]
    flow_cfg = flow.get(flow_type, {})
    base_branch = flow.get("base", "main")

    # Anotações do body (E2/F0.4): a esteira apenas INTERPRETA (não escreve no
    # -body.md). `branch pai` = origem de onde a branch nasce/mescla; `branch` =
    # branch de trabalho (None quando "(ainda não criada)").
    raw_body = body_path.read_text(encoding="utf-8") if body_path.exists() else ""
    _corpo, annot, _cmds = parse_body(raw_body)

    # Origem da branch: a anotação `branch pai` tem precedência; caso não haja
    # pai, a origem declarada no flow (`create`) ou a base.
    origin_branch = annot.parent_branch or flow_cfg.get("create", base_branch)
    # Alvo do merge/PR: `merge` do flow (ou a base).
    merge_branch = flow_cfg.get("merge", base_branch)
    # Template legível do nome da branch (E1 — obrigatório por flow no pipe.yml).
    branch_pattern = flow_cfg.get("branch_pattern", "")

    # Transições
    change = col.get("change", {})

    lines = []

    # ── Cabeçalho ──
    lines.append(f"Você é: {agent_display_name}.")
    lines.append("")
    lines.append(f"**Tarefa:** {title}")
    lines.append(f"**Etapa:** {col.get('name', col_id)}")
    lines.append(f"**Objetivo:** {col.get('target-prompt', '')}")
    _step = col.get("step-prompt")
    if _step and str(_step).strip():
        lines.append("")
        lines.append("**Passos:**")
        lines.append(str(_step).strip())
    lines.append("")

    # ── Sandbox / regras de operação ──
    lines.append("## Diretório de trabalho (OBRIGATÓRIO)")
    lines.append("")
    lines.append(f"Seu diretório de trabalho é o repositório clonado em `{work_dir}`.")
    lines.append("")
    lines.append("Regras invioláveis:")
    lines.append(f"- TODOS os comandos `git` e TODA alteração de código devem ocorrer DENTRO de `{work_dir}`.")
    lines.append(f"- Comece executando `cd {work_dir}` e permaneça lá durante toda a tarefa.")
    lines.append("- NUNCA execute `git checkout`, `git stash`, `git reset` ou qualquer comando git fora desse diretório.")
    lines.append("- Os arquivos da issue (`-body.md`, `-history.md`, `-addcomment.md`) ficam em `.pipe/`, FORA do repositório, e são gerenciados pela esteira. Leia/escreva-os pelos caminhos absolutos indicados, mas NÃO os versione no git.")
    lines.append("")

    # ── Git — preparação da branch (E3: instruções DESCRITIVAS) ──
    # Sem script bash pronto: o COMO fica no steering ("Git — como operar"); aqui
    # damos o objetivo e as proteções do bug #108 em prosa, guiados pelas
    # anotações do body.
    if gitevents in ("create", "use", "merge", "create-merge"):
        can_create = gitevents in ("create", "create-merge")

        lines.append("## Git — preparação da branch")
        lines.append("")
        lines.append(
            f"Comece atualizando as referências remotas (`git fetch origin`) dentro de `{work_dir}`."
        )
        lines.append("")
        lines.append("Descubra a branch de trabalho pela anotação `branch:` do `-body.md`:")
        lines.append("")
        lines.append(
            "- **Se `branch:` já tem um nome** (a branch já foi criada): reutilize-a — "
            "faça checkout dessa branch, trazendo-a do remoto se ainda não existir localmente. "
            "NÃO crie outra branch nem a recrie/sobrescreva; esta etapa é idempotente."
        )
        if can_create:
            lines.append(
                "- **Se `branch:` está como `(ainda não criada)`**: crie a branch de trabalho de "
                f"forma ATÔMICA a partir de `origin/{origin_branch}` — num único passo que já parte "
                "da origem correta, NUNCA a partir do HEAD corrente e NUNCA em duas etapas onde a "
                "criação rode mesmo se a atualização da origem falhar (base errada e silenciosa — "
                f"bug #108). Se `origin/{origin_branch}` não existir, PARE em vez de inventar uma base."
            )
            lines.append(
                f"- Dê à branch um nome seguindo o `branch_pattern` do flow `{flow_type}`: "
                f"`{branch_pattern}` (substitua os campos pelo id e slug reais desta issue). "
                "Depois de criá-la, grave o nome REAL na anotação `branch:` do `-body.md`."
            )
        else:
            lines.append(
                "- Esta etapa opera sobre a branch de trabalho JÁ existente desta issue e não cria "
                "uma branch nova. Se `branch:` ainda estiver `(ainda não criada)`, isso é um erro de "
                "fluxo: registre o bloqueio em vez de criar uma branch a partir da origem."
            )
        lines.append("")

    # ── Executar tarefa ──
    lines.append("## Executar tarefa")
    lines.append("")
    lines.append(f"Leia a issue em `{body_path}` e o histórico em `{history_file}` para contexto completo.")
    lines.append("")
    lines.append("Realize o objetivo descrito acima. Ao concluir ou se houver bloqueio:")
    lines.append("")
    lines.append(f"- Anote observações, dúvidas ou resumo em `{addcomment_file}` (assine com `— {agent_display_name}` no final)")
    lines.append("")

    # ── Versionar (commit e push) — DESCRITIVO ──
    if gitevents in ("create", "use", "merge", "create-merge"):
        lines.append("## Versionar (commit e push)")
        lines.append("")
        lines.append(
            "Faça commit e push do trabalho SEMPRE na branch de trabalho — nunca em "
            f"`{base_branch}` nem na branch de origem (`{origin_branch}`). Use uma mensagem de "
            "commit que descreva esta etapa."
        )
        lines.append("")

    # ── Abrir merge/PR (merge / create-merge) — DESCRITIVO ──
    if gitevents in ("merge", "create-merge"):
        lines.append("## Abrir merge/PR")
        lines.append("")
        lines.append(
            f"Abra o PR da branch de trabalho para `{merge_branch}` (alvo de merge do flow "
            f"`{flow_type}`). ANTES de abrir, garanta que a branch já CONTÉM A PONTA de "
            f"`origin/{merge_branch}`: atualize com `git fetch origin` e, se a base estiver "
            f"defasada, integre `origin/{merge_branch}` na branch (resolvendo conflitos) antes de "
            "abrir o PR. Um PR aberto de base defasada nasce com conflitos e diff poluído "
            "(bug #108). Se já houver um PR aberto para esta branch, confirme-o em vez de criar outro."
        )
        lines.append("")

    # ── Anotações no body (comandos @---) ──
    lines.append(annotations_doc())
    lines.append("")

    # ── Transição de coluna ──
    lines.append("## Transição de coluna")
    lines.append("")
    lines.append("Ao finalizar, mova os 3 arquivos da issue (`-body.md`, `-history.md`, `-addcomment.md`) para a coluna de destino.")
    lines.append("")
    for condition, target_col in change.items():
        target_dir = (BOARDS_DIR / board_id / target_col).resolve()
        lines.append(f"- **{condition}** → `mv {issue_dir}/{slug}-*.md {target_dir}/`")
    lines.append("")

    prompt = "\n".join(lines)

    # Guard de segurança: garante que nenhum arquivo de estado interno da
    # esteira vaze no prompt enviado ao agente.
    _assert_no_protected(prompt)

    return prompt


# ══════════════════════════════════════════════════════════════════════════════
# build_continuation_prompt (E10)
# ══════════════════════════════════════════════════════════════════════════════

def build_continuation_prompt(config: dict, task: dict) -> str:
    """Monta o PROMPT DE CONTINUAÇÃO (E10) para uma sessão preservada.

    Usado quando existe sessão CONFIRMADA para (issue, coluna): o agente já
    trabalhou nesta etapa e retoma via `--resume-id`. Em vez de reexecutar o
    prompt completo, envia um nudge genérico + ponteiros aos arquivos + a
    transição de coluna, para o agente continuar de onde parou.
    """
    board_id = task["board_id"]
    col = task["column"]
    col_id = task["col_id"]
    issue = task["issue"]
    change = col.get("change", {})

    body_path = Path(issue.get("body_path", "")).resolve()
    slug = body_path.stem.removesuffix("-body")
    issue_dir = body_path.parent
    history_file = issue_dir / f"{slug}-history.md"
    addcomment_file = issue_dir / f"{slug}-addcomment.md"

    lines = [
        "Você já trabalhou nesta etapa desta issue. Releia o history/addcomment "
        "em busca de apontamentos novos e continue de onde parou até concluir a "
        "etapa — não recomece do zero.",
        "",
        f"- Histórico: `{history_file}`",
        f"- Anotações/comentário: `{addcomment_file}`",
        f"- Body da issue: `{body_path}`",
        "",
        "## Transição de coluna",
        "",
        "Ao finalizar, mova os 3 arquivos da issue (`-body.md`, `-history.md`, "
        "`-addcomment.md`) para a coluna de destino.",
        "",
    ]
    for condition, target_col in change.items():
        target_dir = (BOARDS_DIR / board_id / target_col).resolve()
        lines.append(f"- **{condition}** → `mv {issue_dir}/{slug}-*.md {target_dir}/`")
    lines.append("")

    prompt = "\n".join(lines)
    _assert_no_protected(prompt)
    return prompt


# ══════════════════════════════════════════════════════════════════════════════
# build_remediation_prompt (E4)
# ══════════════════════════════════════════════════════════════════════════════

def build_remediation_prompt(config: dict, task: dict, errors: str) -> str:
    """Monta o PROMPT DE REMEDIAÇÃO (E4) com os erros da sincronização.

    Enviado uma única vez quando o sync falha com erro corrigível pelo agente
    (validação do board / 422). Distinto do prompt de execução e do de
    continuação (E10, situação 3): não pede refazer a tarefa, só corrigir o que
    causou a falha de sincronização.
    """
    lines = [
        "Sua última execução nesta issue foi concluída, mas a esteira não "
        "conseguiu sincronizar as alterações com o board. Não refaça a tarefa — "
        "corrija apenas o que causou a falha.",
        "",
        "Erros da sincronização:",
        (errors or "").strip() or "(sem detalhes)",
        "",
        "Ajuste os comandos e anotações do `-body.md` (bloco `@---` e anotações) "
        "para resolver esses erros, seguindo as regras do sistema (relações, "
        "anti-ciclo, declarar de um lado só). Altere só o necessário para "
        "sincronizar.",
    ]
    prompt = "\n".join(lines)
    _assert_no_protected(prompt)
    return prompt
