"""Pico em andamento não é maquiado.

Regra proposta: com pico detectado, SEGURA (maquiado) só quando o preço atual
já recuou pelo menos HIKE_RETREAT_THRESHOLD (5%) do máximo da janela E
continua dentro da faixa de fachada (≤3% abaixo do pré-pico, ou acima dele).
Durante a subida, ou oscilando perto do topo, o veredito é neutro.

Estes testes descrevem o comportamento desejado; os de "subida" falham com o
verdict.py atual (que dá maquiado assim que existe um pico na janela).
"""

import importlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from lowpoint.telegram.formatter import AlertContext, format_alert
from lowpoint.verdict import PricePoint, compute_verdict

NOW = datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)


def _history(today: list[str], *, base="1000") -> list[PricePoint]:
    """30 dias horários em `base`, depois `today` a cada 15 min terminando em NOW."""
    pts = []
    start = NOW - timedelta(days=30)
    t = start
    first_today = NOW - timedelta(minutes=15 * (len(today) - 1))
    while t < first_today - timedelta(hours=1):
        pts.append(PricePoint(Decimal(base), None, t))
        t += timedelta(hours=1)
    for i, p in enumerate(today):
        pts.append(PricePoint(Decimal(p), None, first_today + timedelta(minutes=15 * i)))
    return pts


def _verdict(today: list[str]):
    hist = _history(today)
    return compute_verdict(Decimal(today[-1]), None, hist, NOW)


def _render(v, price: str, target="500") -> str:
    ctx = AlertContext(
        product_name="X", item_id="MLB1", price=Decimal(price), original_price=None,
        target_price=Decimal(target), verdict=v.verdict, reason=v.reason,
        lowest_price=v.lowest_price, median_30d=v.median_30d,
        monitoring_days=v.monitoring_days, pre_hike_price=v.pre_hike_price,
        hike_pct=v.hike_pct, hike_days=v.hike_days, peak_price=v.peak_price, baseline_price=v.baseline_price,
        has_warranty=True, is_official=True, suspect_count=0, offer_count=10,
    )
    return format_alert(ctx).text


class TestRetreatConstant:
    def test_constant_in_config(self):
        config = importlib.import_module("lowpoint.config")
        assert getattr(config, "HIKE_RETREAT_THRESHOLD", None) == Decimal("0.05")


class TestPicoSubindo:
    def test_first_point_of_hike_is_neutro(self):
        v = _verdict(["1300"])
        assert v.verdict == "neutro"

    def test_rising_is_neutro(self):
        v = _verdict(["1100", "1200", "1300"])
        assert v.verdict == "neutro"

    def test_oscillating_near_top_is_neutro(self):
        # replay: 1300/1313/1295/1305/1287 → 1287 está só 2% abaixo do topo
        v = _verdict(["1300", "1313", "1295", "1305", "1287"])
        assert v.verdict == "neutro"

    def test_just_under_retreat_threshold_is_neutro(self):
        # topo 1300; 5% abaixo = 1235. 1235.01 ainda não recuou o bastante.
        v = _verdict(["1300", "1235.01"])
        assert v.verdict == "neutro"

    @pytest.mark.parametrize("price", ["1300", "1313", "1287"])
    def test_text_never_says_baixaram_while_at_top(self, price):
        v = _verdict(["1300", "1313", price])
        assert "baixaram de volta" not in _render(v, price)


class TestPicoRecuou:
    def test_exactly_5_percent_below_top_is_maquiado(self):
        v = _verdict(["1300", "1235"])
        assert v.verdict == "maquiado"

    def test_back_near_pre_hike_is_maquiado(self):
        # Caso da landing: subiu 74% e "baixou" pra 4% acima do normal.
        v = _verdict(["1740", "1740", "1040"])
        assert v.verdict == "maquiado"
        assert "e depois baixaram 40%." in _render(v, "1040")

    def test_retreated_below_fachada_follows_normal_rules(self):
        # 10% abaixo do pré-pico e menor preço → desconto real (regra de 10/11)
        v = _verdict(["1300", "1300", "900"])
        assert v.verdict == "real"


def _two_day_hike(today_prices: list[str]) -> list[PricePoint]:
    """30 dias em 1000; pico começa há 2 dias (1313); termina com `today_prices`."""
    pts = []
    t = NOW - timedelta(days=30)
    hike_start = NOW - timedelta(days=2, hours=1)
    while t < hike_start:
        pts.append(PricePoint(Decimal("1000"), None, t))
        t += timedelta(hours=1)
    while t < NOW - timedelta(hours=1):
        pts.append(PricePoint(Decimal("1313"), None, t))
        t += timedelta(hours=1)
    for i, p in enumerate(today_prices):
        pts.append(PricePoint(Decimal(p), None, NOW - timedelta(minutes=15 * (len(today_prices) - 1 - i))))
    return pts


class TestTextoRecuo:
    def _text(self, hist, price):
        v = compute_verdict(Decimal(price), None, hist, NOW)
        assert v.verdict == "maquiado"
        return v, _render(v, price).replace("<b>", "").replace("</b>", "")

    def test_small_retreat_exact_text(self):
        v, text = self._text(_two_day_hike(["1247"]), "1247")
        assert v.peak_price == Decimal("1313")
        assert (
            "Antes de subir, custava R$ 1.000,00.\n"
            "Subiram 31% em 2 dias e depois baixaram 5%. "
            "Tá R$ 247,00 mais caro que antes. Segura."
        ) in text

    def test_retreat_pct_is_floored(self):
        # 1313 → 1240: 5,56% → "5%"
        _, text = self._text(_two_day_hike(["1240"]), "1240")
        assert "e depois baixaram 5%." in text

    def test_never_says_de_volta(self):
        _, text = self._text(_two_day_hike(["1247"]), "1247")
        assert "de volta" not in text


class TestHikeDaysMenosDeUmDia:
    def test_hike_started_hours_ago(self):
        v = _verdict(["1300", "1300", "1200"])
        assert v.verdict == "maquiado"
        assert v.hike_days == 0
        text = _render(v, "1200")
        assert "Subiram 30% em menos de um dia e depois baixaram 7%." in text
        assert "em 1 dia" not in text and "em 0 dias" not in text

    def test_exactly_24h_is_1_dia(self):
        pts = []
        t = NOW - timedelta(days=30)
        start = NOW - timedelta(hours=24)
        while t < start:
            pts.append(PricePoint(Decimal("1000"), None, t))
            t += timedelta(hours=1)
        pts.append(PricePoint(Decimal("1300"), None, start))
        pts.append(PricePoint(Decimal("1200"), None, NOW))
        v = compute_verdict(Decimal("1200"), None, pts, NOW)
        assert v.hike_days == 1
        assert "Subiram 30% em 1 dia e depois baixaram 7%." in _render(v, "1200")
