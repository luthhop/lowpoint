from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lowpoint.models import Base, Product, Watch
from lowpoint.telegram.webhook import handle_update


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("ALLOWED_CHAT_IDS", "100")


def _update(text: str, chat_id: int = 100) -> dict:
    return {
        "message": {
            "chat": {"id": chat_id},
            "text": text,
        }
    }


def _callback(data: str, chat_id: int = 100) -> dict:
    return {
        "callback_query": {
            "id": "cb-1",
            "data": data,
            "message": {"chat": {"id": chat_id}},
        }
    }


def _seed(session, chat_id: int = 100) -> tuple[Product, Watch]:
    product = Product(
        catalog_product_id="MLB57081243",
        title="Console PlayStation 5 Slim Digital Edition",
        url="https://www.mercadolivre.com.br/p/MLB57081243",
    )
    session.add(product)
    session.flush()
    watch = Watch(
        chat_id=chat_id,
        product_id=product.id,
        target_price=Decimal("3500.00"),
    )
    session.add(watch)
    session.commit()
    return product, watch


class TestApelido:
    def test_apelido_shows_buttons(self, db_session):
        _seed(db_session)
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(_update("/apelido"), "test-secret")
        assert result.get("reply_markup")
        buttons = result["reply_markup"]["inline_keyboard"]
        assert any("nick:" in btn[0]["callback_data"] for btn in buttons)

    def test_apelido_direct_rename(self, db_session):
        _, watch = _seed(db_session)
        watch_id = watch.id
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(
                _update(f"/apelido {watch_id} PS5 Slim"),
                "test-secret",
            )
        assert "Renomeado" in result["text"]
        assert "PS5 Slim" in result["text"]

        updated = db_session.get(Watch, watch_id)
        assert updated.nickname == "PS5 Slim"

    def test_apelido_invalid_id(self, db_session):
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(
                _update("/apelido abc Novo Nome"),
                "test-secret",
            )
        assert "inválido" in result["text"].lower()

    def test_apelido_wrong_watch(self, db_session):
        _seed(db_session)
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(
                _update("/apelido 9999 Outro"),
                "test-secret",
            )
        assert "não encontrado" in result["text"].lower()

    def test_apelido_no_watches(self, db_session):
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(_update("/apelido"), "test-secret")
        assert "nenhum" in result["text"].lower()

    def test_nick_callback_shows_instruction(self, db_session):
        _, watch = _seed(db_session)
        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(
                _callback(f"nick:{watch.id}"),
                "test-secret",
            )
        assert "/apelido" in result["text"]
        assert str(watch.id) in result["text"]


class TestListaDesdeHoje:
    def test_zero_days_shows_desde_hoje(self, db_session):
        from datetime import datetime, timezone
        from lowpoint.models import PriceHistory

        product, watch = _seed(db_session)
        now = datetime.now(timezone.utc)
        watch.created_at = now
        db_session.add(PriceHistory(
            product_id=product.id,
            price=Decimal("3800.00"),
            original_price=None,
            item_id="MLB123",
            seller_id=1,
            available=True,
            collected_at=now,
        ))
        db_session.commit()

        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(_update("/lista"), "test-secret")

        assert "desde hoje" in result["text"]
        assert "0 dias" not in result["text"]


class TestAdicionarLivePrice:
    def test_shows_price_on_success(self, db_session):
        from unittest.mock import MagicMock
        from lowpoint.models import Product as Prod

        mock_product = MagicMock()
        mock_product.id = 1
        mock_product.title = "(pendente)"
        mock_watch = MagicMock()
        mock_watch.id = 1

        mock_snapshot = MagicMock()
        mock_snapshot.title = "Console PS5"
        mock_snapshot.image_url = None
        mock_snapshot.offers = [MagicMock()]
        mock_snapshot.offers[0].price = Decimal("3200.00")

        mock_best = MagicMock()
        mock_best.offer.price = Decimal("3200.00")

        with (
            patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session),
            patch("lowpoint.telegram.webhook.extract_catalog_id", return_value="MLB57081243"),
            patch("lowpoint.telegram.webhook.register_product", return_value=(mock_product, mock_watch)),
            patch("lowpoint.telegram.webhook.select_best_offer", return_value=mock_best),
            patch("lowpoint.sources.ml_catalog.MLCatalogSource.fetch_catalog", return_value=mock_snapshot),
        ):
            result = handle_update(
                _update("/adicionar mercadolivre.com.br/p/MLB57081243 3500"),
                "test-secret",
            )

        assert "R$ 3.200,00" in result["text"]
        assert "Console PS5" in result["text"]

    def test_fallback_on_failure(self, db_session):
        from unittest.mock import MagicMock

        mock_product = MagicMock()
        mock_product.id = 1
        mock_product.title = "(pendente)"
        mock_watch = MagicMock()
        mock_watch.id = 1

        with (
            patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session),
            patch("lowpoint.telegram.webhook.extract_catalog_id", return_value="MLB57081243"),
            patch("lowpoint.telegram.webhook.register_product", return_value=(mock_product, mock_watch)),
            patch("lowpoint.sources.ml_catalog.MLCatalogSource.fetch_catalog", side_effect=Exception("timeout")),
        ):
            result = handle_update(
                _update("/adicionar mercadolivre.com.br/p/MLB57081243 3500"),
                "test-secret",
            )

        assert "próxima coleta" in result["text"]


class TestListaPlural:
    def test_1_dia_singular(self, db_session):
        from datetime import datetime, timedelta, timezone
        from lowpoint.models import PriceHistory

        product, watch = _seed(db_session)
        now = datetime.now(timezone.utc)
        watch.created_at = now - timedelta(days=1)
        db_session.add(PriceHistory(
            product_id=product.id,
            price=Decimal("3800.00"),
            original_price=None,
            item_id="MLB123",
            seller_id=1,
            available=True,
            collected_at=now,
        ))
        db_session.commit()

        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(_update("/lista"), "test-secret")

        assert "1 dia" in result["text"]
        assert "1 dias" not in result["text"]

    def test_many_dias_plural(self, db_session):
        from datetime import datetime, timedelta, timezone
        from lowpoint.models import PriceHistory

        product, watch = _seed(db_session)
        now = datetime.now(timezone.utc)
        watch.created_at = now - timedelta(days=10)
        db_session.add(PriceHistory(
            product_id=product.id,
            price=Decimal("3800.00"),
            original_price=None,
            item_id="MLB123",
            seller_id=1,
            available=True,
            collected_at=now,
        ))
        db_session.commit()

        with patch("lowpoint.telegram.webhook.SessionLocal", return_value=db_session):
            result = handle_update(_update("/lista"), "test-secret")

        assert "10 dias" in result["text"]
