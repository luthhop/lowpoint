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
        product_info = {
            "name": "Monitor Gamer LG UltraGear 32GN600 32\" VA QHD 165Hz",
            "pictures": [{"url": "https://http2.mlstatic.com/D_NQ_NP_example.jpg"}],
        }

        source = MLCatalogSource.__new__(MLCatalogSource)

        def mock_get(url):
            if "/items" in url:
                return fixture_data
            return product_info

        with patch.object(source, "_get", side_effect=mock_get):
            result = source.fetch_catalog("MLB24061510")

        assert result.catalog_product_id == "MLB24061510"
        assert result.title == "Monitor Gamer LG UltraGear 32GN600 32\" VA QHD 165Hz"
        assert result.image_url == "https://http2.mlstatic.com/D_NQ_NP_example.jpg"
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
        product_info = {"name": "", "pictures": []}
        empty = {"paging": {"total": 0, "offset": 0, "limit": 50}, "results": []}

        def mock_get(url):
            if "/items" in url:
                return empty
            return product_info

        with patch.object(source, "_get", side_effect=mock_get):
            result = source.fetch_catalog("MLB99999999")

        assert result.offers == []
        assert result.title == ""


class TestRequestResilience:
    """[TESTE] Timeout e retry sem rede: requests.request é falso."""

    def _resp(self, status, headers=None):
        r = MagicMock()
        r.status_code = status
        r.headers = headers or {}
        r.json.return_value = {"ok": True}
        r.raise_for_status.side_effect = None if status < 400 else Exception(status)
        return r

    def _source(self):
        sleeps = []
        source = MLCatalogSource(session_factory=MagicMock(), sleep=sleeps.append)
        source._access_token = "tok"
        return source, sleeps

    def test_timeout_is_always_passed(self):
        source, _ = self._source()
        with patch("lowpoint.sources.ml_catalog.requests.request",
                   return_value=self._resp(200)) as req:
            source._get("https://x/y")
        assert req.call_args.kwargs["timeout"] == (5, 15)

    def test_retries_429_then_succeeds_with_backoff(self):
        source, sleeps = self._source()
        seq = [self._resp(429), self._resp(503), self._resp(200)]
        with patch("lowpoint.sources.ml_catalog.requests.request", side_effect=seq):
            assert source._get("https://x/y") == {"ok": True}
        assert sleeps == [1.0, 2.0]
        assert source.call_count == 3

    def test_gives_up_after_3_attempts(self):
        source, sleeps = self._source()
        with patch("lowpoint.sources.ml_catalog.requests.request",
                   return_value=self._resp(500)) as req:
            try:
                source._get("https://x/y")
                raise AssertionError("devia falhar")
            except Exception as e:
                assert e.args == (500,)
        assert req.call_count == 3 and len(sleeps) == 2

    def test_4xx_is_not_retried(self):
        source, sleeps = self._source()
        with patch("lowpoint.sources.ml_catalog.requests.request",
                   return_value=self._resp(404)) as req:
            try:
                source._get("https://x/y")
            except Exception:
                pass
        assert req.call_count == 1 and sleeps == []

    def test_retry_after_is_capped(self):
        source, sleeps = self._source()
        seq = [self._resp(429, {"Retry-After": "120"}), self._resp(200)]
        with patch("lowpoint.sources.ml_catalog.requests.request", side_effect=seq):
            source._get("https://x/y")
        assert sleeps == [10.0]

    def test_network_timeout_is_retried(self):
        import requests as rq
        source, sleeps = self._source()
        seq = [rq.Timeout(), self._resp(200)]
        with patch("lowpoint.sources.ml_catalog.requests.request", side_effect=seq):
            assert source._get("https://x/y") == {"ok": True}
        assert sleeps == [1.0]
