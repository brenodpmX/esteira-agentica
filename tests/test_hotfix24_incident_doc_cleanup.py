"""Casos de teste — Analisar e tratar branch hotfix24 (issues criadas em dois boards
indevidamente).

Cobre o procedimento descrito na issue #85, parte da story #75 (épico #73):
a branch `hotfix24-24-issues_criadas_em_dois_boards_indevidamente` contém apenas
documentação de incidente
(doc/incidente/issues_criadas_em_dois_boards_indevidamente/ticket.md), sem código de
correção. O procedimento exige duas decisões antes do `git push --delete`:

  1. A correção do isolamento/duplicação entre boards já foi implementada em
     `epic`/`main`?
  2. O ticket de incidente tem valor histórico e deve ser preservado via
     cherry-pick + PR antes da remoção?

Diferença crítica em relação ao caso análogo #84/hotfix23: o body da issue #85 aponta
`_belongs_to_board` como indício de que "o isolamento entre boards foi implementado" —
mas esse método resolve um incidente **diferente** (Issue Fantasma / isolamento de IDs
entre boards, correção 5), não os dois fenômenos descritos no ticket do hotfix24
(propagação de sub-issue sem coluna, e snapshot órfão de board removido do pipe.yml).
Este caso de teste valida essa distinção e confirma, via inspeção do código real do
projeto (não do bare repo simulado), que a correção específica dos dois fenômenos do
ticket **não está implementada** em `epic` — ao contrário do cenário do hotfix23, onde
o fix já existia sob outro nome.

Casos de teste:

  TC-01  branch hotfix24 NÃO é ancestral de epic (conteúdo de doc não mergeado)
  TC-02  `_belongs_to_board` existe em epic, mas é evidência de OUTRO incidente
         (isolamento de IDs/Issue Fantasma) — não responde à Pergunta 1 do ticket hotfix24
  TC-03  Fenômeno 2 (snapshot órfão): `_find_snapshot_issue` no código real do projeto
         não filtra por boards configurados — fix NÃO implementado
  TC-04  Fenômeno 1 (sub-issue propagada sem coluna): nenhuma primitiva de remoção de
         item de projeto (`deleteProjectV2Item`/`remove_from_board`) existe no código
         real do projeto — fix NÃO implementado (permanece em #106, ainda em análise)
  TC-05  leitura do ticket de incidente via `git show <branch>:<path>` sem checkout
  TC-06  cherry-pick de commit de documentação para branch temporária a partir de epic
  TC-07  cherry-pick preserva o conteúdo do ticket (dois fenômenos, causa raiz, decisão)
  TC-08  branch temporária de preservação não contém arquivos de código de produção
  TC-09  remoção da branch hotfix24 do remoto após decisão (push --delete bem-sucedido)
  TC-10  git fetch --prune remove a referência local após remoção do remoto
  TC-11  `git branch -r | grep hotfix24` retorna vazio (critério de aceite final)
  TC-12  epic permanece intacto (hash inalterado) após remoção da branch hotfix24
  TC-13  branch hotfix24 inexistente no remoto é tratada sem erro crítico (idempotência)

Estratégia de isolamento:
  - TC-01, TC-05..TC-13: repositório bare em tmp_path/remote.git (simula origin) + clone
    em tmp_path/repo (simula workdir do agente); branch `epic` e branch
    `hotfix24-...` com apenas documentação, criadas explicitamente no bare, sem tocar no
    remoto real.
  - TC-02, TC-03, TC-04: leem o código-fonte REAL do projeto (`src/`) via caminho
    absoluto do repositório de trabalho — não usam o bare repo simulado, pois o objetivo
    é verificar o estado atual da implementação, não simular um cenário hipotético.
  - Nenhum acesso à rede; nenhuma dependência de credencial; nenhuma chamada real a
    `gh pr create` (fora do escopo do teste — apenas os pré-requisitos de dados, como o
    cherry-pick isolado, são verificados).
"""

