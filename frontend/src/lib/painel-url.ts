// Produção: VITE_PAINEL_URL=https://lowpoint-theta.vercel.app/api/painel nas
// variáveis do projeto lowpoint-web (ver README). Em dev, o Vite faz proxy de /api/painel.
export const PAINEL_URL: string = import.meta.env.VITE_PAINEL_URL
  ?? (import.meta.env.DEV ? '/api/painel' : 'https://lowpoint-theta.vercel.app/api/painel');
