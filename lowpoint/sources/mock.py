from lowpoint.sources.base import CatalogSnapshot, PriceSource


class MockSource(PriceSource):
    def __init__(self, responses: dict[str, CatalogSnapshot] | None = None):
        self._responses = responses or {}

    def set_response(self, catalog_id: str, snapshot: CatalogSnapshot) -> None:
        self._responses[catalog_id] = snapshot

    def fetch_catalog(self, catalog_product_id: str) -> CatalogSnapshot:
        if catalog_product_id not in self._responses:
            raise KeyError(f"No mock response for {catalog_product_id}")
        return self._responses[catalog_product_id]

    def fetch_catalogs_batch(
        self, catalog_product_ids: list[str]
    ) -> dict[str, CatalogSnapshot]:
        return {
            cid: self.fetch_catalog(cid)
            for cid in catalog_product_ids
            if cid in self._responses
        }
