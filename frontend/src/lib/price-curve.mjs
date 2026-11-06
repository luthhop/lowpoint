/** Prices are integer cents. Floating point operations below describe SVG geometry only. */
export function formatPrice(cents, decimals = false) {
  if (!Number.isSafeInteger(cents)) throw new TypeError('Price must be integer cents');
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency', currency: 'BRL',
    minimumFractionDigits: decimals ? 2 : 0, maximumFractionDigits: decimals ? 2 : 0,
  }).format(cents / 100);
}

export function discountPercent(priceCents, baselineCents) {
  if (!Number.isSafeInteger(priceCents) || !Number.isSafeInteger(baselineCents) || baselineCents <= 0) {
    throw new TypeError('Expected integer cents and a positive baseline');
  }
  return Math.floor(((baselineCents - priceCents) * 100) / baselineCents);
}

/**
 * Monotone cubic Hermite curve. Controls stay within each pair's price range:
 * smoothing must never invent a lower price or a higher peak.
 * The horizontal axis is a narrative timeline, not a linear date scale.
 * @param {{priceCents: number, position: number}[]} data
 */
export function priceCurve(data, width = 1000, height = 220) {
  const lower = 300000;
  const upper = 630000;
  const pad = 16;
  const yFor = (/** @type {number} */ price) => pad + (upper - price) / (upper - lower) * (height - pad * 2);
  const points = data.map(p => ({ x: p.position * width, y: yFor(p.priceCents) }));
  if (points.length < 2) throw new RangeError('At least two samples are required');
  const slopes = points.slice(1).map((p, i) => {
    const dx = p.x - points[i].x;
    if (dx <= 0) throw new RangeError('Timeline positions must increase');
    return (p.y - points[i].y) / dx;
  });
  const tangents = points.map((_, i) => {
    if (i === 0) return slopes[0];
    if (i === points.length - 1) return slopes[i - 1];
    const before = slopes[i - 1], after = slopes[i];
    if (before * after <= 0) return 0;
    const left = points[i].x - points[i - 1].x, right = points[i + 1].x - points[i].x;
    const w1 = 2 * right + left, w2 = right + 2 * left;
    return (w1 + w2) / (w1 / before + w2 / after);
  });
  const segments = points.slice(1).map((b, i) => {
    const a = points[i], third = (b.x - a.x) / 3;
    const clamp = (/** @type {number} */ y) => Math.max(Math.min(a.y, b.y), Math.min(Math.max(a.y, b.y), y));
    return { a, b, c1: { x: a.x + third, y: clamp(a.y + tangents[i] * third) }, c2: { x: b.x - third, y: clamp(b.y - tangents[i + 1] * third) } };
  });
  const path = `M${points[0].x},${points[0].y}` + segments.map(s => `C${s.c1.x},${s.c1.y} ${s.c2.x},${s.c2.y} ${s.b.x},${s.b.y}`).join('');
  return { path, points, segments, baselineY: yFor(345000) };
}
