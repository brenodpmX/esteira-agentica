"""Casos de teste — Consolidar duplicata de issues #46/#47.

Cobre o procedimento descrito na issue #96, parte da story #76 (épico #73):
as issues **#46** e **#47** têm título idêntico ("Adicionar volumes de estado
no docker-compose.yml — US-04 / D-05") e cada uma possui sua própria branch
(`epic46-46-...` e `epic47-47-...`). A decisão de Requisitos já definiu:

  - Canônica a preservar: `epic47-47-...` / issue #47
    (10 min mais recente, contém a seção adicional §9 — ".gitignore e os
    diretórios de estado" — em `doc/stories/rodar-no-docker/arquitetura.md`).
  - Duplicata a remover: `epic46-46-...` / issue #46
    (branch removida do remoto; issue fechada como `not_planned`).

Diferença em relação aos lotes de limpeza epic→main (issues #77/#78/#79):
  - Não se trata de branch já integrada em `epic` — são duas branches
    concorrentes (mesma feature, implementada duas vezes) e o critério de
    seleção é qual delas é a mais completa/recente, não ancestralidade.
  - O sinal de evidência é a presença de uma seção específica de conteúdo
    (§9) num arquivo de documentação, não `git merge-base --is-ancestor`.
  - Após a remoção da branch duplicada, o procedimento inclui o fechamento
    da issue duplicada (#46) como `not_planned` via comando `@---` — passo
    sem equivalente nos lotes de limpeza anteriores.

Os testes usam repositórios Git temporários (bare + clones em tmp_path) para
simular os cenários do procedimento sem tocar no remoto real.

  TC-01  duas branches concorrentes — diff --stat aponta apenas os arquivos
         já documentados como divergentes
  TC-02  seção §9 presente na branch canônica (epic47) e ausente na
         duplicata (epic46) — confirmação da evidência
  TC-03  arquivos não relacionados à seção §9 são idênticos entre as branches
         (user-stories.md, .env.prototipo, docker-compose.prototipo.yml)
  TC-04  branch duplicada removida do remoto com sucesso (push --delete)
  TC-05  branch canônica preservada e íntegra após remoção da duplicata
  TC-06  git fetch --prune remove a referência local da duplicata e mantém
         a canônica
  TC-07  bloco `@---` da issue duplicada ganha `/close not_planned` sem
         afetar o restante do conteúdo do body
  TC-08  procedimento completo executado em sequência (Passos 1 a 4 da issue)

Estratégia de isolamento:
  - Repositório bare em tmp_path/remote.git (simula origin)
  - Clone em tmp_path/repo (simula workdir do agente)
  - Duas branches concorrentes criadas a partir de um commit base comum,
    cada uma com seu próprio commit divergente
  - Nenhum acesso à rede; nenhuma dependência de credencial
"""

