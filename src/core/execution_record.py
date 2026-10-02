"""Registro de execução de agentes + consolidação por linhagem histórica (#307).

Capacidade de NEGÓCIO, independente do log detalhado em Markdown
(`logs/<issue_id>/<ts>.md`, sujeito a `log.ttl`). Ao final de CADA execução de
agente e em QUALQUER desfecho, grava-se um registro estruturado e persistente
(`.pipe/executionRecords.json`) contendo identidade, tempo, contexto, resultado
técnico (taxonomia fechada), indicador de avanço independente, repetição sem
avanço (derivada) e consumo com proveniência. Esses registros preservam, de
forma durável e própria, a EXISTÊNCIA de cada issue executada e o VÍNCULO DE
PARENTESCO observado no momento da execução (`issue_parent`), de modo que a
linhagem histórica seja reconstruível a partir dos registros próprios — não dos
arquivos locais (apagados ao arquivar) nem dos logs (expurgados por TTL).

Princípios (issue #307):
- RN-01: resultado técnico e avanço são dimensões independentes.
- RN-02: `resultado` é um de {concluída, falha terminal, timeout, interrompida,
  desconhecida}; desfecho indeterminado grava `desconhecida`, nunca vazio.
- RN-03: repetição sem avanço = nova execução da MESMA issue, na MESMA etapa
  (mesmo board e coluna), após execução anterior naquela etapa que não avançou.
- RN-04/RN-05: consumo preserva valor/unidade/origem/disponibilidade; zero
  reportado e não informado são estados DISTINTOS; nunca soma unidades distintas.
- RN-06/RN-07: linhagem reconstruída dos registros próprios; sem ciclo nem dupla
  contagem; descendente conhecido = existência + parentesco capturados por
  registro.
- RN-08: descendente conhecido sem registro é incluído marcado `sem_registro`.
- RN-09: retenção própria em dias, independente de `log.ttl`; ausente ⇒ sem
  expurgo automático.
- RN-11: registros só nascem na execução e só saem por expurgo (sem exclusão
  manual).
- RN-13: nunca replica prompt/conversa; no máximo `log_ref`.
- CA-18: a contagem de execuções por contexto `(board, coluna, issue)` tem fonte
  única em `agent_circuit_break`; este módulo NÃO cria contador paralelo de
  contexto — grava um registro POR execução (artefato de negócio), que não é
  métrica de contexto.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from src.core.log import log

# Arquivo de estado interno durável e protegido (entra em PROTECTED_PATHS).
STORE_FILE = Path(".pipe/executionRecords.json")

# Versão do formato lógico do armazenamento.
STORE_VERSION = 1

# ── Taxonomia fechada de `resultado` (RN-02) ──────────────────────────────────
CONCLUIDA = "concluída"
FALHA_TERMINAL = "falha terminal"
TIMEOUT = "timeout"
INTERROMPIDA = "interrompida"
DESCONHECIDA = "desconhecida"

RESULTADOS = (CONCLUIDA, FALHA_TERMINAL, TIMEOUT, INTERROMPIDA, DESCONHECIDA)

# ── Disponibilidade do consumo (RN-04) ────────────────────────────────────────
DISPONIVEL = "disponível"
INDISPONIVEL = "indisponível"

# Rótulo geral de consumo no núcleo (RN-05). A unidade NATIVA de cada plataforma
# é preservada em `consumo.unidade`; este rótulo não substitui nem converte nada.
ROTULO_CONSUMO = "Tokens"


# ══════════════════════════════════════════════════════════════════════════════
# Mapeamento ExecutionResult → taxonomia de `resultado` (total e determinístico)
# ══════════════════════════════════════════════════════════════════════════════

def map_resultado(classe: str, origem: str | None = None) -> str:
    """Mapeia a classe de `ExecutionResult` (+ origem) para a taxonomia fechada.

    Total e determinístico (RN-02 / CT-20): toda classe tem destino; nenhuma
    produz vazio. Âncoras obrigatórias:
    - `SUCEDIDO` sem sinal de falha → `concluída` (CT-01);
    - `FALHA`/`falha persistente` → `falha terminal`, exceto quando a origem
      estruturada é `timeout` → `timeout`;
    - `UNKNOWN_OUTCOME` (ambíguo): `timeout` por timeout; `interrompida` quando a
      origem é de interrupção de transporte (`dispatch failure`/`erro interno`);
      `desconhecida` quando a evidência não é conclusiva;
    - `DEFINITE_NOT_STARTED` (não-inicialização comprovada) → `falha terminal`;
    - qualquer classe fora do conhecido → `desconhecida` (nunca vazio).
    """
    from src.core import execution

    org = (origem or "").strip().lower()

    if classe == execution.SUCEDIDO:
        return CONCLUIDA

    if classe == execution.UNKNOWN_OUTCOME:
        if org == "timeout":
            return TIMEOUT
        if org in ("dispatch failure", "erro interno"):
            return INTERROMPIDA
        return DESCONHECIDA

    if classe in (execution.FALHA, execution.FALHA_PERSISTENTE):
        if org == "timeout":
            return TIMEOUT
        return FALHA_TERMINAL

    if classe == execution.DEFINITE_NOT_STARTED:
        return FALHA_TERMINAL

    # Classe desconhecida/indeterminada: nunca vazio (RN-02).
    return DESCONHECIDA


# ══════════════════════════════════════════════════════════════════════════════
# Consumo (proveniência) — RN-04/RN-05
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Consumo:
    """Consumo de uma execução, com proveniência.

    `disponivel=False` ⇒ `valor` é SEMPRE None (invariante RNF-02). Zero
    reportado (`valor=0`, `disponivel=True`) e não informado (`disponivel=False`)
    são estados DISTINTOS que nunca compartilham representação (RN-04).
    """
    disponivel: bool = False
    valor: float | int | None = None
    unidade: str | None = None
    origem: str | None = None

    def __post_init__(self):
        if not self.disponivel:
            # Indisponível NUNCA carrega valor (nem zero).
            self.valor = None

    @property
    def disponibilidade(self) -> str:
        return DISPONIVEL if self.disponivel else INDISPONIVEL

    def to_dict(self) -> dict:
        d = {
            "disponibilidade": self.disponibilidade,
            "unidade": self.unidade,
            "origem": self.origem,
        }
        # `valor` só aparece quando disponível (nunca definido se indisponível).
        if self.disponivel:
            d["valor"] = self.valor
        return d

    @staticmethod
    def indisponivel(origem: str | None = None, unidade: str | None = None) -> "Consumo":
        return Consumo(disponivel=False, valor=None, unidade=unidade, origem=origem)

    @staticmethod
    def reportado(valor: float | int, unidade: str, origem: str) -> "Consumo":
        return Consumo(disponivel=True, valor=valor, unidade=unidade, origem=origem)

    @staticmethod
    def from_dict(d: dict | None) -> "Consumo":
        d = d or {}
        disponivel = d.get("disponibilidade") == DISPONIVEL
        return Consumo(
            disponivel=disponivel,
            valor=d.get("valor") if disponivel else None,
            unidade=d.get("unidade"),
            origem=d.get("origem"),
        )


# ══════════════════════════════════════════════════════════════════════════════
# Registro de execução (campos do contrato)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionRecord:
    """Registro de negócio de UMA execução de agente (um por execução — CA-1)."""

    issue_id: str
    board: str
    etapa: str                       # coluna/etapa no momento da execução
    resultado: str                   # taxonomia fechada (RN-02)
    avancou: bool                    # independente do resultado (RN-01)
    execucao_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    issue_parent: str | None = None  # parentesco observado NA execução (RN-06)
    plataforma: str | None = None
    agente: str | None = None
    modelo: str | None = None
    inicio: float | None = None      # epoch seconds
    fim: float | None = None         # epoch seconds (quando conhecido)
    repeticao_sem_avanco: bool = False  # derivado (RN-03)
    consumo: Consumo = field(default_factory=Consumo)
    log_ref: str | None = None       # referência ao log detalhado (sem conteúdo)

    @property
    def duracao(self) -> float | None:
        """Duração derivada de inicio/fim (quando ambos conhecidos)."""
        if self.inicio is None or self.fim is None:
            return None
        return self.fim - self.inicio

    def to_dict(self) -> dict:
        return {
            "execucao_id": self.execucao_id,
            "issue_id": str(self.issue_id),
            "issue_parent": str(self.issue_parent) if self.issue_parent is not None else None,
            "board": self.board,
            "etapa": self.etapa,
            "plataforma": self.plataforma,
            "agente": self.agente,
            "modelo": self.modelo,
            "inicio": self.inicio,
            "fim": self.fim,
            "duracao": self.duracao,
            "resultado": self.resultado,
            "avancou": self.avancou,
            "repeticao_sem_avanco": self.repeticao_sem_avanco,
            "consumo": self.consumo.to_dict(),
            "log_ref": self.log_ref,
        }

    @staticmethod
    def from_dict(d: dict) -> "ExecutionRecord":
        parent = d.get("issue_parent")
        return ExecutionRecord(
            issue_id=str(d.get("issue_id")),
            board=d.get("board"),
            etapa=d.get("etapa"),
            resultado=d.get("resultado") or DESCONHECIDA,
            avancou=bool(d.get("avancou")),
            execucao_id=d.get("execucao_id") or uuid.uuid4().hex,
            issue_parent=str(parent) if parent is not None else None,
            plataforma=d.get("plataforma"),
            agente=d.get("agente"),
            modelo=d.get("modelo"),
            inicio=d.get("inicio"),
            fim=d.get("fim"),
            repeticao_sem_avanco=bool(d.get("repeticao_sem_avanco")),
            consumo=Consumo.from_dict(d.get("consumo")),
            log_ref=d.get("log_ref"),
        )


# ══════════════════════════════════════════════════════════════════════════════
# Persistência atômica do armazenamento
# ══════════════════════════════════════════════════════════════════════════════

class ExecutionRecordStoreError(Exception):
    """Erro de integridade/persistência do armazenamento de registros.

    Mensagem acionável que NÃO expõe conteúdo sensível interno.
    """
    pass


def load_store() -> dict:
    """Carrega o armazenamento (dict). Vazio-padrão se o arquivo não existir.

    Levanta `ExecutionRecordStoreError` se o arquivo existir mas estiver
    ilegível, com JSON inválido ou versão desconhecida (integridade explícita).
    """
    if not STORE_FILE.exists():
        return {"version": STORE_VERSION, "records": []}
    try:
        raw = STORE_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExecutionRecordStoreError(
            f"registros de execução ilegíveis em {STORE_FILE.name}: "
            f"{exc.__class__.__name__}"
        ) from exc
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ExecutionRecordStoreError(
            f"registros de execução corrompidos em {STORE_FILE.name}: JSON inválido"
        ) from exc
    if not isinstance(data, dict) or data.get("version") != STORE_VERSION:
        found = data.get("version") if isinstance(data, dict) else "?"
        raise ExecutionRecordStoreError(
            f"registros de execução com versão inválida em {STORE_FILE.name}: "
            f"esperada {STORE_VERSION}, encontrada {found}"
        )
    data.setdefault("records", [])
    if not isinstance(data["records"], list):
        raise ExecutionRecordStoreError(
            f"registros de execução corrompidos em {STORE_FILE.name}: "
            f"'records' inválido"
        )
    return data


def save_store(data: dict) -> None:
    """Persiste o armazenamento atomicamente (temp + fsync + os.replace)."""
    directory = STORE_FILE.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=directory, prefix=".executionRecords-", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, STORE_FILE)
        except OSError:
            tmp_path.unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise ExecutionRecordStoreError(
            f"falha ao persistir registros de execução em {STORE_FILE.name}: "
            f"{exc.__class__.__name__}"
        ) from exc


def _load_records() -> list[ExecutionRecord]:
    data = load_store()
    return [ExecutionRecord.from_dict(r) for r in data["records"]]


# ══════════════════════════════════════════════════════════════════════════════
# Gravação do registro por execução
# ══════════════════════════════════════════════════════════════════════════════

def _computa_repeticao_sem_avanco(records: list[ExecutionRecord], board: str,
                                  etapa: str, issue_id: str) -> bool:
    """Deriva `repeticao_sem_avanco` (RN-03).

    True quando JÁ existe ao menos uma execução anterior da MESMA issue na MESMA
    etapa (mesmo board e coluna) que NÃO avançou a issue. Mudança de etapa
    descaracteriza (etapa é parte da identidade). Determinístico sobre os
    registros já persistidos (que não incluem o registro atual ainda).
    """
    issue_id = str(issue_id)
    for r in records:
        if (
            str(r.issue_id) == issue_id
            and r.board == board
            and r.etapa == etapa
            and not r.avancou
        ):
            return True
    return False


def record_execution(
    *,
    issue_id,
    board: str,
    etapa: str,
    resultado: str,
    avancou: bool,
    issue_parent=None,
    plataforma: str | None = None,
    agente: str | None = None,
    modelo: str | None = None,
    inicio: float | None = None,
    fim: float | None = None,
    consumo: Consumo | None = None,
    log_ref: str | None = None,
) -> ExecutionRecord:
    """Grava UM registro de execução (RN-11: criado só pela lógica interna).

    `repeticao_sem_avanco` é derivado dos registros anteriores (RN-03). Nunca
    replica prompt/conversa (RN-13): apenas `log_ref`.

    Levanta `ExecutionRecordStoreError` em falha de integridade/persistência (o
    chamador decide o tratamento — a gravação NÃO deve derrubar a esteira).
    """
    if resultado not in RESULTADOS:
        # Nunca vazio/nulo (RN-02): valor fora da taxonomia vira `desconhecida`.
        resultado = DESCONHECIDA

    data = load_store()
    existing = [ExecutionRecord.from_dict(r) for r in data["records"]]
    repeticao = _computa_repeticao_sem_avanco(existing, board, etapa, str(issue_id))

    record = ExecutionRecord(
        issue_id=str(issue_id),
        board=board,
        etapa=etapa,
        resultado=resultado,
        avancou=bool(avancou),
        issue_parent=str(issue_parent) if issue_parent is not None else None,
        plataforma=plataforma,
        agente=agente,
        modelo=modelo,
        inicio=inicio,
        fim=fim,
        repeticao_sem_avanco=repeticao,
        consumo=consumo or Consumo.indisponivel(origem=plataforma),
        log_ref=log_ref,
    )
    data["records"].append(record.to_dict())
    save_store(data)
    return record


def record_from_execution_result(
    *,
    result,
    issue_id,
    board: str,
    etapa: str,
    avancou: bool,
    issue_parent=None,
    plataforma: str | None = None,
    agente: str | None = None,
    modelo: str | None = None,
    inicio: float | None = None,
    fim: float | None = None,
    consumo: Consumo | None = None,
    log_ref: str | None = None,
) -> ExecutionRecord:
    """Grava um registro a partir de um `ExecutionResult` (mapeando a taxonomia).

    `result` pode ser `None` (adapter honrando o contrato antigo execute->None):
    nesse caso o desfecho é tratado como execução concluída sem sinal de falha
    (`concluída`), preservando o comportamento anterior do dispatch.
    """
    from src.core import execution

    if result is None:
        resultado = CONCLUIDA
    else:
        resultado = map_resultado(result.classe, getattr(result, "origem", None))

    return record_execution(
        issue_id=issue_id,
        board=board,
        etapa=etapa,
        resultado=resultado,
        avancou=avancou,
        issue_parent=issue_parent,
        plataforma=plataforma,
        agente=agente,
        modelo=modelo,
        inicio=inicio,
        fim=fim,
        consumo=consumo,
        log_ref=log_ref,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Consulta direta por issue
# ══════════════════════════════════════════════════════════════════════════════

def records_for_issue(issue_id) -> list[ExecutionRecord]:
    """Todos os registros de uma issue (consulta direta — CA-13/RNF-09).

    Independe de a issue ainda existir localmente: lê apenas os registros
    próprios, nunca os arquivos locais nem os logs.
    """
    issue_id = str(issue_id)
    return [r for r in _load_records() if str(r.issue_id) == issue_id]


# ══════════════════════════════════════════════════════════════════════════════
# Consulta/consolidação por issue raiz (linhagem histórica)
# ══════════════════════════════════════════════════════════════════════════════

def _build_children_map(records: list[ExecutionRecord]) -> dict[str, set[str]]:
    """Mapa pai → {filhos} a partir dos `issue_parent` observados nos registros.

    Captura a existência de cada issue (`issue_id`) e o vínculo observado em cada
    execução (`issue_parent`). Reconstruído SÓ dos registros próprios (RN-06).
    """
    children: dict[str, set[str]] = {}
    for r in records:
        if r.issue_parent is not None:
            children.setdefault(str(r.issue_parent), set()).add(str(r.issue_id))
    return children


def _descendants(root: str, children: dict[str, set[str]]) -> set[str]:
    """Conjunto de descendentes (transitivos) da raiz, inclusive a raiz.

    Travessia resiliente a CICLO e a MÚLTIPLOS CAMINHOS (RN-07): um conjunto
    `visited` garante que cada issue é visitada uma única vez, independentemente
    de quantos caminhos a alcancem ou de o grafo conter ciclos.
    """
    root = str(root)
    visited: set[str] = set()
    stack = [root]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for child in children.get(node, ()):  # determinismo não depende da ordem
            if child not in visited:
                stack.append(child)
    return visited


@dataclass
class LineageResult:
    """Saída lógica da consulta por issue raiz (contrato CA-15)."""
    issue_raiz: str
    itens_por_issue: list[dict]       # [{issue_id, sem_registro, execucoes}]
    agregados: dict                   # ver `consulta_linhagem`

    def to_dict(self) -> dict:
        return {
            "issue_raiz": self.issue_raiz,
            "itens_por_issue": self.itens_por_issue,
            "agregados": self.agregados,
        }


def consulta_linhagem(issue_raiz) -> LineageResult:
    """Consolida a linhagem histórica da issue raiz (CA-7/9/10/11/15, RN-06/07/08).

    Reconstrói a linhagem SOMENTE dos registros próprios (`issue_id` +
    `issue_parent`), sem abrir nenhum log individual nem depender dos arquivos
    locais. Responde:
    - `itens_por_issue`: cada issue conhecida da linhagem (raiz + descendentes),
      com `sem_registro` (true quando conhecida mas sem execução própria) e a
      quantidade de execuções próprias;
    - `agregados`: quantidade de execuções, duração total, consumo segmentado por
      `{unidade, origem}` (nunca soma unidades distintas), distribuição de
      resultados (taxonomia fechada) e repetições sem avanço.

    Invariantes: cada issue e cada execução contam EXATAMENTE uma vez, mesmo com
    ciclo ou múltiplos caminhos (RN-07).
    """
    issue_raiz = str(issue_raiz)
    records = _load_records()
    children = _build_children_map(records)

    # Conjunto de issues da linhagem (raiz + descendentes conhecidos), cada uma
    # uma única vez (dedup por conjunto — neutraliza ciclo e caminho duplo).
    lineage = _descendants(issue_raiz, children)

    # Execuções por issue (apenas as da linhagem), cada execução uma única vez.
    execs_by_issue: dict[str, list[ExecutionRecord]] = {i: [] for i in lineage}
    for r in records:
        iid = str(r.issue_id)
        if iid in lineage:
            execs_by_issue[iid].append(r)

    # ── itens_por_issue (ordenado por issue_id para determinismo) ──
    def _sort_key(iid: str):
        # Ordena numericamente quando possível; senão, lexicograficamente.
        try:
            return (0, int(iid))
        except (TypeError, ValueError):
            return (1, iid)

    itens: list[dict] = []
    for iid in sorted(lineage, key=_sort_key):
        execs = execs_by_issue.get(iid, [])
        itens.append({
            "issue_id": iid,
            "sem_registro": len(execs) == 0,
            "execucoes": len(execs),
        })

    # ── agregados ──
    todas_execucoes = [r for execs in execs_by_issue.values() for r in execs]

    quantidade_execucoes = len(todas_execucoes)

    # Duração total (soma das durações conhecidas; parciais/desconhecidas são
    # ignoradas na soma, pois duração não derivável não é zero).
    duracao_total = 0.0
    tem_duracao = False
    for r in todas_execucoes:
        d = r.duracao
        if d is not None:
            duracao_total += d
            tem_duracao = True
    duracao_total = duracao_total if tem_duracao else 0.0

    # Consumo segmentado por {unidade, origem}; NUNCA soma unidades distintas
    # (RN-05). `ha_indisponivel` sinaliza presença de execução sem consumo.
    consumo_segmentos: dict[tuple, dict] = {}
    for r in todas_execucoes:
        c = r.consumo
        if c.disponivel:
            key = (c.unidade, c.origem)
            seg = consumo_segmentos.setdefault(
                key, {"unidade": c.unidade, "origem": c.origem,
                       "total": 0, "ha_indisponivel": False}
            )
            seg["total"] += c.valor or 0
        else:
            # Indisponível: marca o segmento correspondente (por origem/unidade
            # quando houver), ou um segmento genérico de indisponibilidade.
            key = (c.unidade, c.origem)
            seg = consumo_segmentos.setdefault(
                key, {"unidade": c.unidade, "origem": c.origem,
                       "total": 0, "ha_indisponivel": False}
            )
            seg["ha_indisponivel"] = True

    consumo_por_unidade_origem = list(consumo_segmentos.values())

    # Distribuição de resultados (taxonomia fechada; sempre todas as chaves).
    distribuicao = {r: 0 for r in RESULTADOS}
    for r in todas_execucoes:
        distribuicao[r.resultado] = distribuicao.get(r.resultado, 0) + 1

    repeticoes = sum(1 for r in todas_execucoes if r.repeticao_sem_avanco)

    agregados = {
        "quantidade_execucoes": quantidade_execucoes,
        "duracao_total": duracao_total,
        "consumo_por_unidade_origem": consumo_por_unidade_origem,
        "distribuicao_resultados": distribuicao,
        "repeticoes_sem_avanco": repeticoes,
    }

    return LineageResult(
        issue_raiz=issue_raiz,
        itens_por_issue=itens,
        agregados=agregados,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Retenção própria (expurgo condicional) — RN-09
# ══════════════════════════════════════════════════════════════════════════════

def resolve_retencao_dias(config: dict) -> int | None:
    """Resolve `registro.retencao_dias` (None quando ausente ⇒ sem expurgo).

    Não valida — assume que `validate_registro` já rodou em `check_config`.
    """
    registro = config.get("registro") or {}
    return registro.get("retencao_dias")


def purge_expired(retencao_dias: int | None, now: float | None = None) -> int:
    """Expurga registros com idade `(agora - criacao) >= retencao_dias` (RN-09).

    - `retencao_dias is None` (ausente): NENHUM registro é removido (estado
      seguro por padrão). Retorna 0.
    - A idade é derivada de `inicio` (instante de criação/execução do registro).
      Registros sem `inicio` conhecido não são expurgados (não há idade segura).

    Retorna a quantidade de registros removidos. Idempotente e acionado só pela
    lógica interna do motor (RN-11).
    """
    if retencao_dias is None:
        return 0

    now = time.time() if now is None else now
    limite_seg = retencao_dias * 86400

    data = load_store()
    antes = len(data["records"])
    mantidos = []
    for r in data["records"]:
        inicio = r.get("inicio")
        if inicio is None:
            mantidos.append(r)  # sem idade segura → preserva
            continue
        idade = now - inicio
        if idade >= limite_seg:
            continue  # elegível a expurgo → removido
        mantidos.append(r)
    data["records"] = mantidos
    removidos = antes - len(mantidos)
    if removidos:
        save_store(data)
        log.info(
            "ExecutionRecord",
            f"expurgo de registros por retenção: {removidos} removido(s) "
            f"(retencao_dias={retencao_dias})",
            event="execution_record_purge",
            removidos=removidos, retencao_dias=retencao_dias,
        )
    return removidos
