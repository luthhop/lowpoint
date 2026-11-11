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
        reason="desconto real",
        lowest_price=Decimal("3280.00"),
        median_30d=Decimal("3890.00"),
        monitoring_days=47,
        pre_hike_price=None,
        has_warranty=True,
        is_official=True,
        suspect_count=0,
        cheapest_suspect_price=None,
    )
    defaults.update(overrides)
    return AlertContext(**defaults)


class TestFormatAlertTargetHitReal:
    def test_alert_type(self):
        msg = format_alert(_ctx())
        assert msg.alert_type == "target_hit"

    def test_first_line_has_verdict_and_price(self):
        msg = format_alert(_ctx())
        first = msg.text.split("\n")[0]
        assert "PODE IR" in first
        assert "R$ 3.200,00" in first
        assert "PS5 Digital Edition" in first

    def test_mentions_target(self):
        msg = format_alert(_ctx())
        assert "R$ 3.500,00" in msg.text

    def test_brand_phrase(self):
        msg = format_alert(_ctx())
        assert "Pode ir." in msg.text

    def test_preco_normal_not_mediana(self):
        msg = format_alert(_ctx())
        assert "mediana" not in msg.text.lower()
        assert "Preço normal" in msg.text

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

    def test_brand_phrase(self):
        msg = format_alert(_ctx(price=Decimal("3600.00")))
        assert "Pode ir." in msg.text

    def test_abaixo_do_normal(self):
        msg = format_alert(_ctx(price=Decimal("3600.00")))
        assert "abaixo do normal" in msg.text

    def test_no_mediana(self):
        msg = format_alert(_ctx(price=Decimal("3600.00")))
        assert "mediana" not in msg.text.lower()

    def test_mentions_preco_normal(self):
        msg = format_alert(_ctx(price=Decimal("3600.00")))
        assert "Preço normal" in msg.text


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

    def test_subiram_pra_baixar(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            pre_hike_price=Decimal("3300.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "Subiram pra baixar" in msg.text
        assert "2 semanas" in msg.text
        assert "14d" not in msg.text

    def test_always_ends_with_segura(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            pre_hike_price=Decimal("3300.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "Segura." in msg.text

    def test_segura_without_pre_hike(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "Segura." in msg.text

    def test_preco_normal_no_ultimo_mes(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "último mês" in msg.text
        assert "30d" not in msg.text
        assert "mediana" not in msg.text.lower()

    def test_confronts_claimed_discount(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "Preço riscado:" in msg.text
        assert "R$ 6.000,00" in msg.text
        assert "40%" in msg.text

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
        assert "subiram pra baixar" in msg.text
        assert "Segura." in msg.text

    def test_first_line_segura(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3400.00"),
        ))
        first = msg.text.split("\n")[0]
        assert "SEGURA" in first

    def test_no_mediana(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3400.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "mediana" not in msg.text.lower()


class TestFormatAlertTargetHitNeutro:
    def test_alert_type(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("192.80"),
            target_price=Decimal("200.00"),
            monitoring_days=0,
        ))
        assert msg.alert_type == "target_hit"

    def test_emoji_and_text(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("192.80"),
            target_price=Decimal("200.00"),
            monitoring_days=0,
        ))
        assert "🎯" in msg.text
        assert "R$ 192,80" in msg.text
        assert "bateu teu alvo" in msg.text
        assert "juntando histórico (menos de 1 dia)" in msg.text
        assert "Não dá pra dizer" in msg.text
        assert "A decisão é tua." in msg.text

    def test_no_verdict_claim(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("192.80"),
            target_price=Decimal("200.00"),
            monitoring_days=0,
        ))
        assert "PODE IR" not in msg.text
        assert "SEGURA" not in msg.text
        assert "Pode ir." not in msg.text
        assert "Segura." not in msg.text

    def test_with_few_days(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("192.80"),
            target_price=Decimal("200.00"),
            monitoring_days=3,
        ))
        assert "3 dias" in msg.text
        assert "desde hoje" not in msg.text

    def test_footer_preserved(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("192.80"),
            target_price=Decimal("200.00"),
            monitoring_days=0,
            has_warranty=False,
            suspect_count=2,
            cheapest_suspect_price=Decimal("50.00"),
        ))
        assert "Sem garantia" in msg.text
        assert "golpe" in msg.text

    def test_button(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("192.80"),
            target_price=Decimal("200.00"),
            monitoring_days=0,
        ))
        assert msg.button_text == "Ver oferta"
        assert "MLB-4001551723" in msg.button_url

    def test_max_one_emoji(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("192.80"),
            target_price=Decimal("200.00"),
            monitoring_days=0,
            has_warranty=False,
            suspect_count=2,
            cheapest_suspect_price=Decimal("50.00"),
        ))
        assert msg.text.count("🎯") == 1
        assert "✅" not in msg.text
        assert "⚠" not in msg.text

    def test_maquiado_prevails(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("192.80"),
            target_price=Decimal("200.00"),
            monitoring_days=30,
            median_30d=Decimal("195.00"),
        ))
        assert msg.alert_type == "target_hit_maquiado"
        assert "SEGURA" in msg.text


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

    def test_preco_normal(self):
        msg = format_alert(_ctx(
            verdict="neutro",
            price=Decimal("4000.00"),
        ))
        assert "Preço normal" in msg.text
        assert "mediana" not in msg.text.lower()


