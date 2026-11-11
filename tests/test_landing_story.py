"""
[TESTE] Valida a história de exemplo da landing page contra o código real.
Monta offer_snapshots sintéticos e roda compute_verdict + format_alert.
NÃO grava na tabela alerts.

Testes marcados com "DEVE FALHAR" falham com o código ANTES do fix.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median as _median

import pytest

from lowpoint.best_offer import select_best_offer
from lowpoint.config import PRICE_HIKE_WINDOW_DAYS
from lowpoint.sources.base import OfferData
from lowpoint.telegram.formatter import AlertContext, format_alert
from lowpoint.verdict import PricePoint, compute_verdict


PRODUCT_NAME = "PS5 Digital Edition"
PRODUCT_ID = "MLBEX00001"
ITEM_ID = "MLBEX0000100001"
TARGET = Decimal("3300.00")


def _daily_points(start, end, price, original_price=None):
    """Gera um PricePoint por dia entre start e end (inclusive)."""
    points = []
    d = start
    while d <= end:
        points.append(PricePoint(
            price=price,
            original_price=original_price,
            collected_at=d,
        ))
        d += timedelta(days=1)
    return points


def _build_history_until(end_date):
    """Monta a série completa até end_date.

    Timeline (pico em 15/11, confirmado):
      Ago 1 – Nov 14: R$ 3.450 (preço normal estável)
      Nov 15 – Nov 26: R$ 6.000 (markup silencioso, +74%)
      Nov 27 – Dec 10: R$ 3.600 ("40% OFF" e pós-BF)
      Dec 11+: R$ 3.200 (desconto real)
    """
    points = []
    points += _daily_points(
        datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
        min(datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc), end_date),
        Decimal("3450.00"),
    )
    if end_date >= datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc):
        points += _daily_points(
            datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc),
            min(datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc), end_date),
            Decimal("6000.00"),
        )
    if end_date >= datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc):
        points += _daily_points(
            datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc),
            min(datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc), end_date),
            Decimal("3600.00"),
        )
    if end_date >= datetime(2026, 12, 11, 12, 0, tzinfo=timezone.utc):
        points += _daily_points(
            datetime(2026, 12, 11, 12, 0, tzinfo=timezone.utc),
            end_date,
            Decimal("3200.00"),
        )
    return points


# ─── SEGURA (27/Nov) ────────────────────────────────────────────────

class TestLandingSegura27Nov:
    """27/Nov (BF): R$ 3.600 com original R$ 6.000 → SEGURA."""

    def test_verdict_is_maquiado(self):
        history = _build_history_until(
            datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 11, 27, 12, 0, 0, tzinfo=timezone.utc)
        result = compute_verdict(
            current_price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            history=history,
            now=now,
        )
        assert result.verdict == "maquiado"
        assert result.pre_hike_price is not None

    def test_median_is_prehike(self):
        """median_30d deve ser o preço pré-pico (R$ 3.450)."""
        history = _build_history_until(
            datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 11, 27, 12, 0, 0, tzinfo=timezone.utc)
        result = compute_verdict(
            current_price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            history=history,
            now=now,
        )
        assert result.median_30d == Decimal("3450.00"), (
            f"Expected R$ 3.450 (pre-hike), got R$ {result.median_30d}"
        )

    def test_formatted_alert_has_segura(self):
        history = _build_history_until(
            datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 11, 27, 12, 0, 0, tzinfo=timezone.utc)
        v = compute_verdict(
            current_price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            history=history,
            now=now,
        )
        ctx = AlertContext(
            product_name=PRODUCT_NAME,
            item_id=ITEM_ID,
            price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            target_price=TARGET,
            verdict=v.verdict,
            reason=v.reason,
            lowest_price=v.lowest_price,
            median_30d=v.median_30d,
            monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price,
            has_warranty=True,
            is_official=False,
            suspect_count=0,
        )
        msg = format_alert(ctx)
        assert "SEGURA" in msg.text
        assert msg.alert_type == "verdict_maquiado"

    def test_segura_shows_peak_markup(self):
        """O alerta SEGURA deve mostrar o markup do pico (74%), não 4%."""
        history = _build_history_until(
            datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 11, 27, 12, 0, 0, tzinfo=timezone.utc)
        v = compute_verdict(
            current_price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            history=history,
            now=now,
        )
        ctx = AlertContext(
            product_name=PRODUCT_NAME,
            item_id=ITEM_ID,
            price=Decimal("3600.00"),
            original_price=Decimal("6000.00"),
            target_price=TARGET,
            verdict=v.verdict,
            reason=v.reason,
            lowest_price=v.lowest_price,
            median_30d=v.median_30d,
            monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price,
            hike_pct=v.hike_pct,
            hike_days=v.hike_days,
            has_warranty=True,
            is_official=False,
            suspect_count=0,
        )
        msg = format_alert(ctx)
        assert "74%" in msg.text, (
            f"Expected peak markup '74%' in SEGURA message. Got:\n{msg.text}"
        )


# ─── PODE IR (02/Dez) — BUG: deve ser REAL ─────────────────────────

class TestLandingPodeIr02Dez:
    """DEVE FALHAR: 02/Dez R$ 3.200 é 7% abaixo do pré-pico → REAL."""

    def test_verdict_is_real(self):
        history = _build_history_until(
            datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        result = compute_verdict(
            current_price=Decimal("3200.00"),
            original_price=None,
            history=history,
            now=now,
        )
        assert result.verdict == "real", (
            f"Expected 'real' but got '{result.verdict}'. "
            f"R$ 3.200 is 7.25% below pre-hike R$ 3.450 (> 5% threshold)."
        )

    def test_baseline_is_prehike_not_contaminated(self):
        """baseline_price deve ser o preço pré-pico (R$ 3.450), não a mediana contaminada."""
        history = _build_history_until(
            datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        result = compute_verdict(
            current_price=Decimal("3200.00"),
            original_price=None,
            history=history,
            now=now,
        )
        assert result.baseline_price == Decimal("3450.00"), (
            f"Expected baseline R$ 3.450 (pre-hike) but got R$ {result.baseline_price}. "
            f"Hike prices should not contaminate the baseline."
        )
        assert result.median_30d != result.baseline_price, (
            "median_30d should be the real (contaminated) 30d median, not the baseline"
        )

    def test_formatted_alert_shows_pode_ir(self):
        """DEVE FALHAR (depende do fix do veredito)."""
        history = _build_history_until(
            datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        v = compute_verdict(
            current_price=Decimal("3200.00"),
            original_price=None,
            history=history,
            now=now,
        )
        ctx = AlertContext(
            product_name=PRODUCT_NAME,
            item_id=ITEM_ID,
            price=Decimal("3200.00"),
            original_price=None,
            target_price=TARGET,
            verdict=v.verdict,
            reason=v.reason,
            lowest_price=v.lowest_price,
            median_30d=v.median_30d,
            monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price,
            hike_pct=v.hike_pct,
            hike_days=v.hike_days,
            baseline_price=v.baseline_price,
            has_warranty=True,
            is_official=True,
            suspect_count=1,
            cheapest_suspect_price=Decimal("1899.00"),
        )
        msg = format_alert(ctx)
        assert "PODE IR" in msg.text, (
            f"Expected 'PODE IR' in alert. Got:\n{msg.text}"
        )
        assert "7%" in msg.text, (
            f"Expected '7%' (discount vs pre-hike R$ 3.450). Got:\n{msg.text}"
        )


# ─── "desde que começamos a monitorar" ──────────────────────────────

class TestFormatterMenorDesde:
    """DEVE FALHAR: menor preço == todo o histórico → 'desde que começamos'."""

    def test_menor_desde_dez11(self):
        """Dec 11 — veredito já funciona, só o texto do formatter está errado."""
        history = _build_history_until(
            datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 12, 11, 12, 0, 0, tzinfo=timezone.utc)
        v = compute_verdict(
            current_price=Decimal("3200.00"),
            original_price=None,
            history=history,
            now=now,
        )
        ctx = AlertContext(
            product_name=PRODUCT_NAME,
            item_id=ITEM_ID,
            price=Decimal("3200.00"),
            original_price=None,
            target_price=TARGET,
            verdict=v.verdict,
            reason=v.reason,
            lowest_price=v.lowest_price,
            median_30d=v.median_30d,
            monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price,
            has_warranty=True,
            is_official=True,
            suspect_count=1,
            cheapest_suspect_price=Decimal("1899.00"),
        )
        msg = format_alert(ctx)
        assert "desde que começamos a monitorar" in msg.text, (
            f"Expected 'desde que começamos a monitorar'. Got:\n{msg.text}"
        )


# ─── PODE IR (11/Dez) – regressão ──────────────────────────────────

class TestLandingPodeIr11Dez:
    """11/Dez: R$ 3.200 → hike já saiu da janela naturalmente."""

    def test_verdict_is_real(self):
        history = _build_history_until(
            datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 12, 11, 12, 0, 0, tzinfo=timezone.utc)
        result = compute_verdict(
            current_price=Decimal("3200.00"),
            original_price=None,
            history=history,
            now=now,
        )
        assert result.verdict == "real"

    def test_formatted_alert(self):
        history = _build_history_until(
            datetime(2026, 12, 10, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 12, 11, 12, 0, 0, tzinfo=timezone.utc)
        v = compute_verdict(
            current_price=Decimal("3200.00"),
            original_price=None,
            history=history,
            now=now,
        )
        ctx = AlertContext(
            product_name=PRODUCT_NAME,
            item_id=ITEM_ID,
            price=Decimal("3200.00"),
            original_price=None,
            target_price=TARGET,
            verdict=v.verdict,
            reason=v.reason,
            lowest_price=v.lowest_price,
            median_30d=v.median_30d,
            monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price,
            has_warranty=True,
            is_official=True,
            suspect_count=1,
            cheapest_suspect_price=Decimal("1899.00"),
        )
        msg = format_alert(ctx)
        assert "PODE IR" in msg.text
        assert msg.alert_type == "target_hit"
        assert "R$ 3.300,00" in msg.text


# ─── Regressão: maquiado legítimo ───────────────────────────────────

class TestHikeStillMaquiadoWhenSmallDiscount:
    """R$ 3.400 em 02/dez (1.4% abaixo do pré-pico) → ainda maquiado."""

    def test_small_discount_still_maquiado(self):
        history = _build_history_until(
            datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
        )
        now = datetime(2026, 12, 2, 12, 0, 0, tzinfo=timezone.utc)
        result = compute_verdict(
            current_price=Decimal("3400.00"),
            original_price=None,
            history=history,
            now=now,
        )
        assert result.verdict == "maquiado", (
            f"R$ 3.400 is only 1.4% below pre-hike R$ 3.450 — "
            f"should be maquiado, got '{result.verdict}'"
        )


# ─── GOLPE ──────────────────────────────────────────────────────────

# ─── Template SEGURA opção C: 3 casos ──────────────────────────────

class TestSeguraTemplateC:
    """[TESTE] Template SEGURA opção C, texto exato, via compute_verdict + format_alert."""

    NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
    FOOTER = "\n\nVendedor não oficial · Com garantia"
    HEAD = (
        "⚠ SEGURA · PS5 Digital Edition · {price}\n\n"
        "O anúncio diz {off} OFF (de R$ 6.000,00).\n"
        "Antes de subir, custava R$ 3.450,00.\n"
        "Subiram 74% em 12 dias e baixaram de volta. "
    )

    def _render(self, price):
        history = _build_history_until(
            datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
        )
        v = compute_verdict(price, Decimal("6000.00"), history, self.NOW)
        assert v.verdict == "maquiado"
        assert v.hike_days == 12  # 15/11 (início do pico) → 27/11
        ctx = AlertContext(
            product_name=PRODUCT_NAME, item_id=ITEM_ID, price=price,
            original_price=Decimal("6000.00"), target_price=TARGET,
            verdict=v.verdict, reason=v.reason, lowest_price=v.lowest_price,
            median_30d=v.median_30d, monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price, hike_pct=v.hike_pct,
            hike_days=v.hike_days, baseline_price=v.baseline_price,
            has_warranty=True, is_official=False, suspect_count=0,
        )
        msg = format_alert(ctx)
        assert msg.alert_type == "verdict_maquiado"
        return msg.text.replace("<b>", "").replace("</b>", "")

    def test_standard_27nov_mais_caro(self):
        text = self._render(Decimal("3600.00"))
        assert text == (
            self.HEAD.format(price="R$ 3.600,00", off="40%")
            + "Tá R$ 150,00 mais caro que antes. Segura."
            + self.FOOTER
        )

    def test_edge_2pct_below_prehike(self):
        text = self._render(Decimal("3381.00"))  # 3.450 × 0,98
        assert text == (
            self.HEAD.format(price="R$ 3.381,00", off="43%")
            + "Tá só 2% abaixo do que custava antes. Desconto de fachada. Segura."
            + self.FOOTER
        )
        assert "-R$" not in text and "−R$" not in text

    def test_tied_equal_to_prehike(self):
        text = self._render(Decimal("3450.00"))
        assert text == (
            self.HEAD.format(price="R$ 3.450,00", off="42%")
            + "Voltou ao preço de antes. Desconto de fachada. Segura."
            + self.FOOTER
        )
        assert "R$ 0,00" not in text

    def _render_any(self, price, target):
        history = _build_history_until(
            datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
        )
        history.append(PricePoint(price, Decimal("6000.00"), self.NOW))
        v = compute_verdict(price, Decimal("6000.00"), history, self.NOW)
        ctx = AlertContext(
            product_name=PRODUCT_NAME, item_id=ITEM_ID, price=price,
            original_price=Decimal("6000.00"), target_price=target,
            verdict=v.verdict, reason=v.reason, lowest_price=v.lowest_price,
            median_30d=v.median_30d, monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price, hike_pct=v.hike_pct,
            hike_days=v.hike_days, baseline_price=v.baseline_price,
            has_warranty=True, is_official=False, suspect_count=0,
        )
        msg = format_alert(ctx)
        return v, msg, msg.text.replace("<b>", "").replace("</b>", "")

    def test_faixa_4pct_below_prehike_is_monitorando(self):
        """Faixa 3–5%: 4% abaixo do pré-pico → neutro, MONITORANDO, sem SEGURA."""
        v, msg, text = self._render_any(Decimal("3312.00"), TARGET)  # 3.450 × 0,96
        assert v.verdict == "neutro"
        assert v.baseline_price == Decimal("3450.00")
        assert msg.alert_type == "neutro"
        assert text == (
            "MONITORANDO · PS5 Digital Edition · R$ 3.312,00\n\n"
            "Preço dentro da faixa normal (90 dias de dados).\n"
            "Subiram antes, mas mesmo assim tá 4% abaixo do preço normal.\n"
            "Preço normal: R$ 3.450,00"
            + self.FOOTER
        )

    def test_faixa_4pct_with_target_hit(self):
        """4% abaixo + alvo atingido: único caso em que o neutro vira mensagem."""
        v, msg, text = self._render_any(Decimal("3312.00"), Decimal("3350.00"))
        assert v.verdict == "neutro"
        assert msg.alert_type == "target_hit"
        assert "SEGURA" not in text and "PODE IR" not in text
        assert "alvo atingido" not in text and "O alvo foi" not in text
        assert text == (
            "🎯 PS5 Digital Edition bateu teu alvo: R$ 3.312,00.\n\n"
            "Bateu, mas não é desconto de verdade: subiram antes e agora "
            "tá só 4% abaixo do normal. A decisão é tua.\n"
            "Preço normal: R$ 3.450,00"
            + self.FOOTER
        )

    def test_target_hit_neutro_without_hike(self):
        """Sem pico: corpo genérico, sem menção a subida."""
        ctx = AlertContext(
            product_name=PRODUCT_NAME, item_id=ITEM_ID, price=Decimal("3400.00"),
            original_price=None, target_price=Decimal("3450.00"),
            verdict="neutro", reason="preço dentro da faixa normal (30 dias de dados)",
            lowest_price=Decimal("3350.00"), median_30d=Decimal("3450.00"),
            monitoring_days=30, pre_hike_price=None, has_warranty=True,
            is_official=False, suspect_count=0, baseline_price=Decimal("3450.00"),
        )
        text = format_alert(ctx).text.replace("<b>", "").replace("</b>", "")
        assert text == (
            "🎯 PS5 Digital Edition bateu teu alvo: R$ 3.400,00.\n\n"
            "Bateu, mas ainda não é desconto de verdade pelos critérios do "
            "Lowpoint. A decisão é tua.\n"
            "Preço normal: R$ 3.450,00"
            + self.FOOTER
        )

    def test_pode_ir_with_hike_has_single_7pct_line(self):
        """PODE IR pós-pico com alvo: os 7% aparecem uma vez, numa linha só."""
        v, msg, text = self._render_any(Decimal("3208.50"), TARGET)  # 3.450 × 0,93
        assert v.verdict == "real"
        assert msg.alert_type == "target_hit"
        assert text.count("7%") == 1
        assert (
            "Menor preço desde que começamos a monitorar. "
            "Mesmo depois de subirem antes, tá 7% abaixo do normal.\n"
        ) in text

    def test_pode_ir_without_hike_keeps_original_line(self):
        ctx = AlertContext(
            product_name=PRODUCT_NAME, item_id=ITEM_ID, price=Decimal("3200.00"),
            original_price=None, target_price=TARGET, verdict="real",
            reason="desconto real", lowest_price=Decimal("3200.00"),
            median_30d=Decimal("3450.00"), monitoring_days=30,
            pre_hike_price=None, has_warranty=True, is_official=True,
            suspect_count=0, baseline_price=Decimal("3450.00"),
        )
        text = format_alert(ctx).text
        assert "Menor preço desde que começamos a monitorar, 7% abaixo do normal.\n" in text
        assert "subirem" not in text and "Subiram" not in text

    def test_verdict_real_with_hike_has_single_line(self):
        """PODE IR pós-pico sem alvo atingido (verdict_real): mesma junção."""
        v, msg, text = self._render_any(Decimal("3208.50"), Decimal("3000.00"))
        assert msg.alert_type == "verdict_real"
        assert text.count("7%") == 1
        assert (
            "Novo menor preço. Mesmo depois de subirem antes, tá 7% abaixo do normal."
        ) in text

    def test_hike_days_follows_hike_start(self):
        """{dias} acompanha o início do pico, não a janela fixa de 14 dias."""
        later = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
        history = _build_history_until(datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc))
        v = compute_verdict(Decimal("3600.00"), Decimal("6000.00"), history, later)
        assert v.hike_days == 5


class TestLandingGolpe:
    """Verifica o limiar do filtro anti-golpe para o exemplo."""

    def test_2399_not_suspect(self):
        """R$ 2.399 NÃO é flagrado com mediana ~R$ 3.450 (60% = R$ 2.070)."""
        offers = [
            OfferData(
                item_id=f"MLBEX{i:05d}",
                seller_id=i,
                price=Decimal("3450.00"),
                original_price=None,
                condition="new",
                official_store_id=1 if i == 0 else None,
                free_shipping=True,
                warranty="12 meses",
            )
            for i in range(10)
        ]
        offers.append(OfferData(
            item_id="MLBEX99999",
            seller_id=999,
            price=Decimal("2399.00"),
            original_price=None,
            condition="new",
            official_store_id=None,
            free_shipping=True,
            warranty="12 meses",
        ))
        result = select_best_offer(offers)
        assert Decimal("2399.00") not in [o.price for o in result.suspect_offers]

    def test_1899_is_suspect(self):
        """R$ 1.899 É flagrado com mediana ~R$ 3.450 (60% = R$ 2.070)."""
        offers = [
            OfferData(
                item_id=f"MLBEX{i:05d}",
                seller_id=i,
                price=Decimal("3450.00"),
                original_price=None,
                condition="new",
                official_store_id=1 if i == 0 else None,
                free_shipping=True,
                warranty="12 meses",
            )
            for i in range(10)
        ]
        offers.append(OfferData(
            item_id="MLBEX99999",
            seller_id=999,
            price=Decimal("1899.00"),
            original_price=None,
            condition="new",
            official_store_id=None,
            free_shipping=True,
            warranty="12 meses",
        ))
        result = select_best_offer(offers)
        assert Decimal("1899.00") in [o.price for o in result.suspect_offers]


class TestRecoveredHike:
    """[TESTE] Pipeline em memória, sem Telegram ou banco de produção."""

    @pytest.mark.parametrize("discount, expected", [
        ("0.0299", "maquiado"),
        ("0.03", "maquiado"),
        ("0.0301", "neutro"),
        ("0.04", "neutro"),
        ("0.05", "real"),
        ("0.10", "real"),
        ("0.20", "real"),
    ])
    @pytest.mark.parametrize("original", [None, Decimal("6000.00")])
    @pytest.mark.parametrize("target", [Decimal("1000"), Decimal("3500")])
    def test_recovered_price_follows_normal_rules(self, discount, expected, original, target):
        now = datetime(2026, 12, 2, 12, tzinfo=timezone.utc)
        history = _build_history_until(now - timedelta(days=1))
        price = Decimal("3450") * (1 - Decimal(discount))
        # The collector stores the current sample before computing the verdict.
        history.append(PricePoint(price, original, now))
        v = compute_verdict(price, original, history, now)
        assert v.verdict == expected
        assert v.baseline_price == Decimal("3450")
        assert v.median_30d != v.baseline_price
        if expected != "maquiado":
            # Same outcome as a stable history without the artificial hike.
            clean_history = [
                PricePoint(Decimal("3450"), None, p.collected_at)
                for p in history
            ]
            clean_history[-1] = PricePoint(price, None, now)
            clean = compute_verdict(price, None, clean_history, now)
            assert v.verdict == clean.verdict
        ctx = AlertContext(
            product_name=PRODUCT_NAME, item_id=ITEM_ID, price=price,
            original_price=original, target_price=target,
            verdict=v.verdict, reason=v.reason, lowest_price=v.lowest_price,
            median_30d=v.median_30d, monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price, hike_pct=v.hike_pct,
            hike_days=v.hike_days, baseline_price=v.baseline_price,
            has_warranty=True, is_official=True, suspect_count=0,
        )
        msg = format_alert(ctx)
        if expected == "maquiado":
            assert "SEGURA" in msg.text
            return
        assert "SEGURA" not in msg.text
        assert "Segura" not in msg.text
        post_hike = {
            "neutro": "Subiram antes, mas mesmo assim tá",
            "target_hit_neutro": "subiram antes e agora tá só",
            "real": "Mesmo depois de subirem antes, tá",
        }
        key = expected
        if expected == "neutro" and price <= target:
            key = "target_hit_neutro"
        assert msg.text.count(post_hike[key]) == 1
        assert "Preço normal: R$ 3.450,00" in msg.text
        assert "Ainda tô conhecendo" not in msg.text
        if expected == "real":
            assert "PODE IR" in msg.text
        else:
            assert "PODE IR" not in msg.text

    def test_recovery_does_not_bypass_historical_low(self):
        now = datetime(2026, 12, 2, 12, tzinfo=timezone.utc)
        history = _build_history_until(now - timedelta(days=1))
        history.append(PricePoint(Decimal("2500"), None, now - timedelta(days=60)))
        v = compute_verdict(Decimal("2760"), Decimal("6000"), history, now)
        assert v.verdict == "neutro"
        assert v.lowest_price == Decimal("2500")

    def test_fachada_threshold_is_configurable(self):
        now = datetime(2026, 12, 2, 12, tzinfo=timezone.utc)
        history = _build_history_until(now - timedelta(days=1))
        v = compute_verdict(
            Decimal("3312"), None, history, now,
            fachada_threshold=Decimal("0.02"),
            real_discount_threshold=Decimal("0.03"),
        )
        assert v.verdict == "real"
