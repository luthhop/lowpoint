from decimal import Decimal

from lowpoint.best_offer import select_best_offer
from lowpoint.sources.base import OfferData


def _offer(
    price: float,
    condition: str = "new",
    warranty: str | None = "12 meses",
    official_store_id: int | None = 1234,
    seller_id: int = 1,
    item_id: str = "MLB1",
) -> OfferData:
    return OfferData(
        item_id=item_id,
        seller_id=seller_id,
        price=Decimal(str(price)),
        original_price=None,
        condition=condition,
        official_store_id=official_store_id,
        free_shipping=True,
        warranty=warranty,
    )


class TestSelectBestOffer:
    def test_menor_preco_new(self):
        offers = [_offer(1500), _offer(1300), _offer(1400)]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.price == Decimal("1300")

    def test_ignora_used(self):
        offers = [_offer(800, condition="used"), _offer(1300)]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.price == Decimal("1300")

    def test_sem_ofertas_new_retorna_none(self):
        offers = [_offer(800, condition="used")]
        result = select_best_offer(offers)
        assert result is None

    def test_lista_vazia(self):
        result = select_best_offer([])
        assert result is None

    def test_prefer_official_store(self):
        offers = [
            _offer(1300, official_store_id=None),
            _offer(1350, official_store_id=1234),
        ]
        result = select_best_offer(offers, prefer_official_store=True)
        assert result is not None
        assert result.offer.price == Decimal("1350")
        assert result.offer.official_store_id == 1234

    def test_sem_official_store_pega_mais_barato(self):
        offers = [
            _offer(1300, official_store_id=None),
            _offer(1400, official_store_id=None),
        ]
        result = select_best_offer(offers, prefer_official_store=True)
        assert result is not None
        assert result.offer.price == Decimal("1300")

    def test_require_warranty(self):
        offers = [
            _offer(1200, warranty=None),
            _offer(1400, warranty="12 meses"),
        ]
        result = select_best_offer(offers, require_warranty=True)
        assert result is not None
        assert result.offer.price == Decimal("1400")

    def test_warning_sem_garantia(self):
        offers = [_offer(1200, warranty=None)]
        result = select_best_offer(offers)
        assert result is not None
        assert "sem garantia" in result.warnings[0]

    def test_sem_warning_com_garantia(self):
        offers = [_offer(1200, warranty="12 meses")]
        result = select_best_offer(offers)
        assert result is not None
        assert result.warnings == []

    def test_available_true(self):
        offers = [_offer(1200)]
        result = select_best_offer(offers)
        assert result is not None
        assert result.available is True
