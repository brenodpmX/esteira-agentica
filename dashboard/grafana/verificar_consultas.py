#!/usr/bin/env python3
"""Executa todas as consultas do dashboard contra o Grafana e relata erros.

Uso: GRAFANA_USER=admin GRAFANA_PASSWORD=... python3 grafana/verificar_consultas.py [pipe] [unidade]

Substitui as variáveis do dashboard por valores de teste e envia cada consulta a
/api/ds/query (o próprio plugin ClickHouse expande as macros $__timeFilter etc.).
Saída: uma linha por consulta com nº de linhas ou o erro. Código de saída 1 se
alguma consulta falhar. Só biblioteca padrão.
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = os.environ.get("GRAFANA_URL", "http://127.0.0.1:3000")
USER = os.environ.get("GRAFANA_USER", "admin")
SENHA = os.environ["GRAFANA_PASSWORD"]
DASH = Path(__file__).resolve().parent / "dashboards" / "esteira.json"


def sqlstring(v: str) -> str:
    return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"


def substituir(sql: str, vars_: dict) -> str:
    def rep(m):
        nome, fmt = m.group(1), m.group(2)
        v = vars_.get(nome, "")
        if fmt in ("sqlstring", "singlequote"):
            return sqlstring(v)
        if fmt == "percentencode":
            return v
        return v
    sql = re.sub(r"\$\{(\w+)(?::(\w+))?\}", rep, sql)
    return sql


def consultar(sql: str, fmt: int) -> tuple[bool, str]:
    corpo = {"from": "now-7d", "to": "now", "queries": [{
        "refId": "A", "datasource": {"type": "grafana-clickhouse-datasource", "uid": "esteira-clickhouse"},
        "rawSql": sql, "format": fmt, "editorType": "sql", "intervalMs": 3600000, "maxDataPoints": 500}]}
    auth = base64.b64encode(f"{USER}:{SENHA}".encode()).decode()
    req = urllib.request.Request(f"{URL}/api/ds/query", data=json.dumps(corpo).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read())["results"]["A"]
    except urllib.error.HTTPError as e:
        try:
            res = json.loads(e.read())["results"]["A"]
        except Exception:  # noqa: BLE001
            return False, f"HTTP {e.code}"
    if res.get("error"):
        return False, res["error"][:400]
    frames = res.get("frames", [])
    n = sum(len(f["data"]["values"][0]) if f.get("data", {}).get("values") else 0 for f in frames)
    return True, f"{n} linhas em {len(frames)} frame(s)"


def paineis(lista):
    for p in lista:
        yield p
        yield from paineis(p.get("panels", []))


def main():
    dash = json.loads(DASH.read_text(encoding="utf-8"))
    vars_ = {"pipe": sys.argv[1] if len(sys.argv) > 1 else "https://github.com/exemplo/loja-ficticia.git",
             "unidade": sys.argv[2] if len(sys.argv) > 2 else "Créditos",
             "board": "__all__", "coluna": "__all__", "agente": "__all__", "modelo": "__all__", "resultado": "__all__",
             "raiz": "", "issue": "", "n_barras": "30", "n_exec": "100", "a7_valor": "consumo", "trace": "0" * 32}
    falhas = 0
    alvos = []
    for p in paineis(dash["panels"]):
        for t in p.get("targets", []):
            alvos.append((p["title"] + ("" if t["refId"] == "A" else f" [{t['refId']}]"), t))
    for v in dash["templating"]["list"]:
        if v["type"] == "query":
            alvos.append((f"variável {v['name']}", {"rawSql": v["query"], "format": 1}))
    for a in dash["annotations"]["list"]:
        if "target" in a:
            alvos.append((f"anotação {a['name']}", a["target"]))
    for titulo, t in alvos:
        ok, msg = consultar(substituir(t["rawSql"], vars_), t.get("format", 1))
        falhas += not ok
        print(f"{'OK  ' if ok else 'ERRO'} {titulo}: {msg}")
    print(f"\n{len(alvos) - falhas}/{len(alvos)} consultas OK")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
