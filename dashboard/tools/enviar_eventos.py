"""Envia eventos de teste (Contrato de telemetria v1) para o dashboard.

Usa uma pipe própria (padrão `teste-manual`), que aparece numa aba separada.
Estado (issues criadas, próximo id) fica em /dados/manual.json para os comandos
poderem ser encadeados.

Comandos:
  cenario [--pausa S]                 épico → 2 histórias → 4 tarefas, com execuções
                                      espaçadas por S segundos (padrão 8) para ver a
                                      lista viva reordenar
  issue --board B [--pai ID]          cria uma issue (sai na lista viva sem execução)
  execucao --issue ID [--agente A] [--resultado R] [--consumo V] [--unidade U]
           [--duracao S] [--modelo M] [--nao-avancou] [--sem-consumo]
  mover --issue ID --para COLUNA      transição de coluna
  fechar --issue ID                   issue concluída (closed)
  bloqueio --issue ID                 trip de circuit break (status Bloqueada)
  throttle --valor S                  mudança de throttle do board
  breaker --estado closed|half_open|open
  listar                              issues conhecidas da pipe de teste
  limpar                              esquece o estado local (não apaga dados no banco)

Resultados válidos: concluída, "falha terminal", timeout, interrompida, desconhecida.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import uuid
from pathlib import Path

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://esteira-otlp:4318").rstrip("/")
PIPE_ID = os.environ.get("TESTE_PIPE_ID", "teste-manual")
PIPE_NOME = os.environ.get("TESTE_PIPE_NOME", "teste-manual")
ESTADO = Path(os.environ.get("GERADOR_ESTADO", "/dados")) / f"manual-{PIPE_ID.replace('/', '_')}.json"
NS = 1_000_000_000
RESULTADOS = ("concluída", "falha terminal", "timeout", "interrompida", "desconhecida")
AGENTES = {"planejador": "Planejador", "desenvolvedor": "Desenvolvedor",
           "testador": "Testador", "revisor": "Revisor"}

res = Resource.create({"service.name": "esteira-agentica", "service.version": "teste",
                       "service.instance.id": PIPE_ID, "esteira.pipe.nome": PIPE_NOME,
                       "deployment.environment.name": "teste", "esteira.contrato": 1})
_lp = LoggerProvider(resource=res)
_lp.add_log_record_processor(SimpleLogRecordProcessor(OTLPLogExporter(endpoint=f"{ENDPOINT}/v1/logs")))
_logger = _lp.get_logger("esteira.teste")
_tp = TracerProvider(resource=res)
_tp.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=f"{ENDPOINT}/v1/traces")))
_tracer = _tp.get_tracer("esteira.teste")


# ── estado local ─────────────────────────────────────────────────────────────
def carregar() -> dict:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text())
    return {"proximo_id": 1, "issues": {}}


def salvar(e: dict) -> None:
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(e, ensure_ascii=False, indent=1))


def issue_de(e: dict, iid: str) -> dict:
    i = e["issues"].get(str(iid))
    if not i:
        sys.exit(f"issue {iid} desconhecida; use `listar` ou crie com `issue`")
    return i


# ── emissão ──────────────────────────────────────────────────────────────────
def evento(nome: str, attrs: dict, ts: float | None = None, ctx=None) -> None:
    ts = ts or time.time()
    _logger.emit(timestamp=int(ts * NS), observed_timestamp=int(ts * NS), context=ctx, body=nome,
                 event_name=nome, attributes={k: v for k, v in attrs.items() if v is not None})


def ctx_issue(i: dict) -> dict:
    return {"esteira.board.plataforma": "github", "esteira.board": i["board"], "esteira.coluna": i["coluna"],
            "esteira.issue": i["id"], "esteira.issue.pai": i["pai"] or None}


def upsert(i: dict) -> None:
    evento("esteira.issue.upsert", {**ctx_issue(i), "esteira.issue.filhos": i["filhos"] or None,
                                    "esteira.issue.estado": i["estado"], "esteira.issue.arquivada": False,
                                    "esteira.issue.origem": "incremental"})


def criar(e: dict, board: str, pai: str | None, coluna: str = "todo") -> dict:
    iid = str(e["proximo_id"])
    e["proximo_id"] += 1
    i = {"id": iid, "board": board, "pai": pai or "", "coluna": coluna, "estado": "open", "filhos": []}
    e["issues"][iid] = i
    if pai:
        p = issue_de(e, pai)
        p["filhos"].append(iid)
        upsert(p)
    upsert(i)
    print(f"issue #{iid} criada em {board}" + (f" (pai #{pai})" if pai else ""))
    return i


def mover(i: dict, para: str) -> None:
    de, i["coluna"] = i["coluna"], para
    evento("esteira.issue.transicao", {"esteira.board.plataforma": "github", "esteira.board": i["board"],
                                       "esteira.issue": i["id"], "esteira.coluna.de": de, "esteira.coluna.para": para})
    upsert(i)
    print(f"#{i['id']}: {de} → {para}")


def executar(i: dict, agente: str = "desenvolvedor", resultado: str = "concluída", consumo: float | None = None,
             unidade: str = "Créditos", duracao: float | None = None, modelo: str = "claude-sonnet-4.5",
             avancou: bool | None = None, sem_consumo: bool = False) -> None:
    if resultado not in RESULTADOS:
        sys.exit(f"resultado inválido: {resultado}; válidos: {', '.join(RESULTADOS)}")
    consumo = round(random.uniform(3, 25), 2) if consumo is None else consumo
    duracao = random.uniform(120, 900) if duracao is None else duracao
    avancou = (resultado == "concluída") if avancou is None else avancou
    fim = time.time()
    a = {**ctx_issue(i), "esteira.execucao.id": uuid.uuid4().hex, "esteira.ia.plataforma": "kiro-cli",
         "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.id": agente,
         "gen_ai.agent.name": AGENTES.get(agente, agente), "gen_ai.request.model": modelo,
         "esteira.coluna.destino": i["coluna"], "esteira.execucao.resultado": resultado,
         "esteira.execucao.avancou": avancou, "esteira.execucao.repeticao_sem_avanco": False,
         "esteira.execucao.tentativas": 1, "esteira.execucao.sessao": "nova",
         "esteira.execucao.inicio": round(fim - duracao, 3), "esteira.execucao.fim": round(fim, 3),
         "esteira.execucao.duracao_s": round(duracao, 1), "esteira.execucao.timeout_s": 3600,
         "esteira.consumo.disponivel": not sem_consumo, "esteira.consumo.valor": None if sem_consumo else consumo,
         "esteira.consumo.unidade": unidade, "esteira.consumo.origem": "kiro-cli",
         "esteira.composicao.tokens_entrada": random.randint(6000, 18000)}
    span = _tracer.start_span(f"invoke_agent {a['gen_ai.agent.name']}", start_time=int((fim - duracao) * NS),
                              attributes={k: v for k, v in a.items() if v is not None})
    span.end(end_time=int(fim * NS))
    evento("esteira.agente.execucao", a, fim, ctx=trace.set_span_in_context(span))
    print(f"#{i['id']} execução {agente}: {resultado}, "
          f"{'sem consumo' if sem_consumo else f'{consumo} {unidade}'}, {duracao / 60:.1f} min")


def ciclo() -> None:
    evento("esteira.pipe.ciclo", {"esteira.ciclo.duracao_s": 1.0, "esteira.ciclo.houve_mudanca": True,
                                  "esteira.ciclo.dormiu_s": 0})


# ── comandos ─────────────────────────────────────────────────────────────────
def cmd_cenario(e: dict, pausa: float) -> None:
    def passo():
        ciclo()
        salvar(e)
        time.sleep(pausa)

    evento("esteira.pipe.ciclo_vida", {"esteira.pipe.fase": "startup"})
    ep = criar(e, "epicos", None)
    passo()
    mover(ep, "planejamento")
    executar(ep, "planejador", consumo=4.5, duracao=300)
    hs = [criar(e, "historias", ep["id"]) for _ in range(2)]
    mover(ep, "dev")
    passo()
    ts = []
    for h in hs:
        mover(h, "planejamento")
        executar(h, "planejador", consumo=3.2, duracao=240)
        ts += [criar(e, "tarefas", h["id"], "dev") for _ in range(2)]
        mover(h, "dev")
        passo()
    # tarefas: sucesso, falha, timeout e sem consumo, para ver as cores
    plano = [("concluída", False), ("falha terminal", False), ("timeout", False), ("concluída", True)]
    for t, (r, sem) in zip(ts, plano):
        executar(t, "desenvolvedor", resultado=r, duracao=3600 if r == "timeout" else None, sem_consumo=sem)
        if r == "concluída":
            mover(t, "testes")
        passo()
    # segunda rodada só na primeira tarefa: a árvore volta ao início da lista
    executar(ts[0], "testador", consumo=6.0, unidade="Créditos")
    mover(ts[0], "revisao")
    passo()
    executar(ts[0], "revisor", consumo=2.5)
    mover(ts[0], "done")
    ts[0]["estado"] = "closed"
    upsert(ts[0])
    ciclo()
    print(f"\ncenário pronto: árvore #{ep['id']} (filtro Pipe = {PIPE_NOME}).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cenario"); c.add_argument("--pausa", type=float, default=8)
    c = sub.add_parser("issue"); c.add_argument("--board", required=True); c.add_argument("--pai")
    c.add_argument("--coluna", default="todo")
    c = sub.add_parser("execucao"); c.add_argument("--issue", required=True)
    c.add_argument("--agente", default="desenvolvedor", choices=list(AGENTES))
    c.add_argument("--resultado", default="concluída"); c.add_argument("--consumo", type=float)
    c.add_argument("--unidade", default="Créditos"); c.add_argument("--duracao", type=float, help="segundos")
    c.add_argument("--modelo", default="claude-sonnet-4.5"); c.add_argument("--nao-avancou", action="store_true")
    c.add_argument("--sem-consumo", action="store_true")
    c = sub.add_parser("mover"); c.add_argument("--issue", required=True); c.add_argument("--para", required=True)
    c = sub.add_parser("fechar"); c.add_argument("--issue", required=True)
    c = sub.add_parser("bloqueio"); c.add_argument("--issue", required=True)
    c = sub.add_parser("throttle"); c.add_argument("--valor", type=int, required=True)
    c = sub.add_parser("breaker"); c.add_argument("--estado", required=True, choices=["closed", "half_open", "open"])
    sub.add_parser("listar"); sub.add_parser("limpar")
    a = ap.parse_args()

    e = carregar()
    if a.cmd == "cenario":
        cmd_cenario(e, a.pausa)
    elif a.cmd == "issue":
        criar(e, a.board, a.pai, a.coluna)
    elif a.cmd == "execucao":
        executar(issue_de(e, a.issue), a.agente, a.resultado, a.consumo, a.unidade, a.duracao, a.modelo,
                 False if a.nao_avancou else None, a.sem_consumo)
    elif a.cmd == "mover":
        mover(issue_de(e, a.issue), a.para)
    elif a.cmd == "fechar":
        i = issue_de(e, a.issue); i["estado"] = "closed"; upsert(i); print(f"#{i['id']} fechada")
    elif a.cmd == "bloqueio":
        i = issue_de(e, a.issue)
        for passo in ("persisted", "labeled", "signaled"):
            evento("esteira.agente.circuit_break", {**ctx_issue(i), "esteira.circuit_break.contagem": 3,
                                                    "esteira.circuit_break.limite": 3,
                                                    "esteira.circuit_break.janela_s": 86400,
                                                    "esteira.circuit_break.passo": passo})
        print(f"#{i['id']} bloqueada (circuit break)")
    elif a.cmd == "throttle":
        ant = e.get("throttle", 0); e["throttle"] = a.valor
        evento("esteira.board.throttle", {"esteira.board.plataforma": "github",
                                          "esteira.board.throttle.valor_anterior_s": ant,
                                          "esteira.board.throttle.valor_novo_s": a.valor,
                                          "esteira.board.throttle.motivo": "aumento" if a.valor > ant else "cooldown"})
        print(f"throttle {ant}s → {a.valor}s")
    elif a.cmd == "breaker":
        ant = e.get("breaker", "closed"); e["breaker"] = a.estado
        evento("esteira.sync.circuit_breaker", {"esteira.breaker.escopo": "plataforma",
                                                "esteira.board.plataforma": "github",
                                                "esteira.breaker.estado_anterior": ant,
                                                "esteira.breaker.estado_novo": a.estado})
        print(f"breaker {ant} → {a.estado}")
    elif a.cmd == "listar":
        for i in e["issues"].values():
            print(f"#{i['id']:>4} {i['board']:<10} {i['coluna']:<13} {i['estado']:<7} pai={i['pai'] or '-'}")
        return
    elif a.cmd == "limpar":
        ESTADO.unlink(missing_ok=True); print("estado local apagado"); return
    if a.cmd != "cenario":
        ciclo()
    salvar(e)
    _lp.shutdown(); _tp.shutdown()


if __name__ == "__main__":
    main()
