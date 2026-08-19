"""Casos de teste — Analisar e tratar branch hotfix23 (avaliação de complexidade falhando).

Cobre o procedimento descrito na issue #84, parte da story #75 (épico #73):
a branch `hotfix23-23-avaliacao_de_complexidade_falhando` contém apenas
documentação de incidente (doc/incidente/avaliacao-complexidade-falhando/ticket.md),
sem código de correção. Diferente das issues #77/#78/#79 (lotes de branches já
100% integradas), esta branch **não é ancestral de `epic`** — o conteúdo de
doc nunca foi mergeado. O procedimento exige uma decisão em duas etapas antes
da remoção:

  1. Verificar se a correção do bug (`agent_level` perdido no sync down) já
     foi implementada em `epic` por outra via (fix estrutural via label).
  2. Decidir se o ticket de incidente tem valor histórico e deve ser
     preservado via cherry-pick + PR antes do `git push --delete`.

Casos de teste:

  TC-01  branch hotfix23 NÃO é ancestral de epic (conteúdo de doc não mergeado)
  TC-02  detecção de fix já implementado via grep em `agent_level`/label no código de epic
  TC-03  ausência de commits relativos a "agent_level"/"sync down" não bloqueia decisão
         (fix pode estar implementado sob nome/abordagem diferente — corroborado por TC-02)
  TC-04  leitura do ticket de incidente via `git show <branch>:<path>` sem checkout
  TC-05  cherry-pick de commit de documentação para branch temporária a partir de epic
  TC-06  cherry-pick preserva o conteúdo do arquivo de documentação
  TC-07  branch temporária de preservação não contém arquivos de código de produção
  TC-08  remoção da branch hotfix23 do remoto após decisão (push --delete bem-sucedido)
  TC-09  fetch --prune remove a referência local após remoção do remoto
  TC-10  `git branch -r | grep hotfix23` retorna vazio (critério de aceite final)
  TC-11  epic permanece intacto (hash inalterado) após remoção da branch hotfix23
  TC-12  branch hotfix23 inexistente no remoto é tratada sem erro crítico (idempotência)

Estratégia de isolamento:
  - Repositório bare em tmp_path/remote.git (simula origin)
  - Clone em tmp_path/repo (simula workdir do agente)
  - Branch `epic` e branch `hotfix23-...` com apenas documentação, criadas
    explicitamente no bare, sem tocar no remoto real
  - Nenhum acesso à rede; nenhuma dependência de credencial; nenhuma chamada
    real a `gh pr create` (fora do escopo do teste — apenas os pré-requisitos
    de dados, como o cherry-pick isolado, são verificados)
"""

