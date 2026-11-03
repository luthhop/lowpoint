import os
from datetime import datetime, timezone
from decimal import Decimal

import requests
from dotenv import load_dotenv

from lowpoint.sources.base import CatalogSnapshot, OfferData, PriceSource

load_dotenv()

_API_BASE = "https://api.mercadolibre.com"


class MLCatalogSource(PriceSource):
    def __init__(self, session_factory=None):
        if session_factory is None:
            from lowpoint.db import SessionLocal
            session_factory = SessionLocal
        self._session_factory = session_factory
        self._access_token: str | None = None

    def _load_token(self) -> str:
        if self._access_token:
            return self._access_token
        from lowpoint.models import MLToken

        session = self._session_factory()
        try:
            row = session.query(MLToken).first()
            if not row:
                raise RuntimeError(
                    "Token ML não encontrado no banco. "
                    "Rode: python scripts/migrate_ml_tokens.py"
                )
            self._access_token = row.access_token
            return self._access_token
        finally:
            session.close()

    def _refresh_token(self) -> str:
        from lowpoint.models import MLToken

        session = self._session_factory()
        try:
            row = session.query(MLToken).with_for_update().first()
            if not row:
                raise RuntimeError("Token ML não encontrado no banco.")

            resp = requests.post(
                f"{_API_BASE}/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": os.environ.get("ML_CLIENT_ID"),
                    "client_secret": os.environ.get("ML_CLIENT_SECRET"),
                    "refresh_token": row.refresh_token,
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            new_data = resp.json()

            row.access_token = new_data["access_token"]
            row.refresh_token = new_data.get("refresh_token")
            row.expires_in = new_data.get("expires_in")
            row.user_id = new_data.get("user_id")
            session.commit()

            self._access_token = row.access_token
            return self._access_token
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _get(self, url: str) -> dict:
        token = self._load_token()
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 401:
            self._access_token = None
            token = self._refresh_token()
            resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        return resp.json()

    def _fetch_product_info(self, catalog_product_id: str) -> tuple[str, str | None]:
        data = self._get(f"{_API_BASE}/products/{catalog_product_id}")
        title = data.get("name", "")
        pictures = data.get("pictures", [])
        image_url = pictures[0]["url"] if pictures else None
        return title, image_url

    def fetch_catalog(self, catalog_product_id: str) -> CatalogSnapshot:
        now = datetime.now(timezone.utc)
        offers: list[OfferData] = []
        offset = 0
        limit = 50
        title, image_url = self._fetch_product_info(catalog_product_id)

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
                        item_id=item.get("item_id") or item.get("id", ""),
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
