import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const BOT_INVITE = 'https://t.me/lowpointbr_bot?start=beta';

test('[TESTE] CTAs do wireframe v11: "Ver o código" e "Quero testar"', () => {
  assert.ok(app.includes("const REPOSITORY = 'https://github.com/luthhop/lowpoint'"));
  assert.ok(app.includes(`const BOT_INVITE = '${BOT_INVITE}'`), 'link t.me do bot com ?start=beta');
  const verCodigo = app.match(/>Ver o código</g) ?? [];
  const queroTestar = app.match(/>Quero testar</g) ?? [];
  assert.ok(verCodigo.length >= 3, `"Ver o código" em header, hero e CTA final (achei ${verCodigo.length})`);
  assert.ok(queroTestar.length >= 3, `"Quero testar" em header, hero e CTA final (achei ${queroTestar.length})`);
  assert.ok(!app.includes('Acompanhar no GitHub'), 'CTA final antigo removido');
});

test('[TESTE] alerta PODE IR usa a linha nova (mesma do formatter)', () => {
  assert.ok(app.includes('Esse é de verdade. Pode ir.'));
  assert.ok(app.includes('Menor preço desde que começamos a monitorar. Mesmo depois de subirem antes, tá {realDiscount}% abaixo do normal.'));
  assert.ok(!app.includes('monitorar, {realDiscount}% abaixo do normal'), 'linha antiga removida');
});

test('[TESTE] FAQ "Preciso criar conta?" responde beta por convite', () => {
  const faq = app.match(/\['Preciso criar conta\?', '([^']+)'\]/);
  assert.ok(faq, 'pergunta presente no FAQ');
  assert.match(faq[1], /beta por convite/);
  assert.match(faq[1], /Quero testar/);
});

function faqAnswer(question) {
  const open = `['${question}', '`;
  const start = app.indexOf(open);
  assert.ok(start >= 0, `pergunta "${question}" presente no FAQ`);
  const from = start + open.length;
  return app.slice(from, app.indexOf("']", from));
}

test('[TESTE] FAQ "Quando chega um alerta?" descreve o anti-spam de 14/11', () => {
  const a = faqAnswer('Quando chega um alerta?');
  assert.match(a, /veredito muda/);
  assert.match(a, /3%/);
  assert.match(a, /“Segura”.*1 vez por dia/);
  assert.match(a, /1 aviso por hora/);
  assert.doesNotMatch(a, /abaixo do último aviso/, 'regra antiga removida');
});

test('[TESTE] FAQ e eyebrow alinhados com o beta por convite', () => {
  assert.match(faqAnswer('Já posso usar o bot?'), /beta por convite/);
  assert.ok(!/teste pessoal/i.test(app), 'nenhum "teste pessoal" na landing');
  assert.ok(app.includes('Fase atual / beta por convite'));
});
