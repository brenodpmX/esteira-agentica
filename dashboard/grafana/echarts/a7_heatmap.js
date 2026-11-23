// A7 — Agente × coluna (valor alternável pela variável a7_valor).
const rows = linhas(frame(0));
if (!rows.length) return semDados();
const agentes = [...new Set(rows.map((r) => r.agente))];
const colunas = [...new Set(rows.map((r) => r.coluna))];
const modo = context.grafana.replaceVariables('${a7_valor}');
const campo = modo === 'execucoes' ? 'n' : 'consumo';
const vals = rows.map((r) => r[campo] || 0);
return {
  grid: { left: 110, right: 30, top: 20, bottom: 70 },
  tooltip: { formatter: (p) => {
    const r = rows.find((x) => x.agente === agentes[p.value[1]] && x.coluna === colunas[p.value[0]]);
    return `<b>${r.agente}</b> em <b>${r.coluna}</b><br/>Consumo: ${num(r.consumo)} ${UNIDADE}<br/>Execuções: ${r.n}`;
  } },
  xAxis: { type: 'category', data: colunas, axisLabel: { color: TEXTO2 }, splitArea: { show: true } },
  yAxis: { type: 'category', data: agentes, axisLabel: { color: TEXTO2 }, splitArea: { show: true } },
  visualMap: { min: 0, max: Math.max(...vals, 1), calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
               textStyle: { color: TEXTO2 }, inRange: { color: ['#1f2a44', '#5794F2', '#F2CC0C', '#F2495C'] } },
  series: [{ type: 'heatmap', label: { show: true, color: '#fff', formatter: (p) => num(p.value[2], 0) },
             data: rows.map((r) => [colunas.indexOf(r.coluna), agentes.indexOf(r.agente), r[campo] || 0]) }],
};
