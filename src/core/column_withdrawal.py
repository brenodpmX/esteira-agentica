"""Núcleo de decisão — retirada segura de colunas de board (issue #305).

Esta é uma proteção para MUDANÇA ESTRUTURAL de board: retirar uma coluna da
configuração nunca pode deixar issues sem classificação. NÃO é uma regra geral
de movimentação de trabalho entre colunas (RN-09).

A política é: detectar colunas publicadas no board remoto ausentes da
configuração desejada (candidatas à retirada), classificar cada origem
(vazia/ocupada) por leitura remota no momento da avaliação, validar o destino
quando ocupada, drenar todas as issues ao destino relendo até confirmar vazio e,
só então, contrair (remover a opção). Falha/interrupção preserva o estado
parcial (válido e convergente) e a retomada deriva o trabalho restante do estado
remoto, sem journal paralelo.

A política pertence AO NÚCLEO DE DECISÃO — não à camada de acesso ao provedor
(ver "Riscos" da issue). O provedor expõe apenas as primitivas
(`remote_columns`, `list_issues`, `move_issue`, `prepare_structure`,
`contract_column`), todas sujeitas ao throttle/penalidade existentes.
"""

from dataclasses import dataclass

from src.core.board import Board, PenaltyException
from src.core.log import log

EVENT = "column_migration_attempt"

# Resultados da tentativa.
RESULT_COMPLETED = "completed"
RESULT_BLOCKED = "blocked"
RESULT_INTERRUPTED = "interrupted"

# Motivos padronizados de bloqueio.
REASON_DESTINO_AUSENTE = "destino_ausente"
REASON_DESTINO_INEXISTENTE = "destino_inexistente"
REASON_DESTINO_MESMO_BOARD_INVALIDO = "destino_mesmo_board_invalido"
REASON_DESTINO_E_ORIGEM = "destino_e_origem"
REASON_DESTINO_TAMBEM_RETIRADO = "destino_tambem_retirado"

# Motivo padronizado de interrupção.
REASON_SEM_PROGRESSO = "sem_progresso"

# Guarda defensiva contra laço infinito na drenagem (defesa em profundidade;
# a condição de parada real é "ausência de progresso entre duas leituras").
_MAX_DRAIN_PASSES = 1000


@dataclass
class WithdrawalAttempt:
    """Resultado estruturado de uma tentativa de retirada de uma origem."""
    board: str
    source: str
    destination: str = ""
    initial_count: int = 0
    moved_count: int = 0
    remaining_count: int = 0
    result: str = RESULT_INTERRUPTED
    reason: str = ""


def _desired_columns(config: dict, board_id: str) -> list[str]:
    board_cfg = config.get("boards", {}).get(board_id, {}) or {}
    return list((board_cfg.get("columns", {}) or {}).keys())


def _migrations(config: dict, board_id: str) -> dict:
    board_cfg = config.get("boards", {}).get(board_id, {}) or {}
    raw = board_cfg.get("column-migrations") or {}
    # Normaliza (strip) chaves e valores — a forma já foi validada em config.py.
    return {str(k).strip(): str(v).strip() for k, v in raw.items()}


def _board_ids(config: dict) -> list[str]:
    return [
        bid for bid, cfg in config.get("boards", {}).items()
        if bid != "platform" and isinstance(cfg, dict)
    ]


def _all_other_boards_columns(config: dict, board_id: str) -> set[str]:
    cols: set[str] = set()
    for bid in _board_ids(config):
        if bid == board_id:
            continue
        cols.update(_desired_columns(config, bid))
    return cols


def _count_in(issues, source: str) -> int:
    return sum(1 for i in issues if (i.column or "") == source)


