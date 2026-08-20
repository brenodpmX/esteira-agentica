"""Sync core - sincronização entre local e board remoto."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields as dataclass_fields
from datetime import datetime, timezone
from pathlib import Path

from src.core.board import Board, ChangeItem, Issue, PenaltyException, SyncEvent
from src.core.change_queue import ChangeQueue
from src.core.commands import (AGENT_LEVEL_PREFIX, apply_events_to_commands,
                               compose_body, from_issue, sanitize_relations,
                               split_body)
from src.core.config import resolve_max_attempts
from src.core.dead_letter import DeadLetterEntry, DeadLetterQueue, sanitize_reason
from src.core.log import log
from src.core.snapshot import BOARDS_DIR, Snapshot

PIPE_DIR = Path(".pipe")
ORPHAN_FILE = PIPE_DIR / "orphanFiles.json"


# Substrings estáveis de mensagens de exceção já tratadas como "definitivo"
# em pontos específicos do sync (issue fantasma / isolamento de board). São
# reconhecidas aqui de forma genérica para classify_error.
_DEFINITIVE_MESSAGE_SUBSTRINGS = (
    "Could not resolve to an issue or pull request",
    "não pertence a este board",
)

# next_step: ação recomendada, curta e acionável, por categoria de dead-letter.
_NEXT_STEP = {
    "definitivo": "item não será retentado; revisar manualmente e, se aplicável, recriar a entrada",
    "transitorio_esgotado": "limite de tentativas esgotado; verificar causa raiz antes de reenviar manualmente",
}


def classify_error(exc: Exception) -> str:
    """Classifica um erro de sincronismo em categoria estável.

    Retorna uma das três categorias:
    - "rate_limit": PenaltyException (rate limit do board, tratado pelo
      throttle/penalty — não é responsabilidade do item da fila).
    - "definitivo": mensagens estáveis que indicam que o alvo não existe ou
      nunca vai se resolver (issue fantasma, isolamento de board).
    - "transitorio": qualquer outra exceção (default seguro).

    Função pura: não faz I/O nem loga.
    """
    if isinstance(exc, PenaltyException):
        return "rate_limit"
    message = str(exc)
    if any(substr in message for substr in _DEFINITIVE_MESSAGE_SUBSTRINGS):
        return "definitivo"
    return "transitorio"


def _slugify(text: str) -> str:
    """Converte texto para slug filesystem-safe."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


def _issue_files(board_id: str, col_id: str, issue_id: str, slug: str) -> dict:
    """Retorna paths dos 3 arquivos de uma issue."""
    base = BOARDS_DIR / board_id / col_id
    prefix = f"{issue_id}-{slug}"
    return {
        "body": base / f"{prefix}-body.md",
        "history": base / f"{prefix}-history.md",
        "addcomment": base / f"{prefix}-addcomment.md",
    }


def _is_valid_registered_path(candidate: Path, board_id: str, issue_id: str,
                              snap: Snapshot) -> bool:
    """Valida se o body_path registrado no snapshot pode ser aceito de
    imediato (passo 1 do ADR-01), sem varrer o filesystem.

    Todas as condições abaixo precisam valer:
    - o arquivo existe;
    - está dentro do diretório do board (sem escape via `..`/symlink);
    - o nome termina em '-body.md';
    - o nome começa com '<issue_id>-';
    - nenhuma outra issue do snapshot registra o mesmo body_path.
    """
    if not candidate.exists():
        return False

    board_dir = (BOARDS_DIR / board_id).resolve()
    try:
        resolved = candidate.resolve()
        resolved.relative_to(board_dir)
    except ValueError:
        return False

    name = candidate.name
    if not name.endswith("-body.md"):
        return False
    if not name.startswith(f"{issue_id}-"):
        return False

    for other in snap.issues:
        if str(other.get("id")) == str(issue_id):
            continue
        if other.get("body_path") and Path(other["body_path"]) == candidate:
            return False

    return True


@dataclass
class OrphanEntry:
    """Registro de isolamento de um arquivo local órfão (.pipe/orphanFiles.json).

    Representa um arquivo com prefixo numérico que não corresponde de forma
    confiável a nenhuma issue conhecida do snapshot (ID desconhecido, ou
    ambíguo/conflitante). Deduplicado pela chave (board, apparent_id, reason,
    content_fingerprint) — ver record_orphan().
    """
    board: str
    apparent_id: str
    reason: str
    content_fingerprint: str
    path: str
    recorded_at: str  # timestamp ISO 8601 UTC


def _orphan_key(entry: OrphanEntry) -> tuple:
    return (entry.board, entry.apparent_id, entry.reason, entry.content_fingerprint)


def _read_orphans() -> list[OrphanEntry]:
    if not ORPHAN_FILE.exists():
        return []
    raw = json.loads(ORPHAN_FILE.read_text(encoding="utf-8"))
    fields = {f.name for f in dataclass_fields(OrphanEntry)}
    return [OrphanEntry(**{k: v for k, v in item.items() if k in fields}) for item in raw]


