"""Gerador do steering de SISTEMA — instrui agentes sobre regras e estrutura.

Gerado automaticamente no startup a partir do pipe.yml. O conteúdo é escrito em
`.kiro/steering/esteira.md` e auto-carregado pelo kiro-cli (default agent) via
`KIRO_HOME`. Não é mais injetado por `--agent` nem embutido inline no prompt.

Arquivo gerado:
  .kiro/steering/esteira.md — steering em Markdown (frontmatter `inclusion: always`)

Caminho B (P1.1(b)): NÃO geramos mais `.kiro/agents/pipe_context.json` nem
usamos o gate `--agent pipe_context`. O default agent do kiro-cli carrega o
steering automaticamente quando `KIRO_HOME` aponta para o `.kiro` da esteira.

Regra de regeneração: recria se não existir OU se pipe.yml for mais novo.
"""

from pathlib import Path

# Caminhos usados como variáveis de módulo para facilitar o mock em testes.
PIPE_FILE: Path = Path("pipe.yml")
STEERING_FILE: Path = Path(".kiro") / "steering" / "esteira.md"

# Alias de compatibilidade: código/adapters antigos importam CONTEXT_FILE.
# Aponta para o steering (mesma referência), evitando quebra durante a migração.
CONTEXT_FILE: Path = STEERING_FILE

# Frontmatter do steering. `inclusion: always` é portável (IDE/Web); no CLI todos
# os arquivos de steering entram sempre (no-op), mas mantemos por portabilidade.
_FRONTMATTER = "---\ninclusion: always\n---"

# Arquivos internos da esteira que o agente NUNCA deve tocar.
# Inclui o próprio steering (`.kiro/steering/**/*.md`) conforme P1.3.
_PROTECTED_FILES = [
    ".pipe/boards/*/snapshot.json",
    ".pipe/changeQueue.json",
    ".pipe/deadLetter.json",
    ".pipe/orphanFiles.json",
    ".pipe/sessions.json",
    ".pipe/throttle",
    ".pipe/throttle.json",
    ".pipe/pipe.lock",
    ".kiro/steering/**/*.md",
]


def _needs_regeneration() -> bool:
    """Retorna True se o steering precisa ser (re)criado."""
    if not STEERING_FILE.exists():
        return True
    if not PIPE_FILE.exists():
        return False
    return PIPE_FILE.stat().st_mtime > STEERING_FILE.stat().st_mtime


def _section_restrictions() -> list[str]:
    """Seção de arquivos protegidos (texto aprovado — P1.3 item 1)."""
    lines = [
        "## Arquivos protegidos (NÃO acessar)",
        "Nunca leia, escreva, crie, mova ou versione estes caminhos — são "
        "estado interno da esteira; alterá-los corrompe a pipeline:",
    ]
    for path in _PROTECTED_FILES:
        lines.append(f"- `{path}`")
    lines.append("")
    return lines


def _section_body_structure() -> list[str]:
    """Seção 'Estrutura do -body.md' + comandos @--- (texto aprovado — P1.3 item 2)."""
    return [
        "## Estrutura do `-body.md`",
        "O `-body.md` é seu (do agente): toda edição do arquivo é feita por "
        "você; a esteira apenas o interpreta. Tudo ACIMA de `@---` vira o corpo "
        "da issue no board; tudo ABAIXO vira atributos da issue.",
        "",
        "Ordem obrigatória (5 partes):",
        "1. Corpo — conteúdo que rege a execução.",
        "2. `📝` — linha separadora das anotações.",
        "3. Anotações — memória da issue (persistem no corpo da issue, abaixo do `📝`).",
        "4. `@---` — linha separadora dos comandos.",
        "5. Comandos — um por linha, iniciados por `/`.",
        "",
        "### Anotações (você mantém)",
        "- `pai: #<id> - <nome>` — só se houver issue mãe.",
        "- `branch pai: <branch>` — só se houver issue mãe.",
        "- `branch: <branch de trabalho>` — ou `(ainda não criada)` se ainda não existe.",
        "- `boards: <board1>, <board2>` — board(s) a que esta issue pertence.",
        "",
        "### Comandos",
        "",
        "Estado declarativo: o que está escrito É o estado final. Presente = "
        "garantido; ausente = removido. Não há comando de \"remover\". Todo "
        "comando age sobre ESTA issue (a que você está editando).",
        "",
        "Comandos (efeito sobre esta issue):",
        "- `/parent #N` — N é a mãe desta issue.",
        "- `/children #N, #M` — N e M são filhas desta issue.",
        "- `/blocks #N, #M` — esta issue trava N e M (N e M só avançam quando esta fechar).",
        "- `/blocked_by #N, #M` — esta issue fica travada até N e M fecharem.",
        "- `/labels a, b, c` — informa as labels desta issue; se houver labels "
        "anteriores, são substituídas por estas.",
        "- `/agent-hub-<valor>` — label de roteamento de agente; `<valor>` livre "
        "(ex.: low, middle, high). Use apenas quando o prompt pedir "
        "explicitamente e não altere se não for seu papel.",
        "- `/need_human` — adicione esta label sempre que precisar de intervenção "
        "humana (pedir intervenção sem ela gera erro).",
        "- `/archive` — arquiva esta issue.",
        "",
        "Bloqueio — regras (invioláveis):",
        "- Relações de bloqueio aceitam só o ID (`#N`); nunca use o nome da issue.",
        "- Declare o bloqueio em UMA issue só; a esteira completa o par. Nunca "
        "declare nos dois lados.",
        "- Declare sempre no body da issue que você está editando, escolhendo o "
        "comando certo: `/blocked_by #N` se ESTA issue deve esperar N; "
        "`/blocks #N` se ESTA issue deve travar N.",
        "- Nunca aponte `/blocks #N` e `/blocked_by #N` para o mesmo N: ciclos "
        "são proibidos.",
        "",
        "Ao criar issue nova (nasce sem ID):",
        "- Declare TODAS as relações dela no body DELA mesma — nunca declare a "
        "relação no body da issue-par.",
        "- Quando a esteira atribuir o ID à nova issue, ela mesma vai aos bodies "
        "das issues referenciadas e completa cada par.",
        "- Só use `/parent #N` se for realmente relação mãe→filha (confira o "
        "esquema de issues e o prompt do agente).",
        "",
    ]


