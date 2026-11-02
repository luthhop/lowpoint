"""Spike: test catalog endpoints for price data from third-party listings.

Tests /products/{id}/items and related catalog endpoints.
Read-only — no writes to the ML account.
"""

import json
import os
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
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "user_id": data.get("user_id"),
    }
    TOKENS_PATH.write_text(json.dumps(new_tokens, indent=2), encoding="utf-8")
    return new_tokens


def api_get(url: str, token: str) -> tuple[int, dict | None]:
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    print(f"\n  GET {url}")
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        return resp.status_code, resp.json()
    body = resp.text[:500]
    print(f"  Body: {body}")
    return resp.status_code, None


def test_catalog_items(catalog_id: str, token: str) -> None:
    print(f"\n{'='*60}")
    print(f"CATÁLOGO: {catalog_id}")
    print("=" * 60)

    # 1. /products/{id} — catalog product info
    print("\n--- /products/{id} ---")
    status, product = api_get(
        f"https://api.mercadolibre.com/products/{catalog_id}", token
    )
    if product:
        print(f"  name: {product.get('name')}")
        bbw = product.get("buy_box_winner")
        if bbw:
            print(f"  buy_box_winner.item_id: {bbw.get('item_id')}")
            print(f"  buy_box_winner.price: {bbw.get('price')}")
            print(f"  buy_box_winner.original_price: {bbw.get('original_price')}")
            print(f"  buy_box_winner.seller_id: {bbw.get('seller_id')}")
            print(f"  buy_box_winner keys: {list(bbw.keys())}")
        else:
            print("  buy_box_winner: null/absent")
        print(f"  all top-level keys: {list(product.keys())}")

    # 2. /products/{id}/items — items linked to this catalog product
    print("\n--- /products/{id}/items ---")
    status, items = api_get(
        f"https://api.mercadolibre.com/products/{catalog_id}/items", token
    )
    if items:
        print(f"  Response (first 1500 chars):")
        print(f"  {json.dumps(items, indent=2)[:1500]}")

    # 3. /highlights/MLB/{id} — buy box / featured sellers
    print("\n--- /highlights/MLB/{id} ---")
    status, highlights = api_get(
        f"https://api.mercadolibre.com/highlights/MLB/{catalog_id}", token
    )
    if highlights:
        print(f"  Response (first 1000 chars):")
        print(f"  {json.dumps(highlights, indent=2)[:1000]}")

    # 4. /sites/MLB/search with catalog_product_id — search results include price
    print("\n--- /sites/MLB/search?catalog_product_id={id} ---")
    status, search = api_get(
        f"https://api.mercadolibre.com/sites/MLB/search?catalog_product_id={catalog_id}",
        token,
    )
    if search:
        results = search.get("results", [])
        paging = search.get("paging", {})
        print(f"  total: {paging.get('total')}")
        for r in results[:3]:
            print(f"\n  item_id: {r.get('id')}")
            print(f"    title: {r.get('title')}")
            print(f"    price: {r.get('price')}")
            print(f"    original_price: {r.get('original_price')}")
            print(f"    seller_id: {r.get('seller', {}).get('id')}")
            print(f"    available_quantity: {r.get('available_quantity')}")
            print(f"    condition: {r.get('condition')}")


def main() -> None:
    tokens = load_tokens()

    test = requests.get(
        "https://api.mercadolibre.com/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    if test.status_code == 401:
        print("Token expirado, renovando...")
        tokens = refresh_token(tokens)
        print("Token renovado.\n")

    token = tokens["access_token"]

    catalogs = ["MLB24061510", "MLB57081243"]
    for cat_id in catalogs:
        test_catalog_items(cat_id, token)

    print(f"\n{'='*60}")
    print("SPIKE CATÁLOGO COMPLETO")
    print("=" * 60)


if __name__ == "__main__":
    main()
