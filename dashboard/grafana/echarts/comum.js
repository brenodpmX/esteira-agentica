// Funções comuns aos painéis ECharts (injetadas no início de cada painel pelo build).
const STATUS_COR = {
  'Concluída': '#2E9E44',
  'Em andamento': '#2F6FDB',
  'Falha': '#D93025',
  'Timeout': '#F28C28',
  'Interrompida': '#E8C21B',
  'Bloqueada': '#8E44AD',
  'Desconhecida': '#8A8A8A',
  'Sem execução': '#2F6FDB',
};
const RESULTADO_STATUS = {
  'concluída': 'Concluída', 'falha terminal': 'Falha', 'timeout': 'Timeout',
  'interrompida': 'Interrompida', 'desconhecida': 'Desconhecida',
};
const TEXTO = (context.grafana.theme && context.grafana.theme.colors && context.grafana.theme.colors.text.primary) || '#ccc';
const TEXTO2 = (context.grafana.theme && context.grafana.theme.colors && context.grafana.theme.colors.text.secondary) || '#888';
const GRADE = 'rgba(128,128,128,0.15)';
const UNIDADE = context.grafana.replaceVariables('${unidade}') || '';

function frame(i) {
  const s = (context.panel.data.series || [])[i || 0];
  return s || null;
}
function col(f, nome) {
  if (!f) return [];
  const c = f.fields.find((x) => x.name === nome);
  return c ? Array.from(c.values) : [];
}
function linhas(f) {
  if (!f || !f.fields.length) return [];
  const n = f.fields[0].values.length;
  const out = [];
  for (let i = 0; i < n; i++) {
    const r = {};
    f.fields.forEach((c) => { r[c.name] = c.values[i] !== undefined ? c.values[i] : c.values.get(i); });
    out.push(r);
  }
  return out;
}
function semDados(msg) {
  return { title: { text: msg || 'Sem dados no período', left: 'center', top: 'middle', textStyle: { color: TEXTO2, fontSize: 13, fontWeight: 'normal' } } };
}
// Clareia uma cor hex em `fator` (0..1).
function clarear(hex, fator) {
  const n = parseInt(hex.slice(1), 16);
  const r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  const f = (c) => Math.round(c + (255 - c) * fator);
  return '#' + [f(r), f(g), f(b)].map((c) => c.toString(16).padStart(2, '0')).join('');
}
function hm(seg) {
  if (seg === null || seg === undefined || isNaN(seg)) return '-';
  const h = Math.floor(seg / 3600), m = Math.round((seg % 3600) / 60);
  return h + ':' + String(m === 60 ? 59 : m).padStart(2, '0');
}
function num(v, casas) {
  if (v === null || v === undefined || isNaN(v)) return '-';
  return Number(v).toLocaleString('pt-BR', { maximumFractionDigits: casas === undefined ? 2 : casas });
}
function dataHora(ms) {
  if (!ms) return '-';
  return new Date(ms).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}
function setVar(nome, valor) {
  const q = {}; q['var-' + nome] = valor;
  context.grafana.locationService.partial(q, true);
}
function eixoTempo() {
  return { type: 'value', name: 'tempo (h:mm)', position: 'right', nameTextStyle: { color: TEXTO2 },
           axisLabel: { color: TEXTO2, formatter: (v) => hm(v) }, splitLine: { show: false } };
}
function eixoConsumo() {
  return { type: 'value', name: UNIDADE, position: 'left', nameTextStyle: { color: TEXTO2 },
           axisLabel: { color: TEXTO2, formatter: (v) => num(v, 0) }, splitLine: { lineStyle: { color: GRADE } } };
}