def _write_orphans(entries: list[OrphanEntry]) -> None:
    PIPE_DIR.mkdir(parents=True, exist_ok=True)
    data = [asdict(entry) for entry in entries]
    ORPHAN_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def record_orphan(board_id: str, path: Path, apparent_id: str, reason: str) -> None:
    """Registra um arquivo local órfão (isolamento sem alterar issues).

    Um arquivo é considerado órfão quando tem prefixo numérico mas não
    corresponde de forma confiável a nenhuma issue conhecida do snapshot
    (ID desconhecido, ou ambíguo/conflitante). Este registro:

    - NÃO enfileira create-up/change-up/delete-up;
    - NÃO altera o snapshot;
    - persiste em .pipe/orphanFiles.json (memória interna da esteira, ver
      PROTECTED_PATHS em src/core/agent.py), sobrevivendo entre ciclos e
      processos, seguindo o mesmo padrão de leitura/escrita JSON de
      src/core/change_queue.py e src/core/dead_letter.py;
    - deduplica pela chave (board_id, apparent_id, reason,
      content_fingerprint): só a primeira ocorrência da chave (ou quando a
      causa/conteúdo mudar) gera um novo registro e um novo log.warning.

    content_fingerprint é o SHA-256 do conteúdo do arquivo (bytes), calculado
    apenas se o arquivo ainda existir.
    """
    try:
        content = path.read_bytes()
    except OSError:
        content = b""
    fingerprint = hashlib.sha256(content).hexdigest()

    entry = OrphanEntry(
        board=board_id,
        apparent_id=apparent_id,
        reason=reason,
        content_fingerprint=fingerprint,
        path=str(path),
        recorded_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    entries = _read_orphans()
    key = _orphan_key(entry)
    if any(_orphan_key(existing) == key for existing in entries):
        return

    entries.append(entry)
    _write_orphans(entries)

    log.warning(
        "Sync",
        f"[{board_id}] arquivo órfão detectado: '{path}' (ID aparente "
        f"#{apparent_id}, motivo: {reason}) — verificar manualmente se o "
        f"arquivo pertence a esta issue ou deve ser renomeado sem prefixo "
        f"numérico",
        board_id=board_id, path=str(path), apparent_id=apparent_id,
        reason=reason,
    )


def _find_issue_files(board_id: str, issue_id: str) -> Path | None:
    """Encontra o arquivo body de uma issue em qualquer coluna do board.

    Resolução determinística por identidade (ADR-01 / RN-005 / RN-006):

    1. O body_path registrado no snapshot é a fonte de verdade quando válido
       (existe, dentro do board, sufixo/prefixo corretos, não reivindicado
       por outra issue) — aceito imediatamente, sem varrer o filesystem.
    2. Se o path registrado não for aceito, busca pelo nome completo do
       arquivo (Path(body_path).name) em todas as colunas do board.
    3. Aceita somente se exatamente 1 candidato for encontrado no passo 2 e
       ele não pertencer (via body_path) a outra issue do snapshot.
    4. Sem body_path registrado (issue legada): fallback por prefixo
       numérico ('<issue_id>-*-body.md'), aceito somente com exatamente 1
       candidato.

    Qualquer recusa (zero ou múltiplos candidatos) retorna None e loga um
    warning — nunca escolhe arbitrariamente. Função puramente local: não faz
    chamada de rede/board.
    """
    snap = Snapshot(board_id).load()
    issue_data = snap.issue(issue_id)

    board_dir = BOARDS_DIR / board_id
    if not board_dir.exists():
        return None

    registered = issue_data.get("body_path") if issue_data else None

    if registered:
        candidate = Path(registered)
        if _is_valid_registered_path(candidate, board_id, issue_id, snap):
            return candidate

        # Passo 2/3: path registrado inválido/ausente — buscar pelo nome
        # completo do arquivo em todas as colunas do board. O nome buscado
        # só é uma identidade válida de body file se respeitar o mesmo
        # contrato do passo 1 (sufixo '-body.md' e prefixo '<issue_id>-');
        # caso contrário não há candidato válido possível (ex.: o próprio
        # path registrado tinha sufixo/prefixo errado).
        file_name = Path(registered).name
        if not (file_name.endswith("-body.md") and file_name.startswith(f"{issue_id}-")):
            log.warning(
                "Sync",
                f"[{board_id}] #{issue_id} body_path registrado com nome "
                f"inválido: '{file_name}'",
                board_id=board_id, issue_id=issue_id,
                reason="nome de body_path inválido",
            )
            return None

        candidates = list(board_dir.rglob(file_name))

        if len(candidates) == 0:
            log.warning(
                "Sync",
                f"[{board_id}] #{issue_id} zero candidatos ao buscar '{file_name}'",
                board_id=board_id, issue_id=issue_id, reason="zero candidatos",
            )
            return None
        if len(candidates) > 1:
            log.warning(
                "Sync",
                f"[{board_id}] #{issue_id} múltiplos candidatos: "
                f"{[str(c) for c in candidates]}",
                board_id=board_id, issue_id=issue_id,
                reason=f"múltiplos candidatos: {[str(c) for c in candidates]}",
            )
            return None

        candidate = candidates[0]
        for other in snap.issues:
            if str(other.get("id")) == str(issue_id):
                continue
            if other.get("body_path") and Path(other["body_path"]) == candidate:
                log.warning(
                    "Sync",
                    f"[{board_id}] #{issue_id} candidato '{candidate}' "
                    f"reivindicado por outra issue",
                    board_id=board_id, issue_id=issue_id,
                    reason="candidato reivindicado por outra issue",
                )
                return None
        return candidate

    # Passo 4: sem body_path registrado (issue legada) — fallback por
    # prefixo numérico, aceito somente com exatamente 1 candidato.
    candidates = list(board_dir.rglob(f"{issue_id}-*-body.md"))
    if len(candidates) == 0:
        log.warning(
            "Sync",
            f"[{board_id}] #{issue_id} zero candidatos por prefixo numérico",
            board_id=board_id, issue_id=issue_id, reason="zero candidatos",
        )
        return None
    if len(candidates) > 1:
        log.warning(
            "Sync",
            f"[{board_id}] #{issue_id} múltiplos candidatos: "
            f"{[str(c) for c in candidates]}",
            board_id=board_id, issue_id=issue_id,
            reason=f"múltiplos candidatos: {[str(c) for c in candidates]}",
        )
        return None
    return candidates[0]


def _col_from_path(file_path: Path, board_id: str) -> str:
    """Extrai col_id do path do arquivo."""
    # .pipe/boards/<board_id>/<col_id>/<file>
    return file_path.parent.name


def _fire_column_events(board_id: str, issue_id: str, board_obj: Board,
                        config: dict, old_col: str, new_col: str) -> None:
    """Dispara eventos on_out (coluna de origem) e on_in (coluna de destino)."""
    if not config:
        return
    columns = (config.get("boards", {}).get(board_id, {}) or {}).get("columns", {})

    out_events = (columns.get(old_col, {}) or {}).get("on_out") if old_col else None
    if out_events:
        log.info("Sync", f"[{board_id}] #{issue_id} on_out '{old_col}': {out_events}")
        board_obj.apply_column_events(board_id, issue_id, out_events)

    in_events = (columns.get(new_col, {}) or {}).get("on_in") if new_col else None
    if in_events:
        log.info("Sync", f"[{board_id}] #{issue_id} on_in '{new_col}': {in_events}")
        board_obj.apply_column_events(board_id, issue_id, in_events)


def _column_archives(board_id: str, col_id: str, config: dict) -> bool:
    """True se a coluna arquiva ao entrar (on_in contém o evento 'archive')."""
    if not config or not col_id:
        return False
    columns = (config.get("boards", {}).get(board_id, {}) or {}).get("columns", {})
    return "archive" in ((columns.get(col_id, {}) or {}).get("on_in") or [])


def _compose_down_body(issue: Issue) -> str:
    """Monta o conteúdo do arquivo body no fluxo down.

    Formato: '# {title}\n\n{body_limpo}' + bloco @--- de comandos derivado do
    estado real da issue no board (relações, labels, need_human).
    O body vindo do board é limpo de qualquer bloco @--- pré-existente para
    evitar duplicação, e os comandos autoritativos da API são reescritos.
    """
    clean_body, _ = split_body(issue.body or "")
    cmds = from_issue(issue)
    full = compose_body(clean_body, cmds)
    return f"# {issue.title}\n\n{full}\n"


# ══════════════════════════════════════════════════════════════════════════════
# Estado conhecido no snapshot + gatilho de par recíproco (dependências)
# ══════════════════════════════════════════════════════════════════════════════

# Mapa de relação -> relação recíproca no alvo.
# Se X.parent = Y      então Y.children contém X
# Se X.children ∋ Y     então Y.parent = X
# Se X.blocked_by ∋ Y   então Y.blocks contém X
# Se X.blocks ∋ Y       então Y.blocked_by contém X
_RECIPROCAL = {
    "parent": "children",
    "children": "parent",
    "blocked_by": "blocks",
    "blocks": "blocked_by",
}


def _empty_state() -> dict:
    """Estado conhecido vazio (para issues recém-criadas, sem baseline)."""
    return {
        "labels": [], "parent": None, "children": [],
        "blocked_by": [], "blocks": [], "archived": False, "state": "open",
    }


def _known_state(issue_data: dict) -> dict:
    """Extrai o estado conhecido (para diff) de um registro de snapshot."""
    if not issue_data:
        return _empty_state()
    return {
        "labels": list(issue_data.get("labels") or []),
        "parent": issue_data.get("parent"),
        "children": list(issue_data.get("children") or []),
        "blocked_by": list(issue_data.get("blocked_by") or []),
        "blocks": list(issue_data.get("blocks") or []),
        "archived": bool(issue_data.get("archived")),
        "state": (issue_data.get("state") or "open"),
    }


def _write_state_from_cmds(issue_data: dict, cmds) -> None:
    """Grava no snapshot o estado desejado declarado nos comandos (fluxo up)."""
    issue_data["labels"] = cmds.all_labels()
    issue_data["parent"] = str(cmds.parent) if cmds.parent else None
    issue_data["children"] = [str(c) for c in (cmds.children or [])]
    issue_data["blocked_by"] = [str(b) for b in (cmds.blocked_by or [])]
    issue_data["blocks"] = [str(b) for b in (cmds.blocks or [])]
    issue_data["archived"] = bool(cmds.archive)
    if cmds.close:
        issue_data["state"] = "closed"
    elif cmds.reopen:
        issue_data["state"] = "open"


def _write_state_from_issue(issue_data: dict, issue, fullsync: bool) -> None:
    """Grava no snapshot o estado real vindo do board (fluxo down).

    Sempre grava labels/parent/children/archived/state (chamada única).
    blocked_by/blocks só são sobrescritos em fullsync (senão preserva o que já
    havia no snapshot, pois deps não vêm na chamada única).
    """
    issue_data["labels"] = list(issue.labels or [])
    issue_data["parent"] = issue.parent
    issue_data["children"] = list(issue.children or [])
    issue_data["archived"] = bool(getattr(issue, "archived", False))
    issue_data["state"] = (issue.state or "open")
    if fullsync:
        issue_data["blocked_by"] = list(issue.blocked_by or [])
        issue_data["blocks"] = list(issue.blocks or [])


def _find_snapshot_issue(target_id: str, allowed_boards: list[str] | None = None) -> tuple[str, dict] | None:
    """Localiza o registro de snapshot de uma issue em qualquer board.

    `allowed_boards`, quando informado, restringe a busca aos boards indicados —
    diretórios de boards fora da configuração são ignorados (não servem como
    evidência). `None` mantém o comportamento histórico (varre todo o glob).

    Retorna (board_id, issue_data) ou None se a issue não é rastreada.
    """
    if not BOARDS_DIR.exists():
        return None
    allowed = set(allowed_boards) if allowed_boards is not None else None
    for snap_file in BOARDS_DIR.glob("*/snapshot.json"):
        board_id = snap_file.parent.name
        if allowed is not None and board_id not in allowed:
            continue
        snap = Snapshot(board_id).load()
        data = snap.issue(target_id)
        if data is not None:
            return board_id, data
    return None


def _propagation_proof(board_id: str, issue_id: str, config: dict) -> tuple[str, str] | None:
    """Evidência de que a issue chegou ao board por propagação automática.

    A única evidência aceita é a própria issue já registrada em OUTRO board
    configurado, com coluna conhecida nas `columns` daquele board no `pipe.yml`.
    `parent` isolado NÃO é evidência: uma sub-issue nova e legítima deste board
    também pode chegar com coluna vazia.

    Snapshots de diretórios fora da configuração são ignorados (board removido do
    `pipe.yml` não prova nada).

    Retorna (board_id_de_origem, coluna) ou None quando não há prova.
    """
    boards = (config or {}).get("boards", {}) or {}
    others = [bid for bid in boards if bid != "platform" and bid != board_id]
    if not others:
        return None

    found = _find_snapshot_issue(issue_id, allowed_boards=others)
    if not found:
        return None

    other_board, data = found
    column = (data.get("column") or "").strip()
    known_cols = (boards.get(other_board, {}) or {}).get("columns", {}) or {}
    if column and column in known_cols:
        return other_board, column
    return None


def _reciprocates(target_data: dict, reciprocal_rel: str, source_id: str) -> bool:
    """True se o snapshot do alvo já reflete o par recíproco apontando p/ source."""
    source_id = str(source_id)
    if reciprocal_rel == "parent":
        return str(target_data.get("parent") or "") == source_id
    return source_id in {str(x) for x in (target_data.get(reciprocal_rel) or [])}


def _trigger_reciprocal_downs(source_id: str, deltas: dict, queue) -> None:
    """Enfileira down fullsync dos alvos cujo par recíproco está inconsistente.

    Para cada relação com alvos adicionados/removidos, checa o snapshot do
    alvo:
      - adicionado: enfileira se o alvo AINDA NÃO reciproca source (par a criar)
      - removido:   enfileira se o alvo AINDA reciproca source (par a desfazer)
    A checagem de par é a condição de parada: quando o alvo já está coerente,
    nada é enfileirado, evitando reação em cadeia infinita.
    """
    for rel, reciprocal_rel in _RECIPROCAL.items():
        change = deltas.get(rel) or {}
        for target_id in change.get("added", []):
            found = _find_snapshot_issue(str(target_id))
            if not found:
                continue  # alvo não rastreado - ignora
            t_board, t_data = found
            if not _reciprocates(t_data, reciprocal_rel, source_id):
                if queue.add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id=str(target_id),
                                           board=t_board, fullsync=True)):
                    log.info("Sync", f"[{t_board}] #{target_id} down full (par {rel} "
                             f"adicionado por #{source_id})")
        for target_id in change.get("removed", []):
            found = _find_snapshot_issue(str(target_id))
            if not found:
                continue
            t_board, t_data = found
            if _reciprocates(t_data, reciprocal_rel, source_id):
                if queue.add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id=str(target_id),
                                           board=t_board, fullsync=True)):
                    log.info("Sync", f"[{t_board}] #{target_id} down full (par {rel} "
                             f"removido por #{source_id})")