def _emit(attempt: WithdrawalAttempt) -> None:
    """Emite exatamente um registro de evidência por tentativa.

    `completed` em nível informativo; `blocked`/`interrupted` em nível de aviso.
    A mensagem textual de `blocked`/`interrupted` é auto-contida (board, origem e
    motivo), sem exigir correlação entre registros. Nenhum conteúdo sensível
    (corpo de issue, credencial, estado protegido) entra na evidência — apenas os
    campos de contagem/resultado/identificação.
    """
    extra = dict(
        event=EVENT,
        board=attempt.board,
        source=attempt.source,
        destination=attempt.destination,
        initial_count=attempt.initial_count,
        moved_count=attempt.moved_count,
        remaining_count=attempt.remaining_count,
        result=attempt.result,
        reason=attempt.reason,
    )
    if attempt.result == RESULT_COMPLETED:
        msg = (
            f"{EVENT} board={attempt.board} source={attempt.source} "
            f"result=completed initial_count={attempt.initial_count} "
            f"moved_count={attempt.moved_count} remaining_count={attempt.remaining_count}"
        )
        log.info("ColumnWithdrawal", msg, **extra)
    else:
        msg = (
            f"{EVENT} board={attempt.board} source={attempt.source} "
            f"destination={attempt.destination or '-'} result={attempt.result} "
            f"reason={attempt.reason or '-'} initial_count={attempt.initial_count} "
            f"moved_count={attempt.moved_count} remaining_count={attempt.remaining_count}"
        )
        log.warning("ColumnWithdrawal", msg, **extra)


def _validate_destination(
    config: dict, board_id: str, source: str, destination: str | None,
    withdrawn: set[str],
) -> str | None:
    """Valida (semântica) o destino de uma origem ocupada.

    Retorna o motivo de bloqueio (str) quando inválido, ou None quando válido.
    """
    if not destination:
        return REASON_DESTINO_AUSENTE
    if destination == source:
        return REASON_DESTINO_E_ORIGEM
    if destination in withdrawn:
        return REASON_DESTINO_TAMBEM_RETIRADO
    if destination in _desired_columns(config, board_id):
        return None  # destino válido no mesmo board
    if destination in _all_other_boards_columns(config, board_id):
        return REASON_DESTINO_MESMO_BOARD_INVALIDO
    return REASON_DESTINO_INEXISTENTE


def _reconcile_source(
    board: Board, config: dict, board_id: str, source: str, withdrawn: set[str],
    remaining_columns: list[str],
) -> WithdrawalAttempt:
    """Reconcilia UMA origem retirada. Pode levantar PenaltyException (propaga).

    `remaining_columns` é a lista de colunas que devem permanecer publicadas após
    uma eventual contração desta origem (todas as remotas exceto esta origem).
    """
    migrations = _migrations(config, board_id)
    destination = migrations.get(source)

    # ── Classificação da origem por leitura remota imediatamente anterior ──────
    issues = board.list_issues(board_id)
    initial_count = _count_in(issues, source)

    attempt = WithdrawalAttempt(
        board=board_id, source=source,
        destination=destination or "",
        initial_count=initial_count,
        remaining_count=initial_count,
    )

    # ── Coluna vazia: retira direto, sem exigir destino (RN-01) ────────────────
    if initial_count == 0:
        board.contract_column(board_id, remaining_columns)
        attempt.result = RESULT_COMPLETED
        attempt.moved_count = 0
        attempt.remaining_count = 0
        # Coluna vazia não exige destino; destination fica vazio.
        attempt.destination = ""
        _emit(attempt)
        return attempt

    # ── Coluna ocupada: exige destino válido (RF-04/RF-05) ─────────────────────
    reason = _validate_destination(config, board_id, source, destination, withdrawn)
    if reason is not None:
        attempt.result = RESULT_BLOCKED
        attempt.reason = reason
        attempt.destination = destination or ""
        attempt.moved_count = 0
        attempt.remaining_count = initial_count
        _emit(attempt)
        return attempt

    # ── Drenagem: mover todas as issues da origem ao destino, relendo até vazio.
    moved_ids: set[str] = set()
    current = issues
    passes = 0
    while True:
        passes += 1
        pending = [i for i in current if (i.column or "") == source]
        if not pending:
            break  # origem vazia confirmada pela última leitura

        count_before = len(pending)
        try:
            for issue in pending:
                board.move_issue(board_id, issue.id, destination, from_column=source)
                moved_ids.add(str(issue.id))
        except PenaltyException:
            # Penalidade: não contrai origem parcialmente drenada; registra
            # interrupção e PROPAGA para o laço de reconciliação existente
            # (que trata com time.sleep). Sem retentativa paralela própria.
            remaining = _count_in(board.list_issues(board_id), source)
            attempt.result = RESULT_INTERRUPTED
            attempt.moved_count = len(moved_ids)
            attempt.remaining_count = remaining
            _emit(attempt)
            raise
        except Exception:
            # Erro de transporte/indisponibilidade: preserva estado parcial
            # (issues já movidas no destino, restantes na origem; origem NÃO
            # contraída) e permite retomada. Isolamento: não propaga, segue
            # para as demais origens (RF-15).
            remaining = _count_in(board.list_issues(board_id), source)
            attempt.result = RESULT_INTERRUPTED
            attempt.moved_count = len(moved_ids)
            attempt.remaining_count = remaining
            _emit(attempt)
            return attempt

        # Releitura após o lote (confirma drenagem / detecta issue que chegou).
        current = board.list_issues(board_id)
        count_after = _count_in(current, source)

        # Ausência de progresso: a passagem não reduziu a contagem (> 0).
        # Encerra sem contrair e sem laço infinito (RF-13).
        if count_after >= count_before:
            attempt.result = RESULT_INTERRUPTED
            attempt.reason = REASON_SEM_PROGRESSO
            attempt.moved_count = len(moved_ids)
            attempt.remaining_count = count_after
            _emit(attempt)
            return attempt

        if passes >= _MAX_DRAIN_PASSES:  # defesa extra contra laço infinito
            attempt.result = RESULT_INTERRUPTED
            attempt.reason = REASON_SEM_PROGRESSO
            attempt.moved_count = len(moved_ids)
            attempt.remaining_count = count_after
            _emit(attempt)
            return attempt

    # ── Confirmação de vazio + contração (RF-10/RF-11) ─────────────────────────
    board.contract_column(board_id, remaining_columns)
    attempt.result = RESULT_COMPLETED
    attempt.moved_count = len(moved_ids)
    attempt.remaining_count = 0
    _emit(attempt)
    return attempt


