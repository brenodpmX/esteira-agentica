"""Board core - gerencia boards via port."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from src.core.commands import _sanitize_relations_with_discards
from src.core.config import load_current_config, resolve_cross_board_parent_links
from src.core.log import log


def _is_cross_board_link_blocked(board_id: str, target_issue_id: str,
                                  resolve_board_fn) -> bool:
    """True se a nova relação (este board + target_issue_id) deve ser
    bloqueada pela contingência de suspensão.

    Bloqueia apenas quando: safety.cross_board_parent_links resolve para
    "suspended" E o board do target_issue_id (via resolve_board_fn) é
    conhecido E é diferente de board_id. Relação para issue não rastreada
    (resolve_board_fn retorna None) não é bloqueada aqui — sem prova de
    "outro board", não há decisão segura a tomar nesta camada (mesmo
    princípio de "sem prova, sem bloqueio automático" de RN-B02; mas note
    que RN-B02 trata reconciliação de propagação, não esta contingência —
    são guards independentes).
    """
    if resolve_board_fn is None:
        return False
    config = load_current_config()
    if resolve_cross_board_parent_links(config) != "suspended":
        return False
    target_board = resolve_board_fn(target_issue_id)
    if target_board is None:
        return False
    return target_board != board_id


class PenaltyException(Exception):
    """Rate limit atingido - aguardar antes de tentar novamente."""
    def __init__(self, wait_seconds: int):
        self.wait_seconds = wait_seconds
        super().__init__(f"Rate limit - aguardar {wait_seconds}s")


class BoardAccessError(Exception):
    """Token sem permissão/acesso suficiente para operar o board/repositório.

    Levantada na verificação de startup: a esteira NÃO deve iniciar quando o
    token não consegue operar o repositório configurado.
    """
    pass


class SyncEvent(str, Enum):
    """Evento de sincronismo registrado na fila de mudanças.

    Sufixo '-up' = origem local (precisa subir para o board).
    Sufixo '-down' = origem no board (precisa descer para o local).
    """
    CREATE_UP = "create-up"      # criado localmente
    CREATE_DOWN = "create-down"  # criado no board
    CHANGE_UP = "change-up"      # modificado localmente
    CHANGE_DOWN = "change-down"  # modificado no board
    DELETE_UP = "delete-up"      # deletado localmente
    DELETE_DOWN = "delete-down"  # deletado no board


@dataclass
class ChangeItem:
    """Item da fila de sincronismo (.pipe/changeQueue.json)."""
    timestamp: str       # horário em que foi adicionado na fila (ISO 8601 UTC)
    event: str           # SyncEvent
    id: str = None       # id da issue no board (None quando ainda não existe)
    identifier: str = None  # body_path para issues criadas localmente (sem id)
    board: str = None       # board_id ao qual a issue pertence
    uuid: str = None        # id único na fila (atribuído por add/addAll)
    fullsync: bool = False  # se True, reconcilia todas as propriedades + deps
    attempts: int = 0       # tentativas de processamento já feitas (erro transitório)
    next_attempt_at: str = None  # ISO 8601 UTC (formato de now()); quando
    # preenchido, o item não deve ser processado antes desse instante. Usado
    # por pendências unresolved (ver #242 e a política de classificação de
    # intenção) para aguardar prova sem contar como tentativa esgotada
    # (sync.max_attempts). É independente de attempts: attempts mede
    # tentativas que FALHARAM; next_attempt_at mede uma pendência AGUARDANDO
    # prova, que não necessariamente falhou (ex.: consulta bem-sucedida com
    # evidência ambígua).

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def of(cls, event, id: str = None, identifier: str = None,
           board: str = None, fullsync: bool = False) -> "ChangeItem":
        """Cria um ChangeItem com timestamp atual."""
        return cls(
            timestamp=cls.now(),
            event=event.value if isinstance(event, SyncEvent) else event,
            id=id,
            identifier=identifier,
            board=board,
            fullsync=fullsync,
        )

    def same_target(self, other: "ChangeItem") -> bool:
        """True se representa o mesmo alvo de sincronismo (para deduplicação).

        Considera duplicado quando event, id, identifier e board são iguais.
        """
        return (
            self.event == other.event
            and self.id == other.id
            and self.identifier == other.identifier
            and self.board == other.board
        )


@dataclass
class Issue:
    id: str
    title: str
    body: str
    column: str
    labels: list[str] = None
    updated_at: str = None
    # Relações e estado (preenchidos pelo adapter quando disponível)
    parent: str = None
    children: list[str] = None
    blocked_by: list[str] = None
    blocks: list[str] = None
    state: str = None  # 'open' | 'closed'
    archived: bool = False


@dataclass
class Participation:
    """Uma participação (item de Project V2) de uma issue em um board."""
    board_id: str | None   # board configurado resolvido; None se não resolvido
    item_id: str           # id do ProjectV2Item (necessário para deleteProjectV2Item)
    project_id: str        # id do Project V2 (GraphQL), mesmo quando board_id é None
    status: str | None     # nome da coluna (Status) remota; None/"" quando vazio
    archived: bool = False


class BoardPort(ABC):
    """Port para adapters de board (GitHub, ClickUp, etc)."""

    @abstractmethod
    def connect(self, config: dict) -> None:
        """Conecta ao serviço."""
        pass

    def check_access(self, config: dict) -> None:
        """Verifica permissões/acesso antes de iniciar a esteira.

        Implementação padrão: sem verificação (no-op). Adapters devem
        sobrescrever e levantar BoardAccessError quando o token não puder
        operar o repositório/board configurado.
        """
        return None

    @abstractmethod
    def sync_boards(self, boards: list[dict]) -> None:
        """Sincroniza estrutura de boards e colunas."""
        pass

    @abstractmethod
    def list_issues(self, board_id: str) -> list[Issue]:
        """Lista todas as issues de um board."""
        pass

    @abstractmethod
    def list_issues_since(self, board_id: str, since: str) -> list[Issue]:
        """Lista issues modificadas desde a data informada (ISO 8601)."""
        pass

    @abstractmethod
    def get_issue(self, board_id: str, issue_id: str, fullsync: bool = False) -> Issue:
        """Busca uma issue específica.

        Quando fullsync=True, também traz dependencies (blocked_by/blocks),
        que exigem chamadas REST extras não disponíveis no GraphQL.
        """
        pass

    @abstractmethod
    def create_issue(self, board_id: str, title: str, body: str, column: str) -> Issue:
        """Cria uma issue no board. Retorna a issue criada com id."""
        pass

    @abstractmethod
    def move_issue(self, board_id: str, issue_id: str, column: str, from_column: str = None) -> None:
        """Move issue para outra coluna."""
        pass

    @abstractmethod
    def update_issue(self, board_id: str, issue_id: str, title: str = None, body: str = None) -> None:
        """Atualiza título e/ou body da issue."""
        pass

    @abstractmethod
    def add_comment(self, board_id: str, issue_id: str, comment: str) -> None:
        """Adiciona comentário na issue."""
        pass

    @abstractmethod
    def list_comments(self, board_id: str, issue_id: str) -> list[dict]:
        """Lista comentários de uma issue. Retorna [{author, date, body}]."""
        pass

    @abstractmethod
    def close_issue(self, board_id: str, issue_id: str) -> None:
        """Fecha/arquiva uma issue no board."""
        pass

    # ── Operações opcionais (defaults no-op; adapters sobrescrevem) ───────────

    def reopen_issue(self, board_id: str, issue_id: str) -> None:
        """Reabre uma issue fechada."""
        log.warning("Board", "reopen_issue não implementado neste adapter")

    def set_labels(self, board_id: str, issue_id: str, labels: list[str]) -> None:
        """Define (SET) as labels da issue, substituindo as existentes."""
        log.warning("Board", "set_labels não implementado neste adapter")

    def add_label(self, board_id: str, issue_id: str, label: str) -> None:
        """Adiciona uma única label à issue (mantém as demais)."""
        log.warning("Board", "add_label não implementado neste adapter")

    def remove_label(self, board_id: str, issue_id: str, label: str) -> None:
        """Remove uma única label da issue (mantém as demais)."""
        log.warning("Board", "remove_label não implementado neste adapter")

    def set_parent(self, board_id: str, issue_id: str, parent_id: str | None,
                   known_current=None) -> None:
        """Define o parent (sub-issue de parent_id). None remove o vínculo.

        known_current (opcional): parent atual conhecido, evita leitura extra.
        """
        log.warning("Board", "set_parent não implementado neste adapter")

    def set_children(self, board_id: str, issue_id: str, children_ids: list[str],
                     known_current: list[str] | None = None) -> None:
        """Define (SET) os filhos (sub-issues) desta issue.

        known_current (opcional): filhos atuais conhecidos, evita leitura extra.
        """
        log.warning("Board", "set_children não implementado neste adapter")

    def set_blocked_by(self, board_id: str, issue_id: str, blocker_ids: list[str],
                       known_current: list[str] | None = None) -> None:
        """Define (SET) as issues que bloqueiam esta.

        known_current (opcional): blocked_by atual conhecido, evita leitura extra.
        """
        log.warning("Board", "set_blocked_by não implementado neste adapter")

    def set_blocks(self, board_id: str, issue_id: str, blocked_ids: list[str],
                   known_current: list[str] | None = None) -> None:
        """Define (SET) as issues que esta bloqueia.

        known_current (opcional): blocks atual conhecido, evita leitura extra.
        """
        log.warning("Board", "set_blocks não implementado neste adapter")

    def archive_issue(self, board_id: str, issue_id: str) -> None:
        """Arquiva o item da issue no project."""
        log.warning("Board", "archive_issue não implementado neste adapter")

    def unarchive_issue(self, board_id: str, issue_id: str) -> None:
        """Desarquiva o item da issue no project."""
        log.warning("Board", "unarchive_issue não implementado neste adapter")

    def remove_from_board(self, board_id: str, issue_id: str) -> None:
        """Remove um item de um project (via deleteProjectV2Item)."""
        log.warning("Board", "remove_from_board não implementado neste adapter")

    def list_participations(self, issue_id: str) -> list["Participation"]:
        """Lista as participações (itens de Project V2) da issue em qualquer project.

        Cada `Participation` representa um item, resolvido ou não a um board
        configurado no pipe.yml. Não decide intenção/classificação - isso é
        responsabilidade do core (ParticipationPolicy, story #242).
        """
        log.warning("Board", "list_participations não implementado neste adapter")
        return []


class Board:
    """Core de boards - usa port para operações."""

    def __init__(self, port: BoardPort):
        self._port = port

    def connect(self, config: dict):
        self._port.connect(config)

    def check_access(self, config: dict):
        """Delega a verificação de acesso/permissões ao port.

        Levanta BoardAccessError quando o token não pode operar o board.
        """
        self._port.check_access(config)

    def list_participations(self, issue_id: str) -> list[Participation]:
        """Delega ao port a listagem de participações da issue."""
        return self._port.list_participations(issue_id)

    def sync_boards(self, config: dict):
        """Extrai boards do config e sincroniza via port."""
        boards = []
        for board_id, board_cfg in config.get("boards", {}).items():
            if board_id == "platform":
                continue
            if not isinstance(board_cfg, dict):
                continue
            columns = list(board_cfg.get("columns", {}).keys())
            boards.append({
                "id": board_id,
                "name": board_cfg.get("name"),
                "columns": columns
            })
        # Ordena por prioridade
        boards.sort(key=lambda b: config["boards"][b["id"]].get("priority", 999))
        self._port.sync_boards(boards)

    def list_issues(self, board_id: str) -> list[Issue]:
        return self._port.list_issues(board_id)

    def list_issues_since(self, board_id: str, since: str) -> list[Issue]:
        return self._port.list_issues_since(board_id, since)

    def get_issue(self, board_id: str, issue_id: str, fullsync: bool = False) -> Issue:
        return self._port.get_issue(board_id, issue_id, fullsync)

    def create_issue(self, board_id: str, title: str, body: str, column: str) -> Issue:
        return self._port.create_issue(board_id, title, body, column)

    def move_issue(self, board_id: str, issue_id: str, column: str, from_column: str = None):
        self._port.move_issue(board_id, issue_id, column, from_column)

    def update_issue(self, board_id: str, issue_id: str, title: str = None, body: str = None):
        self._port.update_issue(board_id, issue_id, title, body)

    def add_comment(self, board_id: str, issue_id: str, comment: str):
        self._port.add_comment(board_id, issue_id, comment)

    def list_comments(self, board_id: str, issue_id: str) -> list[dict]:
        return self._port.list_comments(board_id, issue_id)

    def close_issue(self, board_id: str, issue_id: str):
        self._port.close_issue(board_id, issue_id)

    def reopen_issue(self, board_id: str, issue_id: str):
        self._port.reopen_issue(board_id, issue_id)

    def set_labels(self, board_id: str, issue_id: str, labels: list[str]):
        self._port.set_labels(board_id, issue_id, labels)

    def add_label(self, board_id: str, issue_id: str, label: str):
        self._port.add_label(board_id, issue_id, label)

    def remove_label(self, board_id: str, issue_id: str, label: str):
        self._port.remove_label(board_id, issue_id, label)

    def set_parent(self, board_id: str, issue_id: str, parent_id: str | None,
                   known_current=None):
        self._port.set_parent(board_id, issue_id, parent_id, known_current)

    def set_children(self, board_id: str, issue_id: str, children_ids: list[str],
                     known_current: list[str] | None = None):
        self._port.set_children(board_id, issue_id, children_ids, known_current)

    def set_blocked_by(self, board_id: str, issue_id: str, blocker_ids: list[str],
                       known_current: list[str] | None = None):
        self._port.set_blocked_by(board_id, issue_id, blocker_ids, known_current)

    def set_blocks(self, board_id: str, issue_id: str, blocked_ids: list[str],
                   known_current: list[str] | None = None):
        self._port.set_blocks(board_id, issue_id, blocked_ids, known_current)

    def archive_issue(self, board_id: str, issue_id: str):
        self._port.archive_issue(board_id, issue_id)

    def unarchive_issue(self, board_id: str, issue_id: str):
        self._port.unarchive_issue(board_id, issue_id)

    def remove_from_board(self, board_id: str, issue_id: str):
        """Remove um item de um project (via deleteProjectV2Item)."""
        self._port.remove_from_board(board_id, issue_id)

    def apply_commands(self, board_id: str, issue_id: str, cmds, known: dict = None,
                       resolve_board_fn=None) -> dict:
        """Aplica os comandos anotados (IssueCommands) como atributos no board.

        Filosofia presença/ausência: o estado enviado reflete exatamente o que
        está declarado. Labels usam SET (substitui todas), incluindo a label
        especial need_human via all_labels().

        `known` (opcional) é o estado conhecido da issue (snapshot). Quando
        fornecido, cada setter só é chamado se o valor desejado difere do
        conhecido, e o estado conhecido é repassado ao setter para evitar GETs
        redundantes. Sem `known`, comporta-se como reconciliação completa
        (chama todos os setters, que descobrem o estado atual sozinhos).

        `resolve_board_fn` (opcional) é uma função
        `(target_issue_id: str) -> str | None` que retorna o board_id conhecido
        de uma issue (via snapshot), ou `None` se não rastreada. Quando `None`
        (não informado), o gate de contingência de suspensão
        (safety.cross_board_parent_links) é ignorado — comportamento atual,
        preservado para chamadas que não o fornecem. A ausência do parâmetro
        NÃO é tratada como "suspenso" nem como "bloqueia tudo"; equivale a "sem
        informação para decidir, então não impede".

        Retorna deltas das relações para o gatilho de par recíproco:
          {parent:  {"added": [...], "removed": [...]},
           children:{...}, blocked_by:{...}, blocks:{...}}
        Onde 'added'/'removed' são numbers de issues (str).
        """
        cmds, discards = _sanitize_relations_with_discards(issue_id, cmds)
        self_id = str(issue_id)
        for attr_name in discards:
            log.warning(
                "Board",
                f"[{board_id}] auto-referência descartada em {attr_name}: #{self_id}",
                board_id=board_id, issue_id=self_id,
            )

        deltas = {
            "parent": {"added": [], "removed": []},
            "children": {"added": [], "removed": []},
            "blocked_by": {"added": [], "removed": []},
            "blocks": {"added": [], "removed": []},
        }
        has_known = known is not None
        known = known or {}

        # ── Labels (SET; inclui need_human como label comum no board) ──────────
        desired_labels = cmds.all_labels()
        if not has_known or set(desired_labels) != set(known.get("labels") or []):
            self.set_labels(board_id, issue_id, desired_labels)

        # ── Parent ─────────────────────────────────────────────────────────────
        desired_parent = str(cmds.parent) if cmds.parent else None
        known_parent = known.get("parent")
        known_parent = str(known_parent) if known_parent else None
        if not has_known or desired_parent != known_parent:
            is_new_parent = bool(desired_parent) and desired_parent != known_parent
            if is_new_parent and _is_cross_board_link_blocked(
                    board_id, desired_parent, resolve_board_fn):
                # Contingência de suspensão: nova relação pai/filho entre boards
                # distintos é bloqueada, não aplicada. O snapshot não deve
                # registrar o vínculo como criado -> não entra em deltas.
                log.warning(
                    "Board",
                    f"[{board_id}] vínculo pai/filho bloqueado pela contingência "
                    f"(cross_board_parent_links=suspended): #{issue_id} -> parent #{desired_parent}",
                    event_type="cross_board_link_blocked",
                    board_id=board_id, issue_id=issue_id, target_id=desired_parent,
                    relation="parent",
                )
            else:
                self.set_parent(board_id, issue_id, cmds.parent,
                                known_current=(known_parent if has_known else None))
                if desired_parent and desired_parent != known_parent:
                    deltas["parent"]["added"].append(desired_parent)
                if known_parent and desired_parent != known_parent:
                    deltas["parent"]["removed"].append(known_parent)

        # ── Children ────────────────────────────────────────────────────────────
        desired_children = {str(c) for c in (cmds.children or [])}
        known_children = {str(c) for c in (known.get("children") or [])}
        if not has_known or desired_children != known_children:
            added_children = desired_children - known_children
            removed_children = known_children - desired_children
            # Contingência de suspensão: cada id NOVO em board distinto é
            # bloqueado individualmente (children é SET, então parte pode ser
            # aplicada e parte bloqueada na mesma chamada). Remoções nunca são
            # bloqueadas.
            blocked_children = {
                cid for cid in added_children
                if _is_cross_board_link_blocked(board_id, cid, resolve_board_fn)
            }
            for cid in sorted(blocked_children):
                log.warning(
                    "Board",
                    f"[{board_id}] vínculo pai/filho bloqueado pela contingência "
                    f"(cross_board_parent_links=suspended): #{issue_id} -> children #{cid}",
                    event_type="cross_board_link_blocked",
                    board_id=board_id, issue_id=issue_id, target_id=cid,
                    relation="children",
                )
            effective_children = desired_children - blocked_children
            # Só chama set_children se ainda há diferença a aplicar após
            # descartar os bloqueados (evita chamada inútil quando todos os ids
            # adicionados foram bloqueados e não há remoção pendente).
            if not has_known or effective_children != known_children:
                self.set_children(board_id, issue_id, list(effective_children),
                                  known_current=(list(known_children) if has_known else None))
            deltas["children"]["added"] = list(added_children - blocked_children)
            deltas["children"]["removed"] = list(removed_children)

        # ── Dependências: blocked_by ─────────────────────────────────────────────
        desired_bb = {str(b) for b in (cmds.blocked_by or [])}
        known_bb = {str(b) for b in (known.get("blocked_by") or [])}
        if not has_known or desired_bb != known_bb:
            self.set_blocked_by(board_id, issue_id, list(desired_bb),
                                known_current=(list(known_bb) if has_known else None))
            deltas["blocked_by"]["added"] = list(desired_bb - known_bb)
            deltas["blocked_by"]["removed"] = list(known_bb - desired_bb)

        # ── Dependências: blocks ─────────────────────────────────────────────────
        desired_bk = {str(b) for b in (cmds.blocks or [])}
        known_bk = {str(b) for b in (known.get("blocks") or [])}
        if not has_known or desired_bk != known_bk:
            self.set_blocks(board_id, issue_id, list(desired_bk),
                            known_current=(list(known_bk) if has_known else None))
            deltas["blocks"]["added"] = list(desired_bk - known_bk)
            deltas["blocks"]["removed"] = list(known_bk - desired_bk)

        # ── Arquivamento (presença arquiva; ausência desarquiva) ─────────────────
        desired_archived = bool(cmds.archive)
        if not has_known or desired_archived != bool(known.get("archived")):
            if desired_archived:
                self.archive_issue(board_id, issue_id)
            else:
                self.unarchive_issue(board_id, issue_id)

        # ── Fechamento / reabertura ──────────────────────────────────────────────
        # close presente fecha; reopen presente reabre; ausência não altera.
        known_state = (known.get("state") or "").lower() if has_known else None
        if cmds.close:
            if not has_known or known_state != "closed":
                self.close_issue(board_id, issue_id)
        elif cmds.reopen:
            if not has_known or known_state != "open":
                self.reopen_issue(board_id, issue_id)

        return deltas

    def apply_column_events(self, board_id: str, issue_id: str, events: list[str]) -> None:
        """Aplica eventos de coluna (on_in/on_out).

        Cada token do array é interpretado:
          'close'          -> fecha a issue
          'open'           -> reabre (se fechada) e desarquiva (se arquivada)
          'archive'        -> arquiva o item no project
          '-archive'       -> desarquiva o item no project
          'need_human'     -> adiciona a label especial need_human
          '-need_human'    -> remove a label need_human
          '<label>'        -> adiciona a label
          '-<label>'       -> remove a label
        """
        from src.core.commands import NEED_HUMAN_LABEL

        for raw in events or []:
            token = str(raw).strip()
            if not token:
                continue

            if token == "close":
                self.close_issue(board_id, issue_id)
            elif token == "open":
                self.reopen_issue(board_id, issue_id)
                self.unarchive_issue(board_id, issue_id)
            elif token == "archive":
                self.archive_issue(board_id, issue_id)
            elif token == "-archive":
                self.unarchive_issue(board_id, issue_id)
            elif token == "need_human":
                self.add_label(board_id, issue_id, NEED_HUMAN_LABEL)
            elif token == "-need_human":
                self.remove_label(board_id, issue_id, NEED_HUMAN_LABEL)
            elif token.startswith("-"):
                self.remove_label(board_id, issue_id, token[1:])
            else:
                self.add_label(board_id, issue_id, token)

    def board_ids(self, config: dict) -> list[str]:
        """Retorna os ids dos boards configurados (ignora 'platform')."""
        return [
            bid for bid, cfg in config.get("boards", {}).items()
            if bid != "platform" and isinstance(cfg, dict)
        ]

    def detect_board_changes(self, board_id: str, snapshot, queue) -> int:
        """Detecta mudanças de um board comparando com o snapshot e registra na fila.

          - issue no board sem correspondência no snapshot  -> create-down
          - issue no snapshot (com id) ausente no board      -> delete-down
          - issue com updated_at no board > snapshot         -> change-down

        Atualiza snapshot.last_board_update com a data mais recente.
        Atualiza status das issues no snapshot conforme o evento detectado.
        Retorna a quantidade de itens efetivamente adicionados à fila.
        """
        remote_issues = self._port.list_issues(board_id)
        remote_by_id = {str(i.id): i for i in remote_issues}

        snapshot_issues = snapshot.issues
        snapshot_by_id = {
            str(i["id"]): i for i in snapshot_issues if i.get("id") is not None
        }

        added = 0
        max_updated = snapshot.last_board_update or ""

        # Criadas ou modificadas no board
        for issue in remote_issues:
            issue_id = str(issue.id)
            known = snapshot_by_id.get(issue_id)

            if issue.updated_at and issue.updated_at > max_updated:
                max_updated = issue.updated_at

            if known is None:
                if queue.add(ChangeItem.of(SyncEvent.CREATE_DOWN, id=issue_id,
                                           board=board_id, fullsync=True)):
                    added += 1
                continue

            remote_at = issue.updated_at or ""
            snap_at = known.get("updated_at") or ""
            # Coluna vazia é divergência (propagação automática sem Status).
            # Trata-se como change-down para que _apply_change_down possa
            # reaplicar a coluna do snapshot local ou remover o item se for inválido.
            changed = (remote_at and snap_at and remote_at > snap_at) or \
                      (issue.column != known.get("column"))
            if changed:
                # Full sync diário: reconcilia todas as propriedades + deps.
                if queue.add(ChangeItem.of(SyncEvent.CHANGE_DOWN, id=issue_id,
                                           board=board_id, fullsync=True)):
                    known["status"] = SyncEvent.CHANGE_DOWN.value
                    added += 1

        # Deletadas no board (existiam no snapshot com id, sumiram do board)
        for issue_id in snapshot_by_id:
            if issue_id not in remote_by_id:
                if queue.add(ChangeItem.of(SyncEvent.DELETE_DOWN, id=issue_id, board=board_id)):
                    snapshot_by_id[issue_id]["status"] = SyncEvent.DELETE_DOWN.value
                    added += 1

        if max_updated:
            snapshot.last_board_update = max_updated
        snapshot.save()

        return added