def _cleanup_block_relations_on_delete(deleted_id: str, deleted_data: dict,
                                       board_obj: Board, queue) -> None:
    """Remédio 2: ao deletar (up/down) uma issue, remove os vínculos de bloqueio
    recíprocos das issues apontadas por ela (em qualquer board) e as enfileira
    para fullsync (bloqueio removido).

    A issue deletada aponta:
      - blocks ∋ Y      → Y.blocked_by ∋ deletada  → remove deletada de Y.blocked_by
      - blocked_by ∋ Z  → Z.blocks ∋ deletada      → remove deletada de Z.blocks

    Para cada alvo ainda vinculado, remove o vínculo no board (set_*) e enfileira
    um change-down fullsync para reconciliar o estado local.
    """
    if not deleted_data or queue is None:
        return
    deleted_id = str(deleted_id)

    # (relação na deletada, relação recíproca no alvo)
    plan = (
        ("blocks", "blocked_by"),   # alvos que a deletada bloqueava
        ("blocked_by", "blocks"),   # alvos que bloqueavam a deletada
    )
    for rel, reciprocal_rel in plan:
        for target_id in [str(x) for x in (deleted_data.get(rel) or [])]:
            found = _find_snapshot_issue(target_id)
            if not found:
                continue  # alvo não rastreado - ignora
            t_board, _ = found
            t_snap = Snapshot(t_board).load()
            t_data = t_snap.issue(target_id)
            if not t_data:
                continue
            current = [str(x) for x in (t_data.get(reciprocal_rel) or [])]
            if deleted_id not in current:
                continue  # já não há vínculo recíproco
            new_vals = [x for x in current if x != deleted_id]
            if reciprocal_rel == "blocked_by":
                board_obj.set_blocked_by(t_board, target_id, new_vals, known_current=current)
            else:
                board_obj.set_blocks(t_board, target_id, new_vals, known_current=current)
            t_data[reciprocal_rel] = new_vals
            t_snap.save()
            queue.add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id=target_id,
                                    board=t_board, fullsync=True))
            log.info("Sync", f"[{t_board}] #{target_id} bloqueio removido "
                     f"(issue #{deleted_id} deletada)")


