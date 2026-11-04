from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lowpoint.models import Base, OfferSnapshot, PriceHistory, Product, Watch
from lowpoint.sources.base import CatalogSnapshot, OfferData
from lowpoint.sources.mock import MockSource


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def mock_source():
    return MockSource()


def _make_offer(**overrides) -> OfferData:
    defaults = dict(
        item_id="MLB1234",
        seller_id=100,
        price=Decimal("1500.00"),
        original_price=Decimal("2000.00"),
        condition="new",
        official_store_id=1,
        free_shipping=True,
        warranty="12 meses",
    )
    defaults.update(overrides)
    return OfferData(**defaults)


def _make_snapshot(catalog_id: str, offers: list[OfferData] | None = None) -> CatalogSnapshot:
    return CatalogSnapshot(
        catalog_product_id=catalog_id,
        title=f"Produto {catalog_id}",
        image_url=f"https://img.example.com/{catalog_id}.jpg",
        offers=offers or [_make_offer()],
        collected_at=datetime(2026, 11, 2, 12, 0, 0, tzinfo=timezone.utc),
    )


def _seed_product_with_watch(session: Session, catalog_id: str = "MLB24061510") -> Product:
    product = Product(
        catalog_product_id=catalog_id,
        title=f"(pendente — {catalog_id})",
        url=f"https://www.mercadolivre.com.br/p/{catalog_id}",
    )
    session.add(product)
    session.flush()
    watch = Watch(chat_id=0, product_id=product.id, target_price=Decimal("1200.00"))
    session.add(watch)
    session.commit()
    return product


class TestCollectOnce:
    def test_saves_offer_snapshots_and_price_history(self, db_session, mock_source):
        product = _seed_product_with_watch(db_session, "MLB24061510")
        offers = [
            _make_offer(item_id="MLB1001", price=Decimal("1400.00"), seller_id=10),
            _make_offer(item_id="MLB1002", price=Decimal("1500.00"), seller_id=20),
        ]
        mock_source.set_response("MLB24061510", _make_snapshot("MLB24061510", offers))

        with patch("lowpoint.collect.SessionLocal", return_value=db_session):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        snapshots = db_session.query(OfferSnapshot).all()
        assert len(snapshots) == 2
        assert {s.item_id for s in snapshots} == {"MLB1001", "MLB1002"}

        history = db_session.query(PriceHistory).all()
        assert len(history) == 1
        assert history[0].price == Decimal("1400.00")
        assert history[0].available is True

    def test_updates_title_from_pending(self, db_session, mock_source):
        product = _seed_product_with_watch(db_session, "MLB99999")
        product_id = product.id
        mock_source.set_response("MLB99999", _make_snapshot("MLB99999"))

        with patch("lowpoint.collect.SessionLocal", return_value=db_session):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        updated = db_session.get(Product, product_id)
        assert updated.title == "Produto MLB99999"
        assert updated.image_url == "https://img.example.com/MLB99999.jpg"

    def test_does_not_overwrite_existing_title(self, db_session, mock_source):
        product = _seed_product_with_watch(db_session, "MLB11111")
        product.title = "Título Real"
        db_session.commit()
        product_id = product.id

        mock_source.set_response("MLB11111", _make_snapshot("MLB11111"))

        with patch("lowpoint.collect.SessionLocal", return_value=db_session):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        updated = db_session.get(Product, product_id)
        assert updated.title == "Título Real"

    def test_no_active_watches_skips(self, db_session, mock_source):
        with patch("lowpoint.collect.SessionLocal", return_value=db_session):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        assert db_session.query(OfferSnapshot).count() == 0
        assert db_session.query(PriceHistory).count() == 0

    def test_inactive_watch_not_collected(self, db_session, mock_source):
        product = Product(
            catalog_product_id="MLB55555",
            title="Inativo",
            url="https://www.mercadolivre.com.br/p/MLB55555",
        )
        db_session.add(product)
        db_session.flush()
        watch = Watch(
            chat_id=0,
            product_id=product.id,
            target_price=Decimal("100.00"),
            active=False,
        )
        db_session.add(watch)
        db_session.commit()

        mock_source.set_response("MLB55555", _make_snapshot("MLB55555"))

        with patch("lowpoint.collect.SessionLocal", return_value=db_session):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        assert db_session.query(OfferSnapshot).count() == 0

    def test_no_new_offers_records_unavailable(self, db_session, mock_source):
        product = _seed_product_with_watch(db_session, "MLB77777")
        used_offer = _make_offer(condition="used")
        mock_source.set_response(
            "MLB77777", _make_snapshot("MLB77777", [used_offer])
        )

        with patch("lowpoint.collect.SessionLocal", return_value=db_session):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        history = db_session.query(PriceHistory).all()
        assert len(history) == 1
        assert history[0].available is False
        assert history[0].price == Decimal("0")

    def test_one_product_failure_does_not_block_others(self, db_session, mock_source):
        p1 = _seed_product_with_watch(db_session, "MLB_OK")
        p1_id = p1.id
        p2 = _seed_product_with_watch(db_session, "MLB_FAIL")
        p2_id = p2.id

        mock_source.set_response("MLB_OK", _make_snapshot("MLB_OK"))

        with patch("lowpoint.collect.SessionLocal", return_value=db_session):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        assert db_session.query(OfferSnapshot).filter_by(product_id=p1_id).count() == 1
        assert db_session.query(OfferSnapshot).filter_by(product_id=p2_id).count() == 0

    def test_multiple_products_collected(self, db_session, mock_source):
        p1 = _seed_product_with_watch(db_session, "MLBA")
        p2 = _seed_product_with_watch(db_session, "MLBB")

        mock_source.set_response("MLBA", _make_snapshot("MLBA"))
        mock_source.set_response("MLBB", _make_snapshot("MLBB"))

        with patch("lowpoint.collect.SessionLocal", return_value=db_session):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        assert db_session.query(PriceHistory).count() == 2


