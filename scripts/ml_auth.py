"""One-time OAuth2 authorization for Mercado Livre API.

Usage:
    python scripts/ml_auth.py

Flow:
    1. Prints the authorization URL — open it in a browser
    2. Log in on ML, get redirected to the redirect URI
    3. Copy the "code" parameter from the URL bar
    4. Paste it here — the script exchanges it for tokens
    5. Tokens are saved to ml_tokens.json (gitignored)
"""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
TOKENS_PATH = ROOT / "ml_tokens.json"

load_dotenv(ROOT / ".env")

CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("ML_REDIRECT_URI")

if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
    print("Erro: ML_CLIENT_ID, ML_CLIENT_SECRET e ML_REDIRECT_URI devem estar no .env")
    sys.exit(1)


def build_auth_url() -> str:
    params = urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    return f"https://auth.mercadolivre.com.br/authorization?{params}"


def exchange_code(code: str) -> dict:
    resp = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        json={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()


def save_tokens(data: dict) -> None:
    tokens = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "user_id": data.get("user_id"),
    }
    TOKENS_PATH.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    print(f"\nTokens salvos em {TOKENS_PATH.name}")
    print(f"  user_id: {tokens['user_id']}")
    print(f"  expires_in: {tokens['expires_in']}s")
    if tokens["refresh_token"]:
        print("  refresh_token: presente (renovação automática OK)")
    else:
        print()
        print("  ⚠ refresh_token AUSENTE!")
        print("  O token expira e a autorização precisará ser refeita.")
        print("  Verifique se 'Refresh Token' está ativado no DevCenter do ML")
        print("  e refaça a autorização.")


def main() -> None:
    print("=" * 60)
    print("Lowpoint — Autorização Mercado Livre")
    print("=" * 60)
    print()
    print("1. Abra esta URL no navegador:")
    print()
    print(f"   {build_auth_url()}")
    print()
    print("2. Faça login e autorize o app.")
    print("3. Você será redirecionado para o Google.")
    print("   Copie o parâmetro 'code' da barra de endereço.")
    print("   (Ex: https://www.google.com?code=TG-abc123...)")
    print()

    code = input("4. Cole o code aqui: ").strip()
    if not code:
        print("Nenhum code informado.")
        sys.exit(1)

    print("\nTrocando code por tokens...")
    try:
        data = exchange_code(code)
    except requests.HTTPError as e:
        try:
            error_body = e.response.json()
            msg = error_body.get("message", error_body.get("error", str(e)))
        except Exception:
            msg = e.response.text[:300]
        print(f"\nErro na troca: {msg}")
        print(f"Status HTTP: {e.response.status_code}")
        sys.exit(1)

    save_tokens(data)
    print("\nPronto! Tokens válidos para usar a API.")


if __name__ == "__main__":
    main()