import subprocess
from pathlib import Path

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def git_repo(tmp_path):
    """Cria um repositório bare (remote) e um clone local com:
      - commit inicial em `main`
      - branch `epic` criada a partir de `main`
      - branch `hotfix24-24-issues_criadas_em_dois_boards_indevidamente` criada a
        partir de `epic`, contendo APENAS o ticket de incidente em doc/incidente/,
        sem código de correção

    Retorna um dict com:
      - remote: Path para o bare repo (origin)
      - repo:   Path para o clone local (workdir)
      - hotfix_branch: nome da branch de incidente
      - ticket_path: caminho relativo do ticket dentro do repo
    """
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    hotfix_branch = "hotfix24-24-issues_criadas_em_dois_boards_indevidamente"
    ticket_rel = "doc/incidente/issues_criadas_em_dois_boards_indevidamente/ticket.md"

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

    # Branch epic a partir de main (código de produção simulado, sem relação com
    # o fix dos dois fenômenos do ticket)
    subprocess.run(["git", "checkout", "-b", "epic"], cwd=str(repo),
                   check=True, capture_output=True)
    (repo / "epic_base.md").write_text("epic base\n")
    subprocess.run(["git", "add", "epic_base.md"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "chore: epic base"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "epic"], cwd=str(repo),
                   check=True, capture_output=True)

    # Branch hotfix24 a partir de epic — apenas doc de incidente
    subprocess.run(["git", "checkout", "-b", hotfix_branch], cwd=str(repo),
                   check=True, capture_output=True)
    incident_dir = repo / "doc" / "incidente" / "issues_criadas_em_dois_boards_indevidamente"
    incident_dir.mkdir(parents=True)
    ticket_path = incident_dir / "ticket.md"
    ticket_path.write_text(
        "# Incidente — Issues criadas em dois boards indevidamente\n\n"
        "## Triagem\n"
        "Dois fenômenos distintos:\n"
        "1. Fenômeno 1 — sub-issue propagada sem coluna via set_parent "
        "(efeito colateral do GitHub Projects V2).\n"
        "2. Fenômeno 2 — snapshot órfão de board removido do pipe.yml "
        "(_find_snapshot_issue sem filtro de board_ids).\n\n"
        "## Decisão de tratamento\n"
        "Opção 2 — tasks de correção no board Task, uma por fenômeno.\n"
    )
    subprocess.run(["git", "add", "."], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "docs: ticket de incidente dois boards indevidamente"],
        cwd=str(repo), check=True, capture_output=True,
    )
    subprocess.run(["git", "push", "-u", "origin", hotfix_branch], cwd=str(repo),
                   check=True, capture_output=True)

    subprocess.run(["git", "checkout", "main"], cwd=str(repo),
                   check=True, capture_output=True)
    subprocess.run(["git", "fetch", "origin"], cwd=str(repo),
                   check=True, capture_output=True)

    return {
        "remote": remote,
        "repo": repo,
        "hotfix_branch": hotfix_branch,
        "ticket_path": ticket_rel,
    }


