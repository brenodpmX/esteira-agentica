"""Reconciliação de participação, eventos estruturados e retentativa (#310).

Reúne os efeitos (I/O) que a classificação pura (`participation.py`) não faz:

- Eventos estruturados no log diário (`logs/<data>.json`), com campos mínimos e
  SEM segredos (RF-13 / RNF-09).
- Os dois gatilhos de reconciliação:
  - imediata, logo após a criação de um vínculo pai/filho (RF-07);
  - tardia, na descoberta remota de uma presença nova (RF-08).
- Estado de retentativa SEM bloqueio de fila, persistido fora do snapshot em
  `.pipe/participationPending.json` (estado interno protegido): presenças
  `unresolved` ou com falha transitória recebem `next_attempt_at` e são
  reavaliadas em ciclos posteriores, sem consumir tentativa que leve a descarte
  (RF-09 / RNF-01).
- Detecção de remoção externa de uma presença pendente (RF-13 / CT-22).

Nenhum evento carrega token, body de issue ou conteúdo de arquivo protegido.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.core.log import log
from src.core.participation import (
    Classification,
    ParticipationQueryError,
    PROPAGATED,
    UNRESOLVED,
    classify_participation,
)

# Estado interno protegido (nunca exposto ao agente — ver PROTECTED_PATHS).
PENDING_FILE = Path(".pipe/participationPending.json")

# Intervalo padrão de adiamento (segundos) para presenças não resolvidas.
DEFAULT_RETRY_INTERVAL_SECONDS = 300


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def retry_interval_seconds(config: dict) -> int:
    """Intervalo de adiamento (segundos) para presenças não resolvidas.

    Reusa `boards.rerun_cooldown` como intervalo de espera configurado quando
    presente e > 0; senão o default seguro. Mantém a entrega sem introduzir uma
    nova chave de configuração além do escopo.
    """
    boards = (config or {}).get("boards", {}) or {}
    cooldown = boards.get("rerun_cooldown") or 0
    if isinstance(cooldown, int) and not isinstance(cooldown, bool) and cooldown > 0:
        return cooldown
    return DEFAULT_RETRY_INTERVAL_SECONDS


# ── Eventos estruturados ───────────────────────────────────────────────────────

def event_classified(issue, board, classification: Classification) -> None:
    """Emite `participation_classified` (coluna/arquivamento como evidência)."""
    log.info(
        "Participation",
        f"[{board}] #{issue} classificada: {classification.intent}",
        event="participation_classified",
        issue=str(issue), board=board,
        classification=classification.intent,
        evidence=classification.evidence,
        timestamp=_iso(_now()),
    )


def event_reconciled(issue, origin_board, propagated_board, detected_at) -> None:
    """Emite `participation_reconciled` após remoção bem-sucedida."""
    log.info(
        "Participation",
        f"[{propagated_board}] #{issue} presença propagada reconciliada "
        f"(origem '{origin_board}')",
        event="participation_reconciled",
        issue=str(issue), origin_board=origin_board,
        propagated_board=propagated_board,
        detected_at=detected_at, reconciled_at=_iso(_now()),
    )


def event_reconcile_failed(issue, board, attempt, next_attempt_at, error_kind) -> None:
    """Emite `participation_reconcile_failed` (falha de consulta ou remoção)."""
    log.warning(
        "Participation",
        f"[{board}] #{issue} falha na reconciliação (tentativa {attempt}, "
        f"tipo {error_kind})",
        event="participation_reconcile_failed",
        issue=str(issue), board=board, attempt=attempt,
        next_attempt_at=next_attempt_at, error_kind=error_kind,
    )


def event_removed_externally(issue, board, first_seen_at, observed_removed_at) -> None:
    """Emite `participation_removed_externally` (sem inferir autoria)."""
    log.info(
        "Participation",
        f"[{board}] #{issue} presença pendente desapareceu sem reconciliação "
        f"registrada (remoção externa)",
        event="participation_removed_externally",
        issue=str(issue), board=board,
        first_seen_at=first_seen_at, observed_removed_at=observed_removed_at,
    )


def event_cross_board_link_blocked(parent, child, parent_board, child_board,
                                   config_version) -> None:
    """Emite `cross_board_link_blocked` (contingência recusou vínculo)."""
    log.warning(
        "Participation",
        f"vínculo cross-board recusado (contingência): #{child} ({child_board}) "
        f"-> #{parent} ({parent_board})",
        event="cross_board_link_blocked",
        parent=str(parent), child=str(child),
        parent_board=parent_board, child_board=child_board,
        config_version=config_version,
    )


# ── Estado de pendências (retentativa sem bloqueio) ────────────────────────────

def _load_pending() -> dict:
    if not PENDING_FILE.exists():
        return {}
    try:
        return json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_pending(data: dict) -> None:
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=PENDING_FILE.parent,
                                    prefix=".participationPending-", suffix=".tmp")
    tmp_path = PENDING_FILE.parent / Path(tmp_name).name
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, PENDING_FILE)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def _pending_key(board: str, issue) -> str:
    return f"{board}#{issue}"


def defer_pending(board: str, issue, classification: Classification,
                  interval_seconds: int, *, error_kind: str | None = None) -> dict:
    """Registra/atualiza uma pendência com `next_attempt_at` futuro.

    NÃO incrementa um contador que leve a descarte: `attempts` apenas conta
    reavaliações para evidência (RF-09 — sem consumir tentativa que descarta).
    Preserva `first_seen_at` da primeira observação (para remoção externa).
    """
    data = _load_pending()
    key = _pending_key(board, issue)
    now = _now()
    entry = data.get(key) or {}
    entry["board"] = board
    entry["issue"] = str(issue)
    entry["classification"] = classification.intent
    entry["attempts"] = int(entry.get("attempts", 0)) + 1
    entry.setdefault("first_seen_at", _iso(now))
    entry["next_attempt_at"] = _iso(now + timedelta(seconds=interval_seconds))
    if error_kind:
        entry["error_kind"] = error_kind
    data[key] = entry
    _save_pending(data)
    return entry


def clear_pending(board: str, issue) -> None:
    """Remove a pendência (reconciliada com sucesso ou virou intenção confirmada)."""
    data = _load_pending()
    key = _pending_key(board, issue)
    if key in data:
        del data[key]
        _save_pending(data)


def pending_entry(board: str, issue) -> dict | None:
    return _load_pending().get(_pending_key(board, issue))


def is_due(entry: dict, *, now: datetime | None = None) -> bool:
    """True se a pendência venceu o prazo de adiamento (elegível a reavaliação)."""
    now = now or _now()
    nxt = entry.get("next_attempt_at")
    if not nxt:
        return True
    try:
        due = datetime.strptime(nxt, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return True
    return now >= due


# ── Gatilho 1: reconciliação imediata pós-vínculo (RF-07) ──────────────────────

def reconcile_after_link(board, child_id: str, parent_board: str, config: dict,
                         *, labels=None) -> None:
    """Reconcilia as presenças propagadas da filha logo após criar o vínculo.

    Consulta `list_participations(child_id)` e, para cada presença classificada
    como `propagated`, remove-a do quadro indevido ANTES de a operação de
    vínculo ser considerada concluída (RF-07). A relação pai/filho NUNCA é
    tocada (RN-03): este caminho só remove ITENS de project.

    Falha de consulta ou de remoção propaga como erro TIPADO (RN-09): a relação
    pai/filho já criada é preservada e nada é desfeito. Nesse caso emite
    `participation_reconcile_failed`.
    """
    detected_at = _iso(_now())
    try:
        participations = board.list_participations(child_id)
    except ParticipationQueryError:
        event_reconcile_failed(child_id, parent_board, attempt=1,
                               next_attempt_at=None, error_kind="query_failed")
        raise

    labels = labels or []
    for part in participations:
        board_id = (part.board_id or "").strip()
        if not board_id:
            continue  # project fora da config: não é alvo deste gatilho
        classification = classify_participation(
            child_id, board_id, labels, participations, config,
            column=part.column, archived=part.archived,
            has_cross_board_parent=True,
        )
        event_classified(child_id, board_id, classification)
        if classification.should_remove:
            try:
                board.remove_from_board(board_id, child_id)
            except ParticipationQueryError:
                raise
            except Exception as exc:
                event_reconcile_failed(child_id, board_id, attempt=1,
                                       next_attempt_at=None,
                                       error_kind=type(exc).__name__)
                raise
            event_reconciled(child_id, origin_board=_proof_board(classification),
                             propagated_board=board_id, detected_at=detected_at)


def _proof_board(classification: Classification) -> str:
    return (classification.evidence or {}).get("proof_board", "")


# ── Gatilho 2: reconciliação tardia na descoberta remota (RF-08) ───────────────

def reconcile_remote_presence(board, issue_id: str, board_id: str, config: dict,
                              *, labels=None, column: str = "",
                              archived: bool = False,
                              known_participations=None,
                              has_cross_board_parent: bool = False) -> Classification:
    """Classifica e reconcilia uma presença nova detectada na descoberta remota.

    Retorna a classificação. Em `propagated`, remove a presença (o chamador só
    deve consumir o evento APÓS a remoção concluir — a exceção propaga e a fila
    at-least-once reprocessa). Em `unresolved`, registra adiamento sem bloquear
    a fila. Em `origin`/`authorized`, limpa qualquer pendência (segue o fluxo
    normal de criação, a cargo do chamador).
    """
    labels = labels or []
    known = known_participations if known_participations is not None else []
    detected_at = _iso(_now())
    interval = retry_interval_seconds(config)

    try:
        if known_participations is None:
            known = board.list_participations(issue_id)
    except ParticipationQueryError:
        classification = Classification(UNRESOLVED, {"reason": "query_failed"})
        event_classified(issue_id, board_id, classification)
        entry = defer_pending(board_id, issue_id, classification, interval,
                              error_kind="query_failed")
        event_reconcile_failed(issue_id, board_id, attempt=entry["attempts"],
                               next_attempt_at=entry["next_attempt_at"],
                               error_kind="query_failed")
        return classification

    classification = classify_participation(
        issue_id, board_id, labels, known, config,
        column=column, archived=archived,
        has_cross_board_parent=has_cross_board_parent,
    )
    event_classified(issue_id, board_id, classification)

    if classification.intent == PROPAGATED:
        try:
            board.remove_from_board(board_id, issue_id)
        except Exception as exc:
            entry = defer_pending(board_id, issue_id, classification, interval,
                                  error_kind=type(exc).__name__)
            event_reconcile_failed(issue_id, board_id, attempt=entry["attempts"],
                                   next_attempt_at=entry["next_attempt_at"],
                                   error_kind=type(exc).__name__)
            raise
        clear_pending(board_id, issue_id)
        event_reconciled(issue_id, origin_board=_proof_board(classification),
                         propagated_board=board_id, detected_at=detected_at)
    elif classification.intent == UNRESOLVED:
        defer_pending(board_id, issue_id, classification, interval)
    else:
        clear_pending(board_id, issue_id)

    return classification


# ── Contingência: bloqueio de vínculo cross-board (RF-12 / RN-08) ──────────────

class CrossBoardLinkBlocked(Exception):
    """Levantada quando a contingência recusa um novo vínculo cross-board."""

    def __init__(self, parent, child, parent_board, child_board):
        self.parent = str(parent)
        self.child = str(child)
        self.parent_board = parent_board
        self.child_board = child_board
        super().__init__(
            f"vínculo cross-board recusado (contingência): #{child} "
            f"({child_board}) -> #{parent} ({parent_board})"
        )


def cross_board_links_suspended() -> bool:
    """True se a contingência está suspensa, relendo o `pipe.yml` do disco.

    A leitura é feita a cada chamada (sem cache em memória), por data de
    modificação do arquivo — ativar/desativar tem efeito sem reinício (RNF-06).
    """
    from src.core.config import read_cross_board_links_from_disk, SAFETY_SUSPENDED
    return read_cross_board_links_from_disk() == SAFETY_SUSPENDED


def guard_cross_board_link(parent, child, parent_board: str, child_board: str,
                           *, config_version=None) -> bool:
    """Avalia a contingência para um NOVO vínculo pai/filho (RF-12 / CT-18).

    Retorna True se o vínculo é permitido; levanta `CrossBoardLinkBlocked` (e
    emite `cross_board_link_blocked`) se o vínculo é entre quadros DISTINTOS e a
    contingência está suspensa. Vínculo dentro do MESMO quadro é sempre
    permitido; vínculos preexistentes nunca são afetados (RN-08).
    """
    same_board = (parent_board or "") == (child_board or "")
    if same_board:
        return True
    if not cross_board_links_suspended():
        return True
    event_cross_board_link_blocked(parent, child, parent_board, child_board,
                                   config_version)
    raise CrossBoardLinkBlocked(parent, child, parent_board, child_board)


# ── Remoção externa (RF-13 / CT-22) ────────────────────────────────────────────

def detect_external_removal(board, config: dict) -> None:
    """Observa pendências que desapareceram do quadro sem reconciliação própria.

    Para cada pendência registrada, consulta as presenças atuais da issue; se a
    presença no quadro pendente não aparece mais e não há registro de que a
    reconciliação automática a removeu, emite `participation_removed_externally`
    (sem inferir autoria) e limpa a pendência. Falha de consulta é ignorada
    (mantém a pendência para o próximo ciclo) — não infere remoção.
    """
    data = _load_pending()
    if not data:
        return
    now_iso = _iso(_now())
    changed = False
    for key, entry in list(data.items()):
        board_id = entry.get("board")
        issue_id = entry.get("issue")
        if not board_id or not issue_id:
            continue
        try:
            participations = board.list_participations(issue_id)
        except ParticipationQueryError:
            continue  # não infere remoção em falha de consulta
        still_present = any(
            (p.board_id or "").strip() == board_id for p in participations
        )
        if not still_present:
            event_removed_externally(
                issue_id, board_id,
                first_seen_at=entry.get("first_seen_at"),
                observed_removed_at=now_iso,
            )
            del data[key]
            changed = True
    if changed:
        _save_pending(data)