import subprocess
from pathlib import Path

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def git_repo(tmp_path):
    """Cria um repositório bare (remote) e um clone local com commit inicial
    em main.

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

    return {"remote": remote, "repo": repo}


# ─── Helpers ──────────────────────────────────────────────────────────────────

ARQUITETURA_PATH = "doc/stories/rodar-no-docker/arquitetura.md"
SECAO_9_MARKER = "## §9 — \".gitignore e os diretórios de estado\""

COMMON_FILES = {
    "doc/stories/rodar-no-docker/user-stories.md": "user stories — US-04/D-05\n",
    ".env.prototipo": "PIPE_STATE_DIR=./state\n",
    "docker-compose.prototipo.yml": "version: '3'\nservices:\n  pipe: {}\n",
}


def _create_base_arquitetura(repo: Path) -> None:
    """Commit em main com o arquivo de arquitetura sem a seção §9 e os
    arquivos comuns que serão idênticos entre as duas branches concorrentes.
    """
    arq_path = repo / ARQUITETURA_PATH
    arq_path.parent.mkdir(parents=True, exist_ok=True)
    arq_path.write_text("# Arquitetura\n\n## §1 — Visão geral\n\nconteúdo base.\n")

    for rel_path, content in COMMON_FILES.items():
        full = repo / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)

    subprocess.run(["git", "add", "."], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "chore: base US-04/D-05"],
                   cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=str(repo),
                   check=True, capture_output=True)


def _create_duplicate_branch_without_secao_9(repo: Path, branch: str) -> None:
    """Simula epic46: branch a partir de main SEM a seção §9."""
    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", branch], cwd=str(repo),
                   check=True, capture_output=True)

    marker_path = repo / f"{branch}-marker.txt"
    marker_path.write_text(f"volumes de estado — implementação {branch}\n")
    subprocess.run(["git", "add", "."], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"feat: {branch} (volumes de estado, sem §9)"],
        cwd=str(repo), check=True, capture_output=True,
    )
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)


def _create_canonical_branch_with_secao_9(repo: Path, branch: str) -> None:
    """Simula epic47: branch a partir de main COM a seção §9 adicional."""
    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", branch], cwd=str(repo),
                   check=True, capture_output=True)

    marker_path = repo / f"{branch}-marker.txt"
    marker_path.write_text(f"volumes de estado — implementação {branch}\n")

    arq_path = repo / ARQUITETURA_PATH
    arq_path.write_text(
        "# Arquitetura\n\n## §1 — Visão geral\n\nconteúdo base.\n\n"
        f'{SECAO_9_MARKER}\n\n'
        "O .gitignore já exclui corretamente os diretórios de runtime, "
        "resolvendo o critério de aceite D-05.\n"
    )

    subprocess.run(["git", "add", "."], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"feat: {branch} (volumes de estado, com §9)"],
        cwd=str(repo), check=True, capture_output=True,
    )
    subprocess.run(["git", "push", "-u", "origin", branch], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)


BRANCH_DUPLICATA = "epic46-46-adicionar_volumes_de_estado_no_docker_composeyml_us_04_d_05"
BRANCH_CANONICA = "epic47-47-adicionar_volumes_de_estado_no_docker_composeyml_us_04_d_05"


def _setup_both_branches(repo: Path) -> None:
    _create_base_arquitetura(repo)
    _create_duplicate_branch_without_secao_9(repo, BRANCH_DUPLICATA)
    _create_canonical_branch_with_secao_9(repo, BRANCH_CANONICA)


# ─── TC-01: diff --stat entre as duas branches ────────────────────────────────


class TestTC01DiffStatEntreBranches:
    """TC-01: git diff --stat entre as duas branches concorrentes deve
    apontar apenas os arquivos já documentados como divergentes (o marker de
    cada implementação e o arquivo de arquitetura, que ganha a seção §9 em
    uma delas).
    """

    def test_diff_stat_lists_expected_divergent_files(self, git_repo):
        """diff --stat entre epic46 e epic47 lista apenas arquivos esperados."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "diff", f"origin/{BRANCH_DUPLICATA}",
             f"origin/{BRANCH_CANONICA}", "--stat"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert ARQUITETURA_PATH in result.stdout, (
            "diff --stat deve apontar divergência em arquitetura.md (seção §9)."
        )
        # Os arquivos comuns (idênticos entre as branches) não devem aparecer.
        for common_file in COMMON_FILES:
            assert common_file not in result.stdout, (
                f"'{common_file}' é idêntico entre as branches e não deveria "
                f"aparecer no diff --stat."
            )

    def test_diff_stat_does_not_list_unexpected_files(self, git_repo):
        """Nenhum arquivo fora do esperado (markers + arquitetura.md) diverge."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "diff", f"origin/{BRANCH_DUPLICATA}",
             f"origin/{BRANCH_CANONICA}", "--name-only"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        changed_files = {line for line in result.stdout.splitlines() if line}
        expected = {
            ARQUITETURA_PATH,
            f"{BRANCH_DUPLICATA}-marker.txt",
            f"{BRANCH_CANONICA}-marker.txt",
        }

        assert changed_files == expected, (
            f"Divergência inesperada entre as branches. "
            f"Esperado: {expected}, encontrado: {changed_files}"
        )


# ─── TC-02: evidência da seção §9 ──────────────────────────────────────────────


class TestTC02EvidenciaSecao9:
    """TC-02: a seção §9 deve estar presente na branch canônica (epic47) e
    ausente na branch duplicata (epic46) — é a evidência central que
    justifica qual branch preservar.
    """

    def test_secao_9_present_in_canonical_branch(self, git_repo):
        """Seção §9 presente em epic47 (canônica)."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "show", f"origin/{BRANCH_CANONICA}:{ARQUITETURA_PATH}"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert SECAO_9_MARKER in result.stdout, (
            "Seção §9 deve estar presente em arquitetura.md na branch canônica."
        )

    def test_secao_9_absent_in_duplicate_branch(self, git_repo):
        """Seção §9 ausente em epic46 (duplicata)."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "show", f"origin/{BRANCH_DUPLICATA}:{ARQUITETURA_PATH}"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert SECAO_9_MARKER not in result.stdout, (
            "Seção §9 NÃO deve estar presente em arquitetura.md na branch duplicata."
        )

    def test_grep_evidence_matches_expected_pattern_per_branch(self, git_repo):
        """grep pela seção §9 reproduz o comando de evidência do body da issue."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        canonical_show = subprocess.run(
            ["git", "show", f"origin/{BRANCH_CANONICA}:{ARQUITETURA_PATH}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout
        duplicate_show = subprocess.run(
            ["git", "show", f"origin/{BRANCH_DUPLICATA}:{ARQUITETURA_PATH}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout

        canonical_matches = [
            line for line in canonical_show.splitlines()
            if "§9" in line or "gitignore e os diretórios de estado" in line
        ]
        duplicate_matches = [
            line for line in duplicate_show.splitlines()
            if "§9" in line or "gitignore e os diretórios de estado" in line
        ]

        assert canonical_matches, "epic47 deve ter ao menos uma linha casando com §9."
        assert not duplicate_matches, "epic46 não deve ter nenhuma linha casando com §9."


# ─── TC-03: arquivos comuns idênticos entre as branches ───────────────────────


class TestTC03ArquivosComunsIdenticos:
    """TC-03: os arquivos não relacionados à seção §9
    (user-stories.md, .env.prototipo, docker-compose.prototipo.yml) devem
    ser idênticos entre as duas branches — conforme documentado no body da
    issue.
    """

    @pytest.mark.parametrize("rel_path", list(COMMON_FILES))
    def test_common_file_is_identical_between_branches(self, git_repo, rel_path):
        """Cada arquivo comum tem conteúdo idêntico nas duas branches."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        content_duplicata = subprocess.run(
            ["git", "show", f"origin/{BRANCH_DUPLICATA}:{rel_path}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout
        content_canonica = subprocess.run(
            ["git", "show", f"origin/{BRANCH_CANONICA}:{rel_path}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout

        assert content_duplicata == content_canonica, (
            f"'{rel_path}' deve ser idêntico entre epic46 e epic47. "
            f"epic46: {content_duplicata!r} / epic47: {content_canonica!r}"
        )


# ─── TC-04: remoção da branch duplicada ────────────────────────────────────────


class TestTC04RemocaoBranchDuplicada:
    """TC-04: git push origin --delete da branch duplicada (epic46) deve
    ter sucesso.
    """

    def test_push_delete_duplicate_branch_succeeds(self, git_repo):
        """Remoção de epic46 → exit 0."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        result = subprocess.run(
            ["git", "push", "origin", "--delete", BRANCH_DUPLICATA],
            cwd=str(git_repo["repo"]),
            capture_output=True,
        )

        assert result.returncode == 0, (
            f"git push --delete deve ter exit 0 para a branch duplicada. "
            f"stderr: {result.stderr.decode()}"
        )

    def test_duplicate_branch_absent_from_remote_after_delete(self, git_repo):
        """Após delete, epic46 não aparece mais em git branch -r."""
        _setup_both_branches(git_repo["repo"])

        subprocess.run(["git", "push", "origin", "--delete", BRANCH_DUPLICATA],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert f"origin/{BRANCH_DUPLICATA}" not in result.stdout, (
            f"'origin/{BRANCH_DUPLICATA}' não deve aparecer em git branch -r "
            f"após remoção."
        )


# ─── TC-05: preservação da branch canônica ────────────────────────────────────


class TestTC05PreservacaoBranchCanonica:
    """TC-05: a branch canônica (epic47) deve permanecer intacta e presente
    no remoto após a remoção da duplicata.
    """

    def test_canonical_branch_still_present_after_duplicate_delete(self, git_repo):
        """epic47 continua listada em git branch -r após remover epic46."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "push", "origin", "--delete", BRANCH_DUPLICATA],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert f"origin/{BRANCH_CANONICA}" in result.stdout, (
            f"'origin/{BRANCH_CANONICA}' deve permanecer presente no remoto."
        )

    def test_canonical_branch_content_unchanged_after_duplicate_delete(self, git_repo):
        """O hash de epic47 não muda ao remover a branch duplicada."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)
        hash_before = subprocess.run(
            ["git", "rev-parse", f"origin/{BRANCH_CANONICA}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        subprocess.run(["git", "push", "origin", "--delete", BRANCH_DUPLICATA],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        hash_after = subprocess.run(
            ["git", "rev-parse", f"origin/{BRANCH_CANONICA}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        assert hash_before == hash_after, (
            "O hash de origin/epic47 não deve mudar após remover a duplicata."
        )

    def test_secao_9_still_readable_from_canonical_after_delete(self, git_repo):
        """Seção §9 continua legível em epic47 após a remoção de epic46."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "push", "origin", "--delete", BRANCH_DUPLICATA],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "show", f"origin/{BRANCH_CANONICA}:{ARQUITETURA_PATH}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        )

        assert SECAO_9_MARKER in result.stdout


# ─── TC-06: git fetch --prune ──────────────────────────────────────────────────


class TestTC06FetchPruneAtualiza:
    """TC-06: git fetch --prune remove a referência local da duplicata e
    preserva a canônica — critério de aceite explícito no body da issue.
    """

    def test_prune_removes_duplicate_ref_only(self, git_repo):
        """Após prune: epic46 ausente, epic47 presente."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "push", "origin", "--delete", BRANCH_DUPLICATA],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert f"origin/{BRANCH_DUPLICATA}" not in result.stdout
        assert f"origin/{BRANCH_CANONICA}" in result.stdout

    def test_main_ref_preserved_after_prune(self, git_repo):
        """origin/main permanece presente após prune da duplicata."""
        _setup_both_branches(git_repo["repo"])
        subprocess.run(["git", "push", "origin", "--delete", BRANCH_DUPLICATA],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )

        assert "origin/main" in result.stdout


# ─── TC-07: fechamento da issue duplicada via bloco @--- ──────────────────────


class TestTC07FechamentoIssueDuplicadaViaBloco:
    """TC-07: o bloco `@---` da issue duplicada (#46) recebe `/close
    not_planned`, seguindo a filosofia presença/ausência descrita na
    documentação de comandos — sem afetar o restante do body.

    Não depende de rede/board real: testa apenas a manipulação textual do
    arquivo `-body.md`, equivalente ao que o sync aplicaria.
    """

    def test_append_close_not_planned_preserves_body_content(self, tmp_path):
        """Adicionar /close not_planned ao bloco @--- preserva o conteúdo do body."""
        body_file = tmp_path / "46-body.md"
        original_body = (
            "# Adicionar volumes de estado no docker-compose.yml — "
            "US-04 / D-05\n\nconteúdo original da issue.\n\n"
            "@---\n/labels backend, docker\n"
        )
        body_file.write_text(original_body)

        content = body_file.read_text()
        head, _, tail = content.partition("@---\n")
        updated = head + "@---\n" + tail.rstrip("\n") + "\n/close not_planned\n"
        body_file.write_text(updated)

        result = body_file.read_text()
        assert "# Adicionar volumes de estado" in result
        assert "conteúdo original da issue." in result
        assert "/labels backend, docker" in result
        assert "/close not_planned" in result

    def test_close_not_planned_appears_after_at_marker(self, tmp_path):
        """/close not_planned deve aparecer na seção de comandos, após @---."""
        body_file = tmp_path / "46-body.md"
        body_file.write_text("# Título\n\nconteúdo.\n\n@---\n/labels docker\n")

        content = body_file.read_text()
        head, marker, tail = content.partition("@---\n")
        updated = head + marker + tail.rstrip("\n") + "\n/close not_planned\n"
        body_file.write_text(updated)

        result = body_file.read_text()
        pre_marker, _, post_marker = result.partition("@---\n")
        assert "/close" not in pre_marker, (
            "/close not_planned deve ficar no bloco de comandos, não no "
            "conteúdo da issue."
        )
        assert "/close not_planned" in post_marker

    def test_single_at_marker_remains_after_update(self, tmp_path):
        """Após a edição, o arquivo mantém exatamente um marcador @---."""
        body_file = tmp_path / "46-body.md"
        body_file.write_text("# Título\n\nconteúdo.\n\n@---\n/labels docker\n")

        content = body_file.read_text()
        head, marker, tail = content.partition("@---\n")
        updated = head + marker + tail.rstrip("\n") + "\n/close not_planned\n"
        body_file.write_text(updated)

        assert body_file.read_text().count("@---") == 1


# ─── TC-08: procedimento completo (Passos 1 a 4 da issue) ────────────────────


class TestTC08ProcedimentoCompleto:
    """TC-08: executa em sequência os 4 passos do procedimento descrito no
    body da issue #96, confirmando o estado final esperado pelos critérios
    de aceite.
    """

    def test_full_procedure_steps_1_to_4(self, git_repo):
        repo = git_repo["repo"]
        _setup_both_branches(repo)
        subprocess.run(["git", "fetch", "origin"], cwd=str(repo),
                       check=True, capture_output=True)

        # Passo 1 — confirmar evidência: §9 presente em epic47, ausente em epic46
        canonical_arq = subprocess.run(
            ["git", "show", f"origin/{BRANCH_CANONICA}:{ARQUITETURA_PATH}"],
            cwd=str(repo), capture_output=True, text=True,
        ).stdout
        duplicate_arq = subprocess.run(
            ["git", "show", f"origin/{BRANCH_DUPLICATA}:{ARQUITETURA_PATH}"],
            cwd=str(repo), capture_output=True, text=True,
        ).stdout
        assert SECAO_9_MARKER in canonical_arq, "Passo 1 falhou: §9 ausente em epic47."
        assert SECAO_9_MARKER not in duplicate_arq, "Passo 1 falhou: §9 presente em epic46."

        # Passo 2 — remover a branch duplicada do remoto
        delete_result = subprocess.run(
            ["git", "push", "origin", "--delete", BRANCH_DUPLICATA],
            cwd=str(repo), capture_output=True,
        )
        assert delete_result.returncode == 0, "Passo 2 falhou: delete não teve exit 0."

        # Passo 3 — fechar a issue duplicada como not_planned (simulado via arquivo local)
        body_file = repo / "46-body.md"
        body_file.write_text(
            "# Adicionar volumes de estado no docker-compose.yml — US-04 / D-05\n\n"
            "conteúdo original.\n\n@---\n/labels backend, docker\n"
        )
        content = body_file.read_text()
        head, marker, tail = content.partition("@---\n")
        body_file.write_text(
            head + marker + tail.rstrip("\n") + "\n/close not_planned\n"
        )
        assert "/close not_planned" in body_file.read_text()
        body_file.unlink()

        # Passo 4 — confirmar remoção da duplicata e preservação da canônica
        subprocess.run(["git", "fetch", "origin", "--prune"], cwd=str(repo),
                       check=True, capture_output=True)
        branches = subprocess.run(
            ["git", "branch", "-r"], cwd=str(repo),
            capture_output=True, text=True,
        ).stdout

        assert f"origin/{BRANCH_DUPLICATA}" not in branches, (
            "Passo 4 falhou: branch duplicada ainda presente no remoto."
        )
        assert f"origin/{BRANCH_CANONICA}" in branches, (
            "Passo 4 falhou: branch canônica ausente do remoto."
        )
