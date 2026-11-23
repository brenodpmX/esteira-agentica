// G2 — Custo por execução. Cor = resultado; borda tracejada = não avançou.
const rows = linhas(frame(0));
if (!rows.length) return semDados('Nenhuma execução no período');
return {
  animationDurationUpdate: 600,
  grid: { left: 60, right: 70, top: 40, bottom: 60 },
  legend: { bottom: 0, textStyle: { color: TEXTO2 }, data: ['consumo', 'duração'] },
  tooltip: {
    trigger: 'axis', axisPointer: { type: 'shadow' },
    formatter: (ps) => {
      const r = rows[ps[0].dataIndex];
      const st = RESULTADO_STATUS[r.resultado] || 'Desconhecida';
      let s = `<b>${r.board}/#${r.issue}</b> · ${r.coluna}<br/>`;
      s += `<span style="color:${STATUS_COR[st]}">${r.resultado}</span> · ${r.avancou ? 'avançou' : 'não avançou'}${r.repeticao_sem_avanco ? ' · repetição sem avanço' : ''}<br/>`;
      s += `Agente: ${r.agente} · Modelo: ${r.modelo}<br/>`;
      s += `Consumo: <b>${r.consumo_disponivel ? num(r.consumo) + ' ' + r.unidade : 'não informado'}</b><br/>`;
      s += `Duração: ${hm(r.duracao_s)} · Tentativas: ${r.tentativas} · Sessão: ${r.sessao || '-'}<br/>`;
      s += `Tokens de entrada: ${num(r.tokens_entrada, 0)}<br/>Fim: ${dataHora(r.fim)}`;
      return s;
    },
  },
  xAxis: { type: 'category', data: rows.map((r) => dataHora(r.fim)), axisLabel: { show: rows.length <= 40, color: TEXTO2, rotate: 45, fontSize: 10 } },
  yAxis: [eixoConsumo(), eixoTempo()],
  series: [
    { name: 'consumo', type: 'bar', barMaxWidth: 24, barMinHeight: 2,
      data: rows.map((r) => {
        const cor = STATUS_COR[RESULTADO_STATUS[r.resultado] || 'Desconhecida'];
        const st = { color: r.consumo_disponivel ? cor : 'transparent' };
        if (!r.avancou) Object.assign(st, { borderType: 'dashed', borderColor: r.consumo_disponivel ? '#ffffff' : cor, borderWidth: 1.5 });
        else if (!r.consumo_disponivel) Object.assign(st, { borderColor: cor, borderWidth: 1.5 });
        return { value: r.consumo_disponivel ? r.consumo : 0, itemStyle: st };
      }) },
    { name: 'duração', type: 'line', yAxisIndex: 1, symbol: 'circle', symbolSize: 4,
      lineStyle: { color: TEXTO, width: 1.5 }, itemStyle: { color: TEXTO }, data: rows.map((r) => r.duracao_s) },
  ],
};