def _deps_deltas_from_snapshot(issue, issue_data: dict) -> dict:
    """Calcula deltas de blocked_by/blocks entre issue (board) e snapshot.

    Usado no fluxo down fullsync para disparar o gatilho de par recíproco.
    Retorna deltas só das relações de dependência (parent/children não mudam
    de forma reflexiva no down).
    """
    known_bb = {str(x) for x in (issue_data.get("blocked_by") or [])}
    known_bk = {str(x) for x in (issue_data.get("blocks") or [])}
    now_bb = {str(x) for x in (issue.blocked_by or [])}
    now_bk = {str(x) for x in (issue.blocks or [])}
    return {
        "blocked_by": {"added": list(now_bb - known_bb),
                       "removed": list(known_bb - now_bb)},
        "blocks": {"added": list(now_bk - known_bk),
                   "removed": list(known_bk - now_bk)},
    }


# ══════════════════════════════════════════════════════════════════════════════
# sync_remote - busca mudanças do board remoto desde last_board_update
# ══════════════════════════════════════════════════════════════════════════════

def sync_remote(board_id: str, board_obj: Board, queue: ChangeQueue):
    """Busca issues modificados desde last_board_update e enfileira mudanças."""
    snap = Snapshot(board_id).load()
    since = snap.last_board_update

    if not since:
        # Sem data anterior, usa detect_board_changes (full)
        board_obj.detect_board_changes(board_id, snap, queue)
        return

    remote_issues = board_obj.list_issues_since(board_id, since)
    snapshot_by_id = {str(i["id"]): i for i in snap.issues if i.get("id")}
    max_updated = since

    for issue in remote_issues:
        issue_id = str(issue.id)
        if issue.updated_at and issue.updated_at > max_updated:
            max_updated = issue.updated_at

        known = snapshot_by_id.get(issue_id)
        if known is None:
            # Create precisa de fullsync: monta o body com deps (from_issue) e
            # não há baseline no snapshot para preservá-las.
            if queue.add(ChangeItem.of(SyncEvent.CREATE_DOWN, id=issue_id,
                                       board=board_id, fullsync=True)):
                log.trace("Sync", f"[{board_id}] #{issue_id} create-down")
        else:
            if queue.add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id=issue_id, board=board_id)):
                known["status"] = SyncEvent.CHANGE_DOWN.value
                log.trace("Sync", f"[{board_id}] #{issue_id} change-down")

    if max_updated != since:
        snap.last_board_update = max_updated
    snap.save()


# ══════════════════════════════════════════════════════════════════════════════
# detect_local_changes - descobre movimentos locais
# ══════════════════════════════════════════════════════════════════════════════

def detect_local_changes(board_id: str, queue: ChangeQueue):
    """Detecta criações, modificações e deleções locais.

    Arquivos com prefixo numérico (`^(\\d+)-`) só são adotados como o body de
    `issue_id` quando passam na mesma regra de "match confiável" usada por
    `_find_issue_files`/`_is_valid_registered_path` (ADR-01): path já
    registrado e válido no snapshot, ou único candidato por nome completo, ou
    único candidato por prefixo quando a issue ainda não tem `body_path`
    registrado. Qualquer arquivo com prefixo numérico que não passe nessa
    regra (ID desconhecido no snapshot, ou ambíguo/conflitante) é isolado via
    record_orphan() — nunca enfileira create-up/change-up/delete-up nem
    altera o snapshot a partir dele.
    """
    snap = Snapshot(board_id).load()
    board_dir = BOARDS_DIR / board_id
    snapshot_by_id = {str(i["id"]): i for i in snap.issues if i.get("id")}

    # Agrupa todos os arquivos body locais com prefixo numérico por ID
    # aparente, para resolver cada grupo com a regra de match confiável.
    numbered_candidates: dict[str, list[Path]] = {}
    local_bodies = {}  # id -> Path (apenas matches confiáveis)
    for body_file in board_dir.rglob("*-body.md"):
        match = re.match(r"^(\d+)-", body_file.name)
        if match:
            issue_id = match.group(1)
            numbered_candidates.setdefault(issue_id, []).append(body_file)
        else:
            # Arquivo sem id numérico = issue criada localmente (sem id).
            #
            # NÃO usar heurística de contagem de hífens aqui. `_slugify`
            # converte hífens e espaços em underscore, então todo arquivo
            # nomeado pelo próprio sistema tem exatamente UM hífen — o do
            # sufixo `-body`. A condição `count("-") >= 2` descartava
            # silenciosamente esses nomes e o create-up nunca era gerado.
            body_path_str = str(body_file)
            # Verificar se já está no snapshot por body_path
            known = any(
                i.get("body_path") == body_path_str
                for i in snap.issues
            )
            if not known:
                if queue.add(ChangeItem.of(SyncEvent.CREATE_UP, identifier=body_path_str, board=board_id)):
                    snap.issues.append({
                        "id": None,
                        "column": _col_from_path(body_file, board_id),
                        "body_path": body_path_str,
                        "body_mtime": str(body_file.stat().st_mtime),
                        "status": SyncEvent.CREATE_UP.value,
                    })
                    log.trace("Sync", f"[{board_id}] '{body_file.name}' create-up")

    # Resolve cada grupo de candidatos por ID aparente com a mesma regra de
    # match confiável de _find_issue_files (reaproveitando _is_valid_registered_path
    # para não duplicar a lógica de resolução).
    for issue_id, candidates in numbered_candidates.items():
        issue_data = snapshot_by_id.get(issue_id)

        if issue_data is None:
            # ID desconhecido no snapshot: todos os candidatos são órfãos.
            for candidate in candidates:
                record_orphan(board_id, candidate, issue_id,
                             "issue desconhecida no snapshot")
            continue

        registered = issue_data.get("body_path")
        accepted = None

        if registered:
            registered_path = Path(registered)
            if _is_valid_registered_path(registered_path, board_id, issue_id, snap):
                accepted = registered_path
            else:
                # Path registrado inválido: aceita somente se houver
                # exatamente 1 candidato entre os encontrados localmente.
                if len(candidates) == 1:
                    accepted = candidates[0]
        else:
            # Issue legada sem body_path registrado: aceita somente com
            # exatamente 1 candidato.
            if len(candidates) == 1:
                accepted = candidates[0]

        for candidate in candidates:
            if accepted is not None and candidate.resolve() == accepted.resolve():
                continue
            reason = ("ambíguo: múltiplos candidatos" if len(candidates) > 1
                      else "conflita com body_path de outra issue")
            record_orphan(board_id, candidate, issue_id, reason)

        if accepted is not None:
            local_bodies[issue_id] = accepted
        elif len(candidates) > 1:
            # Ambíguo: múltiplos candidatos e nenhum aceito.
            # NÃO tratar como "deletado" — a issue existe fisicamente,
            # apenas a identidade é ambígua. Registrar para que o loop
            # de delete-up a ignore (evita fechar a issue no board por
            # engano — regressão do incidente #76/#97).
            local_bodies[issue_id] = None  # marca presença sem path aceito

    # Para cada issue no snapshot com id, verificar mudanças
    for issue in snap.issues:
        issue_id = str(issue.get("id") or "")
        if not issue_id or issue.get("status") in (
            SyncEvent.CREATE_UP.value, SyncEvent.CREATE_DOWN.value,
            SyncEvent.DELETE_UP.value, SyncEvent.DELETE_DOWN.value,
            SyncEvent.CHANGE_DOWN.value,
        ):
            continue

        body_path = Path(issue.get("body_path") or "")
        local_file = local_bodies.get(issue_id)

        # Delete-up: body não encontrado em nenhum diretório.
        # Quando a resolução é ambígua (issue_id presente em local_bodies
        # com valor None), NÃO emitir delete-up — a issue existe fisicamente,
        # apenas não foi possível determinar com segurança qual arquivo a
        # representa. O isolamento já foi registrado via record_orphan;
        # a issue permanece intacta no snapshot/board até intervenção manual.
        if local_file is None and issue_id not in local_bodies:
            if queue.add(ChangeItem.of(SyncEvent.DELETE_UP, id=issue_id, board=board_id)):
                issue["status"] = SyncEvent.DELETE_UP.value
                log.info("Sync", f"[{board_id}] #{issue_id} delete-up")
            continue

        # Identidade ambígua: issue existe no filesystem mas nenhum candidato
        # foi aceito inequivocamente. Não emitir nenhum evento (nem delete nem
        # change) — esperar intervenção manual.
        if local_file is None:
            continue

        # Arquivo aceito mas removido entre a descoberta e a verificação
        # (race condition): emitir delete-up normalmente.
        if not local_file.exists():
            if queue.add(ChangeItem.of(SyncEvent.DELETE_UP, id=issue_id, board=board_id)):
                issue["status"] = SyncEvent.DELETE_UP.value
                log.trace("Sync", f"[{board_id}] #{issue_id} delete-up")
            continue

        # Change-up: mtime maior, coluna diferente, ou addcomment com conteúdo
        changed = False
        current_mtime = str(local_file.stat().st_mtime)
        stored_mtime = issue.get("body_mtime", "")

        if current_mtime > stored_mtime:
            changed = True

        current_col = _col_from_path(local_file, board_id)
        if current_col != issue.get("column"):
            changed = True

        # Verificar addcomment em qualquer diretório
        slug = local_file.stem.removesuffix("-body")
        for ac_file in board_dir.rglob(f"{slug}-addcomment.md"):
            if ac_file.exists() and ac_file.read_text(encoding="utf-8").strip():
                changed = True
                break

        if changed:
            if queue.add(ChangeItem.of(SyncEvent.CHANGE_UP, id=issue_id, board=board_id)):
                issue["status"] = SyncEvent.CHANGE_UP.value
                log.trace("Sync", f"[{board_id}] #{issue_id} change-up")

    snap.save()