class TestFooter:
    def test_sem_garantia_no_emoji(self):
        msg = format_alert(_ctx(has_warranty=False))
        lines = msg.text.split("\n")
        garantia_line = [l for l in lines if "Sem garantia" in l][0]
        assert "⚠" not in garantia_line

    def test_vendedor_nao_oficial(self):
        msg = format_alert(_ctx(is_official=False))
        assert "Vendedor não oficial" in msg.text

    def test_loja_oficial(self):
        msg = format_alert(_ctx(is_official=True))
        assert "Loja oficial" in msg.text

    def test_suspect_shows_cheapest_price(self):
        msg = format_alert(_ctx(
            suspect_count=3,
            cheapest_suspect_price=Decimal("2399.00"),
        ))
        assert "R$ 2.399,00" in msg.text
        assert "golpe" in msg.text

    def test_no_suspect_footer_when_zero(self):
        msg = format_alert(_ctx(suspect_count=0))
        assert "golpe" not in msg.text

    def test_single_suspect(self):
        msg = format_alert(_ctx(
            suspect_count=1,
            cheapest_suspect_price=Decimal("1500.00"),
        ))
        assert "Ignorei um anúncio" in msg.text
        assert "R$ 1.500,00" in msg.text

    def test_no_descartadas_text(self):
        msg = format_alert(_ctx(
            suspect_count=2,
            cheapest_suspect_price=Decimal("1200.00"),
        ))
        assert "descartada" not in msg.text

    def test_poucos_vendedores_com_1_oferta(self):
        msg = format_alert(_ctx(offer_count=1))
        assert "Poucos vendedores" in msg.text

    def test_poucos_vendedores_com_2_ofertas(self):
        msg = format_alert(_ctx(offer_count=2))
        assert "Poucos vendedores" in msg.text

    def test_sem_aviso_com_3_ofertas(self):
        msg = format_alert(_ctx(offer_count=3))
        assert "Poucos vendedores" not in msg.text

    def test_sem_aviso_sem_offer_count(self):
        msg = format_alert(_ctx())
        assert "Poucos vendedores" not in msg.text


class TestMaxOneEmoji:
    def test_real_one_emoji(self):
        msg = format_alert(_ctx())
        assert msg.text.count("✅") == 1
        assert "⚠" not in msg.text

    def test_maquiado_one_emoji(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            has_warranty=False,
            suspect_count=2,
            cheapest_suspect_price=Decimal("1200.00"),
        ))
        assert msg.text.count("⚠") == 1
        first_line = msg.text.split("\n")[0]
        assert "⚠" in first_line


class TestHtmlEscape:
    def test_ampersand_in_name(self):
        msg = format_alert(_ctx(product_name="TV Samsung 50\" 4K & HDR"))
        assert "&amp;" in msg.text


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
        assert _dias(0) == "hoje"


class TestPluralInAlerts:
    def test_1_dia_no_dias(self):
        msg = format_alert(_ctx(monitoring_days=1, lowest_price=Decimal("3100.00")))
        assert "1 dia" in msg.text
        assert "1 dias" not in msg.text

    def test_many_dias(self):
        msg = format_alert(_ctx(monitoring_days=47, lowest_price=Decimal("3100.00")))
        assert "47 dias" in msg.text


class TestNoAbbreviations:
    def test_no_30d(self):
        msg = format_alert(_ctx())
        assert "30d" not in msg.text

    def test_no_14d_in_maquiado(self):
        msg = format_alert(_ctx(
            verdict="maquiado",
            price=Decimal("3600.00"),
            pre_hike_price=Decimal("3300.00"),
            median_30d=Decimal("3450.00"),
        ))
        assert "14d" not in msg.text


