"""Gerador de telemetria de exemplo (Contrato de telemetria v1).

Simula pipes fictícias da Esteira Agêntica e envia, via OTLP, os mesmos eventos,
métricas e traces que uma pipe real enviaria. Serve para validar o dashboard sem
depender de uma pipe em execução.

Cenário de cada pipe: épicos (board raiz `epicos`) → histórias (`historias`) →
tarefas (`tarefas`), quatro agentes (planejador, desenvolvedor, testador, revisor),
todos os resultados de execução, consumo não informado, limites de consumo, circuit
break, fila de sincronismo, throttle/penalty e circuit breaker do board.

Fases:
1. Histórico: simula GERADOR_HISTORICO_DIAS dias com timestamps no passado (só na
   primeira subida; marcador em /dados).
2. Ao vivo: a cada GERADOR_INTERVALO segundos, um passo da simulação com horário
   atual, para mostrar a reordenação das listas vivas.

Dados 100% fictícios.
"""

from __future__ import annotations

import json
import math
import os
import random
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from opentelemetry import trace
from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import Observation
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://esteira-otlp:4318").rstrip("/")
N_PIPES = int(os.environ.get("GERADOR_PIPES", "2"))
HISTORICO_DIAS = float(os.environ.get("GERADOR_HISTORICO_DIAS", "7"))
INTERVALO = float(os.environ.get("GERADOR_INTERVALO", "6"))
ESTADO_DIR = Path(os.environ.get("GERADOR_ESTADO", "/dados"))
SEED = int(os.environ.get("GERADOR_SEED", "42"))

NS = 1_000_000_000
COLUNAS = ["todo", "planejamento", "dev", "testes", "revisao", "done"]

PIPES = [
    {"id": "https://github.com/exemplo/loja-ficticia.git", "nome": "loja-ficticia",
     "limites": {"diario": 1500, "semanal": 6000, "mensal": 20000}, "tokens": False},
    {"id": "https://github.com/exemplo/escrevas-ficticio.git", "nome": "escrevas-ficticio",
     "limites": {"diario": 300, "semanal": 1900, "mensal": 7500}, "tokens": True},
    {"id": "https://github.com/exemplo/terceira-pipe.git", "nome": "terceira-pipe",
     "limites": {}, "tokens": False},
]

AGENTES = {
    # id: (nome, custo médio em créditos, duração média s, p_sucesso)
    "planejador": ("Planejador", 4.0, 240, 0.88),
    "desenvolvedor": ("Desenvolvedor", 18.0, 900, 0.78),
    "testador": ("Testador", 7.0, 420, 0.82),
    "revisor": ("Revisor", 5.0, 300, 0.86),
}
MODELOS = ["claude-sonnet-4.5", "claude-haiku-4.5"]

OPERACOES_API = ["get_issue", "update_issue", "move_issue", "add_comment", "set_parent",
                 "set_labels", "create_issue", "list_issues"]


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} [gerador] {msg}", flush=True)


@dataclass
class Issue:
    id: str
    board: str
    pai: str = ""
    coluna: str = "todo"
    filhos: list = field(default_factory=list)
    estado: str = "open"
    arquivada: bool = False
    tipo: str = "tarefa"            # epico | historia | tarefa
    bloqueada_ate: float = 0.0
    sem_avanco: int = 0             # execuções seguidas sem avanço na coluna atual
    ultima_sem_avanco: bool = False


