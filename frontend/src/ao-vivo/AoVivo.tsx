import { useEffect, useState } from 'react';
import { bfLabel, cardView, formatBRL, formatWhen, groupByCategory, loadPainel, OFF_MESSAGE, sparkline } from '../lib/painel.mjs';
import { PAINEL_URL } from '../lib/painel-url';

// Contrato de GET /api/painel (memoria/design/painel-ao-vivo.md). Preços em string decimal.
type Produto = {
  id: string; nome: string; categoria: string; url: string;
  preco_atual: string | null; preco_atual_em: string | null; disponivel: boolean; poucas_ofertas: boolean;
  referencia: string | null; vs_referencia_pct: string | null; serie: [string, string][];
};
type Painel = {
  versao: number; gerado_em: string; ultima_coleta: string | null; coleta_atrasada: boolean;
  amostragem: string; referencia: { definicao: string; inicio: string; fim: string; parcial: boolean };
  produtos: Produto[];
};
type Grupo = { categoria: string; produtos: Produto[] };
type State = { status: 'carregando' } | { status: 'ok'; data: Painel } | { status: 'erro' } | { status: 'fora' };
const REPOSITORY = 'https://github.com/luthhop/lowpoint';
const PREREG_TAG = 'https://github.com/luthhop/lowpoint/blob/pre-registro-v1/memoria/analise/plano-pre-registro.md';
const PREREG_EMENDAS = 'https://github.com/luthhop/lowpoint/blob/main/memoria/analise/plano-pre-registro.md#emendas';
const W = 160, H = 44, LABEL_TOP = 12;

function Wordmark() {
  return <span className="wordmark">LOWPOINT<span className="wordmark-dot">.</span></span>;
}

function External({ href, children, className = '' }: { href: string; children: React.ReactNode; className?: string }) {
  return <a className={className} href={href} target="_blank" rel="noopener noreferrer">{children}<span className="link-arrow" aria-hidden="true">↗</span><span className="sr-only"> (abre em nova aba)</span></a>;
}

function Spark({ p, now }: { p: Produto; now: number }) {
  const s = sparkline(p.serie, p.referencia, { width: W, height: H, now, top: LABEL_TOP });
  const label = bfLabel(s.bf, W);
  const aria = (p.referencia ? `Melhor oferta desde 14/11; referência ${formatBRL(p.referencia)}` : 'Melhor oferta desde 14/11')
    + '; faixa marcada: Black Friday, 23 a 27/11';
  return <div className="live-spark-wrap">
    <span className="live-spark-bf-label" aria-hidden="true" style={{ left: label.left, width: label.width }}>{label.text}</span>
    <svg className="live-spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={aria}>
      <rect className="live-spark-bf" x={s.bf.x} y={0} width={s.bf.width} height={H} />
      {s.refY !== null && <line className="live-spark-ref" x1={0} x2={W} y1={s.refY} y2={s.refY} vectorEffect="non-scaling-stroke" />}
      {s.path && <path className="live-spark-line" d={s.path} vectorEffect="non-scaling-stroke" />}
    </svg>
  </div>;
}

function Card({ p, referencia, now }: { p: Produto; referencia: Painel['referencia']; now: number }) {
  const v = cardView(p, referencia);
  const head = <header className="live-card-head"><h3>{p.nome}</h3><External className="live-link mono" href={p.url}>ver anúncio</External></header>;
  if (v.state === 'indisponivel') {
    return <article className="live-card live-card--off">{head}<p className="live-off mono">{v.status}</p></article>;
  }
  return <article className="live-card">
    {head}
    <Spark p={p} now={now} />
    <p className="live-price mono">{v.price}</p>
    <p className="live-pct mono">{v.pct}</p>
    {v.fewOffers && <p className="live-flag mono">poucos vendedores</p>}
  </article>;
}

function Body({ data }: { data: Painel }) {
  const last = data.ultima_coleta ? formatWhen(data.ultima_coleta) : '—';
  const now = Date.parse(data.gerado_em); // hora do servidor: o eixo segue o mesmo JSON em cache
  return <>
    <p className="live-meta mono">Última coleta: {last} · atualiza de hora em hora (a cada 15 min de 23 a 27/11).</p>
    {data.coleta_atrasada && <p className="live-late mono" role="status">A coleta está atrasada; os preços abaixo são de {last}.</p>}
    {(groupByCategory(data.produtos) as Grupo[]).map(g => <section key={g.categoria} className="live-group" aria-label={g.categoria}>
      <h2 className="live-group-title eyebrow">{g.categoria}</h2>
      <div className="live-grid">{g.produtos.map(p => <Card key={p.id} p={p} referencia={data.referencia} now={now} />)}</div>
    </section>)}
  </>;
}

export default function AoVivo() {
  const [state, setState] = useState<State>({ status: 'carregando' });
  useEffect(() => {
    let alive = true;
    loadPainel(fetch, PAINEL_URL).then(s => { if (alive) setState(s as State); });
    return () => { alive = false; };
  }, []);

  return <>
    <a className="skip-link" href="#conteudo">Pular para o conteúdo</a>
    <header className="site-header"><div className="container header-inner"><a href="/" aria-label="Lowpoint, página inicial"><Wordmark /></a><nav aria-label="Navegação principal"><a href="/">Início</a><External href={REPOSITORY}>Ver o código</External></nav></div></header>
    <main id="conteudo" tabIndex={-1} className="live container">
      <div className="live-head">
        <p className="eyebrow">Vitrine / preços reais</p>
        <h1>Ao vivo</h1>
        <p className="live-lede">20 produtos que o Lowpoint está vigiando, atualizados de hora em hora.</p>
      </div>
      <p className="live-notice">Sem veredito ao vivo: o detector de pico precisa de 14 dias de histórico, e o veredito oficial sai na análise de dezembro.</p>
      {state.status === 'carregando' && <p className="live-meta mono" role="status">Carregando os preços…</p>}
      {state.status === 'erro' && <p className="live-late mono" role="status">Não deu para carregar os preços agora.</p>}
      {state.status === 'fora' && <p className="live-late mono" role="status">{OFF_MESSAGE}</p>}
      {state.status === 'ok' && <Body data={state.data} />}
      <footer className="live-method">
        <p className="eyebrow">Método</p>
        <p>Preço = melhor oferta nova do catálogo, coletada de hora em hora (a cada 15 min de 23 a 27/11) e mostrada em blocos de 3h. Referência = mediana de 14/11 14:50 a 17/11 14:50. O percentual compara o preço atual com a referência, truncado para não exagerar.</p>
        <p>As regras da análise foram registradas antes da Black Friday: <External href={PREREG_TAG}>pré-registro v1</External> · <External href={PREREG_EMENDAS}>emendas</External>.</p>
      </footer>
    </main>
    <footer className="site-footer dark"><div className="container footer-inner"><a href="/" aria-label="Voltar ao início"><Wordmark /></a><span className="mono footer-notice">O Lowpoint usa a API oficial de catálogo do Mercado Livre. É um projeto independente: não pertence à plataforma nem é aprovado por ela.</span><External className="mono" href={REPOSITORY}>GitHub</External></div></footer>
  </>;
}
