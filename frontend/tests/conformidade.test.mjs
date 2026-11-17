import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Termos de Desenvolvedores do ML: 2.2.4 (nome fora de títulos, botões, chamadas e
// design) e 4.1 (uma menção factual no rodapé). Comentários de código não contam.
export const AVISO_41 = 'O Lowpoint usa a API oficial de catálogo do Mercado Livre. É um projeto independente: não pertence à plataforma nem é aprovado por ela.';
const PROIBIDO = /mercado|\blivre\b|\bML\b|\bmeli\b/i;

const read = p => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');
const semComentarios = s => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').replace(/<!--[\s\S]*?-->/g, '');

export function assertConforme(file, { footer }) {
  const src = semComentarios(read(file));
  const n = src.split(AVISO_41).length - 1;
  assert.equal(n, footer ? 1 : 0, `${file}: aviso 4.1 aparece ${n}x`);
  const resto = src.split(AVISO_41).join('');
  const linha = resto.split('\n').find(l => PROIBIDO.test(l));
  assert.equal(linha, undefined, `${file}: nome da plataforma fora do rodapé: ${linha?.trim()}`);
}

test('[TESTE] landing: nome da plataforma só no aviso 4.1 do rodapé', () => {
  assertConforme('src/App.tsx', { footer: true });
  const footer = read('src/App.tsx').match(/<footer className="site-footer[\s\S]*?<\/footer>/)[0];
  assert.ok(footer.includes(AVISO_41), 'aviso dentro do <footer>');
});

test('[TESTE] landing: metadados e noscript sem o nome da plataforma', () => {
  assertConforme('index.html', { footer: false });
});

test('[TESTE] landing: textos neutros aprovados', () => {
  const app = read('src/App.tsx');
  for (const t of [
    'Histórico de preços · Telegram · código aberto',
    'Escolhe um produto de catálogo e manda o link no Telegram.',
    '…/p/MLB57081243',
    "['Funciona com qualquer link?'",
  ]) assert.ok(app.includes(t), t);
  assert.ok(read('index.html').includes('Monitoramento de preços com histórico, veredito no Telegram.'));
});
