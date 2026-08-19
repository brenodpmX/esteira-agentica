"""Testes do bloco de Git Setup / Pull Request gerado por build_prompt.

Bug #108 — PR #105 da story #74 nasceu de base errada (`main` em vez de `epic`),
gerando conflitos `add/add` e diff poluído.

Causa raiz no código: o Git Setup de `gitevents: create` era emitido como dois
comandos independentes:

    git checkout <origem> && git pull origin <origem>
    git checkout -b <branch>

A segunda linha executa mesmo se a primeira falhar, criando a branch a partir do
HEAD corrente — base errada e silenciosa.

Correções cobertas aqui:
  - C1: criação atômica `git checkout -b <branch> origin/<origem>`
  - C2: guard `git merge-base --is-ancestor origin/<merge>` antes do `gh pr create`

Nota metodológica (C5): impacto de merge NÃO se mede com
`git diff <base> <branch>` (que mostra divergência entre pontas), e sim com
`git merge-tree --write-tree <base> <branch>` ou `gh pr view <n> --json mergeable`.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.agent import build_prompt


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures / helpers
# ══════════════════════════════════════════════════════════════════════════════

def _config() -> dict:
    """Config com os três flows reais do pipe.yml (origens distintas)."""
    return {
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": {
                "base": "main",
                "hotfix": {"prefix": "hotfix", "create": "main", "merge": "main"},
                "epic": {"prefix": "epic", "create": "main", "merge": "main"},
                "story": {"prefix": "story", "create": "epic", "merge": "epic"},
                "feature": {"prefix": "feature", "create": "epic", "merge": "epic"},
            },
        },
        "agents": {
            "kiro-cli": {
                "dev": {"name": "engineering", "model": "claude-sonnet-4"},
            }
        },
    }


def _task(tmp_path: Path, flow: str = "story", gitevents: str = "create",
          issue_id: str = "74", slug: str = "my-feature") -> dict:
    issue_dir = tmp_path / ".pipe" / "boards" / "myboard" / "doing"
    issue_dir.mkdir(parents=True, exist_ok=True)

    body_path = issue_dir / f"{issue_id}-{slug}-body.md"
    body_path.write_text("# My Feature\n\nDescrição.\n", encoding="utf-8")

    return {
        "board_id": "myboard",
        "board": {"flow": flow, "repo": "main"},
        "col_id": "doing",
        "column": {
            "name": "Doing",
            "agent": "dev",
            "gitevents": gitevents,
            "target-prompt": "Execute a tarefa",
            "change": {"advance": "done"},
        },
        "issue": {"id": issue_id, "body_path": str(body_path)},
    }


def _prompt(tmp_path: Path, flow: str = "story", gitevents: str = "create",
            issue_id: str = "74", slug: str = "my-feature") -> str:
    config = _config()
    task = _task(tmp_path, flow=flow, gitevents=gitevents,
                 issue_id=issue_id, slug=slug)
    boards_dir = tmp_path / ".pipe" / "boards"
    with patch("src.core.agent.BOARDS_DIR", boards_dir):
        return build_prompt(config, task)


# ══════════════════════════════════════════════════════════════════════════════
# C1 — Criação atômica da branch a partir de origin/<origem>
# ══════════════════════════════════════════════════════════════════════════════

class TestCriacaoAtomicaDeBranch:
    """`git checkout -b <branch> origin/<origem>` — sem fallback para HEAD."""

    @pytest.mark.parametrize("flow,origem", [
        ("story", "epic"),
        ("feature", "epic"),
        ("hotfix", "main"),
        ("epic", "main"),
    ])
    def test_branch_nasce_de_origin_da_origem_do_flow(self, tmp_path, flow, origem):
        prompt = _prompt(tmp_path, flow=flow, gitevents="create")
        esperado = f"git checkout -b {flow}74-74-my-feature origin/{origem}"
        assert esperado in prompt, (
            f"flow '{flow}' deve criar a branch a partir de origin/{origem} "
            f"num único comando. Esperado: '{esperado}'"
        )

    @pytest.mark.parametrize("flow", ["story", "feature", "hotfix", "epic"])
    def test_nao_usa_checkout_da_origem_com_and(self, tmp_path, flow):
        """A forma frágil `git checkout <origem> && git pull` foi removida."""
        prompt = _prompt(tmp_path, flow=flow, gitevents="create")
        origem = _config()["git"]["flow"][flow]["create"]
        assert f"git checkout {origem} &&" not in prompt, (
            "o encadeamento `git checkout <origem> && git pull` permite que o "
            "`checkout -b` seguinte crie a branch do HEAD corrente (bug #108)"
        )

    def test_nao_emite_checkout_b_sem_base_explicita(self, tmp_path):
        """Nenhum `checkout -b <branch>` sem a base `origin/<origem>`."""
        prompt = _prompt(tmp_path, flow="story", gitevents="create")
        assert "git checkout -b story74-74-my-feature\n" not in prompt, \
            "`git checkout -b <branch>` sem base explícita usa o HEAD corrente"

    def test_nao_usa_flag_B_que_reescreve_branch_existente(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="create")
        assert "git checkout -B " not in prompt, \
            "`-B` reescreveria uma branch local homônima existente"

    def test_fetch_precede_a_criacao_da_branch(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="create")
        assert prompt.index("git fetch origin") < prompt.index("git checkout -b "), \
            "o fetch deve atualizar origin/<origem> antes do checkout -b"

    def test_create_merge_tambem_usa_criacao_atomica(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="create-merge")
        assert "git checkout -b story74-74-my-feature origin/epic" in prompt

    def test_no_branch_nao_gera_git_setup(self, tmp_path):
        """Regressão: `no-branch` continua sem bloco de Git Setup."""
        prompt = _prompt(tmp_path, flow="story", gitevents="no-branch")
        assert "## Git Setup" not in prompt
        assert "git checkout -b" not in prompt

    def test_use_nao_cria_branch_da_origem(self, tmp_path):
        """`use` opera na branch existente da issue, não na origem do flow."""
        prompt = _prompt(tmp_path, flow="story", gitevents="use")
        assert "origin/story74-74-my-feature" in prompt
        assert "git checkout -b story74-74-my-feature origin/epic" not in prompt


# ══════════════════════════════════════════════════════════════════════════════
# C2 — Guard de base atualizada antes de abrir o PR
# ══════════════════════════════════════════════════════════════════════════════

class TestGuardDeBaseAtualizadaNoPR:
    """A branch deve conter a ponta do alvo de merge antes do `gh pr create`."""

    @pytest.mark.parametrize("gitevents", ["merge", "create-merge"])
    def test_guard_presente_para_merge_e_create_merge(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, flow="story", gitevents=gitevents)
        assert "git merge-base --is-ancestor origin/epic HEAD" in prompt, \
            "o PR deve verificar que a branch já contém a ponta do alvo de merge"
        assert "git merge origin/epic" in prompt, \
            "se a base estiver defasada, integre o alvo antes de abrir o PR"

    def test_guard_usa_alvo_de_merge_do_flow(self, tmp_path):
        prompt = _prompt(tmp_path, flow="hotfix", gitevents="merge")
        assert "git merge-base --is-ancestor origin/main HEAD" in prompt
        assert "origin/epic" not in prompt

    def test_guard_precede_o_gh_pr_create(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="merge")
        assert prompt.index("merge-base --is-ancestor") < prompt.index("gh pr create"), \
            "a verificação de base deve ocorrer antes de abrir o PR"

    def test_push_apos_o_merge_do_alvo(self, tmp_path):
        """O merge de integração precisa subir antes do PR ser aberto."""
        prompt = _prompt(tmp_path, flow="story", gitevents="merge")
        pr_section = prompt[prompt.index("## Pull Request"):]
        assert "git push origin story74-74-my-feature" in pr_section

    @pytest.mark.parametrize("gitevents", ["create", "use", "no-branch"])
    def test_guard_ausente_quando_nao_ha_pr(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, flow="story", gitevents=gitevents)
        assert "## Pull Request" not in prompt
        assert "merge-base --is-ancestor" not in prompt