class TestTargetHitNeutroReasons:
    """[TESTE] Alvo + neutro sem pico: um texto por motivo, texto inteiro."""

    FOOTER = "\n\nVendedor não oficial · Com garantia"

    def _text(self, **kw):
        base = dict(
            product_name="PS5 Digital Edition", item_id="MLB4001551723",
            original_price=None, verdict="neutro",
            reason="preço dentro da faixa normal (30 dias de dados)",
            median_30d=Decimal("3450.00"), baseline_price=Decimal("3450.00"),
            monitoring_days=30, pre_hike_price=None, has_warranty=True,
            is_official=False, suspect_count=0,
        )
        base.update(kw)
        msg = format_alert(AlertContext(**base))
        assert msg.alert_type == "target_hit"
        return msg.text.replace("<b>", "").replace("</b>", "")

    def test_below_normal_less_than_5pct(self):
        text = self._text(price=Decimal("3312.00"), target_price=Decimal("3350.00"),
                          lowest_price=Decimal("3312.00"))
        assert text == (
            "🎯 PS5 Digital Edition bateu teu alvo: R$ 3.312,00.\n\n"
            "Bateu, mas tá só 4% abaixo do normal. Ainda não é desconto de verdade. "
            "A decisão é tua.\n"
            "Preço normal: R$ 3.450,00" + self.FOOTER
        )

    def test_5pct_or_more_but_not_lowest(self):
        text = self._text(price=Decimal("3200.00"), target_price=Decimal("3300.00"),
                          lowest_price=Decimal("3100.00"))
        assert text == (
            "🎯 PS5 Digital Edition bateu teu alvo: R$ 3.200,00.\n\n"
            "Bateu e tá 7% abaixo do normal, mas já esteve mais barato: R$ 3.100,00. "
            "A decisão é tua.\n"
            "Preço normal: R$ 3.450,00" + self.FOOTER
        )

    @pytest.mark.parametrize("price", ["3450.00", "3500.00"])
    def test_at_or_above_normal(self, price):
        p = Decimal(price)
        text = self._text(price=p, target_price=Decimal("3600.00"),
                          lowest_price=Decimal("3400.00"))
        assert text == (
            f"🎯 PS5 Digital Edition bateu teu alvo: {fmt_brl(p)}.\n\n"
            "Bateu teu alvo, mas esse é o preço normal dele. Não é promoção. "
            "A decisão é tua.\n"
            "Preço normal: R$ 3.450,00" + self.FOOTER
        )

    def test_few_days_of_data(self):
        text = self._text(price=Decimal("3312.00"), target_price=Decimal("3350.00"),
                          lowest_price=Decimal("3312.00"), monitoring_days=3,
                          median_30d=None, baseline_price=None)
        assert text == (
            "🎯 PS5 Digital Edition bateu teu alvo: R$ 3.312,00.\n\n"
            "Bateu, mas ainda tô juntando histórico (3 dias). "
            "Não dá pra dizer se é desconto de verdade. A decisão é tua."
            + self.FOOTER
        )


class TestNoHikeNeverClaimsHike:
    """[TESTE] Sem pico, nenhum template fala em subida anterior."""

    @pytest.mark.parametrize("verdict", ["real", "neutro", "maquiado"])
    @pytest.mark.parametrize("price, target", [
        ("3200.00", "3300.00"),   # alvo atingido
        ("3200.00", "3000.00"),   # alvo não atingido
        ("3450.00", "3500.00"),
        ("3600.00", "3000.00"),
    ])
    @pytest.mark.parametrize("original", [None, "6000.00"])
    @pytest.mark.parametrize("days", [0, 3, 30, 120])
    @pytest.mark.parametrize("pre_hike", [None, "3450.00"])  # legado: pre_hike sem hike_pct
    def test_never_mentions_hike(self, verdict, price, target, original, days, pre_hike):
        ctx = AlertContext(
            product_name="PS5 Digital Edition", item_id="MLB4001551723",
            price=Decimal(price), original_price=Decimal(original) if original else None,
            target_price=Decimal(target), verdict=verdict, reason="motivo",
            lowest_price=Decimal("3100.00"), median_30d=Decimal("3450.00"),
            monitoring_days=days, pre_hike_price=Decimal(pre_hike) if pre_hike else None,
            hike_pct=None, hike_days=None, baseline_price=Decimal("3450.00"),
            has_warranty=True, is_official=True, suspect_count=0,
        )
        text = format_alert(ctx).text
        assert "Mesmo depois de subirem antes" not in text
        assert "subiram antes" not in text.lower()

