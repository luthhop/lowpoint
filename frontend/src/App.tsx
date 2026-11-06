import type { ReactNode } from 'react';
import { PriceChart } from './components/PriceChart';
import { useRevealMotion } from './hooks/useMotion';
import { discountPercent, formatPrice } from './lib/price-curve.mjs';
import demo from './data/demo-history.json';

const REPOSITORY = 'https://github.com/luthhop/lowpoint';
const realPrice = demo.points.at(-1)!.priceCents;
const facadePrice = demo.points.at(-2)!.priceCents;
const realDiscount = discountPercent(realPrice, demo.baselineCents);

function Wordmark() {
  return <span className="wordmark">LOWPOINT<span className="wordmark-dot">.</span></span>;
}

function GithubLink({ children = 'GitHub', className = '' }: { children?: ReactNode; className?: string }) {
  return <a className={className} href={REPOSITORY} target="_blank" rel="noopener noreferrer">{children}<span className="link-arrow" aria-hidden="true">↗</span><span className="sr-only"> (abre em nova aba)</span></a>;
}

function ScrollLink({ children, to, className = '' }: { children: ReactNode; to: string; className?: string }) {
  return <a className={`button ${className}`} href={`#${to}`}><span>{children}</span><span className="link-arrow" aria-hidden="true">↓</span></a>;
}

function SectionTitle({ eyebrow, children }: { eyebrow: string; children: ReactNode }) {
  return <div className="section-title" data-reveal><p className="eyebrow">{eyebrow}</p><h2>{children}</h2></div>;
}

function PriceEvidence() {
  return <div className="evidence-scene" aria-label="Exemplo de desconto maquiado no PS5 Digital">
    <div className="evidence-dossier mono"><span>Dossiê 001 — PS5 Digital</span><span>Exemplo ilustrativo</span></div>
    <div className="offer-tag">
      <div className="tag-top mono"><span>Black Friday</span><span>Oferta</span></div>
      <p className="tag-discount">−40%</p>
      <p className="tag-price mono">{formatPrice(facadePrice, true)}</p>
      <p className="tag-original mono">Preço riscado: <del>{formatPrice(demo.crossedOutCents, true)}</del></p>
    </div>
    <svg className="investigation-mark" viewBox="0 0 430 175" fill="none" aria-hidden="true"><path d="M25 153C12 101 68 42 187 32C306 19 405 47 405 94C405 146 290 164 182 158C91 156 36 133 39 100" /></svg>
    <div className="evidence-receipt">
      <div className="receipt-heading mono"><span>O histórico conta outra história</span><span>Ago → Nov</span></div>
      <PriceChart small />
      <div className="receipt-result"><p className="mono"><span>Antes: {formatPrice(demo.baselineCents)}</span><span>Agora: {formatPrice(facadePrice)}</span></p><strong>{formatPrice(facadePrice - demo.baselineCents)} a mais.</strong></div>
    </div>
    <span className="verdict-stamp">Segura.</span>
  </div>;
}

function Hero() {
  return <section className="hero" aria-labelledby="hero-title">
    <div className="hero-inner container">
      <div className="hero-copy" data-reveal>
        <p className="eyebrow"><span className="desktop-copy">Não confie na etiqueta. Confira a história.</span><span className="mobile-copy">Não confie na etiqueta.</span></p>
        <h1 id="hero-title">Tem<br />desconto<br />que engana.</h1>
        <p className="hero-description"><span className="desktop-copy">Preço riscado impressiona. Histórico não mente.<br />O Lowpoint acompanha o produto que você quer e entrega o veredito no Telegram.</span><span className="mobile-copy">A gente confere o histórico.<br />Você recebe o veredito no Telegram.</span></p>
      </div>
      <PriceEvidence />
      <div className="hero-actions" data-reveal>
        <div className="action-row"><ScrollLink to="historia">Ver a história desse preço</ScrollLink><GithubLink className="text-link">O projeto</GithubLink></div>
        <p className="hero-motto mono">Sem gritaria. Sem “corre!”. Com dados.</p>
        <p className="mobile-copy hero-caption mono">Exemplo ilustrativo · preços fictícios<br />Mercado Livre · Telegram · código aberto</p>
      </div>
    </div>
    <div className="hero-strip container mono"><span>Mercado Livre · Telegram · código aberto</span><span>Exemplo ilustrativo. Preços fictícios.</span><a href="#historia">Role para ver a história <span aria-hidden="true">↓</span></a></div>
  </section>;
}

const timeline = [
  { date: 'Ago — 14 Nov', price: demo.baselineCents, title: 'O preço normal', text: 'Meses no mesmo patamar. Essa é a referência antes da alta.', tone: 'normal' },
  { date: '15 Nov', price: demo.crossedOutCents, title: 'A alta antes da oferta', text: 'O preço sobe 74%. O futuro preço riscado acaba de aparecer.', tone: 'hold' },
  { date: '27 Nov', price: facadePrice, title: 'A queda que engana', text: '40% abaixo do pico. Mas R$ 150 acima do que custava antes.', tone: 'hold' },
];

