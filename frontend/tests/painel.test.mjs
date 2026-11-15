import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatPct, formatBRL, formatWhen, groupByCategory, sparkline, DOMAIN, BF_WINDOW, domainFor, pctLabel,
} from '../src/lib/painel.mjs';

test('[TESTE] % vs referência sempre com sinal e palavra (sinal tipográfico, vírgula)', () => {
  assert.equal(formatPct('-7.2'), '−7,2% vs referência');
  assert.equal(formatPct('12.0'), '+12,0% vs referência');
  assert.equal(formatPct('0.0'), '0,0% vs referência');
  assert.equal(formatPct(null), '— vs referência');
});

test('[TESTE] reais no padrão brasileiro, sem float na entrada', () => {
  assert.equal(formatBRL('4050.00'), 'R$ 4.050,00');
  assert.equal(formatBRL('20.00'), 'R$ 20,00');
  assert.equal(formatBRL('1139.90'), 'R$ 1.139,90');
  assert.equal(formatBRL('1234567.89'), 'R$ 1.234.567,89');
  assert.equal(formatBRL(null), '—');
});

test('[TESTE] horário em Brasília', () => {
  assert.equal(formatWhen('2026-11-15T12:45:34Z'), '15/11, 09:45');
  assert.equal(formatWhen('2026-11-23T02:59:00Z'), '22/11, 23:59');
});

test('[TESTE] agrupa por categoria mantendo a ordem do endpoint', () => {
  const ps = [
    { id: 'a', categoria: 'TV e áudio' }, { id: 'b', categoria: 'TV e áudio' },
    { id: 'c', categoria: 'Casa' }, { id: 'd', categoria: 'Controle' },
  ];
  assert.deepEqual(groupByCategory(ps).map(g => [g.categoria, g.produtos.map(p => p.id)]),
    [['TV e áudio', ['a', 'b']], ['Casa', ['c']], ['Controle', ['d']]]);
});

test('[TESTE] mini-gráfico: mesmo eixo de tempo para todos, degraus, referência e faixa da BF', () => {
  assert.equal(DOMAIN.start, Date.parse('2026-11-14T17:50:00Z'));
  assert.equal(DOMAIN.end, Date.parse('2026-12-08T03:00:00Z'));
  assert.equal(BF_WINDOW.start, Date.parse('2026-11-23T03:00:00Z'));
  const serie = [['2026-11-14T17:50:00Z', '100.00'], ['2026-11-14T18:00:00Z', '80.00']];
  const s = sparkline(serie, '90.00', { width: 160, height: 40, now: Date.parse('2026-12-01T12:00:00Z') });
  assert.match(s.path, /^M0(\.0+)? /);           // começa no início do domínio
  assert.ok(s.path.includes(' H '), 'degrau horizontal');
  assert.ok(s.refY > 0 && s.refY < 40);
  const bfX = 160 * (BF_WINDOW.start - DOMAIN.start) / (DOMAIN.end - DOMAIN.start);
  assert.ok(Math.abs(s.bf.x - bfX) < 0.01);
  assert.equal(sparkline([], null, { width: 160, height: 40 }).path, '');
});

test('[TESTE] mini-gráfico com preço constante não divide por zero', () => {
  const s = sparkline([['2026-11-14T17:50:00Z', '20.00'], ['2026-11-15T12:00:00Z', '20.00']], '20.00', { width: 160, height: 40, now: Date.parse('2026-11-15T13:00:00Z') });
  assert.ok(!s.path.includes('NaN') && Number.isFinite(s.refY));
});

const REF = { inicio: '2026-11-14T17:50:00Z', fim: '2026-11-17T17:50:00Z' };
const prod = { disponivel: true, vs_referencia_pct: '-7.2' };

test('[TESTE] referência parcial: cartão diz quando a referência fecha, sem percentual', () => {
  assert.equal(pctLabel(prod, { ...REF, parcial: true }), 'referência fecha em 17/11');
  assert.equal(pctLabel({ disponivel: false, vs_referencia_pct: null }, { ...REF, parcial: true }), 'referência fecha em 17/11');
});

test('[TESTE] referência fechada: cartão mostra o percentual com sinal e palavra', () => {
  assert.equal(pctLabel(prod, { ...REF, parcial: false }), '−7,2% vs referência');
  assert.equal(pctLabel({ disponivel: false, vs_referencia_pct: null }, { ...REF, parcial: false }), '— vs referência');
});

test('[TESTE] eixo até 28/11 00:00 BRT: 14/11 → 28/11, faixa da BF encostada no fim', () => {
  const before = Date.parse('2026-11-28T02:59:59Z');
  assert.deepEqual(domainFor(before), { start: DOMAIN.start, end: BF_WINDOW.end });
  const s = sparkline([['2026-11-15T12:00:00Z', '100.00']], '100.00', { width: 160, height: 40, now: before });
  const bfX = 160 * (BF_WINDOW.start - DOMAIN.start) / (BF_WINDOW.end - DOMAIN.start);
  assert.ok(Math.abs(s.bf.x - bfX) < 0.01);
  assert.ok(Math.abs(s.bf.x + s.bf.width - 160) < 0.01);
});

test('[TESTE] eixo a partir de 28/11 00:00 BRT: 14/11 → 08/12', () => {
  const after = Date.parse('2026-11-28T03:00:00Z');
  assert.deepEqual(domainFor(after), DOMAIN);
  const s = sparkline([['2026-11-15T12:00:00Z', '100.00']], '100.00', { width: 160, height: 40, now: after });
  assert.ok(s.bf.x + s.bf.width < 160 - 1, 'PÓS-BF aparece depois da faixa');
});
