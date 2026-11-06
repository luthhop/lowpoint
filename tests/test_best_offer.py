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

    def test_available_true(self):
        offers = [_offer(1200)]
        result = select_best_offer(offers)
        assert result is not None
        assert result.available is True


class TestLojaOficial:
    def test_desempate_mesmo_preco_prefere_oficial(self):
        offers = [
            _offer(1300, official_store_id=None, item_id="A"),
            _offer(1300, official_store_id=1234, item_id="B"),
        ]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.official_store_id == 1234

    def test_nao_oficial_mais_barato_nao_filtrado(self):
        offers = [
            _offer(1300, official_store_id=None),
            _offer(1350, official_store_id=1234),
        ]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.price == Decimal("1300")
        assert result.offer.official_store_id is None

    def test_sem_loja_oficial_pega_mais_barato(self):
        offers = [
            _offer(1300, official_store_id=None),
            _offer(1400, official_store_id=None),
        ]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.price == Decimal("1300")


class TestGarantia:
    def test_require_warranty_exclui_none(self):
        offers = [
            _offer(1200, warranty=None),
            _offer(1400, warranty="12 meses"),
        ]
        result = select_best_offer(offers, require_warranty=True)
        assert result is not None
        assert result.offer.price == Decimal("1400")

    def test_require_warranty_exclui_sem_garantia_string(self):
        offers = [
            _offer(1200, warranty="Sem garantia"),
            _offer(1400, warranty="Garantia de fábrica: 12 meses"),
        ]
        result = select_best_offer(offers, require_warranty=True)
        assert result is not None
        assert result.offer.price == Decimal("1400")

    def test_require_warranty_sem_nenhuma_com_garantia_mantem_todas(self):
        offers = [
            _offer(1200, warranty=None),
            _offer(1400, warranty="Sem garantia"),
        ]
        result = select_best_offer(offers, require_warranty=True)
        assert result is not None
        assert result.offer.price == Decimal("1200")


class TestWarnings:
    def test_warning_sem_garantia_none(self):
        offers = [_offer(1200, warranty=None)]
        result = select_best_offer(offers)
        assert result is not None
        assert any("sem garantia" in w for w in result.warnings)

    def test_warning_sem_garantia_string(self):
        offers = [_offer(1200, warranty="Sem garantia")]
        result = select_best_offer(offers)
        assert result is not None
        assert any("sem garantia" in w for w in result.warnings)

    def test_sem_warning_com_garantia(self):
        offers = [_offer(1200, warranty="12 meses")]
        result = select_best_offer(offers)
        assert result is not None
        assert not any("sem garantia" in w for w in result.warnings)

    def test_warning_vendedor_nao_oficial(self):
        offers = [_offer(1200, official_store_id=None)]
        result = select_best_offer(offers)
        assert result is not None
        assert any("não oficial" in w for w in result.warnings)

    def test_sem_warning_vendedor_oficial(self):
        offers = [_offer(1200, official_store_id=1234)]
        result = select_best_offer(offers)
        assert result is not None
        assert not any("não oficial" in w for w in result.warnings)


class TestDesempate:
    def test_mesmo_preco_prefere_com_garantia(self):
        offers = [
            _offer(1300, warranty="Sem garantia", official_store_id=None, item_id="A"),
            _offer(1300, warranty="Garantia de fábrica: 6 meses", official_store_id=None, item_id="B"),
        ]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.item_id == "B"

    def test_garantia_antes_de_oficial(self):
        offers = [
            _offer(1300, warranty="Sem garantia", official_store_id=1234, item_id="A"),
            _offer(1300, warranty="12 meses", official_store_id=None, item_id="B"),
            _offer(1300, warranty="12 meses", official_store_id=1234, item_id="C"),
        ]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.item_id == "C"

    def test_oficial_desempata_com_mesma_garantia(self):
        offers = [
            _offer(1300, warranty="12 meses", official_store_id=None, item_id="A"),
            _offer(1300, warranty="12 meses", official_store_id=1234, item_id="B"),
        ]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.item_id == "B"


