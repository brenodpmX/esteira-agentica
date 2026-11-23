"""Aplica as views SQL e sincroniza o dashboard.yml com a tabela esteira.dashboard_config.

Roda em laço: a cada CONFIG_SYNC_INTERVALO segundos relê o dashboard.yml e, se o
conteúdo mudou, regrava a tabela. As views são reaplicadas no arranque e sempre que
algum arquivo de /sql mudar. Mudança no dashboard.yml vale sem rebuild nem restart.
"""

import hashlib
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

CH_URL = os.environ.get("CLICKHOUSE_URL", "http://clickhouse:8123")
CH_USER = os.environ["CLICKHOUSE_USER"]
CH_PASSWORD = os.environ["CLICKHOUSE_PASSWORD"]
CONFIG_FILE = Path(os.environ.get("DASHBOARD_CONFIG", "/config/dashboard.yml"))
SQL_DIR = Path(os.environ.get("SQL_DIR", "/sql"))
INTERVALO = int(os.environ.get("CONFIG_SYNC_INTERVALO", "30"))

CHAVES = ("boards_raiz", "colunas_finais", "ordem_colunas")


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [config-sync] {msg}", flush=True)


def ch(query: str, data: bytes | None = None) -> str:
    params = {"database": "esteira"}
    if data is not None:
        params["query"] = query
        body = data
    else:
        body = query.encode("utf-8")
    req = urllib.request.Request(
        f"{CH_URL}/?{urllib.parse.urlencode(params)}", data=body, method="POST",
        headers={"X-ClickHouse-User": CH_USER, "X-ClickHouse-Key": CH_PASSWORD},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def tabelas_otel_prontas() -> bool:
    out = ch("SELECT count() FROM system.tables WHERE database='esteira' "
             "AND name IN ('otel_logs','otel_metrics_gauge','otel_traces')")
    return out.strip() == "3"


def _statements(texto: str) -> list[str]:
    linhas = [l for l in texto.splitlines() if not l.strip().startswith("--")]
    return [s.strip() for s in "\n".join(linhas).split(";") if s.strip()]


def aplicar_views() -> None:
    for arq in sorted(SQL_DIR.glob("*.sql")):
        for stmt in _statements(arq.read_text(encoding="utf-8")):
            ch(stmt)
    log(f"views aplicadas ({', '.join(a.name for a in sorted(SQL_DIR.glob('*.sql')))})")


def _lista(valor, caminho: str) -> list[str]:
    if valor is None:
        return []
    if not isinstance(valor, list) or not all(isinstance(v, (str, int)) for v in valor):
        raise ValueError(f"{caminho} deve ser lista de textos")
    return [str(v) for v in valor]


def carregar_config(texto: str) -> list[dict]:
    """Retorna linhas (pipe, boards_raiz, colunas_finais, ordem_colunas).

    pipe = '' representa o bloco `padrao`. Cada pipe herda do padrão as chaves
    que não declarar.
    """
    dados = yaml.safe_load(texto) or {}
    if not isinstance(dados, dict):
        raise ValueError("dashboard.yml deve ser um mapa")
    padrao_raw = dados.get("padrao") or {}
    padrao = {k: _lista(padrao_raw.get(k), f"padrao.{k}") for k in CHAVES}
    linhas = [{"pipe": "", **padrao}]
    for pipe, bloco in (dados.get("pipes") or {}).items():
        bloco = bloco or {}
        linha = {"pipe": str(pipe)}
        for k in CHAVES:
            linha[k] = _lista(bloco[k], f"pipes.{pipe}.{k}") if k in bloco else padrao[k]
        linhas.append(linha)
    return linhas


def gravar_config(linhas: list[dict]) -> None:
    import json
    payload = "\n".join(json.dumps(l, ensure_ascii=False) for l in linhas).encode("utf-8")
    ch("TRUNCATE TABLE IF EXISTS dashboard_config")
    ch("INSERT INTO dashboard_config (pipe, boards_raiz, colunas_finais, ordem_colunas) "
       "FORMAT JSONEachRow", payload)
    log(f"dashboard.yml aplicado: {len(linhas) - 1} pipe(s) configurada(s) + padrão")


def hash_sql() -> str:
    h = hashlib.sha256()
    for arq in sorted(SQL_DIR.glob("*.sql")):
        h.update(arq.name.encode())
        h.update(arq.read_bytes())
    return h.hexdigest()


def main() -> None:
    while True:
        try:
            ch("SELECT 1")
            break
        except (urllib.error.URLError, OSError) as exc:
            log(f"aguardando ClickHouse: {exc}")
            time.sleep(3)

    ch("CREATE TABLE IF NOT EXISTS dashboard_config ("
       "pipe String, boards_raiz Array(String), colunas_finais Array(String), "
       "ordem_colunas Array(String)) ENGINE = MergeTree ORDER BY pipe")
    # As tabelas otel_* são criadas pelo Collector no arranque (create_schema);
    # as views dependem delas.
    while not tabelas_otel_prontas():
        log("aguardando o Collector criar as tabelas otel_*")
        time.sleep(3)

    ultimo_sql = None
    ultimo_cfg = None
    while True:
        try:
            atual_sql = hash_sql()
            if atual_sql != ultimo_sql:
                aplicar_views()
                ultimo_sql = atual_sql
            texto = CONFIG_FILE.read_text(encoding="utf-8") if CONFIG_FILE.exists() else ""
            if texto != ultimo_cfg:
                gravar_config(carregar_config(texto))
                ultimo_cfg = texto
        except urllib.error.HTTPError as exc:
            log(f"erro do ClickHouse: {exc.read().decode('utf-8', 'replace')[:500]}")
        except (ValueError, yaml.YAMLError) as exc:
            log(f"dashboard.yml inválido, configuração anterior mantida: {exc}")
            ultimo_cfg = texto
        except Exception as exc:  # noqa: BLE001 - serviço de apoio, nunca morre
            log(f"falha: {exc.__class__.__name__}: {exc}")
        if os.environ.get("CONFIG_SYNC_UMA_VEZ") == "1":
            sys.exit(0)
        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
