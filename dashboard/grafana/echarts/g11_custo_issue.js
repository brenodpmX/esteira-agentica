// G1.1 — Custo por issue (lista viva, todos os boards, sem somar filhas).
const rows = linhas(frame(0));
if (!rows.length) return semDados('Nenhuma issue com atividade no período');
context.panel.chart.off('click');
context.panel.chart.on('click', (p) => { const r = rows[p.dataIndex]; if (r) setVar('issue', r.issue); });
return {
  animationDurationUpdate: 800,
  grid: { left: 60, right: 70, top: 40, bottom: 80 },
  legend: { bottom: 0, textStyle: { color: TEXTO2 }, data: ['consumo', 'tempo'] },
  tooltip: {
    trigger: 'axis', axisPointer: { type: 'shadow' },
    formatter: (ps) => {
      const r = rows[ps[0].dataIndex];
      let s = `<b>${r.board}/#${r.issue}</b> — <span style="color:${STATUS_COR[r.status]}">${r.status}</span><br/>`;
      s += `Coluna atual: ${r.coluna || '-'}<br/>Consumo: <b>${num(r.consumo || 0)} ${UNIDADE}</b> · Execuções: ${r.n_exec}`;
      if (r.n_sem_consumo) s += ` (${r.n_sem_consumo} sem consumo informado)`;
      s += `<br/>Tempo de agente: ${hm(r.tempo_s)}<br/>Última atividade: ${dataHora(r.ultima_atividade)}`;
      return s;
    },
  },
  xAxis: { type: 'category', data: rows.map((r) => r.board + '/#' + r.issue), axisLabel: { color: TEXTO2, rotate: 45, fontSize: 10 } },
  yAxis: [eixoConsumo(), eixoTempo()],
  series: [
    { name: 'consumo', type: 'bar', barMaxWidth: 36, barMinHeight: 3,
      data: rows.map((r) => {
        const cor = STATUS_COR[r.status] || STATUS_COR['Desconhecida'];
        return r.status === 'Sem execução'
          ? { value: r.consumo || 0, itemStyle: { color: 'transparent', borderColor: cor, borderWidth: 2 } }
          : { value: r.consumo || 0, itemStyle: { color: cor } };
      }) },
    { name: 'tempo', type: 'line', yAxisIndex: 1, symbol: 'circle', symbolSize: 5,
      lineStyle: { color: TEXTO }, itemStyle: { color: TEXTO }, data: rows.map((r) => r.tempo_s) },
  ],
};
