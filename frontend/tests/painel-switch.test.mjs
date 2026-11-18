import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { loadPainel, painelOnline, OFF_MESSAGE } from '../src/lib/painel.mjs';

const read = p => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const URL_ = 'https://lowpoint-theta.vercel.app/api/painel';

// fetch falso: devolve o status pedido e registra as chamadas (sem rede).
function fakeFetch(status, body = { versao: 1, produtos: [] }) {
  const calls = [];
  const fn = async (url, init = {}) => {
    calls.push({ url, method: init.method ?? 'GET' });
    return { ok: status >= 200 && status < 300, status, json: async () => body };
  };
  fn.calls = calls;
  return fn;
}
const failing = async () => { throw new TypeError('Failed to fetch'); };

test('[TESTE] interruptor: mensagem de vitrine desligada', () => {
  assert.equal(OFF_MESSAGE, 'Vitrine fora do ar no momento.');
});

test('[TESTE] /ao-vivo: 200 = dados, 404 = fora do ar, resto = erro', async () => {
  assert.deepEqual(await loadPainel(fakeFetch(200, { versao: 1 }), URL_), { status: 'ok', data: { versao: 1 } });
  assert.deepEqual(await loadPainel(fakeFetch(404), URL_), { status: 'fora' });
  for (const s of [500, 503, 400]) assert.deepEqual(await loadPainel(fakeFetch(s), URL_), { status: 'erro' });
  assert.deepEqual(await loadPainel(failing, URL_), { status: 'erro' });
});

test('[TESTE] landing: bloco-chamada só com o painel no ar (HEAD, sem baixar o JSON)', async () => {
  const on = fakeFetch(200);
  assert.equal(await painelOnline(on, URL_), true);
  assert.deepEqual(on.calls, [{ url: URL_, method: 'HEAD' }]);
  assert.equal(await painelOnline(fakeFetch(404), URL_), false);
  assert.equal(await painelOnline(fakeFetch(503), URL_), false);
  assert.equal(await painelOnline(failing, URL_), false);
});

test('[TESTE] /ao-vivo mostra OFF_MESSAGE no estado "fora"', () => {
  const page = read('src/ao-vivo/AoVivo.tsx');
  assert.match(page, /status === 'fora'[\s\S]{0,120}OFF_MESSAGE/);
  assert.match(page, /loadPainel\(fetch, PAINEL_URL\)/);
});

test('[TESTE] landing: bloco-chamada escondido até painelOnline confirmar', () => {
  const app = read('src/App.tsx');
  assert.match(app, /painelOnline\(fetch, PAINEL_URL\)/);
  // começa escondido (false) e só renderiza quando online
  assert.match(app, /useState\(false\)/);
  assert.match(app, /if \(!online\) return null;/);
});

test('[TESTE] landing e /ao-vivo usam a mesma URL do painel', () => {
  for (const p of ['src/App.tsx', 'src/ao-vivo/AoVivo.tsx']) {
    assert.match(read(p), /import \{ PAINEL_URL \} from '(\.\.\/|\.\/)lib\/painel-url'/);
  }
});