@pytest.fixture()
def project_root() -> Path:
    """Raiz do repositório de trabalho real (não o bare repo simulado) — usada
    pelos TCs que inspecionam o estado atual da implementação em `src/`.
    """
    return Path(__file__).resolve().parent.parent


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _is_ancestor(repo: Path, branch: str, base: str = "origin/epic") -> bool:
    """Executa git merge-base --is-ancestor origin/<branch> <base>."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"origin/{branch}", base],
        cwd=str(repo),
        capture_output=True,
    )
    return result.returncode == 0


# ─── TC-01: branch hotfix24 NÃO é ancestral de epic ──────────────────────────


class TestTC01BranchNaoIntegradaEmEpic:
    """TC-01: A branch hotfix24 contém apenas doc/incidente, nunca mergeada em
    epic. Assim como no hotfix23, o critério de remoção não pode ser 'já
    integrada' — exige decisão explícita de preservar ou descartar a doc.
    """

    def test_hotfix24_is_not_ancestor_of_epic(self, git_repo):
        assert not _is_ancestor(git_repo["repo"], git_repo["hotfix_branch"]), (
            "A branch hotfix24 não deve ser detectada como já integrada em "
            "epic — seu conteúdo de documentação nunca foi mergeado."
        )


# ─── TC-02: _belongs_to_board é evidência de OUTRO incidente ────────────────


class TestTC02BelongsToBoardEhOutroIncidente:
    """TC-02: A issue #85 sugere `_belongs_to_board` como indício de que 'o
    isolamento entre boards foi implementado'. Esse método existe de fato em
    `epic`, mas resolve o incidente de isolamento de IDs (Issue Fantasma,
    correção 5) — valida pertinência antes de operações destrutivas
    (update_issue/close_issue), não impede a criação/propagação de uma issue
    em dois boards simultaneamente. Não é evidência válida para a Pergunta 1
    do ticket do hotfix24.
    """

    def test_belongs_to_board_exists_in_real_project(self, project_root):
        """_belongs_to_board existe no código real do projeto (confirma o fato
        observado no body da issue #85)."""
        github_board = project_root / "src" / "adapters" / "github_board.py"
        assert github_board.exists()
        content = github_board.read_text()
        assert "_belongs_to_board" in content

    def test_belongs_to_board_guards_destructive_ops_not_creation(self, project_root):
        """_belongs_to_board é chamado a partir de um guard usado antes de
        operações destrutivas (update/close) — não intercepta a criação/
        propagação de item em múltiplos boards, que é a causa dos dois
        fenômenos do ticket do hotfix24."""
        github_board = project_root / "src" / "adapters" / "github_board.py"
        content = github_board.read_text()
        assert "_assert_belongs_to_board" in content, (
            "Deve existir o guard que usa _belongs_to_board."
        )
        # O guard não aparece em nenhuma primitiva de criação (create_issue)
        # nem no pós-hook de set_parent/sub_issues — ele é escopado a
        # update/close, confirmando que não resolve os fenômenos do hotfix24.
        create_issue_idx = content.find("def create_issue(")
        assert create_issue_idx != -1
        create_issue_body_end = content.find("\n    def ", create_issue_idx + 1)
        create_issue_body = content[create_issue_idx:create_issue_body_end]
        assert "_assert_belongs_to_board" not in create_issue_body, (
            "_belongs_to_board não deve ser parte do fluxo de criação de "
            "issues — ele não é a correção dos fenômenos 1/2 do ticket "
            "hotfix24, apenas evidência do fix de outro incidente."
        )


# ─── TC-03: Fenômeno 2 (snapshot órfão) — fix NÃO implementado ──────────────


class TestTC03Fenomeno2SnapshotOrfaoNaoCorrigido:
    """TC-03: O ticket do hotfix24 propõe filtrar `_find_snapshot_issue` pelos
    boards configurados no pipe.yml. No código real do projeto, essa função
    ainda faz glob irrestrito em `.pipe/boards/*/snapshot.json`, sem receber
    nem aplicar uma lista de board_ids — o fix descrito no ticket não está
    implementado.
    """

    def test_find_snapshot_issue_has_no_board_ids_filter_param(self, project_root):
        sync_py = project_root / "src" / "core" / "sync.py"
        assert sync_py.exists()
        content = sync_py.read_text()
        def_idx = content.find("def _find_snapshot_issue(")
        assert def_idx != -1, "_find_snapshot_issue deve existir em sync.py"
        signature_end = content.find(")", def_idx)
        signature = content[def_idx:signature_end]
        assert "board_ids" not in signature and "config" not in signature, (
            "_find_snapshot_issue ainda não recebe filtro de boards "
            "configurados — o fix do Fenômeno 2 não está implementado."
        )

    def test_find_snapshot_issue_still_globs_unfiltered(self, project_root):
        sync_py = project_root / "src" / "core" / "sync.py"
        content = sync_py.read_text()
        assert 'glob("*/snapshot.json")' in content, (
            "O glob irrestrito por diretórios de board ainda deve estar "
            "presente — confirma que o Fenômeno 2 não foi corrigido."
        )


# ─── TC-04: Fenômeno 1 (sub-issue propagada) — fix NÃO implementado ─────────


class TestTC04Fenomeno1SubIssuePropagadaNaoCorrigido:
    """TC-04: O ticket do hotfix24 propõe uma primitiva de remoção de item de
    projeto (`deleteProjectV2Item`/`remove_from_board`) e um guard em
    `_apply_create_down`. No código real do projeto, nenhuma dessas
    primitivas existe — a correção permanece em andamento sob a issue #106
    (board bug/incidente), não faz parte de `epic`/`main` ainda.
    """

    def test_no_delete_project_v2_item_mutation_in_source(self, project_root):
        src_dir = project_root / "src"
        matches = []
        for path in src_dir.rglob("*.py"):
            text = path.read_text()
            if "deleteProjectV2Item" in text or "remove_from_board" in text:
                matches.append(str(path))
        assert matches == [], (
            f"Nenhum arquivo de produção deve conter a primitiva de remoção "
            f"de item de projeto ainda — encontrado em: {matches}. Se este "
            f"teste falhar, a correção de #106 pode ter sido mergeada e o "
            f"comentário da issue #85 deve ser atualizado."
        )

    def test_apply_create_down_has_no_empty_column_guard_yet(self, project_root):
        sync_py = project_root / "src" / "core" / "sync.py"
        content = sync_py.read_text()
        def_idx = content.find("def _apply_create_down(")
        assert def_idx != -1
        next_def_idx = content.find("\ndef ", def_idx + 1)
        body = content[def_idx: next_def_idx if next_def_idx != -1 else None]
        assert "remove_from_board" not in body, (
            "_apply_create_down ainda não deve conter o guard de remoção "
            "por coluna vazia — confirma que o Fenômeno 1 não foi corrigido."
        )


# ─── TC-05: leitura do ticket sem checkout ────────────────────────────────────


class TestTC05LeituraDoTicketSemCheckout:
    """TC-05: O Passo 2 do procedimento lê o ticket via `git show
    <branch>:<path>`, sem fazer checkout da branch (preserva o workdir atual).
    """

    def test_git_show_reads_ticket_content(self, git_repo):
        result = subprocess.run(
            ["git", "show", f"origin/{git_repo['hotfix_branch']}:{git_repo['ticket_path']}"],
            cwd=str(git_repo["repo"]),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Fenômeno 1" in result.stdout
        assert "Fenômeno 2" in result.stdout

    def test_git_show_does_not_alter_current_branch(self, git_repo):
        before = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        subprocess.run(
            ["git", "show", f"origin/{git_repo['hotfix_branch']}:{git_repo['ticket_path']}"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        )

        after = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        assert before == after == "main", (
            "git show não deve alterar a branch atual do workdir."
        )


# ─── TC-06/TC-07: cherry-pick de doc para branch temporária ─────────────────


class TestTC06CherryPickDeDocumentacao:
    """TC-06/TC-07: Caso A do procedimento — preservar o ticket via
    cherry-pick do commit de documentação para uma branch temporária a
    partir de epic, antes de abrir o PR.
    """

    def test_cherry_pick_doc_commit_succeeds(self, git_repo):
        subprocess.run(["git", "checkout", "-b", "temp-hotfix24-merge", "origin/epic"],
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
        subprocess.run(["git", "checkout", "-b", "temp-hotfix24-merge2", "origin/epic"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        doc_commit = subprocess.run(
            ["git", "log", "--format=%H", f"origin/{git_repo['hotfix_branch']}", "-1"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        subprocess.run(["git", "cherry-pick", doc_commit], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        ticket_path = (
            git_repo["repo"] / "doc" / "incidente"
            / "issues_criadas_em_dois_boards_indevidamente" / "ticket.md"
        )
        assert ticket_path.exists()
        content = ticket_path.read_text()
        assert "Fenômeno 1" in content
        assert "Fenômeno 2" in content
        assert "Opção 2" in content


class TestTC08BranchTempSemCodigoDeProducao:
    """TC-08: Restrição da issue — 'não alterar código de produção nesta
    task, apenas documentação de incidente'. A branch temporária de
    preservação deve conter só o arquivo de doc adicionado pelo cherry-pick.
    """

    def test_temp_branch_diff_from_epic_is_doc_only(self, git_repo):
        subprocess.run(["git", "checkout", "-b", "temp-hotfix24-merge3", "origin/epic"],
                       cwd=str(git_repo["repo"]), check=True, capture_output=True)

        doc_commit = subprocess.run(
            ["git", "log", "--format=%H", f"origin/{git_repo['hotfix_branch']}", "-1"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        ).stdout.strip()

        subprocess.run(["git", "cherry-pick", doc_commit], cwd=str(git_repo["repo"]),
                       check=True, capture_output=True)

        diff_result = subprocess.run(
            ["git", "diff", "--name-only", "origin/epic", "temp-hotfix24-merge3"],
            cwd=str(git_repo["repo"]), capture_output=True, text=True,
        )
        changed_files = [f for f in diff_result.stdout.strip().splitlines() if f]

        assert changed_files, "Cherry-pick deve produzir ao menos um arquivo alterado."
        assert all(f.startswith("doc/") for f in changed_files), (
            f"Apenas arquivos em doc/ devem ser alterados pelo cherry-pick "
            f"de preservação. Encontrado: {changed_files}"
        )
        assert "epic_base.md" not in changed_files, (
            "Código/conteúdo de produção (epic_base.md) não deve ser "
            "alterado pela branch de preservação do ticket."
        )


# ─── TC-09 a TC-12: remoção da branch do remoto ──────────────────────────────


class TestTC09RemocaoDaBranchHotfix24:
    """TC-09/TC-10/TC-11/TC-12: Passo 4 do procedimento — remover hotfix24 do
    remoto após a decisão do Passo 3, confirmar via prune e garantir que epic
    permanece intacto.
    """

    def test_push_delete_hotfix24_succeeds(self, git_repo):
        result = subprocess.run(
            ["git", "push", "origin", "--delete", git_repo["hotfix_branch"]],
            cwd=str(git_repo["repo"]), capture_output=True,
        )
        assert result.returncode == 0, (
            f"Remoção da branch hotfix24 deve ter sucesso. "
            f"stderr: {result.stderr.decode()}"
        )

    def test_fetch_prune_removes_local_reference(self, git_repo):
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

    def test_branch_r_grep_hotfix24_returns_empty(self, git_repo):
        """Critério de aceite: `git branch -r | grep hotfix24` retorna vazio."""
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

        matches = [line for line in branch_r.splitlines() if "hotfix24" in line]
        assert matches == [], (
            f"git branch -r | grep hotfix24 deve retornar vazio. "
            f"Encontrado: {matches}"
        )

    def test_epic_hash_unchanged_after_hotfix24_deletion(self, git_repo):
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
            "origin/epic não deve ser afetado pela remoção da branch hotfix24."
        )


class TestTC13BranchInexistenteEIdempotencia:
    """TC-13: Se a branch hotfix24 já não existir no remoto (ex.: segunda
    execução do procedimento, ou remoção manual prévia), a tentativa de
    remoção deve falhar de forma previsível — sem erro crítico do
    procedimento, apenas exit não-zero tratável.
    """

    def test_deleting_already_removed_branch_returns_nonzero_not_crash(
        self, git_repo,
    ):
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