# ══════════════════════════════════════════════════════════════════════════════
# apply_changes - persiste mudanças da fila
# ══════════════════════════════════════════════════════════════════════════════

def apply_changes(board_obj: Board, queue: ChangeQueue, config: dict = None):
    """Consome toda a fila e aplica mudanças. Para no primeiro PenaltyException.

    Erros não classificados como rate limit nunca interrompem o processamento
    dos demais itens (evita head-of-line blocking, ver incidente #97):
    - "definitivo": item sai da fila já na primeira falha.
    - "transitorio": item volta ao fim da fila com attempts incrementado, até
      esgotar o limite configurado (sync.max_attempts); aí também sai da fila.
    Cada item é tentado no máximo uma vez por chamada de apply_changes.
    """
    config = config or {}
    max_attempts = resolve_max_attempts(config)
    tried_targets = []

    while True:
        item = queue.getNext()
        if not item:
            return
        if any(item.same_target(t) for t in tried_targets):
            # Já tentamos este alvo nesta chamada (requeue ao fim da fila) —
            # não reprocessar no mesmo ciclo, evita loop infinito.
            return
        tried_targets.append(item)

        board_id = item.board
        try:
            if item.event == SyncEvent.CREATE_UP.value:
                _apply_create_up(board_id, item, board_obj, queue)
            elif item.event == SyncEvent.CREATE_DOWN.value:
                _apply_create_down(board_id, item, board_obj, queue, config)
            elif item.event == SyncEvent.CHANGE_UP.value:
                _apply_change_up(board_id, item, board_obj, queue, config)
            elif item.event == SyncEvent.CHANGE_DOWN.value:
                _apply_change_down(board_id, item, board_obj, queue, config)
            elif item.event == SyncEvent.DELETE_UP.value:
                _apply_delete_up(board_id, item, board_obj, queue)
            elif item.event == SyncEvent.DELETE_DOWN.value:
                _apply_delete_down(board_id, item, board_obj, queue)

            queue.remove(item.uuid)
        except PenaltyException:
            log.warning("Sync", f"[{board_id}] Penalty - abandonando apply_changes")
            return
        except Exception as exc:
            category = classify_error(exc)
            if category == "definitivo":
                log.warning(
                    "Sync",
                    f"[{board_id}] #{item.id} erro definitivo em {item.event} - "
                    f"removendo da fila: {exc}",
                    board_id=board_id, issue_id=item.id, event=item.event,
                    reason=sanitize_reason(str(exc)), attempts=item.attempts,
                    category=category, next_step=_NEXT_STEP[category],
                )
                _isolate_in_dead_letter(board_id, item, category, exc)
                queue.remove(item.uuid)
                continue

            # transitorio
            item.attempts += 1
            if item.attempts >= max_attempts:
                category = "transitorio_esgotado"
                log.warning(
                    "Sync",
                    f"[{board_id}] #{item.id} esgotou tentativas ({item.attempts}) "
                    f"em {item.event} - removendo da fila: {exc}",
                    board_id=board_id, issue_id=item.id, event=item.event,
                    reason=sanitize_reason(str(exc)), attempts=item.attempts,
                    category=category, next_step=_NEXT_STEP[category],
                )
                _isolate_in_dead_letter(board_id, item, category, exc)
                queue.remove(item.uuid)
                continue

            log.warning(
                "Sync",
                f"[{board_id}] #{item.id} erro transitório em {item.event} "
                f"(tentativa {item.attempts}/{max_attempts}) - reenfileirando: {exc}",
                issue_id=item.id, event=item.event, attempts=item.attempts,
            )
            queue.requeue(item)


def _isolate_in_dead_letter(board_id: str, item: ChangeItem, category: str,
                            exc: Exception) -> None:
    """Persiste o item isolado em dead-letter antes de removê-lo da fila ativa.

    add() é idempotente por alvo (board+id/identifier+event): se o processo
    for interrompido entre esta chamada e o queue.remove() subsequente, o
    pior caso é uma nova tentativa do mesmo item sobrescrever esta entrada
    com dados atualizados — seguro, sem duplicar nem perder o registro.
    """
    entry = DeadLetterEntry(
        uuid=item.uuid,
        board=board_id,
        id=item.id,
        identifier=item.identifier,
        event=item.event,
        category=category,
        reason=sanitize_reason(str(exc)),
        attempts=item.attempts,
        isolated_at=ChangeItem.now(),
        next_step=_NEXT_STEP[category],
    )
    DeadLetterQueue().add(entry)


