// T2 — Árvore da raiz: nó = issue, tamanho = consumo, cor = status.
const rows = linhas(frame(0));
if (!rows.length) return semDados('Clique numa barra do "Custo por árvore" para abrir a árvore');
const por = {};
rows.forEach((r) => { por[r.issue] = { r, children: [] }; });
let raiz = null;
rows.forEach((r) => {
  if (r.nivel === 0) raiz = por[r.issue];
  else if (por[r.pai]) por[r.pai].children.push(por[r.issue]);
});
if (!raiz) return semDados();
const maxC = Math.max(...rows.map((r) => r.consumo || 0), 1);
const conv = (n) => ({
  name: `${n.r.board}/#${n.r.issue}`,
  value: n.r.consumo || 0,
  symbolSize: 8 + 26 * Math.sqrt((n.r.consumo || 0) / maxC),
  itemStyle: { color: STATUS_COR[n.r.status] || STATUS_COR['Desconhecida'], borderColor: STATUS_COR[n.r.status] },
  status: n.r.status, n_exec: n.r.n_exec, tempo: n.r.tempo_s,
  children: n.children.map(conv),
});
return {
  tooltip: { trigger: 'item', formatter: (p) => `<b>${p.data.name}</b> — ${p.data.status}<br/>Consumo: ${num(p.data.value)} ${UNIDADE}<br/>Execuções: ${p.data.n_exec} · Tempo: ${hm(p.data.tempo)}` },
  series: [{ type: 'tree', data: [conv(raiz)], top: '5%', left: '12%', bottom: '5%', right: '18%', initialTreeDepth: -1,
             label: { color: TEXTO, position: 'left', verticalAlign: 'middle', align: 'right' },
             leaves: { label: { position: 'right', align: 'left' } }, lineStyle: { color: TEXTO2 },
             expandAndCollapse: true, animationDurationUpdate: 600 }],
};