function Timeline() {
  return <section id="historia" className="timeline section-pad" aria-labelledby="history-title">
    <div className="container">
      <div className="section-heading"><h2 id="history-title" data-reveal>O que a etiqueta<br />não te conta.</h2><p className="mono section-aside" data-reveal>Mesmo PS5. Mesmo histórico.<br />Três datas para conferir.</p></div>
      <ol className="timeline-events">{timeline.map((event, i) => <li key={event.date} className={`timeline-event tone-${event.tone}`} data-reveal style={{ '--reveal-delay': `${i * 80}ms` } as React.CSSProperties}>
        <span className="event-index mono" aria-hidden="true">0{i + 1}</span><div className="event-content"><p className="event-date mono"><span className="desktop-copy">0{i + 1} / </span>{event.date}</p><p className="event-price mono">{formatPrice(event.price)}</p><h3>{event.title}</h3><p>{event.text}</p></div>
      </li>)}</ol>
    </div>
  </section>;
}

function Resolution() {
  return <section className="resolution dark" aria-labelledby="resolution-title">
    <div className="resolution-inner container">
      <p className="resolution-date eyebrow">04 / 02 Dez — o desconto real</p>
      <h2 id="resolution-title" className="resolution-title" data-reveal>O preço cai.<br />A dúvida<br />também.</h2>
      <div className="resolution-aside" data-reveal><p>{formatPrice(realPrice)}: {realDiscount}% abaixo do preço normal e abaixo do alvo de {formatPrice(demo.targetCents)}.</p><p className="mono desktop-copy">Sem adivinhar.<br />Sem cair no preço riscado.</p></div>
      <div className="resolution-actions action-row"><ScrollLink to="alerta" className="button--light">Ver o alerta que chega</ScrollLink><GithubLink className="text-link desktop-copy">Conhecer o projeto</GithubLink></div>
      <div className="resolution-plot"><PriceChart real /></div>
      <div className="resolution-normal mono"><span>Antes da alta</span><span>{formatPrice(demo.baselineCents)}</span></div>
      <div className="resolution-current"><div><p className="eyebrow">Novo menor preço</p><p className="current-price mono">{formatPrice(realPrice)}</p></div><span className="verdict-badge">Pode ir.</span></div>
      <p className="resolution-caption mono mobile-copy">PS5 Digital · exemplo com preços fictícios<br />Preço normal {formatPrice(demo.baselineCents)} · agora {formatPrice(realPrice)}</p>
    </div>
  </section>;
}

function AlertPreview() {
  return <section id="alerta" className="alert-section dark" aria-labelledby="alert-title">
    <div className="container alert-layout"><div className="alert-intro" data-reveal><p className="eyebrow">Do histórico para o teu Telegram</p><h2 id="alert-title">O veredito chega.<br />A decisão é tua.</h2><p>Você escolhe o produto e quanto quer pagar.<br />O Lowpoint acompanha o preço e confere a história.</p></div>
      <article className="alert-preview" data-reveal aria-label="Trecho ilustrativo de um alerta do Lowpoint"><header><strong>Pode ir</strong><span className="mono">Lowpoint / Telegram</span></header><p className="alert-product mono"><span className="desktop-copy">PS5 Digital</span><span className="mobile-copy">PS5</span> · {formatPrice(realPrice, true)}</p><p>Bateu teu alvo de {formatPrice(demo.targetCents, true)}.<br />Menor preço desde que começamos a monitorar, {realDiscount}% abaixo do normal.</p><p className="alert-disclaimer mono">Trecho do alerta · exemplo com preços fictícios</p></article>
    </div>
  </section>;
}

const steps = [
  ['Manda o link', 'Escolhe um produto de catálogo do Mercado Livre e manda o link no Telegram.'],
  ['Define teu alvo', 'Diz quanto quer pagar. O produto fica na tua lista de monitoramento.'],
  ['Recebe o aviso', 'Coletas programadas a cada hora. O alerta chega com contexto quando os critérios são atingidos.'],
];

function HowItWorks() {
  return <section id="como-funciona" className="how section-pad" aria-labelledby="how-title"><div className="container">
    <div className="section-heading"><SectionTitle eyebrow="Como funciona"><span id="how-title">Você escolhe.<br />A gente fica de olho.</span></SectionTitle><p className="section-aside" data-reveal>Um produto que você quer.<br />Um preço que faz sentido pra você.<br />O histórico ajuda a decidir.</p></div>
    <div className="how-layout"><ol className="steps">{steps.map(([title, text], i) => <li key={title} data-reveal><span className="step-number mono" aria-hidden="true">0{i + 1}</span><div><h3>{title}</h3><p>{text}</p></div></li>)}</ol>
      <aside className="command-demo" data-reveal aria-label="Exemplo de como adicionar um produto"><p className="eyebrow">Exemplo de comando / Telegram</p><div className="command"><span className="mono">Você</span><code>/adicionar<br />mercadolivre.com.br/p/MLB57081243<br />3300 PS5</code></div><h3>Produto escolhido.<br />Alvo definido.</h3><p>Você acompanha a tua lista.<br />O Lowpoint acompanha os preços.</p><p className="demo-note mono">Demonstração ilustrativa.<br />O bot ainda está em teste pessoal.</p></aside>
    </div>
  </div></section>;
}

