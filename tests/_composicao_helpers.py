"""Helpers compartilhados pelos testes de composição em camadas (#308).

Fixture canônica (`canonical_config`/`canonical_task`) e BASELINE CONGELADO da
versão-base (pré-#308), medido uma vez com o código anterior e fixado como
constante para a medição ser determinística (CT-01/CT-02), sem acionar o
`kiro-cli` nem depender da versão antiga em runtime.
"""

from pathlib import Path
from unittest.mock import patch

from src.core.agent import build_prompt
from src.core.composition import BaselineSnapshot


# ── Baseline congelado da versão-base (pré-#308), canonical create-merge ──
# Medido com o build_prompt anterior (manual `@---` sempre embutido + regras de
# diretório verbosas) e o steering anterior (com o exemplo de branch redundante).
#   - prompt_dinamico_estatico_chars: conteúdo INVARIANTE do prompt (linhas
#     comuns a duas tarefas distintas) na versão-base.
#   - prompt_dinamico_chars: prompt completo da fixture canônica na versão-base.
#   - contexto_sempre_carregado_chars: steering da versão-base.
BASELINE = BaselineSnapshot(
    prompt_dinamico_estatico_chars=4311,
    prompt_dinamico_chars=4858,
    contexto_sempre_carregado_chars=4392,
)


def canonical_config() -> dict:
    return {
        "project": {
            "name": "Esteira Agêntica",
            "summary": "Esteira de board único.",
            "humans": [{"name": "Breno", "role": "dono do produto"}],
        },
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": {
                "base": "main",
                "feature": {
                    "prefix": "feature", "create": "main", "merge": "main",
                    "branch_pattern": "feature/{id}-{slug}",
                },
            },
        },
        "agents": {
            "kiro-cli": {"dev": {"name": "engineering", "model": "claude"}}
        },
        "boards": {
            "platform": "github",
            "entrega": {
                "name": "Entrega", "flow": "feature",
                "columns": {"desenvolvimento": {"name": "Desenvolvimento", "agent": "dev"}},
            },
        },
    }


def make_task(tmp_path: Path, *, gitevents: str = "create-merge",
              issue_id: str = "308", slug: str = "foo",
              col_overrides: dict | None = None,
              board_id: str = "entrega", col_id: str = "desenvolvimento",
              body: str | None = None,
              change: dict | None = None,
              issue_labels: list[str] | None = None) -> dict:
    issue_dir = tmp_path / ".pipe" / "boards" / board_id / col_id
    issue_dir.mkdir(parents=True, exist_ok=True)
    body_path = issue_dir / f"{issue_id}-{slug}-body.md"
    body_path.write_text(body or f"# {slug}\n\nDescrição.\n", encoding="utf-8")

    column = {
        "name": "Desenvolvimento", "agent": "dev", "gitevents": gitevents,
        "target-prompt": "Execute a tarefa",
        "change": {"advance": "execucao-testes"} if change is None else change,
    }
    if col_overrides:
        column.update(col_overrides)

    issue = {"id": issue_id, "body_path": str(body_path)}
    if issue_labels is not None:
        issue["labels"] = issue_labels

    return {
        "board_id": board_id,
        "board": {"flow": "feature", "repo": "main"},
        "col_id": col_id,
        "column": column,
        "issue": issue,
    }


def prompt_for(tmp_path: Path, config: dict, task: dict) -> str:
    boards_dir = tmp_path / ".pipe" / "boards"
    with patch("src.core.agent.BOARDS_DIR", boards_dir):
        return build_prompt(config, task)


def normalize(text: str, tmp_path: Path) -> str:
    """Remove a variação de comprimento dos caminhos absolutos do tmp_path.

    A medição estrutural (CA-1/CA-2) não deve depender do comprimento do
    diretório temporário do ambiente de teste. Substituímos o prefixo do
    tmp_path por um marcador fixo para a medição ser determinística.
    """
    return text.replace(str(tmp_path.resolve()), "<ROOT>").replace(str(tmp_path), "<ROOT>")


def static_chars(p1: str, p2: str) -> int:
    """Conteúdo ESTÁTICO = linhas comuns a dois prompts de tarefas distintas."""
    common = set(p1.splitlines()) & set(p2.splitlines())
    return sum(len(line) for line in common)


class FakeAdapterNoTokens:
    """Adapter de referência que NÃO expõe contagem de tokens (CA-17)."""
    name = "kiro-cli"


class FakeAdapterWithTokens:
    """Adapter que expõe contagem de tokens (prova de degradação suave)."""
    name = "fake-tokens"

    def input_token_count(self, prompt: str) -> int:
        return max(1, len(prompt) // 4)