class TestAnomalousCollection:
    """Coletas com queda drástica de ofertas não geram alertas."""

    def _seed_history(self, db_session, product, num_collections=5, offers_per=80):
        """Cria coletas anteriores com muitas ofertas para estabelecer baseline."""
        for i in range(num_collections):
            ts = datetime(2026, 11, 1, i, 0, 0, tzinfo=timezone.utc)
            for j in range(offers_per):
                db_session.add(OfferSnapshot(
                    product_id=product.id,
                    item_id=f"MLB{i}_{j}",
                    seller_id=j,
                    price=Decimal("4000.00"),
                    condition="new",
                    official_store_id=None,
                    free_shipping=True,
                    warranty="12 meses",
                    collected_at=ts,
                ))
            db_session.add(PriceHistory(
                product_id=product.id,
                price=Decimal("4000.00"),
                original_price=None,
                item_id=f"MLB{i}_0",
                seller_id=0,
                available=True,
                collected_at=ts,
            ))
        db_session.commit()

    def test_anomalous_suppresses_alerts(self, db_session, mock_source):
        product = _seed_product_with_watch(db_session, "MLB_ANOM")
        self._seed_history(db_session, product, num_collections=5, offers_per=80)

        few_offers = [_make_offer(item_id=f"MLB_FEW_{i}", price=Decimal("3900.00")) for i in range(2)]
        mock_source.set_response("MLB_ANOM", _make_snapshot("MLB_ANOM", few_offers))

        with (
            patch("lowpoint.collect.SessionLocal", return_value=db_session),
            patch("lowpoint.collect.send_alerts_after_collect") as mock_alert,
        ):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        mock_alert.assert_not_called()
        assert db_session.query(PriceHistory).filter_by(
            product_id=product.id
        ).count() == 6

    def test_normal_collection_sends_alerts(self, db_session, mock_source):
        product = _seed_product_with_watch(db_session, "MLB_NORM")
        self._seed_history(db_session, product, num_collections=5, offers_per=80)

        many_offers = [_make_offer(item_id=f"MLB_MANY_{i}", price=Decimal("3900.00")) for i in range(70)]
        mock_source.set_response("MLB_NORM", _make_snapshot("MLB_NORM", many_offers))

        with (
            patch("lowpoint.collect.SessionLocal", return_value=db_session),
            patch("lowpoint.collect.send_alerts_after_collect") as mock_alert,
        ):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        mock_alert.assert_called_once()

    def test_first_collection_not_anomalous(self, db_session, mock_source):
        product = _seed_product_with_watch(db_session, "MLB_FIRST")
        few_offers = [_make_offer(item_id="MLB_ONE")]
        mock_source.set_response("MLB_FIRST", _make_snapshot("MLB_FIRST", few_offers))

        with (
            patch("lowpoint.collect.SessionLocal", return_value=db_session),
            patch("lowpoint.collect.send_alerts_after_collect") as mock_alert,
        ):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        mock_alert.assert_called_once()


class TestAlertIsolation:
    """send_alerts_after_collect failures must never crash the collector."""

    def test_alert_exception_does_not_crash_collect(self, db_session, mock_source):
        product = _seed_product_with_watch(db_session, "MLB_ALERT_FAIL")
        mock_source.set_response("MLB_ALERT_FAIL", _make_snapshot("MLB_ALERT_FAIL"))

        def _boom(*args, **kwargs):
            raise ConnectionError("Telegram is down")

        with (
            patch("lowpoint.collect.SessionLocal", return_value=db_session),
            patch("lowpoint.collect.send_alerts_after_collect", side_effect=_boom),
        ):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        assert db_session.query(PriceHistory).filter_by(product_id=product.id).count() == 1

    def test_alert_skipped_when_no_token(self, db_session, mock_source, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        product = _seed_product_with_watch(db_session, "MLB_NO_TOKEN")
        product_id = product.id
        mock_source.set_response("MLB_NO_TOKEN", _make_snapshot("MLB_NO_TOKEN"))

        with (
            patch("lowpoint.collect.SessionLocal", return_value=db_session),
            patch("lowpoint.telegram.notify._send_message") as mock_send,
        ):
            from lowpoint.collect import collect_once
            collect_once(mock_source)

        mock_send.assert_not_called()
        assert db_session.query(PriceHistory).filter_by(product_id=product_id).count() == 1
