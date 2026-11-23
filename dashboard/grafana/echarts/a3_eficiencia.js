// A3 — Eficiência por agente: barra = custo por avanço; linha = % repetição sem avanço.
const rows = linhas(frame(0));
if (!rows.length) return semDados();
return {
  grid: { left: 60, right: 60, top: 40, bottom: 50 },
  legend: { bottom: 0, textStyle: { color: TEXTO2 } },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
    valueFormatter: (v) => num(v) },
  xAxis: { type: 'category', data: rows.map((r) => r.agente), axisLabel: { color: TEXTO2 } },
  yAxis: [
    { type: 'value', name: UNIDADE + ' / avanço', nameTextStyle: { color: TEXTO2 }, axisLabel: { color: TEXTO2 }, splitLine: { lineStyle: { color: GRADE } } },
    { type: 'value', name: '% repetição', max: 100, nameTextStyle: { color: TEXTO2 }, axisLabel: { color: TEXTO2, formatter: '{value}%' }, splitLine: { show: false } },
  ],
  series: [
    { name: 'custo por avanço', type: 'bar', barMaxWidth: 48, itemStyle: { color: '#5794F2' }, data: rows.map((r) => r.custo_por_avanco) },
    { name: '% repetição sem avanço', type: 'line', yAxisIndex: 1, symbolSize: 7, itemStyle: { color: '#F2495C' }, data: rows.map((r) => r.pct_repeticao) },
  ],
};
