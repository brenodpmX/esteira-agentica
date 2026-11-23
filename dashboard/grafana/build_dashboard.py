#!/usr/bin/env python3
"""Gera grafana/dashboards/esteira.json (dashboard como código).

Uso: python3 grafana/build_dashboard.py      (só biblioteca padrão)

O JSON gerado é versionado e provisionado pelo Grafana; editar pela UI não vale
(o provisionamento bloqueia). Para mudar um painel, mude este script ou o .js do
painel em grafana/echarts/ e rode de novo.
"""

import json
import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ECHARTS = AQUI / "echarts"
SAIDA = AQUI / "dashboards" / "esteira.json"

DS = {"type": "grafana-clickhouse-datasource", "uid": "esteira-clickhouse"}
UID = "esteira-pipes"

STATUS_COR = {
    "Concluída": "#2E9E44", "Em andamento": "#2F6FDB", "Falha": "#D93025",
    "Timeout": "#F28C28", "Interrompida": "#E8C21B", "Bloqueada": "#8E44AD",
    "Desconhecida": "#8A8A8A", "Sem execução": "#2F6FDB",
}
STATUS_EXEC = ["Concluída", "Falha", "Timeout", "Interrompida", "Desconhecida"]
RESULTADO_STATUS = {"concluída": "Concluída", "falha terminal": "Falha", "timeout": "Timeout",
                    "interrompida": "Interrompida", "desconhecida": "Desconhecida"}

# ── Fragmentos SQL ───────────────────────────────────────────────────────────
PIPE = "pipe = ${pipe:sqlstring}"
UNI = "${unidade:sqlstring}"


def multi(var: str, coluna: str) -> str:
    """Filtro de variável múltipla com 'Todos' = '__all__'."""
    return f"('__all__' IN (${{{var}:singlequote}}) OR {coluna} IN (${{{var}:singlequote}}))"


EXEC_F = " AND ".join([
    PIPE, "$__timeFilter(fim)", multi("board", "board"), multi("coluna", "coluna"),
    multi("agente", "agente"), multi("modelo", "modelo"), multi("resultado", "resultado"),
])
EXEC_F_SEM_TEMPO = EXEC_F.replace(" AND $__timeFilter(fim)", "")
EV_F = f"{PIPE} AND $__timeFilter(ts)"
CONSUMO_UNI = f"unidade = {UNI}"

# ── Construção ───────────────────────────────────────────────────────────────
_id = [0]


def nid() -> int:
    _id[0] += 1
    return _id[0]


def alvo(sql: str, fmt: int = 1, ref: str = "A") -> dict:
    """fmt: 0 = série temporal (longo → largo pelo plugin), 1 = tabela."""
    return {"datasource": DS, "editorType": "sql", "format": fmt, "queryType": "table" if fmt == 1 else "timeseries",
            "rawSql": " ".join(l.strip() for l in sql.strip().splitlines()), "refId": ref,
            "pluginVersion": "4.23.5"}


def painel(tipo: str, titulo: str, w: int, h: int, alvos, descricao: str = "", opcoes=None,
           defaults=None, overrides=None, transformacoes=None, links=None) -> dict:
    p = {"id": nid(), "type": tipo, "title": titulo, "description": descricao, "datasource": DS,
         "gridPos": {"w": w, "h": h}, "targets": alvos if isinstance(alvos, list) else [alvos],
         "options": opcoes or {},
         "fieldConfig": {"defaults": defaults or {}, "overrides": overrides or []}}
    if tipo in ("timeseries", "state-timeline") and any(t.get("format") == 0 for t in p["targets"]):
        p["fieldConfig"]["defaults"].setdefault("displayName", "${__field.labels.__values}")
    if transformacoes:
        p["transformations"] = transformacoes
    if links:
        p["links"] = links
    return p


def echarts(titulo: str, w: int, h: int, sql: str, js: str, descricao: str = "") -> dict:
    codigo = (ECHARTS / "comum.js").read_text(encoding="utf-8") + "\n" + (ECHARTS / js).read_text(encoding="utf-8")
    return painel("volkovlabs-echarts-panel", titulo, w, h, alvo(sql), descricao, opcoes={
        "editorMode": "code", "renderer": "canvas", "map": "none", "getOption": codigo,
        "editor": {"format": "auto", "height": 600},
        "themeEditor": {"name": "default", "config": "{}"},
    })


def cor_fixa(nome: str, cor: str) -> dict:
    return {"matcher": {"id": "byName", "options": nome},
            "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": cor}}]}


def cores_status(nomes=STATUS_EXEC) -> list:
    return [cor_fixa(n, STATUS_COR[n]) for n in nomes]


def serie_tempo(estilo: str = "line", empilhar: str = "none", unidade: str = "short", **extra) -> dict:
    custom = {"drawStyle": estilo, "lineWidth": 2, "fillOpacity": 70 if estilo == "bars" else 10,
              "spanNulls": False, "showPoints": "never", "stacking": {"mode": empilhar, "group": "A"},
              "axisPlacement": "auto", "barAlignment": 0}
    custom.update(extra)
    return {"custom": custom, "unit": unidade, "color": {"mode": "palette-classic-by-name"}}


OPC_TEMPO = {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
             "tooltip": {"mode": "multi", "sort": "desc"}}


def barras(titulo, w, h, sql, descricao="", horizontal=True, empilhar="normal", unidade="short",
           overrides=None, x_campo=None, mostrar_valor="never") -> dict:
    return painel("barchart", titulo, w, h, alvo(sql), descricao, opcoes={
        "orientation": "horizontal" if horizontal else "vertical", "stacking": empilhar,
        "showValue": mostrar_valor, "groupWidth": 0.75, "barWidth": 0.9, "xField": x_campo,
        "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
        "tooltip": {"mode": "multi", "sort": "none"}, "xTickLabelRotation": 0, "fullHighlight": False,
    }, defaults={"unit": "percentunit" if empilhar == "percent" else unidade, "color": {"mode": "palette-classic-by-name"},
                 "custom": {"fillOpacity": 85, "lineWidth": 0, "gradientMode": "none"}},
        overrides=overrides or [])


def stat(titulo, w, h, sql, descricao="", unidade="short", fmt=1, calc="lastNotNull", cor="value",
         grafico="none", thresholds=None, mapeamentos=None, decimais=None, valores=False, links=None,
         texto="auto", defaults_extra=None) -> dict:
    d = {"unit": unidade, "mappings": mapeamentos or [], "color": {"mode": "thresholds"},
         "thresholds": {"mode": "absolute", "steps": thresholds or [{"color": "#5794F2", "value": None}]}}
    if decimais is not None:
        d["decimals"] = decimais
    if defaults_extra:
        d.update(defaults_extra)
    return painel("stat", titulo, w, h, alvo(sql, fmt), descricao, opcoes={
        "reduceOptions": {"calcs": [calc], "fields": "/.*/" if texto == "value" else "", "values": valores},
        "colorMode": cor, "graphMode": grafico, "justifyMode": "auto", "textMode": texto,
        "orientation": "auto", "wideLayout": True, "showPercentChange": False,
    }, defaults=d, links=links)


def linha(titulo: str, colapsada: bool = False) -> dict:
    return {"id": nid(), "type": "row", "title": titulo, "collapsed": colapsada, "gridPos": {"w": 24, "h": 1},
            "panels": []}


# ═════════════════════════════════════════════════════════════════════════════
# Painéis
# ═════════════════════════════════════════════════════════════════════════════

