import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

const read = p => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const page = read('src/ao-vivo/AoVivo.tsx');
const css = read('src/ao-vivo/ao-vivo.css');
const app = read('src/App.tsx');

test('[TESTE] /ao-vivo é página própria no build do Vite', () => {
  assert.ok(existsSync(new URL('../ao-vivo/index.html', import.meta.url)));
  assert.match(read('vite.config.ts'), /ao-vivo\/index\.html/);
});

test('[TESTE] /ao-vivo tem os textos aprovados', () => {
  for (const t of [
    'Sem veredito ao vivo: o detector de pico precisa de 14 dias de histórico, e o veredito oficial sai na análise de dezembro.',
    'Última coleta:',
    'A coleta está atrasada; os preços abaixo são de',
    'poucos vendedores',
    'Não deu para carregar os preços agora.',
    'https://github.com/luthhop/lowpoint/blob/pre-registro-v1/memoria/analise/plano-pre-registro.md',
    'https://github.com/luthhop/lowpoint/blob/main/memoria/analise/plano-pre-registro.md#emendas',
  ]) assert.ok(page.includes(t), t);
});

test('[TESTE] /ao-vivo sem Forest, sem Ochre e sem palavra de veredito', () => {
  for (const src of [page, css]) {
    assert.doesNotMatch(src, /forest|ochre|#1b6b3a|#7a5a10/i);
  }
  assert.doesNotMatch(page, /Pode ir|Segura|desconto real|Monitorando/i);
});

test('[TESTE] landing: subtítulo e reforço novos, bloco-chamada para /ao-vivo', () => {
  assert.ok(app.includes('Veja ao vivo os preços que o Lowpoint está vigiando. O bot no Telegram está em beta fechado, por convite.'));
  assert.ok(app.includes('Ou só olha a vitrine ao vivo.'));
  assert.ok(app.includes('Os preços reais, agora.'));
  assert.ok(app.includes('Ver a vitrine ao vivo'));
  assert.ok((app.match(/href="\/ao-vivo\/"/g) ?? []).length >= 3, 'hero, bloco-chamada e CTA final');
  assert.ok(!app.includes('e o veredito de cada preço'), 'promessa de veredito ao vivo fora');
});

test('[TESTE] mini-gráfico tem o rótulo "BF" em Plex Mono ~9px, cor #666', () => {
  assert.match(page, /className="live-spark-bf-label[^"]*"[^>]*>\{label\.text\}/);
  const rule = css.match(/\.live-spark-bf-label\{([^}]*)\}/);
  assert.ok(rule, 'regra .live-spark-bf-label');
  assert.match(rule[1], /font-family:var\(--mono\)/);
  assert.match(rule[1], /font-size:9px/);
  assert.match(rule[1], /color:var\(--muted\)/);
});

test('[TESTE] cartão indisponível não renderiza preço, percentual nem gráfico', () => {
  assert.ok(!page.includes('sem oferta nova na última coleta'), 'linha com o último preço removida');
  const card = page.match(/function Card[\s\S]*?\r?\n}\r?\n/)[0];
  assert.ok(read('src/lib/painel.mjs').includes("status: 'indisponível agora'"));
  assert.match(card, /cardView\(/);
  assert.match(card, /v\.state === 'indisponivel'/);
});
