// Lógica pura da /ao-vivo (testada em tests/painel.test.mjs). Preços chegam
// como string decimal do /api/painel; números só para desenhar o gráfico.

// Mesmo eixo de tempo em todos os cartões. Eixo final: da B0 (14/11 14:50 BRT)
// ao fim da PÓS-BF (08/12 00:00 BRT), igual à análise. Até a BF acabar
// (28/11 00:00 BRT) o eixo termina no fim da BF, para a série não virar um
// traço espremido à esquerda.
export const DOMAIN = { start: Date.parse('2026-11-14T17:50:00Z'), end: Date.parse('2026-12-08T03:00:00Z') };
export const BF_WINDOW = { start: Date.parse('2026-11-23T03:00:00Z'), end: Date.parse('2026-11-28T03:00:00Z') };

export function domainFor(now) {
  return now < BF_WINDOW.end ? { start: DOMAIN.start, end: BF_WINDOW.end } : DOMAIN;
}

const MINUS = '−';

export function formatPct(pct) {
  if (pct === null || pct === undefined) return '— vs referência';
  const neg = pct.startsWith('-');
  const abs = (neg ? pct.slice(1) : pct).replace('.', ',');
  const sign = neg ? MINUS : abs === '0,0' ? '' : '+';
  return `${sign}${abs}% vs referência`;
}

export function formatBRL(value) {
  if (value === null || value === undefined) return '—';
  const [int, dec = '00'] = value.split('.');
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `R$ ${grouped},${dec.padEnd(2, '0').slice(0, 2)}`;
}

const WHEN = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
});

export function formatWhen(iso) {
  const parts = Object.fromEntries(WHEN.formatToParts(new Date(iso)).map(p => [p.type, p.value]));
  return `${parts.day}/${parts.month}, ${parts.hour}:${parts.minute}`;
}

const DAY = new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit' });

// Enquanto a Referência é parcial, o percentual não diz nada (compara o preço
// com ele mesmo): o cartão mostra quando ela fecha.
export function pctLabel(produto, referencia) {
  if (referencia.parcial) return `referência fecha em ${DAY.format(new Date(referencia.fim))}`;
  return formatPct(produto.disponivel ? produto.vs_referencia_pct : null);
}

export function groupByCategory(produtos) {
  const groups = [];
  for (const p of produtos) {
    let g = groups.find(x => x.categoria === p.categoria);
    if (!g) groups.push(g = { categoria: p.categoria, produtos: [] });
    g.produtos.push(p);
  }
  return groups;
}

const f = n => n.toFixed(1);

// Rótulo "BF" em HTML sobre o SVG (o SVG estica com preserveAspectRatio="none";
// texto dentro dele sairia deformado). Posição em % da largura do gráfico.
export function bfLabel(bf, width) {
  return { text: 'BF', left: `${(100 * bf.x / width).toFixed(3)}%`, width: `${(100 * bf.width / width).toFixed(3)}%` };
}

export function sparkline(serie, ref, { width, height, now, top = 0 }) {
  const d = domainFor(now);
  const span = d.end - d.start;
  const x = t => width * (t - d.start) / span;
  const bf = { x: x(BF_WINDOW.start), width: x(BF_WINDOW.end) - x(BF_WINDOW.start) };
  const pts = serie.map(([t, v]) => [Date.parse(t), Number(v)]);
  const values = pts.map(p => p[1]).concat(ref ? [Number(ref)] : []);
  if (!pts.length) return { path: '', refY: null, bf };
  let lo = Math.min(...values), hi = Math.max(...values);
  const pad = (hi - lo) * 0.15 || Math.max(hi * 0.02, 1);
  lo -= pad; hi += pad;
  // `top` reserva o alto do gráfico para o rótulo "BF": os dados ficam em [top, height].
  const y = v => height - (v - lo) / (hi - lo) * (height - top);
  let path = `M${f(x(pts[0][0]))} ${f(y(pts[0][1]))}`;
  for (const [t, v] of pts.slice(1)) path += ` H ${f(x(t))} V ${f(y(v))}`;
  return { path, refY: ref ? y(Number(ref)) : null, bf };
}
