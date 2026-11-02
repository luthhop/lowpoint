"""Spike: test ML API endpoints with real products.

Usage:
    python scripts/ml_spike.py

Requires ml_tokens.json from ml_auth.py.
Read-only — no writes to the ML account.
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
TOKENS_PATH = ROOT / "ml_tokens.json"

load_dotenv(ROOT / ".env")

CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")


def load_tokens() -> dict:
    if not TOKENS_PATH.exists():
        print("Erro: ml_tokens.json não encontrado. Rode ml_auth.py primeiro.")
        sys.exit(1)
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def refresh_token(tokens: dict) -> dict:
    resp = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        json={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": tokens["refresh_token"],
        },
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()
    new_tokens = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_in": data.get("expires_in"),
        "user_id": data.get("user_id"),
    }
    TOKENS_PATH.write_text(json.dumps(new_tokens, indent=2), encoding="utf-8")
    return new_tokens


def api_get(url: str, token: str) -> dict | None:
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    print(f"\n  GET {url}")
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        return resp.json()
    print(f"  Body: {resp.text[:500]}")
    return None


def extract_item_id(url: str) -> str | None:
    """Extract MLB item ID from a mercadolivre.com.br listing URL."""
    match = re.search(r"(MLB)-?(\d+)", url)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    return None


def extract_catalog_id(url: str) -> str | None:
    """Extract catalog product ID from /p/MLB... URL."""
    match = re.search(r"/p/(MLB\d+)", url)
    if match:
        return match.group(1)
    return None


def test_item(item_id: str, token: str) -> None:
    print(f"\n{'='*60}")
    print(f"TESTE: item {item_id}")
    print("=" * 60)

    # 1. /items/{id} — metadata + deprecated price fields
    print("\n--- /items/{id} (metadados + preço legado) ---")
    item = api_get(f"https://api.mercadolibre.com/items/{item_id}", token)
    if item:
        print(f"  title: {item.get('title')}")
        print(f"  price: {item.get('price')}")
        print(f"  base_price: {item.get('base_price')}")
        print(f"  original_price: {item.get('original_price')}")
        print(f"  currency_id: {item.get('currency_id')}")
        print(f"  status: {item.get('status')}")
        print(f"  available_quantity: {item.get('available_quantity')}")
        print(f"  catalog_product_id: {item.get('catalog_product_id')}")
        print(f"  thumbnail: {item.get('thumbnail')}")
        print(f"  permalink: {item.get('permalink')}")

    # 2. /items/{id}/sale_price — new price endpoint
    print("\n--- /items/{id}/sale_price ---")
    sale = api_get(f"https://api.mercadolibre.com/items/{item_id}/sale_price", token)
    if sale:
        print(f"  amount: {sale.get('amount')}")
        print(f"  regular_amount: {sale.get('regular_amount')}")
        print(f"  currency_id: {sale.get('currency_id')}")
        print(f"  reference_date: {sale.get('reference_date')}")
        print(f"  metadata: {json.dumps(sale.get('metadata', {}), indent=4)}")

    # 3. /items/{id}/prices — all price types
    print("\n--- /items/{id}/prices ---")
    prices = api_get(f"https://api.mercadolibre.com/items/{item_id}/prices", token)
    if prices:
        print(f"  Full response: {json.dumps(prices, indent=2)[:1000]}")


def test_catalog(catalog_id: str, token: str) -> None:
    print(f"\n{'='*60}")
    print(f"TESTE CATÁLOGO: {catalog_id}")
    print("=" * 60)

    # 1. /products/{id} — catalog product info
    print("\n--- /products/{id} ---")
    product = api_get(f"https://api.mercadolibre.com/products/{catalog_id}", token)
    if product:
        print(f"  name: {product.get('name')}")
        print(f"  buy_box_winner: {json.dumps(product.get('buy_box_winner', {}), indent=2)[:500]}")
        print(f"  status: {product.get('status')}")
        keys = list(product.keys())
        print(f"  all keys: {keys}")

    # 2. /highlights/MLB/{catalog_id} — buy box / best seller
    print("\n--- /highlights/MLB/{catalog_id} ---")
    highlights = api_get(
        f"https://api.mercadolibre.com/highlights/MLB/{catalog_id}", token
    )
    if highlights:
        print(f"  Full response: {json.dumps(highlights, indent=2)[:1000]}")

    # 3. Search items by catalog_product_id
    print("\n--- /sites/MLB/search?catalog_product_id={id} ---")
    search = api_get(
        f"https://api.mercadolibre.com/sites/MLB/search?catalog_product_id={catalog_id}",
        token,
    )
    if search:
        results = search.get("results", [])
        print(f"  total results: {search.get('paging', {}).get('total')}")
        if results:
            winner = results[0]
            print(f"  first result (buy box winner):")
            print(f"    item_id: {winner.get('id')}")
            print(f"    title: {winner.get('title')}")
            print(f"    price: {winner.get('price')}")
            print(f"    original_price: {winner.get('original_price')}")
            print(f"    seller_id: {winner.get('seller', {}).get('id')}")


def test_multiget(item_ids: list[str], token: str) -> None:
    print(f"\n{'='*60}")
    print(f"TESTE MULTIGET: {item_ids}")
    print("=" * 60)

    ids_param = ",".join(item_ids)
    data = api_get(f"https://api.mercadolibre.com/items?ids={ids_param}", token)
    if data:
        for entry in data:
            code = entry.get("code")
            body = entry.get("body", {})
            print(f"\n  [{code}] {body.get('id')}: {body.get('title', 'N/A')}")
            print(f"    price: {body.get('price')}, original: {body.get('original_price')}")


def main() -> None:
    tokens = load_tokens()

    # Try a simple call; if 401, refresh
    test = requests.get(
        "https://api.mercadolibre.com/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    if test.status_code == 401:
        print("Token expirado, renovando...")
        tokens = refresh_token(tokens)
        print("Token renovado.\n")

    token = tokens["access_token"]

    # ---- Produtos reais do Lucas ----
    products = [
        {
            "name": "LG UltraGear 32GN600",
            "catalog_id": "MLB24061510",
            "item_id": "MLB5299585130",
        },
        {
            "name": "PS5 Slim Digital (Astro Bot + GT7)",
            "catalog_id": "MLB57081243",
            "item_id": "MLB4214670787",
        },
    ]

    for p in products:
        # Test catalog endpoint
        test_catalog(p["catalog_id"], token)
        # Test item endpoints (the specific listing from the URL)
        test_item(p["item_id"], token)

    # Test multiget with both item IDs
    test_multiget([p["item_id"] for p in products], token)

    print("\n" + "=" * 60)
    print("SPIKE COMPLETO")
    print("=" * 60)


if __name__ == "__main__":
    main()