const verdicts = [
  { label: 'Pode ir', title: 'Desconto com histórico.', description: 'Novo menor preço, pelo menos 5% abaixo do preço normal. O desconto passa pelos critérios do Lowpoint.', tone: 'real' },
  { label: 'Segura', title: 'A conta não fecha.', description: 'A queda parece maior do que é. O histórico não sustenta o desconto anunciado.', tone: 'hold' },
  { label: 'Monitorando', title: 'Ainda sem sinal verde.', description: 'Falta histórico ou o preço ainda não atende aos critérios de desconto real. Se bater teu alvo, o bot pode avisar.', tone: 'normal' },
];

function Verdicts() {
  return <section id="vereditos" className="verdicts section-pad" aria-labelledby="verdicts-title"><div className="container"><div className="section-heading"><SectionTitle eyebrow="Os vereditos"><span id="verdicts-title">Três respostas.<br />Nenhuma pressão.</span></SectionTitle><p className="section-aside" data-reveal>O selo vem do histórico.<br />A decisão continua sendo tua.</p></div>
    <dl className="verdict-list">{verdicts.map(item => <div key={item.tone} className={`verdict-row tone-${item.tone}`} data-reveal><dt>{item.label}</dt><dd><h3>{item.title}</h3><p>{item.description}</p></dd></div>)}</dl>
  </div></section>;
}

const questions = [
  ['Já posso usar o bot?', 'Por enquanto, o Lowpoint está em teste pessoal, com acesso restrito. Você pode acompanhar o desenvolvimento e o código no GitHub.'],
  ['Funciona com qualquer link do Mercado Livre?', 'Nesta versão, usamos links de produtos de catálogo: aqueles com /p/MLB no endereço. Links de anúncios individuais ainda não são aceitos.'],
  ['Quando chega um alerta?', 'As coletas são programadas a cada hora. O bot confere o alvo e o histórico antes de avisar. O mesmo tipo de alerta só é reenviado se o preço cair abaixo do último aviso.'],
  ['E se ainda não houver histórico?', 'Antes de completar sete dias de monitoramento, o bot pode avisar que o alvo foi atingido, mas não afirma que encontrou um desconto real.'],
  ['Como trata ofertas suspeitas?', 'O Lowpoint compara os preços para filtrar ofertas muito abaixo do padrão e informa quando alguma foi ignorada. Vale conferir o vendedor e as condições da oferta.'],
  ['Você ganha comissão se eu comprar?', 'Hoje não há links de afiliado. A regra do projeto é que uma comissão nunca influencie o veredito.'],
];

function FAQ() {
  return <section id="perguntas" className="faq section-pad" aria-labelledby="faq-title"><div className="container faq-layout"><div className="faq-intro" data-reveal><SectionTitle eyebrow="Perguntas frequentes"><span id="faq-title">Perguntas<br />sem rodeio.</span></SectionTitle><p>Tudo que você precisa saber<br />sobre esta versão do Lowpoint.</p><p className="eyebrow">Fase atual / teste pessoal</p></div><div className="faq-items">{questions.map(([q, a], i) => <details key={q} name="lowpoint-faq" open={i === 0 || undefined} data-reveal><summary>{q}<span className="faq-symbol" aria-hidden="true">+</span></summary><p>{a}</p></details>)}</div></div></section>;
}

function FinalCTA() {
  return <section className="final-cta dark section-pad" aria-labelledby="cta-title"><div className="container"><p className="eyebrow" data-reveal>Código aberto / em desenvolvimento</p><h2 id="cta-title" data-reveal>Antes de comprar,<br />confere a história.</h2><div className="cta-bottom" data-reveal><p>O Lowpoint está em desenvolvimento.<br />Acompanhe o código, as decisões e a evolução do projeto.</p><GithubLink className="button button--light">Acompanhar no GitHub</GithubLink></div></div></section>;
}

export default function App() {
  useRevealMotion();
  return <>
    <a className="skip-link" href="#conteudo">Pular para o conteúdo</a>
    <header id="inicio" className="site-header"><div className="container header-inner"><a href="#inicio" aria-label="Lowpoint, início"><Wordmark /></a><nav aria-label="Navegação principal"><a href="#como-funciona">Como funciona</a><a href="#vereditos">Os vereditos</a><a href="#perguntas">Perguntas</a><GithubLink /></nav></div></header>
    <main id="conteudo" tabIndex={-1}><Hero /><Timeline /><Resolution /><AlertPreview /><HowItWorks /><Verdicts /><FAQ /><FinalCTA /></main>
    <footer className="site-footer dark"><div className="container footer-inner"><a href="#inicio" aria-label="Voltar ao início"><Wordmark /></a><span className="mono">Acompanhe o desenvolvimento</span><GithubLink className="mono" /></div></footer>
  </>;
}
