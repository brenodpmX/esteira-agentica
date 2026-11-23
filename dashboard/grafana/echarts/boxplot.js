// Box plot por agente (A4 custo / A5 duração). Colunas: agente, p5, p25, p50, p75, p95, n [, limite].
const rows = linhas(frame(0));
if (!rows.length) return semDados();
const ehTempo = rows[0].tipo === 'tempo';
const fmt = ehTempo ? hm : (v) => num(v);
const serie = [{
  name: ehTempo ? 'duração' : 'custo', type: 'boxplot', itemStyle: { color: 'rgba(87,148,242,0.35)', borderColor: '#5794F2' },
  data: rows.map((r) => [r.p5, r.p25, r.p50, r.p75, r.p95]),
}];
const limite = rows.find((r) => r.limite) ? Math.max(...rows.map((r) => r.limite || 0)) : null;
if (limite) {
  serie[0].markLine = { symbol: 'none', lineStyle: { color: '#F28C28', type: 'dashed' },
    label: { formatter: 'timeout ' + hm(limite), color: '#F28C28' }, data: [{ yAxis: limite }] };
}
return {
  grid: { left: 70, right: 30, top: 30, bottom: 40 },
  tooltip: { trigger: 'item', formatter: (p) => {
    const r = rows[p.dataIndex];
    return `<b>${r.agente}</b> (${r.n} exec)<br/>p95: ${fmt(r.p95)}<br/>p75: ${fmt(r.p75)}<br/>p50: ${fmt(r.p50)}<br/>p25: ${fmt(r.p25)}<br/>p5: ${fmt(r.p5)}`;
  } },
  xAxis: { type: 'category', data: rows.map((r) => r.agente), axisLabel: { color: TEXTO2 } },
  yAxis: { type: 'value', name: ehTempo ? 'h:mm' : UNIDADE, nameTextStyle: { color: TEXTO2 },
           axisLabel: { color: TEXTO2, formatter: (v) => fmt(v) }, splitLine: { lineStyle: { color: GRADE } } },
  series: serie,
};
