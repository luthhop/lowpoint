from decimal import Decimal

import pytest

from lowpoint.telegram.formatter import (
    AlertContext,
    AlertMessage,
    _dias,
    fmt_brl,
    format_alert,
    item_url,
)


class TestFmtBrl:
    def test_simple(self):
        assert fmt_brl(Decimal("1234.56")) == "R$ 1.234,56"

    def test_thousands(self):
        assert fmt_brl(Decimal("1234567.89")) == "R$ 1.234.567,89"

    def test_zero(self):
        assert fmt_brl(Decimal("0")) == "R$ 0,00"

    def test_cents_only(self):
        assert fmt_brl(Decimal("0.99")) == "R$ 0,99"

    def test_no_cents(self):
        assert fmt_brl(Decimal("100")) == "R$ 100,00"

    def test_large(self):
        assert fmt_brl(Decimal("99999.00")) == "R$ 99.999,00"

    def test_exact_thousand(self):
        assert fmt_brl(Decimal("1000.00")) == "R$ 1.000,00"

    def test_single_digit(self):
        assert fmt_brl(Decimal("5.50")) == "R$ 5,50"


class TestItemUrl:
    def test_mlb(self):
        assert item_url("MLB1234567890") == (
            "https://produto.mercadolivre.com.br/MLB-1234567890"
        )

    def test_short_id(self):
        assert item_url("MLB123") == (
            "https://produto.mercadolivre.com.br/MLB-123"
        )


def _ctx(**overrides) -> AlertContext:
    defaults = dict(
        product_name="PS5 Digital Edition",
        item_id="MLB4001551723",
        price=Decimal("3200.00"),
        original_price=Decimal("4500.00"),
        target_price=Decimal("3500.00"),
        verdict="real",
        reason="desconto real de 18% vs. mediana — menor preço em 47 dias",
        lowest_price=Decimal("3280.00"),
        median_30d=Decimal("3890.00"),
        monitoring_days=47,
        pre_hike_price=None,
        has_warranty=True,
        is_official=True,
        suspect_count=0,
    )
    defaults.update(overrides)
    return AlertContext(**defaults)


class TestFormatAlertTargetHitReal:
    def test_alert_type(self):
        msg = format_alert(_ctx())
        assert msg.alert_type == "target_hit"

    def test_first_line_has_verdict_and_price(self):
        msg = format_alert(_ctx())
        assert "PODE IR" in msg.text.split("\n")[0]
        assert "R$ 3.200,00" in msg.text.split("\n")[0]
        assert "PS5 Digital Edition" in msg.text.split("\n")[0]

    def test_mentions_target(self):
        msg = format_alert(_ctx())
        assert "R$ 3.500,00" in msg.text

    def test_mentions_median(self):
        msg = format_alert(_ctx())
        assert "R$ 3.890,00" in msg.text

    def test_mentions_lowest(self):
        msg = format_alert(_ctx())
        assert "R$ 3.280,00" in msg.text

    def test_button(self):
        msg = format_alert(_ctx())
        assert msg.button_text == "Ver oferta"
        assert "MLB-4001551723" in msg.button_url

    def test_parse_mode_html(self):
        msg = format_alert(_ctx())
        assert msg.parse_mode == "HTML"


class TestFormatAlertVerdictReal:
    def test_no_target_hit(self):
        msg = format_alert(_ctx(price=Decimal("3600.00")))
        assert msg.alert_type == "verdict_real"

    def test_first_line(self):
        msg = format_alert(_ctx(price=Decimal("3600.00")))
        first = msg.text.split("\n")[0]
        assert "PODE IR" in first
        assert "R$ 3.600,00" in first

    def test_mentions_menor_preco(self):
        msg = format_alert(_ctx(price=Decimal("3600.00")))
        assert "menor preço" in msg.text.lower()


class TestFormatAlertMaquiado:
    def test_alert_type(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            median_30d=Decimal("3450.00"),
            pre_hike_price=Decimal("3300.00"),
        ))
        assert msg.alert_type == "verdict_maquiado"

    def test_first_line_segura(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
        ))
        first = msg.text.split("\n")[0]
        assert "SEGURA" in first
        assert "R$ 3.600,00" in first

    def test_confronts_claimed_discount(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "40% OFF" in msg.text
        assert "R$ 6.000,00" in msg.text
        assert "R$ 3.450,00" in msg.text

    def test_shows_pre_hike(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            pre_hike_price=Decimal("3300.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "R$ 3.300,00" in msg.text


class TestFormatAlertTargetHitMaquiado:
    def test_alert_type(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3400.00"),
            original_price=Decimal("5600.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert msg.alert_type == "target_hit_maquiado"

    def test_mentions_both_facts(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3400.00"),
            original_price=Decimal("5600.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "teu alvo" in msg.text
        assert "maquiado" in msg.text

    def test_first_line_segura(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3400.00"),
        ))
        first = msg.text.split("\n")[0]
        assert "SEGURA" in first


class TestFormatAlertNeutro:
    def test_alert_type(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("4000.00"),
        ))
        assert msg.alert_type == "neutro"

    def test_first_line_monitorando(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("4000.00"),
        ))
        first = msg.text.split("\n")[0]
        assert "MONITORANDO" in first


class TestFooter:
    def test_sem_garantia_highlighted(self):
        msg = format_alert(_ctx(has_warranty=False))
        assert "Sem garantia informada" in msg.text

    def test_vendedor_nao_oficial_discrete(self):
        msg = format_alert(_ctx(is_official=False))
        assert "Vendedor não-oficial" in msg.text

    def test_loja_oficial(self):
        msg = format_alert(_ctx(is_official=True))
        assert "Loja oficial" in msg.text

    def test_suspect_footer(self):
        msg = format_alert(_ctx(suspect_count=3))
        assert "3 ofertas suspeitas descartadas" in msg.text

    def test_no_suspect_footer_when_zero(self):
        msg = format_alert(_ctx(suspect_count=0))
        assert "suspeita" not in msg.text

    def test_single_suspect(self):
        msg = format_alert(_ctx(suspect_count=1))
        assert "1 oferta suspeita descartada" in msg.text


class TestHtmlEscape:
    def test_ampersand_in_name(self):
        msg = format_alert(_ctx(product_name="TV Samsung 50\" 4K & HDR"))
        assert "&amp;" in msg.text
        assert "&#x27;" in msg.text or "&quot;" in msg.text or '"' not in msg.text.split("\n")[0]


class TestNoOriginalPrice:
    def test_maquiado_without_original(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            original_price=None,
            median_30d=Decimal("3450.00"),
        ))
        assert "OFF" not in msg.text
        assert "R$ 3.450,00" in msg.text


class TestDias:
    def test_singular(self):
        assert _dias(1) == "1 dia"

    def test_plural(self):
        assert _dias(2) == "2 dias"
        assert _dias(30) == "30 dias"

    def test_zero(self):
        assert _dias(0) == "0 dias"


class TestPluralInAlerts:
    def test_1_dia_no_dias(self):
        msg = format_alert(_ctx(monitoring_days=1))
        assert "1 dia" in msg.text
        assert "1 dias" not in msg.text

    def test_many_dias(self):
        msg = format_alert(_ctx(monitoring_days=47))
        assert "47 dias" in msg.text