def _section_issue_naming() -> list[str]:
    """Seção de convenções de nomeação de issues (P1.3 item 3)."""
    return [
        "## Criação de issues",
        "",
        "Ao criar uma nova issue em um board, crie APENAS o seguinte arquivo:",
        "",
        "- `<slug>-body.md`",
        "",
        "### Regras de nomeação (sem prefixo numérico)",
        "",
        "NÃO prefixe o nome com números.",
        "O padrão errado seria algo como `4-login-body.md` — isso está errado.",
        "O ID real é atribuído pelo GitHub após o sync; antes disso o arquivo "
        "não tem e não deve ter prefixo numérico.",
        "",
        "**Correto:** `implementar-login-body.md`",
        "**Errado:** `4-implementar-login-body.md`",
        "",
        "NÃO escreva IDs numéricos no nome do arquivo.",
        "",
    ]


def _section_boards(config: dict) -> list[str]:
    """Seção de boards e colunas derivada do pipe.yml (P1.3 item 4)."""
    lines = [
        "## Boards e colunas",
        "",
        "Estrutura de boards e colunas configurada no pipe.yml:",
        "",
    ]
    boards_cfg = config.get("boards", {})
    for board_id, board in boards_cfg.items():
        if board_id == "platform":
            continue
        if not isinstance(board, dict):
            continue
        board_name = board.get("name", board_id)
        board_flow = board.get("flow", "—")
        lines += [
            f"### Board: {board_name} (id: `{board_id}`)",
            "",
            f"- **Flow:** `{board_flow}`",
            "",
            "| Coluna (id) | Nome | Agente |",
            "|-------------|------|--------|",
        ]
        for col_id, col in board.get("columns", {}).items():
            if not isinstance(col, dict):
                continue
            col_name = col.get("name", col_id)
            agent = col.get("agent", "—")
            lines.append(f"| `{col_id}` | {col_name} | {agent} |")
        lines.append("")
    return lines


def _section_branches(config: dict) -> list[str]:
    """Seção de git flow e prefixos de branch (P1.3 item 5)."""
    lines = [
        "## Git flow e branches",
        "",
        "Flows disponíveis e seus prefixos de branch:",
        "",
        "| Flow | Prefixo | Origem | Merge em |",
        "|------|---------|--------|----------|",
    ]
    flow_cfg = config.get("git", {}).get("flow", {})
    base = flow_cfg.get("base", "main")
    for flow_id, flow in flow_cfg.items():
        if flow_id == "base" or not isinstance(flow, dict):
            continue
        prefix = flow.get("prefix", "—")
        create = flow.get("create", base)
        merge = flow.get("merge", base)
        lines.append(f"| `{flow_id}` | `{prefix}` | `{create}` | `{merge}` |")
    lines += [
        "",
        f"Branch base: `{base}`",
        "",
        "Ao criar uma branch, use o prefixo correspondente ao flow do board.",
        "Exemplo: flow `feature` → branch `feature/<id>-<slug>`.",
        "",
    ]
    return lines


def _build_content(config: dict) -> str:
    """Monta o conteúdo completo do steering `esteira.md`."""
    sections: list[str] = [
        _FRONTMATTER,
        "",
        "# Contexto do sistema — gerado automaticamente",
        "",
        "Este arquivo é gerado pelo startup da esteira a partir do `pipe.yml` "
        "e carregado como steering do kiro-cli em cada execução.",
        "**Não edite manualmente** — será sobrescrito ao reiniciar.",
        "",
    ]
    sections += _section_restrictions()
    sections += _section_issue_naming()
    sections += _section_body_structure()
    sections += _section_boards(config)
    sections += _section_branches(config)
    return "\n".join(sections)


def generate_context(config: dict) -> Path:
    """Gera `.kiro/steering/esteira.md` a partir do config.

    Cria o arquivo se não existir. Regenera se pipe.yml foi modificado após o
    steering. Não sobrescreve se o steering já estiver atualizado.

    Retorna o Path do steering gerado.
    """
    if not _needs_regeneration():
        return STEERING_FILE

    STEERING_FILE.parent.mkdir(parents=True, exist_ok=True)
    content = _build_content(config)
    STEERING_FILE.write_text(content, encoding="utf-8")
    return STEERING_FILE


def ensure_steering_integrity(config: dict) -> bool:
    """Guarda de integridade do steering (P1.5 / F0.9).

    Compara o conteúdo atual de `.kiro/steering/esteira.md` com o que o gerador
    produziria a partir do config. Se o arquivo não existe ou divergiu (ex.: um
    agente o alterou), REESCREVE com o conteúdo autoritativo e retorna True
    (divergiu). Retorna False se já estava íntegro.

    Chamada antes de despachar cada agente para garantir que o steering nunca é
    corrompido silenciosamente entre execuções.
    """
    expected = _build_content(config)
    try:
        current = STEERING_FILE.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        current = None
    if current == expected:
        return False
    STEERING_FILE.parent.mkdir(parents=True, exist_ok=True)
    STEERING_FILE.write_text(expected, encoding="utf-8")
    return True