import subprocess
from pathlib import Path

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def git_repo(tmp_path):
    """Cria um repositório bare (remote) e um clone local com:
      - commit inicial em `main`
      - branch `epic` criada a partir de `main`, com o fix estrutural de
        `agent_level` (simulado como commit que adiciona a lógica de label)
      - branch `hotfix23-23-avaliacao_de_complexidade_falhando` criada a
        partir de `epic` (num ponto anterior ao fix), contendo APENAS o
        ticket de incidente em doc/incidente/, sem código de correção

    Retorna um dict com:
      - remote: Path para o bare repo (origin)
      - repo:   Path para o clone local (workdir)
      - hotfix_branch: nome da branch de incidente
    """
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    hotfix_branch = "hotfix23-23-avaliacao_de_complexidade_falhando"

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

    # Branch epic a partir de main
    subprocess.run(["git", "checkout", "-b", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    (repo / "epic_base.md").write_text("epic base\n")
    subprocess.run(["git", "add", "epic_base.md"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "chore: epic base"], cwd=str(repo),
                   check=True, capture_output=True)

    # Ponto de bifurcação: hotfix23 nasce daqui (ANTES do fix estrutural)
    subprocess.run(["git", "checkout", "-b", hotfix_branch], cwd=str(repo),
                   check=True, capture_output=True)
    incident_dir = repo / "doc" / "incidente" / "avaliacao-complexidade-falhando"
    incident_dir.mkdir(parents=True)
    ticket_path = incident_dir / "ticket.md"
    ticket_path.write_text(
        "# Ticket de incidente — avaliação de complexidade falhando\n\n"
        "## Causa raiz\n"
        "agent_level perdido no ciclo de sync down.\n\n"
        "## Abordagens avaliadas\n"
        "1. Persistir em arquivo local (descartada)\n"
        "2. Persistir via label agent-level-<nivel> no GitHub (escolhida)\n"
    )
    subprocess.run(["git", "add", "."], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "docs: ticket de incidente agent_level sync down"],
        cwd=str(repo), check=True, capture_output=True,
    )
    subprocess.run(["git", "push", "-u", "origin", hotfix_branch], cwd=str(repo),
                   check=True, capture_output=True)

    # epic segue adiante com o FIX estrutural (implementado por outra via,
    # sem nunca mergear a branch hotfix23)
    subprocess.run(["git", "checkout", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    (repo / "commands.py").write_text(
        'AGENT_LEVEL_PREFIX = "agent-level-"\n'
        "# from_issue() popula agent_level a partir da label agent-level-<nivel>\n"
    )
    subprocess.run(["git", "add", "commands.py"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: persistir agent_level via label no github"],
        cwd=str(repo), check=True, capture_output=True,
    )
    subprocess.run(["git", "push", "-u", "origin", "epic"], cwd=str(repo),
                   check=True, capture_output=True)

    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "fetch", "origin"], cwd=str(repo),
                   check=True, capture_output=True)

    return {"remote": remote, "repo": repo, "hotfix_branch": hotfix_branch}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _is_ancestor(repo: Path, branch: str, base: str = "origin/epic") -> bool:
    """Executa git merge-base --is-ancestor origin/<branch> <base>."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"origin/{branch}", base],
        cwd=str(repo),
        capture_output=True,
    )
    return result.returncode == 0


# ─── TC-01: branch hotfix23 NÃO é ancestral de epic ──────────────────────────


class TestTC01BranchNaoIntegradaEmEpic:
    """TC-01: A branch hotfix23 contém apenas doc/incidente, nunca mergeada
    em epic. Diferente dos lotes A/B (#77/#78/#79), o critério de segurança
    de remoção NÃO pode ser 'branch já integrada' — precisa da decisão
    explícita de preservar ou descartar o conteúdo de documentação.
    """

    def test_hotfix23_is_not_ancestor_of_epic(self, git_repo):
        """hotfix23 não é ancestral de origin/epic (doc nunca foi mergeada)."""
        assert not _is_ancestor(git_repo["repo"], git_repo["hotfix_branch"]), (
            "A branch hotfix23 não deve ser detectada como já integrada em "
            "epic — seu conteúdo de documentação nunca foi mergeado."
        )

    def test_naive_ancestor_check_would_block_deletion(self, git_repo):
        """Um procedimento que dependesse só de merge-base bloquearia a remoção
        indefinidamente — por isso a issue exige decisão explícita (preservar
        via PR ou descartar), não apenas checagem de ancestralidade.
        """
        is_anc = _is_ancestor(git_repo["repo"], git_repo["hotfix_branch"])
        assert is_anc is False


# ─── TC-02/TC-03: verificação de fix já implementado (Pergunta 1) ────────────


class TestTC02FixJaImplementadoEmEpic:
    """TC-02/TC-03: A issue pede para confirmar, via análise do código de
    epic, se a correção do agent_level no sync down já existe — ainda que
    sob abordagem/nome diferente do commit original do incidente.
    """

    def test_grep_agent_level_prefix_found_in_epic(self, git_repo):
        """O trecho AGENT_LEVEL_PREFIX (evidência do fix estrutural) existe em epic."""
        result = subprocess.run(
            ["git", "show", "origin/epic:commands.py"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "AGENT_LEVEL_PREFIX" in result.stdout, (
            "Evidência do fix (label agent-level-<nivel>) deve estar presente "
            "no código de epic."
        )

    def test_git_log_epic_contains_agent_level_fix_commit(self, git_repo):
        """git log em epic contém commit que referencia agent_level."""
        result = subprocess.run(
            ["git", "log", "--oneline", "origin/epic"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        assert "agent_level" in result.stdout.lower(), (
            "Deve haver commit em epic referenciando agent_level, confirmando "
            "que a Pergunta 1 do body (fix já implementado?) responde SIM."
        )

    def test_absence_of_literal_sync_down_term_does_not_block_confirmation(
        self, git_repo,
    ):
        """A ausência do termo literal 'sync down' no log não invalida a
        confirmação do fix — a evidência correta é o mecanismo (label
        AGENT_LEVEL_PREFIX), não uma string exata no histórico de commits.
        """
        result = subprocess.run(
            ["git", "log", "--oneline", "origin/epic"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        # O termo exato pode não aparecer, mesmo com o fix implementado.
        literal_absent = "sync down" not in result.stdout.lower()
        code_result = subprocess.run(
            ["git", "show", "origin/epic:commands.py"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        fix_present = "AGENT_LEVEL_PREFIX" in code_result.stdout

        assert literal_absent and fix_present, (
            "Mesmo sem o termo literal no log, a evidência no código confirma "
            "o fix — a decisão não deve depender só de grep textual no log."
        )


# ─── TC-04: leitura do ticket sem checkout ────────────────────────────────────


class TestTC04LeituraDoTicketSemCheckout:
    """TC-04: O Passo 2 do procedimento lê o ticket via `git show
    <branch>:<path>`, sem fazer checkout da branch (preserva o workdir atual).
    """

    def test_git_show_reads_ticket_content(self, git_repo):
        """git show origin/hotfix23:...ticket.md retorna o conteúdo do ticket."""
        path = "doc/incidente/avaliacao-complexidade-falhando/ticket.md"
        result = subprocess.run(
            ["git", "show", f"origin/{git_repo['hotfix_branch']}:{path}"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Causa raiz" in result.stdout
        assert "agent_level" in result.stdout

    def test_git_show_does_not_alter_current_branch(self, git_repo):
        """git show não altera a branch atualmente checked out."""
        path = "doc/incidente/avaliacao-complexidade-falhando/ticket.md"
        before = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        subprocess.run(
            ["git", "show", f"origin/{git_repo['hotfix_branch']}:{path}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        )

        after = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        assert before == after == "main", (
            "git show não deve alterar a branch atual do workdir."
        )


# ─── TC-05/TC-06: cherry-pick de doc para branch temporária ──────────────────


class TestTC05CherryPickDeDocumentacao:
    """TC-05/TC-06: Caso A do procedimento — preservar o ticket via
    cherry-pick do commit de documentação para uma branch temporária a
    partir de epic, antes de abrir o PR.
    """

    def test_cherry_pick_doc_commit_succeeds(self, git_repo):
        """Cherry-pick do commit de doc do hotfix23 em branch temp a partir de epic."""
        subprocess.run(["git", "checkout", "-b", "temp-hotfix23-merge", "origin/epic"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        doc_commit = subprocess.run(
            ["git", "log", "--format=%H", f"origin/{git_repo['hotfix_branch']}", "-1"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        result = subprocess.run(
            ["git", "cherry-pick", doc_commit],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        )

        assert result.returncode == 0, (
            f"Cherry-pick do commit de doc deve ter sucesso (sem conflito). "
            f"stderr: {result.stderr}"
        )

    def test_cherry_picked_ticket_content_matches_original(self, git_repo):
        """Após o cherry-pick, o conteúdo do ticket na branch temp é idêntico ao original."""
        subprocess.run(["git", "checkout", "-b", "temp-hotfix23-merge2", "origin/epic"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        doc_commit = subprocess.run(
            ["git", "log", "--format=%H", f"origin/{git_repo['hotfix_branch']}", "-1"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        subprocess.run(["git", "cherry-pick", doc_commit], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        ticket_path = (
            git_repo["repo"] / "doc" / "incidente"
            / "avaliacao-complexidade-falhando" / "ticket.md"
        )
        assert ticket_path.exists()
        content = ticket_path.read_text()
        assert "Causa raiz" in content
        assert "Persistir via label agent-level" in content


class TestTC07BranchTempSemCodigoDeProducao:
    """TC-07: Restrição da issue — 'não alterar código de produção nesta
    task, apenas documentação de incidente'. A branch temporária de
    preservação deve conter só o arquivo de doc adicionado pelo cherry-pick,
    sem tocar em código já existente em epic.
    """

    def test_temp_branch_diff_from_epic_is_doc_only(self, git_repo):
        """O diff entre a branch temp e epic contém apenas arquivos em doc/."""
        subprocess.run(["git", "checkout", "-b", "temp-hotfix23-merge3", "origin/epic"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        doc_commit = subprocess.run(
            ["git", "log", "--format=%H", f"origin/{git_repo['hotfix_branch']}", "-1"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        subprocess.run(["git", "cherry-pick", doc_commit], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        diff_result = subprocess.run(
            ["git", "diff", "--name-only", "origin/epic", "temp-hotfix23-merge3"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        )
        changed_files = [f for f in diff_result.stdout.strip().splitlines() if f]

        assert changed_files, "Cherry-pick deve produzir ao menos um arquivo alterado."
        assert all(f.startswith("doc/") for f in changed_files), (
            f"Apenas arquivos em doc/ devem ser alterados pelo cherry-pick "
            f"de preservação. Encontrado: {changed_files}"
        )
        assert "commands.py" not in changed_files, (
            "Código de produção (commands.py) não deve ser alterado pela "
            "branch de preservação do ticket."
        )


# ─── TC-08 a TC-11: remoção da branch do remoto ──────────────────────────────


class TestTC08RemocaoDaBranchHotfix23:
    """TC-08/TC-09/TC-10/TC-11: Passo 4 do procedimento — remover
    hotfix23 do remoto após a decisão do Passo 3, confirmar via prune e
    garantir que epic permanece intacto.
    """

    def test_push_delete_hotfix23_succeeds(self, git_repo):
        """git push origin --delete hotfix23-... tem exit 0."""
        result = subprocess.run(
            ["git", "push", "origin", "--delete", git_repo["hotfix_branch"]],
            cwd=str(git_repo["repo"]), capture_output=True,
        )
        assert result.returncode == 0, (
            f"Remoção da branch hotfix23 deve ter sucesso. "
            f"stderr: {result.stderr.decode()}"
        )

    def test_fetch_prune_removes_local_reference(self, git_repo):
        """git fetch --prune remove a referência local após delete no remoto."""
        subprocess.run(
            ["git", "push", "origin", "--delete", git_repo["hotfix_branch"]],
            cwd=str(git_repo["repo"]), check=True, capture_output=True,
        )
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        result = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        )
        assert f"origin/{git_repo['hotfix_branch']}" not in result.stdout

    def test_branch_r_grep_hotfix23_returns_empty(self, git_repo):
        """Critério de aceite: `git branch -r | grep hotfix23` retorna vazio."""
        subprocess.run(
            ["git", "push", "origin", "--delete", git_repo["hotfix_branch"]],
            cwd=str(git_repo["repo"]), check=True, capture_output=True,
        )
        subprocess.run(["git", "fetch", "origin", "--prune"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        branch_r = subprocess.run(
            ["git", "branch", "-r"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout

        matches = [line for line in branch_r.splitlines() if "hotfix23" in line]
        assert matches == [], (
            f"git branch -r | grep hotfix23 deve retornar vazio. "
            f"Encontrado: {matches}"
        )

    def test_epic_hash_unchanged_after_hotfix23_deletion(self, git_repo):
        """Remoção de hotfix23 não altera o hash de origin/epic."""
        before = subprocess.run(
            ["git", "rev-parse", "origin/epic"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        subprocess.run(
            ["git", "push", "origin", "--delete", git_repo["hotfix_branch"]],
            cwd=str(git_repo["repo"]), check=True, capture_output=True,
        )
        subprocess.run(["git", "fetch", "origin"], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        after = subprocess.run(
            ["git", "rev-parse", "origin/epic"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        assert before == after, (
            "origin/epic não deve ser afetado pela remoção da branch hotfix23."
        )


class TestTC12BranchInexistenteEIdempotencia:
    """TC-12: Se a branch hotfix23 já não existir no remoto (ex.: segunda
    execução do procedimento, ou remoção manual prévia), a tentativa de
    remoção deve falhar de forma previsível — sem erro crítico do
    procedimento, apenas exit não-zero tratável.
    """

    def test_deleting_already_removed_branch_returns_nonzero_not_crash(
        self, git_repo,
    ):
        """Segunda tentativa de delete da mesma branch retorna exit não-zero,
        sem lançar exceção — o procedimento deve tratar isso como 'já removida'.
        """
        subprocess.run(
            ["git", "push", "origin", "--delete", git_repo["hotfix_branch"]],
            cwd=str(git_repo["repo"]), check=True, capture_output=True,
        )

        result = subprocess.run(
            ["git", "push", "origin", "--delete", git_repo["hotfix_branch"]],
            cwd=str(git_repo["repo"]), capture_output=True,
        )

        assert result.returncode != 0, (
            "Segunda remoção da mesma branch deve retornar exit não-zero "
            "(branch já ausente), não exit 0."
        )

    def test_branch_r_confirms_absence_idempotently(self, git_repo):
        """Após remoção, chamadas repetidas de fetch --prune + branch -r
        continuam confirmando ausência sem efeito colateral.
        """
        subprocess.run(
            ["git", "push", "origin", "--delete", git_repo["hotfix_branch"]],
            cwd=str(git_repo["repo"]), check=True, capture_output=True,
        )

        for _ in range(2):
            subprocess.run(["git", "fetch", "origin", "--prune"],
                           cwd=str(git_repo["repo"]), check=True, capture_output=True)
            result = subprocess.run(
                ["git", "branch", "-r"],
                cwd=str(git_repo["repo"]), capture_output=True, text=True,
            )
            assert f"origin/{git_repo['hotfix_branch']}" not in result.stdout
