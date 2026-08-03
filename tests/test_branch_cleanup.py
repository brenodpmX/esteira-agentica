"""Casos de teste — Verificar e remover branches integradas em `main`.

Cobre o procedimento descrito na issue #77, parte da story #74 (épico #73):
confirmar que branches já integradas não possuem commits exclusivos e podem
ser removidas com segurança do remoto.

Os testes usam repositórios Git temporários (bare + clones em tmp_path) para
simular os três cenários do procedimento obrigatório sem tocar no remoto real:

  TC-01  branch totalmente absorvida por main → git log retorna vazio (seguro remover)
  TC-02  branch com commit exclusivo → git log retorna commits (NÃO remover)
  TC-03  branch inexistente no remoto → ausência não gera erro de verificação
  TC-04  delete de branch integrada no remoto → push --delete bem-sucedido
  TC-05  delete de branch inexistente → git push --delete retorna erro apropriado
  TC-06  git fetch --prune remove referências locais de branches deletadas do remoto
  TC-07  verificação abrange ambas as branches alvo (#77): feature7 e hotfix5

Estratégia de isolamento:
  - Repositório bare em tmp_path/remote.git (simula origin)
  - Clone em tmp_path/repo (simula workdir do agente)
  - Nenhum acesso à rede; nenhuma dependência de credencial
"""

import subprocess
from pathlib import Path

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def git_repo(tmp_path):
    """Cria um repositório bare (remote) e um clone local com commit inicial em main.

    Retorna um dict com:
      - remote: Path para o bare repo (origin)
      - repo:   Path para o clone local (workdir)
    """
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"

    # Repositório bare simula o GitHub remote
    # Força branch padrão como "main" independente da config global do ambiente
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remote)],
                   check=True, capture_output=True)

    # Clone local
    subprocess.run(["git", "clone", str(remote), str(repo)], check=True,
                   capture_output=True)

    # Configuração local para commits
    subprocess.run(["git", "config", "user.email", "test@test.com"],
                   cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"],
                   cwd=str(repo), check=True, capture_output=True)

    # Commit inicial em main (renomeia branch local para "main" caso necessário)
    (repo / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo),
                   check=True, capture_output=True)
    # Garante branch local chamada "main" e faz push
    subprocess.run(["git", "branch", "-M", "main"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(repo),
                   check=True, capture_output=True)

    return {"remote": remote, "repo": repo}


def _create_branch_integrated(repo: Path, branch: str) -> None:
    """Cria branch, faz commit e faz merge em main (branch fica absorvida)."""
    subprocess.run(["git", "checkout", "-b", branch], cwd=str(repo),
                   check=True, capture_output=True)
    (repo / f"{branch}.txt").write_text(f"content of {branch}\n")
    subprocess.run(["git", "add", "."], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"feat: {branch}"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "merge", "--no-ff", branch, "-m", f"merge: {branch}"],
                   cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=str(repo),
                   check=True, capture_output=True)


def _create_branch_unintegrated(repo: Path, branch: str) -> None:
    """Cria branch com commit exclusivo (NÃO mergeada em main)."""
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


