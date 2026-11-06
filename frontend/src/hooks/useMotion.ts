import { useEffect, useRef } from 'react';

export function useRevealMotion() {
  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    let observer: IntersectionObserver | undefined;
    const configure = () => {
      observer?.disconnect();
      delete document.documentElement.dataset.motion;
      if (media.matches || !('IntersectionObserver' in window)) return;
      const elements = [...document.querySelectorAll<HTMLElement>('[data-reveal]')];
      elements.forEach(el => {
        if (el.getBoundingClientRect().top < innerHeight * .95) el.classList.add('is-visible');
      });
      observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer?.unobserve(entry.target);
          }
        });
      }, { rootMargin: '0px 0px -6% 0px' });
      elements.forEach(el => observer?.observe(el));
      document.documentElement.dataset.motion = 'ready';
    };
    configure();
    media.addEventListener('change', configure);
    return () => {
      observer?.disconnect();
      media.removeEventListener('change', configure);
      delete document.documentElement.dataset.motion;
    };
  }, []);
}

export function useScrollDrawing() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    const update = () => {
      frame = 0;
      const rect = node.getBoundingClientRect();
      const progress = media.matches ? 1 : Math.max(0, Math.min(1, (innerHeight * .96 - rect.top) / (innerHeight * .42)));
      node.style.setProperty('--chart-progress', String(progress));
      node.dataset.complete = String(progress >= .98);
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    addEventListener('scroll', schedule, { passive: true });
    addEventListener('resize', schedule);
    media.addEventListener('change', schedule);
    return () => {
      cancelAnimationFrame(frame);
      removeEventListener('scroll', schedule);
      removeEventListener('resize', schedule);
      media.removeEventListener('change', schedule);
    };
  }, []);
  return ref;
}
