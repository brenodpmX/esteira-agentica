"""Casos de teste — Remover branches integradas em `epic` — lote A.

Cobre o procedimento descrito na issue #78, parte da story #74 (épico #73):
confirmar via `git merge-base --is-ancestor` que as branches do lote A foram
absorvidas por `epic` e podem ser removidas com segurança do remoto.

As branches alvo desta issue são:
  - feature28-28-refatoracao_persistir_agent_level_via_label_agent_level_nivel_no_github
  - feature33-33-ajustar_copy_das_mensagens_de_erro_de_ssh_para_contexto_docker
  - feature34-34-implementar_funcao_preflight_de_verificacao_de_credenciais_no_arranque
  - feature35-35-integrar_preflight_ao_fluxo_de_boot_da_esteira
  - feature37-37-criar_docker_composeyml_com_servico_volumes_secret_e_envs

Diferença em relação à issue #77 (branches em `main`):
  - A base de comparação é `epic`, não `main`.
  - O critério de integração é `git merge-base --is-ancestor <branch> epic`
    (exit 0 = integrada), não `git log ^origin/main` (saída vazia = integrada).

Os testes usam repositórios Git temporários (bare + clones em tmp_path) para
simular os cenários do procedimento obrigatório sem tocar no remoto real.

  TC-01  branch totalmente absorvida por epic → merge-base --is-ancestor retorna exit 0
  TC-02  branch com commit exclusivo → merge-base --is-ancestor retorna exit não-zero
  TC-03  branch inexistente no remoto → ausência detectável, tratável sem erro crítico
  TC-04  delete de branch integrada no remoto → push --delete bem-sucedido
  TC-05  delete de branch inexistente → git push --delete retorna erro apropriado
  TC-06  git fetch --prune remove referências locais de branches deletadas do remoto
  TC-07  verificação abrange todas as 5 branches alvo do lote A (feature28/33/34/35/37)
  TC-08  lote parcial — branch não integrada bloqueia somente ela, demais prosseguem

Estratégia de isolamento:
  - Repositório bare em tmp_path/remote.git (simula origin)
  - Clone em tmp_path/repo (simula workdir do agente)
  - Branch `epic` criada explicitamente no bare
  - Nenhum acesso à rede; nenhuma dependência de credencial
"""