def _apply_create_up(board_id: str, item: ChangeItem, board_obj: Board, queue: ChangeQueue = None):
    """Cria issue no board a partir do arquivo local."""
    snap = Snapshot(board_id).load()
    issue_data = next((i for i in snap.issues if i.get("body_path") == item.identifier), None)
    if not issue_data:
        return

    body_path = Path(issue_data["body_path"])
    if not body_path.exists():
        return

    content = body_path.read_text(encoding="utf-8")
    # Primeira linha = título
    lines = content.strip().splitlines()
    title = lines[0].lstrip("# ").strip() if lines else Path(item.identifier).stem
    raw_body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    # Separar comandos do body real
    body, cmds = split_body(raw_body)
    column = issue_data["column"]

    created = board_obj.create_issue(board_id, title, body, column)
    log.info("Sync", f"[{board_id}] create-up '{title}' -> #{created.id}",
             issue_id=created.id, column=column)
    cmds = sanitize_relations(created.id, cmds)

    # Aplicar comandos (labels, relações, etc). Create parte de estado vazio:
    # known=_empty_state() garante que os deltas 'added' reflitam tudo que foi
    # declarado, e que os setters não façam GET redundante (nada existe ainda).
    deltas = {}
    if not cmds.is_empty():
        deltas = board_obj.apply_commands(board_id, created.id, cmds, known=_empty_state())

    # Verificar addcomment
    slug = body_path.stem.removesuffix("-body")
    ac_file = body_path.parent / f"{slug}-addcomment.md"
    if ac_file.exists() and ac_file.read_text(encoding="utf-8").strip():
        board_obj.add_comment(board_id, created.id, ac_file.read_text(encoding="utf-8").strip())
        ac_file.write_text("", encoding="utf-8")

    # Renomear arquivos com o id atribuído
    new_slug = _slugify(title)
    new_files = _issue_files(board_id, column, created.id, new_slug)
    new_files["body"].parent.mkdir(parents=True, exist_ok=True)
    body_path.rename(new_files["body"])

    # History
    comments = board_obj.list_comments(board_id, created.id)
    history_content = _format_history(comments)
    new_files["history"].write_text(history_content, encoding="utf-8")

    # Addcomment limpo
    new_files["addcomment"].write_text("", encoding="utf-8")

    # Remover arquivos antigos (history/addcomment do path anterior)
    old_history = body_path.parent / f"{slug}-history.md"
    old_ac = body_path.parent / f"{slug}-addcomment.md"
    if old_history.exists():
        old_history.unlink()
    if old_ac.exists():
        old_ac.unlink()

    # Atualizar snapshot
    issue_data["id"] = created.id
    issue_data["body_path"] = str(new_files["body"])
    issue_data["body_mtime"] = str(new_files["body"].stat().st_mtime)
    issue_data["updated_at"] = created.updated_at
    issue_data["status"] = "ok"
    # Gravar o estado desejado (declarado) como conhecido no snapshot ANTES de
    # disparar o gatilho, para que o alvo, ao reciprocar, encontre este vínculo.
    _write_state_from_cmds(issue_data, cmds)
    snap.save()

    # Gatilho de par recíproco sobre as relações recém-criadas.
    if queue is not None and deltas:
        _trigger_reciprocal_downs(created.id, deltas, queue)


def _apply_create_down(board_id: str, item: ChangeItem, board_obj: Board, queue: ChangeQueue = None,
                       config: dict = None):
    """Cria arquivos locais a partir do issue no board."""
    snap = Snapshot(board_id).load()
    issue = board_obj.get_issue(board_id, item.id, fullsync=item.fullsync)
    # Coluna já vem na chamada única de get_issue (projectItems/Status).
    column = issue.column or ""

    # Guard de propagação automática: o GitHub Projects V2 adiciona a sub-issue
    # aos projects do pai sem definir Status. Só descarta o evento (e remove o
    # item do board) quando há PROVA de propagação — a issue já registrada em
    # outro board configurado com coluna conhecida. `parent` isolado é apenas
    # contexto de log: sub-issue nova e legítima deste board também pode chegar
    # sem coluna, e removê-la seria perda de dado.
    if not column:
        proof = _propagation_proof(board_id, item.id, config)
        if proof:
            other_board, other_col = proof
            log.info("Sync", f"[{board_id}] #{item.id} create-down descartado - "
                     f"propagação automática (issue em '{other_board}/{other_col}')")
            # A remoção precisa CONCLUIR antes de o evento ser descartado: falha
            # propaga e a fila (at-least-once) reprocessa no ciclo seguinte.
            board_obj.remove_from_board(board_id, item.id)
            return
        if issue.parent:
            log.info("Sync", f"[{board_id}] #{item.id} create-down com parent #{issue.parent} "
                     f"e coluna vazia, sem prova de propagação - criando local")

    if not column:
        column = list(snap.board.keys())[0] if snap.board else ""

    slug = _slugify(issue.title)
    files = _issue_files(board_id, column, item.id, slug)
    files["body"].parent.mkdir(parents=True, exist_ok=True)

    # Body
    files["body"].write_text(_compose_down_body(issue), encoding="utf-8")

    # History
    comments = board_obj.list_comments(board_id, item.id)
    files["history"].write_text(_format_history(comments), encoding="utf-8")

    # Addcomment vazio
    files["addcomment"].write_text("", encoding="utf-8")

    log.info("Sync", f"[{board_id}] create-down #{item.id} '{issue.title}' -> {column}",
             issue_id=item.id, column=column)

    # Atualizar snapshot
    new_data = {
        "id": item.id,
        "column": column,
        "body_path": str(files["body"]),
        "body_mtime": str(files["body"].stat().st_mtime),
        "updated_at": issue.updated_at,
        "status": "ok",
    }
    _write_state_from_issue(new_data, issue, fullsync=item.fullsync)
    snap.issues.append(new_data)
    snap.save()

    # Gatilho de par recíproco: alvos de deps recém-descobertas no board.
    # Só em fullsync (única situação em que blocked_by/blocks vêm preenchidos).
    if queue is not None and item.fullsync:
        deltas = _deps_deltas_from_snapshot(issue, _empty_state())
        _trigger_reciprocal_downs(item.id, deltas, queue)


