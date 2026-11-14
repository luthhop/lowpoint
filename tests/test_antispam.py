"""Regras do anti-spam por watch (lowpoint.antispam.should_send)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from lowpoint.antispam import alert_kind, should_send
from lowpoint.config import (
    ALERT_MIN_INTERVAL,
    MAQUIADO_REPEAT_INTERVAL,
    REPEAT_ALERT_MIN_DROP,
)

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)


def _last(alert_type: str, price: str, ago: timedelta):
    return SimpleNamespace(
        alert_type=alert_type,
        price_at_alert=Decimal(price),
        sent_at=NOW - ago,
    )


class TestConstants:
    def test_values(self):
        assert ALERT_MIN_INTERVAL == timedelta(hours=1)
        assert MAQUIADO_REPEAT_INTERVAL == timedelta(hours=24)
        assert REPEAT_ALERT_MIN_DROP == Decimal("0.03")


class TestAlertKind:
    @pytest.mark.parametrize("alert_type,kind", [
        ("verdict_real", "real"),
        ("target_hit", "target_hit"),
        ("verdict_maquiado", "maquiado"),
        ("target_hit_maquiado", "maquiado"),
        ("neutro", "neutro"),
    ])
    def test_mapping(self, alert_type, kind):
        assert alert_kind(alert_type) == kind


class TestFirstAlert:
    @pytest.mark.parametrize("alert_type", [
        "verdict_real", "target_hit", "verdict_maquiado", "target_hit_maquiado",
    ])
    def test_no_previous_alert_sends(self, alert_type):
        assert should_send(alert_type, Decimal("1000"), NOW, None).send


class TestHourlyCap:
    def test_59_minutes_blocks_even_on_type_change(self):
        last = _last("verdict_maquiado", "1000", timedelta(minutes=59))
        d = should_send("verdict_real", Decimal("500"), NOW, last)
        assert not d.send
        assert "1 por hora" in d.reason

    def test_exactly_1h_allows_type_change(self):
        last = _last("verdict_maquiado", "1000", timedelta(hours=1))
        assert should_send("verdict_real", Decimal("1000"), NOW, last).send

    def test_just_under_1h_blocks(self):
        last = _last("verdict_maquiado", "1000", timedelta(hours=1) - timedelta(seconds=1))
        assert not should_send("verdict_real", Decimal("1000"), NOW, last).send

    def test_cap_applies_to_big_drop_same_type(self):
        last = _last("target_hit", "1000", timedelta(minutes=15))
        assert not should_send("target_hit", Decimal("500"), NOW, last).send

    def test_naive_sent_at_is_utc(self):
        """SQLite devolve datetime sem fuso; tratado como UTC."""
        last = SimpleNamespace(
            alert_type="verdict_maquiado",
            price_at_alert=Decimal("1000"),
            sent_at=(NOW - timedelta(minutes=30)).replace(tzinfo=None),
        )
        assert not should_send("verdict_real", Decimal("1000"), NOW, last).send


class TestTypeChange:
    @pytest.mark.parametrize("prev,curr", [
        ("verdict_maquiado", "verdict_real"),
        ("verdict_real", "target_hit"),
        ("target_hit", "verdict_real"),
        ("target_hit", "target_hit_maquiado"),
    ])
    def test_type_change_sends_even_if_price_higher(self, prev, curr):
        last = _last(prev, "1000", timedelta(hours=2))
        d = should_send(curr, Decimal("1100"), NOW, last)
        assert d.send
        assert "mudou" in d.reason

    def test_maquiado_variants_are_same_type(self):
        last = _last("verdict_maquiado", "1000", timedelta(hours=2))
        assert not should_send("target_hit_maquiado", Decimal("900"), NOW, last).send


class TestPriceDropRule:
    @pytest.mark.parametrize("alert_type", ["verdict_real", "target_hit"])
    def test_exactly_3_percent_sends(self, alert_type):
        last = _last(alert_type, "1000.00", timedelta(hours=2))
        assert should_send(alert_type, Decimal("970.00"), NOW, last).send

    @pytest.mark.parametrize("alert_type", ["verdict_real", "target_hit"])
    def test_just_under_3_percent_blocks(self, alert_type):
        last = _last(alert_type, "1000.00", timedelta(hours=2))
        d = should_send(alert_type, Decimal("970.01"), NOW, last)
        assert not d.send
        assert "3%" in d.reason

    @pytest.mark.parametrize("alert_type", ["verdict_real", "target_hit"])
    def test_same_or_higher_price_blocks(self, alert_type):
        last = _last(alert_type, "1000.00", timedelta(days=3))
        assert not should_send(alert_type, Decimal("1000.00"), NOW, last).send
        assert not should_send(alert_type, Decimal("1010.00"), NOW, last).send

    def test_1_percent_oscillation_blocks(self):
        last = _last("target_hit", "1000.00", timedelta(hours=2))
        assert not should_send("target_hit", Decimal("990.00"), NOW, last).send


class TestMaquiadoRule:
    @pytest.mark.parametrize("alert_type", ["verdict_maquiado", "target_hit_maquiado"])
    def test_exactly_24h_sends(self, alert_type):
        last = _last(alert_type, "1000", timedelta(hours=24))
        assert should_send(alert_type, Decimal("1000"), NOW, last).send

    @pytest.mark.parametrize("alert_type", ["verdict_maquiado", "target_hit_maquiado"])
    def test_just_under_24h_blocks_even_with_big_drop(self, alert_type):
        last = _last(alert_type, "1000", timedelta(hours=24) - timedelta(seconds=1))
        d = should_send(alert_type, Decimal("500"), NOW, last)
        assert not d.send
        assert "24h" in d.reason