class TestOfertaSuspeita:
    def test_oferta_suspeita_descartada(self):
        offers = [
            _offer(100, item_id="GOLPE"),
            _offer(1000, item_id="A"),
            _offer(1100, item_id="B"),
            _offer(1200, item_id="C"),
        ]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.price == Decimal("1000")
        assert len(result.suspect_offers) == 1
        assert result.suspect_offers[0].price == Decimal("100")

    def test_warning_oferta_suspeita(self):
        offers = [_offer(100), _offer(1000), _offer(1100)]
        result = select_best_offer(offers)
        assert result is not None
        assert any("suspeita" in w for w in result.warnings)

    def test_sem_deteccao_com_poucas_ofertas_sem_historico(self):
        offers = [_offer(100), _offer(1000)]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.price == Decimal("100")
        assert result.suspect_offers == []

    def test_threshold_configuravel(self):
        offers = [_offer(500), _offer(1000), _offer(1100)]
        # default 0.60: mediana=1000, cutoff=600 → 500 é suspeita
        r1 = select_best_offer(offers)
        assert r1 is not None
        assert r1.offer.price == Decimal("1000")
        assert len(r1.suspect_offers) == 1

        # threshold 0.40: cutoff=400 → 500 não é suspeita
        r2 = select_best_offer(offers, suspect_threshold=Decimal("0.40"))
        assert r2 is not None
        assert r2.offer.price == Decimal("500")
        assert r2.suspect_offers == []

    def test_nenhuma_suspeita_quando_precos_proximos(self):
        offers = [_offer(950), _offer(1000), _offer(1050)]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.price == Decimal("950")
        assert result.suspect_offers == []


class TestHistoricalMedianFallback:
    """Quando < 3 ofertas, historical_median serve de referência anti-golpe."""

    def test_suspeita_com_historical_median_e_2_ofertas(self):
        offers = [_offer(1500, item_id="GOLPE"), _offer(4000)]
        result = select_best_offer(offers, historical_median=Decimal("4100"))
        assert result is not None
        # cutoff = 4100 * 0.60 = 2460 → R$ 1500 < 2460 → suspeita
        assert result.offer.price == Decimal("4000")
        assert len(result.suspect_offers) == 1
        assert result.suspect_offers[0].price == Decimal("1500")

    def test_suspeita_com_historical_median_e_1_oferta(self):
        offers = [_offer(1500)]
        result = select_best_offer(offers, historical_median=Decimal("4100"))
        # única oferta é suspeita → nenhuma elegível → None
        assert result is None

    def test_sem_historico_com_2_ofertas_nao_filtra(self):
        offers = [_offer(1500), _offer(4000)]
        result = select_best_offer(offers)
        assert result is not None
        assert result.offer.price == Decimal("1500")
        assert result.suspect_offers == []

    def test_historical_median_nao_interfere_com_3_ofertas(self):
        offers = [_offer(1500), _offer(4000), _offer(4200)]
        # mediana coleta = 4000, cutoff = 2400 → 1500 suspeita (filtro normal)
        result = select_best_offer(offers, historical_median=Decimal("4100"))
        assert result is not None
        assert result.offer.price == Decimal("4000")
        assert len(result.suspect_offers) == 1

    def test_preco_acima_do_cutoff_historico_nao_e_suspeito(self):
        offers = [_offer(3000), _offer(4000)]
        # cutoff = 4100 * 0.60 = 2460 → 3000 > 2460 → não suspeita
        result = select_best_offer(offers, historical_median=Decimal("4100"))
        assert result is not None
        assert result.offer.price == Decimal("3000")
        assert result.suspect_offers == []