import subprocess
from pathlib import Path

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def git_repo(tmp_path):
    """Cria um repositório bare (remote) e um clone local com commit inicial
    em main e branch `epic` criada a partir de main.

    Retorna um dict com:
      - remote: Path para o bare repo (origin)
      - repo:   Path para o clone local (workdir)
    """
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"

    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(remote)],
        check=True, capture_output=True,
    )
    subprocess.run(["git", "clone", str(remote), str(repo)],
                   check=True, capture_output=True)

    subprocess.run(["git", "config", "user.email", "test@test.com"],
                   cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"],
                   cwd=str(repo), check=True, capture_output=True)

    # Commit inicial em main
    (repo / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(repo),
                   check=True, capture_output=True)

    # Cria branch epic a partir de main e publica no remoto
    subprocess.run(["git", "checkout", "-b", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    (repo / "epic_base.md").write_text("epic base\n")
    subprocess.run(["git", "add", "epic_base.md"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "chore: epic base"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)

    return {"remote": remote, "repo": repo}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _create_branch_integrated_in_epic(repo: Path, branch: str) -> None:
    """Cria branch a partir de epic, faz commit e merge de volta em epic."""
    subprocess.run(["git", "fetch", "origin"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "pull", "origin", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", branch], cwd=str(repo),
                   check=True, capture_output=True)
    (repo / f"{branch}.txt").write_text(f"content of {branch}\n")
    subprocess.run(["git", "add", "."], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"feat: {branch}"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(
        ["git", "merge", "--no-ff", branch, "-m", f"merge: {branch}"],
        cwd=str(repo), check=True, capture_output=True,
    )
    subprocess.run(["git", "push", "origin", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)


def _create_branch_unintegrated_from_epic(repo: Path, branch: str) -> None:
    """Cria branch a partir de epic com commit exclusivo (NÃO mergeada em epic)."""
    subprocess.run(["git", "fetch", "origin"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "pull", "origin", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", branch], cwd=str(repo),
                   check=True, capture_output=True)
    (repo / f"{branch}.txt").write_text(f"exclusive content of {branch}\n")
    subprocess.run(["git", "add", "."], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"feat: exclusive {branch}"],
                   cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)


def _is_ancestor(repo: Path, branch: str, base: str = "origin/epic") -> bool:
    """Executa git merge-base --is-ancestor origin/<branch> <base>.

    Retorna True se exit 0 (branch absorvida), False caso contrário.
    """
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"origin/{branch}", base],
        cwd=str(repo),
        capture_output=True,
    )
    return result.returncode == 0


# ─── TC-01: branch absorvida por epic → merge-base --is-ancestor exit 0 ──────


class TestTC01BranchIntegradaEmEpic:
    """TC-01: Confirmar que branch totalmente absorvida por epic retorna exit 0
    no comando `git merge-base --is-ancestor`.

    Critério de aceite da issue: saída `INTEGRADA` (exit 0) para cada branch.
    """

    def test_integrated_branch_is_ancestor_of_epic(self, git_repo):
        """Branch mergeada em epic → merge-base --is-ancestor retorna exit 0."""
        branch = "feature28-28-refatoracao_persistir_agent_level"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        assert _is_ancestor(git_repo["repo"], branch), (
            f"Branch '{branch}' mergeada em epic deve ser antepassada de "
            f"origin/epic (merge-base --is-ancestor exit 0)."
        )

    def test_exit_zero_means_safe_to_delete(self, git_repo):
        """Exit 0 de merge-base --is-ancestor confirma que a remoção é segura."""
        branch = "feature33-33-ajustar_copy_mensagens_erro"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor",
             f"origin/{branch}", "origin/epic"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        assert result.returncode == 0, (
            "Exit 0 é o sinal de segurança para remoção. "
            f"Retornou: {result.returncode}"
        )

    def test_integrated_branch_produces_no_stdout(self, git_repo):
        """merge-base --is-ancestor não produz saída stdout para branch integrada."""
        branch = "feature34-34-implementar_funcao_preflight"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor",
             f"origin/{branch}", "origin/epic"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
            text=True,
        )

        assert result.stdout.strip() == "", (
            "merge-base --is-ancestor não deve produzir saída stdout. "
            f"stdout: {result.stdout!r}"
        )


# ─── TC-02: branch não integrada → merge-base --is-ancestor exit não-zero ────


class TestTC02BranchNaoIntegradaEmEpic:
    """TC-02: Confirmar que branch com commit exclusivo (não mergeada em epic)
    retorna exit não-zero no `git merge-base --is-ancestor`.

    A lógica de parada obrigatória da issue: se o resultado for `NAO INTEGRADA`,
    parar imediatamente e não remover a branch.
    """

    def test_unintegrated_branch_is_not_ancestor_of_epic(self, git_repo):
        """Branch não mergeada em epic → merge-base --is-ancestor retorna exit não-zero."""
        branch = "feature-not-merged-in-epic"
        _create_branch_unintegrated_from_epic(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        assert not _is_ancestor(git_repo["repo"], branch), (
            f"Branch '{branch}' não mergeada em epic NÃO deve ser antepassada "
            f"de origin/epic (merge-base --is-ancestor exit não-zero)."
        )

    def test_nonzero_exit_must_block_deletion(self, git_repo):
        """Exit não-zero sinaliza que a remoção deve ser bloqueada."""
        branch = "feature-exclusive-unmerged"
        _create_branch_unintegrated_from_epic(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor",
             f"origin/{branch}", "origin/epic"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        assert result.returncode != 0, (
            "Exit não-zero detectado — remoção desta branch deve ser bloqueada."
        )

    def test_branch_created_after_epic_diverge_point_is_not_ancestor(self, git_repo):
        """Branch criada a partir de epic, mas sem merge, diverge de epic."""
        branch = "feature-diverged-from-epic"
        _create_branch_unintegrated_from_epic(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        is_anc = _is_ancestor(git_repo["repo"], branch)

        assert not is_anc, (
            "Branch divergida de epic (sem merge) não deve ser antepassada de epic."
        )


# ─── TC-03: branch inexistente no remoto ──────────────────────────────────────


class TestTC03BranchInexistenteNoRemoto:
    """TC-03: Se a branch já não existir no remoto, a verificação deve ser
    tratada como 'já removida' — não como erro crítico do procedimento.

    A issue especifica: 'Se a branch já não existir no remoto ao verificar,
    registrar no comentário e seguir.'
    """

    def test_merge_base_on_nonexistent_remote_branch_exits_nonzero(self, git_repo):
        """merge-base --is-ancestor em branch remota inexistente retorna exit não-zero."""
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor",
             "origin/branch-que-nao-existe", "origin/epic"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        assert result.returncode != 0, (
            "merge-base --is-ancestor em branch inexistente deve retornar "
            "exit não-zero (detecção de ausência)."
        )

    def test_git_push_delete_nonexistent_branch_returns_error(self, git_repo):
        """git push --delete de branch inexistente retorna exit não-zero."""
        result = subprocess.run(
            ["git", "push", "origin", "--delete", "branch-que-nao-existe"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        assert result.returncode != 0, (
            "git push --delete de branch inexistente deve retornar exit não-zero "
            "(não é erro de procedimento — branch já estava ausente)."
        )

    def test_branch_absence_detectable_via_branch_r(self, git_repo):
        """Ausência de branch é confirmável via git branch -r após fetch --prune."""
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
            text=True,
        )

        assert "origin/branch-que-nao-existe" not in result.stdout, (
            "Branch inexistente não deve aparecer em git branch -r."
        )

    def test_epic_branch_still_present_when_feature_absent(self, git_repo):
        """Ausência da feature branch não afeta a existência de origin/epic."""
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
            text=True,
        )

        assert "origin/epic" in result.stdout, (
            "origin/epic deve permanecer presente mesmo sem as branches de feature."
        )


# ─── TC-04: delete de branch integrada em epic ───────────────────────────────


class TestTC04DeleteBranchIntegradaEmEpic:
    """TC-04: git push origin --delete de branch já integrada em epic
    deve ter sucesso.
    """

    def test_push_delete_integrated_branch_succeeds(self, git_repo):
        """Remoção de branch integrada em epic → exit 0."""
        branch = "feature35-35-integrar-preflight-boot"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "push", "origin", "--delete", branch],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        assert result.returncode == 0, (
            f"git push --delete deve ter exit 0 para branch existente. "
            f"stderr: {result.stderr.decode()}"
        )

    def test_branch_absent_from_remote_after_delete(self, git_repo):
        """Após delete, branch não aparece mais em git branch -r."""
        branch = "feature37-37-docker-compose-to-delete"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)

        subprocess.run(["git", "push", "origin", "--delete", branch],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
            text=True,
        )

        assert f"origin/{branch}" not in result.stdout, (
            f"Branch '{branch}' não deve aparecer em 'git branch -r' após remoção."
        )

    def test_epic_content_intact_after_branch_delete(self, git_repo):
        """Remoção da branch não altera o hash de origin/epic."""
        branch = "feature-safe-delete-epic"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)

        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)
        result_before = subprocess.run(
            ["git", "rev-parse", "origin/epic"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        hash_before = result_before.stdout.strip()

        subprocess.run(["git", "push", "origin", "--delete", branch],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result_after = subprocess.run(
            ["git", "rev-parse", "origin/epic"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        hash_after = result_after.stdout.strip()

        assert hash_before == hash_after, (
            "O hash de origin/epic não deve mudar após remover uma branch integrada."
        )

    def test_main_content_intact_after_epic_branch_delete(self, git_repo):
        """Remoção de branch integrada em epic não afeta origin/main."""
        branch = "feature-delete-no-affect-main"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)

        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)
        result_before = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        hash_main_before = result_before.stdout.strip()

        subprocess.run(["git", "push", "origin", "--delete", branch],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result_after = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        hash_main_after = result_after.stdout.strip()

        assert hash_main_before == hash_main_after, (
            "O hash de origin/main não deve mudar ao remover branch integrada em epic."
        )


# ─── TC-05: delete de branch inexistente ──────────────────────────────────────


class TestTC05DeleteBranchInexistente:
    """TC-05: git push --delete em branch inexistente retorna erro não-zero.

    Esse comportamento é esperado e não deve interromper o procedimento como
    falha crítica — a branch já está ausente, que é o estado desejado.
    """

    def test_delete_nonexistent_branch_exits_nonzero(self, git_repo):
        """git push --delete de branch inexistente retorna exit não-zero."""
        result = subprocess.run(
            ["git", "push", "origin", "--delete", "non-existent-branch"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        assert result.returncode != 0

    def test_delete_nonexistent_branch_error_output_is_informative(self, git_repo):
        """Stderr do git push --delete deve conter mensagem informativa."""
        result = subprocess.run(
            ["git", "push", "origin", "--delete", "non-existent-branch"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
            text=True,
        )

        error_output = result.stderr.lower()
        has_ref_message = (
            "remote ref does not exist" in error_output
            or "error" in error_output
            or "fatal" in error_output
        )
        assert has_ref_message, (
            f"stderr deve conter mensagem informativa sobre ref ausente. "
            f"stderr: {result.stderr!r}"
        )

    def test_absent_branch_state_is_desired_outcome(self, git_repo):
        """Confirmar que a ausência da branch já é o estado final desejado."""
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
            text=True,
        )

        # Branch que nunca existiu não está listada — estado final correto
        assert "origin/non-existent-branch" not in result.stdout


# ─── TC-06: git fetch --prune remove refs locais de branches deletadas ────────


class TestTC06FetchPruneAtualiza:
    """TC-06: Após git push --delete + git fetch --prune, a referência local
    de tracking deve desaparecer.

    Este é o Passo 3 do procedimento da issue: confirmar a remoção via
    git branch -r (saída esperada: VAZIA para as branches do lote A).
    """

    def test_prune_removes_deleted_remote_tracking_ref(self, git_repo):
        """git fetch --prune remove ref local de branch deletada do remoto."""
        branch = "feature-to-prune-epic"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result_before = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        assert f"origin/{branch}" in result_before.stdout, (
            "Branch deve existir no remoto antes do teste de prune."
        )

        subprocess.run(["git", "push", "origin", "--delete", branch],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result_after = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert f"origin/{branch}" not in result_after.stdout, (
            f"Após prune, 'origin/{branch}' não deve aparecer em git branch -r. "
            f"Saída: {result_after.stdout}"
        )

    def test_epic_ref_preserved_after_prune(self, git_repo):
        """git fetch --prune não remove a ref de origin/epic."""
        branch = "another-to-prune-epic"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)
        subprocess.run(["git", "push", "origin", "--delete", branch],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert "origin/epic" in result.stdout, (
            "origin/epic deve permanecer em git branch -r após prune de outras branches."
        )

    def test_main_ref_preserved_after_prune(self, git_repo):
        """git fetch --prune não remove a ref de origin/main."""
        branch = "yet-another-to-prune"
        _create_branch_integrated_in_epic(git_repo["repo"], branch)
        subprocess.run(["git", "push", "origin", "--delete", branch],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert "origin/main" in result.stdout, (
            "origin/main deve permanecer em git branch -r após prune de branches de epic."
        )


# ─── TC-07: Verificação das 5 branches alvo do lote A ────────────────────────


class TestTC07BranchesAlvoLoteA:
    """TC-07: Simula o cenário completo da issue #78 — verificação e remoção
    das cinco branches alvo do lote A integradas em epic.

    Os nomes de branch simulam os slugs reais da issue para documentar
    o critério de aceite de forma inequívoca.
    """

    FEATURE28 = "feature28-28-refatoracao_persistir_agent_level_via_label_agent_level_nivel_no_github"
    FEATURE33 = "feature33-33-ajustar_copy_das_mensagens_de_erro_de_ssh_para_contexto_docker"
    FEATURE34 = "feature34-34-implementar_funcao_preflight_de_verificacao_de_credenciais_no_arranque"
    FEATURE35 = "feature35-35-integrar_preflight_ao_fluxo_de_boot_da_esteira"
    FEATURE37 = "feature37-37-criar_docker_composeyml_com_servico_volumes_secret_e_envs"

    ALL_BRANCHES = [FEATURE28, FEATURE33, FEATURE34, FEATURE35, FEATURE37]

    def test_each_branch_is_ancestor_of_epic_after_merge(self, git_repo):
        """Cada branch do lote A mergeada em epic → merge-base --is-ancestor exit 0."""
        for branch in self.ALL_BRANCHES:
            _create_branch_integrated_in_epic(git_repo["repo"], branch)

        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        for branch in self.ALL_BRANCHES:
            assert _is_ancestor(git_repo["repo"], branch), (
                f"Branch '{branch}' mergeada em epic deve ser antepassada de "
                f"origin/epic. Falhou em: {branch}"
            )

    def test_all_branches_deleted_from_remote(self, git_repo):
        """Todas as 5 branches do lote A deletadas do remoto → ausentes em git branch -r."""
        for branch in self.ALL_BRANCHES:
            _create_branch_integrated_in_epic(git_repo["repo"], branch)

        for branch in self.ALL_BRANCHES:
            subprocess.run(["git", "push", "origin", "--delete", branch],
                           cwd=str(git_repo["repo"]), check=True, capture_output=True)

        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        for branch in self.ALL_BRANCHES:
            assert f"origin/{branch}" not in result.stdout, (
                f"'origin/{branch}' não deve aparecer em git branch -r após remoção."
            )

    def test_grep_filter_finds_no_residual_lote_a_branches(self, git_repo):
        """Confirma que grep pelos prefixos do lote A retorna vazio após limpeza."""
        for branch in self.ALL_BRANCHES:
            _create_branch_integrated_in_epic(git_repo["repo"], branch)

        for branch in self.ALL_BRANCHES:
            subprocess.run(["git", "push", "origin", "--delete", branch],
                           cwd=str(git_repo["repo"]), check=True, capture_output=True)

        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        residual = [
            line for line in result.stdout.splitlines()
            if any(f"feature{n}" in line for n in ["28", "33", "34", "35", "37"])
        ]

        assert residual == [], (
            f"Nenhuma branch do lote A deve restar após limpeza. "
            f"Residual: {residual}"
        )

    def test_complete_procedure_step_by_step(self, git_repo):
        """Executa o procedimento completo dos 3 passos da issue em sequência."""
        # Setup: todas as branches existem e estão integradas em epic
        for branch in self.ALL_BRANCHES:
            _create_branch_integrated_in_epic(git_repo["repo"], branch)

        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        # Passo 1: Confirmar integração via merge-base --is-ancestor
        for branch in self.ALL_BRANCHES:
            assert _is_ancestor(git_repo["repo"], branch), (
                f"Passo 1 falhou: '{branch}' não é antepassada de origin/epic."
            )

        # Passo 2: Remover do remoto
        for branch in self.ALL_BRANCHES:
            result = subprocess.run(
                ["git", "push", "origin", "--delete", branch],
                cwd=str(git_repo["repo"]),
                capture_output=True,
            )
            assert result.returncode == 0, (
                f"Passo 2 falhou: git push --delete '{branch}' retornou "
                f"{result.returncode}. stderr: {result.stderr.decode()}"
            )

        # Passo 3: Confirmar remoção
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        for branch in self.ALL_BRANCHES:
            assert f"origin/{branch}" not in result.stdout, (
                f"Passo 3 falhou: '{branch}' ainda aparece em git branch -r."
            )


# ─── TC-08: lote parcial — branch não integrada bloqueia somente ela ─────────


class TestTC08LoteParcialBloqueioSeletivo:
    """TC-08: Se uma branch do lote retornar NAO INTEGRADA, o procedimento
    deve bloquear somente essa branch. As demais confirmadas como INTEGRADAS
    podem e devem prosseguir com a remoção.

    Isso valida a semântica de 'parar para a branch divergente' da issue,
    sem impedir a limpeza das branches saudáveis do lote.
    """

    def test_integrated_branches_removed_despite_one_blocked(self, git_repo):
        """Branches integradas são removidas mesmo que uma do lote esteja bloqueada."""
        integrated = [
            "feature28-28-lote-a-integrated-1",
            "feature33-33-lote-a-integrated-2",
            "feature34-34-lote-a-integrated-3",
            "feature35-35-lote-a-integrated-4",
        ]
        blocked = "feature37-37-lote-a-not-integrated"

        for branch in integrated:
            _create_branch_integrated_in_epic(git_repo["repo"], branch)
        _create_branch_unintegrated_from_epic(git_repo["repo"], blocked)

        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        # Verificação: integradas = True, bloqueada = False
        for branch in integrated:
            assert _is_ancestor(git_repo["repo"], branch), (
                f"Branch '{branch}' deve ser antepassada de epic."
            )
        assert not _is_ancestor(git_repo["repo"], blocked), (
            f"Branch '{blocked}' NÃO deve ser antepassada de epic."
        )

        # Remove apenas as integradas
        for branch in integrated:
            result = subprocess.run(
                ["git", "push", "origin", "--delete", branch],
                cwd=str(git_repo["repo"]),
                capture_output=True,
            )
            assert result.returncode == 0, (
                f"Remoção de '{branch}' deve ter sucesso. "
                f"stderr: {result.stderr.decode()}"
            )

        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        # Integradas removidas
        for branch in integrated:
            assert f"origin/{branch}" not in result.stdout, (
                f"Branch integrada '{branch}' deve ter sido removida."
            )

        # Bloqueada permanece (não foi removida)
        assert f"origin/{blocked}" in result.stdout, (
            f"Branch bloqueada '{blocked}' deve permanecer no remoto."
        )

    def test_blocked_branch_remains_ancestor_check_fails(self, git_repo):
        """A branch bloqueada retorna exit não-zero no merge-base --is-ancestor."""
        blocked = "feature-blocked-not-in-epic"
        _create_branch_unintegrated_from_epic(git_repo["repo"], blocked)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        assert not _is_ancestor(git_repo["repo"], blocked), (
            "Branch não integrada deve falhar no merge-base --is-ancestor."
        )
