import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      // Duas páginas: a landing e a vitrine /ao-vivo/ (sem roteador). Caminhos relativos à raiz do Vite.
      input: { main: 'index.html', aoVivo: 'ao-vivo/index.html' },
    },
  },
  server: {
    host: '127.0.0.1', port: 5173, strictPort: true,
    // Em desenvolvimento, /api/painel vai para o endpoint local (scripts/painel_local.py).
    proxy: { '/api/painel': 'http://127.0.0.1:8787' },
  },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
});
