"""Classificação pura de intenção de participação de issues entre quadros (#310).

Uma "participação" é a presença de uma issue em um quadro (project), materializada
como item de project — com ou sem coluna (Status). A plataforma pode criar
participações automaticamente como efeito colateral de uma relação pai/filho
entre issues de quadros distintos; essas presenças não representam uma decisão
de quem opera a esteira e nunca devem virar trabalho executável no quadro errado.

Este módulo oferece uma função PURA e sem I/O de rede (`classify_participation`)
que classifica cada par (issue, quadro) em exatamente um de quatro estados:

- ``origin``     — primeira presença em quadro configurado, sem outra presença
                   confirmada em outro quadro; é a criação intencional.
- ``authorized`` — a issue carrega o rótulo reservado ``board-intent-<quadro>``
                   que nomeia exatamente o quadro avaliado (participação
                   multi-quadro explicitamente autorizada).
- ``propagated`` — a issue já está confirmada, com coluna conhecida, em OUTRO
                   quadro configurado, e não há autorização para o quadro atual;
                   é propagação automática — deve ser removida.
- ``unresolved`` — evidência ambígua, falha transitória de consulta, ou
                   duplicidade legada sem autorização; mantém pendente e adia,
                   nunca vira issue nova nem é removida por omissão.

Determinismo (RN-07 / RNF-05): o resultado depende SOMENTE do estado de entrada
(issue, quadro, rótulos, presenças conhecidas, configuração), nunca da ordem de
avaliação nem de estado mutável compartilhado entre chamadas. A coluna (Status)
preenchida ou vazia NÃO influencia a classificação (RN-06).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.core.log import log

# Estados de intenção (strings estáveis — persistidas no snapshot e em logs).
ORIGIN = "origin"
AUTHORIZED = "authorized"
PROPAGATED = "propagated"
UNRESOLVED = "unresolved"

INTENT_STATES = frozenset({ORIGIN, AUTHORIZED, PROPAGATED, UNRESOLVED})

# Estados que confirmam intenção (podem executar / passar no gate final).
CONFIRMED_INTENTS = frozenset({ORIGIN, AUTHORIZED})

# Prefixo do rótulo reservado de autorização multi-quadro.
BOARD_INTENT_PREFIX = "board-intent-"


class ParticipationQueryError(Exception):
    """Falha TIPADA ao consultar as participações de uma issue (#310 / RN-09).

    A consulta de presenças NUNCA retorna lista vazia silenciosa em caso de
    falha: a reconciliação precisa distinguir "nenhuma presença" de "não foi
    possível consultar". Uma falha transitória (transporte, rate limit da
    consulta, resposta malformada) é propagada como esta exceção, que a
    reconciliação traduz em classificação ``unresolved`` com adiamento.
    """
    pass


@dataclass
class Participation:
    """Presença de uma issue em um quadro, materializada como item de project.

    Campos (contrato de porta exigido pela demanda):
    - ``item_id``: identificador do item de project.
    - ``board_id``: quadro configurado resolvido, ou "" quando o project não
      corresponde a nenhum quadro configurado.
    - ``project_id``: identificador do project na plataforma.
    - ``column``: nome do Status (coluna), ou "" quando vazio.
    - ``archived``: indicador de arquivamento do item.
    """

    item_id: str
    board_id: str
    project_id: str
    column: str = ""
    archived: bool = False


@dataclass
class Classification:
    """Resultado da classificação pura de uma participação.

    - ``intent``: um de ORIGIN/AUTHORIZED/PROPAGATED/UNRESOLVED.
    - ``evidence``: dados mínimos e auditáveis que sustentam a decisão —
      apenas coluna avaliada e indicador de arquivamento (e o motivo),
      NUNCA body ou lista completa de rótulos (RNF-09).
    """

    intent: str
    evidence: dict = field(default_factory=dict)

    @property
    def confirmed(self) -> bool:
        """True se a intenção é confirmada (origem/autorizada)."""
        return self.intent in CONFIRMED_INTENTS

    @property
    def should_remove(self) -> bool:
        """True se a participação deve ser removida do quadro (propagada)."""
        return self.intent == PROPAGATED


def _configured_boards(config: dict) -> set[str]:
    """Ids de quadros configurados no pipe.yml (ignora 'platform')."""
    boards = (config or {}).get("boards", {}) or {}
    return {
        bid for bid, cfg in boards.items()
        if bid != "platform" and isinstance(cfg, dict)
    }


def authorized_boards(labels, config: dict) -> set[str]:
    """Quadros autorizados por rótulo ``board-intent-<quadro>`` válido.

    Um rótulo autoriza somente o quadro cujo id corresponde EXATAMENTE ao
    sufixo. Rótulo que nomeia um quadro inexistente é ignorado para autorização
    e gera um aviso (RN-04 / CT-07) — nunca levanta exceção. Não há curinga.
    """
    configured = _configured_boards(config)
    result: set[str] = set()
    for raw in labels or []:
        label = str(raw)
        if not label.startswith(BOARD_INTENT_PREFIX):
            continue
        suffix = label[len(BOARD_INTENT_PREFIX):]
        if not suffix:
            continue
        if suffix in configured:
            result.add(suffix)
        else:
            log.warning(
                "Participation",
                f"rótulo de autorização ignorado: '{label}' nomeia quadro "
                f"inexistente '{suffix}'",
                event="participation_authorization_label_invalid",
                label=label, board=suffix,
            )
    return result


def classify_participation(
    issue_id: str,
    board_id: str,
    labels,
    known_participations,
    config: dict,
    *,
    column: str = "",
    archived: bool = False,
    query_failed: bool = False,
    has_cross_board_parent: bool = False,
) -> Classification:
    """Classifica a intenção de uma participação (issue, quadro) — PURA, sem rede.

    Parâmetros:
    - ``issue_id``: number da issue (apenas para evidência/log, não altera lógica).
    - ``board_id``: quadro avaliado (deve ser um quadro configurado).
    - ``labels``: rótulos da issue (lista de str); usados só para autorização.
    - ``known_participations``: iterável de ``Participation`` com as presenças
      CONFIRMADAS/conhecidas da issue em quadros configurados (fonte: snapshots
      locais). Uma presença em OUTRO quadro configurado, com coluna conhecida,
      é a única prova de propagação aceita (RN-02).
    - ``config``: configuração carregada (para resolver quadros e autorização).
    - ``column`` / ``archived``: estado do item avaliado (evidência; coluna não
      influencia o resultado — RN-06).
    - ``query_failed``: True quando a consulta de presenças falhou de forma
      transitória — força ``unresolved`` (RN-09 / CT-05).
    - ``has_cross_board_parent``: True quando a issue tem uma relação pai/filho
      que a liga a outro quadro. Por si só NÃO decide nada: a propagação da
      plataforma se materializa como uma SEGUNDA presença, nunca como uma só
      (RN-02). Com presença única o resultado é sempre ``origin`` (não há cópia
      a remover nem impasse resolúvel); o sinal só diferencia o motivo em
      ``evidence`` (``sole_presence_cross_board_parent`` vs ``first_presence``).
      A adjudicação de propagação/duplicidade depende de haver presença em
      OUTRO quadro configurado, não deste sinal.

    Determinismo: nenhuma dependência de ordem, relógio ou estado mutável
    compartilhado. A ordem de precedência das regras é fixa.
    """
    column = (column or "").strip()
    evidence = {"column": column, "archived": bool(archived)}

    # 0) Falha transitória de consulta ⇒ não resolvida (sem remoção, adia).
    if query_failed:
        evidence["reason"] = "query_failed"
        return Classification(UNRESOLVED, evidence)

    # 1) Autorização explícita por rótulo válido tem precedência sobre tudo
    #    (participação multi-quadro intencional, com ou sem coluna — RN-04).
    if board_id in authorized_boards(labels, config):
        evidence["reason"] = "authorized_label"
        return Classification(AUTHORIZED, evidence)

    # 2) Prova de propagação: a issue já está confirmada, com coluna conhecida,
    #    em OUTRO quadro configurado. Coluna vazia ou quadro não configurado NÃO
    #    prova (RN-02). `parent` isolado tampouco prova (não é consultado aqui).
    configured = _configured_boards(config)
    boards_cfg = (config or {}).get("boards", {}) or {}
    proof_board = None
    for part in known_participations or []:
        other = (part.board_id or "").strip()
        if not other or other == board_id:
            continue
        if other not in configured:
            continue  # snapshot de quadro não configurado não prova (RN-02)
        other_col = (part.column or "").strip()
        known_cols = (boards_cfg.get(other, {}) or {}).get("columns", {}) or {}
        if other_col and other_col in known_cols:
            proof_board = other
            break

    if proof_board is not None:
        evidence["reason"] = "propagation_proof"
        evidence["proof_board"] = proof_board
        return Classification(PROPAGATED, evidence)

    # 3) Sem autorização e sem prova de propagação. Distinguir:
    #    - presença conhecida em OUTRO quadro configurado SEM coluna conhecida
    #      ⇒ duplicidade ambígua: há duas cópias e falta a coluna que elege a
    #      origem; adia (RN-02).
    #    - presença ÚNICA (nenhuma outra em quadro configurado) ⇒ origem, mesmo
    #      com pai cross-board (ver abaixo).
    has_other_presence = any(
        (part.board_id or "").strip() not in ("", board_id)
        and (part.board_id or "").strip() in configured
        for part in (known_participations or [])
    )
    if has_other_presence:
        evidence["reason"] = "ambiguous_duplicate"
        return Classification(UNRESOLVED, evidence)

    # Presença única: não há segunda cópia para remover nem impasse que o tempo
    # resolva (nenhuma prova futura chega para uma presença só, nenhum rótulo
    # virá). A propagação da plataforma SEMPRE se materializa como uma SEGUNDA
    # presença; uma relação pai/filho cross-board isolada é o estado normal de
    # uma hierarquia (epic->story->task), não prova de propagação (RN-02).
    # Classificar `unresolved` aqui seria deadlock permanente: a presença nunca
    # entra no snapshot, e cada ciclo a redescobre e readia — loop eterno ao
    # reconstruir um snapshot vazio (pod morto). Logo: origem.
    evidence["reason"] = (
        "sole_presence_cross_board_parent" if has_cross_board_parent
        else "first_presence"
    )
    return Classification(ORIGIN, evidence)


# ── Gate final na seleção de tarefas (RF-10 / RNF-04) ──────────────────────────
#
# A barreira final NÃO faz chamadas de rede: lê apenas `participation_intent` do
# snapshot local. Só deixa passar intenção confirmada (origin/authorized); as
# demais (propagated/unresolved/ausente) são ignoradas para seleção e avanço, e
# geram um evento `dispatch_blocked_unconfirmed_intent` DEDUPLICADO por
# (board, coluna, issue) — reemitido só ao mudar de coluna ou reiniciar o
# processo (cache em memória, por processo).

_dispatch_blocked_seen: set[tuple[str, str, str]] = set()


def reset_dispatch_dedup() -> None:
    """Zera a deduplicação de despacho bloqueado (simula reinício do processo)."""
    _dispatch_blocked_seen.clear()


def gate_allows(issue: dict) -> bool:
    """True se a issue tem intenção confirmada (origin/authorized) no snapshot.

    Função PURA: inspeciona somente o campo `participation_intent` do dict da
    issue (vindo do snapshot). Nunca toca a rede (RNF-04).
    """
    return issue.get("participation_intent") in CONFIRMED_INTENTS


def gate_block_event(board_id: str, col_id: str, issue: dict) -> None:
    """Emite `dispatch_blocked_unconfirmed_intent` deduplicado por (board,col,issue).

    Reemitido só ao mudar de coluna (chave diferente) ou reiniciar o processo
    (cache em memória — ver `reset_dispatch_dedup`).
    """
    issue_id = str(issue.get("id"))
    key = (board_id, col_id, issue_id)
    if key in _dispatch_blocked_seen:
        return
    _dispatch_blocked_seen.add(key)
    classification = issue.get("participation_intent") or "absent"
    log.warning(
        "Participation",
        f"[{board_id}] #{issue_id} despacho bloqueado em '{col_id}': "
        f"intenção não confirmada ({classification})",
        event="dispatch_blocked_unconfirmed_intent",
        issue=issue_id, board=board_id, column=col_id,
        classification=classification,
    )


def gate_keep(board_id: str, col_id: str, issue: dict) -> bool:
    """Decisão do gate para uma issue candidata (RF-10).

    Retorna True se a issue pode seguir para seleção/avanço (intenção
    confirmada). Caso contrário, emite o evento deduplicado e retorna False.
    """
    if gate_allows(issue):
        return True
    gate_block_event(board_id, col_id, issue)
    return False


def backfill_intent_if_absent(board_id: str, issue: dict, config: dict) -> None:
    """Backfill tardio da intenção de uma issue legada ainda sem o campo.

    A migração de legados (RF-11) roda no startup e garante o campo antes da
    primeira seleção. Este backfill é a mesma regra aplicada defensivamente no
    momento da seleção, para que uma issue legada presente em UM único quadro
    configurado seja reconhecida como `origin` sem depender exclusivamente da
    migração ter rodado. NÃO reclassifica issues que já têm o campo (incluindo
    `propagated`/`unresolved`, que seguem bloqueadas pelo gate), nem escolhe
    origem arbitrária para duplicidade — mutação apenas no dict em memória.
    """
    if "participation_intent" in issue:
        return
    issue_id = str(issue.get("id") or "")
    if not issue_id:
        return
    # Conta em quantos quadros configurados a issue aparece (snapshots locais).
    from src.core.snapshot import Snapshot
    boards = sorted(_configured_boards(config))
    seen_in = 0
    for bid in boards:
        snap = Snapshot(bid).load()
        if snap.issue(issue_id) is not None:
            seen_in += 1
    # Único quadro ⇒ origem (criação original legítima). Duplicidade ⇒ não
    # resolvida (sem escolher origem), permanecendo bloqueada pelo gate.
    issue["participation_intent"] = ORIGIN if seen_in <= 1 else UNRESOLVED


# ── Migração de legados no startup (RF-11 / CT-11/12/13) ───────────────────────

def migrate_legacy_intents(config: dict) -> int:
    """Atribui `participation_intent` a issues legadas, nos snapshots locais.

    Regra (idempotente, nunca sobrescreve campo já presente):
    - issue presente em UM único quadro configurado, sem o campo ⇒ `origin`;
    - issue duplicada em DOIS+ quadros configurados, sem autorização e sem o
      campo ⇒ `unresolved` em TODAS as entradas (sem escolher origem);
    - entrada que JÁ tem `participation_intent` nunca é alterada;
    - rodar duas vezes não muda nada (idempotência).

    Roda no startup, antes da primeira seleção de tarefas. Retorna o número de
    entradas migradas (para evidência de log). Importado localmente para evitar
    dependência circular com `snapshot`.
    """
    from src.core.snapshot import Snapshot

    boards = sorted(_configured_boards(config))
    # Mapeia issue_id -> lista de (board_id, entrada do snapshot).
    occurrences: dict[str, list[tuple[str, dict]]] = {}
    snapshots: dict[str, Snapshot] = {}
    for board_id in boards:
        snap = Snapshot(board_id).load()
        snapshots[board_id] = snap
        for issue in snap.issues:
            issue_id = str(issue.get("id") or "")
            if not issue_id:
                continue
            occurrences.setdefault(issue_id, []).append((board_id, issue))

    migrated = 0
    dirty: set[str] = set()
    for issue_id, entries in occurrences.items():
        # Issues presentes em mais de um quadro configurado = duplicidade.
        duplicated = len({b for b, _ in entries}) > 1
        for board_id, issue in entries:
            if "participation_intent" in issue:
                continue  # já preenchido: nunca sobrescreve
            if duplicated:
                # Autorização individual por quadro poderia tornar `authorized`,
                # mas a regra de migração de legados é conservadora: duplicidade
                # sem o campo vira `unresolved` em ambas (sem escolher origem).
                labels = issue.get("labels") or []
                if board_id in authorized_boards(labels, config):
                    issue["participation_intent"] = AUTHORIZED
                else:
                    issue["participation_intent"] = UNRESOLVED
            else:
                issue["participation_intent"] = ORIGIN
            migrated += 1
            dirty.add(board_id)

    for board_id in dirty:
        snapshots[board_id].save()

    if migrated:
        log.info(
            "Participation",
            f"migração de legados: {migrated} entrada(s) receberam intenção",
            event="participation_legacy_migrated", migrated=migrated,
        )
    return migrated


# ── Evidência de execução no startup (RF-14 / CT-21 / RN-10) ───────────────────

# Arquivo gravado no build com o commit em execução (fonte quando não há .git).
COMMIT_FILE = Path(".pipe_commit")
ENVIRONMENT_ENV = "PIPE_ENVIRONMENT"


def _resolve_commit() -> str | None:
    """Resolve o commit em execução: `git rev-parse HEAD` ou arquivo de build.

    Retorna None quando não é possível determinar (campo ausente — sinalizado
    explicitamente, sem inferir sucesso). Não levanta.
    """
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd="repo/main",
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except OSError:
        pass
    try:
        if COMMIT_FILE.exists():
            value = COMMIT_FILE.read_text(encoding="utf-8").strip()
            if value:
                return value
    except OSError:
        pass
    return None


def rollout_evidence(version: str, *, commit: str | None = None,
                     environment: str | None = None) -> dict:
    """Registra `rollout_evidence` no startup (RF-14).

    Campos: `version`, `commit`, `environment`, `started_at`. Qualquer campo
    ausente é registrado EXPLICITAMENTE como `null` (não omitido), sem inferir
    sucesso (RN-10). O commit, quando não informado, é resolvido do checkout ou
    de um arquivo de build; o ambiente, quando não informado, de `PIPE_ENVIRONMENT`.
    """
    if commit is None:
        commit = _resolve_commit()
    if environment is None:
        environment = os.environ.get(ENVIRONMENT_ENV) or None

    evidence = {
        "version": version or None,
        "commit": commit or None,
        "environment": environment or None,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    missing = [k for k, v in evidence.items() if v is None]
    log.info(
        "Participation",
        f"evidência de execução: v{evidence['version']} "
        f"commit={evidence['commit']} env={evidence['environment']}"
        + (f" (campos ausentes: {', '.join(missing)})" if missing else ""),
        event="rollout_evidence", **evidence,
    )
    return evidence
