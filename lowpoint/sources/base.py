from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class OfferData:
    item_id: str
    seller_id: int
    price: Decimal
    original_price: Decimal | None
    condition: str
    official_store_id: int | None
    free_shipping: bool
    warranty: str | None


@dataclass(frozen=True)
class CatalogSnapshot:
    catalog_product_id: str
    title: str
    image_url: str | None
    offers: list[OfferData]
    collected_at: datetime


class PriceSource(ABC):
    @abstractmethod
    def fetch_catalog(self, catalog_product_id: str) -> CatalogSnapshot:
        ...

    @abstractmethod
    def fetch_catalogs_batch(
        self, catalog_product_ids: list[str]
    ) -> dict[str, CatalogSnapshot]:
        ...