def aba_pipes():
    sql = f"""
    SELECT pipe, if(pipe = ${{pipe:sqlstring}}, concat('▶ ', pipe_nome), pipe_nome) AS nome,
           (SELECT count() FROM v_execucoes e WHERE e.pipe = p.pipe AND $__timeFilter(e.fim)) AS execucoes
    FROM v_pipes p WHERE $__timeFilter(ultima_atividade) OR pipe = ${{pipe:sqlstring}}
    ORDER BY ultima_atividade DESC"""
    return stat("Pipes", 24, 3, sql, "Uma aba por pipe (service.instance.id). Clique para trocar. Valor = execuções no período.",
                valores=True, cor="background", texto="value_and_name") | {"fieldConfig": {"defaults": {
                    "displayName": "${__data.fields.nome}", "unit": "none",
                    "color": {"mode": "fixed", "fixedColor": "#2B3A55"},
                    "links": [{"title": "Abrir aba da pipe",
                               "url": f"/d/{UID}/esteira?var-pipe=${{__data.fields.pipe:percentencode}}&var-unidade=&${{__url_time_range}}"}],
                }, "overrides": [{"matcher": {"id": "byName", "options": "pipe"},
                                  "properties": [{"id": "custom.hidden", "value": True}]}]}}


def topo():
    ps = []
    metr = lambda m: f"""argMaxIf(valor, ts, metrica = '{m}' AND a['esteira.consumo.periodo'] = p)"""
    sql_pct = f"""
    SELECT
      100 * {metr('esteira.consumo.acumulado').replace('p)', "'diario')")} / nullIf({metr('esteira.consumo.limite').replace('p)', "'diario')")}, 0) AS `Dia`,
      100 * {metr('esteira.consumo.acumulado').replace('p)', "'semanal')")} / nullIf({metr('esteira.consumo.limite').replace('p)', "'semanal')")}, 0) AS `Semana`,
      100 * {metr('esteira.consumo.acumulado').replace('p)', "'mensal')")} / nullIf({metr('esteira.consumo.limite').replace('p)', "'mensal')")}, 0) AS `Mês`
    FROM v_metricas WHERE {PIPE} AND a['esteira.consumo.unidade'] = {UNI} AND ts > now() - INTERVAL 1 HOUR"""
    ps.append(painel("gauge", "Consumo × limite", 6, 5, alvo(sql_pct),
                     "Acumulado do período corrente sobre o limite configurado (métricas esteira.consumo.*). Sem limite: sem valor.",
                     opcoes={"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                             "showThresholdMarkers": True, "showThresholdLabels": False, "minVizHeight": 75},
                     defaults={"unit": "percent", "min": 0, "max": 100, "decimals": 0, "noValue": "sem limite",
                               "color": {"mode": "thresholds"},
                               "thresholds": {"mode": "absolute", "steps": [
                                   {"color": "#2E9E44", "value": None}, {"color": "#E8C21B", "value": 70},
                                   {"color": "#D93025", "value": 90}]}}))
    sql_abs = f"""
    SELECT {metr('esteira.consumo.acumulado').replace('p)', "'diario')")} AS `Dia`,
           {metr('esteira.consumo.acumulado').replace('p)', "'semanal')")} AS `Semana`,
           {metr('esteira.consumo.acumulado').replace('p)', "'mensal')")} AS `Mês`
    FROM v_metricas WHERE {PIPE} AND a['esteira.consumo.unidade'] = {UNI} AND ts > now() - INTERVAL 1 HOUR"""
    ps.append(stat("Acumulado (${unidade})", 4, 5, sql_abs, "Valor absoluto do período corrente.", decimais=0))
    sql_exec = f"SELECT $__timeInterval(fim) AS time, count() AS `Execuções` FROM v_execucoes WHERE {EXEC_F} GROUP BY time ORDER BY time"
    ps.append(stat("Execuções", 3, 5, sql_exec, "Execuções de agente no período.", fmt=0, calc="sum", grafico="area"))
    taxa = lambda expr, nome: f"SELECT {expr} AS `{nome}` FROM v_execucoes WHERE {EXEC_F}"
    ps.append(stat("Sucesso", 3, 5, taxa("100 * countIf(resultado = 'concluída') / nullIf(count(), 0)", "Sucesso"),
                   "Execuções com resultado concluída / total.", unidade="percent", decimais=0,
                   thresholds=[{"color": "#D93025", "value": None}, {"color": "#E8C21B", "value": 70}, {"color": "#2E9E44", "value": 85}]))
    ps.append(stat("Avanço", 3, 5, taxa("100 * countIf(avancou) / nullIf(count(), 0)", "Avanço"),
                   "Execuções que avançaram a issue / total.", unidade="percent", decimais=0,
                   thresholds=[{"color": "#D93025", "value": None}, {"color": "#E8C21B", "value": 60}, {"color": "#2E9E44", "value": 75}]))
    ps.append(stat("Custo/avanço", 3, 5,
                   taxa(f"sumIf(consumo, {CONSUMO_UNI}) / nullIf(countIf(avancou), 0)", "Custo por avanço"),
                   "Consumo na unidade selecionada / execuções que avançaram.", decimais=1))
    sql_viva = f"""
    SELECT if(dateDiff('second', max(ts), now()) > greatest(180, 3 * maxIf(toFloat64OrZero(a['esteira.ciclo.dormiu_s']), ts > now() - INTERVAL 1 DAY)),
              'Parada', 'Viva') AS `Estado`,
           dateDiff('second', max(ts), now()) AS `Último ciclo`
    FROM v_eventos WHERE {PIPE} AND evento = 'esteira.pipe.ciclo' AND ts > now() - INTERVAL 30 DAY"""
    p = stat("Pipe", 2, 5, sql_viva, "Parada = último ciclo há mais de 3× o maior sono observado (mínimo 3 min).",
             cor="background", texto="value")
    p["fieldConfig"]["overrides"] = [
        {"matcher": {"id": "byName", "options": "Último ciclo"}, "properties": [{"id": "custom.hidden", "value": True}]}]
    p["fieldConfig"]["defaults"]["mappings"] = [{"type": "value", "options": {
        "Viva": {"color": "#2E9E44", "index": 0}, "Parada": {"color": "#D93025", "index": 1}}}]
    p["options"]["reduceOptions"]["fields"] = "/^Estado$/"
    ps.append(p)

    sql_fila = f"""
    SELECT sumIf(v, m = 'esteira.sync.fila.profundidade') AS `Fila`,
           maxIf(v, m = 'esteira.sync.fila.idade_maxima') AS `Idade máxima`,
           sumIf(v, m = 'esteira.sync.dead_letter.total') AS `Dead-letter`
    FROM (SELECT metrica AS m, a, argMax(valor, ts) AS v FROM v_metricas
          WHERE {PIPE} AND ts > now() - INTERVAL 1 HOUR
            AND metrica IN ('esteira.sync.fila.profundidade', 'esteira.sync.fila.idade_maxima', 'esteira.sync.dead_letter.total')
          GROUP BY m, a)"""
    p = stat("Fila e dead-letter", 24, 3, sql_fila, "Estado atual (métricas esteira.sync.*).", texto="value_and_name")
    p["fieldConfig"]["overrides"] = [
        {"matcher": {"id": "byName", "options": "Idade máxima"}, "properties": [{"id": "unit", "value": "s"}]},
        {"matcher": {"id": "byName", "options": "Dead-letter"}, "properties": [
            {"id": "thresholds", "value": {"mode": "absolute", "steps": [{"color": "#2E9E44", "value": None}, {"color": "#D93025", "value": 1}]}}]}]
    ps.append(p)
    return ps


def principais():
    lista_arvore = f"v_lista_arvore(unidade = {UNI})"
    sql_g1 = f"""
    WITH barras AS (
      SELECT raiz, any(ultima_atividade) AS ua FROM {lista_arvore}
      WHERE {PIPE} AND $__timeFilter(ultima_atividade) AND {multi('board', 'raiz_board')}
        AND (${{raiz:sqlstring}} = '' OR raiz = ${{raiz:sqlstring}})
      GROUP BY raiz ORDER BY ua DESC LIMIT toUInt32OrDefault(${{n_barras:sqlstring}}, toUInt32(30)))
    SELECT l.raiz AS raiz, l.raiz_board AS raiz_board, l.nivel AS nivel, coalesce(l.consumo, 0) AS consumo,
           l.n_exec AS n_exec, l.n_sem_consumo AS n_sem_consumo, l.n_outra_unidade AS n_outra_unidade,
           l.n_issues AS n_issues, l.tempo_s AS tempo_s, l.tempo_total_s AS tempo_total_s,
           coalesce(l.consumo_total, 0) AS consumo_total, l.n_exec_total AS n_exec_total, l.status AS status,
           l.ultima_atividade AS ultima_atividade, l.criada_em AS criada_em
    FROM {lista_arvore} AS l INNER JOIN barras AS b ON b.raiz = l.raiz
    WHERE l.{PIPE}
    ORDER BY l.ultima_atividade DESC, l.nivel"""
    g1 = echarts("Custo por árvore", 24, 11, sql_g1, "g1_custo_arvore.js",
                 "Lista viva: uma barra por issue raiz (boards_raiz no dashboard.yml), criada assim que a raiz nasce. "
                 "Cada pilha é um nível (raiz, filhas, netas…); cada execução da árvore soma na barra e a traz para a esquerda. "
                 "Cor = status atual da árvore. Linha = tempo de agente acumulado. O período escolhe quais barras entram; "
                 "o tamanho é sempre o total acumulado. Clique filtra a raiz.")
    sql_g11 = f"""
    SELECT issue, board, coluna, coalesce(consumo, 0) AS consumo, tempo_s, n_exec, n_sem_consumo, status,
           ultima_atividade, criada_em
    FROM v_lista_issue(unidade = {UNI})
    WHERE {PIPE} AND $__timeFilter(ultima_atividade) AND (${{issue:sqlstring}} = '' OR issue = ${{issue:sqlstring}})
    ORDER BY ultima_atividade DESC LIMIT toUInt32OrDefault(${{n_barras:sqlstring}}, toUInt32(30))"""
    g11 = echarts("Custo por issue (todos os boards)", 12, 10, sql_g11, "g11_custo_issue.js",
                  "Lista viva por issue de qualquer board, só com as execuções da própria issue. "
                  "Ignora o filtro de board. Clique filtra a issue no gráfico de execuções.")
    sql_g2 = f"""
    SELECT fim, issue, board, coluna, agente, modelo, resultado, avancou, repeticao_sem_avanco, consumo_disponivel,
           consumo, unidade, duracao_s, tentativas, sessao, tokens_entrada
    FROM v_execucoes
    WHERE {EXEC_F} AND ({CONSUMO_UNI} OR NOT consumo_disponivel)
      AND (${{issue:sqlstring}} = '' OR issue = ${{issue:sqlstring}})
      AND (${{raiz:sqlstring}} = '' OR issue IN (SELECT issue FROM v_arvore WHERE {PIPE} AND raiz = ${{raiz:sqlstring}}))
    ORDER BY fim DESC LIMIT toUInt32OrDefault(${{n_exec:sqlstring}}, toUInt32(100))"""
    g2 = echarts("Custo por execução", 12, 10, sql_g2, "g2_custo_execucao.js",
                 "Uma barra por execução (mais recente à esquerda). Cor = resultado; borda tracejada = não avançou; "
                 "barra vazada = consumo não informado. Linha = duração.")
    return [g1, g11, g2]


def consumo():
    ps = []
    sql_g3 = f"""
    SELECT $__timeInterval(ts) AS time, concat(a['esteira.consumo.periodo'], if(metrica = 'esteira.consumo.limite', ' limite', ' acumulado')) AS serie,
           max(valor) AS v
    FROM v_metricas
    WHERE {PIPE} AND $__timeFilter(ts) AND metrica IN ('esteira.consumo.acumulado', 'esteira.consumo.limite')
      AND a['esteira.consumo.unidade'] = {UNI}
    GROUP BY time, serie ORDER BY time"""
    d = serie_tempo()
    ps.append(painel("timeseries", "Acumulado × limite", 9, 8, alvo(sql_g3, 0),
                     "Acumulado do período corrente (diário, semanal, mensal) e o limite (tracejado).",
                     opcoes=OPC_TEMPO, defaults=d,
                     overrides=[{"matcher": {"id": "byRegexp", "options": ".*limite"}, "properties": [
                         {"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 10]}},
                         {"id": "custom.fillOpacity", "value": 0}]}]))
    sql_proj = f"""
    WITH ult AS (
      SELECT a['esteira.consumo.periodo'] AS p, argMaxIf(valor, ts, metrica = 'esteira.consumo.acumulado') AS acc,
             argMaxIf(valor, ts, metrica = 'esteira.consumo.limite') AS lim
      FROM v_metricas WHERE {PIPE} AND a['esteira.consumo.unidade'] = {UNI} AND ts > now() - INTERVAL 1 HOUR GROUP BY p),
    agora AS (SELECT toDateTime(now(), 'America/Sao_Paulo') AS n)
    SELECT
      anyIf(100 * acc / ((dateDiff('second', toStartOfDay(n), n) + 1) / 86400) / nullIf(lim, 0), p = 'diario') AS `Dia`,
      anyIf(100 * acc / ((dateDiff('second', toMonday(n), n) + 1) / 604800) / nullIf(lim, 0), p = 'semanal') AS `Semana`,
      anyIf(100 * acc / ((dateDiff('second', toStartOfMonth(n), n) + 1) / (toDayOfMonth(toLastDayOfMonth(n)) * 86400)) / nullIf(lim, 0), p = 'mensal') AS `Mês`
    FROM ult CROSS JOIN agora"""
    ps.append(stat("Projeção", 3, 8, sql_proj,
                   "Projeção linear do acumulado até o fim do período de calendário, em % do limite. "
                   "Aproximação: usa calendário (dia, semana de segunda, mês), não o dia de reset configurado.",
                   unidade="percent", decimais=0,
                   thresholds=[{"color": "#2E9E44", "value": None}, {"color": "#E8C21B", "value": 90}, {"color": "#D93025", "value": 100}]))
    cols = ", ".join(f"sumIf(consumo, esteira_status_execucao(resultado) = '{s}') AS `{s}`" for s in STATUS_EXEC)
    ps.append(barras("Consumo por coluna", 6, 8,
                     f"SELECT coluna, {cols} FROM v_execucoes WHERE {EXEC_F} AND {CONSUMO_UNI} GROUP BY coluna ORDER BY sum(consumo) DESC",
                     "Consumo (unidade selecionada) por coluna, empilhado pelo resultado.", overrides=cores_status()))
    sql_g6 = f"SELECT toStartOfDay(fim) AS time, modelo, sum(consumo) AS v FROM v_execucoes WHERE {EXEC_F} AND {CONSUMO_UNI} GROUP BY time, modelo ORDER BY time"
    ps.append(painel("timeseries", "Consumo diário por modelo", 6, 8, alvo(sql_g6, 0), "", opcoes=OPC_TEMPO,
                     defaults=serie_tempo("bars", "normal")))
    return ps


def resultados():
    sql_g8 = f"SELECT toStartOfDay(fim) AS time, esteira_status_execucao(resultado) AS s, count() AS n FROM v_execucoes WHERE {EXEC_F} GROUP BY time, s ORDER BY time"
    g8 = painel("timeseries", "Resultados por dia", 12, 8, alvo(sql_g8, 0), "Proporção dos resultados de execução por dia.",
                opcoes=OPC_TEMPO, defaults=serie_tempo("bars", "percent", "percentunit"), overrides=cores_status())
    sql_g9 = f"""SELECT toStartOfDay(ts) AS time, a['esteira.admissao.motivo'] AS motivo, count() AS n FROM v_eventos
    WHERE {EV_F} AND evento = 'esteira.agente.admissao_negada' AND {multi('board', "a['esteira.board']")}
    GROUP BY time, motivo ORDER BY time"""
    g9 = painel("timeseries", "Admissões negadas", 12, 8, alvo(sql_g9, 0),
                "Execuções não despachadas, por motivo (demanda reprimida).", opcoes=OPC_TEMPO,
                defaults=serie_tempo("bars", "normal"))
    return [g8, g9]


def agentes():
    ps = []
    base = f"FROM v_execucoes WHERE {EXEC_F}"
    ps.append(stat("Agentes ativos", 4, 4, f"SELECT uniqExact(agente) AS `Agentes` {base}", "Agentes com execução no período."))
    ps.append(stat("Mais consome", 6, 4, f"""
        SELECT concat(agente, ' — ', toString(round(100 * c / nullIf(sum(c) OVER (), 0))), '%') AS `Agente`
        FROM (SELECT agente, sumIf(consumo, {CONSUMO_UNI}) AS c {base} GROUP BY agente) ORDER BY c DESC LIMIT 1""",
                   "Agente com maior consumo e % do total.", texto="value"))
    ps.append(stat("Maior taxa de falha", 7, 4, f"""
        SELECT concat(agente, ' — ', toString(round(100 * f / n)), '%') AS `Agente`
        FROM (SELECT agente, countIf(resultado != 'concluída') AS f, count() AS n {base} GROUP BY agente HAVING n >= 5)
        ORDER BY f / n DESC LIMIT 1""", "Mínimo de 5 execuções no período para entrar.", texto="value",
                   thresholds=[{"color": "#D93025", "value": None}]))
    ps.append(stat("Menor taxa de avanço", 7, 4, f"""
        SELECT concat(agente, ' — ', toString(round(100 * a / n)), '%') AS `Agente`
        FROM (SELECT agente, countIf(avancou) AS a, count() AS n {base} GROUP BY agente HAVING n >= 5)
        ORDER BY a / n ASC LIMIT 1""", "Mínimo de 5 execuções no período para entrar.", texto="value",
                   thresholds=[{"color": "#F28C28", "value": None}]))

    anterior = EXEC_F.replace("$__timeFilter(fim)",
                              "fim >= $__fromTime - ($__toTime - $__fromTime) AND fim < $__fromTime")
    sql_ta = f"""
    WITH atual AS (
      SELECT agente, count() AS n, sumIf(consumo, {CONSUMO_UNI}) AS c,
             quantileIf(0.5)(consumo, {CONSUMO_UNI}) AS c_p50, quantileIf(0.95)(consumo, {CONSUMO_UNI}) AS c_p95,
             countIf(resultado = 'concluída') / n AS sucesso, countIf(avancou) / n AS avanco,
             countIf(repeticao_sem_avanco) / n AS repeticao,
             quantile(0.5)(duracao_s) AS d_p50, quantile(0.95)(duracao_s) AS d_p95,
             countIf(resultado = 'timeout') AS timeouts {base} GROUP BY agente),
    ant AS (
      SELECT agente, sumIf(consumo, {CONSUMO_UNI}) AS c, countIf(resultado = 'concluída') / count() AS sucesso
      FROM v_execucoes WHERE {anterior} GROUP BY agente)
    SELECT atual.agente AS agente, atual.n AS `Execuções`, atual.c AS `Consumo`,
           atual.c / nullIf(sum(atual.c) OVER (), 0) AS `% do total`,
           atual.c / atual.n AS `Custo médio`,
           atual.c_p95 AS `Custo p95`, atual.sucesso AS `Sucesso`, atual.avanco AS `Avanço`,
           atual.repeticao AS `Repetição sem avanço`, atual.d_p50 AS `Duração p50`, atual.d_p95 AS `Duração p95`,
           atual.timeouts AS `Timeouts`,
           if(ant.c > 0, atual.c / ant.c - 1, NULL) AS `Δ consumo`,
           if(ant.agente != '', atual.sucesso - ant.sucesso, NULL) AS `Δ sucesso`
    FROM atual LEFT JOIN ant ON ant.agente = atual.agente
    ORDER BY `Consumo` DESC"""
    sql_spark = f"SELECT toStartOfDay(fim) AS time, agente, sumIf(consumo, {CONSUMO_UNI}) AS v {base} GROUP BY time, agente ORDER BY time"
    pct = lambda n: {"matcher": {"id": "byName", "options": n}, "properties": [{"id": "unit", "value": "percentunit"}, {"id": "decimals", "value": 0}]}
    dec = lambda n: {"matcher": {"id": "byName", "options": n}, "properties": [{"id": "decimals", "value": 1}]}
    seg = lambda n: {"matcher": {"id": "byName", "options": n}, "properties": [{"id": "unit", "value": "s"}, {"id": "decimals", "value": 0}]}
    delta = lambda n, invertido: {"matcher": {"id": "byName", "options": n}, "properties": [
        {"id": "unit", "value": "percentunit"}, {"id": "decimals", "value": 0},
        {"id": "custom.cellOptions", "value": {"type": "color-text"}},
        {"id": "thresholds", "value": {"mode": "absolute", "steps": [
            {"color": "#2E9E44" if invertido else "#D93025", "value": None},
            {"color": "#8A8A8A", "value": -0.0001},
            {"color": "#D93025" if invertido else "#2E9E44", "value": 0.0001}]}}]}
    ta = painel("table", "Placar dos agentes", 24, 8, [alvo(sql_ta), alvo(sql_spark, 0, "B")],
                "Comparação no período; Δ = variação contra o período anterior de mesmo tamanho. "
                "Tendência = consumo diário. Clique no agente para filtrar a aba.",
                opcoes={"showHeader": True, "cellHeight": "sm", "footer": {"show": False},
                        "sortBy": [{"displayName": "Consumo", "desc": True}]},
                defaults={"custom": {"align": "auto", "cellOptions": {"type": "auto"}, "inspect": False}},
                overrides=[dec("Consumo"), dec("Custo médio"), dec("Custo p95"), pct("% do total"), pct("Sucesso"), pct("Avanço"), pct("Repetição sem avanço"),
                           seg("Duração p50"), seg("Duração p95"), delta("Δ consumo", True), delta("Δ sucesso", False),
                           {"matcher": {"id": "byName", "options": "Agente"}, "properties": [
                               {"id": "links", "value": [{"title": "Filtrar por agente",
                                                          "url": f"/d/{UID}/esteira?${{__all_variables}}&${{__url_time_range}}&var-agente=${{__value.raw:percentencode}}"}]}]},
                           {"matcher": {"id": "byName", "options": "Tendência"}, "properties": [
                               {"id": "custom.cellOptions", "value": {"type": "sparkline"}}]}],
                transformacoes=[
                    {"id": "timeSeriesTable", "options": {"B": {"timeField": "time", "stat": "lastNotNull"}}},
                    {"id": "joinByField", "options": {"byField": "agente", "mode": "outer"}},
                    {"id": "renameByRegex", "options": {"regex": "^(.*) A$", "renamePattern": "$1"}},
                    {"id": "organize", "options": {"renameByName": {"Trend #B": "Tendência", "agente": "Agente"},
                                                   "excludeByName": {"Last *": True}}},
                ])
    ps.append(ta)

    cols = ", ".join(f"sumIf(consumo, esteira_status_execucao(resultado) = '{s}') AS `{s}`" for s in STATUS_EXEC)
    ps.append(barras("Ranking de consumo", 12, 8,
                     f"SELECT agente, {cols} {base} AND {CONSUMO_UNI} GROUP BY agente ORDER BY sum(consumo) DESC",
                     "Consumo por agente (maior no topo), empilhado por resultado.", overrides=cores_status()))
    cols_n = ", ".join(f"countIf(esteira_status_execucao(resultado) = '{s}') AS `{s}`" for s in STATUS_EXEC)
    ps.append(barras("Sucesso e falhas", 12, 8, f"SELECT agente, {cols_n} {base} GROUP BY agente ORDER BY count() DESC",
                     "Proporção dos resultados por agente.", empilhar="percent", overrides=cores_status(), mostrar_valor="auto"))
    ps.append(echarts("Eficiência", 12, 8, f"""
        SELECT agente, sumIf(consumo, {CONSUMO_UNI}) / nullIf(countIf(avancou), 0) AS custo_por_avanco,
               100 * countIf(repeticao_sem_avanco) / count() AS pct_repeticao
        {base} GROUP BY agente ORDER BY custo_por_avanco DESC""", "a3_eficiencia.js",
                      "Barra = consumo por execução que avançou. Linha = % de repetições sem avanço."))
    ps.append(echarts("Custo por execução (dispersão)", 12, 8, f"""
        SELECT agente, 'custo' AS tipo, count() AS n, q[1] AS p5, q[2] AS p25, q[3] AS p50, q[4] AS p75, q[5] AS p95
        FROM (SELECT agente, count() AS n0, quantiles(0.05, 0.25, 0.5, 0.75, 0.95)(consumo) AS q
              {base} AND {CONSUMO_UNI} AND consumo_disponivel GROUP BY agente)
        GROUP BY agente, q ORDER BY p50 DESC""", "boxplot.js",
                      "Distribuição do custo por execução (p5–p95). Caixa alta = agente caro às vezes; caixa toda alta = caro sempre."))
    ps.append(echarts("Duração", 12, 8, f"""
        SELECT agente, 'tempo' AS tipo, n, q[1] AS p5, q[2] AS p25, q[3] AS p50, q[4] AS p75, q[5] AS p95, lim AS limite
        FROM (SELECT agente, count() AS n, quantiles(0.05, 0.25, 0.5, 0.75, 0.95)(duracao_s) AS q, max(timeout_s) AS lim
              {base} GROUP BY agente)
        ORDER BY p50 DESC""", "boxplot.js", "Duração por agente (p5–p95). Linha tracejada = timeout configurado."))
    ps.append(painel("timeseries", "Consumo no tempo por agente", 12, 8,
                     alvo(f"SELECT toStartOfDay(fim) AS time, agente, sumIf(consumo, {CONSUMO_UNI}) AS v {base} GROUP BY time, agente ORDER BY time", 0),
                     "Consumo diário empilhado por agente.", opcoes=OPC_TEMPO,
                     defaults=serie_tempo("line", "normal", fillOpacity=40, lineInterpolation="smooth")))

    extras = []
    extras.append(echarts("Agente × coluna", 12, 8, f"""
        SELECT agente, coluna, sumIf(consumo, {CONSUMO_UNI}) AS consumo, count() AS n {base} GROUP BY agente, coluna""",
                          "a7_heatmap.js", "Valor alternável pela variável 'Agente × coluna mostra'."))
    a8 = barras("Agente × modelo", 12, 8,
                f"SELECT agente, modelo, sumIf(consumo, {CONSUMO_UNI}) AS v {base} GROUP BY agente, modelo ORDER BY agente",
                "Consumo por modelo usado em cada agente.")
    a8["transformations"] = [
        {"id": "groupingToMatrix", "options": {"columnField": "modelo", "rowField": "agente", "valueField": "v", "emptyValue": "zero"}},
        {"id": "organize", "options": {"renameByName": {"agente\\modelo": "agente"}}}]
    extras.append(a8)
    extras.append(barras("Tamanho do contexto", 12, 8, f"""
        SELECT agente, quantile(0.5)(tokens_entrada) AS `p50`, quantile(0.95)(tokens_entrada) AS `p95`
        {base} GROUP BY agente ORDER BY p50 DESC""", "Tokens de entrada (composição do prompt). p95 crescendo = prompt inchando.",
                         empilhar="none", overrides=[cor_fixa("p50", "#5794F2"), cor_fixa("p95", "#B877D9")]))
    extras.append(barras("Robustez", 12, 8, f"""
        SELECT e.agente AS agente, e.tent AS `Tentativas médias`, e.retomada AS `% sessão retomada`,
               e.timeouts AS `Timeouts`, coalesce(b.trips, 0) AS `Trips de circuit break`, coalesce(b.negadas, 0) AS `Admissões negadas`
        FROM (SELECT agente, avg(tentativas) AS tent, 100 * countIf(sessao = 'retomada') / count() AS retomada,
                     countIf(resultado = 'timeout') AS timeouts {base} GROUP BY agente) AS e
        LEFT JOIN (
          SELECT ag.agente AS agente, countIf(v.evento = 'esteira.agente.circuit_break' AND v.a['esteira.circuit_break.passo'] = 'persisted') AS trips,
                 countIf(v.evento = 'esteira.agente.admissao_negada') AS negadas
          FROM v_eventos AS v
          INNER JOIN (SELECT DISTINCT pipe, board, coluna, agente FROM v_execucoes WHERE {PIPE}) AS ag
            ON ag.pipe = v.pipe AND ag.board = v.a['esteira.board'] AND ag.coluna = v.a['esteira.coluna']
          WHERE v.{PIPE} AND $__timeFilter(v.ts) AND v.evento IN ('esteira.agente.circuit_break', 'esteira.agente.admissao_negada')
          GROUP BY agente) AS b ON b.agente = e.agente""",
                         "Agrupado por agente. Trips e admissões negadas são atribuídos ao agente da coluna onde ocorreram.",
                         horizontal=False, empilhar="none"))
    return ps, extras


def fluxo():
    ps = []
    finais = f"(SELECT colunas_finais FROM v_config WHERE {PIPE})"
    sql_g10 = f"""
    WITH concl AS (
      SELECT issue, min(ts) AS t FROM (
        SELECT issue, ts FROM v_transicoes WHERE {PIPE} AND has({finais}, para)
        UNION ALL
        SELECT a['esteira.issue'] AS issue, ts FROM v_eventos WHERE {PIPE} AND evento = 'esteira.issue.upsert' AND a['esteira.issue.estado'] = 'closed')
      GROUP BY issue)
    SELECT time, n AS `Concluídas`, avg(n) OVER (ORDER BY time ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS `Média móvel 7d`
    FROM (SELECT toStartOfDay(t) AS time, count() AS n FROM concl WHERE $__timeFilter(t) GROUP BY time ORDER BY time
          WITH FILL FROM toStartOfDay($__fromTime) TO $__toTime STEP INTERVAL 1 DAY)
    ORDER BY time"""
    ps.append(painel("timeseries", "Throughput", 8, 8, alvo(sql_g10, 1), "Issues que ficaram concluídas por dia.",
                     opcoes=OPC_TEMPO, defaults=serie_tempo("line"),
                     overrides=[{"matcher": {"id": "byName", "options": "Concluídas"}, "properties": [
                         {"id": "custom.drawStyle", "value": "bars"}, {"id": "custom.fillOpacity", "value": 70},
                         {"id": "color", "value": {"mode": "fixed", "fixedColor": "#2E9E44"}}]},
                                {"matcher": {"id": "byName", "options": "Média móvel 7d"}, "properties": [
                                    {"id": "color", "value": {"mode": "fixed", "fixedColor": "#FFFFFF"}}]}]))
    sql_g11 = f"""
    WITH dias AS (SELECT arrayJoin(arrayMap(i -> toStartOfDay($__fromTime) + toIntervalDay(i),
                                    range(toUInt32(dateDiff('day', $__fromTime, $__toTime) + 1)))) AS d)
    SELECT d AS time, coluna, count() AS n FROM (
      SELECT d, x.issue AS issue, argMax(x.para, x.ts) AS coluna
      FROM dias CROSS JOIN (SELECT issue, para, ts FROM v_transicoes WHERE {PIPE}) AS x
      WHERE x.ts < d + INTERVAL 1 DAY GROUP BY d, issue)
    WHERE NOT has({finais}, coluna) GROUP BY time, coluna ORDER BY time"""
    ps.append(painel("timeseries", "WIP por coluna", 8, 8, alvo(sql_g11, 0),
                     "Issues em cada coluna no fim de cada dia (exceto colunas finais).", opcoes=OPC_TEMPO,
                     defaults=serie_tempo("line", "normal", fillOpacity=50)))
    sql_g12 = f"""
    SELECT para AS coluna, quantile(0.5)(permanencia_s) AS `p50`, quantile(0.95)(permanencia_s) AS `p95`
    FROM v_transicoes WHERE {PIPE} AND $__timeFilter(ts) AND permanencia_s IS NOT NULL AND {multi('board', 'board')}
    GROUP BY coluna ORDER BY p50 DESC"""
    ps.append(barras("Tempo por coluna", 8, 8, sql_g12, "Tempo de calendário que a issue fica em cada coluna.",
                     empilhar="none", unidade="s", overrides=[cor_fixa("p50", "#5794F2"), cor_fixa("p95", "#B877D9")]))
    ordem = f"(SELECT ordem_colunas FROM v_config WHERE {PIPE})"
    sql_g13 = f"""
    SELECT de AS coluna, count() AS `Devoluções` FROM v_transicoes
    WHERE {PIPE} AND $__timeFilter(ts) AND {multi('board', 'board')}
      AND indexOf({ordem}, para) > 0 AND indexOf({ordem}, de) > indexOf({ordem}, para)
    GROUP BY coluna ORDER BY 2 DESC"""
    ps.append(barras("Retrabalho", 12, 8, sql_g13, "Transições para uma coluna anterior (ordem_colunas no dashboard.yml), pela coluna que devolveu.",
                     overrides=[cor_fixa("Devoluções", "#F28C28")]))
    ps.append(echarts("Caminho das issues", 12, 8, f"""
        SELECT de, para, count() AS n FROM v_transicoes WHERE {PIPE} AND $__timeFilter(ts) AND {multi('board', 'board')}
        GROUP BY de, para""", "g14_sankey.js", "Transições de → para no período."))
    return ps


def board_sync():
    ps = []
    sql_lat = f"""
    SELECT $__timeInterval(ts) AS time, a['esteira.board.operacao'] AS op,
           quantile(0.95)(toFloat64OrZero(a['esteira.board.duracao_s'])) AS p95
    FROM v_eventos WHERE {EV_F} AND evento = 'esteira.board.api' GROUP BY time, op ORDER BY time"""
    sql_err = f"""
    SELECT $__timeInterval(ts) AS time, a['esteira.board.status'] AS status, count() AS n
    FROM v_eventos WHERE {EV_F} AND evento = 'esteira.board.api' AND a['esteira.board.status'] != 'ok'
    GROUP BY time, status ORDER BY time"""
    ps.append(painel("timeseries", "Latência da API do board (p95 por operação)", 12, 8, [alvo(sql_lat, 0), alvo(sql_err, 0, "B")],
                     "Linhas = p95 por operação. Barras (eixo direito) = chamadas com erro e rate limit.", opcoes=OPC_TEMPO,
                     defaults=serie_tempo("line", unidade="s"),
                     overrides=[{"matcher": {"id": "byFrameRefID", "options": "B"}, "properties": [
                         {"id": "custom.drawStyle", "value": "bars"}, {"id": "custom.axisPlacement", "value": "right"},
                         {"id": "unit", "value": "short"}, {"id": "custom.fillOpacity", "value": 80}]},
                                cor_fixa("erro", "#D93025"), cor_fixa("rate_limit", "#F28C28")]))
    sql_thr = f"""
    SELECT time, serie, v FROM (
      SELECT ts AS time, 'throttle (s)' AS serie, toFloat64OrZero(a['esteira.board.throttle.valor_novo_s']) AS v
      FROM v_eventos WHERE {EV_F} AND evento = 'esteira.board.throttle'
      UNION ALL
      SELECT ts AS time, 'penalty (h)' AS serie, toFloat64OrZero(a['esteira.board.penalty.horas']) AS v
      FROM v_eventos WHERE {EV_F} AND evento = 'esteira.board.penalty'
      UNION ALL
      SELECT now() AS time, if(metrica = 'esteira.board.throttle', 'throttle (s)', 'penalty (h)') AS serie, argMax(valor, ts) AS v
      FROM v_metricas WHERE {PIPE} AND metrica IN ('esteira.board.throttle', 'esteira.board.penalty') AND ts > now() - INTERVAL 1 HOUR
      GROUP BY serie)
    ORDER BY time"""
    ps.append(painel("timeseries", "Throttle e penalty", 12, 8, alvo(sql_thr, 0), "Valor em degrau a cada mudança.",
                     opcoes=OPC_TEMPO, defaults=serie_tempo("line", lineInterpolation="stepAfter", showPoints="always", pointSize=4),
                     overrides=[{"matcher": {"id": "byRegexp", "options": "penalty.*"}, "properties": [
                         {"id": "custom.axisPlacement", "value": "right"}, {"id": "color", "value": {"mode": "fixed", "fixedColor": "#D93025"}}]}]))
    sql_br = f"""
    SELECT time, plataforma, estado FROM (
      SELECT $__fromTime AS time, a['esteira.board.plataforma'] AS plataforma, argMax(a['esteira.breaker.estado_novo'], ts) AS estado
      FROM v_eventos WHERE {PIPE} AND ts < $__fromTime AND evento = 'esteira.sync.circuit_breaker' AND a['esteira.breaker.escopo'] = 'plataforma'
      GROUP BY plataforma
      UNION ALL
      SELECT ts AS time, a['esteira.board.plataforma'] AS plataforma, a['esteira.breaker.estado_novo'] AS estado
      FROM v_eventos WHERE {EV_F} AND evento = 'esteira.sync.circuit_breaker' AND a['esteira.breaker.escopo'] = 'plataforma')
    ORDER BY time"""
    p = painel("state-timeline", "Circuit breaker do board", 12, 5, alvo(sql_br, 1),
               "Estado por plataforma: closed, half_open, open.",
               opcoes={"showValue": "auto", "mergeValues": True, "alignValue": "left", "rowHeight": 0.8,
                       "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True}},
               defaults={"color": {"mode": "thresholds"}, "custom": {"fillOpacity": 80, "lineWidth": 0},
                         "mappings": [{"type": "value", "options": {
                             "closed": {"color": "#2E9E44", "index": 0}, "half_open": {"color": "#E8C21B", "index": 1},
                             "open": {"color": "#D93025", "index": 2}}}]},
               transformacoes=[{"id": "partitionByValues", "options": {"fields": ["plataforma"], "keepFields": False,
                                                                       "naming": {"asLabels": False}}}])
    ps.append(p)
    sql_fila = f"""
    SELECT time, serie, v FROM (
      SELECT ts AS time, 'profundidade' AS serie, sum(valor) AS v FROM v_metricas
      WHERE {PIPE} AND $__timeFilter(ts) AND metrica = 'esteira.sync.fila.profundidade' GROUP BY time
      UNION ALL
      SELECT ts AS time, 'idade máxima' AS serie, max(valor) AS v FROM v_metricas
      WHERE {PIPE} AND $__timeFilter(ts) AND metrica = 'esteira.sync.fila.idade_maxima' GROUP BY time)
    ORDER BY time"""
    ps.append(painel("timeseries", "Fila de sincronismo", 12, 5, alvo(sql_fila, 0),
                     "Área = itens na fila. Linha (eixo direito) = idade do item mais antigo.", opcoes=OPC_TEMPO,
                     defaults=serie_tempo("line", fillOpacity=30),
                     overrides=[{"matcher": {"id": "byName", "options": "idade máxima"}, "properties": [
                         {"id": "custom.axisPlacement", "value": "right"}, {"id": "unit", "value": "s"},
                         {"id": "custom.fillOpacity", "value": 0}]}]))
    sql_lag = f"""
    SELECT $__timeInterval(ts) AS time, concat(a['esteira.sync.evento'], ' p95') AS serie,
           quantile(0.95)(toFloat64OrZero(a['esteira.sync.lag_s'])) AS v
    FROM v_eventos WHERE {EV_F} AND evento = 'esteira.sync.item' GROUP BY time, serie ORDER BY time"""
    ps.append(painel("timeseries", "Lag de sincronismo", 8, 8, alvo(sql_lag, 0),
                     "Tempo entre o enfileiramento e o fim do processamento, p95 por tipo de evento.", opcoes=OPC_TEMPO,
                     defaults=serie_tempo("line", unidade="s")))
    sql_desf = f"""
    SELECT toStartOfDay(ts) AS time, a['esteira.sync.desfecho'] AS desfecho, count() AS n FROM v_eventos
    WHERE {EV_F} AND evento = 'esteira.sync.item' GROUP BY time, desfecho ORDER BY time"""
    ps.append(painel("timeseries", "Desfechos do sincronismo", 8, 8, alvo(sql_desf, 0), "", opcoes=OPC_TEMPO,
                     defaults=serie_tempo("bars", "normal"),
                     overrides=[cor_fixa("aplicado", "#2E9E44"), cor_fixa("reenfileirado", "#E8C21B"), cor_fixa("dead_letter", "#D93025")]))
    ps.append(barras("Dead-letter por categoria", 8, 8, f"""
        SELECT a['esteira.sync.dead_letter.categoria'] AS categoria, count() AS `Itens`
        FROM v_eventos WHERE {EV_F} AND evento = 'esteira.sync.item' AND a['esteira.sync.desfecho'] = 'dead_letter'
        GROUP BY categoria ORDER BY 2 DESC""", "Itens isolados no dead-letter no período.", overrides=[cor_fixa("Itens", "#D93025")]))
    ps.append(painel("table", "Últimos itens no dead-letter", 24, 6, alvo(f"""
        SELECT ts AS `Quando`, a['esteira.board'] AS `Board`, a['esteira.issue'] AS `Issue`, a['esteira.sync.evento'] AS `Evento`,
               a['esteira.sync.dead_letter.categoria'] AS `Categoria`, a['error.type'] AS `Erro`, a['esteira.erro.mensagem'] AS `Mensagem`
        FROM v_eventos WHERE {EV_F} AND evento = 'esteira.sync.item' AND a['esteira.sync.desfecho'] = 'dead_letter'
        ORDER BY ts DESC LIMIT 50"""), "", opcoes={"cellHeight": "sm", "showHeader": True}))
    return ps


def saude():
    ps = []
    sql_vida = f"""
    SELECT time, if(n > 0, 'Viva', 'Parada') AS estado FROM (
      SELECT toStartOfInterval(ts, toIntervalSecond(greatest(900, $__interval_s))) AS time, count() AS n
      FROM v_eventos WHERE {EV_F} AND evento = 'esteira.pipe.ciclo' GROUP BY time ORDER BY time
      WITH FILL FROM toStartOfInterval($__fromTime, toIntervalSecond(greatest(900, $__interval_s))) TO $__toTime
      STEP toIntervalSecond(greatest(900, $__interval_s)))"""
    ps.append(painel("state-timeline", "Vida da pipe", 24, 4, alvo(sql_vida, 1),
                     "Viva = houve ciclo na janela (mínimo 15 min). Startup e shutdown aparecem como anotação.",
                     opcoes={"showValue": "never", "mergeValues": True, "rowHeight": 0.8,
                             "legend": {"displayMode": "list", "placement": "bottom", "showLegend": False}},
                     defaults={"color": {"mode": "thresholds"}, "custom": {"fillOpacity": 80, "lineWidth": 0},
                               "mappings": [{"type": "value", "options": {
                                   "Viva": {"color": "#2E9E44", "index": 0}, "Parada": {"color": "#D93025", "index": 1}}}]}))
    ps.append(painel("table", "Incidentes", 12, 8, alvo(f"""
        SELECT ts AS `Quando`, a['esteira.incidente.tipo'] AS `Tipo`, a['esteira.board'] AS `Board`, a['esteira.issue'] AS `Issue`
        FROM v_eventos WHERE {EV_F} AND evento = 'esteira.pipe.incidente' ORDER BY ts DESC LIMIT 100"""),
                     "esteira.pipe.incidente. Também aparecem como anotação nos gráficos de tempo.", opcoes={"cellHeight": "sm"}))
    sql_t2 = f"""
    SELECT a.issue AS issue, a.nivel AS nivel, n.pai AS pai, n.board AS board, coalesce(l.consumo, 0) AS consumo,
           l.n_exec AS n_exec, l.tempo_s AS tempo_s, l.status AS status
    FROM v_arvore AS a
    INNER JOIN v_nos AS n ON n.pipe = a.pipe AND n.issue = a.issue
    INNER JOIN (SELECT * FROM v_lista_issue(unidade = {UNI}) WHERE {PIPE}) AS l ON l.issue = a.issue
    WHERE a.{PIPE} AND a.raiz = if(${{raiz:sqlstring}} != '', ${{raiz:sqlstring}},
          (SELECT raiz FROM v_lista_arvore(unidade = {UNI}) WHERE {PIPE} ORDER BY n_exec_total > 0 DESC, ultima_atividade DESC LIMIT 1))
    ORDER BY a.nivel"""
    ps.append(echarts("Árvore da raiz", 12, 8, sql_t2, "t2_arvore.js",
                      "Raiz selecionada no 'Custo por árvore' (ou a mais recente). Tamanho do nó = consumo; cor = status."))
    cor_res = {"type": "value", "options": {r: {"color": STATUS_COR[s], "index": i}
                                             for i, (r, s) in enumerate(RESULTADO_STATUS.items())}}
    sql_t1 = f"""
    SELECT fim AS `Fim`, board AS `Board`, issue AS `Issue`, coluna AS `Coluna`, agente AS `Agente`, modelo AS `Modelo`,
           resultado AS `Resultado`, if(avancou, 'sim', 'não') AS `Avançou`, duracao_s AS `Duração`,
           if(consumo_disponivel, toString(round(consumo, 2)), 'não informado') AS `Consumo`, unidade AS `Unidade`,
           tentativas AS `Tentativas`, trace_id AS `Trace`
    FROM v_execucoes WHERE {EXEC_F}
      AND (${{issue:sqlstring}} = '' OR issue = ${{issue:sqlstring}})
      AND (${{raiz:sqlstring}} = '' OR issue IN (SELECT issue FROM v_arvore WHERE {PIPE} AND raiz = ${{raiz:sqlstring}}))
    ORDER BY fim DESC LIMIT 500"""
    ps.append(painel("table", "Execuções", 24, 10, alvo(sql_t1),
                     "Uma linha por execução. Clique no Trace para ver os spans da execução abaixo.",
                     opcoes={"cellHeight": "sm", "showHeader": True},
                     defaults={"custom": {"align": "auto", "cellOptions": {"type": "auto"}}},
                     overrides=[{"matcher": {"id": "byName", "options": "Resultado"}, "properties": [
                         {"id": "mappings", "value": [cor_res]}, {"id": "custom.cellOptions", "value": {"type": "color-background"}}]},
                                {"matcher": {"id": "byName", "options": "Duração"}, "properties": [{"id": "unit", "value": "s"}]},
                                {"matcher": {"id": "byName", "options": "Trace"}, "properties": [
                                    {"id": "links", "value": [{"title": "Ver spans",
                                                               "url": f"/d/{UID}/esteira?${{__all_variables}}&${{__url_time_range}}&var-trace=${{__value.raw}}"}]}]}]))
    ps.append(painel("table", "Spans do trace selecionado", 24, 6, alvo("""
        SELECT Timestamp AS `Início`, SpanName AS `Span`, Duration / 1e9 AS `Duração`, StatusCode AS `Status`,
               SpanAttributes['esteira.issue'] AS `Issue`, SpanAttributes['esteira.board.operacao'] AS `Operação`,
               SpanAttributes['esteira.execucao.resultado'] AS `Resultado`
        FROM otel_traces WHERE TraceId = ${trace:sqlstring} ORDER BY Timestamp"""),
                     "Spans (invoke_agent / esteira.sync.item / esteira.board.api) do trace escolhido na tabela Execuções.",
                     opcoes={"cellHeight": "sm"},
                     overrides=[{"matcher": {"id": "byName", "options": "Duração"}, "properties": [{"id": "unit", "value": "s"}]}]))
    return ps


# ═════════════════════════════════════════════════════════════════════════════
# Variáveis, anotações e montagem
# ═════════════════════════════════════════════════════════════════════════════

def var_query(nome, rotulo, sql, multi_=True, todos=True, ocultar=0, ordenar=0):
    v = {"name": nome, "label": rotulo, "type": "query", "datasource": DS, "query": " ".join(sql.split()),
         "definition": " ".join(sql.split()), "refresh": 2, "multi": multi_, "includeAll": todos, "hide": ocultar,
         "sort": ordenar, "current": {}, "options": []}
    if todos:
        v["allValue"] = "'__all__'"
        v["current"] = {"text": "Todos", "value": "$__all"}
    return v


def var_texto(nome, rotulo, padrao="", ocultar=0):
    return {"name": nome, "label": rotulo, "type": "textbox", "query": padrao, "hide": ocultar,
            "current": {"text": padrao, "value": padrao}, "options": [{"selected": True, "text": padrao, "value": padrao}]}


def variaveis():
    base = f"FROM v_execucoes WHERE {PIPE} AND $__timeFilter(fim)"
    pipe = var_query("pipe", "Pipe", "SELECT pipe AS __value, pipe_nome AS __text FROM v_pipes ORDER BY ultima_atividade DESC",
                     multi_=False, todos=False)
    unidade = var_query("unidade", "Unidade", f"SELECT unidade {base} AND consumo_disponivel GROUP BY unidade ORDER BY count() DESC",
                        multi_=False, todos=False)
    a7 = {"name": "a7_valor", "label": "Agente × coluna mostra", "type": "custom", "query": "consumo,execucoes",
          "current": {"text": "consumo", "value": "consumo"}, "hide": 0,
          "options": [{"text": "consumo", "value": "consumo", "selected": True},
                      {"text": "execucoes", "value": "execucoes", "selected": False}]}
    v = [pipe, unidade,
         var_query("board", "Board", f"SELECT DISTINCT board {base} ORDER BY board"),
         var_query("coluna", "Coluna", f"SELECT DISTINCT coluna {base} ORDER BY coluna"),
         var_query("agente", "Agente", f"SELECT DISTINCT agente {base} ORDER BY agente"),
         var_query("modelo", "Modelo", f"SELECT DISTINCT modelo {base} ORDER BY modelo"),
         var_query("resultado", "Resultado", f"SELECT DISTINCT resultado {base} ORDER BY resultado"),
         var_texto("raiz", "Raiz"), var_texto("issue", "Issue"),
         var_texto("n_barras", "N barras (listas)", "30"), var_texto("n_exec", "N execuções", "100"),
         a7, var_texto("trace", "Trace", "", ocultar=2)]
    return v


def anotacoes():
    def anot(nome, cor, sql):
        return {"name": nome, "enable": True, "iconColor": cor, "datasource": DS,
                "target": alvo(sql) | {"format": 1}}
    return [
        {"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "hide": True,
         "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard"},
        anot("Startup/shutdown", "#5794F2", f"""SELECT ts AS time, concat('Pipe: ', a['esteira.pipe.fase'], ' (', versao, ')') AS text,
             ['ciclo_vida'] AS tags FROM v_eventos WHERE {EV_F} AND evento = 'esteira.pipe.ciclo_vida'"""),
        anot("Incidentes", "#F2495C", f"""SELECT ts AS time, concat('Incidente: ', a['esteira.incidente.tipo']) AS text,
             ['incidente'] AS tags FROM v_eventos WHERE {EV_F} AND evento = 'esteira.pipe.incidente'"""),
    ]


def posicionar(blocos):
    """Distribui painéis em linhas de 24 colunas, na ordem dada."""
    y = 0
    saida = []
    for blk in blocos:
        if blk["type"] == "row":
            filhos = blk.pop("_filhos", [])
            blk["gridPos"] = {"x": 0, "y": y, "w": 24, "h": 1}
            y += 1
            if blk["collapsed"]:
                yy = y
                x = 0
                alt = 0
                for p in filhos:
                    w, h = p["gridPos"]["w"], p["gridPos"]["h"]
                    if x + w > 24:
                        yy += alt
                        x, alt = 0, 0
                    p["gridPos"] = {"x": x, "y": yy, "w": w, "h": h}
                    x += w
                    alt = max(alt, h)
                blk["panels"] = filhos
                saida.append(blk)
                continue
            saida.append(blk)
            x, alt = 0, 0
            for p in filhos:
                w, h = p["gridPos"]["w"], p["gridPos"]["h"]
                if x + w > 24:
                    y += alt
                    x, alt = 0, 0
                p["gridPos"] = {"x": x, "y": y, "w": w, "h": h}
                x += w
                alt = max(alt, h)
                saida.append(p)
            y += alt
    return saida


def secao(titulo, paineis, colapsada=False):
    # EXPANDIR_TUDO=1: gera com todas as linhas abertas (útil para validar o render)
    r = linha(titulo, colapsada and os.environ.get("EXPANDIR_TUDO") != "1")
    r["_filhos"] = paineis
    return r


def main():
    ag, ag_extra = agentes()
    blocos = [
        secao("Pipe", [aba_pipes()] + topo()),
        secao("Custo das issues", principais()),
        secao("Consumo", consumo()),
        secao("Resultados", resultados()),
        secao("Agentes", ag),
        secao("Agentes — detalhe", ag_extra, colapsada=True),
        secao("Fluxo das issues", fluxo()),
        secao("Board e sincronismo", board_sync(), colapsada=True),
        secao("Saúde e detalhe", saude(), colapsada=True),
    ]
    dash = {
        "uid": UID, "title": "Esteira — acompanhamento", "tags": ["esteira", "telemetria"],
        "timezone": "America/Sao_Paulo", "editable": False, "graphTooltip": 1, "refresh": "30s",
        "time": {"from": "now-7d", "to": "now"}, "fiscalYearStartMonth": 0, "liveNow": False,
        "timepicker": {"refresh_intervals": ["10s", "30s", "1m", "5m", "15m"]},
        "schemaVersion": 41, "version": 1,
        "templating": {"list": variaveis()},
        "annotations": {"list": anotacoes()},
        "links": [],
        "panels": posicionar(blocos),
        "description": "Telemetria da Esteira Agêntica (Contrato de telemetria v1). Uma aba por pipe.",
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dash, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = sum(1 + len(p.get("panels", [])) for p in dash["panels"])
    print(f"gerado {SAIDA.relative_to(AQUI.parent)} ({n} painéis/linhas)")


if __name__ == "__main__":
    main()