def _apply_change_up(board_id: str, item: ChangeItem, board_obj: Board,
                     queue: ChangeQueue = None, config: dict = None):
    """Propaga mudança local para o board."""
    snap = Snapshot(board_id).load()
    issue_data = snap.issue(item.id)
    if not issue_data:
        return

    body_path = _find_issue_files(board_id, item.id)
    if not body_path:
        return

    content = body_path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    title = lines[0].lstrip("# ").strip() if lines else ""
    raw_body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    # Separar comandos do body real
    body, cmds = split_body(raw_body)
    cmds = sanitize_relations(item.id, cmds)

    # Remédio 1: se a issue está sendo arquivada (comando /archive no body OU
    # coluna de destino com on_in:[archive]), remove TODOS os bloqueios antes
    # de arquivar. A remoção produz deltas 'removed' em blocked_by/blocks e o
    # _trigger_reciprocal_downs (ao final desta função) enfileira um fullsync
    # (change-down) para cada issue reciprocamente vinculada — desbloqueando-as.
    dest_col = _col_from_path(body_path, board_id)
    if (cmds.archive or _column_archives(board_id, dest_col, config)) \
            and (cmds.blocked_by or cmds.blocks):
        log.info("Sync", f"[{board_id}] #{item.id} arquivando: removendo bloqueios "
                 f"(blocked_by={cmds.blocked_by}, blocks={cmds.blocks})",
                 issue_id=item.id)
        cmds.blocked_by = []
        cmds.blocks = []

    # Atualizar body/title no board (body limpo, sem o bloco @---)
    try:
        board_obj.update_issue(board_id, item.id, title=title, body=body)
    except Exception as e:
        if "Could not resolve to an issue or pull request" in str(e):
            log.warning("Sync", f"[{board_id}] #{item.id} não existe no GitHub — "
                        "removendo do snapshot (issue fantasma)")
            snap.issues = [i for i in snap.issues if str(i.get("id")) != str(item.id)]
            snap.save()
            return
        raise

    # Aplicar comandos como estado autoritativo, comparando contra o estado
    # conhecido (snapshot): só chama o setter do atributo que realmente mudou,
    # e passa o estado conhecido ao setter para evitar GETs redundantes.
    known = _known_state(issue_data)
    deltas = board_obj.apply_commands(board_id, item.id, cmds, known=known)

    # Verificar mudança de coluna
    current_col = _col_from_path(body_path, board_id)
    old_col = issue_data.get("column")
    if current_col != old_col:
        board_obj.move_issue(board_id, item.id, current_col, from_column=old_col)
        _fire_column_events(board_id, item.id, board_obj, config, old_col, current_col)
        issue_data["column"] = current_col

    # Verificar addcomment
    slug = body_path.stem.removesuffix("-body")
    ac_file = body_path.parent / f"{slug}-addcomment.md"
    if ac_file.exists():
        comment = ac_file.read_text(encoding="utf-8").strip()
        if comment:
            board_obj.add_comment(board_id, item.id, comment)
            ac_file.write_text("", encoding="utf-8")

    # Atualizar history
    comments = board_obj.list_comments(board_id, item.id)
    history_file = body_path.parent / f"{slug}-history.md"
    history_file.write_text(_format_history(comments), encoding="utf-8")

    col_label = f"{old_col} -> {current_col}" if old_col and old_col != current_col else f"-> {current_col}"
    log.info("Sync", f"[{board_id}] change-up #{item.id} {col_label}",
             issue_id=item.id, column=current_col, from_column=old_col)

    # Atualizar snapshot
    issue_data["body_path"] = str(body_path)
    issue_data["body_mtime"] = str(body_path.stat().st_mtime)
    issue_data["status"] = "ok"
    # Gravar o estado desejado como conhecido ANTES de disparar o gatilho.
    _write_state_from_cmds(issue_data, cmds)
    snap.save()

    # Gatilho de par recíproco sobre relações adicionadas/removidas.
    if queue is not None and deltas:
        _trigger_reciprocal_downs(item.id, deltas, queue)


def _apply_change_down(board_id: str, item: ChangeItem, board_obj: Board,
                       queue: ChangeQueue = None, config: dict = None):
    """Propaga mudança do board para local."""
    snap = Snapshot(board_id).load()
    issue_data = snap.issue(item.id)
    if not issue_data:
        return

    old_col = issue_data.get("column")
    issue = board_obj.get_issue(board_id, item.id, fullsync=item.fullsync)
    # Sem fullsync, deps (blocked_by/blocks) não vêm na chamada única. Para não
    # apagar o bloco de deps ao reescrever o body, preserva o que o snapshot já
    # conhece sobre as dependências desta issue.
    if not item.fullsync:
        issue.blocked_by = list(issue_data.get("blocked_by") or [])
        issue.blocks = list(issue_data.get("blocks") or [])
    # Coluna já vem na chamada única de get_issue (projectItems/Status).
    remote_col = issue.column or ""

    # Coluna vazia no board (propagação automática que apagou o Status): reaplicar
    # no BOARD a coluna conhecida do snapshot. Feito antes de qualquer decisão
    # sobre arquivos locais porque a reconciliação é do board — se dependesse de
    # movimentação local, o caso comum (arquivo já na coluna certa) deixaria o
    # item remoto sem Status e `detect_board_changes` acusaria a mesma divergência
    # em todo full sync, indefinidamente.
    if not remote_col and old_col:
        log.info("Sync", f"[{board_id}] #{item.id} - coluna vazia no board, "
                 f"reaplicando '{old_col}' do snapshot")
        try:
            board_obj.move_issue(board_id, item.id, old_col)
        except PenaltyException:
            raise
        except Exception as e:
            # Reconciliação oportunista: não descarta evento nem interrompe o down.
            log.warning("Sync", f"[{board_id}] #{item.id} - falha ao reaplicar coluna "
                        f"'{old_col}' no board: {e}")
        remote_col = old_col

    body_path = _find_issue_files(board_id, item.id)
    if not body_path:
        # Arquivos não existem, criar
        slug = _slugify(issue.title)
        col = remote_col or issue_data.get("column", "")
        files = _issue_files(board_id, col, item.id, slug)
        files["body"].parent.mkdir(parents=True, exist_ok=True)
        body_path = files["body"]

    # Atualizar body
    body_path.write_text(_compose_down_body(issue), encoding="utf-8")

    # Mover se coluna mudou
    current_col = _col_from_path(body_path, board_id)

    if remote_col and remote_col != current_col:
        slug = body_path.stem.removesuffix("-body")
        new_files = _issue_files(board_id, remote_col, item.id, slug.split("-", 1)[1] if "-" in slug else slug)
        new_files["body"].parent.mkdir(parents=True, exist_ok=True)
        body_path.rename(new_files["body"])
        # Mover history e addcomment
        old_hist = body_path.parent / f"{slug}-history.md"
        old_ac = body_path.parent / f"{slug}-addcomment.md"
        if old_hist.exists():
            old_hist.rename(new_files["history"])
        if old_ac.exists():
            old_ac.rename(new_files["addcomment"])
        body_path = new_files["body"]
        current_col = remote_col
        # Sem move_issue aqui: no down quem manda é o board. Escrever de volta a
        # coluna que ele já tem custa 2 chamadas GraphQL por movimentação manual.
        # A única escrita legítima no board é a reaplicação de coluna perdida,
        # tratada acima.

    # Atualizar history
    slug = body_path.stem.removesuffix("-body")
    comments = board_obj.list_comments(board_id, item.id)
    history_file = body_path.parent / f"{slug}-history.md"
    history_file.write_text(_format_history(comments), encoding="utf-8")

    # Limpar addcomment
    ac_file = body_path.parent / f"{slug}-addcomment.md"
    ac_file.write_text("", encoding="utf-8")

    log.trace("Sync", f"[{board_id}] change-down #{item.id} -> {current_col}",
             issue_id=item.id, column=current_col)

    # Gatilho de par recíproco: calcula deltas de deps ANTES de sobrescrever o
    # estado conhecido no snapshot. Só em fullsync (deps preenchidas).
    deps_deltas = None
    if queue is not None and item.fullsync:
        deps_deltas = _deps_deltas_from_snapshot(issue, issue_data)

    # Atualizar snapshot
    issue_data["column"] = current_col
    issue_data["body_path"] = str(body_path)
    issue_data["body_mtime"] = str(body_path.stat().st_mtime)
    issue_data["updated_at"] = issue.updated_at
    issue_data["status"] = "ok"
    # Gravar o estado real do board como conhecido ANTES de disparar o gatilho.
    _write_state_from_issue(issue_data, issue, fullsync=item.fullsync)
    snap.save()

    if deps_deltas:
        _trigger_reciprocal_downs(item.id, deps_deltas, queue)

    # Movimentação manual no board: aplicar on_out/on_in da mudança de coluna.
    # O snapshot NÃO é alterado aqui; reescrevemos o arquivo APÓS o body_mtime
    # já registrado, de modo que o próximo sync detecte a modificação local e
    # dispare um change-up — garantindo que status/labels subam para o board.
    if config and old_col and current_col and old_col != current_col:
        _bake_column_events(board_id, body_path, config, old_col, current_col)