class Pipe:
    def __init__(self, idx: int, cfg: dict, rnd: random.Random, proximo_id: int):
        self.cfg = cfg
        self.rnd = rnd
        self.idx = idx
        self.proximo_id = proximo_id
        self.issues: dict[str, Issue] = {}
        self.throttle = 0
        self.throttle_desde = 0.0
        self.penalty_h = 0
        self.penalty_ate = 0.0
        self.breaker = "closed"
        self.breaker_desde = 0.0
        self.erros_seguidos = 0
        self.issues_breaker = 0
        self.fila: list[float] = []          # timestamps de enfileiramento
        self.dead_letter: dict[str, int] = {}
        self.orfaos = 0
        self.consumo: dict[str, tuple[str, float]] = {}  # periodo -> (chave_periodo, acumulado)
        self.bloqueado_limite = False
        self.degradado_ate = 0.0         # janela de instabilidade do board

        res = Resource.create({
            "service.name": "esteira-agentica",
            "service.version": "1.30.0",
            "service.instance.id": cfg["id"],
            "esteira.pipe.nome": cfg["nome"],
            "deployment.environment.name": "exemplo",
            "esteira.contrato": 1,
        })
        self.lp = LoggerProvider(resource=res)
        self.lp.add_log_record_processor(BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=f"{ENDPOINT}/v1/logs"),
            max_queue_size=200_000, max_export_batch_size=2048, schedule_delay_millis=2000))
        self.logger = self.lp.get_logger("esteira.gerador")
        self.tp = TracerProvider(resource=res)
        self.tp.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{ENDPOINT}/v1/traces"),
            max_queue_size=100_000, max_export_batch_size=2048, schedule_delay_millis=2000))
        self.tracer = self.tp.get_tracer("esteira.gerador")
        self.mp = MeterProvider(resource=res, metric_readers=[PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{ENDPOINT}/v1/metrics"), export_interval_millis=15000)])
        self._metricas()

    # ── emissão ────────────────────────────────────────────────────────────
    def evento(self, nome: str, ts: float, attrs: dict, ctx=None, sev=SeverityNumber.INFO) -> None:
        limpos = {k: v for k, v in attrs.items() if v is not None}
        self.logger.emit(timestamp=int(ts * NS), observed_timestamp=int(ts * NS), context=ctx,
                         severity_number=sev, severity_text=sev.name, body=nome,
                         event_name=nome, attributes=limpos)

    def _metricas(self) -> None:
        m = self.mp.get_meter("esteira.gerador")
        plat = {"esteira.board.plataforma": "github"}
        m.create_observable_gauge("esteira.board.throttle", unit="s",
                                  callbacks=[lambda o: [Observation(self.throttle, plat)]])
        m.create_observable_gauge("esteira.board.penalty", unit="h",
                                  callbacks=[lambda o: [Observation(self.penalty_h if time.time() < self.penalty_ate else 0, plat)]])
        m.create_observable_gauge("esteira.sync.circuit_breaker.estado", unit="1",
                                  callbacks=[lambda o: [Observation({"closed": 0, "half_open": 1, "open": 2}[self.breaker], plat)]])
        m.create_observable_gauge("esteira.sync.circuit_breaker.issues_abertas", unit="{issue}",
                                  callbacks=[lambda o: [Observation(self.issues_breaker, plat)]])

        def consumo(o):
            obs = []
            for periodo, (_, acc) in self.consumo.items():
                obs.append(Observation(round(acc, 2), {"esteira.ia.plataforma": "kiro-cli",
                                                       "esteira.consumo.periodo": periodo,
                                                       "esteira.consumo.unidade": "Créditos"}))
            return obs

        def limite(o):
            return [Observation(v, {"esteira.ia.plataforma": "kiro-cli", "esteira.consumo.periodo": p,
                                    "esteira.consumo.unidade": "Créditos"})
                    for p, v in self.cfg["limites"].items()]

        m.create_observable_gauge("esteira.consumo.acumulado", unit="1", callbacks=[consumo])
        m.create_observable_gauge("esteira.consumo.limite", unit="1", callbacks=[limite])
        m.create_observable_gauge("esteira.consumo.bloqueado", unit="1",
                                  callbacks=[lambda o: [Observation(int(self.bloqueado_limite), {"esteira.ia.plataforma": "kiro-cli"})]])

        def fila(o):
            por_board: dict[str, int] = {}
            for b in ("epicos", "historias", "tarefas"):
                por_board[b] = 0
            n = len(self.fila)
            return [Observation(n // 3 + (1 if i < n % 3 else 0),
                                {"esteira.board": b, "esteira.sync.evento": "change-up"})
                    for i, b in enumerate(por_board)]

        m.create_observable_gauge("esteira.sync.fila.profundidade", unit="{item}", callbacks=[fila])
        m.create_observable_gauge("esteira.sync.fila.idade_maxima", unit="s", callbacks=[
            lambda o: [Observation(round(time.time() - min(self.fila), 1) if self.fila else 0,
                                   {"esteira.board": "tarefas"})]])
        m.create_observable_gauge("esteira.sync.dead_letter.total", unit="{item}", callbacks=[
            lambda o: [Observation(v, {"esteira.sync.dead_letter.categoria": k}) for k, v in self.dead_letter.items()]])
        m.create_observable_gauge("esteira.sync.orfaos.total", unit="{arquivo}", callbacks=[
            lambda o: [Observation(self.orfaos, {"esteira.board": "tarefas"})]])

    def flush(self) -> None:
        self.lp.force_flush()
        self.tp.force_flush()

    def shutdown(self) -> None:
        self.lp.shutdown()
        self.tp.shutdown()
        self.mp.shutdown()

    # ── simulação ──────────────────────────────────────────────────────────
    def novo_id(self) -> str:
        self.proximo_id += 1
        return str(self.proximo_id)

    def ctx_issue(self, i: Issue) -> dict:
        return {"esteira.board.plataforma": "github", "esteira.board": i.board,
                "esteira.coluna": i.coluna, "esteira.issue": i.id, "esteira.issue.pai": i.pai or None}

    def upsert(self, i: Issue, ts: float, origem: str = "incremental") -> None:
        self.evento("esteira.issue.upsert", ts, {
            **self.ctx_issue(i), "esteira.issue.filhos": list(i.filhos) or None,
            "esteira.issue.bloqueada_por": None, "esteira.issue.bloqueia": None,
            "esteira.issue.estado": i.estado, "esteira.issue.arquivada": i.arquivada,
            "esteira.issue.origem": origem})

    def mover(self, i: Issue, para: str, ts: float) -> None:
        de = i.coluna
        i.coluna = para
        i.sem_avanco = 0
        i.ultima_sem_avanco = False
        if para == "done":
            i.estado = "closed"
        self.evento("esteira.issue.transicao", ts, {
            "esteira.board.plataforma": "github", "esteira.board": i.board,
            "esteira.issue": i.id, "esteira.coluna.de": de, "esteira.coluna.para": para})
        self.upsert(i, ts)
        self.sync_item(i, "change-up", ts)

    def criar(self, tipo: str, pai: Issue | None, ts: float) -> Issue:
        board = {"epico": "epicos", "historia": "historias", "tarefa": "tarefas"}[tipo]
        i = Issue(id=self.novo_id(), board=board, pai=pai.id if pai else "", tipo=tipo,
                  coluna="todo" if tipo != "tarefa" else "dev")
        self.issues[i.id] = i
        if pai:
            pai.filhos.append(i.id)
            self.upsert(pai, ts)
        self.upsert(i, ts)
        self.sync_item(i, "create-up", ts)
        return i

    def sync_item(self, i: Issue, evento: str, ts: float) -> None:
        r = self.rnd
        enfileirado = ts - r.uniform(0.5, 40)
        inicio = ts
        n_api = r.randint(1, 3)
        dur_total = 0.0
        desfecho = "aplicado"
        erro = None
        categoria = None
        span = self.tracer.start_span(f"esteira.sync.item {evento}", start_time=int(inicio * NS))
        ctx = trace.set_span_in_context(span)
        t = inicio
        for _ in range(n_api):
            op = r.choice(OPERACOES_API)
            d = max(0.05, r.lognormvariate(math.log(0.45), 0.6)) + self.throttle
            status = "ok"
            degradado = ts < self.degradado_ate
            p_erro = 0.45 if degradado else (0.02 if self.breaker == "closed" else 0.2)
            p_rl = 0.25 if degradado else 0.015
            x = r.random()
            if x < p_rl:
                status = "rate_limit"
            elif x < p_rl + p_erro:
                status = "erro"
            a = {"esteira.board.plataforma": "github", "esteira.board.operacao": op,
                 "esteira.board": i.board, "esteira.issue": i.id, "esteira.board.duracao_s": round(d, 3),
                 "esteira.board.status": status,
                 "error.type": {"erro": "BoardAccessError", "rate_limit": "RateLimit"}.get(status)}
            s2 = self.tracer.start_span(f"esteira.board.api {op}", context=ctx, start_time=int(t * NS),
                                        attributes={k: v for k, v in a.items() if v is not None})
            s2.end(end_time=int((t + d) * NS))
            self.evento("esteira.board.api", t + d, a, ctx=trace.set_span_in_context(s2))
            t += d
            dur_total += d
            if status == "rate_limit":
                self.throttle_hit(t)
            if status == "erro":
                erro = "BoardAccessError"
                self.erros_seguidos += 1
                if self.erros_seguidos >= 2 and self.breaker == "closed":
                    self.breaker_transicao("open", t)
            else:
                self.erros_seguidos = 0
        if erro:
            if r.random() < 0.25:
                desfecho = "dead_letter"
                categoria = r.choice(["definitivo", "transitorio_esgotado", "corrigivel_pelo_agente"])
                self.dead_letter[categoria] = self.dead_letter.get(categoria, 0) + 1
                if categoria == "corrigivel_pelo_agente":
                    self.evento("esteira.sync.escalacao", t, {"esteira.board": i.board, "esteira.issue": i.id,
                                                              "error.type": erro})
            else:
                desfecho = "reenfileirado"
                self.fila.append(time.time())
        elif self.fila and r.random() < 0.6:
            self.fila.pop(0)
        a = {"esteira.sync.uuid": uuid.uuid4().hex, "esteira.sync.evento": evento,
             "esteira.sync.fullsync": False, "esteira.board": i.board, "esteira.issue": i.id,
             "esteira.sync.tentativa": 1 if desfecho == "aplicado" else r.randint(1, 5),
             "esteira.sync.desfecho": desfecho, "esteira.sync.dead_letter.categoria": categoria,
             "esteira.sync.lag_s": round(t - enfileirado, 3), "esteira.sync.duracao_s": round(dur_total, 3),
             "error.type": erro, "esteira.erro.mensagem": "falha ao acessar o board (exemplo)" if erro else None}
        span.set_attributes({k: v for k, v in a.items() if v is not None})
        span.end(end_time=int(t * NS))
        self.evento("esteira.sync.item", t, a, ctx=ctx)
        # breaker: open → half_open → closed
        if self.breaker == "open" and t - self.breaker_desde > 900:
            self.breaker_transicao("half_open", t)
        elif self.breaker == "half_open" and not erro:
            self.breaker_transicao("closed", t)

    def breaker_transicao(self, novo: str, ts: float) -> None:
        self.evento("esteira.sync.circuit_breaker", ts, {
            "esteira.breaker.escopo": "plataforma", "esteira.board.plataforma": "github",
            "esteira.breaker.estado_anterior": self.breaker, "esteira.breaker.estado_novo": novo})
        self.breaker = novo
        self.breaker_desde = ts
        self.issues_breaker = 0 if novo == "closed" else self.rnd.randint(1, 4)

    def throttle_hit(self, ts: float) -> None:
        ant = self.throttle
        if ant >= 64:
            self.penalty_h = max(1, self.penalty_h * 2) if self.penalty_h else 1
            self.penalty_ate = ts + self.penalty_h * 3600
            self.evento("esteira.board.penalty", ts, {"esteira.board.plataforma": "github",
                                                       "esteira.board.penalty.estado": "ativo",
                                                       "esteira.board.penalty.horas": self.penalty_h,
                                                       "esteira.board.penalty.retorno_em": time.strftime(
                                                           "%Y-%m-%dT%H:%M:%S", time.localtime(self.penalty_ate))})
            return
        self.throttle = 1 if ant == 0 else min(ant * 2, 64)
        self.throttle_desde = ts
        self.evento("esteira.board.throttle", ts, {"esteira.board.plataforma": "github",
                                                    "esteira.board.throttle.valor_anterior_s": ant,
                                                    "esteira.board.throttle.valor_novo_s": self.throttle,
                                                    "esteira.board.throttle.motivo": "aumento"})

    def throttle_cooldown(self, ts: float) -> None:
        if self.throttle and ts - self.throttle_desde > 3600:
            ant = self.throttle
            self.throttle = 0 if ant == 1 else ant // 2
            self.throttle_desde = ts
            self.evento("esteira.board.throttle", ts, {"esteira.board.plataforma": "github",
                                                        "esteira.board.throttle.valor_anterior_s": ant,
                                                        "esteira.board.throttle.valor_novo_s": self.throttle,
                                                        "esteira.board.throttle.motivo": "cooldown"})
        if self.penalty_h and ts > self.penalty_ate:
            self.evento("esteira.board.penalty", ts, {"esteira.board.plataforma": "github",
                                                       "esteira.board.penalty.estado": "inativo",
                                                       "esteira.board.penalty.horas": 0})
            self.penalty_h = 0

    def periodos(self, ts: float) -> dict[str, str]:
        lt = time.localtime(ts)
        return {"diario": time.strftime("%Y-%m-%d", lt), "semanal": time.strftime("%Y-W%W", lt),
                "mensal": time.strftime("%Y-%m", lt)}

    def checar_limite(self, i: Issue, ts: float) -> bool:
        limites = self.cfg["limites"]
        chaves = self.periodos(ts)
        for p, chave in chaves.items():
            atual = self.consumo.get(p)
            if not atual or atual[0] != chave:
                if atual:
                    self.evento("esteira.consumo.limite", ts, {
                        "esteira.ia.plataforma": "kiro-cli", "esteira.consumo.periodo": p,
                        "esteira.consumo.tipo": "virada_periodo", "esteira.consumo.acumulado": round(atual[1], 2),
                        "esteira.consumo.limite": limites.get(p), "esteira.consumo.unidade": "Créditos"})
                    if self.bloqueado_limite:
                        self.bloqueado_limite = False
                        self.evento("esteira.consumo.limite", ts, {
                            "esteira.ia.plataforma": "kiro-cli", "esteira.consumo.periodo": p,
                            "esteira.consumo.tipo": "retomada", "esteira.consumo.unidade": "Créditos"})
                self.consumo[p] = (chave, 0.0)
        for p, lim in limites.items():
            if self.consumo[p][1] >= lim:
                if not self.bloqueado_limite:
                    self.bloqueado_limite = True
                    self.evento("esteira.consumo.limite", ts, {
                        "esteira.ia.plataforma": "kiro-cli", "esteira.consumo.periodo": p,
                        "esteira.consumo.tipo": "bloqueio", "esteira.consumo.acumulado": round(self.consumo[p][1], 2),
                        "esteira.consumo.limite": lim, "esteira.consumo.unidade": "Créditos"})
                if self.rnd.random() < 0.1:
                    self.evento("esteira.agente.admissao_negada", ts, {
                        **self.ctx_issue(i), "esteira.ia.plataforma": "kiro-cli",
                        "esteira.admissao.motivo": "limite_consumo", "esteira.consumo.periodo": p})
                return False
        return True

    def executar(self, i: Issue, agente_id: str, destino: str, fim: float) -> bool:
        """Roda uma execução e devolve se avançou."""
        r = self.rnd
        if fim < i.bloqueada_ate:
            if r.random() < 0.1:
                self.evento("esteira.agente.admissao_negada", fim, {
                    **self.ctx_issue(i), "esteira.ia.plataforma": "kiro-cli",
                    "esteira.admissao.motivo": "circuit_break"})
            return False
        if r.random() < 0.03:
            self.evento("esteira.agente.admissao_negada", fim, {
                **self.ctx_issue(i), "esteira.ia.plataforma": "kiro-cli", "esteira.admissao.motivo": "cooldown"})
            return False
        if not self.checar_limite(i, fim):
            return False

        nome, custo_m, dur_m, p_ok = AGENTES[agente_id]
        usa_tokens = self.cfg["tokens"] and agente_id == "testador"
        plataforma = "outro-cli" if usa_tokens else "kiro-cli"
        modelo = "modelo-exemplo-x" if usa_tokens else r.choices(MODELOS, weights=[0.7, 0.3])[0]
        fator = 0.45 if modelo == "claude-haiku-4.5" else 1.0
        x = r.random()
        if x < p_ok:
            resultado = "concluída"
        elif x < p_ok + 0.08:
            resultado = "falha terminal"
        elif x < p_ok + 0.13:
            resultado = "timeout"
        elif x < p_ok + 0.17:
            resultado = "interrompida"
        else:
            resultado = "desconhecida"
        timeout_s = 3600
        dur = timeout_s if resultado == "timeout" else max(20.0, r.lognormvariate(math.log(dur_m), 0.5))
        dur = min(dur, timeout_s)
        avancou = resultado == "concluída" and r.random() < 0.85
        repeticao = i.ultima_sem_avanco
        inicio = fim - dur
        disponivel = r.random() > 0.05
        if usa_tokens:
            valor, unidade = round(r.lognormvariate(math.log(60000), 0.5)), "Tokens"
        else:
            valor, unidade = round(max(0.1, r.lognormvariate(math.log(custo_m * fator), 0.55)) * dur / dur_m, 2), "Créditos"
        tentativas = 1 if r.random() < 0.9 else r.randint(2, 3)
        a = {**self.ctx_issue(i),
             "esteira.execucao.id": uuid.uuid4().hex, "esteira.ia.plataforma": plataforma,
             "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.id": agente_id, "gen_ai.agent.name": nome,
             "gen_ai.request.model": modelo, "esteira.coluna.destino": destino if avancou else i.coluna,
             "esteira.execucao.resultado": resultado, "esteira.execucao.avancou": avancou,
             "esteira.execucao.repeticao_sem_avanco": repeticao,
             "esteira.execucao.classe": {"concluída": "SUCEDIDO", "falha terminal": "FALHA", "timeout": "FALHA",
                                         "interrompida": "UNKNOWN_OUTCOME", "desconhecida": "UNKNOWN_OUTCOME"}[resultado],
             "esteira.execucao.origem": {"timeout": "timeout", "interrompida": "dispatch failure"}.get(resultado, "exit-code"),
             "esteira.execucao.tentativas": tentativas,
             "esteira.execucao.sessao": "retomada" if repeticao or r.random() < 0.2 else "nova",
             "esteira.execucao.inicio": round(inicio, 3), "esteira.execucao.fim": round(fim, 3),
             "esteira.execucao.duracao_s": round(dur, 1), "esteira.execucao.timeout_s": timeout_s,
             "esteira.consumo.disponivel": disponivel, "esteira.consumo.valor": valor if disponivel else None,
             "esteira.consumo.unidade": unidade, "esteira.consumo.origem": plataforma,
             "esteira.composicao.tokens_entrada": int(r.lognormvariate(math.log(9000 if agente_id != "desenvolvedor" else 16000), 0.35)),
             "esteira.composicao.caracteres_sempre_carregado": r.randint(18000, 26000)}
        span = self.tracer.start_span(f"invoke_agent {nome}", start_time=int(inicio * NS),
                                      kind=trace.SpanKind.INTERNAL,
                                      attributes={k: v for k, v in a.items() if v is not None})
        if resultado != "concluída":
            span.set_status(trace.Status(trace.StatusCode.ERROR, resultado))
        span.end(end_time=int(fim * NS))
        self.evento("esteira.agente.execucao", fim, a, ctx=trace.set_span_in_context(span),
                    sev=SeverityNumber.INFO if resultado == "concluída" else SeverityNumber.WARN)
        if disponivel and unidade == "Créditos":
            for p, (k, acc) in list(self.consumo.items()):
                self.consumo[p] = (k, acc + valor)

        if avancou:
            i.sem_avanco = 0
            i.ultima_sem_avanco = False
        else:
            i.sem_avanco += 1
            i.ultima_sem_avanco = True
            if i.sem_avanco >= 3:
                for passo in ("persisted", "labeled", "signaled"):
                    self.evento("esteira.agente.circuit_break", fim + 1, {
                        **self.ctx_issue(i), "esteira.circuit_break.contagem": i.sem_avanco,
                        "esteira.circuit_break.limite": 3, "esteira.circuit_break.janela_s": 86400,
                        "esteira.circuit_break.passo": passo})
                i.bloqueada_ate = fim + r.uniform(2, 8) * 3600
                i.sem_avanco = 0
        return avancou

    def candidatos(self, ts: float) -> list[Issue]:
        out = []
        for i in self.issues.values():
            if i.estado == "closed":
                continue
            # bloqueada por circuit break: quase nunca é escolhida (só para emitir admissão negada)
            if ts < i.bloqueada_ate and self.rnd.random() > 0.05:
                continue
            if i.tipo in ("epico", "historia") and i.coluna == "dev":
                filhos = [self.issues[f] for f in i.filhos if f in self.issues]
                if filhos and all(f.estado == "closed" for f in filhos):
                    out.append(i)
                continue
            out.append(i)
        return out

    def passo(self, ts: float) -> bool:
        """Um ciclo da pipe. Devolve se houve mudança."""
        r = self.rnd
        self.throttle_cooldown(ts)
        if ts > self.degradado_ate and r.random() < 0.006:
            self.degradado_ate = ts + r.uniform(40, 120) * 60
        abertos = [i for i in self.issues.values() if i.tipo == "epico" and i.estado == "open"]
        if len(abertos) < 2 or (len(abertos) < 5 and r.random() < 0.04):
            self.criar("epico", None, ts)
        cands = self.candidatos(ts)
        if not cands:
            return False
        # prioridade para o trabalho mais fundo (tarefas), como uma esteira real
        pesos = [{"tarefa": 4, "historia": 2, "epico": 1}[c.tipo] for c in cands]
        i = r.choices(cands, weights=pesos)[0]
        if i.coluna == "todo":
            self.mover(i, "planejamento", ts)
            return True
        if i.tipo in ("epico", "historia"):
            if i.coluna == "planejamento":
                if self.executar(i, "planejador", "dev", ts):
                    for _ in range(r.randint(2, 3) if i.tipo == "epico" else r.randint(2, 4)):
                        self.criar("historia" if i.tipo == "epico" else "tarefa", i, ts + 1)
                    self.mover(i, "dev", ts + 2)
            elif i.coluna == "dev":
                self.mover(i, "revisao", ts)
            elif i.coluna == "revisao":
                if self.executar(i, "revisor", "done", ts):
                    self.mover(i, "done", ts + 1)
            return True
        # tarefa: dev → testes → revisao → done (revisão pode devolver para dev)
        fluxo = {"dev": ("desenvolvedor", "testes"), "testes": ("testador", "revisao"),
                 "revisao": ("revisor", "done")}
        if i.coluna not in fluxo:
            return False
        agente, destino = fluxo[i.coluna]
        if self.executar(i, agente, destino, ts):
            if i.coluna == "revisao" and r.random() < 0.15:
                self.mover(i, "dev", ts + 1)       # retrabalho
            else:
                self.mover(i, destino, ts + 1)
        return True

    def ciclo(self, ts: float, mudou: bool, dormiu: float) -> None:
        self.evento("esteira.pipe.ciclo", ts, {"esteira.ciclo.duracao_s": round(self.rnd.uniform(0.3, 4.0), 2),
                                               "esteira.ciclo.houve_mudanca": mudou,
                                               "esteira.ciclo.dormiu_s": dormiu})
        if self.rnd.random() < 0.003:
            self.evento("esteira.pipe.incidente", ts, {
                "esteira.incidente.tipo": self.rnd.choice(["steering_reescrito", "snapshot_restaurado",
                                                           "arquivo_fantasma", "cross_board_bloqueado"]),
                "esteira.board": "tarefas"}, sev=SeverityNumber.WARN)
            self.orfaos += 1

    def ciclo_vida(self, fase: str, ts: float) -> None:
        self.evento("esteira.pipe.ciclo_vida", ts, {"esteira.pipe.fase": fase,
                                                    "vcs.ref.head.revision": "0000000exemplo"})

    def full_sync(self, ts: float) -> None:
        for i in self.issues.values():
            if not i.arquivada:
                self.upsert(i, ts, origem="full_sync")


def main() -> None:
    rnd = random.Random(SEED)
    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    marcador = ESTADO_DIR / "estado.json"
    estado = json.loads(marcador.read_text()) if marcador.exists() else {}
    base_id = estado.get("proximo_id", 1000)

    pipes = [Pipe(k, PIPES[k], random.Random(SEED + k), base_id + k * 100000) for k in range(min(N_PIPES, len(PIPES)))]
    log(f"{len(pipes)} pipe(s) → {ENDPOINT}")

    parar = {"v": False}

    def sigterm(*_):
        parar["v"] = True
    signal.signal(signal.SIGTERM, sigterm)
    signal.signal(signal.SIGINT, sigterm)

    agora = time.time()
    if not estado.get("historico_feito") and HISTORICO_DIAS > 0:
        for p in pipes:
            t = agora - HISTORICO_DIAS * 86400
            p.ciclo_vida("startup", t)
            ultimo_full = t
            n = 0
            while t < agora - 60 and not parar["v"]:
                mudou = p.passo(t)
                dormiu = 0 if mudou else 30
                p.ciclo(t, mudou, dormiu)
                if t - ultimo_full > 86400:
                    p.full_sync(t)
                    ultimo_full = t
                t += rnd.uniform(4, 14) * 60
                n += 1
                if n % 200 == 0:
                    p.flush()
            p.flush()
            log(f"histórico de {p.cfg['nome']}: {n} ciclos, {len(p.issues)} issues")
        estado["historico_feito"] = True
    for p in pipes:
        p.ciclo_vida("startup", time.time())
        p.full_sync(time.time())

    def salvar():
        estado["proximo_id"] = max(p.proximo_id for p in pipes) + 1
        marcador.write_text(json.dumps(estado))
    salvar()

    log("modo ao vivo")
    while not parar["v"]:
        for p in pipes:
            ts = time.time()
            mudou = p.passo(ts)
            p.ciclo(ts, mudou, 0 if mudou else INTERVALO)
        salvar()
        time.sleep(INTERVALO)

    for p in pipes:
        p.ciclo_vida("shutdown", time.time())
        p.shutdown()
    log("encerrado")


if __name__ == "__main__":
    main()
