import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from lowpoint.sources.base import CatalogSnapshot, OfferData
from lowpoint.sources.mock import MockSource
from lowpoint.sources.ml_catalog import MLCatalogSource

FIXTURES = Path(__file__).parent / "fixtures"


class TestMockSource:
    def test_fetch_catalog(self):
        snapshot = CatalogSnapshot(
            catalog_product_id="MLB24061510",
            title="Monitor LG",
            image_url="https://example.com/img.jpg",
            offers=[
                OfferData(
                    item_id="MLB1",
                    seller_id=1,
                    price=Decimal("1329.00"),
                    original_price=Decimal("2180.00"),
                    condition="new",
                    official_store_id=1234,
                    free_shipping=True,
                    warranty="12 meses",
                ),
            ],
            collected_at=datetime.now(timezone.utc),
        )
        source = MockSource({"MLB24061510": snapshot})
        result = source.fetch_catalog("MLB24061510")
        assert result.title == "Monitor LG"
        assert len(result.offers) == 1
        assert result.offers[0].price == Decimal("1329.00")

    def test_fetch_batch(self):
        s1 = CatalogSnapshot(
            catalog_product_id="A",
            title="A",
            image_url=None,
            offers=[],
            collected_at=datetime.now(timezone.utc),
        )
        s2 = CatalogSnapshot(
            catalog_product_id="B",
            title="B",
            image_url=None,
            offers=[],
            collected_at=datetime.now(timezone.utc),
        )
        source = MockSource({"A": s1, "B": s2})
        result = source.fetch_catalogs_batch(["A", "B", "C"])
        assert set(result.keys()) == {"A", "B"}

    def test_missing_raises(self):
        source = MockSource()
        try:
            source.fetch_catalog("MISSING")
            assert False, "Should have raised"
        except KeyError:
            pass


class TestMLCatalogSourceParsing:
    def test_parse_fixture(self):
        fixture_data = json.loads(
            (FIXTURES / "ml_catalog_response.json").read_text(encoding="utf-8")
        )

        source = MLCatalogSource.__new__(MLCatalogSource)

        with patch.object(source, "_get", return_value=fixture_data):
            result = source.fetch_catalog("MLB24061510")

        assert result.catalog_product_id == "MLB24061510"
        assert result.title == "Monitor Gamer LG UltraGear 32GN600 32\" VA QHD 165Hz"
        assert len(result.offers) == 3

        best_new = [o for o in result.offers if o.condition == "new"]
        assert len(best_new) == 2

        official = best_new[0]
        assert official.price == Decimal("1329")
        assert official.original_price == Decimal("2180")
        assert official.official_store_id == 1234
        assert official.free_shipping is True
        assert official.warranty == "12 meses de garantia de fábrica"

        cheap = best_new[1]
        assert cheap.price == Decimal("1450")
        assert cheap.original_price is None
        assert cheap.official_store_id is None
        assert cheap.warranty is None

        used = [o for o in result.offers if o.condition == "used"]
        assert len(used) == 1
        assert used[0].price == Decimal("1200")

    def test_empty_results(self):
        source = MLCatalogSource.__new__(MLCatalogSource)
        empty = {"paging": {"total": 0, "offset": 0, "limit": 50}, "results": []}

        with patch.object(source, "_get", return_value=empty):
            result = source.fetch_catalog("MLB99999999")

        assert result.offers == []
        assert result.title == ""
