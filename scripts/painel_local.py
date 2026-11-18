"""Servidor local do GET /api/painel para desenvolvimento da /ao-vivo.

Usa o mesmo handler do Vercel (api/painel.py) e lê o Neon real numa
transação READ ONLY (lowpoint.painel.fetch_from_db). Não grava nada.

    python scripts/painel_local.py        # http://127.0.0.1:8787/api/painel
    PAINEL_ENABLED=false python scripts/painel_local.py   # simula a vitrine desligada
    cd frontend && npm run dev            # o Vite faz proxy de /api/painel
"""
import os
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Em dev o interruptor vem ligado; PAINEL_ENABLED=false simula a vitrine fora do ar.
os.environ.setdefault("PAINEL_ENABLED", "true")

from api.painel import handler  # noqa: E402

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8787), handler)
    print("painel local em http://127.0.0.1:8787/api/painel (Neon em READ ONLY)", flush=True)
    server.serve_forever()
