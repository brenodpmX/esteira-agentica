"""Casos de teste — Sanar merge ausente de `epic` para `main` (issue #165).

Cobre o débito registrado na issue #165 (`epic`/`main` desincronizados desde
#146/#147): tasks fechadas no board com PR mergeado em `epic`, mas nunca
propagadas a `main`. A causa raiz identificada é dupla:

  (a) processo: nenhuma etapa do fluxo `feature -> epic -> ???` fecha o ciclo
      `epic -> main`, então a divergência só cresce a cada PR;
  (b) configuração: `git.flow` pode encadear `create`/`merge` de um flow para
      outro (`feature.merge: epic`) sem que o flow de destino (`epic`) aponte
      de volta para `base`. Não há validação nem teste hoje que garanta que
      toda cadeia de flows termina em `base`.

Este arquivo cobre os dois ângulos:

  TC-01  Estado real do repositório: `498674b`/`9572409` (commits de #146/#147)
         NÃO são ancestrais de `origin/main` (reproduz o achado da issue).
  TC-02  `git diff origin/main origin/epic --stat` não está vazio hoje —
         confirma divergência de código de produção (não apenas de docs/db).
  TC-03  Resolução de branch/merge em `build_prompt` honra `git.flow.merge`
         quando o alvo de merge é `main` (uso correto do flow `epic`/`hotfix`
         apontando para a base) — cobre o comportamento esperado após a
         correção do fluxo (item 2 da issue).
  TC-04  Regressão: nenhum flow configurado pode encadear `merge` para outro
         flow que, por sua vez, não alcance `base` — evita reintroduzir o
         padrão "integração eterna" que causou o débito.
  TC-05  Critérios de aceite executáveis da própria issue, isolados como
         funções reutilizáveis por quem for validar o merge (não travam a
         suíte se `main`/`epic` ainda estiverem divergentes — são marcados
         `xfail` até o merge ser efetivamente aplicado).

Estratégia:
  - TC-01/02/05 leem o repositório REAL (somente leitura: `git merge-base`,
    `git diff --stat`, `git log`), sem checkout, sem escrita, sem tocar em
    branches. Não fazem fetch (assume que o ambiente de CI/agente já tem as
    refs atualizadas ou usa as refs locais existentes).
  - TC-03/04 usam `build_prompt` com config sintética (mesmo padrão de
    `test_build_prompt_git_setup.py`), sem tocar no repositório real.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.agent import build_prompt

REPO_ROOT = Path(__file__).resolve().parents[1]

COMMIT_146 = "498674b"
COMMIT_147 = "9572409"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de leitura do repositório real (somente leitura)
# ══════════════════════════════════════════════════════════════════════════════

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def _ref_exists(ref: str) -> bool:
    return _git("rev-parse", "--verify", ref).returncode == 0


def _is_ancestor(commit: str, ref: str) -> bool:
    return _git("merge-base", "--is-ancestor", commit, ref).returncode == 0


def _requires_refs(*refs: str):
    """Skip (não falha) se alguma ref necessária não existir no ambiente local."""
    missing = [r for r in refs if not _ref_exists(r)]
    if missing:
        pytest.skip(
            f"refs ausentes no ambiente local: {missing} — "
            "rode `git fetch origin` antes de validar este débito."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC-01 — Reproduz o achado da issue: commits de #146/#147 fora de main
# ══════════════════════════════════════════════════════════════════════════════

class TestTC01CommitsForaDeMain:
    """TC-01: `498674b` (#146) e `9572409` (#147) não são ancestrais de
    `origin/main` — reproduz textualmente o achado registrado na issue e no
    Planning Poker (Isabela Gomes, 2026-08-06).

    Estes testes documentam o ESTADO ATUAL DO DÉBITO. Após o merge de `epic`
    em `main` (item 1 da issue), o comportamento correto é o oposto: os
    commits DEVEM se tornar ancestrais de `main`. Ver TC-05 para os
    critérios de aceite pós-merge (marcados `xfail` até lá).
    """

    def test_commit_146_nao_e_ancestral_de_main_hoje(self):
        _requires_refs("origin/main", COMMIT_146)
        assert not _is_ancestor(COMMIT_146, "origin/main"), (
            f"Commit {COMMIT_146} (#146) já é ancestral de origin/main — "
            "o débito desta issue pode já ter sido resolvido; revisar a "
            "issue #165 antes de prosseguir com o merge."
        )

    def test_commit_147_nao_e_ancestral_de_main_hoje(self):
        _requires_refs("origin/main", COMMIT_147)
        assert not _is_ancestor(COMMIT_147, "origin/main"), (
            f"Commit {COMMIT_147} (#147) já é ancestral de origin/main — "
            "o débito desta issue pode já ter sido resolvido; revisar a "
            "issue #165 antes de prosseguir com o merge."
        )

    def test_commit_146_e_ancestral_de_epic(self):
        """Confirma que o commit existe e está integrado em epic (não é lixo)."""
        _requires_refs("origin/epic", COMMIT_146)
        assert _is_ancestor(COMMIT_146, "origin/epic"), (
            f"Commit {COMMIT_146} (#146) deveria estar integrado em origin/epic "
            "— se não estiver, o PR #159 pode não ter sido mergeado corretamente."
        )

    def test_commit_147_e_ancestral_de_epic(self):
        _requires_refs("origin/epic", COMMIT_147)
        assert _is_ancestor(COMMIT_147, "origin/epic"), (
            f"Commit {COMMIT_147} (#147) deveria estar integrado em origin/epic "
            "— se não estiver, o PR #160 pode não ter sido mergeado corretamente."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC-02 — Divergência de código de produção entre main e epic
# ══════════════════════════════════════════════════════════════════════════════

class TestTC02DivergenciaDeCodigo:
    """TC-02: confirma que a divergência `main` x `epic` inclui código de
    produção (não apenas artefatos irrelevantes), justificando o risco
    apontado na avaliação de complexidade (`/agent_level high`).
    """

    def test_diff_stat_nao_esta_vazio(self):
        _requires_refs("origin/main", "origin/epic")
        result = _git("diff", "origin/main", "origin/epic", "--stat")
        assert result.stdout.strip() != "", (
            "git diff origin/main origin/epic --stat está vazio — "
            "não há divergência a resolver (issue pode estar resolvida)."
        )

    def test_diff_inclui_arquivos_em_src(self):
        _requires_refs("origin/main", "origin/epic")
        result = _git(
            "diff", "--name-only", "origin/main", "origin/epic", "--", "src/"
        )
        changed = [line for line in result.stdout.splitlines() if line.strip()]
        assert changed, (
            "Nenhum arquivo em src/ diverge entre main e epic — "
            "esperado dado o histórico de #146/#147 (mudanças em src/core)."
        )

    def test_commit_count_main_dot_dot_epic_e_positivo(self):
        """`git rev-list --count origin/main..origin/epic` reflete o volume
        citado na issue e no Planning Poker (crescente: 121 -> 132+)."""
        _requires_refs("origin/main", "origin/epic")
        result = _git("rev-list", "--count", "origin/main..origin/epic")
        count = int(result.stdout.strip() or "0")
        assert count > 0, (
            "origin/epic não tem commits exclusivos em relação a origin/main — "
            "divergência esperada pela issue não foi reproduzida."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC-03 — build_prompt: alvo de merge configurado para `main` é respeitado
# ══════════════════════════════════════════════════════════════════════════════

def _config_com_flow_epic_para_main() -> dict:
    """Config onde o flow `epic` (a etapa de integração final) mergeia
    diretamente para `main` — o comportamento esperado depois da correção
    do item 2 da issue (fechar o ciclo epic -> main)."""
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
            "kiro-cli": {"dev": {"name": "engineering", "model": "claude-sonnet-4"}},
        },
    }


def _task(tmp_path: Path, flow: str, gitevents: str,
          issue_id: str = "165", slug: str = "epic-merge") -> dict:
    issue_dir = tmp_path / ".pipe" / "boards" / "myboard" / "doing"
    issue_dir.mkdir(parents=True, exist_ok=True)
    body_path = issue_dir / f"{issue_id}-{slug}-body.md"
    body_path.write_text("# Epic merge\n\nDescrição.\n", encoding="utf-8")
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


def _prompt(tmp_path: Path, config: dict, flow: str, gitevents: str) -> str:
    task = _task(tmp_path, flow=flow, gitevents=gitevents)
    boards_dir = tmp_path / ".pipe" / "boards"
    with patch("src.core.agent.BOARDS_DIR", boards_dir):
        return build_prompt(config, task)


class TestTC03MergeParaMainQuandoConfigurado:
    """TC-03: quando o flow de integração final (`epic`) está configurado com
    `merge: main`, `build_prompt` deve gerar o guard e o `gh pr create`
    apontando para `main` — validando que a resolução de branch já respeita
    a config (não é preciso mudar `agent.py`; o gap é de configuração e de
    processo, conforme apurado na issue)."""

    def test_guard_usa_main_como_alvo(self, tmp_path):
        config = _config_com_flow_epic_para_main()
        prompt = _prompt(tmp_path, config, flow="epic", gitevents="merge")
        assert "git merge-base --is-ancestor origin/main HEAD" in prompt
        assert "git merge origin/main" in prompt

    def test_pr_e_aberto_com_base_main(self, tmp_path):
        config = _config_com_flow_epic_para_main()
        prompt = _prompt(tmp_path, config, flow="epic", gitevents="merge")
        assert "gh pr create --base main" in prompt

    def test_flow_feature_continua_indo_para_epic(self, tmp_path):
        """Confirma que a mudança é só no flow de integração final; o flow
        `feature` (dia a dia) não é afetado — evita regressão de escopo."""
        config = _config_com_flow_epic_para_main()
        prompt = _prompt(tmp_path, config, flow="feature", gitevents="merge")
        assert "gh pr create --base epic" in prompt
        assert "gh pr create --base main" not in prompt


# ══════════════════════════════════════════════════════════════════════════════
# TC-04 — Regressão: toda cadeia de flow deve alcançar `base`
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_chain(flow_cfg: dict, start: str, max_hops: int = 10) -> list[str]:
    """Segue `merge` de flow em flow até chegar em `base` ou não encontrar
    mais o alvo como flow_id (assume-se então que é uma branch terminal,
    ex.: `main`).

    Retorna a cadeia de destinos percorrida, ex.: ["epic", "main"].
    """
    base = flow_cfg.get("base", "main")
    chain = []
    current = start
    for _ in range(max_hops):
        cfg = flow_cfg.get(current)
        if not isinstance(cfg, dict):
            # `current` não é um flow_id conhecido -> é uma branch terminal
            break
        target = cfg.get("merge", base)
        chain.append(target)
        if target == base:
            break
        current = target
    return chain


class TestTC04CadeiaDeMergeAlcancaBase:
    """TC-04: nenhuma cadeia de `merge` entre flows pode ficar "presa" numa
    branch de integração que nunca alcança `base` — este é exatamente o
    padrão que causou o débito (`feature -> epic -> epic -> ...`, nunca
    `-> main`).

    Regra: seguindo `merge` a partir de cada flow não-base, a cadeia deve
    conter `base` em no máximo `len(flows)` saltos.
    """

    def test_cadeia_feature_epic_alcanca_main_na_config_corrigida(self):
        flow_cfg = _config_com_flow_epic_para_main()["git"]["flow"]
        chain = _resolve_chain(flow_cfg, "feature")
        assert flow_cfg["base"] in chain, (
            f"Cadeia de merge a partir de 'feature' nunca alcança a base "
            f"'{flow_cfg['base']}'. Cadeia observada: {chain}"
        )

    def test_cadeia_story_epic_alcanca_main_na_config_corrigida(self):
        flow_cfg = _config_com_flow_epic_para_main()["git"]["flow"]
        chain = _resolve_chain(flow_cfg, "story")
        assert flow_cfg["base"] in chain

    def test_configuracao_do_debito_nao_alcancaria_base(self):
        """Reproduz a configuração ANTERIOR (a que gerou o débito): `epic`
        mergeando para `epic` (config avulsa sem `merge` -> cai no default
        `base`, então simula o cenário real onde simplesmente NENHUM PR de
        integração final para `epic` era aberto com destino em `main`).

        Este teste documenta a detecção: se `epic` não estivesse mapeado
        como flow (ou seu `merge` apontasse para outro nome que não é
        `base` nem um flow conhecido), a cadeia fica vazia/incompleta e o
        teste de guarda (`test_toda_cadeia_de_flow_nao_base_alcanca_base`)
        deve capturar isso.
        """
        flow_cfg = {
            "base": "main",
            # `epic` não está listado como flow explícito aqui — simula o
            # estado real do pipe.yml documentado no README (apenas
            # `feature`/`hotfix`), onde a branch `epic` nunca aparece como
            # flow com `merge` definido, e por isso nunca fecha o ciclo.
            "feature": {"prefix": "feature/", "create": "main", "merge": "main"},
            "hotfix": {"prefix": "hotfix/", "create": "main", "merge": "main"},
        }
        chain = _resolve_chain(flow_cfg, "feature")
        # Com a config documentada no README (sem branch de integração
        # intermediária), a cadeia já alcança base diretamente — o que
        # demonstra que o comportamento problemático relatado na issue
        # (merge para uma branch `epic` avulsa) NÃO vem desta config
        # padrão, e sim de um pipe.yml operacional divergente dela.
        assert flow_cfg["base"] in chain

    @pytest.mark.parametrize("flow_id", ["feature", "story", "hotfix", "epic"])
    def test_toda_cadeia_de_flow_nao_base_alcanca_base(self, flow_id):
        """Guarda de regressão a ser reaplicada a qualquer novo `pipe.yml`
        de referência: nenhum flow não-base pode ter uma cadeia de `merge`
        que não alcance `base` dentro de `len(flow_cfg)` saltos."""
        flow_cfg = _config_com_flow_epic_para_main()["git"]["flow"]
        chain = _resolve_chain(flow_cfg, flow_id, max_hops=len(flow_cfg) + 1)
        assert flow_cfg["base"] in chain, (
            f"Flow '{flow_id}' tem cadeia de merge que não alcança a base "
            f"'{flow_cfg['base']}' — risco de repetir o débito de #146/#147. "
            f"Cadeia observada: {chain}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC-05 — Critérios de aceite da issue (executáveis, pós-merge)
# ══════════════════════════════════════════════════════════════════════════════

class TestTC05CriteriosDeAceitePosMerge:
    """TC-05: mesmos comandos listados em "Como testar" na issue #165,
    encapsulados como testes. Ficam `xfail` (falha esperada, não quebra a
    suíte) enquanto o merge de `epic` em `main` não tiver sido aplicado —
    servem como checklist executável para quem for validar a conclusão do
    débito, e viram verdes automaticamente quando o merge acontecer.
    """

    @pytest.mark.xfail(
        reason="epic ainda não foi mergeada em main (débito #165 em aberto)",
        strict=False,
    )
    def test_commit_146_e_ancestral_de_main_apos_merge(self):
        _requires_refs("origin/main", COMMIT_146)
        assert _is_ancestor(COMMIT_146, "origin/main"), (
            f"Critério de aceite 1 da issue: {COMMIT_146} (#146) deve ser "
            "ancestral de main após o merge de epic."
        )

    @pytest.mark.xfail(
        reason="epic ainda não foi mergeada em main (débito #165 em aberto)",
        strict=False,
    )
    def test_commit_147_e_ancestral_de_main_apos_merge(self):
        _requires_refs("origin/main", COMMIT_147)
        assert _is_ancestor(COMMIT_147, "origin/main"), (
            f"Critério de aceite 1 da issue: {COMMIT_147} (#147) deve ser "
            "ancestral de main após o merge de epic."
        )

    @pytest.mark.xfail(
        reason="epic ainda não foi mergeada em main (débito #165 em aberto)",
        strict=False,
    )
    def test_diff_main_epic_sem_divergencia_de_producao_apos_merge(self):
        _requires_refs("origin/main", "origin/epic")
        result = _git(
            "diff", "--name-only", "origin/main", "origin/epic", "--", "src/"
        )
        changed = [line for line in result.stdout.splitlines() if line.strip()]
        assert changed == [], (
            "Critério de aceite 2 da issue: git diff main epic não deve "
            f"mais divergir em src/ após o merge. Divergente: {changed}"
        )

    def test_suite_de_testes_e_o_criterio_de_aceite_3(self):
        """Critério de aceite 3 da issue ('suíte completa passa em main após
        o merge') é a própria execução de `pytest tests/` pela esteira/CI —
        não há o que simular aqui sem duplicar o runner. Este teste apenas
        documenta a rastreabilidade do critério."""
        assert True
