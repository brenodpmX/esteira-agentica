"""Migração de snapshots legados sem `participation_intent` (RN-B01/ADR-001).

Função pura em I/O de rede: lê e escreve apenas os snapshots locais
(`.pipe/boards/<board_id>/snapshot.json`). Não importa adapter nem
`Board`/`BoardPort` — só depende de `Snapshot`.

Roda uma única vez por issue, no full sync de startup, antes do primeiro
`keep_task`. Ver ADR-001, seção Decisão ("Duplicidades legadas sem label
permanecem bloqueadas").
"""

from src.core.log import log
from src.core.snapshot import Snapshot


def migrate_legacy_participation_intent(config: dict) -> None:
    """Migra snapshots legados sem participation_intent (RN-B01/ADR-001).

    Roda uma única vez por issue: NUNCA sobrescreve um participation_intent
    já presente (preenchido por qualquer camada). Para cada issue sem o
    campo, em cada board configurado (config["boards"], exceto "platform"):
      - conta em quantos boards configurados essa issue aparece no
        snapshot local (por id);
      - aparece em exatamente 1 board -> participation_intent = "origin"
        nesse único snapshot;
      - aparece em 2+ boards -> participation_intent = "unresolved" em
        TODOS os snapshots onde aparece (nenhuma escolha automática de
        qual board é a origem legítima - ver ADR-001, seção Decisão,
        "Duplicidades legadas sem label permanecem bloqueadas").
    Não faz chamada de rede: lê e escreve apenas os snapshots locais
    (.pipe/boards/<board_id>/snapshot.json) já sincronizados por
    board_full_sync antes desta chamada.
    """
    board_ids = [
        bid
        for bid, cfg in config.get("boards", {}).items()
        if bid != "platform" and isinstance(cfg, dict)
    ]

    # Carrega os snapshots de todos os boards configurados uma única vez.
    snapshots = {bid: Snapshot(bid).load() for bid in board_ids}

    # Mapa issue_id -> set de board_ids configurados onde ela aparece.
    # "Aparece" = existe uma entrada com aquele id em snap.issues (qualquer
    # coluna/status; não filtra).
    presence: dict[str, set[str]] = {}
    for bid, snap in snapshots.items():
        for issue in snap.issues:
            issue_id = issue.get("id")
            if issue_id is None:
                continue
            presence.setdefault(str(issue_id), set()).add(bid)

    changed_boards: set[str] = set()

    for bid, snap in snapshots.items():
        for issue in snap.issues:
            issue_id = issue.get("id")
            if issue_id is None:
                continue
            # Só processa entradas ainda não migradas. Distingue campo ausente
            # de campo presente com valor None/"": se já existe, não toca.
            if "participation_intent" in issue:
                continue

            # 1 board configurado no total -> origin; 2+ -> unresolved.
            board_count = len(presence.get(str(issue_id), set()))
            issue["participation_intent"] = (
                "origin" if board_count <= 1 else "unresolved"
            )
            changed_boards.add(bid)

    # Salva apenas os snapshots efetivamente alterados.
    for bid in changed_boards:
        snapshots[bid].save()

    if changed_boards:
        log.info(
            "Migration",
            f"participation_intent migrado em {len(changed_boards)} snapshot(s)",
        )
