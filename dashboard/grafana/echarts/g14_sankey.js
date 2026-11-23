// G14 — Caminho das issues: transições de → para (bipartido, para aceitar ciclos).
const rows = linhas(frame(0));
if (!rows.length) return semDados('Nenhuma transição no período');
const nos = new Set();
const links = rows.map((r) => { const s = 'de ' + r.de, t = 'para ' + r.para; nos.add(s); nos.add(t); return { source: s, target: t, value: r.n }; });
return {
  tooltip: { trigger: 'item' },
  series: [{ type: 'sankey', left: 20, right: 90, top: 10, bottom: 10, nodeGap: 10, emphasis: { focus: 'adjacency' },
             label: { color: TEXTO }, lineStyle: { color: 'gradient', opacity: 0.45 },
             data: [...nos].map((n) => ({ name: n })), links }],
};
