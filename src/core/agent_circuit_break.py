"""Limitador de reexecuções de agente por contexto (issue #306).

Mecanismo opt-in e complementar ao cooldown (`boards.rerun_cooldown`): enquanto
o cooldown apenas ESPAÇA reexecuções da mesma issue no mesmo
`(board, coluna, issue)`, este limitador impõe um TETO de execuções por janela
de tempo. Ao atingir o limite, bloqueia a próxima execução ANTES de ela começar,
marca a issue com `need_human`, publica um comentário acionável idempotente e
zera a franquia do contexto (de modo que a remoção de `need_human` conceda uma
nova franquia completa).

Fonte única da contagem (nota de integração #307/#315): este módulo é a ÚNICA
fonte de verdade para "quantas execuções houve neste contexto". Toda entrega de
uma issue ao agente é contabilizada aqui, no instante da entrega, independente do
resultado.

Contratos (ver issue #306 / casos de teste):
- Identidade do contexto: `(board, coluna, issue)`. Mudar de coluna é contexto
  novo, sem herança (há no máximo um contexto ativo por `(board, issue)`).
- Janela: só contam ocorrências com idade ESTRITAMENTE menor que `T` (idade `==T`
  já expira).
- Sem política configurada (`agent_circuit_break` ausente): nada é bloqueado, mas
  a contagem interna continua ocorrendo.
- Estado persistido de forma atômica (arquivo temporário + fsync + os.replace) em
  arquivo JSON local protegido; conteúdo nunca exposto a agente/comentário/log.
- Fail-closed: falha ao persistir a ocorrência ou estado corrompido NEGA a
  admissão da issue (não executa) — nunca assume contagem vazia.
- Ordem obrigatória do bloqueio: (1) persistir evento + esvaziar ocorrências;
  (2) aplicar `need_human`; (3) publicar comentário só se o marcador ausente;
  (4) reconciliar; (5) manter execução negada até sinalização reconciliada.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from src.core.commands import NEED_HUMAN_LABEL
from src.core.log import log

# Arquivo de estado interno protegido (entra em PROTECTED_PATHS — src/core/agent.py).
STATE_FILE = Path(".pipe/agentCircuitBreak.json")

# Versão do formato lógico do estado persistido.
STATE_VERSION = 1

# Marcador técnico oculto do comentário de bloqueio (idempotência). Carrega
# APENAS o event_id — nunca conteúdo sensível.
COMMENT_MARKER_PREFIX = "agent-circuit-break:"

# Progresso da sinalização (máquina de estados do `trip`).
STEP_PERSISTED = "persisted"      # evento persistido, label ainda não aplicada
STEP_LABELED = "labeled"          # label aplicada, comentário pendente
STEP_SIGNALED = "signaled"        # label + comentário confirmados (reconciliado)


# ══════════════════════════════════════════════════════════════════════════════
# Configuração (validação de forma + resolução da política)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CircuitBreakPolicy:
    """Política resolvida do limitador. `active=False` quando o bloco é ausente."""
    active: bool
    executions: int | None = None
    window: int | None = None


def validate_agent_circuit_break(config: dict) -> None:
    """Valida a chave opcional de raiz `agent_circuit_break` (issue #306).

    Importa `ConfigError` localmente para evitar ciclo de importação com
    `src.core.config` (que chama esta função em `check_config`).

    Regras (cada violação levanta ConfigError citando o caminho completo):
    - ausência do bloco é válida (política inativa);
    - se presente, deve ser um mapa com EXATAMENTE `executions` e `window`
      (ambos obrigatórios juntos); campos desconhecidos são rejeitados;
    - `executions`: inteiro >= 1 (bool rejeitado ANTES de int — True/False são
      instâncias de int em Python);
    - `window`: inteiro >= 1 (segundos; bool rejeitado antes de int).
    """
    from src.core.config import ConfigError

    if "agent_circuit_break" not in config:
        return

    block = config["agent_circuit_break"]
    if not isinstance(block, dict):
        raise ConfigError(
            f"agent_circuit_break: deve ser um mapa com 'executions' e 'window' "
            f"(valor recebido: {block!r})"
        )

    # Campos desconhecidos rejeitados (citando o caminho do campo indevido).
    known = {"executions", "window"}
    for key in block:
        if key not in known:
            raise ConfigError(
                f"agent_circuit_break.{key}: campo desconhecido "
                f"(permitidos: 'executions', 'window')"
            )

    # Obrigatoriedade conjunta: se o bloco existe, exige ambos.
    if "executions" not in block:
        raise ConfigError(
            "agent_circuit_break.executions: campo obrigatório quando o bloco "
            "'agent_circuit_break' está presente"
        )
    if "window" not in block:
        raise ConfigError(
            "agent_circuit_break.window: campo obrigatório quando o bloco "
            "'agent_circuit_break' está presente"
        )

    executions = block["executions"]
    if isinstance(executions, bool) or not isinstance(executions, int) or executions < 1:
        raise ConfigError(
            f"agent_circuit_break.executions: deve ser inteiro >= 1 "
            f"(valor recebido: {executions!r})"
        )

    window = block["window"]
    if isinstance(window, bool) or not isinstance(window, int) or window < 1:
        raise ConfigError(
            f"agent_circuit_break.window: deve ser inteiro >= 1 (segundos) "
            f"(valor recebido: {window!r})"
        )


def resolve_policy(config: dict) -> CircuitBreakPolicy:
    """Resolve a política a partir do config.

    Não valida — assume que `validate_agent_circuit_break` já rodou em
    `check_config`. Ausência do bloco = política inativa (`active=False`).
    """
    block = config.get("agent_circuit_break")
    if not isinstance(block, dict):
        return CircuitBreakPolicy(active=False)
    return CircuitBreakPolicy(
        active=True,
        executions=block["executions"],
        window=block["window"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# Erros de integridade / persistência
# ══════════════════════════════════════════════════════════════════════════════

class CircuitBreakStateError(Exception):
    """Erro de integridade/persistência do estado do limitador.

    Levantado quando o estado está ilegível/corrompido ou não pode ser
    persistido. A mensagem é acionável e NÃO expõe o conteúdo interno. O ponto
    de entrega trata este erro como fail-closed: nega a admissão da issue.
    """
    pass


# ══════════════════════════════════════════════════════════════════════════════
# Persistência atômica do estado
# ══════════════════════════════════════════════════════════════════════════════

def _context_key(board_id: str, issue_id) -> str:
    """Chave lógica do contexto ativo: `<board>/<issue>` (a coluna completa a
    identidade e vive dentro do registro)."""
    return f"{board_id}/{issue_id}"


def load_state() -> dict:
    """Carrega o estado persistido (dict). Vazio-padrão se o arquivo não existir.

    Levanta `CircuitBreakStateError` se o arquivo existir mas estiver ilegível,
    com JSON inválido ou com `version` desconhecida (integridade explícita — não
    assume contagem vazia).
    """
    if not STATE_FILE.exists():
        return {"version": STATE_VERSION, "active_contexts": {}}
    try:
        raw = STATE_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise CircuitBreakStateError(
            f"estado do limitador ilegível em {STATE_FILE.name}: {exc.__class__.__name__}"
        ) from exc
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise CircuitBreakStateError(
            f"estado do limitador corrompido em {STATE_FILE.name}: JSON inválido"
        ) from exc
    if not isinstance(data, dict) or data.get("version") != STATE_VERSION:
        raise CircuitBreakStateError(
            f"estado do limitador com versão inválida em {STATE_FILE.name}: "
            f"esperada {STATE_VERSION}, encontrada {data.get('version') if isinstance(data, dict) else '?'}"
        )
    data.setdefault("active_contexts", {})
    if not isinstance(data["active_contexts"], dict):
        raise CircuitBreakStateError(
            f"estado do limitador corrompido em {STATE_FILE.name}: "
            f"'active_contexts' inválido"
        )
    return data


def save_state(data: dict) -> None:
    """Persiste o estado atomicamente (arquivo temporário + fsync + os.replace).

    Levanta `CircuitBreakStateError` em falha de I/O (fail-closed no chamador).
    """
    directory = STATE_FILE.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=directory, prefix=".agentCircuitBreak-", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, STATE_FILE)
        except OSError:
            tmp_path.unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise CircuitBreakStateError(
            f"falha ao persistir o estado do limitador em {STATE_FILE.name}: "
            f"{exc.__class__.__name__}"
        ) from exc


def _get_or_reset_context(data: dict, board_id: str, col_id: str, issue_id) -> dict:
    """Retorna o registro do contexto ativo `(board, issue)`, reiniciando-o se a
    coluna mudou (contexto novo, sem herança — RN-02).

    Muta `data` in-place (substituindo o registro quando a coluna diverge).
    """
    key = _context_key(board_id, issue_id)
    ctx = data["active_contexts"].get(key)
    if ctx is None or ctx.get("column") != col_id:
        # Transição de coluna (ou primeiro registro): substitui por contexto vazio.
        ctx = {"column": col_id, "occurrences": [], "trip": None}
        data["active_contexts"][key] = ctx
    return ctx


def _count_within_window(occurrences: list, now: float, window: int) -> int:
    """Conta ocorrências com idade ESTRITAMENTE menor que `window` (RN-03/RF-04).

    Idade == window já expira (borda fechada em T).
    """
    return sum(1 for ts in occurrences if (now - ts) < window)


# ══════════════════════════════════════════════════════════════════════════════
# Admissão: contagem no instante da entrega + decisão de bloqueio
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AdmissionDecision:
    """Resultado da avaliação de admissão de uma entrega.

    - `admitted`: True se o agente pode ser despachado; False se bloqueado ou
      negado por falha fechada.
    - `blocked`: True quando a negação é por bloqueio de limite (teto atingido).
    - `event_id`: id do evento de bloqueio (quando `blocked`).
    """
    admitted: bool
    blocked: bool = False
    event_id: str | None = None


class CircuitBreaker:
    """Núcleo do limitador: contagem por contexto e decisão de bloqueio.

    Instanciado por entrega no ponto de entrega (`call_agent`). O `clock` é
    injetável para testes de janela (default: `time.time`).
    """

    def __init__(self, policy: CircuitBreakPolicy, board, clock=time.time):
        self._policy = policy
        self._board = board
        self._clock = clock

    # ── Admissão (contagem + bloqueio) ────────────────────────────────────────

    def admit(self, board_id: str, col_id: str, issue_id,
              need_human_present: bool = False) -> AdmissionDecision:
        """Avalia a admissão de uma entrega ao agente.

        `need_human_present` informa se a issue ainda carrega a label
        `need_human` no board/body no momento da avaliação. É o sinal de retomada
        humana: um `trip` persistido com a label JÁ removida significa que o
        operador liberou a issue — o `trip` é descartado e uma franquia completa
        é concedida (sem resíduo da janela anterior). Em produção, `keep_task`
        pula issues com `need_human` (via `_is_blocked`), então a admissão de uma
        issue com `trip` só é alcançada quando a label já foi removida — a
        retomada. A reconciliação de um `trip` ainda sinalizado (label presente)
        é usada na recuperação após queda/reinício.

        Fluxo:
        1. Carrega o estado (fail-closed em corrupção/ilegibilidade).
        2. `trip` presente:
           - label ainda presente → recuperação: retoma a sinalização faltante e
             mantém a execução NEGADA;
           - label ausente → retomada humana: descarta o `trip`, zera o contexto
             e concede franquia completa (segue para a decisão normal abaixo).
        3. Sem política: registra a ocorrência (contagem interna) e admite.
        4. Com política: decide pelo número de ocorrências dentro da janela.
           - abaixo do limite: registra a ocorrência e admite;
           - no limite: aciona o bloqueio (persiste evento + esvazia ocorrências
             → aplica need_human → publica comentário idempotente) e NEGA.

        Levanta `CircuitBreakStateError` em falha de integridade/persistência —
        o chamador trata como fail-closed (não despacha).
        """
        now = self._clock()
        data = load_state()
        ctx = _get_or_reset_context(data, board_id, col_id, issue_id)

        # ── Bloqueio pendente (trip) ──────────────────────────────────────────
        if ctx.get("trip") is not None:
            if need_human_present:
                # Label ainda presente → recuperação: retoma a sinalização
                # faltante e mantém a execução negada.
                trip = ctx["trip"]
                if trip.get("step") != STEP_SIGNALED:
                    self._reconcile_trip(data, board_id, issue_id, ctx)
                return AdmissionDecision(admitted=False, blocked=True,
                                         event_id=ctx["trip"].get("event_id"))
            # Label ausente → retomada humana: descarta o trip e zera o contexto
            # (franquia completa, sem resíduo). Segue para a decisão normal.
            ctx["trip"] = None
            ctx["occurrences"] = []
            save_state(data)

        if not self._policy.active:
            # Sem política: contagem interna continua, nunca bloqueia. Como não
            # há teto a proteger, a persistência da ocorrência é best-effort: uma
            # falha de escrita NÃO nega a admissão (não há risco de execução
            # excedente sem limite). A integridade de leitura (corrupção) acima
            # continua fail-closed, pois representa estado inconsistente.
            ctx["occurrences"].append(int(now))
            try:
                save_state(data)
            except CircuitBreakStateError as exc:
                log.warning(
                    "CircuitBreak",
                    f"[{board_id}] #{issue_id} contagem interna não persistida "
                    f"(política inativa, best-effort): {exc.__class__.__name__}",
                    event="agent_circuit_break_count_write_skipped",
                    board_id=board_id, issue_id=str(issue_id),
                )
            return AdmissionDecision(admitted=True)

        # Política ativa: decide ANTES de registrar a ocorrência excedente.
        within = _count_within_window(ctx["occurrences"], now, self._policy.window)
        if within >= self._policy.executions:
            # Teto atingido → bloqueia (não conta a excedente).
            event_id = self._trip(data, board_id, col_id, issue_id, ctx)
            return AdmissionDecision(admitted=False, blocked=True, event_id=event_id)

        # Abaixo do limite: conta a entrega e admite.
        ctx["occurrences"].append(int(now))
        save_state(data)
        return AdmissionDecision(admitted=True)

    # ── Máquina de estados do bloqueio (trip) ─────────────────────────────────

    def _trip(self, data: dict, board_id: str, col_id: str, issue_id, ctx: dict) -> str:
        """Aciona o bloqueio seguindo a ordem obrigatória do contrato.

        (1) persistir evento + esvaziar ocorrências ANTES de qualquer chamada
        externa; (2) aplicar need_human; (3) publicar comentário idempotente;
        (4) reconciliar/avançar o progresso. Qualquer falha externa é capturada
        por issue (não trava o loop global) — o progresso parcial fica no `trip`
        para retomada no ciclo seguinte.
        """
        event_id = uuid.uuid4().hex[:12]
        ctx["trip"] = {
            "event_id": event_id,
            "executions": self._policy.executions,
            "window": self._policy.window,
            "column": col_id,
            "step": STEP_PERSISTED,
        }
        # (1) Esvaziar as ocorrências ANTES de qualquer chamada externa (RN-06).
        ctx["occurrences"] = []
        save_state(data)

        log.warning(
            "CircuitBreak",
            f"[{board_id}] #{issue_id} bloqueada em '{col_id}' — limite "
            f"{self._policy.executions} execução(ões) em {self._policy.window}s atingido",
            event="agent_circuit_break_trip", board_id=board_id, issue_id=str(issue_id),
            col_id=col_id, executions=self._policy.executions,
            window=self._policy.window, event_id=event_id,
        )

        # (2)+(3) Sinalização (aplicar label + comentário idempotente).
        self._reconcile_trip(data, board_id, issue_id, ctx)
        return event_id

    def _reconcile_trip(self, data: dict, board_id: str, issue_id, ctx: dict) -> None:
        """Retoma a sinalização pendente a partir do progresso atual do `trip`.

        Idempotente: aplica apenas os passos faltantes. Falha externa é capturada
        por issue (registra pendência acionável, não propaga) — o progresso fica
        persistido para o ciclo seguinte.
        """
        trip = ctx["trip"]
        event_id = trip["event_id"]
        try:
            # (2) Aplicar need_human (idempotente no board).
            if trip["step"] == STEP_PERSISTED:
                self._board.add_label(board_id, issue_id, NEED_HUMAN_LABEL)
                trip["step"] = STEP_LABELED
                save_state(data)

            # (3) Publicar comentário só se o marcador do evento ainda não existe.
            if trip["step"] == STEP_LABELED:
                if not self._comment_exists(board_id, issue_id, event_id):
                    self._board.add_comment(
                        board_id, issue_id,
                        self._build_comment(board_id, issue_id, trip),
                    )
                trip["step"] = STEP_SIGNALED
                save_state(data)
        except Exception as exc:  # falha externa por issue — não trava o loop
            log.error(
                "CircuitBreak",
                f"[{board_id}] #{issue_id} sinalização de bloqueio pendente "
                f"(evento {event_id}) — será retomada: {exc.__class__.__name__}",
                event="agent_circuit_break_signal_pending",
                board_id=board_id, issue_id=str(issue_id), event_id=event_id,
                step=trip.get("step"),
            )

    def _comment_exists(self, board_id: str, issue_id, event_id: str) -> bool:
        """True se já existe comentário com o marcador do evento (idempotência)."""
        marker = f"{COMMENT_MARKER_PREFIX}{event_id}"
        for c in self._board.list_comments(board_id, issue_id) or []:
            if marker in (c.get("body") or ""):
                return True
        return False

    def _build_comment(self, board_id: str, issue_id, trip: dict) -> str:
        """Monta o comentário de bloqueio (motivo, issue, board, coluna, N, T) +
        marcador oculto do evento. Legível e autossuficiente para o operador —
        sem exigir leitura de estado interno. Nunca inclui conteúdo sensível.
        """
        n = trip["executions"]
        t = trip["window"]
        col = trip["column"]
        return (
            f"🚦 **Execução bloqueada pelo limitador de reexecuções (circuit break).**\n\n"
            f"Esta issue atingiu o limite de execuções permitidas no contexto "
            f"atual e foi marcada com `need_human`.\n\n"
            f"- **Motivo:** limite de reexecuções atingido no contexto "
            f"`(board, coluna, issue)`.\n"
            f"- **Issue:** #{issue_id}\n"
            f"- **Board:** {board_id}\n"
            f"- **Coluna:** {col}\n"
            f"- **Limite (N):** {n} execução(ões)\n"
            f"- **Janela (T):** {t}s ({_format_duration(t)})\n\n"
            f"Para retomar: investigue/redirecione a issue e **remova a label "
            f"`need_human`**. A remoção concede uma nova franquia completa de "
            f"{n} execução(ões).\n\n"
            f"<!-- {COMMENT_MARKER_PREFIX}{trip['event_id']} -->"
        )


def _format_duration(seconds: int) -> str:
    """Formata uma duração em segundos para leitura humana (não altera o valor
    configurado — só a apresentação)."""
    if seconds % 3600 == 0:
        h = seconds // 3600
        return f"{h}h"
    if seconds % 60 == 0:
        m = seconds // 60
        return f"{m}min"
    return f"{seconds}s"


# ══════════════════════════════════════════════════════════════════════════════
# Capacidade exigida do adaptador de board (gate de inicialização)
# ══════════════════════════════════════════════════════════════════════════════

def adapter_can_apply_label(adapter) -> bool:
    """True se o adaptador de board sobrescreve a aplicação de label (não é o
    default no-op inócuo de `BoardPort`).

    Com a política ativa, aplicar `need_human` precisa ter efeito real; um
    adaptador que herda o default no-op (`BoardPort.add_label`/`set_labels`)
    deve provocar falha na inicialização, nunca aparentar que sinalizou.

    A detecção compara os métodos `add_label` e `set_labels` da instância com os
    de `BoardPort`: se AMBOS forem os defaults herdados, não há capacidade real.
    """
    from src.core.board import BoardPort

    add_default = getattr(type(adapter), "add_label", None) is BoardPort.add_label
    set_default = getattr(type(adapter), "set_labels", None) is BoardPort.set_labels
    return not (add_default and set_default)


def check_label_capability(config: dict, adapter) -> None:
    """Gate de inicialização: com a política ativa, exige capacidade real de
    aplicar label no adaptador. Caso contrário, levanta `CircuitBreakStateError`
    citando a capacidade ausente — a esteira não deve iniciar.

    Sem política ativa, é no-op (o mecanismo está desligado).
    """
    policy = resolve_policy(config)
    if not policy.active:
        return
    if not adapter_can_apply_label(adapter):
        raise CircuitBreakStateError(
            "agent_circuit_break ativo exige capacidade real de aplicar label "
            "no adaptador de board (need_human), mas o adaptador "
            f"'{type(adapter).__name__}' não sobrescreve add_label/set_labels "
            "(usa o default no-op de BoardPort). A sinalização de bloqueio não "
            "teria efeito. Corrija o adaptador ou desative a política."
        )
