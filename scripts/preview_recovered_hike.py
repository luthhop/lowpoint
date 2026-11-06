"""[TESTE] Preview local de descontos pós-pico: sem rede ou banco.

Usage: python scripts/preview_recovered_hike.py
"""

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lowpoint.telegram.formatter import AlertContext, format_alert
from lowpoint.verdict import PricePoint, compute_verdict


def main():
    now = datetime(2026, 12, 2, 12, tzinfo=timezone.utc)
    baseline = Decimal("3450.00")
    original = Decimal("6000.00")
    history = [
        PricePoint(
            baseline if days > 17 else original if days > 5 else Decimal("3600"),
            None,
            now - timedelta(days=days),
        )
        for days in range(60, 0, -1)
    ]
    for pct in (4, 10, 20):
        price = baseline * (1 - Decimal(pct) / 100)
        v = compute_verdict(
            price, original, history + [PricePoint(price, original, now)], now,
        )
        ctx = AlertContext(
            product_name="PS5 Digital Edition", item_id="MLBEX0000100001",
            price=price, original_price=original, target_price=Decimal("3500"),
            verdict=v.verdict, reason=v.reason, lowest_price=v.lowest_price,
            median_30d=v.median_30d, monitoring_days=v.monitoring_days,
            pre_hike_price=v.pre_hike_price, hike_pct=v.hike_pct,
            hike_days=v.hike_days, baseline_price=v.baseline_price,
            has_warranty=True, is_official=True, suspect_count=0,
        )
        msg = format_alert(ctx)
        print(f"[TESTE] {pct}% abaixo do pré-pico | {v.verdict} | {msg.alert_type}")
        print(msg.text.replace("<b>", "").replace("</b>", ""))
        print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