def _bake_column_events(board_id: str, body_path: Path, config: dict,
                        old_col: str, new_col: str) -> None:
    """Reescreve o arquivo body aplicando on_out/on_in no bloco de comandos.

    Não toca no snapshot. Como o body_mtime já foi salvo, esta reescrita deixa
    o arquivo "mais novo" que o snapshot, fazendo o próximo sync tratá-lo como
    modificação local (change-up).
    """
    columns = (config.get("boards", {}).get(board_id, {}) or {}).get("columns", {})
    out_events = (columns.get(old_col, {}) or {}).get("on_out") or []
    in_events = (columns.get(new_col, {}) or {}).get("on_in") or []
    if not out_events and not in_events:
        return

    content = body_path.read_text(encoding="utf-8")
    first_nl = content.find("\n")
    header = content[:first_nl] if first_nl != -1 else content
    rest = content[first_nl + 1:] if first_nl != -1 else ""

    body, cmds = split_body(rest)
    apply_events_to_commands(cmds, out_events)
    apply_events_to_commands(cmds, in_events)

    new_content = f"{header}\n{compose_body(body, cmds)}\n"
    body_path.write_text(new_content, encoding="utf-8")
    log.info("Sync", f"[{board_id}] eventos de coluna aplicados localmente "
             f"({old_col} → {new_col}); change-up pendente",
             out_events=out_events, in_events=in_events)


def _apply_delete_up(board_id: str, item: ChangeItem, board_obj: Board,
                     queue: ChangeQueue = None):
    """Fecha issue no board (arquivo local já foi removido)."""
    # Captura as relações da issue ANTES de removê-la do snapshot (Remédio 2).
    deleted_data = Snapshot(board_id).load().issue(item.id)

    try:
        board_obj.close_issue(board_id, item.id)
    except Exception as e:
        if "Could not resolve to an issue or pull request" in str(e):
            log.warning("Sync", f"[{board_id}] #{item.id} não existe no GitHub — "
                        "removendo do snapshot (issue fantasma)")
            snap = Snapshot(board_id).load()
            snap.issues = [i for i in snap.issues if str(i.get("id")) != str(item.id)]
            snap.save()
            return
        raise

    # Remédio 2: remover bloqueios recíprocos nas issues apontadas + fullsync.
    _cleanup_block_relations_on_delete(item.id, deleted_data, board_obj, queue)

    snap = Snapshot(board_id).load()
    snap.issues = [i for i in snap.issues if str(i.get("id")) != str(item.id)]
    snap.save()

    log.info("Sync", f"[{board_id}] delete-up #{item.id} - issue fechada",
             issue_id=item.id)


def _apply_delete_down(board_id: str, item: ChangeItem, board_obj: Board,
                       queue: ChangeQueue = None):
    """Remove arquivos locais (issue foi removida do board)."""
    snap = Snapshot(board_id).load()
    # Captura as relações da issue ANTES de removê-la do snapshot (Remédio 2).
    deleted_data = snap.issue(item.id)

    # Remover arquivos
    body_path = _find_issue_files(board_id, item.id)
    if body_path:
        slug = body_path.stem.removesuffix("-body")
        for suffix in ("-body.md", "-history.md", "-addcomment.md"):
            f = body_path.parent / f"{slug}{suffix}"
            if f.exists():
                f.unlink()

    # Remédio 2: remover bloqueios recíprocos nas issues apontadas + fullsync.
    _cleanup_block_relations_on_delete(item.id, deleted_data, board_obj, queue)

    snap = Snapshot(board_id).load()
    snap.issues = [i for i in snap.issues if str(i.get("id")) != str(item.id)]
    snap.save()

    log.info("Sync", f"[{board_id}] delete-down #{item.id} - arquivos removidos",
             issue_id=item.id)


def migrate_agent_level_labels(board_id: str, queue: ChangeQueue) -> int:
    """Migra issues abertas com /agent_level no @--- para label agent-level-<nível>.

    Para cada issue rastreada no snapshot que:
    - não possui nenhuma label agent-level-* no estado conhecido, E
    - possui /agent_level no bloco @--- do arquivo body local

    … enfileira um change-up para que o ciclo de sync-up grave a label correta
    no board via all_labels(). A reescrita do body não é necessária: o
    serialize_commands já emite /agent_level, e o all_labels() já emite a label
    correspondente — basta que o item suba.

    Retorna o número de issues migradas (enfileiradas).
    """
    snap = Snapshot(board_id).load()
    migrated = 0

    for issue_data in snap.issues:
        issue_id = str(issue_data.get("id") or "")
        if not issue_id:
            continue
        if issue_data.get("status", "ok") != "ok":
            continue

        # Verifica se o estado conhecido já tem label agent-level-*
        known_labels = issue_data.get("labels") or []
        has_level_label = any(
            str(lbl).startswith(AGENT_LEVEL_PREFIX) for lbl in known_labels
        )
        if has_level_label:
            continue  # já migrada ou nível já presente no board

        # Verifica se o body local possui /agent_level no bloco @---
        body_path = Path(issue_data.get("body_path", ""))
        if not body_path.exists():
            continue

        content = body_path.read_text(encoding="utf-8")
        # Remove a primeira linha (título)
        raw_body = content.split("\n", 1)[1] if "\n" in content else ""
        _, cmds = split_body(raw_body)

        if not cmds.agent_level:
            continue  # sem /agent_level no body — nada a migrar

        # Enfileira change-up para que o sync-up grave a label no board
        if queue.add(ChangeItem.of(SyncEvent.CHANGE_UP, id=issue_id, board=board_id)):
            issue_data["status"] = SyncEvent.CHANGE_UP.value
            log.info("Migrate", f"[{board_id}] #{issue_id} agent_level='{cmds.agent_level}' "
                     f"→ enfileirado change-up para gravar label agent-level-{cmds.agent_level}")
            migrated += 1

    if migrated:
        snap.save()

    return migrated


def _format_history(comments: list[dict]) -> str:
    """Formata comentários para o arquivo history."""
    if not comments:
        return ""
    parts = []
    for c in comments:
        author = c.get("author", "?")
        body = c.get("body", "")
        date = c.get("date", "")
        if date:
            date = date.replace("T", " ").replace("Z", "")[:19]
        parts.append(f"## {author} - {date}\n\n{body}\n---")
    return "\n\n".join(parts) + "\n"
