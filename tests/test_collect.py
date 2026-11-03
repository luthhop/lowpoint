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