def reconcile_board_withdrawals(board: Board, config: dict, board_id: str) -> list[WithdrawalAttempt]:
    """Reconcilia as colunas retiradas de UM board.

    Detecta as opções publicadas no board remoto ausentes da configuração
    desejada (candidatas à retirada), e trata cada origem de forma independente
    (bloqueio/interrupção de uma não impede as demais — RF-15). Retorna a lista
    de tentativas (uma por origem retirada).

    PenaltyException propaga (deve ser tratada pelo laço de reconciliação com
    throttle/sleep); erros de transporte por origem NÃO propagam (isolamento).
    """
    published = board.remote_columns(board_id)
    desired = _desired_columns(config, board_id)
    withdrawn_order = [c for c in published if c not in desired]
    withdrawn = set(withdrawn_order)

    attempts: list[WithdrawalAttempt] = []
    if not withdrawn:
        return attempts

    # Estado remoto efetivo das opções: começa de `published` e remove conforme
    # cada contração conclui (preserva as demais, inclusive origens retidas).
    effective = list(published)

    for source in withdrawn_order:
        if source not in effective:
            continue  # já removida (não deveria ocorrer, mas defensivo)
        remaining_columns = [c for c in effective if c != source]
        attempt = _reconcile_source(
            board, config, board_id, source, withdrawn, remaining_columns,
        )
        attempts.append(attempt)
        if attempt.result == RESULT_COMPLETED:
            effective = remaining_columns  # a origem foi contraída
    return attempts


def reconcile_withdrawals(board: Board, config: dict) -> list[WithdrawalAttempt]:
    """Reconcilia as colunas retiradas de TODOS os boards configurados.

    Isolamento entre boards: a reconciliação de um board não impede a de outro
    (RF-15). Retorna todas as tentativas de todos os boards.
    """
    all_attempts: list[WithdrawalAttempt] = []
    for board_id in _board_ids(config):
        all_attempts.extend(reconcile_board_withdrawals(board, config, board_id))
    return all_attempts


def reconcile_structure(board: Board, config: dict) -> list[WithdrawalAttempt]:
    """Reconciliação estrutural completa de retirada segura de coluna.

    1. Preparação NÃO destrutiva: cria boards/campo Status/colunas ausentes,
       preservando todas as opções remotas existentes (inclusive em retirada).
    2. Reconciliação das colunas retiradas (validar/drenar/confirmar/contrair),
       por origem e por board, de forma isolada.

    Retorna a lista de tentativas (vazia quando nada foi retirado).
    """
    board.prepare_boards(config)
    return reconcile_withdrawals(board, config)
