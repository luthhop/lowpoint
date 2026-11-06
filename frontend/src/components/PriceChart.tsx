import { useId, useLayoutEffect, useState } from 'react';
import demo from '../data/demo-history.json';
import { priceCurve } from '../lib/price-curve.mjs';
import { useScrollDrawing } from '../hooks/useMotion';

export function PriceChart({ real = false, small = false }: { real?: boolean; small?: boolean }) {
  const clipId = useId();
  const titleId = useId();
  const ref = useScrollDrawing();
  const [size, setSize] = useState({ width: 1000, height: 220 });
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    const measure = () => {
      const box = node.getBoundingClientRect();
      const next = { width: Math.round(box.width), height: Math.round(box.height) };
      if (next.width > 0 && next.height > 0) setSize(previous => previous.width === next.width && previous.height === next.height ? previous : next);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [ref]);
  const data = real ? demo.points : demo.points.slice(0, -1);
  // Normalize the shorter facade timeline, keeping the same vertical price scale.
  const normalized = data.map(p => ({ ...p, position: p.position / data.at(-1)!.position }));
  const curve = priceCurve(normalized, Math.max(100, size.width - 36), size.height);
  const last = curve.points.at(-1)!;
  const peak = curve.points[5];
  const facade = curve.points[8];
  return (
    <div ref={ref} className={`price-chart ${small ? 'price-chart--small' : 'price-chart--large'} ${real ? 'price-chart--real' : ''}`}>
      <svg viewBox={`-18 0 ${size.width} ${size.height}`} role="img" aria-labelledby={titleId}>
        <title id={titleId}>{real
          ? 'Exemplo ilustrativo: preço normal de R$ 3.450, alta para R$ 6.000, falsa promoção de R$ 3.600 e novo mínimo de R$ 3.200.'
          : 'Exemplo ilustrativo: o preço sobe de R$ 3.450 para R$ 6.000 e cai para R$ 3.600. Ainda está R$ 150 mais caro que antes.'}</title>
        <defs><clipPath id={clipId}><rect x={curve.points.at(-2)!.x} y="0" width={size.width} height={size.height} /></clipPath></defs>
        <path className="price-baseline" d={`M0 ${curve.baselineY}H${size.width - 36}`} />
        <path className="price-line" d={curve.path} pathLength="1" />
        {real && <path className="price-line price-line--real" d={curve.path} pathLength="1" clipPath={`url(#${clipId})`} />}
        <g className="price-end" transform={`translate(${last.x},${last.y})`}>
          <circle className="price-end-ring" r={small ? 9 : 13} />
          <circle className="price-end-dot" r={small ? 4 : 5.5} />
        </g>
        {!small && <g className="price-dates" aria-hidden="true">
          <text x={peak.x} y={peak.y + 36}>{size.width < 600 ? '15 NOV' : '15 NOV · R$ 6.000'}</text>
          <text x={facade.x - 10} y={facade.y - 20}>27 NOV</text>
        </g>}
      </svg>
    </div>
  );
}