def _exclusive_commits(repo: Path, branch: str) -> list[str]:
    """Executa git log --oneline <branch> ^main e retorna linhas de saída."""
    result = subprocess.run(
        ["git", "log", "--oneline", f"origin/{branch}", "^origin/main"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


# ─── TC-01: branch absorvida → git log retorna vazio ─────────────────────────


class TestTC01BranchIntegradaRetornaVazio:
    """TC-01: Confirmar que branch totalmente absorvida por main não possui
    commits exclusivos (saída do git log deve estar vazia).

    Critério de aceite da issue: 'git log ... ^origin/main' retorna saída vazia.
    """

    def test_integrated_branch_has_no_exclusive_commits(self, git_repo):
        """Branch mergeada em main → exclusivos = 0."""
        branch = "feature7-7-incidente_issue_fantasma_correcao_2"
        _create_branch_integrated(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        commits = _exclusive_commits(git_repo["repo"], branch)

        assert commits == [], (
            f"Branch '{branch}' deve ter 0 commits exclusivos após merge em main. "
            f"Encontrado: {commits}"
        )

    def test_empty_log_output_means_safe_to_delete(self, git_repo):
        """Saída vazia do git log confirma que a branch é segura para remoção."""
        branch = "hotfix5-5-incidente_issue_fantasma"
        _create_branch_integrated(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        commits = _exclusive_commits(git_repo["repo"], branch)

        # Saída vazia = seguro remover
        assert len(commits) == 0, (
            "Saída vazia do git log é o critério de segurança para remoção. "
            f"Commits exclusivos inesperados: {commits}"
        )

    def test_git_log_exit_code_zero_when_integrated(self, git_repo):
        """git log retorna exit 0 para branch integrada (não confundir com erro)."""
        branch = "feature-integrated"
        _create_branch_integrated(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "log", "--oneline", f"origin/{branch}", "^origin/main"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        assert result.returncode == 0, (
            f"git log deve retornar exit 0 para branch integrada. "
            f"Retornou: {result.returncode}"
        )


# ─── TC-02: branch não integrada → git log retorna commits ───────────────────


class TestTC02BranchNaoIntegradaRetornaCommits:
    """TC-02: Confirmar que branch com commit exclusivo retorna linhas no git log.

    A lógica de parada obrigatória da issue: se o log retornar commits, NÃO
    remover a branch.
    """

    def test_unintegrated_branch_has_exclusive_commits(self, git_repo):
        """Branch não mergeada em main → exclusivos > 0 → não deve ser removida."""
        branch = "feature-not-merged"
        _create_branch_unintegrated(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        commits = _exclusive_commits(git_repo["repo"], branch)

        assert len(commits) > 0, (
            f"Branch '{branch}' não mergeada deve ter ao menos 1 commit exclusivo. "
            f"Encontrado: {commits}"
        )

    def test_non_empty_log_must_block_deletion(self, git_repo):
        """Presença de commits exclusivos sinaliza que a remoção deve ser bloqueada."""
        branch = "hotfix-unfinished"
        _create_branch_unintegrated(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        commits = _exclusive_commits(git_repo["repo"], branch)

        # A verificação é simples: lista não-vazia = NÃO remover
        assert commits, (
            "Commits exclusivos detectados — remoção deve ser bloqueada."
        )

    def test_exclusive_commit_message_is_visible_in_log(self, git_repo):
        """A mensagem do commit exclusivo deve aparecer na saída do git log."""
        branch = "feature-visible-msg"
        _create_branch_unintegrated(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        commits = _exclusive_commits(git_repo["repo"], branch)

        assert any("exclusive" in c for c in commits), (
            f"Mensagem do commit exclusivo deve aparecer no log. Log: {commits}"
        )


# ─── TC-03: branch inexistente no remoto ──────────────────────────────────────


class TestTC03BranchInexistenteNoRemoto:
    """TC-03: Se a branch já não existir no remoto, a verificação deve ser
    tratada como 'já removida' — não como erro crítico do procedimento.

    A issue especifica: 'Se a branch já não existir no remoto, registrar no
    comentário e seguir.'
    """

    def test_git_log_on_nonexistent_remote_branch_exits_nonzero(self, git_repo):
        """git log em branch remota inexistente retorna exit não-zero (detecção de ausência)."""
        result = subprocess.run(
            ["git", "log", "--oneline",
             "origin/branch-que-nao-existe", "^origin/main"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        # Retorno não-zero indica que a referência não existe
        assert result.returncode != 0, (
            "git log em branch remota inexistente deve retornar exit não-zero."
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
        """Ausência de branch é confirmável via git branch -r após fetch."""
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


# ─── TC-04: delete de branch integrada ───────────────────────────────────────


class TestTC04DeleteBranchIntegrada:
    """TC-04: git push origin --delete de branch já integrada deve ter sucesso."""

    def test_push_delete_integrated_branch_succeeds(self, git_repo):
        """Remoção de branch integrada no remoto → exit 0."""
        branch = "feature7-7-integrated-to-delete"
        _create_branch_integrated(git_repo["repo"], branch)
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
        branch = "hotfix5-5-to-delete"
        _create_branch_integrated(git_repo["repo"], branch)

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

    def test_main_content_intact_after_branch_delete(self, git_repo):
        """Remoção da branch não afeta o conteúdo de main."""
        branch = "feature-safe-delete"
        _create_branch_integrated(git_repo["repo"], branch)

        # Anota hash de main antes
        result_before = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        hash_before = result_before.stdout.strip()

        subprocess.run(["git", "push", "origin", "--delete", branch],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        # Hash de main deve ser idêntico
        result_after = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        hash_after = result_after.stdout.strip()

        assert hash_before == hash_after, (
            "O hash de origin/main não deve mudar após remover uma branch integrada."
        )


# ─── TC-05: delete de branch inexistente ──────────────────────────────────────


class TestTC05DeleteBranchInexistente:
    """TC-05: git push --delete em branch inexistente retorna erro não-zero.

    Isso é esperado e não deve interromper o procedimento como falha crítica —
    a branch já está ausente, que é o estado desejado.
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
        """Stderr do git push --delete deve mencionar que a branch não existe."""
        result = subprocess.run(
            ["git", "push", "origin", "--delete", "non-existent-branch"],
            cwd=str(git_repo["repo"]),
            capture_output=True,
            text=True,
        )

        error_output = result.stderr.lower()
        # Mensagem esperada: "remote ref does not exist" ou similar
        has_ref_message = (
            "remote ref does not exist" in error_output
            or "error" in error_output
            or "fatal" in error_output
        )
        assert has_ref_message, (
            f"stderr deve conter mensagem informativa sobre ref ausente. "
            f"stderr: {result.stderr!r}"
        )


# ─── TC-06: git fetch --prune remove refs locais de branches deletadas ────────


class TestTC06FetchPruneAtualiza:
    """TC-06: Após git push --delete + git fetch --prune, a referência local
    de tracking deve desaparecer.

    Este é o Passo 3 do procedimento da issue: confirmar a remoção via
    git branch -r.
    """

    def test_prune_removes_deleted_remote_tracking_ref(self, git_repo):
        """git fetch --prune remove ref local de branch deletada do remoto."""
        branch = "feature-to-prune"
        _create_branch_integrated(git_repo["repo"], branch)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        # Confirma que a ref existe antes
        result_before = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        assert f"origin/{branch}" in result_before.stdout

        # Deleta do remoto e prune
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

    def test_main_ref_preserved_after_prune(self, git_repo):
        """git fetch --prune não remove a ref de origin/main."""
        branch = "another-to-prune"
        _create_branch_integrated(git_repo["repo"], branch)
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
            "origin/main deve permanecer em git branch -r após prune de outras branches."
        )


# ─── TC-07: Verificação das duas branches alvo da issue #77 ──────────────────


class TestTC07BranchesAlvoIssue77:
    """TC-07: Simula o cenário completo da issue #77 — verificação e remoção
    das duas branches alvo: feature7 e hotfix5.

    Os nomes de branch simulam os slugs reais da issue para documentar
    o critério de aceite de forma inequívoca.
    """

    FEATURE7 = "feature7-7-incidente_issue_fantasma_correcao_2"
    HOTFIX5 = "hotfix5-5-incidente_issue_fantasma"

    def test_feature7_has_no_exclusive_commits_after_merge(self, git_repo):
        """Simula feature7 mergeada em main → 0 commits exclusivos."""
        _create_branch_integrated(git_repo["repo"], self.FEATURE7)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        commits = _exclusive_commits(git_repo["repo"], self.FEATURE7)

        assert commits == [], (
            f"feature7 simulada deve ter 0 commits exclusivos. Encontrado: {commits}"
        )

    def test_hotfix5_has_no_exclusive_commits_after_merge(self, git_repo):
        """Simula hotfix5 mergeada em main → 0 commits exclusivos."""
        _create_branch_integrated(git_repo["repo"], self.HOTFIX5)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        commits = _exclusive_commits(git_repo["repo"], self.HOTFIX5)

        assert commits == [], (
            f"hotfix5 simulada deve ter 0 commits exclusivos. Encontrado: {commits}"
        )

    def test_both_branches_deleted_from_remote(self, git_repo):
        """Ambas as branches alvo deletadas do remoto → não aparecem em git branch -r."""
        for branch in (self.FEATURE7, self.HOTFIX5):
            _create_branch_integrated(git_repo["repo"], branch)

        for branch in (self.FEATURE7, self.HOTFIX5):
            subprocess.run(["git", "push", "origin", "--delete", branch],
                           cwd=str(git_repo["repo"]), check=True, capture_output=True)

        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        for branch in (self.FEATURE7, self.HOTFIX5):
            assert f"origin/{branch}" not in result.stdout, (
                f"'origin/{branch}' não deve aparecer em git branch -r após remoção."
            )

    def test_complete_procedure_step_by_step(self, git_repo):
        """Executa o procedimento completo dos 3 passos da issue em sequência."""
        # Setup: ambas as branches existem e estão integradas
        for branch in (self.FEATURE7, self.HOTFIX5):
            _create_branch_integrated(git_repo["repo"], branch)

        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        # Passo 1: Confirmar integração
        for branch in (self.FEATURE7, self.HOTFIX5):
            commits = _exclusive_commits(git_repo["repo"], branch)
            assert commits == [], (
                f"Passo 1 falhou: '{branch}' tem commits exclusivos: {commits}"
            )

        # Passo 2: Remover do remoto
        for branch in (self.FEATURE7, self.HOTFIX5):
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

        for branch in (self.FEATURE7, self.HOTFIX5):
            assert f"origin/{branch}" not in result.stdout, (
                f"Passo 3 falhou: '{branch}' ainda aparece em git branch -r."
            )

    def test_grep_filter_finds_no_residual_branches(self, git_repo):
        """Confirma que grep por 'feature7|hotfix5' retorna vazio após limpeza."""
        for branch in (self.FEATURE7, self.HOTFIX5):
            _create_branch_integrated(git_repo["repo"], branch)

        for branch in (self.FEATURE7, self.HOTFIX5):
            subprocess.run(["git", "push", "origin", "--delete", branch],
                           cwd=str(git_repo["repo"]), check=True, capture_output=True)

        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        branches_result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        residual = [
            line for line in branches_result.stdout.splitlines()
            if "feature7" in line or "hotfix5" in line
        ]

        assert residual == [], (
            f"Nenhuma branch feature7 ou hotfix5 deve restar após limpeza. "
            f"Residual: {residual}"
        )
