"""Testes da preparação de git gerada por build_prompt — forma DESCRITIVA (E3).

Antes (até F0.5) o `build_prompt` emitia scripts bash prontos (`git checkout -b`,
`gh pr create`, etc). A partir de F1.1 (decisão E3) esses blocos viram
INSTRUÇÕES descritivas: o COMO fica no steering ("Git — como operar") e o
prompt passa apenas o objetivo + as proteções, guiado pelas anotações do
`-body.md` (`branch pai` = origem; `branch` = trabalho) e pelo `branch_pattern`
do flow (E1). O agente é quem cria/reutiliza a branch e grava o nome em `branch:`.

Este arquivo valida a forma descritiva e as proteções do bug #108 EXPRESSAS EM
PROSA (não mais o bash):

  Bug #108 — PR #105 da story #74 nasceu de base errada (`main` em vez de `epic`),
  gerando conflitos `add/add` e diff poluído. A causa raiz foi um Git Setup em
  duas etapas onde o `checkout -b` criava a branch a partir do HEAD corrente.

Proteções a preservar (agora em prosa):
  - P1: criação ATÔMICA a partir de `origin/<origem>`, NUNCA do HEAD corrente.
  - P2: antes de abrir PR, a branch deve CONTER A PONTA do alvo de merge.
  - P3: idempotência — reutiliza a branch se `branch:` já tem nome.
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
    """Config com os flows reais do pipe.yml (origens distintas + branch_pattern)."""
    return {
        "git": {
            "repo": {"main": "git@github.com:user/repo.git"},
            "flow": {
                "base": "main",
                "hotfix": {"prefix": "hotfix", "create": "main", "merge": "main",
                           "branch_pattern": "hotfix/{id}-{slug}"},
                "epic": {"prefix": "epic", "create": "main", "merge": "main",
                         "branch_pattern": "epic/{id}-{slug}"},
                "story": {"prefix": "story", "create": "epic", "merge": "epic",
                          "branch_pattern": "story/{id}-{slug}"},
                "feature": {"prefix": "feature", "create": "epic", "merge": "epic",
                            "branch_pattern": "feature/{id}-{slug}"},
            },
        },
        "agents": {
            "kiro-cli": {
                "dev": {"name": "engineering", "model": "claude-sonnet-4"},
            }
        },
    }


def _task(tmp_path: Path, flow: str = "story", gitevents: str = "create",
          issue_id: str = "74", slug: str = "my-feature",
          body: str | None = None) -> dict:
    issue_dir = tmp_path / ".pipe" / "boards" / "myboard" / "doing"
    issue_dir.mkdir(parents=True, exist_ok=True)

    body_path = issue_dir / f"{issue_id}-{slug}-body.md"
    body_path.write_text(body or "# My Feature\n\nDescrição.\n", encoding="utf-8")

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
            issue_id: str = "74", slug: str = "my-feature",
            body: str | None = None) -> str:
    config = _config()
    task = _task(tmp_path, flow=flow, gitevents=gitevents,
                 issue_id=issue_id, slug=slug, body=body)
    boards_dir = tmp_path / ".pipe" / "boards"
    with patch("src.core.agent.BOARDS_DIR", boards_dir):
        return build_prompt(config, task)


def _body_with_annotations(branch: str = "(ainda não criada)",
                           branch_pai: str | None = None) -> str:
    lines = ["# My Feature", "", "Descrição.", "", "📝"]
    if branch_pai is not None:
        lines.append(f"branch pai: {branch_pai}")
    lines.append(f"branch: {branch}")
    return "\n".join(lines) + "\n"


# ══════════════════════════════════════════════════════════════════════════════
# Forma DESCRITIVA — não emite mais script bash pronto
# ══════════════════════════════════════════════════════════════════════════════

class TestFormaDescritivaSemBash:
    """O prompt não deve mais conter os comandos git/gh prontos."""

    @pytest.mark.parametrize("gitevents", ["create", "use", "merge", "create-merge"])
    def test_nao_emite_bloco_bash(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, gitevents=gitevents)
        assert "```bash" not in prompt, "a preparação de git não é mais um script bash"

    @pytest.mark.parametrize("gitevents", ["create", "use", "merge", "create-merge"])
    def test_nao_emite_comandos_git_prontos(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, gitevents=gitevents)
        assert "git checkout -b " not in prompt
        assert "git checkout -B " not in prompt
        assert "gh pr create" not in prompt

    def test_nao_monta_nome_de_branch_fixo(self, tmp_path):
        """A esteira não monta mais `<prefix><id>-<slug>`; passa o padrão."""
        prompt = _prompt(tmp_path, flow="story", gitevents="create")
        assert "story74-74-my-feature" not in prompt


# ══════════════════════════════════════════════════════════════════════════════
# P1 — Criação ATÔMICA a partir de origin/<origem>, NUNCA do HEAD (em prosa)
# ══════════════════════════════════════════════════════════════════════════════

class TestCriacaoAtomicaEmProsa:

    @pytest.mark.parametrize("flow,origem", [
        ("story", "epic"),
        ("feature", "epic"),
        ("hotfix", "main"),
        ("epic", "main"),
    ])
    def test_instrui_criar_atomica_de_origin_da_origem(self, tmp_path, flow, origem):
        prompt = _prompt(tmp_path, flow=flow, gitevents="create")
        assert "ATÔMICA" in prompt or "atômica" in prompt.lower()
        assert f"origin/{origem}" in prompt, (
            f"flow '{flow}' deve instruir criar a branch a partir de origin/{origem}"
        )

    @pytest.mark.parametrize("gitevents", ["create", "create-merge"])
    def test_proibe_criar_do_head_corrente(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, gitevents=gitevents)
        assert "NUNCA" in prompt and "HEAD" in prompt, (
            "a prosa deve proibir criar a branch a partir do HEAD corrente (bug #108)"
        )

    def test_referencia_o_bug_108(self, tmp_path):
        prompt = _prompt(tmp_path, gitevents="create")
        assert "#108" in prompt

    def test_usa_branch_pattern_do_flow_como_instrucao(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="create")
        assert "story/{id}-{slug}" in prompt, (
            "o padrão de nome do flow deve ser passado como instrução ao agente"
        )

    def test_instrui_gravar_nome_real_em_branch(self, tmp_path):
        prompt = _prompt(tmp_path, gitevents="create")
        assert "`branch:`" in prompt and "grave" in prompt.lower()

    def test_create_merge_tambem_cria(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="create-merge")
        assert "origin/epic" in prompt
        assert "ATÔMICA" in prompt

    def test_no_branch_nao_gera_secao_git(self, tmp_path):
        prompt = _prompt(tmp_path, gitevents="no-branch")
        assert "## Git — preparação da branch" not in prompt
        assert "## Versionar" not in prompt

    def test_use_e_merge_nao_criam_da_origem(self, tmp_path):
        """`use`/`merge` operam na branch existente — não criam da origem do flow."""
        for gitevents in ("use", "merge"):
            prompt = _prompt(tmp_path, flow="story", gitevents=gitevents)
            assert "ATÔMICA" not in prompt, (
                f"'{gitevents}' não deve instruir criação de branch nova"
            )
            assert "não cria uma branch nova" in prompt


# ══════════════════════════════════════════════════════════════════════════════
# P1b — Origem guiada pela anotação `branch pai` (precedência sobre o flow)
# ══════════════════════════════════════════════════════════════════════════════

class TestOrigemDasAnotacoes:

    def test_branch_pai_tem_precedencia_sobre_create_do_flow(self, tmp_path):
        body = _body_with_annotations(branch_pai="release-2.0")
        prompt = _prompt(tmp_path, flow="story", gitevents="create", body=body)
        assert "origin/release-2.0" in prompt, (
            "a origem deve vir da anotação `branch pai` quando presente"
        )

    def test_sem_branch_pai_usa_origem_do_flow(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="create")
        assert "origin/epic" in prompt


# ══════════════════════════════════════════════════════════════════════════════
# P3 — Idempotência: reutiliza a branch se `branch:` já tem nome (em prosa)
# ══════════════════════════════════════════════════════════════════════════════

class TestIdempotenciaEmProsa:

    @pytest.mark.parametrize("gitevents", ["create", "use", "merge", "create-merge"])
    def test_instrui_reutilizar_branch_existente(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, gitevents=gitevents)
        assert "reutilize" in prompt.lower() or "reutilizar" in prompt.lower()
        assert "idempotente" in prompt.lower()

    def test_reuso_nao_recria_branch(self, tmp_path):
        prompt = _prompt(tmp_path, gitevents="create")
        assert "NÃO crie outra branch" in prompt


# ══════════════════════════════════════════════════════════════════════════════
# P2 — Guard de base atualizada antes de abrir o PR (em prosa)
# ══════════════════════════════════════════════════════════════════════════════

class TestGuardDeBaseNoPREmProsa:

    @pytest.mark.parametrize("gitevents", ["merge", "create-merge"])
    def test_exige_conter_a_ponta_do_alvo(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, flow="story", gitevents=gitevents)
        assert "CONTÉM A PONTA" in prompt or "contém a ponta" in prompt.lower()
        assert "origin/epic" in prompt

    def test_guard_usa_alvo_de_merge_do_flow(self, tmp_path):
        prompt = _prompt(tmp_path, flow="hotfix", gitevents="merge")
        assert "origin/main" in prompt

    def test_confirma_pr_existente_em_vez_de_duplicar(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="merge")
        assert "confirme-o em vez de criar outro" in prompt

    @pytest.mark.parametrize("gitevents", ["create", "use", "no-branch"])
    def test_secao_pr_ausente_quando_nao_ha_merge(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, flow="story", gitevents=gitevents)
        assert "## Abrir merge/PR" not in prompt


# ══════════════════════════════════════════════════════════════════════════════
# Versionar — commit/push sempre na branch de trabalho
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionar:

    @pytest.mark.parametrize("gitevents", ["create", "use", "merge", "create-merge"])
    def test_orienta_commit_push_na_branch_de_trabalho(self, tmp_path, gitevents):
        prompt = _prompt(tmp_path, gitevents=gitevents)
        assert "## Versionar (commit e push)" in prompt
        assert "branch de trabalho" in prompt

    def test_proibe_commit_na_base_ou_origem(self, tmp_path):
        prompt = _prompt(tmp_path, flow="story", gitevents="create")
        # base = main, origem = epic
        assert "`main`" in prompt and "`epic`" in prompt

    def test_no_branch_nao_versiona(self, tmp_path):
        prompt = _prompt(tmp_path, gitevents="no-branch")
        assert "## Versionar" not in prompt
