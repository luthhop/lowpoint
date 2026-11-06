import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { priceCurve, discountPercent, formatPrice } from '../src/lib/price-curve.mjs';

const demo = JSON.parse(readFileSync(new URL('../src/data/demo-history.json', import.meta.url), 'utf8'));

test('[TESTE] demo prices use cents and retain the approved story', () => {
  assert.equal(demo.illustrative, true);
  assert.ok(demo.points.every(p => Number.isSafeInteger(p.priceCents)));
  assert.equal(demo.points.find(p => p.date === '2026-11-27').priceCents, 360000);
  assert.equal(demo.points.at(-1).priceCents, 320000);
  assert.equal(discountPercent(360000, demo.crossedOutCents), 40);
  assert.equal(discountPercent(320000, demo.baselineCents), 7);
});

test('[TESTE] smoothing never invents a discount or an inflated peak', () => {
  const { segments } = priceCurve(demo.points);
  for (const s of segments) {
    const min = Math.min(s.a.y, s.b.y), max = Math.max(s.a.y, s.b.y);
    for (let tick = 0; tick <= 100; tick++) {
      const t = tick / 100, u = 1 - t;
      const y = u ** 3 * s.a.y + 3 * u ** 2 * t * s.c1.y + 3 * u * t ** 2 * s.c2.y + t ** 3 * s.b.y;
      assert.ok(y >= min - 1e-8 && y <= max + 1e-8, 'Curve exceeded the recorded prices');
    }
  }
});

test('[TESTE] facade and real charts use one vertical scale', () => {
  const before = priceCurve(demo.points.slice(0, -1));
  const after = priceCurve(demo.points);
  assert.equal(before.baselineY, after.baselineY);
  assert.deepEqual(before.points, after.points.slice(0, -1));
  assert.ok(after.points.at(-1).y > after.baselineY);
});

test('[TESTE] monetary display follows pt-BR without rounding percentages up', () => {
  assert.equal(formatPrice(320000, true).replaceAll('\u00a0', ' '), 'R$ 3.200,00');
  assert.equal(discountPercent(331201, 345000), 3);
  assert.throws(() => formatPrice(3200.5), TypeError);
  assert.throws(() => discountPercent(320000, 0), TypeError);
});

test('[TESTE] the plotted curve ends on the actual latest sample', () => {
  const curve = priceCurve(demo.points);
  const last = curve.segments.at(-1).b;
  assert.equal(last.x, 1000);
  assert.deepEqual(last, curve.points.at(-1));
  assert.ok(Number.isFinite(last.y));
  assert.ok(!curve.path.includes('NaN'));
});
