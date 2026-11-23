// G1 — Custo por árvore (lista viva). Uma barra por raiz, pilha por nível,
// cor pelo status da árvore, tom mais claro a cada nível; linha = tempo acumulado.
const rows = linhas(frame(0));
if (!rows.length) return semDados('Nenhuma árvore com atividade no período');

const raizes = [];
const info = {};
rows.forEach((r) => {
  if (!info[r.raiz]) {
    info[r.raiz] = { status: r.status, board: r.raiz_board, tempo: r.tempo_total_s, consumo: r.consumo_total,
                     n_exec: r.n_exec_total, ultima: r.ultima_atividade, criada: r.criada_em, niveis: {} };
    raizes.push(r.raiz);
  }
  info[r.raiz].niveis[r.nivel] = r;
});
const maxNivel = Math.max(...rows.map((r) => r.nivel));
const NOME_NIVEL = (n) => (n === 0 ? 'raiz' : n === 1 ? 'filhas' : n === 2 ? 'netas' : 'nível ' + n);

const series = [];
for (let n = 0; n <= maxNivel; n++) {
  series.push({
    name: NOME_NIVEL(n), type: 'bar', stack: 'arvore', barMaxWidth: 48,
    // cor da legenda: tom neutro por nível (a cor real de cada barra vem do status)
    itemStyle: { color: clarear('#6E7681', Math.min(0.8, n * 0.25)) },
    barMinHeight: n === 0 ? 3 : 0,
    emphasis: { focus: 'none' },
    data: raizes.map((rz) => {
      const it = info[rz];
      const v = it.niveis[n] ? (it.niveis[n].consumo || 0) : 0;
      const cor = STATUS_COR[it.status] || STATUS_COR['Desconhecida'];
      if (it.status === 'Sem execução') {
        return { value: v, itemStyle: { color: 'transparent', borderColor: cor, borderWidth: 2 } };
      }
      return { value: v, itemStyle: { color: clarear(cor, Math.min(0.8, n * 0.2)) } };
    }),
  });
}
series.push({
  name: 'tempo acumulado', type: 'line', yAxisIndex: 1, symbol: 'circle', symbolSize: 6,
  lineStyle: { width: 2, color: TEXTO }, itemStyle: { color: TEXTO },
  data: raizes.map((rz) => info[rz].tempo),
});

context.panel.chart.off('click');
context.panel.chart.on('click', (p) => { if (raizes[p.dataIndex] !== undefined) setVar('raiz', raizes[p.dataIndex]); });

return {
  animationDurationUpdate: 800,
  grid: { left: 60, right: 70, top: 40, bottom: 70 },
  legend: { bottom: 0, textStyle: { color: TEXTO2 } },
  tooltip: {
    trigger: 'axis', axisPointer: { type: 'shadow' },
    formatter: (ps) => {
      const rz = raizes[ps[0].dataIndex];
      const it = info[rz];
      let s = `<b>#${rz}</b> (${it.board}) — <span style="color:${STATUS_COR[it.status]}">${it.status}</span><br/>`;
      s += `Consumo: <b>${num(it.consumo)} ${UNIDADE}</b> · Execuções: ${it.n_exec}<br/>`;
      s += `Tempo de agente: ${hm(it.tempo)} · Calendário desde a criação: ${hm((it.ultima - it.criada) / 1000)}<br/>`;
      Object.keys(it.niveis).sort().forEach((n) => {
        const l = it.niveis[n];
        let extra = '';
        if (l.n_sem_consumo) extra += ` · ${l.n_sem_consumo} sem consumo informado`;
        if (l.n_outra_unidade) extra += ` · ${l.n_outra_unidade} em outra unidade`;
        s += `&nbsp;&nbsp;${NOME_NIVEL(Number(n))} (${l.n_issues} issue${l.n_issues > 1 ? 's' : ''}): ${num(l.consumo || 0)} · ${l.n_exec} exec${extra}<br/>`;
      });
      s += `Última atividade: ${dataHora(it.ultima)}`;
      return s;
    },
  },
  xAxis: { type: 'category', data: raizes.map((r) => '#' + r), axisLabel: { color: TEXTO2, rotate: raizes.length > 20 ? 45 : 0 } },
  yAxis: [eixoConsumo(), eixoTempo()],
  series,
};
