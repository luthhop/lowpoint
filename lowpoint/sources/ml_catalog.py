import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import requests
from dotenv import load_dotenv

from lowpoint.sources.base import CatalogSnapshot, OfferData, PriceSource

load_dotenv()

_TOKENS_PATH = Path(__file__).resolve().parent.parent.parent / "ml_tokens.json"
_API_BASE = "https://api.mercadolibre.com"


class MLCatalogSource(PriceSource):
    def __init__(self, tokens_path: Path | None = None):
        self._tokens_path = tokens_path or _TOKENS_PATH
        self._access_token: str | None = None

    def _load_token(self) -> str:
        if self._access_token:
            return self._access_token
        data = json.loads(self._tokens_path.read_text(encoding="utf-8"))
        self._access_token = data["access_token"]
        return self._access_token

    def _refresh_token(self) -> str:
        data = json.loads(self._tokens_path.read_text(encoding="utf-8"))
        resp = requests.post(
            f"{_API_BASE}/oauth/token",
            json={
                "grant_type": "refresh_token",
                "client_id": os.environ.get("ML_CLIENT_ID"),
                "client_secret": os.environ.get("ML_CLIENT_SECRET"),
                "refresh_token": data.get("refresh_token"),
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        new_data = resp.json()
        tokens = {
            "access_token": new_data["access_token"],
            "refresh_token": new_data.get("refresh_token"),
            "expires_in": new_data.get("expires_in"),
            "user_id": new_data.get("user_id"),
        }
        self._tokens_path.write_text(
            json.dumps(tokens, indent=2), encoding="utf-8"
        )
        self._access_token = tokens["access_token"]
        return self._access_token

    def _get(self, url: str) -> dict:
        token = self._load_token()
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 401:
            token = self._refresh_token()
            resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        return resp.json()

    def fetch_catalog(self, catalog_product_id: str) -> CatalogSnapshot:
        now = datetime.now(timezone.utc)
        offers: list[OfferData] = []
        offset = 0
        limit = 50
        title = ""
        image_url = None

        while True:
            url = (
                f"{_API_BASE}/products/{catalog_product_id}/items"
                f"?offset={offset}&limit={limit}"
            )
            data = self._get(url)
            results = data.get("results", data) if isinstance(data, dict) else data

            if isinstance(data, dict):
                paging = data.get("paging", {})
                results = data.get("results", [])
            else:
                results = data
                paging = {}

            for item in results:
                if not title and item.get("title"):
                    title = item["title"]
                if not image_url and item.get("thumbnail"):
                    image_url = item["thumbnail"]

                shipping = item.get("shipping", {})
                sale_price = item.get("sale_price", {})
                price_raw = sale_price.get("amount") if sale_price else item.get("price")
                original_raw = (
                    sale_price.get("regular_amount")
                    if sale_price
                    else item.get("original_price")
                )

                if price_raw is None:
                    continue

                offers.append(
                    OfferData(
                        item_id=item.get("id", ""),
                        seller_id=item.get("seller_id", item.get("seller", {}).get("id", 0)),
                        price=Decimal(str(price_raw)),
                        original_price=(
                            Decimal(str(original_raw)) if original_raw else None
                        ),
                        condition=item.get("condition", "new"),
                        official_store_id=item.get("official_store_id"),
                        free_shipping=shipping.get("free_shipping", False),
                        warranty=item.get("warranty"),
                    )
                )

            total = paging.get("total", len(results))
            offset += limit
            if offset >= total or not results:
                break

        return CatalogSnapshot(
            catalog_product_id=catalog_product_id,
            title=title,
            image_url=image_url,
            offers=offers,
            collected_at=now,
        )

    def fetch_catalogs_batch(
        self, catalog_product_ids: list[str]
    ) -> dict[str, CatalogSnapshot]:
        return {
            cid: self.fetch_catalog(cid)
            for cid in catalog_product_ids
        }
