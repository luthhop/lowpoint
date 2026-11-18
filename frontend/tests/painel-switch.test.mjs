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

// Sem esperar de verdade e sem poluir o console do teste.
function quiet() {
  const waits = [], logs = [];
  return { waits, logs, opts: { sleep: async ms => { waits.push(ms); }, log: (...a) => logs.push(a.join(' ')) } };
}

// Respostas em sequência: [503, 200] = falha na 1ª, funciona na 2ª.
function seqFetch(statuses, body = { versao: 1 }) {
  const calls = [];
  const fn = async url => {
    const s = statuses[Math.min(calls.length, statuses.length - 1)];
    calls.push(url);
    if (s === 'rede') throw new TypeError('Failed to fetch');
    return { ok: s >= 200 && s < 300, status: s, json: async () => body };
  };
  fn.calls = calls;
  return fn;
}

test('[TESTE] /ao-vivo: 200 = dados, 404 = fora do ar, resto = erro', async () => {
  const q = quiet();
  assert.deepEqual(await loadPainel(fakeFetch(200, { versao: 1 }), URL_, q.opts), { status: 'ok', data: { versao: 1 } });
  assert.deepEqual(await loadPainel(fakeFetch(404), URL_, q.opts), { status: 'fora' });
  for (const s of [500, 503, 400]) assert.deepEqual(await loadPainel(fakeFetch(s), URL_, q.opts), { status: 'erro' });
  assert.deepEqual(await loadPainel(failing, URL_, q.opts), { status: 'erro' });
});

test('[TESTE] /ao-vivo: no erro, espera ~3 s e tenta de novo uma vez', async () => {
  const q = quiet();
  const f = seqFetch([503, 200]);
  assert.deepEqual(await loadPainel(f, URL_, q.opts), { status: 'ok', data: { versao: 1 } });
  assert.equal(f.calls.length, 2);
  assert.deepEqual(q.waits, [3000]);
});

test('[TESTE] /ao-vivo: duas falhas = mensagem de erro, sem 3ª tentativa', async () => {
  const q = quiet();
  const f = seqFetch([503, 500, 200]);
  assert.deepEqual(await loadPainel(f, URL_, q.opts), { status: 'erro' });
  assert.equal(f.calls.length, 2);
  assert.deepEqual(q.waits, [3000]);
});

test('[TESTE] /ao-vivo: registra o status HTTP (ou falha de rede) no console', async () => {
  const q = quiet();
  await loadPainel(seqFetch([503, 'rede']), URL_, q.opts);
  assert.equal(q.logs.length, 2);
  assert.match(q.logs[0], /\[painel\].*HTTP 503.*tentativa 1\/2/);
  assert.match(q.logs[1], /\[painel\].*rede.*Failed to fetch.*tentativa 2\/2/);
});

test('[TESTE] /ao-vivo: JSON inválido também conta como erro e é registrado', async () => {
  const q = quiet();
  const bad = async () => ({ ok: true, status: 200, json: async () => { throw new SyntaxError('Unexpected end of JSON input'); } });
  assert.deepEqual(await loadPainel(bad, URL_, q.opts), { status: 'erro' });
  assert.match(q.logs[0], /JSON.*Unexpected end/);
});

test('[TESTE] /ao-vivo: 404 (interruptor desligado) não tenta de novo nem registra erro', async () => {
  const q = quiet();
  const f = seqFetch([404, 200]);
  assert.deepEqual(await loadPainel(f, URL_, q.opts), { status: 'fora' });
  assert.equal(f.calls.length, 1);
  assert.deepEqual(q.waits, []);
  assert.deepEqual(q.logs, []);
});

test('[TESTE] /ao-vivo: padrão é 3 s e console.warn', async () => {
  const { RETRY_DELAY_MS } = await import('../src/lib/painel.mjs');
  assert.equal(RETRY_DELAY_MS, 3000);
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