class TestBugPS5TargetHitSuspeita:
    """Reproduz o bug: alerta target_hit com oferta suspeita de R$ 1.500 para PS5."""

    def test_ps5_r1500_com_poucas_ofertas_sem_historico_bug(self):
        """Cenário do bug: < 3 ofertas, sem historical_median → golpe passa."""
        offers = [
            _offer(
                1500.00,
                warranty="Garantia de fábrica: 12 meses",
                official_store_id=1473,
                seller_id=99999,
                item_id="MLBGOLPE",
            ),
            _offer(
                4599.90,
                warranty="Garantia de fábrica: 12 meses",
                official_store_id=1473,
                seller_id=480263032,
                item_id="MLB4214670787",
            ),
        ]
        result = select_best_offer(offers)
        assert result is not None
        # BUG: sem historical_median, o golpe passa
        assert result.offer.price == Decimal("1500")

    def test_ps5_r1500_com_poucas_ofertas_com_historico_fix(self):
        """Com historical_median, o golpe é filtrado."""
        offers = [
            _offer(
                1500.00,
                warranty="Garantia de fábrica: 12 meses",
                official_store_id=1473,
                seller_id=99999,
                item_id="MLBGOLPE",
            ),
            _offer(
                4599.90,
                warranty="Garantia de fábrica: 12 meses",
                official_store_id=1473,
                seller_id=480263032,
                item_id="MLB4214670787",
            ),
        ]
        result = select_best_offer(
            offers, historical_median=Decimal("4121.51")
        )
        assert result is not None
        assert result.offer.price == Decimal("4599.90")
        assert len(result.suspect_offers) == 1
        assert result.suspect_offers[0].item_id == "MLBGOLPE"

    def test_ps5_r1500_unica_oferta_com_historico(self):
        """Se a única oferta é suspeita, retorna None (indisponível)."""
        offers = [
            _offer(
                1500.00,
                warranty="Garantia de fábrica: 12 meses",
                official_store_id=1473,
                seller_id=99999,
                item_id="MLBGOLPE",
            ),
        ]
        result = select_best_offer(
            offers, historical_median=Decimal("4121.51")
        )
        assert result is None


class TestCasoRealPS5:
    """Fixture da coleta real do PS5 em 2026-11-02."""

    def _ps5_offers(self) -> list[OfferData]:
        return [
            _offer(
                2399.00,
                warranty="Garantia de fábrica: 12 meses",
                official_store_id=None,
                seller_id=2526368073,
                item_id="MLB5271087369",
            ),
            _offer(
                4121.51,
                warranty="Garantia de fábrica: 6 meses",
                official_store_id=None,
                seller_id=2576541371,
                item_id="MLB5476497029",
            ),
            _offer(
                4121.51,
                warranty="Sem garantia",
                official_store_id=None,
                seller_id=1633812407,
                item_id="MLB7921858724",
            ),
            _offer(
                4121.51,
                warranty="Garantia de fábrica: 2 anos",
                official_store_id=None,
                seller_id=161014135,
                item_id="MLB7917853192",
            ),
            _offer(
                4599.90,
                warranty="Garantia de fábrica: 12 meses",
                official_store_id=1473,
                seller_id=480263032,
                item_id="MLB4214670787",
            ),
            _offer(
                4767.00,
                warranty="Garantia de fábrica: 12 meses",
                official_store_id=442784,
                seller_id=1087613885,
                item_id="MLB5317347357",
            ),
        ]

    def test_nao_seleciona_oferta_de_loja_oficial_cara(self):
        result = select_best_offer(self._ps5_offers())
        assert result is not None
        assert result.offer.price != Decimal("4599.90")

    def test_seleciona_mais_barata_nao_suspeita(self):
        result = select_best_offer(self._ps5_offers())
        assert result is not None
        assert result.offer.price == Decimal("4121.51")
        # Desempate: entre as 3 ofertas de R$ 4.121,51, escolhe com garantia
        assert result.offer.item_id in ("MLB5476497029", "MLB7917853192")
        assert result.offer.item_id != "MLB7921858724"  # "Sem garantia" perde

    def test_r2399_e_suspeita(self):
        result = select_best_offer(self._ps5_offers())
        assert result is not None
        assert len(result.suspect_offers) == 1
        assert result.suspect_offers[0].price == Decimal("2399.00")

    def test_warnings_esperados(self):
        result = select_best_offer(self._ps5_offers())
        assert result is not None
        texto = " ".join(result.warnings)
        assert "não oficial" in texto
        assert "suspeita" in texto
