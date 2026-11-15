"""Servidor local do GET /api/painel para desenvolvimento da /ao-vivo.

Usa o mesmo handler do Vercel (api/painel.py) e lê o Neon real numa
transação READ ONLY (lowpoint.painel.fetch_from_db). Não grava nada.

    python scripts/painel_local.py        # http://127.0.0.1:8787/api/painel
    cd frontend && npm run dev            # o Vite faz proxy de /api/painel
"""
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.painel import handler  # noqa: E402

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8787), handler)
    print("painel local em http://127.0.0.1:8787/api/painel (Neon em READ ONLY)", flush=True)
    server.serve_forever()
